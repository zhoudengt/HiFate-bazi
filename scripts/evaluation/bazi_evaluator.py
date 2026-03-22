#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字评测主脚本

批量调用流式接口，生成评测数据并写入Excel。
数据流与流式接口完全一致：基础数据从 type=data 事件提取，LLM 分析从 content 提取。

使用方式:
    # 单条测试
    python bazi_evaluator.py --input /path/to/10.xlsx --row 2

    # 批量测试
    python bazi_evaluator.py --input /path/to/10.xlsx

    # 显示详细进度
    python bazi_evaluator.py --input /path/to/10.xlsx --verbose
"""

import sys
import os
import asyncio
import argparse
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from scripts.evaluation.config import EvaluationConfig, DEFAULT_CONFIG
from scripts.evaluation.excel_handler import ExcelHandler, TestCase
from scripts.evaluation.api_client import BaziApiClient, StreamResponse


class BaziEvaluator:
    """八字评测器 - 批量调用流式接口"""

    def __init__(self, config: EvaluationConfig = None, verbose: bool = False):
        self.config = config or DEFAULT_CONFIG
        self.verbose = verbose
        self.api_client = BaziApiClient(self.config)

    def _log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def _log_progress(self, message: str):
        if self.verbose:
            self._log(message, "PROGRESS")

    def _extract_basic_data_from_streams(
        self,
        wuxing_resp: Any,
        xishen_resp: Any,
        fortune_resp: Any = None,
        day_pillar_from_excel: str = "",
    ) -> Dict[str, str]:
        """
        从流式接口的 type=data 事件中提取排盘基础数据。
        数据源头与流式接口完全一致（wuxing_proportion + xishen_jishen 的 SSE data 事件）。
        大运流年优先从 fortune/display 接口获取（完整 8+ 大运），失败时回退到 _key_dayuns。

        Args:
            wuxing_resp: wuxing_proportion/stream 的 StreamResponse（含 .data）
            xishen_resp: xishen_jishen/stream 的 StreamResponse（含 .data）
            fortune_resp: fortune/display 的 JSON 响应（含 dayun.list，可选）
            day_pillar_from_excel: 若 Excel 八字列解析出日柱，优先使用
        """
        result = {
            "day_stem": "",
            "wuxing": "",
            "shishen": "",
            "xi_ji": "",
            "wangshuai": "",
            "geju": "",
            "dayun_liunian": "",
        }

        # 解析 wuxing_proportion 的 type=data 内容
        wuxing_data = {}
        if isinstance(wuxing_resp, StreamResponse) and wuxing_resp.data:
            payload = wuxing_resp.data
            if isinstance(payload, dict) and payload.get("success"):
                wuxing_data = payload.get("data", {}) or {}

        # 解析 xishen_jishen 的 type=data 内容
        xishen_data = {}
        if isinstance(xishen_resp, StreamResponse) and xishen_resp.data:
            payload = xishen_resp.data
            if isinstance(payload, dict) and payload.get("success"):
                xishen_data = payload.get("data", {}) or {}

        # 日柱：bazi_pillars.day
        if day_pillar_from_excel:
            result["day_stem"] = day_pillar_from_excel
        else:
            pillars = wuxing_data.get("bazi_pillars") or wuxing_data.get("_bazi_pillars") or {}
            day_pillar = pillars.get("day", {})
            if isinstance(day_pillar, dict):
                stem = day_pillar.get("stem", "")
                branch = day_pillar.get("branch", "")
                result["day_stem"] = f"{stem}{branch}" if stem and branch else stem or ""

        # 五行：proportions
        proportions = wuxing_data.get("proportions", {})
        if proportions:
            sorted_elements = sorted(
                proportions.items(),
                key=lambda x: (x[1] or {}).get("percentage", 0) if isinstance(x[1], dict) else 0,
                reverse=True,
            )
            wuxing_parts = []
            for element, info in sorted_elements:
                if isinstance(info, dict):
                    pct = info.get("percentage", 0)
                    details = "".join(info.get("details", []))
                    wuxing_parts.append(f"{element}{pct}%({details})")
            result["wuxing"] = "、".join(wuxing_parts)

        # 十神：ten_gods 或 _details
        ten_gods = wuxing_data.get("ten_gods", {})
        details = wuxing_data.get("_details", {})
        pillar_map = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
        pillar_order = ["year", "month", "day", "hour"]
        shishen_parts = []

        for pillar_type in pillar_order:
            pillar_detail = ten_gods.get(pillar_type) or details.get(pillar_type, {})
            if isinstance(pillar_detail, dict):
                main_star = pillar_detail.get("main_star", "")
                hidden_stars = pillar_detail.get("hidden_stars", []) or pillar_detail.get("sub_stars", [])
                pillar_name = pillar_map.get(pillar_type, pillar_type)
                if main_star or hidden_stars:
                    parts = []
                    if main_star:
                        parts.append(f"主星-{main_star}")
                    if hidden_stars:
                        parts.append(f"副星-{'/'.join(hidden_stars)}")
                    shishen_parts.append(f"{pillar_name}: {', '.join(parts)}")

        if shishen_parts:
            result["shishen"] = "\n".join(shishen_parts)

        # 喜忌：wangshuai.final_xi_ji（优先）或 xishen_data
        wangshuai_block = wuxing_data.get("wangshuai", {})
        if isinstance(wangshuai_block, dict):
            final_xi_ji = wangshuai_block.get("final_xi_ji", {})
            if final_xi_ji and final_xi_ji.get("xi_shen_elements"):
                xi_elements = final_xi_ji.get("xi_shen_elements", [])
                ji_elements = final_xi_ji.get("ji_shen_elements", [])
            else:
                xi_elements = wangshuai_block.get("xi_shen_elements", [])
                ji_elements = wangshuai_block.get("ji_shen_elements", [])
        else:
            xi_elements = xishen_data.get("xi_shen_elements", [])
            ji_elements = xishen_data.get("ji_shen_elements", [])

        def _element_names(lst):
            return [x.get("name", x) if isinstance(x, dict) else x for x in (lst or [])]

        xi_names = _element_names(xi_elements)
        ji_names = _element_names(ji_elements)
        xi_str = "、".join(xi_names) if xi_names else "无"
        ji_str = "、".join(ji_names) if ji_names else "无"
        result["xi_ji"] = f"喜：{xi_str}；忌：{ji_str}"

        # 旺衰
        wangshuai_value = ""
        total_score = 0
        if isinstance(wangshuai_block, dict):
            wangshuai_value = wangshuai_block.get("wangshuai", "")
            total_score = wangshuai_block.get("total_score", 0)
        if not wangshuai_value and xishen_data:
            wangshuai_value = xishen_data.get("wangshuai", "")
            total_score = xishen_data.get("total_score", 0)

        wangshuai_full = f"{wangshuai_value}({total_score}分)"
        if xi_str != "无" or ji_str != "无":
            wangshuai_full += f"，喜用五行：{xi_str}，忌讳五行：{ji_str}"
        tiaohou = wangshuai_block.get("tiaohou", {}) if isinstance(wangshuai_block, dict) else {}
        if isinstance(tiaohou, dict) and tiaohou.get("description"):
            wangshuai_full += f" | 调候：{tiaohou.get('description', '')}"
        result["wangshuai"] = wangshuai_full

        # 格局：xishen_data.shishen_mingge
        shishen_mingge = xishen_data.get("shishen_mingge", [])
        if shishen_mingge:
            geju_names = [mg.get("name", "") for mg in shishen_mingge[:3] if isinstance(mg, dict) and mg.get("name")]
            result["geju"] = "、".join(geju_names) if geju_names else ""

        # 大运流年：优先 fortune/display（完整 8+ 大运），失败时回退 _key_dayuns
        dayun_parts = []

        def _normalize_stem_branch(dy):
            """兼容 fortune/display（stem/branch 为 dict）与 _key_dayuns（直接字符串）"""
            stem = dy.get("stem", "")
            branch = dy.get("branch", "")
            if isinstance(stem, dict):
                stem = stem.get("char", "")
            if isinstance(branch, dict):
                branch = branch.get("char", "")
            if not stem and not branch:
                ganzhi = dy.get("ganzhi", "")
                if isinstance(ganzhi, str) and len(ganzhi) >= 2:
                    stem, branch = ganzhi[0], ganzhi[1]
            return stem, branch

        def _format_liunian(ln):
            """格式化单个流年：年:干支(主星) 或 年:干支"""
            if not isinstance(ln, dict):
                return ""
            y = ln.get("year", "")
            g = ln.get("ganzhi", "") or f"{ln.get('stem','')}{ln.get('branch','')}"
            ms = ln.get("main_star", "")
            return f"{y}:{g}({ms})" if ms else f"{y}:{g}"

        def _format_dayun(dy):
            if not isinstance(dy, dict):
                return ""
            stem, branch = _normalize_stem_branch(dy)
            if not stem and not branch:
                return ""
            gz = f"{stem}{branch}" if stem and branch else stem or branch
            main_star = dy.get("main_star", "")
            age_range = dy.get("age_range", {}) or {}
            start = age_range.get("start", dy.get("start_age", ""))
            end = age_range.get("end", dy.get("end_age", ""))
            s = gz
            if main_star:
                s += f"({main_star})"
            if start and end:
                s += f" [{start}-{end}岁]"
            liunians = dy.get("liunian_sequence", []) or dy.get("liunians", [])
            if not liunians:
                # 回退 liunian_simple（仅 year+ganzhi）
                simple = dy.get("liunian_simple", []) or []
                liunians = [{"year": x.get("year"), "ganzhi": x.get("ganzhi", "")} for x in simple if isinstance(x, dict)]
            if liunians:
                ln_parts = [_format_liunian(ln) for ln in liunians[:10] if _format_liunian(ln)]
                if ln_parts:
                    s += " 流年:" + ", ".join(ln_parts)
            return s

        # 1. 优先从 fortune/display 提取
        if isinstance(fortune_resp, dict) and fortune_resp.get("success"):
            dayun_list = (fortune_resp.get("dayun") or {}).get("list", []) or []
            for dy in dayun_list:
                if dy.get("is_xiaoyun"):
                    continue
                part = _format_dayun(dy)
                if part:
                    dayun_parts.append(part)

        # 2. 回退到 wuxing 的 _key_dayuns
        if not dayun_parts:
            key_dayuns = wuxing_data.get("_key_dayuns", []) or []
            current_dayun = wuxing_data.get("_current_dayun", {}) or {}
            if key_dayuns:
                for dy in key_dayuns[:8]:
                    part = _format_dayun(dy)
                    if part:
                        dayun_parts.append(part)
            elif current_dayun:
                part = _format_dayun(current_dayun)
                if part:
                    dayun_parts.append(part)

        result["dayun_liunian"] = "\n".join(dayun_parts) if dayun_parts else ""

        return result

    def _format_stream_content(self, resp: Any) -> str:
        """从 StreamResponse 或异常提取 content"""
        if isinstance(resp, Exception):
            return f"[异常] {resp}"
        if isinstance(resp, StreamResponse):
            if resp.error:
                return f"[错误] {resp.error}"
            return resp.content or ""
        return ""

    def _format_rizhu(self, resp: Any) -> str:
        """从 rizhu_liujiazi JSON 响应格式化"""
        if isinstance(resp, Exception):
            return f"[异常] {resp}"
        if not isinstance(resp, dict):
            return ""
        if not resp.get("success"):
            return resp.get("error", "")
        data = resp.get("data", {})
        analysis = data.get("analysis", "")
        rizhu = data.get("rizhu", "")
        return f"{rizhu}日: {analysis}" if analysis else rizhu

    async def evaluate_single(self, test_case: TestCase) -> Dict[str, Any]:
        """评测单条数据：并行调用所有流式接口，提取基础数据与 LLM 内容"""
        results = {}
        solar_date = test_case.solar_date
        solar_time = test_case.solar_time
        gender = test_case.gender

        if test_case.parse_error:
            self._log(f"跳过 {test_case.user_name}: {test_case.parse_error}", "WARN")
            return {"error": test_case.parse_error}

        self._log(f"开始评测: {test_case.user_name} ({solar_date} {solar_time} {gender})")
        start_time = time.time()

        try:
            self._log_progress("  并行调用所有接口...")

            # 单阶段：并行调用 rizhu_liujiazi + fortune_display + 9 个流式接口
            tasks = [
                self.api_client.call_rizhu_liujiazi(solar_date, solar_time, gender),
                self.api_client.call_fortune_display(solar_date, solar_time, gender),
                self.api_client.call_wuxing_proportion_stream(solar_date, solar_time, gender),
                self.api_client.call_xishen_jishen_stream(solar_date, solar_time, gender),
                self.api_client.call_career_wealth_stream(solar_date, solar_time, gender),
                self.api_client.call_marriage_analysis_stream(solar_date, solar_time, gender),
                self.api_client.call_health_stream(solar_date, solar_time, gender),
                self.api_client.call_children_study_stream(solar_date, solar_time, gender),
                self.api_client.call_general_review_stream(solar_date, solar_time, gender),
                self.api_client.call_daily_fortune_calendar_stream(solar_date, solar_time, gender),
                self.api_client.call_annual_report_stream(solar_date, solar_time, gender),
            ]

            all_responses = await asyncio.gather(*tasks, return_exceptions=True)

            rizhu_resp = all_responses[0]
            fortune_resp = all_responses[1]
            wuxing_resp = all_responses[2]
            xishen_resp = all_responses[3]

            # 基础数据：从 wuxing_proportion + xishen_jishen 的 type=data 提取，大运流年优先从 fortune_display
            results["basic"] = self._extract_basic_data_from_streams(
                wuxing_resp=wuxing_resp,
                xishen_resp=xishen_resp,
                fortune_resp=fortune_resp,
                day_pillar_from_excel=test_case.day_pillar or "",
            )

            # 日元六十甲子
            results["rizhu_liujiazi"] = self._format_rizhu(rizhu_resp)

            # LLM 分析：从各 stream 的 content 提取
            stream_keys = [
                "wuxing_analysis",
                "xishen_jishen",
                "career_wealth",
                "marriage",
                "health",
                "children_study",
                "general_review",
                "daily_fortune",
                "annual_report",
            ]
            for i, key in enumerate(stream_keys):
                results[key] = self._format_stream_content(all_responses[i + 2])

            total_time = time.time() - start_time
            self._log(f"完成评测: {test_case.user_name} (总耗时: {total_time:.1f}秒)")

        except Exception as e:
            self._log(f"评测失败 {test_case.user_name}: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            results["error"] = str(e)

        return results

    async def evaluate_batch(
        self,
        test_cases: List[TestCase],
        progress_callback=None,
        max_concurrency: int = 3,
    ) -> List[tuple]:
        """批量评测"""
        total = len(test_cases)
        self._log(f"开始批量评测，共 {total} 条数据，并发数: {max_concurrency}")

        semaphore = asyncio.Semaphore(max_concurrency)
        completed_count = 0

        async def evaluate_with_semaphore(idx: int, tc: TestCase):
            nonlocal completed_count
            async with semaphore:
                result = await self.evaluate_single(tc)
                completed_count += 1
                self._log(f"进度: {completed_count}/{total} 完成")
                if progress_callback:
                    progress_callback(completed_count, total, tc, result)
                return idx, tc, result

        tasks = [evaluate_with_semaphore(i, tc) for i, tc in enumerate(test_cases)]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for item in batch_results:
            if isinstance(item, Exception):
                self._log(f"批量任务异常: {item}", "ERROR")
                continue
            results.append((item[1], item[2]))

        self._log(f"批量评测完成，共处理 {len(results)}/{total} 条数据")
        return results

    async def close(self):
        await self.api_client.close()


async def main():
    parser = argparse.ArgumentParser(
        description="八字评测工具 - 批量调用流式接口生成评测数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python bazi_evaluator.py --input /path/to/10.xlsx --row 2   # 单条
  python bazi_evaluator.py --input /path/to/10.xlsx           # 批量
  python bazi_evaluator.py --input /path/to/10.xlsx --verbose # 详细进度
        """,
    )
    parser.add_argument("--input", "-i", required=True, help="输入Excel文件路径")
    parser.add_argument("--row", "-r", type=int, help="只处理指定数据行（从1开始）")
    parser.add_argument("--concurrency", "-c", type=int, default=3, help="批量处理并发数（默认: 3）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细进度")
    parser.add_argument("--base-url", help="API服务地址")

    args = parser.parse_args()

    config = EvaluationConfig()
    if args.base_url:
        config.base_url = args.base_url

    evaluator = BaziEvaluator(config=config, verbose=args.verbose)

    try:
        print(f"打开Excel文件: {args.input}")
        with ExcelHandler(args.input) as excel:
            if args.row:
                test_cases = excel.read_test_cases(data_row_start=args.row, data_row_end=args.row)
            else:
                test_cases = excel.read_test_cases()

            if not test_cases:
                print("未找到有效的测试数据")
                return

            print(f"读取到 {len(test_cases)} 条测试数据")

            results = await evaluator.evaluate_batch(test_cases, max_concurrency=args.concurrency)

            print("写入评测结果...")
            for test_case, result in results:
                if "error" not in result or result.get("basic"):
                    excel.write_result(test_case, result)

            excel.save()
            print(f"评测完成，结果已保存到: {args.input}")

    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"评测过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await evaluator.close()


if __name__ == "__main__":
    asyncio.run(main())

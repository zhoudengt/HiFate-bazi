#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口首个 Token 时间（TTFT）测试脚本

测试所有流式接口，测量从请求发出到收到首个 SSE data 行的时间（Time To First Token），
并生成 Markdown 报告。

用法:
  python scripts/evaluation/stream_ttft_report.py [--base-url URL] [--output FILE] [--runs N]
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# 使用 requests 以便同步测量 TTFT（无需 asyncio）
import requests

# 默认测试参数（八字类接口通用）
DEFAULT_SOLAR_DATE = "1990-01-15"
DEFAULT_SOLAR_TIME = "12:00"
DEFAULT_GENDER = "male"
DEFAULT_CALENDAR_TYPE = "solar"


@dataclass
class StreamEndpoint:
    """流式接口定义"""
    name: str
    path: str  # 不含 base_url，如 /api/v1/general-review/stream
    method: str  # POST | GET
    payload_builder: Optional[Callable[[], Dict[str, Any]]] = None  # 用于 POST
    params_builder: Optional[Callable[[], Dict[str, Any]]] = None   # 用于 GET
    skip_reason: Optional[str] = None  # 若需跳过（如需上传图片）


def _bazi_payload() -> Dict[str, Any]:
    return {
        "solar_date": DEFAULT_SOLAR_DATE,
        "solar_time": DEFAULT_SOLAR_TIME,
        "gender": DEFAULT_GENDER,
        "calendar_type": DEFAULT_CALENDAR_TYPE,
    }


def _daily_fortune_payload() -> Dict[str, Any]:
    return {
        "date": None,  # 默认今天
        "solar_date": DEFAULT_SOLAR_DATE,
        "solar_time": DEFAULT_SOLAR_TIME,
        "gender": DEFAULT_GENDER,
    }


def _annual_report_payload() -> Dict[str, Any]:
    return {
        "solar_date": DEFAULT_SOLAR_DATE,
        "solar_time": DEFAULT_SOLAR_TIME,
        "gender": DEFAULT_GENDER,
    }


def _smart_analyze_params() -> Dict[str, Any]:
    # GET 接口，通过 query 传参（场景1：选择项）
    return {
        "year": 1990,
        "month": 1,
        "day": 15,
        "hour": 12,
        "gender": DEFAULT_GENDER,
        "category": "事业财富",
        "user_id": "ttft_test",
    }


def _action_suggestions_payload() -> Dict[str, Any]:
    # 行动建议接口需要 yi/ji 列表（宜/忌），通常由每日运势日历接口返回后调用
    return {
        "yi": ["解除", "扫舍", "馀事勿取"],
        "ji": ["诸事不宜"],
    }


# 所有流式接口定义（不含需要上传图片的接口）
STREAM_ENDPOINTS: List[StreamEndpoint] = [
    StreamEndpoint(
        name="总评分析",
        path="/api/v1/general-review/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="事业财富",
        path="/api/v1/career-wealth/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="感情婚姻",
        path="/api/v1/bazi/marriage-analysis/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="健康分析",
        path="/api/v1/health/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="子女学习",
        path="/api/v1/children-study/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="五行占比",
        path="/api/v1/bazi/wuxing-proportion/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="喜神忌神",
        path="/api/v1/bazi/xishen-jishen/stream",
        method="POST",
        payload_builder=_bazi_payload,
    ),
    StreamEndpoint(
        name="每日运势日历",
        path="/api/v1/daily-fortune-calendar/stream",
        method="POST",
        payload_builder=_daily_fortune_payload,
    ),
    StreamEndpoint(
        name="行动建议流式",
        path="/api/v1/daily-fortune-calendar/action-suggestions/stream",
        method="POST",
        payload_builder=_action_suggestions_payload,
    ),
    StreamEndpoint(
        name="年运报告",
        path="/api/v1/annual-report/stream",
        method="POST",
        payload_builder=_annual_report_payload,
    ),
    StreamEndpoint(
        name="智能分析流",
        path="/api/v1/smart-fortune/smart-analyze-stream",
        method="GET",
        params_builder=_smart_analyze_params,
    ),
    # 以下需要上传图片，默认不测；若提供 --with-image 可传入测试图片路径
    StreamEndpoint(
        name="办公桌风水(需图片)",
        path="/api/v2/desk-fengshui/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
    StreamEndpoint(
        name="面相分析V2(需图片)",
        path="/api/v2/face/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
    StreamEndpoint(
        name="手相分析(需图片)",
        path="/api/v1/fortune/hand/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
    StreamEndpoint(
        name="面相分析(需图片)",
        path="/api/v1/fortune/face/analyze/stream",
        method="POST",
        skip_reason="需要上传图片",
    ),
]


def measure_ttft(
    base_url: str,
    endpoint: StreamEndpoint,
    timeout: int = 120,
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    测量单个流式接口的首个 Token 时间（TTFT）。

    Returns:
        (ttft_seconds, first_line_type, error_message)
        ttft_seconds: 从请求发出到收到第一条 data 行的时间（秒），失败为 None
        first_line_type: 首条 data 的 type（如 data/progress/complete/error）
        error_message: 若失败则为错误信息
    """
    url = base_url.rstrip("/") + endpoint.path
    headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}

    if endpoint.skip_reason:
        return None, None, endpoint.skip_reason

    try:
        start = time.perf_counter()
        if endpoint.method == "GET":
            params = endpoint.params_builder() if endpoint.params_builder else {}
            resp = requests.get(
                url,
                headers=headers,
                params=params,
                stream=True,
                timeout=(10, timeout),
            )
        else:
            payload = endpoint.payload_builder() if endpoint.payload_builder else {}
            # 移除 None 键以便服务端使用默认值
            payload = {k: v for k, v in payload.items() if v is not None}
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(10, timeout),
            )

        try:
            resp.raise_for_status()
            first_line_type = None
            buffer = b""
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                buffer += chunk
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    try:
                        line = line_bytes.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        continue
                    if not line or not line.startswith("data:"):
                        continue
                    json_str = line[5:].strip()
                    if not json_str:
                        continue
                    try:
                        msg = json.loads(json_str)
                        first_line_type = msg.get("type", "")
                        ttft = time.perf_counter() - start
                        return round(ttft, 3), first_line_type, None
                    except json.JSONDecodeError:
                        continue
            return None, None, "流结束未收到任何 data 行"
        finally:
            resp.close()
    except requests.exceptions.Timeout as e:
        return None, None, f"超时: {e}"
    except requests.exceptions.RequestException as e:
        return None, None, f"请求失败: {e}"
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def run_ttft(
    base_url: str,
    runs: int = 1,
    timeout: int = 120,
    skip_image: bool = True,
) -> List[Dict[str, Any]]:
    """对每个接口执行 runs 次 TTFT 测量，返回结果列表。"""
    results = []
    for ep in STREAM_ENDPOINTS:
        if skip_image and ep.skip_reason:
            results.append({
                "name": ep.name,
                "path": ep.path,
                "method": ep.method,
                "skip": True,
                "skip_reason": ep.skip_reason,
                "ttft_sec": None,
                "first_type": None,
                "error": None,
                "runs": [],
            })
            continue
        ttft_list = []
        last_first_type = None
        last_error = None
        for i in range(runs):
            ttft, first_type, err = measure_ttft(base_url, ep, timeout=timeout)
            if ttft is not None:
                ttft_list.append(ttft)
                last_first_type = first_type
            else:
                last_error = err
        avg_ttft = round(sum(ttft_list) / len(ttft_list), 3) if ttft_list else None
        results.append({
            "name": ep.name,
            "path": ep.path,
            "method": ep.method,
            "skip": False,
            "skip_reason": None,
            "ttft_sec": avg_ttft,
            "first_type": last_first_type,
            "error": last_error if not ttft_list else None,
            "runs": ttft_list,
        })
    return results


def to_markdown_report(results: List[Dict[str, Any]], base_url: str) -> str:
    """生成 Markdown 格式的首个 Token 时间报告。"""
    lines = [
        "# 流式接口首个 Token 时间（TTFT）报告",
        "",
        f"**基准 URL**: `{base_url}`",
        f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. 汇总表",
        "",
        "| 接口名称 | 路径 | 方法 | TTFT(秒) | 首条类型 | 备注 |",
        "|----------|------|------|----------|----------|------|",
    ]
    for r in results:
        if r["skip"]:
            lines.append(
                f"| {r['name']} | `{r['path']}` | {r['method']} | - | - | {r['skip_reason']} |"
            )
        else:
            ttft_str = str(r["ttft_sec"]) if r["ttft_sec"] is not None else "-"
            first_type = r["first_type"] or "-"
            note = r["error"] if r["error"] else ""
            if r.get("runs") and len(r["runs"]) > 1:
                note = f"共 {len(r['runs'])} 次, 取值平均"
            lines.append(
                f"| {r['name']} | `{r['path']}` | {r['method']} | {ttft_str} | {first_type} | {note} |"
            )
    lines.extend([
        "",
        "## 2. 说明",
        "",
        "- **TTFT**: 从请求发出到收到第一条 SSE `data:` 行的时间（秒）。",
        "- **首条类型**: 第一条 data 的 `type` 字段（如 `data`/`progress`/`complete`/`error`）。",
        "- 需要上传图片的接口未参与本次测试，可在脚本中配置测试图片后重跑。",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="流式接口首个 Token 时间（TTFT）测试并生成报告"
    )
    parser.add_argument(
        "--base-url",
        default="http://8.210.52.217:8001",
        help="API 基准 URL（默认: http://8.210.52.217:8001）",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="报告输出文件路径（默认: 打印到 stdout）",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="每个接口测试次数，多次时取平均（默认: 1）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="单次请求流式超时秒数（默认: 120）",
    )
    parser.add_argument(
        "--with-image",
        action="store_true",
        help="包含需要上传图片的接口（需在脚本内配置图片路径）",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = run_ttft(
        base_url,
        runs=args.runs,
        timeout=args.timeout,
        skip_image=not args.with_image,
    )
    report = to_markdown_report(results, base_url)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已写入: {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    # 修复 GET 请求：当前脚本里 GET 用了 requests.get 但参数传错了
    sys.exit(main())

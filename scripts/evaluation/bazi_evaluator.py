#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字评测主脚本

批量调用API接口，生成评测数据并写入Excel。
独立运行，不影响现有系统功能。

支持 Coze 和 百炼 双平台对比评测。

使用方式:
    # 单条测试
    python bazi_evaluator.py --input /path/to/10.xlsx --row 2
    
    # 批量测试
    python bazi_evaluator.py --input /path/to/10.xlsx
    
    # 显示详细进度
    python bazi_evaluator.py --input /path/to/10.xlsx --verbose
    
    # 使用百炼平台
    python bazi_evaluator.py --input /path/to/10.xlsx --platform bailian
    
    # 双平台对比评测
    python bazi_evaluator.py --input /path/to/10.xlsx --platform both
"""

import sys
import os
import asyncio
import argparse
import random
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from scripts.evaluation.config import EvaluationConfig, DEFAULT_CONFIG
from scripts.evaluation.data_parser import DataParser
from scripts.evaluation.excel_handler import ExcelHandler, TestCase
from scripts.evaluation.api_client import BaziApiClient

# 百炼平台客户端（可选导入）
try:
    from scripts.evaluation.bailian import BailianClient, BailianConfig
    BAILIAN_AVAILABLE = True
except ImportError:
    BAILIAN_AVAILABLE = False
    BailianClient = None
    BailianConfig = None


class BaziEvaluator:
    """八字评测器"""
    
    def __init__(self, config: EvaluationConfig = None, verbose: bool = False):
        """
        初始化评测器
        
        Args:
            config: 评测配置
            verbose: 是否显示详细进度
        """
        self.config = config or DEFAULT_CONFIG
        self.verbose = verbose
        
        # Coze 平台客户端（通过后端代理）
        self.api_client = BaziApiClient(self.config)
        
        # 百炼平台客户端（可选）
        self.bailian_client = None
        if self.config.use_bailian:
            if not BAILIAN_AVAILABLE:
                raise ImportError("百炼平台模块不可用，请确保已安装 dashscope SDK: pip install dashscope")
            
            bailian_config = BailianConfig(api_key=self.config.bailian_api_key)
            self.bailian_client = BailianClient(bailian_config)
            self._log("百炼平台客户端已初始化")
    
    def _log(self, message: str, level: str = "INFO"):
        """输出日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def _log_progress(self, message: str):
        """输出进度信息（仅verbose模式）"""
        if self.verbose:
            self._log(message, "PROGRESS")
    
    def _format_basic_data_from_unified(self, unified_data: Dict[str, Any]) -> Dict[str, str]:
        """
        从统一接口 /bazi/data 返回的数据中提取基础八字数据
        
        Args:
            unified_data: /bazi/data 接口返回的数据
            
        Returns:
            格式化后的基础数据字典
        """
        result = {
            'day_stem': '',
            'wuxing': '',
            'shishen': '',
            'xi_ji': '',
            'wangshuai': '',
            'geju': '',
            'dayun_liunian': ''
        }
        
        if not unified_data or not unified_data.get('success'):
            return result
        
        data = unified_data.get('data', {})
        
        # 从 bazi 模块获取基础数据
        bazi_data = data.get('bazi', {}).get('bazi', {})
        
        # 日柱（完整：日干+日支）
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = bazi_pillars.get('day', {})
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        result['day_stem'] = f"{day_stem}{day_branch}" if day_stem and day_branch else day_stem
        
        # 五行
        element_counts = bazi_data.get('element_counts', {})
        if element_counts:
            wuxing_parts = []
            for element in ['金', '木', '水', '火', '土']:
                count = element_counts.get(element, 0)
                wuxing_parts.append(f"{element}{count}")
            result['wuxing'] = ' '.join(wuxing_parts)
        
        # 十神（按四柱分组显示每柱的主星+副星）
        # 优先从 details 中获取每个柱的主星和副星
        details = data.get('bazi', {}).get('details', {})
        if not details:
            # 如果 bazi.details 不存在，尝试从顶层获取
            details = bazi_data.get('details', {})
        
        pillar_map = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
        pillar_order = ['year', 'month', 'day', 'hour']
        
        shishen_parts = []
        for pillar_type in pillar_order:
            pillar_detail = details.get(pillar_type, {})
            if isinstance(pillar_detail, dict):
                main_star = pillar_detail.get('main_star', '')
                # hidden_stars 是副星列表
                hidden_stars = pillar_detail.get('hidden_stars', [])
                if not hidden_stars:
                    hidden_stars = pillar_detail.get('sub_stars', [])
                
                pillar_name = pillar_map.get(pillar_type, pillar_type)
                
                if main_star or hidden_stars:
                    # 格式：年柱: 主星-食神, 副星-七杀/比肩/偏印
                    parts = []
                    if main_star:
                        parts.append(f"主星-{main_star}")
                    if hidden_stars:
                        parts.append(f"副星-{'/'.join(hidden_stars)}")
                    shishen_parts.append(f"{pillar_name}: {', '.join(parts)}")
        
        if shishen_parts:
            result['shishen'] = '\n'.join(shishen_parts)
        else:
            # 如果 details 中没有数据，使用原有的 ten_gods_stats 方式（兼容）
            ten_gods_stats = bazi_data.get('ten_gods_stats', {})
            if ten_gods_stats:
                main_gods = ten_gods_stats.get('main', {})
                main_parts = []
                for god, info in main_gods.items():
                    if god not in ['元男', '元女'] and isinstance(info, dict):
                        pillars = info.get('pillars', {})
                        pillar_names = []
                        for p, count in pillars.items():
                            if count > 0:
                                pillar_names.append({'year': '年', 'month': '月', 'day': '日', 'hour': '时'}.get(p, p))
                        if pillar_names:
                            main_parts.append(f"{god}({','.join(pillar_names)})")
                
                branch_gods = ten_gods_stats.get('branch', {})
                branch_parts = []
                for god, info in branch_gods.items():
                    if god not in ['元男', '元女'] and isinstance(info, dict):
                        count = info.get('count', 0)
                        if count > 0:
                            branch_parts.append(f"{god}x{count}")
                
                shishen_str = "主星: " + '、'.join(main_parts) if main_parts else ""
                if branch_parts:
                    shishen_str += " | 副星: " + '、'.join(branch_parts)
                result['shishen'] = shishen_str
        
        # 旺衰数据（从 wangshuai 模块获取，注意嵌套结构：{success, data: {...}}）
        wangshuai_outer = data.get('wangshuai', {})
        wangshuai_data = wangshuai_outer.get('data', wangshuai_outer) if isinstance(wangshuai_outer, dict) else {}
        
        # 喜忌
        xi_elements = wangshuai_data.get('xi_shen_elements', [])
        ji_elements = wangshuai_data.get('ji_shen_elements', [])
        if xi_elements or ji_elements:
            xi_str = '、'.join(xi_elements) if xi_elements else '无'
            ji_str = '、'.join(ji_elements) if ji_elements else '无'
            result['xi_ji'] = f"喜：{xi_str}；忌：{ji_str}"
        
        # 旺衰（详细格式）
        wangshuai_value = wangshuai_data.get('wangshuai', '')
        xi_str = '、'.join(xi_elements) if xi_elements else '无'
        ji_str = '、'.join(ji_elements) if ji_elements else '无'
        element_scores = wangshuai_data.get('element_scores', {})
        scores_str = ''
        if element_scores:
            scores_parts = [f"{k}:{v}" for k, v in element_scores.items()]
            scores_str = ', '.join(scores_parts)
        
        wangshuai_full = f"日主{wangshuai_value}"
        if xi_str != '无' or ji_str != '无':
            wangshuai_full += f" | 喜神：{xi_str} | 忌神：{ji_str}"
        if scores_str:
            wangshuai_full += f" | 五行得分：{scores_str}"
        result['wangshuai'] = wangshuai_full
        
        # 格局（从 xishen_jishen 模块中的十神命格获取）
        xishen_outer = data.get('xishen_jishen', {})
        xishen_data = xishen_outer.get('data', {}) if isinstance(xishen_outer, dict) else {}
        shishen_mingge = xishen_data.get('shishen_mingge', [])
        if shishen_mingge:
            geju_names = [mg.get('name', '') for mg in shishen_mingge[:3] if isinstance(mg, dict) and mg.get('name')]
            result['geju'] = '、'.join(geju_names) if geju_names else ''
        
        # 大运流年（8步大运 + 每步大运下的所有流年）
        dayun_data = data.get('dayun', [])
        if dayun_data and isinstance(dayun_data, list):
            dayun_parts = []
            for dy in dayun_data[:8]:  # 取前8步大运
                if isinstance(dy, dict):
                    stem = dy.get('stem', '')
                    branch = dy.get('branch', '')
                    main_star = dy.get('main_star', '')
                    age_range = dy.get('age_range', {})
                    start_age = age_range.get('start', dy.get('start_age', ''))
                    end_age = age_range.get('end', dy.get('end_age', ''))
                    
                    if stem and branch:
                        # 大运基础信息
                        dy_str = f"{stem}{branch}"
                        if main_star:
                            dy_str += f"({main_star})"
                        if start_age and end_age:
                            dy_str += f" [{start_age}-{end_age}岁]"
                        
                        # 该大运下的流年
                        liunian_seq = dy.get('liunian_sequence', [])
                        if liunian_seq:
                            ln_parts = []
                            for ln in liunian_seq:
                                if isinstance(ln, dict):
                                    ln_year = ln.get('year', '')
                                    ln_stem = ln.get('stem', '')
                                    ln_branch = ln.get('branch', '')
                                    ln_star = ln.get('main_star', '')
                                    if ln_year and ln_stem and ln_branch:
                                        ln_str = f"{ln_year}:{ln_stem}{ln_branch}"
                                        if ln_star:
                                            ln_str += f"({ln_star})"
                                        ln_parts.append(ln_str)
                            if ln_parts:
                                dy_str += " 流年:" + ', '.join(ln_parts)
                        
                        dayun_parts.append(dy_str)
            
            result['dayun_liunian'] = '\n'.join(dayun_parts) if dayun_parts else ''
        
        return result
    
    def _build_bailian_prompt(self, test_case: TestCase, scene: str, basic_data: Dict[str, Any] = None) -> str:
        """
        构建发送给百炼智能体的 prompt
        
        Args:
            test_case: 测试用例
            scene: 场景名称
            basic_data: 基础八字数据（可选）
            
        Returns:
            格式化的 prompt
        """
        gender_text = "男" if test_case.gender == "male" else "女"
        
        # 基础信息
        prompt_parts = [
            f"请分析以下八字的{scene}：",
            "",
            "八字信息：",
            f"- 出生日期：{test_case.solar_date} {test_case.solar_time}",
            f"- 性别：{gender_text}",
        ]
        
        # 添加八字信息
        if test_case.bazi_text and test_case.bazi_text != "nan":
            prompt_parts.append(f"- 八字：{test_case.bazi_text}")
        
        if test_case.day_pillar:
            prompt_parts.append(f"- 日柱：{test_case.day_pillar}")
        
        # 添加基础数据（如果有）
        if basic_data:
            if basic_data.get('wuxing'):
                prompt_parts.append(f"- 五行：{basic_data['wuxing']}")
            if basic_data.get('xi_ji'):
                prompt_parts.append(f"- 喜忌：{basic_data['xi_ji']}")
            if basic_data.get('wangshuai'):
                prompt_parts.append(f"- 旺衰：{basic_data['wangshuai']}")
        
        prompt_parts.append("")
        prompt_parts.append(f"请给出详细的{scene}分析。")
        
        return "\n".join(prompt_parts)
    
    async def _call_bailian_stream_and_collect(self, app_id: str, prompt: str) -> str:
        """
        调用百炼流式接口并收集完整结果
        
        Args:
            app_id: 智能体应用 ID
            prompt: 提示词
            
        Returns:
            完整的响应内容
        """
        content_parts = []
        error = None
        
        try:
            async for chunk in self.bailian_client.call_stream(app_id, prompt):
                chunk_type = chunk.get('type', '')
                chunk_content = chunk.get('content', '')
                
                if chunk_type == 'error':
                    error = chunk_content
                    break
                elif chunk_type == 'progress':
                    content_parts.append(chunk_content)
                elif chunk_type == 'complete':
                    if chunk_content:
                        content_parts.append(chunk_content)
        except Exception as e:
            error = str(e)
        
        if error:
            return f"[百炼错误] {error}"
        
        return ''.join(content_parts)
    
    async def evaluate_single(self, test_case: TestCase) -> Dict[str, Any]:
        """
        评测单条数据（并行执行所有API调用以提高性能）
        
        支持 Coze 和 百炼 双平台对比评测。
        
        Args:
            test_case: 测试用例
            
        Returns:
            评测结果字典
        """
        results = {}
        solar_date = test_case.solar_date
        solar_time = test_case.solar_time
        gender = test_case.gender
        
        # 检查解析错误
        if test_case.parse_error:
            self._log(f"跳过 {test_case.user_name}: {test_case.parse_error}", "WARN")
            return {'error': test_case.parse_error}
        
        platform_info = f"平台: {self.config.platform}"
        self._log(f"开始评测: {test_case.user_name} ({solar_date} {solar_time} {gender}) [{platform_info}]")
        start_time = time.time()
        
        try:
            # ==================== 阶段1：并行调用 Coze API ====================
            coze_results = [None] * 10  # Coze 结果占位
            
            if self.config.use_coze:
                self._log_progress("  并行调用 Coze API 接口...")
                
                # 定义 Coze API 调用任务
                coze_tasks = [
                    self.api_client.call_bazi_data(solar_date, solar_time, gender),           # 0: 统一数据接口
                    self.api_client.call_rizhu_liujiazi(solar_date, solar_time, gender),      # 1: 日元-六十甲子
                    self.api_client.call_wuxing_proportion_stream(solar_date, solar_time, gender),  # 2: 五行占比
                    self.api_client.call_xishen_jishen_stream(solar_date, solar_time, gender),      # 3: 喜神忌神
                    self.api_client.call_career_wealth_stream(solar_date, solar_time, gender),      # 4: 事业财富
                    self.api_client.call_marriage_analysis_stream(solar_date, solar_time, gender),  # 5: 感情婚姻
                    self.api_client.call_health_stream(solar_date, solar_time, gender),             # 6: 身体健康
                    self.api_client.call_children_study_stream(solar_date, solar_time, gender),     # 7: 子女学习
                    self.api_client.call_general_review_stream(solar_date, solar_time, gender),     # 8: 总评
                    self.api_client.call_daily_fortune_calendar_stream(solar_date, solar_time, gender),  # 9: 每日运势
                ]
                
                coze_results = await asyncio.gather(*coze_tasks, return_exceptions=True)
                coze_time = time.time() - start_time
                self._log_progress(f"  Coze API 调用完成，耗时: {coze_time:.1f}秒")
            
            # ==================== 阶段2：处理 Coze API 返回结果 ====================
            
            # 处理统一数据接口 (index 0)
            unified_data = coze_results[0] if coze_results[0] else {}
            if isinstance(unified_data, Exception):
                self._log(f"  统一数据接口异常: {unified_data}", "WARN")
                results['basic'] = self._format_basic_data_from_unified({})
            else:
                results['basic'] = self._format_basic_data_from_unified(unified_data)
            
            # 如果从八字列解析出了日柱，使用八字列的日柱（优先级更高）
            if test_case.day_pillar:
                results['basic']['day_stem'] = test_case.day_pillar
            
            if self.config.use_coze:
                # 处理日元-六十甲子 (index 1)
                rizhu_data = coze_results[1]
                if isinstance(rizhu_data, Exception):
                    results['rizhu_liujiazi'] = f"[异常] {rizhu_data}"
                elif rizhu_data and rizhu_data.get('success'):
                    analysis = rizhu_data.get('data', {}).get('analysis', '')
                    rizhu = rizhu_data.get('data', {}).get('rizhu', '')
                    results['rizhu_liujiazi'] = f"{rizhu}日: {analysis}" if analysis else rizhu
                else:
                    results['rizhu_liujiazi'] = rizhu_data.get('error', '') if rizhu_data else ''
                
                # 处理流式分析接口结果
                stream_mapping = [
                    (2, 'wuxing_analysis', '五行占比'),
                    (3, 'xishen_jishen', '喜神忌神'),
                    (4, 'career_wealth', '事业财富'),
                    (5, 'marriage', '感情婚姻'),
                    (6, 'health', '身体健康'),
                    (7, 'children_study', '子女学习'),
                    (8, 'general_review', '总评'),
                    (9, 'daily_fortune', '每日运势'),
                ]
                
                for idx, key, name in stream_mapping:
                    resp = coze_results[idx]
                    if isinstance(resp, Exception):
                        results[key] = f"[异常] {resp}"
                        self._log(f"  {name}接口异常: {resp}", "WARN")
                    elif resp:
                        results[key] = resp.content or resp.error or ''
                    else:
                        results[key] = ''
            
            # ==================== 阶段3：并行调用百炼 API ====================
            
            if self.config.use_bailian and self.bailian_client:
                self._log_progress("  并行调用百炼 API 接口...")
                bailian_start = time.time()
                
                # 获取基础数据用于构建 prompt
                basic_data = results.get('basic', {})
                
                # 定义百炼场景映射
                bailian_scenes = [
                    ("wuxing_proportion", "bailian_wuxing_analysis", "五行解析"),
                    ("xishen_jishen", "bailian_xishen_jishen", "喜神忌神"),
                    ("career_wealth", "bailian_career_wealth", "事业财富"),
                    ("marriage", "bailian_marriage", "感情婚姻"),
                    ("health", "bailian_health", "身体健康"),
                    ("children_study", "bailian_children_study", "子女学习"),
                    ("general_review", "bailian_general_review", "总评"),
                    ("daily_fortune", "bailian_daily_fortune", "每日运势"),
                ]
                
                # 构建百炼调用任务
                async def return_not_configured(key):
                    return f"[未配置] {key} 智能体"
                
                bailian_tasks = []
                for scene_key, result_key, scene_name in bailian_scenes:
                    app_id = self.bailian_client.config.get_app_id(scene_key)
                    if app_id:
                        prompt = self._build_bailian_prompt(test_case, scene_name, basic_data)
                        bailian_tasks.append(
                            self._call_bailian_stream_and_collect(app_id, prompt)
                        )
                    else:
                        bailian_tasks.append(return_not_configured(scene_key))
                
                # 并行执行百炼调用
                bailian_results = await asyncio.gather(*bailian_tasks, return_exceptions=True)
                
                # 处理百炼结果
                for i, (scene_key, result_key, scene_name) in enumerate(bailian_scenes):
                    resp = bailian_results[i]
                    if isinstance(resp, Exception):
                        results[result_key] = f"[百炼异常] {resp}"
                        self._log(f"  百炼 {scene_name} 异常: {resp}", "WARN")
                    else:
                        results[result_key] = resp or ''
                
                bailian_time = time.time() - bailian_start
                self._log_progress(f"  百炼 API 调用完成，耗时: {bailian_time:.1f}秒")
            
            # ==================== 阶段4：AI多轮问答（仅 Coze，需要串行） ====================
            if self.config.use_coze:
                self._log_progress("  开始AI多轮问答...")
                ai_qa_start = time.time()
                ai_qa_result = await self._evaluate_ai_qa(test_case)
                results['ai_qa'] = ai_qa_result
                ai_qa_time = time.time() - ai_qa_start
                self._log_progress(f"  AI问答完成，耗时: {ai_qa_time:.1f}秒")
            
            total_time = time.time() - start_time
            self._log(f"完成评测: {test_case.user_name} (总耗时: {total_time:.1f}秒)")
            
        except Exception as e:
            self._log(f"评测失败 {test_case.user_name}: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)
        
        return results
    
    async def _evaluate_ai_qa(self, test_case: TestCase) -> Dict[str, str]:
        """
        评测AI多轮问答
        
        Args:
            test_case: 测试用例
            
        Returns:
            AI问答结果字典
        """
        result = {
            'category': '',
            'output1': '',
            'input2': '',
            'output2': '',
            'input3': '',
            'output3': ''
        }
        
        try:
            # 随机选择业务场景
            category = random.choice(self.config.ai_qa_categories)
            result['category'] = category
            
            # 提取年月日时
            year, month, day = DataParser.extract_year_month_day(test_case.solar_date)
            hour = DataParser.extract_hour(test_case.solar_time)
            
            # 生成评测用户ID
            user_id = BaziApiClient.generate_user_id()
            
            # 场景1：选择业务分类
            self._log_progress(f"    场景1: 选择 {category} ...")
            scenario1_resp = await self.api_client.call_smart_analyze_scenario1(
                year=year, month=month, day=day, hour=hour,
                gender=test_case.gender, category=category, user_id=user_id
            )
            
            if scenario1_resp.get('error'):
                result['output1'] = f"[错误] {scenario1_resp['error']}"
                return result
            
            result['output1'] = scenario1_resp.get('brief_response', '')
            preset_questions = scenario1_resp.get('preset_questions', [])
            
            # 场景2：选择预设问题
            if preset_questions:
                question2 = random.choice(preset_questions)
                if isinstance(question2, dict):
                    question2 = question2.get('question', question2.get('text', str(question2)))
                result['input2'] = question2
                
                self._log_progress(f"    场景2: 问题 '{question2[:20]}...' ...")
                scenario2_resp = await self.api_client.call_smart_analyze_scenario2(
                    category=category, question=question2, user_id=user_id
                )
                
                if scenario2_resp.get('error'):
                    result['output2'] = f"[错误] {scenario2_resp['error']}"
                else:
                    result['output2'] = scenario2_resp.get('llm_response', '')
                    related_questions = scenario2_resp.get('related_questions', [])
                    
                    # 场景3：选择相关问题
                    if related_questions:
                        question3 = random.choice(related_questions)
                        if isinstance(question3, dict):
                            question3 = question3.get('question', question3.get('text', str(question3)))
                        result['input3'] = question3
                        
                        self._log_progress(f"    场景3: 问题 '{question3[:20]}...' ...")
                        scenario3_resp = await self.api_client.call_smart_analyze_scenario2(
                            category=category, question=question3, user_id=user_id
                        )
                        
                        if scenario3_resp.get('error'):
                            result['output3'] = f"[错误] {scenario3_resp['error']}"
                        else:
                            result['output3'] = scenario3_resp.get('llm_response', '')
            
        except Exception as e:
            result['output1'] = f"[异常] {e}"
        
        return result
    
    async def evaluate_batch(self, test_cases: List[TestCase], 
                             progress_callback=None,
                             max_concurrency: int = 3) -> List[Dict[str, Any]]:
        """
        批量评测（支持用户间并行处理）
        
        Args:
            test_cases: 测试用例列表
            progress_callback: 进度回调函数
            max_concurrency: 最大并发数（同时处理的用户数），默认3
            
        Returns:
            评测结果列表
        """
        total = len(test_cases)
        self._log(f"开始批量评测，共 {total} 条数据，并发数: {max_concurrency}")
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrency)
        completed_count = 0
        results_dict = {}  # 用字典保存结果，保持顺序
        
        async def evaluate_with_semaphore(idx: int, test_case: TestCase):
            nonlocal completed_count
            async with semaphore:
                result = await self.evaluate_single(test_case)
                completed_count += 1
                self._log(f"进度: {completed_count}/{total} 完成")
                
                if progress_callback:
                    progress_callback(completed_count, total, test_case, result)
                
                return idx, test_case, result
        
        # 创建所有任务
        tasks = [
            evaluate_with_semaphore(idx, test_case) 
            for idx, test_case in enumerate(test_cases)
        ]
        
        # 并行执行所有任务
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 按原始顺序整理结果
        results = []
        for item in batch_results:
            if isinstance(item, Exception):
                self._log(f"批量任务异常: {item}", "ERROR")
                continue
            idx, test_case, result = item
            results.append((test_case, result))
        
        self._log(f"批量评测完成，共处理 {len(results)}/{total} 条数据")
        return results
    
    async def close(self):
        """关闭资源"""
        await self.api_client.close()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='八字评测工具 - 批量调用API生成评测数据（支持Coze和百炼双平台）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单条数据（第2行）
  python bazi_evaluator.py --input /path/to/10.xlsx --row 2
  
  # 批量处理所有数据
  python bazi_evaluator.py --input /path/to/10.xlsx
  
  # 显示详细进度
  python bazi_evaluator.py --input /path/to/10.xlsx --verbose
  
  # 仅使用百炼平台
  python bazi_evaluator.py --input /path/to/10.xlsx --platform bailian
  
  # 双平台对比评测（Coze + 百炼）
  python bazi_evaluator.py --input /path/to/10.xlsx --platform both
        """
    )
    
    parser.add_argument('--input', '-i', required=True, help='输入Excel文件路径')
    parser.add_argument('--row', '-r', type=int, help='只处理指定数据行（从1开始，1表示第一条数据）')
    parser.add_argument('--concurrency', '-c', type=int, default=3, help='批量处理并发数（默认: 3，同时处理的用户数）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细进度')
    parser.add_argument('--base-url', help='API服务地址（默认: http://8.210.52.217:8001）')
    parser.add_argument('--platform', '-p', choices=['coze', 'bailian', 'both'], default='coze',
                       help='评测平台: coze(默认), bailian(百炼), both(双平台对比)')
    parser.add_argument('--bailian-api-key', help='百炼平台 API Key（也可通过环境变量 DASHSCOPE_API_KEY 设置）')
    
    args = parser.parse_args()
    
    # 创建配置
    config = EvaluationConfig()
    if args.base_url:
        config.base_url = args.base_url
    
    # 设置平台
    config.platform = args.platform
    if args.bailian_api_key:
        config.bailian_api_key = args.bailian_api_key
    
    # 检查百炼平台依赖
    if config.use_bailian and not BAILIAN_AVAILABLE:
        print("错误: 使用百炼平台需要安装 dashscope SDK")
        print("请运行: pip install dashscope")
        sys.exit(1)
    
    print(f"评测平台: {config.platform}")
    
    # 创建评测器
    evaluator = BaziEvaluator(config=config, verbose=args.verbose)
    
    try:
        # 打开Excel文件
        print(f"打开Excel文件: {args.input}")
        with ExcelHandler(args.input) as excel:
            # 读取测试用例
            if args.row:
                test_cases = excel.read_test_cases(data_row_start=args.row, data_row_end=args.row)
            else:
                test_cases = excel.read_test_cases()
            
            if not test_cases:
                print("未找到有效的测试数据")
                return
            
            print(f"读取到 {len(test_cases)} 条测试数据")
            
            # 执行评测（支持并发处理）
            results = await evaluator.evaluate_batch(test_cases, max_concurrency=args.concurrency)
            
            # 写入结果
            print("写入评测结果...")
            for test_case, result in results:
                if 'error' not in result or result.get('basic'):
                    excel.write_result(test_case, result)
            
            # 保存文件
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


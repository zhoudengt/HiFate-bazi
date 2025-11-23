#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 生成服务 - 类似 FateTell 的实时生成模式
从八字数据直接生成完整报告，而非规则匹配
"""

import sys
import os
from typing import Dict, Any, Optional
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from src.ai.bazi_ai_analyzer import BaziAIAnalyzer


class LLMGenerateService:
    """LLM 生成服务 - 类似 FateTell 的实时生成模式"""
    
    @staticmethod
    def build_comprehensive_prompt(bazi_data: Dict[str, Any], user_question: Optional[str] = None) -> str:
        """
        构建完整的 LLM Prompt，包含八字数据和命理知识
        
        Args:
            bazi_data: 八字数据
            user_question: 用户问题（可选）
            
        Returns:
            str: 完整的 Prompt
        """
        lines = []
        
        # 1. 角色设定
        lines.append("你是一位资深的命理师，精通八字命理、紫微斗数等传统命理学。")
        lines.append("请根据用户提供的八字信息，生成一份专业、详细、个性化的命理分析报告。")
        lines.append("")
        
        # 2. 八字基本信息
        basic_info = bazi_data.get('basic_info', {})
        lines.append("【用户基本信息】")
        lines.append(f"出生日期：{basic_info.get('solar_date', '')} {basic_info.get('solar_time', '')}")
        lines.append(f"性别：{'男' if basic_info.get('gender') == 'male' else '女'}")
        
        lunar_date = basic_info.get('lunar_date', {})
        if isinstance(lunar_date, dict):
            lines.append(f"农历：{lunar_date.get('year', '')}年{lunar_date.get('month', '')}月{lunar_date.get('day', '')}日")
        lines.append("")
        
        # 3. 四柱八字
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        lines.append("【四柱八字】")
        pillar_names = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            pillar_name = pillar_names.get(pillar_type, pillar_type)
            stem = pillar.get('stem', '')
            branch = pillar.get('branch', '')
            lines.append(f"{pillar_name}：{stem}{branch}")
        lines.append("")
        
        # 4. 详细四柱信息
        details = bazi_data.get('details', {})
        if details:
            lines.append("【详细四柱信息】")
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar_detail = details.get(pillar_type, {})
                if not isinstance(pillar_detail, dict):
                    continue
                
                pillar_name = pillar_names.get(pillar_type, pillar_type)
                lines.append(f"{pillar_name}：")
                
                if pillar_detail.get('main_star'):
                    lines.append(f"  主星：{pillar_detail.get('main_star')}")
                if pillar_detail.get('nayin'):
                    lines.append(f"  纳音：{pillar_detail.get('nayin')}")
                if pillar_detail.get('deities'):
                    deities = pillar_detail.get('deities', [])
                    if deities:
                        lines.append(f"  神煞：{', '.join(deities)}")
                if pillar_detail.get('kongwang'):
                    lines.append(f"  空亡：{pillar_detail.get('kongwang')}")
            lines.append("")
        
        # 5. 十神统计
        # 【防御性代码】修复 ten_gods_stats 可能为字符串的问题
        ten_gods_stats_raw = bazi_data.get('ten_gods_stats', {})
        if isinstance(ten_gods_stats_raw, str):
            try:
                import ast
                ten_gods_stats_raw = ast.literal_eval(ten_gods_stats_raw)
            except (ValueError, SyntaxError):
                try:
                    import json
                    ten_gods_stats_raw = json.loads(ten_gods_stats_raw)
                except (json.JSONDecodeError, TypeError):
                    ten_gods_stats_raw = {}
        if not isinstance(ten_gods_stats_raw, dict):
            ten_gods_stats_raw = {}
        ten_gods_stats = ten_gods_stats_raw
        
        if ten_gods_stats:
            lines.append("【十神统计】")
            for god_name, count in ten_gods_stats.items():
                # 确保 count 是整数
                try:
                    count_int = int(count) if count is not None else 0
                    if count_int > 0:
                        lines.append(f"{god_name}：{count_int}个")
                except (ValueError, TypeError):
                    # 如果转换失败，跳过
                    pass
            lines.append("")
        
        # 6. 五行统计
        element_counts = bazi_data.get('element_counts', {})
        if element_counts:
            lines.append("【五行统计】")
            wuxing_names = {'wood': '木', 'fire': '火', 'earth': '土', 'metal': '金', 'water': '水'}
            for element, count in element_counts.items():
                # 确保 count 是整数
                try:
                    count_int = int(count) if count is not None else 0
                    element_name = wuxing_names.get(element, element)
                    if count_int > 0:
                        lines.append(f"{element_name}：{count_int}个")
                except (ValueError, TypeError):
                    # 如果转换失败，跳过
                    pass
            lines.append("")
        
        # 7. 用户问题（如果有）
        if user_question:
            lines.append("【用户问题】")
            lines.append(user_question)
            lines.append("")
        
        # 8. 生成要求
        lines.append("【生成要求】")
        lines.append("请根据以上八字信息，生成一份详细的命理分析报告，包括但不限于：")
        lines.append("1. 性格特点分析（基于日主、十神、格局等）")
        lines.append("2. 事业运势分析（适合的职业方向、发展建议）")
        lines.append("3. 财运分析（财富积累方式、理财建议）")
        lines.append("4. 感情婚姻分析（感情特点、婚姻建议）")
        lines.append("5. 健康运势分析（需要注意的健康方面）")
        lines.append("6. 流年运势建议（近期需要注意的事项）")
        lines.append("")
        lines.append("要求：")
        lines.append("- 内容要专业、准确，符合传统命理学原理")
        lines.append("- 语言要自然、流畅，避免过于玄学化")
        lines.append("- 要给出具体的建议，而非空泛的描述")
        lines.append("- 避免绝对化的表述，使用'倾向于'、'可能'等相对温和的措辞")
        lines.append("- 报告长度控制在800-1500字之间")
        lines.append("")
        lines.append("请开始生成报告：")
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_report(
        solar_date: str,
        solar_time: str,
        gender: str,
        user_question: Optional[str] = None,
        access_token: Optional[str] = None,
        bot_id: Optional[str] = None,
        api_base: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用 LLM 生成完整的命理报告（类似 FateTell）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            user_question: 用户问题（可选）
            access_token: Coze Access Token（可选）
            bot_id: Coze Bot ID（可选）
            api_base: Coze API 基础URL（可选）
            
        Returns:
            dict: 包含生成的报告和原始数据
        """
        try:
            # 1. 计算八字数据
            bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
            if not bazi_result:
                return {
                    "success": False,
                    "error": "八字计算失败",
                    "report": None,
                    "bazi_data": None
                }
            
            bazi_data = bazi_result.get('bazi', {})
            
            # 2. 构建 Prompt
            prompt = LLMGenerateService.build_comprehensive_prompt(bazi_data, user_question)
            
            # 3. 调用 LLM 生成报告
            init_kwargs = {}
            if access_token:
                init_kwargs['access_token'] = access_token
            if bot_id:
                init_kwargs['bot_id'] = bot_id
            if api_base:
                init_kwargs['api_base'] = api_base
            
            ai_analyzer = BaziAIAnalyzer(**init_kwargs)
            
            # 调用 Coze API 生成报告
            result = ai_analyzer._call_coze_api(prompt, bazi_data)
            
            if result.get('success'):
                report = result.get('analysis', '')
                return {
                    "success": True,
                    "report": report,
                    "bazi_data": bazi_data,
                    "prompt_length": len(prompt),
                    "report_length": len(report) if report else 0
                }
            else:
                # 改进错误信息，提供更友好的提示
                error_msg = result.get('error', 'LLM 生成失败')
                
                # 检查是否是 Coze API 服务器问题
                if "server issues" in error_msg.lower() or "currently experiencing" in error_msg.lower():
                    friendly_error = (
                        "Coze API 服务暂时不可用，请稍后重试。\n"
                        "提示：您可以使用规则匹配模式获取分析结果：\n"
                        "  POST /api/v1/bazi/rules/curated"
                    )
                elif "timeout" in error_msg.lower() or "超时" in error_msg:
                    friendly_error = (
                        "LLM 生成超时，请稍后重试。\n"
                        "提示：您可以使用规则匹配模式获取更快的响应：\n"
                        "  POST /api/v1/bazi/rules/curated"
                    )
                else:
                    friendly_error = f"LLM 生成失败: {error_msg}\n提示：您可以使用规则匹配模式作为替代方案"
                
                return {
                    "success": False,
                    "error": friendly_error,
                    "error_detail": error_msg,  # 保留原始错误信息供调试
                    "report": None,
                    "bazi_data": bazi_data,
                    "suggestion": "可以使用规则匹配模式：POST /api/v1/bazi/rules/curated"
                }
                
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"生成报告异常: {str(e)}\n{traceback.format_exc()}",
                "report": None,
                "bazi_data": None
            }


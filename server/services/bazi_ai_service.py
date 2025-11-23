#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字AI分析服务层
调用八字接口，获取数据后传递给AI进行分析
"""

import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from src.ai.bazi_ai_analyzer import BaziAIAnalyzer
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer


class BaziAIService:
    """八字AI分析服务类"""
    
    @staticmethod
    def analyze_bazi_with_ai(solar_date: str, solar_time: str, gender: str,
                             user_question: Optional[str] = None,
                             access_token: Optional[str] = None,
                             bot_id: Optional[str] = None,
                             api_base: Optional[str] = None,
                             include_rizhu_analysis: bool = True) -> Dict[str, Any]:
        """
        调用八字接口，获取数据后传递给Coze AI进行分析
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
            user_question: 用户的问题或分析需求，可选
            access_token: Coze Access Token，可选（不提供则使用环境变量）
            bot_id: Coze Bot ID，可选（不提供则使用环境变量）
            api_base: Coze API 基础URL，可选
            include_rizhu_analysis: 是否包含日柱性别分析结果
        
        Returns:
            dict: 包含八字数据和AI分析结果
        """
        # 1. 调用八字计算接口获取数据
        bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
        
        if not bazi_result:
            return {
                "success": False,
                "error": "八字计算失败",
                "bazi_data": None,
                "ai_analysis": None
            }
        
        # 2. 获取日柱性别分析结果（只传递这部分给AI）
        rizhu_analysis_text = ""
        if include_rizhu_analysis:
            try:
                # bazi_result 的结构是 {"bazi": {...}, "rizhu": "...", "matched_rules": [...]}
                bazi_data = bazi_result.get('bazi', {})
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                analyzer = RizhuGenderAnalyzer(bazi_pillars, gender)
                rizhu_analysis_text = analyzer.get_formatted_output()
                print(f"✓ 已获取日柱性别分析内容（长度: {len(rizhu_analysis_text)} 字符）")
            except Exception as e:
                print(f"获取日柱性别分析失败: {e}")
                rizhu_analysis_text = ""
        
        # 3. 调用Coze AI分析器
        try:
            # 构建初始化参数
            init_kwargs = {}
            if access_token:
                init_kwargs['access_token'] = access_token
            if bot_id:
                init_kwargs['bot_id'] = bot_id
            if api_base:
                init_kwargs['api_base'] = api_base
            
            ai_analyzer = BaziAIAnalyzer(**init_kwargs)
            
            # 5. 如果有【性格与命运解析】内容，将其传递给大模型进行处理
            polished_rules = None
            polished_rules_info = None  # 包含润色前后的对比信息
            if include_rizhu_analysis and rizhu_analysis_text:
                try:
                    # 检查是否包含【性格与命运解析】格式
                    if "【性格与命运解析】" in rizhu_analysis_text:
                        # 提取用户指令（如果用户问题中包含处理要求）
                        polish_instruction = None
                        if user_question:
                            # 检查用户问题中是否包含处理相关指令
                            polish_keywords = ['润色', '优化', '改进', '美化', '完善', '处理']
                            if any(keyword in user_question for keyword in polish_keywords):
                                polish_instruction = user_question
                        
                        polished_result = ai_analyzer.polish_character_analysis(rizhu_analysis_text, polish_instruction)
                        if polished_result.get('success'):
                            polished_rules = polished_result.get('polished_content')  # 润色后的内容
                            polished_rules_info = {
                                "original": polished_result.get('original_content'),  # 原始内容
                                "polished": polished_result.get('polished_content'),  # 润色后的内容
                                "changes": polished_result.get('changes', []),  # 修改列表
                                "changes_count": polished_result.get('changes_count', 0)  # 修改数量
                            }
                        else:
                            print(f"性格与命运解析处理失败: {polished_result.get('error')}")
                except Exception as e:
                    print(f"性格与命运解析处理异常: {e}")
                    polished_rules = None
                    polished_rules_info = None
            
            # 6. 进行AI分析（只传递日柱性别分析内容，不传递其他八字信息）
            if include_rizhu_analysis and rizhu_analysis_text:
                # 只传递日柱性别分析文本给AI
                ai_result = ai_analyzer.analyze_rizhu_gender_only(
                    rizhu_analysis_text,
                    user_question
                )
            else:
                # 如果没有日柱性别分析，返回空结果
                ai_result = {
                    "success": False,
                    "error": "未提供日柱性别分析内容",
                    "analysis": None
                }
            
            return {
                "success": True,
                "bazi_data": bazi_result,
                "ai_analysis": ai_result,
                "rizhu_analysis": rizhu_analysis_text if include_rizhu_analysis else None,
                "polished_rules": polished_rules,  # 润色后的规则内容
                "polished_rules_info": polished_rules_info  # 润色前后的对比信息
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"AI分析失败: {str(e)}",
                "bazi_data": bazi_result,
                "ai_analysis": None
            }


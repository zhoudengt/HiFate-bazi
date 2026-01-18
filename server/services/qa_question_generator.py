#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA 问题生成服务
基于用户问题、答案内容和八字信息生成后续问题
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.coze_stream_service import CozeStreamService

logger = logging.getLogger(__name__)


class QAQuestionGenerator:
    """问题生成服务"""
    
    def __init__(self):
        # 导入配置加载器（从数据库读取配置）
        try:
            from server.config.config_loader import get_config_from_db_only
        except ImportError:
            def get_config_from_db_only(key: str) -> Optional[str]:
                raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
        
        # 只从数据库读取，不降级到环境变量
        self.question_bot_id = get_config_from_db_only("QA_QUESTION_GENERATOR_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
        if not self.question_bot_id:
            raise ValueError("数据库配置缺失: QA_QUESTION_GENERATOR_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置")
        self.coze_service = CozeStreamService(bot_id=self.question_bot_id)
    
    async def generate_questions_after_answer(
        self,
        user_question: str,
        answer: str,
        bazi_data: Dict[str, Any],
        intent_result: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> List[str]:
        """
        答案生成后生成相关问题（使用方案2）
        
        Args:
            user_question: 用户问题
            answer: 答案内容（可能只包含前200字，用于并行生成）
            bazi_data: 八字数据
            intent_result: 意图识别结果
            conversation_history: 对话历史
        
        Returns:
            相关问题列表（最多2个）
        """
        try:
            # 构建输入数据（包含答案内容）
            input_data = {
                'user_question': user_question,
                'answer': answer[:500] if answer else '',  # 只取前500字
                'intent': intent_result.get('intents', []),
                'bazi_summary': self._summarize_bazi(bazi_data),
                'conversation_context': {
                    'previous_questions': [h['question'] for h in conversation_history[-3:]],
                    'previous_answers': [h['answer'] for h in conversation_history[-3:] if h.get('answer')]
                }
            }
            
            # 使用方案2：format_input_data_for_coze
            formatted_data = self.format_input_data_for_coze(input_data)
            
            # 调用问题生成 Bot（提示词在 Coze Bot 中）
            questions = await self._call_question_bot(formatted_data)
            return questions[:2]  # 返回最多2个问题（根据用户提示词要求）
            
        except Exception as e:
            logger.error(f"生成问题失败（答案后）: {e}", exc_info=True)
            return []
    
    def _summarize_bazi(self, bazi_data: Dict[str, Any]) -> str:
        """生成八字摘要"""
        summary_parts = []
        
        # 四柱
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        if bazi_pillars:
            pillars = []
            for key in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(key, {})
                stem = pillar.get('stem', '')
                branch = pillar.get('branch', '')
                if stem and branch:
                    pillars.append(f"{stem}{branch}")
            if pillars:
                summary_parts.append(f"四柱：{' '.join(pillars)}")
        
        # 十神
        ten_gods_stats = bazi_data.get('ten_gods_stats', {})
        if ten_gods_stats:
            ten_gods_list = [f"{k}:{v}" for k, v in ten_gods_stats.items() if v]
            if ten_gods_list:
                summary_parts.append(f"十神：{', '.join(ten_gods_list[:5])}")
        
        # 五行
        element_counts = bazi_data.get('element_counts', {})
        if element_counts:
            elements = [f"{k}:{v}" for k, v in element_counts.items() if v]
            if elements:
                summary_parts.append(f"五行：{', '.join(elements)}")
        
        return '；'.join(summary_parts) if summary_parts else '八字信息待完善'
    
    def format_input_data_for_coze(self, data: dict) -> str:
        """
        格式化输入数据为 JSON 字符串（方案2）
        
        ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
        提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
        
        Args:
            data: 输入数据字典
            
        Returns:
            str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
        """
        import json
        
        optimized_data = {
            'user_question': data.get('user_question', ''),
            'answer': data.get('answer', '')[:500] if data.get('answer') else '',  # 只取前500字
            'intent': data.get('intent', []),
            'bazi_summary': data.get('bazi_summary', ''),
            'conversation_context': data.get('conversation_context', {})
        }
        
        return json.dumps(optimized_data, ensure_ascii=False, indent=2)
    
    async def _call_question_bot(self, formatted_data: str) -> List[str]:
        """
        调用问题生成 Bot（使用方案2）
        
        Args:
            formatted_data: 格式化后的 JSON 数据（方案2）
        
        Returns:
            问题列表（最多2个）
        """
        try:
            questions_text = ""
            
            # 调用 Coze Bot（流式，提示词在 Coze Bot 中）
            async for chunk in self.coze_service.stream_custom_analysis(formatted_data, bot_id=self.question_bot_id):
                if chunk.get('type') == 'progress':
                    questions_text += chunk.get('content', '')
                elif chunk.get('type') == 'complete':
                    questions_text += chunk.get('content', '')
                    break
                elif chunk.get('type') == 'error':
                    logger.error(f"问题生成 Bot 返回错误: {chunk.get('content')}")
                    return []
            
            # 解析问题（按行分割，去除空行和编号）
            questions = []
            for line in questions_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # 去除编号（如 "1. "、"1、"等）
                line = line.lstrip('0123456789.、）)')
                line = line.strip()
                
                if line and len(line) > 5:  # 至少5个字符
                    questions.append(line)
            
            return questions[:2]  # 返回最多2个问题（根据用户提示词要求）
            
        except Exception as e:
            logger.error(f"调用问题生成 Bot 失败: {e}", exc_info=True)
            return []


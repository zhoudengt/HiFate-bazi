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
        # 问题生成 Bot ID（从环境变量读取）
        self.question_bot_id = os.getenv("QA_QUESTION_GENERATOR_BOT_ID") or os.getenv("COZE_BOT_ID")
        self.coze_service = CozeStreamService(bot_id=self.question_bot_id)
    
    async def generate_questions_after_question(
        self,
        user_question: str,
        bazi_data: Dict[str, Any],
        intent_result: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> List[str]:
        """
        用户提问后生成3个相关问题
        
        Args:
            user_question: 用户问题
            bazi_data: 八字数据
            intent_result: 意图识别结果
            conversation_history: 对话历史
        
        Returns:
            3个相关问题列表
        """
        try:
            # 构建输入数据（结构化）
            input_data = {
                'user_question': user_question,
                'intent': intent_result.get('intents', []),
                'bazi_summary': self._summarize_bazi(bazi_data),
                'conversation_context': {
                    'previous_questions': [h['question'] for h in conversation_history[-3:]]
                }
            }
            
            # 转换为自然语言格式
            prompt = self._build_question_generation_prompt(input_data, include_answer=False)
            
            # 调用问题生成 Bot（提示词在 Coze Bot 中配置）
            questions = await self._call_question_bot(prompt)
            return questions[:3]  # 返回3个问题
            
        except Exception as e:
            logger.error(f"生成问题失败（提问后）: {e}", exc_info=True)
            return []
    
    async def generate_questions_after_answer(
        self,
        user_question: str,
        answer: str,
        bazi_data: Dict[str, Any],
        intent_result: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> List[str]:
        """
        答案生成后生成3个相关问题
        
        Args:
            user_question: 用户问题
            answer: 答案内容
            bazi_data: 八字数据
            intent_result: 意图识别结果
            conversation_history: 对话历史
        
        Returns:
            3个相关问题列表
        """
        try:
            # 构建输入数据（包含答案内容）
            input_data = {
                'user_question': user_question,
                'answer': answer,
                'intent': intent_result.get('intents', []),
                'bazi_summary': self._summarize_bazi(bazi_data),
                'conversation_context': {
                    'previous_questions': [h['question'] for h in conversation_history[-3:]],
                    'previous_answers': [h['answer'] for h in conversation_history[-3:] if h.get('answer')]
                }
            }
            
            # 转换为自然语言格式
            prompt = self._build_question_generation_prompt(input_data, include_answer=True)
            
            # 调用问题生成 Bot
            questions = await self._call_question_bot(prompt)
            return questions[:3]  # 返回3个问题
            
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
    
    def _build_question_generation_prompt(
        self,
        data: dict,
        include_answer: bool = False
    ) -> str:
        """
        构建问题生成提示词
        
        Args:
            data: 输入数据
            include_answer: 是否包含答案内容
        
        Returns:
            自然语言格式的提示词
        """
        prompt_lines = []
        
        # 1. 用户问题
        prompt_lines.append(f"【用户问题】")
        prompt_lines.append(f"{data.get('user_question', '')}")
        prompt_lines.append("")
        
        # 2. 答案内容（如果包含）
        if include_answer and data.get('answer'):
            prompt_lines.append(f"【答案内容】")
            answer = data.get('answer', '')
            # 只取前500字符
            prompt_lines.append(f"{answer[:500]}...")
            prompt_lines.append("")
        
        # 3. 意图
        intent = data.get('intent', [])
        if intent:
            prompt_lines.append(f"【意图识别】")
            prompt_lines.append(f"{', '.join(intent)}")
            prompt_lines.append("")
        
        # 4. 八字摘要
        bazi_summary = data.get('bazi_summary', '')
        if bazi_summary:
            prompt_lines.append(f"【八字摘要】")
            prompt_lines.append(f"{bazi_summary}")
            prompt_lines.append("")
        
        # 5. 对话上下文
        conversation_context = data.get('conversation_context', {})
        previous_questions = conversation_context.get('previous_questions', [])
        if previous_questions:
            prompt_lines.append(f"【对话历史】")
            for i, q in enumerate(previous_questions, 1):
                prompt_lines.append(f"  问题{i}：{q}")
            prompt_lines.append("")
        
        return '\n'.join(prompt_lines)
    
    async def _call_question_bot(self, prompt: str) -> List[str]:
        """
        调用问题生成 Bot
        
        Args:
            prompt: 提示词
        
        Returns:
            问题列表
        """
        try:
            questions_text = ""
            
            # 调用 Coze Bot（流式）
            async for chunk in self.coze_service.stream_custom_analysis(prompt, bot_id=self.question_bot_id):
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
            
            return questions[:3]  # 返回最多3个问题
            
        except Exception as e:
            logger.error(f"调用问题生成 Bot 失败: {e}", exc_info=True)
            return []


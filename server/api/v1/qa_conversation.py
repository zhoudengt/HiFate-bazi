#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA 多轮对话 API
支持问题分类引导、智能问题生成和流式回答
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from fastapi import APIRouter, Path
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.services.qa_conversation_service import QAConversationService

logger = logging.getLogger(__name__)

router = APIRouter()

# 延迟创建服务实例（避免模块加载时初始化失败）
_qa_service = None

def get_qa_service():
    """获取QA服务实例（延迟初始化）"""
    global _qa_service
    if _qa_service is None:
        try:
            _qa_service = QAConversationService()
        except Exception as e:
            logger.error(f"QAConversationService 初始化失败: {e}", exc_info=True)
            raise
    return _qa_service


class QAStartRequest(BaziBaseRequest):
    """开始对话请求"""
    user_id: Optional[str] = Field(None, description="用户ID", example="user123")


class QAAskRequest(BaseModel):
    """提问请求"""
    session_id: str = Field(..., description="会话ID", example="550e8400-e29b-41d4-a716-446655440000")
    question: str = Field(..., description="用户问题", example="我想了解一下我的事业运势")


@router.post("/qa/start", summary="开始新对话")
async def start_conversation(request: QAStartRequest):
    """
    开始新对话
    
    Args:
        request: 开始对话请求参数
    
    Returns:
        {
            'success': bool,
            'session_id': str,
            'initial_question': str,
            'categories': List[Dict[str, str]]
        }
    """
    try:
        qa_service = get_qa_service()
        result = await qa_service.start_conversation(
            user_id=request.user_id or "anonymous",
            solar_date=request.solar_date,
            solar_time=request.solar_time,
            gender=request.gender
        )
        return result
    except Exception as e:
        logger.error(f"开始对话失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


class CategoryQuestionsRequest(BaseModel):
    """获取分类问题请求"""
    category: str = Field(..., description="分类名称", example="career_wealth")


@router.post("/qa/category-questions", summary="获取分类问题列表（POST）")
async def get_category_questions(request: CategoryQuestionsRequest):
    """
    获取分类下的问题列表（POST方式）
    
    Args:
        request: 请求参数
    
    Returns:
        问题列表
    """
    try:
        category = request.category
        if not category:
            return {
                'success': False,
                'error': 'category 参数缺失',
                'questions': []
            }
        qa_service = get_qa_service()
        questions = await qa_service.get_category_questions(category)
        return {
            'success': True,
            'category': category,
            'questions': questions
        }
    except Exception as e:
        logger.error(f"获取分类问题失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'questions': []
        }


@router.get("/qa/categories/{category}/questions", summary="获取分类问题列表（GET）")
async def get_category_questions_get(category: str = Path(..., description="分类名称", example="career_wealth")):
    """
    获取分类下的问题列表（GET方式）
    
    Args:
        category: 分类名称（路径参数）
    
    Returns:
        问题列表
    """
    try:
        if not category:
            return {
                'success': False,
                'error': 'category 参数缺失',
                'questions': []
            }
        qa_service = get_qa_service()
        questions = await qa_service.get_category_questions(category)
        return {
            'success': True,
            'category': category,
            'questions': questions
        }
    except Exception as e:
        logger.error(f"获取分类问题失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'questions': []
        }


@router.post("/qa/ask", summary="提问（流式）")
async def ask_question(request: QAAskRequest):
    """
    提问并生成答案（流式）
    
    Args:
        request: 提问请求参数
    
    Returns:
        SSE 流式响应
    """
    async def generate():
        try:
            qa_service = get_qa_service()
            async for chunk in qa_service.ask_question(
                    session_id=request.session_id,
                    question=request.question
                ):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"提问处理失败: {e}", exc_info=True)
            error_chunk = {
                'type': 'error',
                'content': f'处理失败: {str(e)}'
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


class ConversationHistoryRequest(BaseModel):
    """获取对话历史请求"""
    session_id: str = Field(..., description="会话ID", example="550e8400-e29b-41d4-a716-446655440000")


@router.post("/qa/conversation-history", summary="获取对话历史（POST）")
async def get_conversation_history(request: ConversationHistoryRequest):
    """
    获取对话历史（POST方式）
    
    Args:
        request: 请求参数
    
    Returns:
        对话历史列表
    """
    try:
        session_id = request.session_id
        if not session_id:
            return {
                'success': False,
                'error': 'session_id 参数缺失',
                'history': []
            }
        qa_service = get_qa_service()
        history = await qa_service._get_conversation_history(session_id)
        return {
            'success': True,
            'session_id': session_id,
            'history': history
        }
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'history': []
        }


@router.get("/qa/sessions/{session_id}/history", summary="获取对话历史（GET）")
async def get_conversation_history_get(session_id: str = Path(..., description="会话ID")):
    """
    获取对话历史（GET方式）
    
    Args:
        session_id: 会话ID（路径参数）
    
    Returns:
        对话历史列表
    """
    try:
        if not session_id:
            return {
                'success': False,
                'error': 'session_id 参数缺失',
                'history': []
            }
        qa_service = get_qa_service()
        history = await qa_service._get_conversation_history(session_id)
        return {
            'success': True,
            'session_id': session_id,
            'history': history
        }
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'history': []
        }


class ValidateSessionRequest(BaseModel):
    """验证会话请求"""
    session_id: str = Field(..., description="会话ID", example="550e8400-e29b-41d4-a716-446655440000")


@router.post("/qa/validate-session", summary="验证会话是否存在（POST）")
async def validate_session(request: ValidateSessionRequest):
    """
    验证会话是否存在（POST方式）
    
    Args:
        request: 请求参数
    
    Returns:
        会话验证结果
    """
    try:
        session_id = request.session_id
        if not session_id:
            return {
                'success': False,
                'valid': False,
                'exists': False,
                'error': 'session_id 参数缺失'
            }
        qa_service = get_qa_service()
        result = await qa_service._validate_session(session_id)
        return {
            'success': True,
            **result
        }
    except Exception as e:
        logger.error(f"验证会话失败: {e}", exc_info=True)
        return {
            'success': False,
            'valid': False,
            'exists': False,
            'error': str(e)
        }


@router.get("/qa/sessions/{session_id}/validate", summary="验证会话是否存在（GET）")
async def validate_session_get(session_id: str = Path(..., description="会话ID")):
    """
    验证会话是否存在（GET方式）
    
    Args:
        session_id: 会话ID（路径参数）
    
    Returns:
        会话验证结果
    """
    try:
        if not session_id:
            return {
                'success': False,
                'valid': False,
                'exists': False,
                'error': 'session_id 参数缺失'
            }
        qa_service = get_qa_service()
        result = await qa_service._validate_session(session_id)
        return {
            'success': True,
            **result
        }
    except Exception as e:
        logger.error(f"验证会话失败: {e}", exc_info=True)
        return {
            'success': False,
            'valid': False,
            'exists': False,
            'error': str(e)
        }


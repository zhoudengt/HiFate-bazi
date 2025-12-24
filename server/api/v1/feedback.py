#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户反馈API
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from server.db.feedback_dao import FeedbackDAO

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    rule_code: str = Field(..., description="规则代码")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分(1-5星)")
    accuracy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="准确性评分(0-1)")
    usefulness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="有用性评分(0-1)")
    comment: Optional[str] = Field(None, description="评论")


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    success: bool
    message: str


class RuleFeedbackStatsResponse(BaseModel):
    """规则反馈统计响应模型"""
    success: bool
    rule_code: str
    stats: Optional[dict] = None


@router.post("/feedback", response_model=FeedbackResponse, summary="提交用户反馈")
async def submit_feedback(
    request: FeedbackRequest
):
    """
    提交用户反馈
    
    支持：
    - 评分（1-5星）
    - 准确性评分（0-1）
    - 有用性评分（0-1）
    - 评论
    """
    try:
        # 使用匿名用户（认证功能已移除）
        user_id = 'anonymous'
        
        success = FeedbackDAO.add_feedback(
            user_id=user_id,
            rule_code=request.rule_code,
            rating=request.rating,
            accuracy_score=request.accuracy_score,
            usefulness_score=request.usefulness_score,
            comment=request.comment
        )
        
        if success:
            return FeedbackResponse(
                success=True,
                message="反馈提交成功"
            )
        else:
            raise HTTPException(status_code=500, detail="反馈提交失败")
            
    except Exception as e:
        logger.error(f"提交反馈失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")


@router.get("/feedback/rule/{rule_code}/stats", response_model=RuleFeedbackStatsResponse, summary="获取规则反馈统计")
async def get_rule_feedback_stats(
    rule_code: str,
    days: int = 30
):
    """
    获取规则的反馈统计
    
    Args:
        rule_code: 规则代码
        days: 统计天数，默认30天
    """
    try:
        stats = FeedbackDAO.get_rule_feedback_stats(rule_code, days)
        
        return RuleFeedbackStatsResponse(
            success=True,
            rule_code=rule_code,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"获取规则反馈统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/feedback/user", summary="获取用户反馈历史")
async def get_user_feedback(
    limit: int = 50
):
    """
    获取当前用户的反馈历史
    """
    try:
        # 使用匿名用户（认证功能已移除）
        user_id = 'anonymous'
        
        feedback_list = FeedbackDAO.get_user_feedback(user_id, limit)
        
        return {
            "success": True,
            "feedback": feedback_list
        }
        
    except Exception as e:
        logger.error(f"获取用户反馈历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取反馈历史失败: {str(e)}")


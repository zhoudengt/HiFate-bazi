#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息评价 API - 用户对流式 AI 消息的赞/踩反馈
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.db.message_feedback_dao import MessageFeedbackDAO

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageFeedbackRequest(BaseModel):
    """消息评价请求"""
    request_id: str = Field(..., description="关联的流式消息 request_id")
    rating: str = Field(..., description="评价: up(赞) 或 down(踩)")
    comment: Optional[str] = Field(None, description="用户补充说明（踩时可选）")


@router.post("/message-feedback", summary="提交消息评价")
async def submit_message_feedback(req: MessageFeedbackRequest):
    """
    提交对某条流式 AI 消息的赞/踩评价。

    - request_id 必须存在于 stream_api_call_logs 表
    - 同一 request_id 重复提交时覆盖（幂等）
    - rating 仅允许 up / down
    """
    if req.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating 只允许 up 或 down")

    if not MessageFeedbackDAO.request_id_exists(req.request_id):
        raise HTTPException(status_code=404, detail="request_id 不存在")

    ok = MessageFeedbackDAO.upsert(req.request_id, req.rating, req.comment)
    if not ok:
        raise HTTPException(status_code=500, detail="评价写入失败")

    return {"success": True}

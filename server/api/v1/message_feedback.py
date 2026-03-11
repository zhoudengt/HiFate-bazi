#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息评价 API - 用户对流式 AI 消息的好/一般/不好反馈（异步写入）
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.db.message_feedback_dao import MessageFeedbackDAO

logger = logging.getLogger(__name__)

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="msg_feedback")


class MessageFeedbackRequest(BaseModel):
    """消息评价请求"""
    request_id: str = Field(..., description="关联的流式消息 request_id")
    rating: str = Field(..., description="评价: good(好) / neutral(一般) / bad(不好)")
    comment: Optional[str] = Field(None, description="用户补充说明（踩时可选）")
    email: Optional[str] = Field(None, description="用户邮箱")
    name: Optional[str] = Field(None, description="用户名称")


def _write_feedback(request_id: str, rating: str, comment: Optional[str],
                    email: Optional[str], name: Optional[str]):
    """后台线程写入数据库"""
    try:
        MessageFeedbackDAO.upsert(request_id, rating, comment, email=email, name=name)
    except Exception as e:
        logger.error(f"[MessageFeedback] 异步写入失败: {e}", exc_info=True)


@router.post("/message-feedback", summary="提交消息评价")
async def submit_message_feedback(req: MessageFeedbackRequest):
    """
    提交对某条流式 AI 消息的好/一般/不好评价。

    - 同一 request_id 重复提交时覆盖（幂等）
    - rating 仅允许 good / neutral / bad
    - 异步写入，立即返回
    """
    if req.rating not in ("good", "neutral", "bad"):
        raise HTTPException(status_code=400, detail="rating 只允许 good / neutral / bad")

    _executor.submit(_write_feedback, req.request_id, req.rating, req.comment,
                     req.email, req.name)

    return {"success": True}

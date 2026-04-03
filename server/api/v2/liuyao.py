#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 六爻 API：起卦 + 流式解读（无 JWT）。
路径前缀由 router_registry 注册为 /api/v2/liuyao。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from server.db import v2_liuyao_dao
from server.services.liuyao_service import divinate as liuyao_divinate

router = APIRouter()
logger = logging.getLogger(__name__)


class LiuYaoV2Request(BaseModel):
    question: str = Field(..., description="占卜问题")
    method: str = Field(..., description="起卦方式: coin / number / time")
    coin_results: Optional[list] = Field(None, description="铜钱法: 6 个 2/3/6/9")
    number: Optional[list] = Field(None, description="数字法: 3 个数字")
    divination_time: Optional[str] = Field(None, description="时间法: YYYY-MM-DD HH:mm")
    category: Optional[str] = Field("general", description="事业/感情/财运等，仅落库用")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选）")
    persist: bool = Field(True, description="是否尝试写入 v2_liuyao_castings")


@router.post("/divinate", summary="V2 六爻起卦（仅卦象，可落库）")
async def divinate_v2(request: LiuYaoV2Request) -> Dict[str, Any]:
    try:
        data = liuyao_divinate(
            question=request.question,
            method=request.method,
            coin_results=request.coin_results,
            number=request.number,
            divination_time=request.divination_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("V2 六爻起卦异常")
        raise HTTPException(status_code=500, detail=str(e))

    casting_id: Optional[int] = None
    if request.persist:
        casting_id = v2_liuyao_dao.insert_casting(
            question=request.question.strip(),
            method=request.method,
            category=request.category,
            coin_results=request.coin_results,
            number_input=request.number,
            divination_time=request.divination_time,
            result_json=data,
        )

    return {"success": True, "data": data, "casting_id": casting_id}


@router.post("/stream", summary="V2 六爻流式解读（同 V1 逻辑）")
async def stream_liuyao_v2(request: LiuYaoV2Request):
    """先卦象后 LLM；请求体与 divinate 一致（忽略 persist）。"""
    try:
        from server.api.v1.liuyao import LiuYaoRequest, liuyao_stream_generator

        legacy = LiuYaoRequest(
            question=request.question,
            method=request.method,
            coin_results=request.coin_results,
            number=request.number,
            divination_time=request.divination_time,
            bot_id=request.bot_id,
        )
        return StreamingResponse(
            liuyao_stream_generator(legacy),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.exception("V2 六爻流式接口异常")
        raise HTTPException(status_code=500, detail=str(e))

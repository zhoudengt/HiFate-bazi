#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六爻占卜 API：非流式起卦 + 流式 AI 解读。
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from server.services.liuyao_service import divinate as liuyao_divinate

router = APIRouter()
logger = logging.getLogger(__name__)


class LiuYaoRequest(BaseModel):
    question: str = Field(..., description="占卜问题")
    method: str = Field(..., description="起卦方式: coin / number / time")
    coin_results: Optional[List[int]] = Field(None, description="铜钱法: 6 个 2/3/6/9")
    number: Optional[List[int]] = Field(None, description="数字法: 3 个数字")
    divination_time: Optional[str] = Field(None, description="时间法: YYYY-MM-DD HH:mm")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选）")


def _format_liuyao_for_llm(data: Dict[str, Any]) -> str:
    """将卦象数据格式化为 LLM 可读文本。"""
    lines = []
    lines.append(f"【占卜问题】{data.get('question', '')}")
    lines.append(f"【起卦方式】{data.get('method', '')}")
    ben = data.get("ben_gua", {})
    lines.append(f"【本卦】{ben.get('name', '')}")
    lines.append(f"【卦辞】{data.get('gua_ci', '')}")
    for li in ben.get("lines", [])[::-1]:
        pos = li.get("position", 0)
        yin_yang = "阳" if li.get("yin_yang") == "yang" else "阴"
        dong = "（动）" if li.get("is_dong") else ""
        lines.append(f"  第{pos}爻 {yin_yang}{dong} 六亲:{li.get('liu_qin','')} 六神:{li.get('liu_shen','')} 爻辞:{li.get('yao_ci','')}")
    bian = data.get("bian_gua", {})
    lines.append(f"【变卦】{bian.get('name', '')}")
    shi_ying = data.get("shi_ying", {})
    lines.append(f"【世应】世爻:{shi_ying.get('shi_yao')} 应爻:{shi_ying.get('ying_yao')}")
    return "\n".join(lines)


@router.post("/liuyao/divinate", summary="六爻起卦（仅卦象）")
async def divinate(request: LiuYaoRequest) -> Dict[str, Any]:
    """仅返回卦象，不调用 LLM。"""
    try:
        data = liuyao_divinate(
            question=request.question,
            method=request.method,
            coin_results=request.coin_results,
            number=request.number,
            divination_time=request.divination_time,
        )
        return {"success": True, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("六爻起卦异常")
        raise HTTPException(status_code=500, detail=str(e))


async def liuyao_stream_generator(
    request: LiuYaoRequest,
    request_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """流式生成：先 data，再 progress/complete。"""
    def _sse(msg: Dict[str, Any]) -> str:
        return f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

    try:
        data = liuyao_divinate(
            question=request.question,
            method=request.method,
            coin_results=request.coin_results,
            number=request.number,
            divination_time=request.divination_time,
        )
        yield _sse({"type": "data", "content": {"success": True, "data": data}})

        formatted = _format_liuyao_for_llm(data)
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            llm_service = LLMServiceFactory.get_service(scene="liuyao", bot_id=request.bot_id)
        except Exception as e:
            logger.warning(f"六爻 LLM 初始化失败: {e}")
            yield _sse({"type": "error", "content": f"LLM 服务不可用: {str(e)}"})
            return

        stream_kwargs: Dict[str, Any] = {}
        if hasattr(llm_service, "bot_id") and llm_service.bot_id:
            stream_kwargs["bot_id"] = request.bot_id or llm_service.bot_id

        has_content = False
        async for chunk in llm_service.stream_analysis(formatted, **stream_kwargs):
            t = chunk.get("type", "progress")
            c = chunk.get("content", "")
            if t == "progress" and c:
                has_content = True
                yield _sse({"type": "progress", "content": c})
                await asyncio.sleep(0)
            elif t == "complete":
                yield _sse({"type": "complete", "content": c or ""})
                return
            elif t == "error":
                yield _sse({"type": "error", "content": c or "分析失败"})
                return

        if not has_content:
            yield _sse({"type": "complete", "content": ""})
    except ValueError as e:
        yield _sse({"type": "error", "content": str(e)})
    except Exception as e:
        logger.exception("六爻流式异常")
        yield _sse({"type": "error", "content": str(e)})


@router.post("/liuyao/stream", summary="六爻流式解读")
async def stream_liuyao(request: LiuYaoRequest):
    """先返回卦象，再流式返回 AI 解读。"""
    try:
        return StreamingResponse(
            liuyao_stream_generator(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.exception("六爻流式接口异常")
        raise HTTPException(status_code=500, detail=str(e))

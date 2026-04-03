# -*- coding: utf-8 -*-
# [DEPRECATED] V1 六爻 gRPC-Web 已下线，请使用 REST POST /api/v2/liuyao/divinate 与 /stream。
"""六爻占卜 gRPC-Web 端点处理器（已不再从 grpc_gateway 加载）。"""

import logging
from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register
from server.api.grpc_gateway.utils import _collect_sse_stream
from server.api.v1.liuyao import LiuYaoRequest, liuyao_stream_generator
from server.services.liuyao_service import divinate as liuyao_divinate

logger = logging.getLogger(__name__)


@_register("/liuyao/divinate")
async def _handle_liuyao_divinate(payload: Dict[str, Any]):
    request_model = LiuYaoRequest(**payload)
    result = liuyao_divinate(
        question=request_model.question,
        method=request_model.method,
        coin_results=request_model.coin_results,
        number=request_model.number,
        divination_time=request_model.divination_time,
    )
    return {"success": True, "data": result}


@_register("/liuyao/stream")
async def _handle_liuyao_stream(payload: Dict[str, Any]):
    _request_id = payload.pop("_request_id", None)
    request_model = LiuYaoRequest(**payload)
    generator = liuyao_stream_generator(request_model, request_id=_request_id)
    return await _collect_sse_stream(generator)

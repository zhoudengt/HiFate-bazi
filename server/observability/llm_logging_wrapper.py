#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 流式服务日志包装器

包装 BaseLLMStreamService，在调用前后自动记录：
- 发送给 LLM 的完整 prompt
- LLM 的完整响应内容及耗时

所有日志调用静默失败，不影响业务返回值与异常。

性能优化：
- 响应内容使用列表收集，最后一次性 join
- 日志调用在 try-except 中，不影响流式迭代性能
"""

import time
import logging
import uuid
from typing import Dict, Any, Optional, AsyncGenerator

from server.services.base_llm_stream_service import BaseLLMStreamService
from server.observability.stream_flow_logger import get_stream_flow_logger, STREAM_FLOW_LOGGING_ENABLED

logger = logging.getLogger(__name__)


class LoggingLLMWrapper(BaseLLMStreamService):
    """
    包装任意 LLM 流式服务，自动记录 prompt 与 response。
    不修改原有流式行为，异常与返回值与原服务一致。
    """

    def __init__(self, inner: BaseLLMStreamService, scene: str = ""):
        self._inner = inner
        self._scene = scene or "unknown"

    async def stream_analysis(
        self,
        prompt: str,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """包装流式调用：记录 prompt → 调用原服务 → 收集响应 → 记录 response。"""
        # 如果日志未启用，直接透传
        if not STREAM_FLOW_LOGGING_ENABLED:
            async for chunk in self._inner.stream_analysis(prompt, trace_id=trace_id, **kwargs):
                yield chunk
            return

        # 确保 trace_id 非空（用于日志关联）
        tid = trace_id if trace_id else f"auto-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        full_response_parts: list = []
        error_occurred = False

        # 记录 prompt（静默失败）
        try:
            flow_logger = get_stream_flow_logger()
            flow_logger.log_prompt(
                trace_id=tid,
                prompt=prompt,
                endpoint=f"/stream/{self._scene}",
                model_or_app_id=kwargs.get("bot_id") or kwargs.get("app_id"),
            )
        except Exception as e:
            logger.debug("stream_flow log_prompt 静默失败: %s", e)

        # 流式迭代
        try:
            async for chunk in self._inner.stream_analysis(prompt, trace_id=trace_id, **kwargs):
                ct = chunk.get("type")
                if ct == "progress":
                    content = chunk.get("content", "")
                    if content:
                        full_response_parts.append(content)
                elif ct == "complete":
                    content = chunk.get("content", "")
                    if content:
                        full_response_parts.append(content)
                elif ct == "error":
                    error_occurred = True
                yield chunk
        except Exception:
            error_occurred = True
            raise
        finally:
            # 记录 response（静默失败，不影响异常传播）
            duration_ms = (time.time() - start_time) * 1000
            full_response = "".join(full_response_parts)
            try:
                flow_logger = get_stream_flow_logger()
                flow_logger.log_llm_response(
                    trace_id=tid,
                    response=full_response,
                    duration_ms=duration_ms,
                    endpoint=f"/stream/{self._scene}",
                    model_or_app_id=kwargs.get("bot_id") or kwargs.get("app_id"),
                )
                # 如果发生错误，额外记录错误状态
                if error_occurred and not full_response:
                    flow_logger.log_error(
                        trace_id=tid,
                        error_message="LLM 调用失败或无响应",
                        endpoint=f"/stream/{self._scene}",
                    )
            except Exception as e:
                logger.debug("stream_flow log_llm_response 静默失败: %s", e)

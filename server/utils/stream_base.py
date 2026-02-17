#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口公共基础设施

提取5个分析接口流式生成器的共性代码：
- Bot ID 解析
- LLM 缓存读写
- 流式循环（SSE 事件生成）
- 错误处理与日志
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

from server.utils.stream_cache_helper import (
    get_llm_cache, set_llm_cache,
    compute_input_data_hash, LLM_CACHE_TTL
)

logger = logging.getLogger(__name__)


def resolve_bot_id(
    request_bot_id: Optional[str],
    config_key: str,
    env_key: str,
    get_config_from_db_only=None
) -> str:
    """
    按优先级解析 Bot ID：请求参数 > 数据库配置 > 环境变量
    """
    import os

    if request_bot_id:
        return request_bot_id

    if get_config_from_db_only:
        try:
            db_bot_id = get_config_from_db_only(config_key)
            if db_bot_id:
                return db_bot_id
        except Exception:
            pass

    return os.getenv(env_key, "")


async def stream_with_cache(
    *,
    analysis_type: str,
    input_data: dict,
    format_func,
    bot_id: str,
    request_id: str = "",
    stream_logger=None,
) -> AsyncGenerator[str, None]:
    """
    通用的 LLM 流式调用（含缓存、SSE 输出、日志）。

    Args:
        analysis_type: 分析类型名称（用于日志和缓存 key）
        input_data: 已构建好的输入数据
        format_func: 格式化函数，将 input_data 转为 LLM 文本
        bot_id: Coze Bot ID
        request_id: 请求追踪 ID
        stream_logger: 可选的流式调用日志器
    """
    from server.services.llm_service_factory import LLMServiceFactory

    # 1. 格式化
    formatted_data = format_func(input_data)

    # 2. 缓存检查
    cache_key = compute_input_data_hash(formatted_data)
    cached = await get_llm_cache(cache_key)
    if cached:
        logger.info(f"[{analysis_type}] LLM 缓存命中 key={cache_key[:16]}...")
        yield f"data: {json.dumps({'type': 'progress', 'content': cached}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'complete', 'content': ''}, ensure_ascii=False)}\n\n"
        return

    # 3. 创建 LLM 服务
    try:
        llm_service = LLMServiceFactory.get_service(bot_id=bot_id)
    except Exception as e:
        logger.error(f"[{analysis_type}] LLM 服务创建失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': f'LLM服务创建失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        return

    # 4. 流式调用
    full_content = ""
    start_time = time.time()
    try:
        async for result in llm_service.stream_analysis(formatted_data):
            if isinstance(result, dict):
                content = result.get("content", "")
            else:
                content = str(result)
            if content:
                full_content += content
                yield f"data: {json.dumps({'type': 'progress', 'content': content}, ensure_ascii=False)}\n\n"

        # 5. 写缓存
        if full_content:
            await set_llm_cache(cache_key, full_content, ttl=LLM_CACHE_TTL)

        yield f"data: {json.dumps({'type': 'complete', 'content': ''}, ensure_ascii=False)}\n\n"

        elapsed = time.time() - start_time
        logger.info(f"[{analysis_type}] 流式完成 {len(full_content)}字 {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"[{analysis_type}] 流式调用异常: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': f'流式调用异常: {str(e)}'}, ensure_ascii=False)}\n\n"

    # 6. 异步日志
    if stream_logger and full_content:
        try:
            await stream_logger.log_async(
                analysis_type=analysis_type,
                request_id=request_id,
                input_data=input_data,
                output_content=full_content,
                duration=time.time() - start_time,
            )
        except Exception:
            pass

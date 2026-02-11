#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口调用记录服务 - 异步写入，不影响业务性能

使用方式：
    from server.services.stream_call_logger import get_stream_call_logger
    logger = get_stream_call_logger()
    logger.log_async(
        trace_id="xxx",
        function_type="marriage",
        frontend_api="/api/v1/bazi/marriage-analysis/stream",
        frontend_input={...},
        input_data="...",
        llm_output="...",
        api_total_ms=1234,
        input_data_gen_ms=200,
        llm_first_token_ms=800,
        llm_total_ms=5000,
    )
"""

import logging
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from server.db.stream_call_log_dao import StreamCallLogDAO

logger = logging.getLogger(__name__)


class StreamCallLogger:
    """流式接口调用记录服务（异步写入）"""

    # 单例
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="stream_call_log")
        self._initialized = True
        logger.info("[StreamCallLogger] 初始化完成")

    def log_async(
        self,
        function_type: str,
        frontend_api: str,
        frontend_input: Dict[str, Any],
        input_data: str = '',
        llm_output: str = '',
        api_total_ms: Optional[int] = None,
        input_data_gen_ms: Optional[int] = None,
        llm_first_token_ms: Optional[int] = None,
        llm_total_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        cache_hit: bool = False,
        bot_id: Optional[str] = None,
        llm_platform: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """
        异步记录流式接口调用（即发即忘，不阻塞业务）

        Args:
            function_type: 场景类型（marriage/wealth/children/health/general/desk_fengshui/face 等）
            frontend_api: 前端调用的端点路径
            frontend_input: 用户入参
            input_data: 给大模型的结构化八字数据（JSON 字符串）
            llm_output: 大模型完整返回内容
            api_total_ms: 接口总耗时（毫秒）
            input_data_gen_ms: 数据编排 + 格式化耗时（毫秒）
            llm_first_token_ms: 大模型首 token 耗时（毫秒）
            llm_total_ms: 大模型总耗时（毫秒）
            status: 状态（success / failed / cache_hit）
            error_message: 错误详情
            cache_hit: 是否命中缓存
            bot_id: Bot ID
            llm_platform: 大模型平台（coze / bailian）
            trace_id: 请求追踪 ID，不传则自动生成
        """
        _trace_id = trace_id or str(uuid.uuid4())
        self.executor.submit(
            self._write_sync,
            _trace_id, function_type, frontend_api,
            frontend_input, input_data, llm_output,
            api_total_ms, input_data_gen_ms, llm_first_token_ms, llm_total_ms,
            status, error_message, cache_hit,
            bot_id, llm_platform,
        )

    def _write_sync(
        self,
        trace_id: str,
        function_type: str,
        frontend_api: str,
        frontend_input: Dict[str, Any],
        input_data: str,
        llm_output: str,
        api_total_ms: Optional[int],
        input_data_gen_ms: Optional[int],
        llm_first_token_ms: Optional[int],
        llm_total_ms: Optional[int],
        status: str,
        error_message: Optional[str],
        cache_hit: bool,
        bot_id: Optional[str],
        llm_platform: Optional[str],
    ):
        """在后台线程中同步写入数据库"""
        try:
            StreamCallLogDAO.insert(
                trace_id=trace_id,
                function_type=function_type,
                frontend_api=frontend_api,
                frontend_input=frontend_input,
                input_data=input_data,
                llm_output=llm_output,
                api_total_ms=api_total_ms,
                input_data_gen_ms=input_data_gen_ms,
                llm_first_token_ms=llm_first_token_ms,
                llm_total_ms=llm_total_ms,
                status=status,
                error_message=error_message,
                cache_hit=cache_hit,
                bot_id=bot_id,
                llm_platform=llm_platform,
            )
        except Exception as e:
            logger.error(f"[StreamCallLogger] 写入失败: {e}", exc_info=True)

    def shutdown(self):
        """关闭服务"""
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("[StreamCallLogger] 服务已关闭")


# 全局单例
_instance: Optional[StreamCallLogger] = None


def get_stream_call_logger() -> StreamCallLogger:
    """获取 StreamCallLogger 单例"""
    global _instance
    if _instance is None:
        _instance = StreamCallLogger()
    return _instance

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户交互记录服务 - 异步记录，不影响业务性能
"""

import logging
import uuid
import json
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from server.db.user_interaction_dao import UserInteractionDAO
from server.db.mongo_interaction_dao import get_mongo_dao

logger = logging.getLogger(__name__)


class UserInteractionLogger:
    """用户交互记录服务（异步）"""
    
    # 单例模式
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UserInteractionLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化记录服务"""
        if hasattr(self, '_initialized'):
            return
        
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="interaction_logger")
        self.mysql_dao = UserInteractionDAO()
        self.mongo_dao = get_mongo_dao()
        self._initialized = True
        logger.info("[UserInteractionLogger] 初始化完成")
    
    def log_function_usage_async(
        self,
        function_type: str,
        function_name: str,
        frontend_api: str,
        frontend_input: Dict[str, Any],
        input_data: Dict[str, Any],
        llm_output: str,
        llm_api: Optional[str] = None,
        api_response_time_ms: Optional[int] = None,
        llm_first_token_time_ms: Optional[int] = None,
        llm_total_time_ms: Optional[int] = None,
        round_number: int = 1,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        bot_id: Optional[str] = None,
        token_count: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        performance_timeline: Optional[list] = None,
        **kwargs
    ):
        """
        异步记录功能使用（不阻塞业务）
        
        Args:
            function_type: 功能类型（marriage/wealth/children/health/general/chat）
            function_name: 功能名称
            frontend_api: 前端调用的接口
            frontend_input: 前端输入（完整）
            input_data: 给大模型的input_data（完整对象）
            llm_output: 大模型输出（完整内容）
            llm_api: 给大模型数据的接口
            api_response_time_ms: 接口总响应时间（毫秒）
            llm_first_token_time_ms: 大模型第一个token响应时间（毫秒）
            llm_total_time_ms: 大模型总响应时间（毫秒）
            round_number: 轮次（多轮对话时递增）
            user_id: 用户ID
            session_id: 会话ID
            model_name: 模型名称
            model_version: 模型版本
            bot_id: Coze Bot ID
            token_count: Token使用量
            status: 状态（success/failed/partial）
            error_message: 错误信息
            performance_timeline: 性能时间线
        """
        # 提交到线程池异步执行，不等待结果
        future = self.executor.submit(
            self._log_function_usage_sync,
            function_type, function_name, frontend_api,
            frontend_input, input_data, llm_output, llm_api,
            api_response_time_ms, llm_first_token_time_ms,
            llm_total_time_ms, round_number, user_id, session_id,
            model_name, model_version, bot_id, token_count,
            status, error_message, performance_timeline, **kwargs
        )
        # 不等待结果，避免阻塞
        return future
    
    def _log_function_usage_sync(
        self,
        function_type: str,
        function_name: str,
        frontend_api: str,
        frontend_input: Dict[str, Any],
        input_data: Dict[str, Any],
        llm_output: str,
        llm_api: Optional[str],
        api_response_time_ms: Optional[int],
        llm_first_token_time_ms: Optional[int],
        llm_total_time_ms: Optional[int],
        round_number: int,
        user_id: Optional[str],
        session_id: Optional[str],
        model_name: Optional[str],
        model_version: Optional[str],
        bot_id: Optional[str],
        token_count: Optional[int],
        status: str,
        error_message: Optional[str],
        performance_timeline: Optional[list],
        **kwargs
    ):
        """同步记录（在后台线程执行）"""
        try:
            # 1. 生成记录ID
            record_id = str(uuid.uuid4())
            
            # 2. 准备摘要（用于MySQL快速查询）
            frontend_input_summary = json.dumps(frontend_input, ensure_ascii=False)[:500]
            input_data_summary = json.dumps(input_data, ensure_ascii=False)[:500]
            llm_output_summary = llm_output[:500] if llm_output else ""
            
            # 3. 保存到MongoDB（完整数据）
            mongo_doc_id = None
            try:
                performance = {
                    'api_response_time_ms': api_response_time_ms,
                    'llm_first_token_time_ms': llm_first_token_time_ms,
                    'llm_total_time_ms': llm_total_time_ms,
                    'token_count': token_count,
                    'timeline': performance_timeline or []
                }
                
                metadata = {
                    'model_name': model_name,
                    'model_version': model_version,
                    'bot_id': bot_id,
                    'frontend_api': frontend_api,
                    'llm_api': llm_api,
                    'round_number': round_number,
                    'streaming': kwargs.get('streaming', False)
                }
                
                mongo_doc_id = self.mongo_dao.save_details(
                    record_id=record_id,
                    session_id=session_id,
                    user_id=user_id or 'anonymous',
                    function_type=function_type,
                    function_name=function_name,
                    frontend_input=frontend_input,
                    input_data=input_data,
                    llm_output=llm_output,
                    performance=performance,
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"[UserInteractionLogger] MongoDB保存失败: {e}", exc_info=True)
                # MongoDB失败不影响MySQL保存
            
            # 4. 保存到MySQL（元数据）
            try:
                self.mysql_dao.save_record(
                    record_id=record_id,
                    user_id=user_id or 'anonymous',
                    session_id=session_id,
                    function_type=function_type,
                    function_name=function_name,
                    frontend_api=frontend_api,
                    llm_api=llm_api,
                    round_number=round_number,
                    frontend_input_summary=frontend_input_summary,
                    input_data_summary=input_data_summary,
                    llm_output_summary=llm_output_summary,
                    mongo_doc_id=mongo_doc_id,
                    api_response_time_ms=api_response_time_ms,
                    llm_first_token_time_ms=llm_first_token_time_ms,
                    llm_total_time_ms=llm_total_time_ms,
                    token_count=token_count,
                    model_name=model_name,
                    model_version=model_version,
                    bot_id=bot_id,
                    status=status,
                    error_message=error_message
                )
            except Exception as e:
                logger.error(f"[UserInteractionLogger] MySQL保存失败: {e}", exc_info=True)
            
            logger.debug(f"[UserInteractionLogger] 记录保存完成: record_id={record_id}, function_type={function_type}")
            
        except Exception as e:
            logger.error(f"[UserInteractionLogger] 记录保存异常: {e}", exc_info=True)
    
    def shutdown(self):
        """关闭记录服务"""
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("[UserInteractionLogger] 记录服务已关闭")


# 全局单例
_logger_instance: Optional[UserInteractionLogger] = None


def get_user_interaction_logger() -> UserInteractionLogger:
    """获取用户交互记录服务实例（单例）"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = UserInteractionLogger()
    return _logger_instance


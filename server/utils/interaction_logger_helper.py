#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户交互记录辅助函数 - 简化API集成
"""

import time
from typing import Dict, Any, Optional
from server.services.user_interaction_logger import get_user_interaction_logger


class InteractionLoggerHelper:
    """交互记录辅助类"""
    
    def __init__(self, function_type: str, function_name: str, frontend_api: str):
        """
        初始化辅助类
        
        Args:
            function_type: 功能类型（marriage/wealth/children/health/general/chat）
            function_name: 功能名称
            frontend_api: 前端API路径
        """
        self.function_type = function_type
        self.function_name = function_name
        self.frontend_api = frontend_api
        self.api_start_time = None
        self.llm_start_time = None
        self.llm_first_token_time = None
        self.frontend_input = {}
        self.input_data = {}
        self.llm_output_chunks = []
        self.bot_id = None
    
    def start(self, frontend_input: Dict[str, Any]):
        """开始记录（在API开始时调用）"""
        self.api_start_time = time.time()
        self.frontend_input = frontend_input
    
    def set_input_data(self, input_data: Dict[str, Any]):
        """设置input_data（在构建input_data后调用）"""
        self.input_data = input_data
    
    def set_bot_id(self, bot_id: str):
        """设置bot_id"""
        self.bot_id = bot_id
    
    def start_llm(self):
        """开始LLM调用（在调用LLM前调用）"""
        self.llm_start_time = time.time()
    
    def record_first_token(self):
        """记录第一个token（在收到第一个token时调用）"""
        if self.llm_first_token_time is None and self.llm_start_time:
            self.llm_first_token_time = time.time()
    
    def append_output(self, content: str):
        """追加输出内容（在收到每个chunk时调用）"""
        self.llm_output_chunks.append(content)
    
    def finish(self, status: str = 'success', error_message: Optional[str] = None):
        """
        完成记录（在API结束时调用）
        
        Args:
            status: 状态（success/failed/partial）
            error_message: 错误信息（如果有）
        """
        if self.api_start_time is None:
            return
        
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - self.api_start_time) * 1000)
        llm_total_time_ms = int((api_end_time - self.llm_start_time) * 1000) if self.llm_start_time else None
        llm_output = ''.join(self.llm_output_chunks)
        
        llm_first_token_time_ms = None
        if self.llm_first_token_time and self.llm_start_time:
            llm_first_token_time_ms = int((self.llm_first_token_time - self.llm_start_time) * 1000)
        
        # 异步记录（不等待结果）
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type=self.function_type,
            function_name=self.function_name,
            frontend_api=self.frontend_api,
            frontend_input=self.frontend_input,
            input_data=self.input_data,
            llm_output=llm_output,
            llm_api='coze_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=llm_first_token_time_ms,
            llm_total_time_ms=llm_total_time_ms,
            round_number=1,
            bot_id=self.bot_id,
            status=status,
            error_message=error_message,
            streaming=True
        )


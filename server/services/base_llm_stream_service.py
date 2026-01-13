#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 流式服务基类

定义统一的 LLM 流式服务接口，支持 Coze 和百炼平台。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator


class BaseLLMStreamService(ABC):
    """LLM 流式服务基类 - 定义统一接口"""
    
    @abstractmethod
    async def stream_analysis(
        self,
        prompt: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成分析结果（通用方法）
        
        Args:
            prompt: 提示词
            trace_id: 请求追踪ID（可选，用于日志关联）
            **kwargs: 其他参数（如 bot_id, app_id 等）
            
        Yields:
            dict: 包含 type 和 content 的字典
                - type: 'progress' 或 'complete' 或 'error'
                - content: 内容文本
        """
        pass
    
    async def stream_action_suggestions(
        self,
        yi_list: list,
        ji_list: list,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成行动建议
        
        Args:
            yi_list: 宜事项列表
            ji_list: 忌事项列表
            **kwargs: 其他参数
            
        Yields:
            dict: 包含 type 和 content 的字典
                - type: 'progress' 或 'complete' 或 'error'
                - content: 内容文本
        """
        # 构建 prompt
        yi_text = '、'.join(yi_list) if yi_list else '无'
        ji_text = '、'.join(ji_list) if ji_list else '无'
        prompt = f"""宜：{yi_text}
忌：{ji_text}"""
        
        # 调用通用方法
        async for chunk in self.stream_analysis(prompt, **kwargs):
            yield chunk

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze 流式服务
用于调用 Coze API 生成流式响应（SSE格式）
"""

import os
import sys
import json
import requests
from typing import Dict, Any, Optional, AsyncGenerator
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class CozeStreamService:
    """Coze 流式服务"""
    
    def __init__(self, access_token: Optional[str] = None, bot_id: Optional[str] = None,
                 api_base: str = "https://api.coze.cn"):
        """
        初始化Coze流式服务
        
        Args:
            access_token: Coze Access Token，如果为None则从环境变量获取
            bot_id: Coze Bot ID，如果为None则从环境变量获取
            api_base: Coze API 基础URL，默认为 https://api.coze.cn
        """
        self.access_token = access_token or os.getenv("COZE_ACCESS_TOKEN")
        self.bot_id = bot_id or os.getenv("COZE_BOT_ID")
        self.api_base = api_base.rstrip('/')
        
        if not self.access_token:
            raise ValueError("需要提供 Coze Access Token 或设置环境变量 COZE_ACCESS_TOKEN")
        
        if not self.bot_id:
            raise ValueError("需要提供 Coze Bot ID 或设置环境变量 COZE_BOT_ID")
        
        # 设置请求头
        if self.access_token.startswith("pat_"):
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        
        # 也准备一个使用 PAT 前缀的认证头
        self.headers_pat = {
            "Authorization": f"PAT {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def stream_action_suggestions(
        self,
        yi_list: list,
        ji_list: list,
        bot_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成行动建议
        
        Args:
            yi_list: 宜事项列表
            ji_list: 忌事项列表
            bot_id: Bot ID（可选，默认使用初始化时的bot_id）
            
        Yields:
            dict: 包含 type 和 content 的字典
                - type: 'progress' 或 'complete' 或 'error'
                - content: 内容文本
        """
        used_bot_id = bot_id or self.bot_id
        
        # 构建提示词
        yi_text = '、'.join(yi_list) if yi_list else '无'
        ji_text = '、'.join(ji_list) if ji_list else '无'
        
        prompt = f"""请将以下万年历的宜忌信息美化成两段话，每段不超过60字：

宜：{yi_text}
忌：{ji_text}

要求：
1. 宜的内容美化成一段话，不超过60字
2. 忌的内容美化成一段话，不超过60字
3. 语言要自然流畅，符合日常表达习惯
4. 直接输出两段话，不需要额外说明

格式：
宜：[美化后的内容]
忌：[美化后的内容]"""
        
        # Coze API 端点（流式）
        possible_endpoints = [
            "/open_api/v2/chat",  # Coze v2 标准端点
            "/open_api/v2/chat/completions",
            "/v2/chat",
        ]
        
        # 流式 payload 格式
        payload = {
            "bot_id": str(used_bot_id),
            "user": "daily_fortune",
            "query": prompt,
            "stream": True
        }
        
        last_error = None
        
        # 尝试不同的端点
        for endpoint in possible_endpoints:
            url = f"{self.api_base}{endpoint}"
            
            # 尝试两种认证方式
            for headers_to_use in [self.headers, self.headers_pat]:
                try:
                    # 发送流式请求（在线程池中运行，避免阻塞）
                    import asyncio
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: requests.post(
                            url,
                            headers=headers_to_use,
                            json=payload,
                            stream=True,
                            timeout=60
                        )
                    )
                    
                    if response.status_code == 200:
                        # 处理流式响应
                        buffer = ""
                        has_content = False
                        for line in response.iter_lines():
                            if not line:
                                continue
                            
                            # 让出控制权，避免阻塞
                            await asyncio.sleep(0)
                            
                            line_str = line.decode('utf-8')
                            
                            # SSE 格式：data: {...} 或 data:{...} 或 data {...}
                            data_str = None
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]  # 移除 "data: " 前缀
                            elif line_str.startswith('data:'):
                                data_str = line_str[5:]  # 移除 "data:" 前缀（没有空格）
                            elif line_str.startswith('data'):
                                # 处理 data{...} 格式（没有冒号）
                                data_str = line_str[4:]  # 移除 "data" 前缀
                            
                            if data_str:
                                if data_str.strip() == '[DONE]':
                                    # 流结束
                                    if buffer.strip():
                                        yield {
                                            'type': 'complete',
                                            'content': buffer.strip()
                                        }
                                    else:
                                        yield {
                                            'type': 'error',
                                            'content': 'Coze API 返回空内容，请检查Bot配置和提示词'
                                        }
                                    return
                                
                                try:
                                    data = json.loads(data_str)
                                    
                                    # 跳过技术性消息（如 generate_answer_finish）
                                    if data.get('msg_type') in ['generate_answer_finish', 'conversation_finish']:
                                        continue
                                    
                                    # 提取内容（根据Coze API响应格式）
                                    content = self._extract_content_from_response(data)
                                    if content:
                                        # 过滤掉提示词和指令文本
                                        if self._is_prompt_or_instruction(content):
                                            continue
                                        
                                        has_content = True
                                        buffer += content
                                        yield {
                                            'type': 'progress',
                                            'content': content
                                        }
                                except json.JSONDecodeError as e:
                                    # 忽略无效的JSON，但记录日志
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.debug(f"JSON解析失败: {e}, 原始数据: {data_str[:100]}")
                                    continue
                            
                            # 直接JSON格式
                            elif line_str.startswith('{'):
                                try:
                                    data = json.loads(line_str)
                                    
                                    # 跳过技术性消息
                                    if data.get('msg_type') in ['generate_answer_finish', 'conversation_finish']:
                                        continue
                                    
                                    content = self._extract_content_from_response(data)
                                    if content:
                                        # 过滤掉提示词和指令文本
                                        if self._is_prompt_or_instruction(content):
                                            continue
                                        
                                        has_content = True
                                        buffer += content
                                        yield {
                                            'type': 'progress',
                                            'content': content
                                        }
                                except json.JSONDecodeError:
                                    continue
                        
                        # 流结束
                        if has_content and buffer.strip():
                            yield {
                                'type': 'complete',
                                'content': buffer.strip()
                            }
                        else:
                            # 如果没有收到任何内容，返回错误
                            yield {
                                'type': 'error',
                                'content': f'Coze API 返回空内容。响应状态: {response.status_code}，请检查Bot配置、提示词和API端点'
                            }
                        return
                    
                    elif response.status_code in [401, 403]:
                        last_error = f"认证失败: {response.text[:200]}"
                        continue
                    elif response.status_code == 404:
                        # 端点不存在，尝试下一个
                        break
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        continue
                        
                except Exception as e:
                    last_error = str(e)
                    continue
        
        # 所有尝试都失败
        yield {
            'type': 'error',
            'content': f"Coze API 调用失败: {last_error or '未知错误'}"
        }
    
    def _extract_content_from_response(self, data: Dict[str, Any]) -> str:
        """
        从Coze API响应中提取内容
        
        Args:
            data: API响应数据
            
        Returns:
            str: 提取的内容文本
        """
        # 尝试多种可能的响应格式
        content = None
        
        # 格式1: data.content 或 data.text
        if 'data' in data and isinstance(data['data'], dict):
            content = data['data'].get('content') or data['data'].get('text') or data['data'].get('message')
        
        # 格式2: content 或 text（注意：message可能是字典，需要特殊处理）
        if not content:
            content = data.get('content') or data.get('text')
            # 如果message是字符串，才使用它
            message_val = data.get('message')
            if not content and isinstance(message_val, str):
                content = message_val
        
        # 格式3: choices[0].delta.content (类似OpenAI格式)
        if not content and 'choices' in data:
            choices = data.get('choices', [])
            if choices and isinstance(choices[0], dict):
                delta = choices[0].get('delta', {})
                content = delta.get('content') or delta.get('text')
        
        # 格式4: event.data.content
        if not content and 'event' in data:
            event_data = data.get('event', {})
            if isinstance(event_data, dict) and 'data' in event_data:
                content = event_data['data'].get('content') or event_data['data'].get('text')
        
        # 格式5: result.content (Coze常见格式)
        if not content and 'result' in data:
            result = data.get('result', {})
            if isinstance(result, dict):
                content = result.get('content') or result.get('text') or result.get('message')
        
        # 格式6: message.content (Coze v2 API格式: {"event":"message","message":{"content":"..."}})
        if not content and 'message' in data:
            message = data.get('message', {})
            if isinstance(message, dict):
                # 确保提取的是字符串内容，不是整个对象
                content = message.get('content')
                if content and not isinstance(content, str):
                    # 如果content不是字符串，尝试转换为字符串
                    content = str(content) if content else None
                if not content:
                    content = message.get('text') or message.get('message')
                    if content and not isinstance(content, str):
                        content = str(content) if content else None
        
        # 格式7: 直接是字符串
        if not content and isinstance(data, str):
            content = data
        
        # 调试日志（可选，生产环境可关闭）
        if not content:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"无法从Coze响应中提取内容，原始数据: {data}")
        
        return content or ''
    
    def _is_prompt_or_instruction(self, text: str) -> bool:
        """
        判断文本是否是提示词或指令（不应该显示给用户）
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 如果是提示词或指令返回True，否则返回False
        """
        if not text or len(text.strip()) < 5:
            return False
        
        # 提示词和指令的关键词
        prompt_keywords = [
            '再润色',
            '如何用',
            '用对偶',
            '用诗词',
            '美化万年历',
            '请再将其',
            '请将以下',
            '要求：',
            '格式：',
            '输出格式',
            'msg_type',
            'generate_answer_finish',
            'finish_reason',
            'from_module',
            'from_unit'
        ]
        
        text_lower = text.lower()
        for keyword in prompt_keywords:
            if keyword in text:
                return True
        
        # 检查是否包含JSON结构（技术性消息）
        if '{' in text and ('msg_type' in text or 'finish_reason' in text):
            return True
        
        return False


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
        
        # 设置请求头（参考 fortune_llm_client.py）
        if self.access_token.startswith("pat_"):
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        
        # 也准备一个使用 PAT 前缀的认证头
        self.headers_pat = {
            "Authorization": f"PAT {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
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
                                        # 检查 buffer 中是否包含错误消息
                                        if self._is_error_response(buffer.strip()):
                                            import logging
                                            logger = logging.getLogger(__name__)
                                            logger.error(f"Coze Bot 返回错误响应 (stream_action_suggestions): {buffer.strip()[:200]}")
                                            yield {
                                                'type': 'error',
                                                'content': 'Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。'
                                            }
                                        else:
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
                                        # 检测是否为错误消息
                                        if self._is_error_response(content):
                                            import logging
                                            logger = logging.getLogger(__name__)
                                            logger.warning(f"Coze Bot 返回错误消息: {content[:100]}... (stream_action_suggestions)")
                                            # 标记有错误，但不立即返回，继续处理其他内容
                                            continue
                                        
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
                                        # 检测是否为错误消息
                                        if self._is_error_response(content):
                                            import logging
                                            logger = logging.getLogger(__name__)
                                            logger.warning(f"Coze Bot 返回错误消息: {content[:100]}... (stream_action_suggestions)")
                                            # 标记有错误，但不立即返回，继续处理其他内容
                                            continue
                                        
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
                            # 检查 buffer 中是否包含错误消息
                            if self._is_error_response(buffer.strip()):
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error(f"Coze Bot 返回错误响应 (stream_action_suggestions): {buffer.strip()[:200]}")
                                yield {
                                    'type': 'error',
                                    'content': 'Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。'
                                }
                                return
                            
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
    
    async def stream_custom_analysis(
        self,
        prompt: str,
        bot_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成自定义分析（通用方法）
        
        Args:
            prompt: 提示词
            bot_id: Bot ID（可选，默认使用初始化时的bot_id）
            
        Yields:
            dict: 包含 type 和 content 的字典
                - type: 'progress' 或 'complete' 或 'error'
                - content: 内容文本
        """
        # ⚠️ 关键修复：每次调用时重新读取环境变量（支持热更新环境变量）
        current_access_token = os.getenv("COZE_ACCESS_TOKEN") or self.access_token
        if not current_access_token:
            yield {
                'type': 'error',
                'content': 'Coze Access Token 未设置，请检查环境变量 COZE_ACCESS_TOKEN'
            }
            return
        
        # 更新 headers（使用最新的 Token）
        if current_access_token.startswith("pat_"):
            headers_to_use = {
                "Authorization": f"Bearer {current_access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        else:
            headers_to_use = {
                "Authorization": f"Bearer {current_access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        headers_pat_to_use = {
            "Authorization": f"PAT {current_access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        used_bot_id = bot_id or self.bot_id
        
        if not used_bot_id:
            yield {
                'type': 'error',
                'content': 'Coze Bot ID 未设置'
            }
            return
        
        # Coze API 端点（流式）- 使用 v3 API（参考 fortune_llm_client.py）
        possible_endpoints = [
            "/v3/chat",  # Coze v3 标准端点
        ]
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 流式 payload 格式（使用 additional_messages 格式，参考 fortune_llm_client.py）
        payload = {
            "bot_id": str(used_bot_id),
            "user_id": "system",
            "additional_messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "content_type": "text"
                }
            ],
            "stream": True
        }
        
        logger.info(f"🚀 准备调用 Coze API: Bot ID={used_bot_id}, Prompt长度={len(prompt)}")
        logger.info(f"📝 Prompt前1000字符: {prompt[:1000]}...")
        logger.info(f"📦 发送的 payload 结构: bot_id, user_id, additional_messages, stream")
        
        last_error = None
        
        # 尝试不同的端点
        for endpoint in possible_endpoints:
            url = f"{self.api_base}{endpoint}"
            
            # 尝试两种认证方式
            for headers_to_use in [self.headers, self.headers_pat]:
                try:
                    # 发送流式请求（在线程池中运行，避免阻塞）
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
                    
                    # ⚠️ 检查响应 Content-Type
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 如果响应是 JSON 格式（可能是错误响应），先检查
                    if 'application/json' in content_type:
                        try:
                            error_data = response.json()
                            error_code = error_data.get('code', 0)
                            error_msg = error_data.get('msg', '未知错误')
                            
                            # Token 错误（code: 4101）
                            if error_code == 4101:
                                logger.error(f"❌ Coze API Token 错误 (code: {error_code}): {error_msg}")
                                yield {
                                    'type': 'error',
                                    'content': f'Coze API Token 配置错误（错误码: {error_code}）。请检查环境变量 COZE_ACCESS_TOKEN 是否正确配置。错误信息: {error_msg}'
                                }
                                return
                            
                            # 其他错误
                            logger.error(f"❌ Coze API 返回错误 (code: {error_code}): {error_msg}")
                            yield {
                                'type': 'error',
                                'content': f'Coze API 错误（错误码: {error_code}）: {error_msg}'
                            }
                            return
                        except:
                            # JSON 解析失败，继续处理为 SSE 流
                            pass
                    
                    if response.status_code == 200:
                        # 处理流式响应（重构：参考fortune_llm_client.py的实现）
                        import logging
                        logger = logging.getLogger(__name__)
                        
                        buffer = ""
                        sent_length = 0  # 跟踪已发送的内容长度（优化方案2.2）
                        has_content = False
                        current_event = None  # 保存当前事件类型
                        stream_ended = False
                        line_count = 0  # 记录行数
                        
                        logger.info(f"📡 开始处理 Coze API 流式响应 (Bot ID: {used_bot_id})")
                        logger.info(f"📋 请求URL: {url}")
                        logger.info(f"📋 请求Headers: Authorization={headers_to_use.get('Authorization', '')[:20]}..., Accept={headers_to_use.get('Accept', '')}")
                        logger.info(f"📋 请求Payload: bot_id={payload.get('bot_id')}, stream={payload.get('stream')}, prompt_length={len(prompt)}")
                        
                        # 按行处理SSE流（参考fortune_llm_client.py的行处理逻辑）
                        for line in response.iter_lines():
                            if not line:
                                continue
                            
                            await asyncio.sleep(0)
                            
                            line_str = line.decode('utf-8').strip()
                            if not line_str:
                                continue
                            
                            line_count += 1
                            # 记录前20行，帮助调试（增加行数）
                            if line_count <= 20:
                                logger.info(f"📨 SSE行 {line_count}: {line_str[:200]}")
                            
                            # 处理 event: 行（新增：Coze API的事件在event行中）
                            if line_str.startswith('event:'):
                                current_event = line_str[6:].strip()
                                continue
                            
                            # 处理 data: 行
                            elif line_str.startswith('data:'):
                                data_str = line_str[5:].strip()
                                
                                if data_str == '[DONE]':
                                    # 流结束
                                    if has_content and buffer.strip():
                                        # 检查 buffer 中是否包含错误消息
                                        if self._is_error_response(buffer.strip()):
                                            logger.error(f"Coze Bot 返回错误响应 (Bot ID: {used_bot_id}): {buffer.strip()[:200]}")
                                            yield {
                                                'type': 'error',
                                                'content': 'Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。'
                                            }
                                        else:
                                            yield {
                                                'type': 'complete',
                                                'content': buffer.strip()
                                            }
                                    else:
                                        yield {
                                            'type': 'error',
                                            'content': 'Coze API 返回空内容，请检查Bot配置和提示词'
                                        }
                                    stream_ended = True
                                    break
                                
                                try:
                                    data = json.loads(data_str)
                                    
                                    # 防御性检查：确保 data 是字典
                                    if not isinstance(data, dict):
                                        logger.warning(f"⚠️ SSE数据不是字典: {type(data)}, 数据: {data_str[:100]}")
                                        continue
                                    
                                    # 使用 current_event 或 data 中的 event 字段
                                    event_type = current_event or data.get('event', '')
                                    msg_type = data.get('type', '')
                                    status = data.get('status', '')
                                    
                                    logger.debug(f"📨 处理SSE数据: event={event_type}, type={msg_type}, status={status}, keys={list(data.keys())[:10]}")
                                    
                                    # 优先检查status字段
                                    if status == 'failed':
                                        last_error = data.get('last_error', {})
                                        error_code = last_error.get('code', 0)
                                        error_msg = last_error.get('msg', 'Bot处理失败')
                                        logger.error(f"❌ Bot处理失败（通过status字段）: code={error_code}, msg={error_msg}")
                                        yield {
                                            'type': 'error',
                                            'content': f'Bot处理失败: {error_msg} (错误码: {error_code})'
                                        }
                                        stream_ended = True
                                        break
                                    
                                    # 处理 conversation.message.delta 事件（增量内容）
                                    if event_type == 'conversation.message.delta':
                                        # 跳过非answer类型
                                        if msg_type in ['knowledge_recall', 'verbose']:
                                            logger.debug(f"⏭️ 跳过 {msg_type} 类型的delta消息")
                                            continue
                                        
                                        # ⚠️ 关键修复：Coze API 可能将内容放在 reasoning_content 字段而不是 content 字段
                                        content = data.get('content', '') or data.get('reasoning_content', '')
                                        
                                        # 增强日志：记录所有delta事件，即使content为空
                                        if not content:
                                            logger.debug(f"⚠️ Delta事件content和reasoning_content都为空: event={event_type}, type={msg_type}, data_keys={list(data.keys())[:10]}")
                                            # 记录所有可能的字段
                                            if 'reasoning_content' in data:
                                                logger.debug(f"⚠️ Delta事件有reasoning_content但为空: {data.get('reasoning_content', '')[:50]}")
                                        
                                        if content and isinstance(content, str):
                                            # 处理content可能是JSON字符串的情况
                                            try:
                                                if content.strip().startswith('{'):
                                                    parsed_content = json.loads(content)
                                                    if isinstance(parsed_content, dict):
                                                        # 如果是 knowledge_recall JSON，跳过
                                                        if parsed_content.get('msg_type') == 'knowledge_recall':
                                                            logger.debug("⏭️ 跳过 knowledge_recall JSON delta")
                                                            continue
                                                        # 尝试提取文本
                                                        text_content = parsed_content.get('text') or parsed_content.get('content') or parsed_content.get('message')
                                                        if text_content and isinstance(text_content, str):
                                                            content = text_content
                                            except (json.JSONDecodeError, AttributeError, ValueError):
                                                pass
                                            
                                            # 检测是否为错误消息
                                            if self._is_error_response(content):
                                                logger.warning(f"⚠️ Coze Bot 返回错误消息: {content[:100]}... (Bot ID: {used_bot_id})")
                                                continue
                                            
                                            # 过滤掉提示词和指令文本
                                            if self._is_prompt_or_instruction(content):
                                                logger.info(f"⚠️ 内容被过滤（提示词/指令）: {content[:50]}...")
                                                continue
                                            
                                            has_content = True
                                            buffer += content
                                            sent_length += len(content)  # 记录已发送长度（优化方案2.2）
                                            logger.debug(f"📤 Delta 内容: {len(content)}字符, 累计已发送: {sent_length}字符, Buffer总长度: {len(buffer)}字符")  # 优化方案2.3
                                            yield {
                                                'type': 'progress',
                                                'content': content
                                            }
                                        elif content:
                                            # content存在但不是字符串，记录日志
                                            logger.warning(f"⚠️ Delta事件content类型异常: {type(content)}, content={str(content)[:100]}")
                                        continue
                                    
                                    # 处理 conversation.message.completed 事件（完整消息）
                                    elif event_type == 'conversation.message.completed':
                                        # 对于 verbose 类型，直接跳过
                                        if msg_type == 'verbose':
                                            logger.info(f"⏭️ 跳过 verbose 类型消息（知识库召回/调试信息，不是Bot回答），content长度: {len(str(data.get('content', '')))}")
                                            continue
                                        
                                        # 跳过 knowledge_recall 类型的消息
                                        if msg_type == 'knowledge_recall':
                                            logger.info(f"⏭️ 跳过 {msg_type} 类型消息（知识库召回，不是Bot回答）")
                                            continue
                                        
                                        # ⚠️ 关键修复：如果没有收到 delta 事件，尝试从 completed 事件中提取内容（不限制 msg_type）
                                        # 只有在没有收到 delta 事件时才处理 completed 事件
                                        if not has_content:
                                            content = data.get('content', '')
                                            
                                            # ⚠️ 增强日志：记录所有相关信息
                                            logger.info(f"📝 conversation.message.completed 事件详情: msg_type={msg_type or '(无)'}, has_content={has_content}, content类型={type(content)}, content长度={len(str(content)) if content else 0}")
                                            if content:
                                                logger.info(f"📝 content预览: {str(content)[:200]}")
                                            logger.info(f"📝 完整data keys: {list(data.keys())}")
                                            
                                            # 尝试多种方式提取内容
                                            if not content:
                                                # content 为空，尝试从 data 中提取
                                                content = self._extract_content_from_response(data)
                                                logger.info(f"📝 使用 _extract_content_from_response 提取内容: 长度={len(str(content)) if content else 0}")
                                            
                                            if content:
                                                # 处理不同类型的 content
                                                if isinstance(content, str):
                                                    # 直接使用字符串内容
                                                    pass
                                                elif isinstance(content, dict):
                                                    # content 是字典，尝试提取文本
                                                    content = content.get('text') or content.get('content') or content.get('message') or str(content)
                                                else:
                                                    # 其他类型，转换为字符串
                                                    content = str(content)
                                            
                                            # ⚠️ 关键修复：如果没有收到任何 delta 事件，从 completed 事件中提取内容
                                            if content and isinstance(content, str) and len(content.strip()) > 10:
                                                logger.info(f"📝 收到完整消息（conversation.message.completed，未收到delta事件，使用completed内容）: msg_type={msg_type}, content长度={len(content)}")
                                                
                                                # 检查 content 是否是JSON字符串（需要解析）
                                                try:
                                                    if content.strip().startswith('{'):
                                                        parsed_content = json.loads(content)
                                                        if isinstance(parsed_content, dict):
                                                            # 如果是 knowledge_recall JSON，跳过
                                                            if parsed_content.get('msg_type') == 'knowledge_recall':
                                                                logger.info("⏭️ 跳过 knowledge_recall JSON内容")
                                                                continue
                                                            # 尝试提取文本内容
                                                            text_content = parsed_content.get('text') or parsed_content.get('content') or parsed_content.get('message')
                                                            if text_content and isinstance(text_content, str):
                                                                content = text_content
                                                except (json.JSONDecodeError, AttributeError, ValueError):
                                                    pass
                                                
                                                # 检测是否为错误消息
                                                if self._is_error_response(content):
                                                    logger.warning(f"⚠️ Coze Bot 返回错误消息: {content[:100]}... (Bot ID: {used_bot_id})")
                                                    continue
                                                
                                                # 过滤掉提示词和指令文本
                                                if self._is_prompt_or_instruction(content):
                                                    logger.info(f"⚠️ 内容被过滤（提示词/指令）: {content[:50]}...")
                                                    continue
                                                
                                                has_content = True
                                                buffer = content  # 使用完整内容替换 buffer
                                                sent_length = 0  # 重置已发送长度
                                                
                                                # 分段发送内容（避免一次性发送过长内容）
                                                chunk_size = 100  # 每次发送100字符
                                                for i in range(0, len(content), chunk_size):
                                                    chunk = content[i:i + chunk_size]
                                                    yield {
                                                        'type': 'progress',
                                                        'content': chunk
                                                    }
                                                    sent_length += len(chunk)
                                                
                                                logger.info(f"📤 已发送完整消息（从completed事件）: 总长度={len(content)}字符")
                                            else:
                                                logger.warning(f"⚠️ conversation.message.completed 事件中 content 为空或无效: msg_type={msg_type}, content类型={type(content)}, content长度={len(str(content)) if content else 0}")
                                                logger.warning(f"⚠️ 完整data内容: {json.dumps(data, ensure_ascii=False)[:500]}")
                                        else:
                                            # 如果已经收到 delta 事件，跳过 completed 事件避免重复
                                            logger.info(f"📝 收到完整消息（conversation.message.completed，已收到delta事件，跳过避免重复）: msg_type={msg_type}, buffer长度={len(buffer)}, 已发送长度={sent_length}")
                                        continue
                                    
                                    # 处理 conversation.chat.completed 事件（对话完成）
                                    elif event_type == 'conversation.chat.completed':
                                        logger.info(f"✅ 对话完成（conversation.chat.completed）: buffer长度={len(buffer)}, 已发送长度={sent_length}")  # 优化方案2.3
                                        if has_content and len(buffer) > sent_length:
                                            # 优化方案2.2：只发送新增部分（去重）
                                            new_content = buffer[sent_length:]
                                            logger.info(f"📤 发送完成消息: 新增内容长度={len(new_content)}字符")  # 优化方案2.3
                                            yield {
                                                'type': 'complete',
                                                'content': new_content.strip()
                                            }
                                        elif has_content and buffer.strip():
                                            # 如果已发送所有内容，发送空完成消息
                                            logger.info(f"📤 发送完成消息（无新增内容，已全部发送）")  # 优化方案2.3
                                            yield {
                                                'type': 'complete',
                                                'content': ''
                                            }
                                        else:
                                            yield {
                                                'type': 'error',
                                                'content': 'Coze API 返回空内容'
                                            }
                                        stream_ended = True
                                        break
                                    
                                    # 处理 conversation.chat.failed 事件（对话失败）
                                    elif event_type == 'conversation.chat.failed':
                                        last_error = data.get('last_error', {})
                                        error_code = last_error.get('code', 0)
                                        error_msg = last_error.get('msg', '未知错误')
                                        logger.error(f"❌ Bot处理失败: code={error_code}, msg={error_msg}")
                                        yield {
                                            'type': 'error',
                                            'content': f'Bot处理失败: {error_msg} (code: {error_code})'
                                        }
                                        stream_ended = True
                                        break
                                    
                                    # 处理错误事件
                                    elif event_type == 'error' or msg_type == 'error':
                                        error_msg = data.get('message', data.get('content', data.get('error', '未知错误')))
                                        logger.error(f"❌ Bot返回错误: {error_msg}")
                                        yield {
                                            'type': 'error',
                                            'content': error_msg
                                        }
                                        stream_ended = True
                                        break
                                    
                                    # 其他格式（兼容旧格式，使用原有的提取逻辑作为fallback）
                                    else:
                                        # 跳过技术性消息
                                        if data.get('msg_type') in ['generate_answer_finish', 'conversation_finish']:
                                            continue
                                        
                                        # 尝试提取内容（使用原有的逻辑作为fallback）
                                        content = self._extract_content_from_response(data)
                                        if content:
                                            # 只处理answer类型（如果msg_type存在）
                                            if msg_type and msg_type != 'answer':
                                                continue
                                            
                                            # 检测是否为错误消息
                                            if self._is_error_response(content):
                                                logger.warning(f"⚠️ Coze Bot 返回错误消息: {content[:100]}... (Bot ID: {used_bot_id})")
                                                continue
                                            
                                            # 过滤掉提示词和指令文本
                                            if self._is_prompt_or_instruction(content):
                                                logger.info(f"⚠️ 内容被过滤（提示词/指令）: {content[:50]}...")
                                                continue
                                            
                                            has_content = True
                                            buffer += content
                                            yield {
                                                'type': 'progress',
                                                'content': content
                                            }
                                        else:
                                            logger.debug(f"⚠️ 未能从响应中提取内容 (Bot ID: {used_bot_id}), event={event_type}, type={msg_type}, 原始数据: {json.dumps(data, ensure_ascii=False)[:200]}")
                                
                                except json.JSONDecodeError as e:
                                    logger.debug(f"JSON解析失败: {e}, 原始数据: {data_str[:100]}")
                                    continue
                            
                            # 如果流已结束，跳出循环
                            if stream_ended:
                                break
                        
                        # 流结束处理
                        if not stream_ended:
                            if has_content and buffer.strip():
                                # 检查 buffer 中是否包含错误消息
                                if self._is_error_response(buffer.strip()):
                                    logger.error(f"Coze Bot 返回错误响应 (Bot ID: {used_bot_id}): {buffer.strip()[:200]}")
                                    yield {
                                        'type': 'error',
                                        'content': 'Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。'
                                    }
                                else:
                                    logger.info(f"✅ 流式生成完成 (Bot ID: {used_bot_id}), buffer长度: {len(buffer)}, has_content: {has_content}")
                                    yield {
                                        'type': 'complete',
                                        'content': buffer.strip()
                                    }
                            else:
                                # 增强错误信息：记录更多调试信息
                                logger.warning(f"⚠️ Coze API 返回空内容 (Bot ID: {used_bot_id})")
                                logger.warning(f"   响应状态: {response.status_code}")
                                logger.warning(f"   has_content: {has_content}")
                                logger.warning(f"   buffer长度: {len(buffer)}")
                                logger.warning(f"   buffer内容预览: {buffer[:500]}")
                                logger.warning(f"   已处理行数: {line_count}")
                                
                                # 提供更详细的错误信息
                                error_details = []
                                error_details.append(f"响应状态: {response.status_code}")
                                error_details.append(f"Bot ID: {used_bot_id}")
                                
                                if not has_content:
                                    error_details.append("未收到任何内容增量（delta事件）")
                                if not buffer.strip():
                                    error_details.append("Buffer为空或只包含空白字符")
                                
                                error_msg = f"Coze API 返回空内容。{'; '.join(error_details)}。请检查：1) Bot配置是否正确，2) Prompt格式是否符合Bot期望，3) Bot是否已启用并配置了正确的提示词。"
                                
                                yield {
                                    'type': 'error',
                                    'content': error_msg
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
        
        # 过滤错误消息（Coze Bot 无法回答时返回的默认消息）
        error_messages = [
            '对不起，我无法回答这个问题',
            '对不起,我无法回答这个问题',
            '对不起我无法回答这个问题',
            '无法回答这个问题',
            '我无法回答这个问题',
        ]
        
        text_normalized = text.strip()
        for error_msg in error_messages:
            if error_msg in text_normalized:
                return True  # 过滤掉这种错误消息
        
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
    
    def _is_error_response(self, text: str) -> bool:
        """
        检测是否为 Coze Bot 返回的错误消息
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 如果是错误消息返回True，否则返回False
        """
        if not text or len(text.strip()) < 5:
            return False
        
        # 错误消息的关键词
        error_keywords = [
            '对不起，我无法回答这个问题',
            '对不起,我无法回答这个问题',
            '对不起我无法回答这个问题',
            '无法回答这个问题',
            '我无法回答这个问题',
            '抱歉，我无法',
            '抱歉,我无法',
            '我无法处理',
            '无法处理',
        ]
        
        text_normalized = text.strip()
        for keyword in error_keywords:
            if keyword in text_normalized:
                return True
        
        return False


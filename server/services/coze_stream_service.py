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

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")


class CozeStreamService:
    """Coze 流式服务"""
    
    # 思考过程开头特征（需过滤）
    THINKING_START_PATTERNS = [
        '我现在需要', '现在我需要', '我需要处理', '我需要根据',
        '首先，', '首先,', '首先看', '首先处理', '首先分析',
        '用户现在', '用户提供', '用户输入',
        '根据传统术语', '根据术语对照', '根据对照表',
        '接下来要', '接下来需要', '接下来分析',
        '检查一下', '检查字数', '确保格式',
        '然后看', '然后处理', '然后分析',
        '需要将', '需要把', '需要转化',
    ]
    
    # 正式答案开头特征（停止过滤）
    ANSWER_START_PATTERNS = [
        '宜：', '忌：', '宜:', '忌:',
        '因为', '原因是', '这是由于',
        '您的', '你的', '命主',
        '今日', '本月', '今年',
        '适合', '不适合', '建议',
    ]
    
    def __init__(self, access_token: Optional[str] = None, bot_id: Optional[str] = None,
                 api_base: str = "https://api.coze.cn"):
        """
        初始化Coze流式服务
        
        Args:
            access_token: Coze Access Token，如果为None则从数据库获取
            bot_id: Coze Bot ID，如果为None则从数据库获取（优先级：参数 > 数据库）
            api_base: Coze API 基础URL，默认为 https://api.coze.cn
        """
        # 优先级：参数传入 > 数据库配置（只从数据库读取，不降级到环境变量）
        if not access_token:
            access_token = get_config_from_db_only("COZE_ACCESS_TOKEN")
        self.access_token = access_token
        
        if not bot_id:
            bot_id = get_config_from_db_only("COZE_BOT_ID")
        self.bot_id = bot_id
        
        self.api_base = api_base.rstrip('/')
        
        if not self.access_token:
            raise ValueError("数据库配置缺失: COZE_ACCESS_TOKEN，请在 service_configs 表中配置")
        
        if not self.bot_id:
            raise ValueError("数据库配置缺失: COZE_BOT_ID，请在 service_configs 表中配置")
        
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
        
        # 构建输入数据（简化格式，让 Bot 根据自己的配置处理）
        yi_text = '、'.join(yi_list) if yi_list else '无'
        ji_text = '、'.join(ji_list) if ji_list else '无'
        
        # ⚠️ 重要：不在代码中硬编码提示词，让 Bot 使用自己的配置
        # Bot 的提示词应该在 Coze Bot 控制台中配置
        prompt = f"""宜：{yi_text}
忌：{ji_text}"""
        
        # Coze API 端点（流式）- 使用 v3 API（与 stream_custom_analysis 保持一致）
        possible_endpoints = [
            "/v3/chat",  # Coze v3 标准端点
        ]
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 流式 payload 格式（使用 additional_messages 格式，与 stream_custom_analysis 保持一致）
        payload = {
            "bot_id": str(used_bot_id),
            "user_id": "daily_fortune",
            "additional_messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "content_type": "text"
                }
            ],
            "stream": True
        }
        
        logger.info(f"🚀 准备调用 Coze API (行动建议): Bot ID={used_bot_id}, Prompt长度={len(prompt)}")
        
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
                    # 超时设置：(连接超时, 读取超时)
                    # 大模型生成内容需要较长时间，读取超时设置为 180 秒
                    response = await loop.run_in_executor(
                        None,
                        lambda: requests.post(
                            url,
                            headers=headers_to_use,
                            json=payload,
                            stream=True,
                            timeout=(30, 180)  # 连接30秒，读取180秒
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
                        # 处理流式响应（使用与 stream_custom_analysis 相同的逻辑）
                        buffer = ""
                        sent_length = 0
                        has_content = False
                        current_event = None
                        stream_ended = False
                        line_count = 0
                        is_thinking = False  # 标志位：是否处于思考过程中
                        thinking_buffer = ""  # 累积思考过程内容，用于检测
                        
                        logger.info(f"📡 开始处理 Coze API 流式响应 (行动建议, Bot ID: {used_bot_id})")
                        
                        # 按行处理SSE流
                        for line in response.iter_lines():
                            if not line:
                                continue
                            
                            await asyncio.sleep(0)
                            
                            line_str = line.decode('utf-8').strip()
                            if not line_str:
                                continue
                            
                            line_count += 1
                            if line_count <= 20:
                                logger.info(f"📨 SSE行 {line_count}: {line_str[:200]}")
                            
                            # 处理 event: 行
                            if line_str.startswith('event:'):
                                current_event = line_str[6:].strip()
                                continue
                            
                            # 处理 data: 行
                            elif line_str.startswith('data:'):
                                data_str = line_str[5:].strip()
                                
                                if data_str == '[DONE]':
                                    # 流结束
                                    if has_content and buffer.strip():
                                        if self._is_error_response(buffer.strip()):
                                            logger.error(f"Coze Bot 返回错误响应 (行动建议, Bot ID: {used_bot_id}): {buffer.strip()[:200]}")
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
                                    
                                    # 防御性检查
                                    if not isinstance(data, dict):
                                        logger.warning(f"⚠️ SSE数据不是字典: {type(data)}, 数据: {data_str[:100]}")
                                        continue
                                    
                                    # 使用 current_event 或 data 中的 event 字段
                                    event_type = current_event or data.get('event', '')
                                    msg_type = data.get('type', '')
                                    status = data.get('status', '')
                                    
                                    # 优先检查status字段
                                    if status == 'failed':
                                        last_error = data.get('last_error', {})
                                        error_code = last_error.get('code', 0)
                                        error_msg = last_error.get('msg', 'Bot处理失败')
                                        logger.error(f"❌ Bot处理失败（行动建议）: code={error_code}, msg={error_msg}")
                                        
                                        # 特殊处理配额错误（4028）
                                        if error_code == 4028:
                                            # 检查是否有备用 Token
                                            backup_token = None
                                            try:
                                                backup_token = get_config_from_db_only("COZE_ACCESS_TOKEN_BACKUP")
                                            except Exception:
                                                pass
                                            
                                            if backup_token and backup_token != self.access_token:
                                                error_content = f'Coze API 免费配额已用完（错误码: 4028）。系统已检测到备用 Token，但当前请求仍失败。请检查备用 Token 是否有效，或升级到付费计划。'
                                            else:
                                                error_content = 'Coze API 免费配额已用完（错误码: 4028）。请升级到付费计划或联系管理员。如需使用备用 Token，请在 service_configs 表中配置 COZE_ACCESS_TOKEN_BACKUP。'
                                        else:
                                            error_content = f'Bot处理失败: {error_msg} (错误码: {error_code})'
                                        
                                        yield {
                                            'type': 'error',
                                            'content': error_content
                                        }
                                        stream_ended = True
                                        break
                                    
                                    # 处理 conversation.message.delta 事件（增量内容）
                                    if event_type == 'conversation.message.delta':
                                        # 跳过非answer类型
                                        if msg_type in ['knowledge_recall', 'verbose']:
                                            continue
                                        
                                        # 只使用 content 字段，过滤掉深度思考模型的 reasoning_content（思考过程）
                                        content = data.get('content', '')
                                        
                                        if content and isinstance(content, str):
                                            # 检测是否为错误消息
                                            if self._is_error_response(content):
                                                logger.warning(f"⚠️ Coze Bot 返回错误消息: {content[:100]}... (行动建议)")
                                                continue
                                            
                                            # 累积内容用于检测思考过程
                                            thinking_buffer += content
                                            
                                            # 标志位检测逻辑：检测思考过程开头和正式答案开头
                                            if not has_content:  # 还没有发送过内容
                                                if self._is_thinking_start(thinking_buffer):
                                                    is_thinking = True
                                                    logger.debug(f"🧠 检测到思考过程开头，开始过滤: {thinking_buffer[:50]}...")
                                                elif self._is_answer_start(thinking_buffer):
                                                    is_thinking = False
                                                    logger.debug(f"✅ 检测到正式答案开头: {thinking_buffer[:50]}...")
                                            
                                            # 如果正在思考过程中，检测是否出现正式答案
                                            if is_thinking:
                                                if self._is_answer_start(content):
                                                    is_thinking = False
                                                    logger.debug(f"✅ 思考过程结束，检测到正式答案: {content[:50]}...")
                                                else:
                                                    # 仍在思考过程中，跳过此内容
                                                    logger.debug(f"🧠 过滤思考过程: {content[:50]}...")
                                                    continue
                                            
                                            # 过滤掉提示词和指令文本（作为备选过滤）
                                            if self._is_prompt_or_instruction(content):
                                                logger.debug(f"⚠️ 过滤提示词/指令: {content[:50]}...")
                                                continue
                                            
                                            has_content = True
                                            buffer += content
                                            sent_length += len(content)
                                            yield {
                                                'type': 'progress',
                                                'content': content
                                            }
                                        continue
                                    
                                    # 处理 conversation.message.completed 事件（完整消息）
                                    elif event_type == 'conversation.message.completed':
                                        if msg_type == 'verbose':
                                            continue
                                        
                                        if msg_type == 'knowledge_recall':
                                            continue
                                        
                                        # 如果没有收到 delta 事件，尝试从 completed 事件中提取内容
                                        if not has_content:
                                            content = data.get('content', '')
                                            if not content:
                                                content = self._extract_content_from_response(data)
                                            
                                            if content and isinstance(content, str) and len(content.strip()) > 10:
                                                # 检查 content 是否是JSON字符串
                                                try:
                                                    if content.strip().startswith('{'):
                                                        parsed_content = json.loads(content)
                                                        if isinstance(parsed_content, dict):
                                                            if parsed_content.get('msg_type') == 'knowledge_recall':
                                                                continue
                                                            text_content = parsed_content.get('text') or parsed_content.get('content') or parsed_content.get('message')
                                                            if text_content and isinstance(text_content, str):
                                                                content = text_content
                                                except (json.JSONDecodeError, AttributeError, ValueError):
                                                    pass
                                                
                                                # 检测是否为错误消息
                                                if self._is_error_response(content):
                                                    logger.warning(f"⚠️ Coze Bot 返回错误消息: {content[:100]}... (行动建议)")
                                                    continue
                                                
                                                # 过滤掉提示词和指令文本
                                                if self._is_prompt_or_instruction(content):
                                                    continue
                                                
                                                has_content = True
                                                buffer = content
                                                sent_length = 0
                                                
                                                # 分段发送内容
                                                chunk_size = 100
                                                for i in range(0, len(content), chunk_size):
                                                    chunk = content[i:i + chunk_size]
                                                    yield {
                                                        'type': 'progress',
                                                        'content': chunk
                                                    }
                                                    sent_length += len(chunk)
                                        
                                        continue
                                    
                                    # 处理 conversation.chat.completed 事件（对话完成）
                                    elif event_type == 'conversation.chat.completed':
                                        logger.info(f"✅ 对话完成（行动建议）: buffer长度={len(buffer)}, 已发送长度={sent_length}, has_content={has_content}")
                                        if has_content and buffer.strip():
                                            # 如果有未发送的内容，发送剩余部分
                                            if len(buffer) > sent_length:
                                                new_content = buffer[sent_length:]
                                                yield {
                                                    'type': 'complete',
                                                    'content': new_content.strip()
                                                }
                                            else:
                                                # 所有内容已通过 progress 发送，发送空 complete 表示完成
                                                yield {
                                                    'type': 'complete',
                                                    'content': ''
                                                }
                                        else:
                                            # 没有收到任何内容，返回错误
                                            logger.warning(f"⚠️ 对话完成但无内容: has_content={has_content}, buffer长度={len(buffer)}")
                                            yield {
                                                'type': 'error',
                                                'content': 'Coze API 返回空内容，请检查Bot配置和提示词'
                                            }
                                        stream_ended = True
                                        break
                                    
                                    # 处理 conversation.chat.failed 事件（对话失败）
                                    elif event_type == 'conversation.chat.failed':
                                        last_error = data.get('last_error', {})
                                        error_code = last_error.get('code', 0)
                                        error_msg = last_error.get('msg', '未知错误')
                                        logger.error(f"❌ Bot处理失败（行动建议）: code={error_code}, msg={error_msg}")
                                        yield {
                                            'type': 'error',
                                            'content': f'Bot处理失败: {error_msg} (code: {error_code})'
                                        }
                                        stream_ended = True
                                        break
                                    
                                    # 处理错误事件
                                    elif event_type == 'error' or msg_type == 'error':
                                        error_msg = data.get('message', data.get('content', data.get('error', '未知错误')))
                                        logger.error(f"❌ Bot返回错误（行动建议）: {error_msg}")
                                        yield {
                                            'type': 'error',
                                            'content': error_msg
                                        }
                                        stream_ended = True
                                        break
                                
                                except json.JSONDecodeError as e:
                                    logger.debug(f"JSON解析失败: {e}, 原始数据: {data_str[:100]}")
                                    continue
                            
                            # 如果流已结束，跳出循环
                            if stream_ended:
                                break
                        
                        # 流结束处理
                        if not stream_ended:
                            if has_content and buffer.strip():
                                if self._is_error_response(buffer.strip()):
                                    logger.error(f"Coze Bot 返回错误响应 (行动建议, Bot ID: {used_bot_id}): {buffer.strip()[:200]}")
                                    yield {
                                        'type': 'error',
                                        'content': 'Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。'
                                    }
                                else:
                                    logger.info(f"✅ 流式生成完成 (行动建议, Bot ID: {used_bot_id}), buffer长度: {len(buffer)}, has_content: {has_content}")
                                    yield {
                                        'type': 'complete',
                                        'content': buffer.strip()
                                    }
                            else:
                                logger.warning(f"⚠️ Coze API 返回空内容 (行动建议, Bot ID: {used_bot_id})")
                                logger.warning(f"   响应状态: {response.status_code}")
                                logger.warning(f"   has_content: {has_content}")
                                logger.warning(f"   buffer长度: {len(buffer)}")
                                
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
        # ⚠️ 关键修复：每次调用时重新从数据库读取配置（支持热更新）
        # 优先级：参数传入 > 数据库配置 > 实例变量（只从数据库读取，不降级到环境变量）
        current_access_token = get_config_from_db_only("COZE_ACCESS_TOKEN") or self.access_token
        if not current_access_token:
            yield {
                'type': 'error',
                'content': '数据库配置缺失: COZE_ACCESS_TOKEN，请在 service_configs 表中配置'
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
        
        # 优先级：参数传入 > 数据库配置 > 实例变量（只从数据库读取，不降级到环境变量）
        used_bot_id = bot_id or get_config_from_db_only("COZE_BOT_ID") or self.bot_id
        
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
                    # 超时设置：(连接超时, 读取超时)
                    # 大模型生成内容需要较长时间，读取超时设置为 180 秒
                    response = await loop.run_in_executor(
                        None,
                        lambda: requests.post(
                            url,
                            headers=headers_to_use,
                            json=payload,
                            stream=True,
                            timeout=(30, 180)  # 连接30秒，读取180秒
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
                        is_thinking = False  # 标志位：是否处于思考过程中
                        thinking_buffer = ""  # 累积思考过程内容，用于检测
                        
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
                                        
                                        # 只使用 content 字段，过滤掉深度思考模型的 reasoning_content（思考过程）
                                        content = data.get('content', '')
                                        
                                        # 增强日志：记录delta事件
                                        if not content:
                                            logger.debug(f"⚠️ Delta事件content为空: event={event_type}, type={msg_type}, data_keys={list(data.keys())[:10]}")
                                        
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
                                            
                                            # 累积内容用于检测思考过程
                                            thinking_buffer += content
                                            
                                            # 标志位检测逻辑：检测思考过程开头和正式答案开头
                                            if not has_content:  # 还没有发送过内容
                                                if self._is_thinking_start(thinking_buffer):
                                                    is_thinking = True
                                                    logger.debug(f"🧠 检测到思考过程开头，开始过滤: {thinking_buffer[:50]}...")
                                                elif self._is_answer_start(thinking_buffer):
                                                    is_thinking = False
                                                    logger.debug(f"✅ 检测到正式答案开头: {thinking_buffer[:50]}...")
                                            
                                            # 如果正在思考过程中，检测是否出现正式答案
                                            if is_thinking:
                                                if self._is_answer_start(content):
                                                    is_thinking = False
                                                    logger.debug(f"✅ 思考过程结束，检测到正式答案: {content[:50]}...")
                                                else:
                                                    # 仍在思考过程中，跳过此内容
                                                    logger.debug(f"🧠 过滤思考过程: {content[:50]}...")
                                                    continue
                                            
                                            # 过滤掉提示词和指令文本（作为备选过滤）
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
    
    def _is_thinking_start(self, text: str) -> bool:
        """
        检测文本是否以思考过程特征开头
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 如果是思考过程开头返回True
        """
        if not text:
            return False
        text_stripped = text.strip()
        for pattern in self.THINKING_START_PATTERNS:
            if text_stripped.startswith(pattern):
                return True
        return False
    
    def _is_answer_start(self, text: str) -> bool:
        """
        检测文本是否以正式答案特征开头
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 如果是正式答案开头返回True
        """
        if not text:
            return False
        text_stripped = text.strip()
        for pattern in self.ANSWER_START_PATTERNS:
            if text_stripped.startswith(pattern):
                return True
        return False
    
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
        
        # 提示词和指令的关键词（包括思考过程）
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
            'from_unit',
            # 过滤思考过程 - 基础关键词
            '用户现在需要',
            '首先处理',
            '然后处理',
            '然后忌：',
            '检查字数',
            '把宜和忌',
            '按照要求',
            '按照现代化要求',
            '不能超过',
            '不超过60字',
            '确保简洁',
            '调整下表述',
            '调整表述',
            '这些不利于现代生活',
            # 过滤思考过程 - 增强关键词
            '首先，我得',
            '首先，先从',
            '首先得按照',
            '我得按照',
            '我需要根据',
            '需要一步步',
            '一步步来',
            '一步步详细',
            '逐步展开',
            '接下来',
            '接下来分析',
            '接下来看',
            '然后是',
            '然后再',
            '现在需要',
            '现在一步步',
            '分析。首先',
            '报告。首先',
            '来展开',
            '来分析',
            '来生成',
            '按照要求的',
            '五个部分',
            '四个部分',
            '三个部分',
            '逐一分析',
        ]
        
        text_lower = text.lower()
        for keyword in prompt_keywords:
            if keyword in text:
                logger.debug(f"🚫 过滤内容（匹配关键词 '{keyword}'）: {text[:80]}...")
                return True
        
        # 检查开头是否是思考过程模式
        thinking_start_patterns = [
            '用户现在',
            '首先，',
            '首先,',
            '我现在需要',
            '现在我需要',
            '需要分析',
            '需要根据',
        ]
        for pattern in thinking_start_patterns:
            if text.strip().startswith(pattern):
                logger.debug(f"🚫 过滤内容（开头匹配 '{pattern}'）: {text[:80]}...")
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


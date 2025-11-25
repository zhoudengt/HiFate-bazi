# -*- coding: utf-8 -*-
"""
Intent Service 专用 LLM 客户端
"""
import requests
import json
import hashlib
import redis
import time
from typing import Dict, Any, Optional
from services.intent_service.config import (
    COZE_ACCESS_TOKEN,
    INTENT_BOT_ID,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_CACHE_TTL
)
from services.intent_service.logger import logger


class IntentLLMClient:
    """Intent Service 专用 LLM 客户端（基于 Coze API）"""
    
    def __init__(self):
        self.access_token = COZE_ACCESS_TOKEN
        self.bot_id = INTENT_BOT_ID
        self.base_url = "https://api.coze.cn/v3/chat"
        
        # 初始化 Redis 缓存
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed, cache disabled: {e}")
            self.redis_client = None
            self.cache_enabled = False
    
    def _generate_cache_key(self, question: str, prompt_version: str) -> str:
        """生成缓存键"""
        content = f"{question}:{prompt_version}"
        return f"intent:cache:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取结果"""
        if not self.cache_enabled:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache hit: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """保存到缓存"""
        if not self.cache_enabled:
            return
        
        try:
            self.redis_client.setex(
                cache_key,
                REDIS_CACHE_TTL,
                json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"Cache saved: {cache_key}")
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def call_coze_api(
        self,
        question: str,
        prompt_template: str,
        use_cache: bool = True,
        prompt_version: str = "v1.0"
    ) -> Dict[str, Any]:
        """
        调用 Coze API 进行意图识别
        
        Args:
            question: 用户问题
            prompt_template: Prompt 模板
            use_cache: 是否使用缓存
            prompt_version: Prompt 版本
        
        Returns:
            意图识别结果
        """
        # 检查缓存
        cache_key = self._generate_cache_key(question, prompt_version)
        if use_cache:
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        # 构建完整 Prompt
        full_prompt = prompt_template.format(question=question)
        
        # 准备请求
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "bot_id": self.bot_id,
            "user_id": "intent_service",
            "stream": False,
            "auto_save_history": True,  # 改为 True 避免 stream 字段要求
            "additional_messages": [
                {
                    "role": "user",
                    "content": full_prompt,
                    "content_type": "text"
                }
            ]
        }
        
        try:
            # 调用 Coze API
            logger.info(f"Calling Coze API for question: {question[:50]}...")
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 记录完整响应以便调试
            logger.info(f"Coze API response: {json.dumps(result, ensure_ascii=False)[:500]}")
            
            if result.get("code") != 0:
                raise Exception(f"Coze API error: {result.get('msg', 'Unknown error')}")
            
            data = result.get("data", {})
            chat_id = data.get("id")
            conversation_id = data.get("conversation_id")
            status = data.get("status")
            
            # 如果状态是 in_progress，需要轮询等待完成
            if status == "in_progress":
                logger.info(f"Chat {chat_id} is in progress, start polling...")
                status, last_error = self._poll_chat_result(chat_id, conversation_id)
                
                if status == "failed":
                    error_msg = last_error.get("msg", "Unknown error")
                    raise Exception(f"Chat failed: {error_msg}")
                
                # 获取完整消息列表
                messages = self._get_messages(conversation_id, chat_id)
            else:
                # 直接从响应中获取消息
                messages = data.get("messages", [])
            
            # 提取消息内容
            answer_content = ""
            for msg in messages:
                logger.info(f"Message: role={msg.get('role')}, type={msg.get('type')}")
                if msg.get("role") == "assistant" and msg.get("type") == "answer":
                    answer_content = msg.get("content", "")
                    break
            
            if not answer_content:
                logger.warning(f"No answer in messages. Full data: {json.dumps(result.get('data', {}), ensure_ascii=False)[:500]}")
                raise Exception("No answer content in Coze response")
            
            # 解析 JSON 格式的结果
            parsed_result = self._parse_llm_response(answer_content)
            parsed_result["prompt_version"] = prompt_version
            
            # 保存到缓存
            if use_cache:
                self._save_to_cache(cache_key, parsed_result)
            
            logger.info(f"LLM call successful: {parsed_result}")
            return parsed_result
            
        except requests.RequestException as e:
            logger.error(f"Coze API request failed: {e}")
            raise Exception(f"LLM API call failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise Exception(f"Invalid LLM response format: {e}")
        except Exception as e:
            logger.error(f"LLM call error: {e}")
            raise
    
    def _poll_chat_result(self, chat_id: str, conversation_id: str, max_wait: int = 30) -> tuple:
        """
        轮询查询聊天结果
        
        Args:
            chat_id: 聊天 ID
            conversation_id: 会话 ID
            max_wait: 最大等待时间（秒）
        
        Returns:
            (status, last_error)
        """
        retrieve_url = f"https://api.coze.cn/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(retrieve_url, headers=headers, timeout=5)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 0:
                    logger.error(f"Retrieve API error: {result.get('msg')}")
                    return "failed", {"msg": result.get("msg", "Unknown error")}
                
                data = result.get("data", {})
                status = data.get("status")
                last_error = data.get("last_error", {})
                
                logger.info(f"Poll chat {chat_id}: status={status}")
                
                if status == "completed":
                    return status, last_error
                elif status == "failed":
                    return status, last_error
                elif status in ["in_progress", "created"]:
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    logger.warning(f"Unknown status: {status}")
                    return "failed", {"msg": f"Unknown status: {status}"}
                    
            except Exception as e:
                logger.error(f"Poll error: {e}")
                time.sleep(1)
        
        # 超时
        logger.error(f"Poll timeout after {max_wait}s")
        return "failed", {"msg": f"Timeout after {max_wait}s"}
    
    def _get_messages(self, conversation_id: str, chat_id: str) -> list:
        """
        获取聊天消息列表
        
        Args:
            conversation_id: 会话 ID
            chat_id: 聊天 ID
        
        Returns:
            消息列表
        """
        messages_url = f"https://api.coze.cn/v3/chat/message/list?conversation_id={conversation_id}&chat_id={chat_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(messages_url, headers=headers, timeout=5)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                logger.error(f"Messages API error: {result.get('msg')}")
                return []
            
            messages = result.get("data", [])
            logger.info(f"Got {len(messages)} messages")
            return messages
            
        except Exception as e:
            logger.error(f"Get messages error: {e}")
            return []
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        解析 LLM 返回的 JSON 格式结果
        
        Args:
            content: LLM 返回的文本内容
        
        Returns:
            解析后的字典
        """
        try:
            # 尝试直接解析 JSON
            return json.loads(content)
        except json.JSONDecodeError:
            # 如果不是纯 JSON，尝试提取 ```json ... ``` 代码块
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 如果都失败，返回默认结构
            logger.warning(f"Failed to parse LLM response as JSON: {content[:200]}")
            return {
                "intents": ["general"],
                "confidence": 0.5,
                "reasoning": content,
                "is_ambiguous": True
            }
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查 Coze API 是否可访问
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(
                "https://api.coze.cn/v1/workspace/list",
                headers=headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


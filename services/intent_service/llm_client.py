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
        
        try:
            from shared.config.redis import get_redis_client_str
            self.redis_client = get_redis_client_str()
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis cache initialized (shared pool)")
        except Exception:
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                    decode_responses=True
                )
                self.redis_client.ping()
                self.cache_enabled = True
                logger.info("Redis cache initialized (standalone)")
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
        
        request_id = f"llm_{int(time.time() * 1000)}"
        try:
            # 调用 Coze API
            logger.info(f"[LLMClient][{request_id}] ========== 开始调用Coze API ==========")
            logger.info(f"[LLMClient][{request_id}] 📥 输入: question={question[:50]}..., use_cache={use_cache}, prompt_version={prompt_version}")
            api_start = time.time()
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            api_time = int((time.time() - api_start) * 1000)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 记录完整响应以便调试
            logger.info(f"[LLMClient][{request_id}] [API调用] ✅ API调用完成: 耗时={api_time}ms")
            logger.info(f"[LLMClient][{request_id}] [API调用] 📤 响应: {json.dumps(result, ensure_ascii=False)[:500]}")
            
            if result.get("code") != 0:
                raise Exception(f"Coze API error: {result.get('msg', 'Unknown error')}")
            
            data = result.get("data", {})
            chat_id = data.get("id")
            conversation_id = data.get("conversation_id")
            status = data.get("status")
            
            # 如果状态是 in_progress，需要轮询等待完成
            poll_time = 0
            if status == "in_progress":
                logger.info(f"[LLMClient][{request_id}] [轮询] Chat {chat_id} is in progress, start polling...")
                poll_start = time.time()
                status, last_error = self._poll_chat_result(chat_id, conversation_id)
                poll_time = int((time.time() - poll_start) * 1000)
                
                if status == "failed":
                    error_msg = last_error.get("msg", "Unknown error")
                    logger.error(f"[LLMClient][{request_id}] [轮询] ❌ Chat失败: {error_msg}, 耗时={poll_time}ms")
                    raise Exception(f"Chat failed: {error_msg}")
                
                logger.info(f"[LLMClient][{request_id}] [轮询] ✅ 轮询完成: status={status}, 耗时={poll_time}ms")
                # 获取完整消息列表
                messages = self._get_messages(conversation_id, chat_id)
            else:
                # 直接从响应中获取消息
                messages = data.get("messages", [])
                logger.info(f"[LLMClient][{request_id}] [轮询] ⏭️ 无需轮询，直接获取消息")
            
            # 提取消息内容
            logger.info(f"[LLMClient][{request_id}] [消息提取] 开始提取消息内容...")
            answer_content = ""
            for msg in messages:
                logger.info(f"[LLMClient][{request_id}] [消息提取] Message: role={msg.get('role')}, type={msg.get('type')}")
                if msg.get("role") == "assistant" and msg.get("type") == "answer":
                    answer_content = msg.get("content", "")
                    break
            
            if not answer_content:
                logger.warning(f"[LLMClient][{request_id}] [消息提取] ❌ 未找到答案内容")
                logger.warning(f"[LLMClient][{request_id}] [消息提取] Full data: {json.dumps(result.get('data', {}), ensure_ascii=False)[:500]}")
                raise Exception("No answer content in Coze response")
            
            logger.info(f"[LLMClient][{request_id}] [消息提取] ✅ 提取到答案内容: {answer_content[:100]}...")
            
            # 解析 JSON 格式的结果
            logger.info(f"[LLMClient][{request_id}] [结果解析] 开始解析JSON结果...")
            parse_start = time.time()
            try:
                parsed_result = self._parse_llm_response(answer_content)
                parsed_result["prompt_version"] = prompt_version
                parse_time = int((time.time() - parse_start) * 1000)
                logger.info(f"[LLMClient][{request_id}] [结果解析] ✅ 解析完成: 耗时={parse_time}ms")
                logger.info(f"[LLMClient][{request_id}] [结果解析] 📤 解析结果: {parsed_result}")
            except Exception as e:
                parse_time = int((time.time() - parse_start) * 1000)
                logger.error(f"[LLMClient][{request_id}] [结果解析] ❌ 解析失败: {e}, 耗时={parse_time}ms", exc_info=True)
                raise
            
            # 保存到缓存
            if use_cache:
                logger.info(f"[LLMClient][{request_id}] [缓存] 保存到缓存...")
                try:
                    self._save_to_cache(cache_key, parsed_result)
                    logger.info(f"[LLMClient][{request_id}] [缓存] ✅ 缓存保存成功")
                except Exception as e:
                    logger.warning(f"[LLMClient][{request_id}] [缓存] ⚠️ 缓存保存失败: {e}")
            
            total_time = int((time.time() - api_start) * 1000)
            logger.info(f"[LLMClient][{request_id}] ========== Coze API调用完成 ==========")
            logger.info(f"[LLMClient][{request_id}] 📊 总耗时: {total_time}ms "
                       f"(API调用={api_time}ms, "
                       f"{'轮询=' + str(poll_time) + 'ms, ' if poll_time > 0 else ''}"
                       f"解析={parse_time}ms)")
            logger.info(f"[LLMClient][{request_id}] 📤 最终输出: {parsed_result}")
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
        poll_id = f"poll_{int(time.time() * 1000)}"
        logger.info(f"[LLMClient][{poll_id}] ========== 开始轮询 ==========")
        logger.info(f"[LLMClient][{poll_id}] 📥 输入: chat_id={chat_id}, conversation_id={conversation_id}, max_wait={max_wait}s")
        
        retrieve_url = f"https://api.coze.cn/v3/chat/retrieve?chat_id={chat_id}&conversation_id={conversation_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        poll_count = 0
        while time.time() - start_time < max_wait:
            poll_count += 1
            elapsed = int(time.time() - start_time)
            try:
                poll_start = time.time()
                response = requests.get(retrieve_url, headers=headers, timeout=5)
                poll_time = int((time.time() - poll_start) * 1000)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 0:
                    logger.error(f"[LLMClient][{poll_id}] [轮询#{poll_count}] ❌ Retrieve API错误: {result.get('msg')}, 耗时={poll_time}ms")
                    return "failed", {"msg": result.get("msg", "Unknown error")}
                
                data = result.get("data", {})
                status = data.get("status")
                last_error = data.get("last_error", {})
                
                logger.info(f"[LLMClient][{poll_id}] [轮询#{poll_count}] status={status}, 已等待={elapsed}s, 本次耗时={poll_time}ms")
                
                if status == "completed":
                    total_time = int((time.time() - start_time) * 1000)
                    logger.info(f"[LLMClient][{poll_id}] ========== 轮询完成 ==========")
                    logger.info(f"[LLMClient][{poll_id}] 📊 总耗时: {total_time}ms, 轮询次数: {poll_count}, 最终状态: {status}")
                    return status, last_error
                elif status == "failed":
                    total_time = int((time.time() - start_time) * 1000)
                    error_msg = last_error.get("msg", "Unknown error")
                    logger.error(f"[LLMClient][{poll_id}] ========== 轮询失败 ==========")
                    logger.error(f"[LLMClient][{poll_id}] 📊 总耗时: {total_time}ms, 轮询次数: {poll_count}, 错误: {error_msg}")
                    return status, last_error
                elif status in ["in_progress", "created"]:
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    logger.warning(f"[LLMClient][{poll_id}] [轮询#{poll_count}] ⚠️ 未知状态: {status}")
                    return "failed", {"msg": f"Unknown status: {status}"}
                    
            except Exception as e:
                poll_time = int((time.time() - poll_start) * 1000)
                logger.error(f"[LLMClient][{poll_id}] [轮询#{poll_count}] ❌ 轮询异常: {e}, 耗时={poll_time}ms", exc_info=True)
                time.sleep(1)
        
        # 超时
        total_time = int((time.time() - start_time) * 1000)
        logger.error(f"[LLMClient][{poll_id}] ========== 轮询超时 ==========")
        logger.error(f"[LLMClient][{poll_id}] 📊 总耗时: {total_time}ms, 轮询次数: {poll_count}, 超时时间: {max_wait}s")
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


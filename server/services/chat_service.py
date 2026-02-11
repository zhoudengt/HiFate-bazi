#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话服务 - 24/7 AI 对话功能（类似 FateTell）
支持多轮对话，维护上下文
"""

import sys
import os
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from core.analyzers.bazi_ai_analyzer import BaziAIAnalyzer
from server.services.stream_call_logger import get_stream_call_logger
import time

# 尝试导入 Redis（可选）
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# 内存存储（Redis 不可用时的降级方案）
_memory_storage = {}
_memory_storage_ttl = {}


class ChatService:
    """对话服务 - 支持多轮对话"""
    
    def __init__(self):
        """初始化对话服务"""
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                # 使用统一的 Redis 连接池（性能优化：避免重复创建连接）
                # 使用字符串模式客户端（decode_responses=True）
                from shared.config.redis import get_redis_client_str
                self.redis_client = get_redis_client_str()
                if self.redis_client:
                    # 测试连接
                    self.redis_client.ping()
            except Exception:
                self.redis_client = None
    
    def _get_storage_key(self, conversation_id: str) -> str:
        """获取存储键"""
        return f"bazi_chat:{conversation_id}"
    
    def _get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话上下文"""
        if self.redis_client:
            try:
                data = self.redis_client.get(self._get_storage_key(conversation_id))
                if data:
                    return json.loads(data)
            except Exception:
                pass
        
        # 降级到内存存储
        if conversation_id in _memory_storage:
            # 检查是否过期
            if conversation_id in _memory_storage_ttl:
                if time.time() > _memory_storage_ttl[conversation_id]:
                    del _memory_storage[conversation_id]
                    del _memory_storage_ttl[conversation_id]
                    return None
            return _memory_storage[conversation_id]
        
        return None
    
    def _save_conversation(self, conversation_id: str, conversation: Dict[str, Any], ttl: int = 3600):
        """保存对话上下文"""
        if self.redis_client:
            try:
                self.redis_client.setex(
                    self._get_storage_key(conversation_id),
                    ttl,
                    json.dumps(conversation, ensure_ascii=False)
                )
                return
            except Exception:
                pass
        
        # 降级到内存存储
        _memory_storage[conversation_id] = conversation
        _memory_storage_ttl[conversation_id] = time.time() + ttl
    
    def _delete_conversation(self, conversation_id: str):
        """删除对话上下文"""
        if self.redis_client:
            try:
                self.redis_client.delete(self._get_storage_key(conversation_id))
                return
            except Exception:
                pass
        
        # 降级到内存存储
        if conversation_id in _memory_storage:
            del _memory_storage[conversation_id]
        if conversation_id in _memory_storage_ttl:
            del _memory_storage_ttl[conversation_id]
    
    def create_conversation(
        self,
        solar_date: str,
        solar_time: str,
        gender: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新对话
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            user_name: 用户名称（可选）
            
        Returns:
            dict: 包含 conversation_id 和初始信息
        """
        # 计算八字数据
        bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
        if not bazi_result:
            return {
                "success": False,
                "error": "八字计算失败",
                "conversation_id": None
            }
        
        # 生成对话 ID
        conversation_id = str(uuid.uuid4())
        
        # 构建初始对话上下文
        bazi_data = bazi_result.get('bazi', {})
        basic_info = bazi_data.get('basic_info', {})
        
        conversation = {
            "conversation_id": conversation_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "bazi_data": bazi_data,
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "user_name": user_name,
            "messages": [
                {
                    "role": "system",
                    "content": f"你是一位资深的命理师。用户的基本信息：出生日期 {solar_date} {solar_time}，性别{'男' if gender == 'male' else '女'}。请根据用户的八字信息，提供专业的命理分析和建议。",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        # 保存对话上下文
        self._save_conversation(conversation_id, conversation, ttl=7200)  # 2小时过期
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "对话已创建"
        }
    
    def chat(
        self,
        conversation_id: str,
        user_message: str,
        access_token: Optional[str] = None,
        bot_id: Optional[str] = None,
        api_base: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送消息并获取 AI 回复
        
        Args:
            conversation_id: 对话 ID
            user_message: 用户消息
            access_token: Coze Access Token（可选）
            bot_id: Coze Bot ID（可选）
            api_base: Coze API 基础URL（可选）
            
        Returns:
            dict: 包含 AI 回复和对话历史
        """
        # 获取对话上下文
        conversation = self._get_conversation(conversation_id)
        if not conversation:
            return {
                "success": False,
                "error": "对话不存在或已过期",
                "reply": None
            }
        
        # 添加用户消息
        conversation["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 构建对话历史（用于 LLM）
        chat_history = []
        for msg in conversation["messages"][-10:]:  # 只保留最近10条消息
            chat_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 构建 Prompt（包含八字信息和对话历史）
        bazi_data = conversation.get("bazi_data", {})
        prompt_lines = []
        prompt_lines.append("你是一位资深的命理师，正在与用户进行对话。")
        prompt_lines.append("")
        prompt_lines.append("【用户八字信息】")
        basic_info = bazi_data.get('basic_info', {})
        prompt_lines.append(f"出生日期：{basic_info.get('solar_date', '')} {basic_info.get('solar_time', '')}")
        prompt_lines.append(f"性别：{'男' if basic_info.get('gender') == 'male' else '女'}")
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        prompt_lines.append("四柱八字：")
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
            prompt_lines.append(f"  {pillar_name}：{pillar.get('stem', '')}{pillar.get('branch', '')}")
        prompt_lines.append("")
        prompt_lines.append("【对话历史】")
        for msg in chat_history:
            role_name = "用户" if msg["role"] == "user" else "助手"
            prompt_lines.append(f"{role_name}：{msg['content']}")
        prompt_lines.append("")
        prompt_lines.append("请根据以上信息，回复用户的问题。要求：")
        prompt_lines.append("1. 回答要专业、准确，符合传统命理学原理")
        prompt_lines.append("2. 语言要自然、友好，像朋友聊天一样")
        prompt_lines.append("3. 可以结合用户的八字信息给出具体建议")
        prompt_lines.append("4. 避免绝对化的表述")
        prompt_lines.append("")
        prompt_lines.append("请开始回复：")
        
        prompt = "\n".join(prompt_lines)
        
        # 记录开始时间和前端输入
        api_start_time = time.time()
        frontend_input = {
            'conversation_id': conversation_id,
            'user_message': user_message,
            'bot_id': bot_id
        }
        input_data = {
            'prompt': prompt,
            'bazi_data': bazi_data,
            'chat_history': chat_history
        }
        
        # 调用 LLM
        try:
            init_kwargs = {}
            if access_token:
                init_kwargs['access_token'] = access_token
            if bot_id:
                init_kwargs['bot_id'] = bot_id
            if api_base:
                init_kwargs['api_base'] = api_base
            
            llm_start_time = time.time()
            ai_analyzer = BaziAIAnalyzer(**init_kwargs)
            result = ai_analyzer._call_coze_api(prompt, bazi_data)
            
            # 记录第一个token时间（非流式，使用总时间的一半作为估算）
            llm_first_token_time = llm_start_time + (time.time() - llm_start_time) / 2 if result.get('success') else None
            
            if result.get('success'):
                ai_reply = result.get('analysis', '')
                
                # 添加 AI 回复到对话历史
                conversation["messages"].append({
                    "role": "assistant",
                    "content": ai_reply,
                    "timestamp": datetime.now().isoformat()
                })
                conversation["updated_at"] = datetime.now().isoformat()
                
                # 保存更新后的对话上下文
                self._save_conversation(conversation_id, conversation, ttl=7200)
                
                # 计算轮次（从对话历史中获取）
                round_number = len([m for m in conversation["messages"] if m["role"] == "user"])
                
                # 记录交互数据（异步，不阻塞）
                api_end_time = time.time()
                api_response_time_ms = int((api_end_time - api_start_time) * 1000)
                llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
                
                stream_logger = get_stream_call_logger()
                stream_logger.log_async(
                    function_type='chat',
                    frontend_api='/api/v1/bazi/chat/send',
                    frontend_input=frontend_input,
                    input_data=json.dumps(input_data, ensure_ascii=False) if input_data else '',
                    llm_output=ai_reply,
                    api_total_ms=api_response_time_ms,
                    llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
                    llm_total_ms=llm_total_time_ms,
                    bot_id=bot_id,
                    llm_platform='coze',
                    status='success',
                )
                
                return {
                    "success": True,
                    "reply": ai_reply,
                    "conversation_id": conversation_id,
                    "message_count": len(conversation["messages"])
                }
            else:
                error_msg = result.get('error', 'LLM 调用失败')
                
                # 记录错误
                api_end_time = time.time()
                api_response_time_ms = int((api_end_time - api_start_time) * 1000)
                round_number = len([m for m in conversation["messages"] if m["role"] == "user"])
                
                stream_logger = get_stream_call_logger()
                stream_logger.log_async(
                    function_type='chat',
                    frontend_api='/api/v1/bazi/chat/send',
                    frontend_input=frontend_input,
                    input_data=json.dumps(input_data, ensure_ascii=False) if input_data else '',
                    api_total_ms=api_response_time_ms,
                    bot_id=bot_id,
                    llm_platform='coze',
                    status='failed',
                    error_message=error_msg,
                )
                
                return {
                    "success": False,
                    "error": error_msg,
                    "reply": None
                }
        except Exception as e:
            import traceback
            error_str = f"对话异常: {str(e)}\n{traceback.format_exc()}"
            
            # 记录错误
            api_end_time = time.time()
            api_response_time_ms = int((api_end_time - api_start_time) * 1000)
            round_number = len([m for m in conversation["messages"] if m["role"] == "user"]) if conversation else 1
            
            stream_logger = get_stream_call_logger()
            stream_logger.log_async(
                function_type='chat',
                frontend_api='/api/v1/bazi/chat/send',
                frontend_input=frontend_input,
                input_data=json.dumps(input_data, ensure_ascii=False) if 'input_data' in locals() and input_data else '',
                api_total_ms=api_response_time_ms,
                bot_id=bot_id,
                llm_platform='coze',
                status='failed',
                error_message=str(e),
            )
            
            return {
                "success": False,
                "error": error_str,
                "reply": None
            }
    
    def get_conversation_history(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话历史"""
        conversation = self._get_conversation(conversation_id)
        if not conversation:
            return {
                "success": False,
                "error": "对话不存在或已过期",
                "messages": []
            }
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "messages": conversation.get("messages", []),
            "created_at": conversation.get("created_at"),
            "updated_at": conversation.get("updated_at")
        }
    
    def delete_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """删除对话"""
        self._delete_conversation(conversation_id)
        return {
            "success": True,
            "message": "对话已删除"
        }


# 全局单例
_chat_service_instance = None

def get_chat_service() -> ChatService:
    """获取对话服务实例（单例）"""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    return _chat_service_instance


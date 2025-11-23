#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话接口 API - 24/7 AI 对话功能（类似 FateTell）
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.chat_service import get_chat_service

router = APIRouter()

# 线程池
import os
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class CreateConversationRequest(BaseModel):
    """创建对话请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    user_name: Optional[str] = Field(None, description="用户名称（可选）")
    
    @validator('solar_date')
    def validate_date(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_time')
    def validate_time(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v


class ChatRequest(BaseModel):
    """对话请求模型"""
    conversation_id: str = Field(..., description="对话 ID")
    user_message: str = Field(..., description="用户消息", example="我想了解我的事业运势")
    access_token: Optional[str] = Field(None, description="Coze Access Token（可选）")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选）")
    api_base: Optional[str] = Field(None, description="Coze API 基础URL（可选）")


@router.post("/bazi/chat/create", summary="创建新对话")
async def create_conversation(request: CreateConversationRequest):
    """
    创建新的对话会话
    
    对话会保存用户的八字信息，后续可以基于此进行多轮对话
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **user_name**: 用户名称（可选）
    
    返回 conversation_id，用于后续对话
    """
    try:
        loop = asyncio.get_event_loop()
        chat_service = get_chat_service()
        result = await loop.run_in_executor(
            executor,
            chat_service.create_conversation,
            request.solar_date,
            request.solar_time,
            request.gender,
            request.user_name
        )
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '创建对话失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"创建对话异常: {str(e)}\n{traceback.format_exc()}")


@router.post("/bazi/chat/send", summary="发送消息")
async def send_message(request: ChatRequest):
    """
    发送消息并获取 AI 回复
    
    - **conversation_id**: 对话 ID（从创建对话接口获取）
    - **user_message**: 用户消息
    - **access_token**: Coze Access Token（可选）
    - **bot_id**: Coze Bot ID（可选）
    - **api_base**: Coze API 基础URL（可选）
    
    返回 AI 回复
    """
    try:
        loop = asyncio.get_event_loop()
        chat_service = get_chat_service()
        result = await loop.run_in_executor(
            executor,
            chat_service.chat,
            request.conversation_id,
            request.user_message,
            request.access_token,
            request.bot_id,
            request.api_base
        )
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '对话失败'))
            
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"对话异常: {str(e)}\n{traceback.format_exc()}")


@router.get("/bazi/chat/history/{conversation_id}", summary="获取对话历史")
async def get_conversation_history(conversation_id: str):
    """
    获取对话历史
    
    - **conversation_id**: 对话 ID
    
    返回对话历史记录
    """
    try:
        loop = asyncio.get_event_loop()
        chat_service = get_chat_service()
        result = await loop.run_in_executor(
            executor,
            chat_service.get_conversation_history,
            conversation_id
        )
        
        return result
            
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"获取历史异常: {str(e)}\n{traceback.format_exc()}")


@router.delete("/bazi/chat/{conversation_id}", summary="删除对话")
async def delete_conversation(conversation_id: str):
    """
    删除对话
    
    - **conversation_id**: 对话 ID
    
    删除对话及其历史记录
    """
    try:
        loop = asyncio.get_event_loop()
        chat_service = get_chat_service()
        result = await loop.run_in_executor(
            executor,
            chat_service.delete_conversation,
            conversation_id
        )
        
        return result
            
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"删除对话异常: {str(e)}\n{traceback.format_exc()}")


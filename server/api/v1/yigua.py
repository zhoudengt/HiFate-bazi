#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一事一卦 API - 基于《周易》六十四卦进行占卜（类似 FateTell）
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.yigua_service import YiGuaService

router = APIRouter()

# 线程池
import os
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


class YiGuaRequest(BaseModel):
    """一事一卦请求模型"""
    question: str = Field(..., description="要占卜的问题", example="我这次投资能成功吗？")
    timestamp: Optional[str] = Field(None, description="时间戳（可选，ISO格式）")


@router.post("/bazi/yigua/divinate", summary="一事一卦占卜")
async def divinate(request: YiGuaRequest):
    """
    基于《周易》六十四卦进行占卜（类似 FateTell 的"一事一卦"功能）
    
    根据用户的问题，从六十四卦中抽取一卦，并给出解读和建议。
    
    特点：
    - 确定性：相同问题在同一时间会得到相同结果
    - 传统：基于《周易》六十四卦
    - 快速：本地计算，无需调用 LLM
    
    适用场景：
    - 决策参考
    - 运势占卜
    - 问题咨询
    
    - **question**: 要占卜的问题
    - **timestamp**: 时间戳（可选，ISO格式，用于增加随机性）
    
    返回卦的信息和解读
    """
    try:
        # 解析时间戳
        timestamp = None
        if request.timestamp:
            try:
                timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            except:
                timestamp = None
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            YiGuaService.divinate,
            request.question,
            timestamp
        )
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '占卜失败'))
            
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"占卜异常: {str(e)}\n{traceback.format_exc()}")


@router.get("/bazi/yigua/list", summary="获取六十四卦列表")
async def get_gua_list():
    """
    获取《周易》六十四卦的完整列表
    
    返回所有卦的信息，包括卦名、拼音、含义、卦辞等
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            YiGuaService.get_all_gua_list
        )
        
        return result
            
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"获取列表异常: {str(e)}\n{traceback.format_exc()}")


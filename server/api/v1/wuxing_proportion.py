#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行占比分析API接口
提供五行占比查询和大模型流式分析功能
"""

import sys
import os
import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any

from server.services.wuxing_proportion_service import WuxingProportionService
from server.services.coze_stream_service import CozeStreamService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor

router = APIRouter()

# Coze Bot ID（五行占比分析专用）
WUXING_PROPORTION_BOT_ID = "7585498208202473523"


class WuxingProportionRequest(BaziBaseRequest):
    """五行占比查询请求模型"""
    pass


class WuxingProportionResponse(BaseModel):
    """五行占比查询响应模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/bazi/wuxing-proportion", response_model=WuxingProportionResponse, summary="查询五行占比")
async def get_wuxing_proportion(request: WuxingProportionRequest):
    """
    查询五行占比分析
    
    基于生辰八字统计五行占比（金木水火土），包括：
    - 五行占比统计（天干+地支，8个位置）
    - 四柱十神信息（主星和副星）
    - 旺衰分析结果
    - 相生相克关系
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    
    返回五行占比分析数据
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        result = WuxingProportionService.calculate_proportion(
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        if not result.get('success'):
            return WuxingProportionResponse(
                success=False,
                error=result.get('error', '计算失败')
            )
        
        # 添加转换信息到结果
        if result and isinstance(result, dict) and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
            result['conversion_info'] = conversion_info
        
        return WuxingProportionResponse(
            success=True,
            data=result
        )
    except Exception as e:
        import traceback
        print(f"❌ 五行占比查询失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


async def wuxing_proportion_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str
):
    """
    五行占比流式分析生成器
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
    
    Yields:
        SSE格式的流式数据
    """
    try:
        # 1. 发送开始消息
        start_msg = {
            'type': 'start',
            'statusText': '开始分析五行占比',
            'showAnalysis': True
        }
        yield f"data: {json.dumps(start_msg, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)
        
        # 2. 获取五行占比数据
        progress_msg = {
            'type': 'progress',
            'statusText': '正在计算五行占比...',
            'showAnalysis': True
        }
        yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
        
        proportion_data = WuxingProportionService.calculate_proportion(
            solar_date, solar_time, gender
        )
        
        if not proportion_data.get('success'):
            error_msg = {
                'type': 'error',
                'error': proportion_data.get('error', '计算失败'),
                'statusText': '分析失败',
                'showAnalysis': False
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 3. 构建大模型提示词
        progress_msg = {
            'type': 'progress',
            'statusText': '正在构建分析提示词...',
            'showAnalysis': True
        }
        yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
        
        prompt = WuxingProportionService.build_llm_prompt(proportion_data)
        
        if not prompt:
            error_msg = {
                'type': 'error',
                'error': '提示词构建失败',
                'statusText': '分析失败',
                'showAnalysis': False
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 4. 调用流式服务
        progress_msg = {
            'type': 'progress',
            'statusText': '正在调用大模型分析...',
            'showAnalysis': True
        }
        yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.1)
        
        # 初始化 Coze 流式服务
        try:
            coze_service = CozeStreamService(bot_id=WUXING_PROPORTION_BOT_ID)
        except Exception as e:
            error_msg = {
                'type': 'error',
                'error': f'Coze服务初始化失败: {str(e)}',
                'statusText': '分析失败',
                'showAnalysis': False
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 调用流式分析（使用自定义方法）
        try:
            # 创建新的服务实例（使用指定的bot_id）
            coze_service_custom = CozeStreamService(bot_id=WUXING_PROPORTION_BOT_ID)
            async for chunk in coze_service_custom.stream_custom_analysis(prompt):
                chunk_type = chunk.get('type', 'progress')
                
                if chunk_type == 'progress':
                    # 流式内容
                    progress_msg = {
                        'type': 'progress',
                        'content': chunk.get('content', ''),
                        'statusText': '正在生成分析...',
                        'showAnalysis': True
                    }
                    yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
                elif chunk_type == 'complete':
                    # 完成
                    complete_msg = {
                        'type': 'complete',
                        'content': chunk.get('content', ''),
                        'statusText': '分析完成',
                        'showAnalysis': True
                    }
                    yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
                elif chunk_type == 'error':
                    # 错误
                    error_msg = {
                        'type': 'error',
                        'error': chunk.get('content', '分析失败'),
                        'statusText': '分析失败',
                        'showAnalysis': False
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        except Exception as e:
            import traceback
            print(f"❌ 流式分析失败: {e}\n{traceback.format_exc()}")
            error_msg = {
                'type': 'error',
                'error': f'流式分析失败: {str(e)}',
                'statusText': '分析失败',
                'showAnalysis': False
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
    
    except Exception as e:
        import traceback
        print(f"❌ 流式生成器异常: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'error': f'分析失败: {str(e)}',
            'statusText': '分析失败',
            'showAnalysis': False
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


@router.post("/bazi/wuxing-proportion/stream", summary="五行占比流式分析")
async def stream_wuxing_proportion(request: WuxingProportionRequest):
    """
    五行占比流式分析接口
    
    使用大模型（Coze Bot）基于五行占比、十神、旺衰等信息进行流式分析
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    
    使用 Server-Sent Events (SSE) 实时返回分析结果
    """
    try:
        return StreamingResponse(
            wuxing_proportion_stream_generator(
                request.solar_date,
                request.solar_time,
                request.gender
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式分析失败: {str(e)}")


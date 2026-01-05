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
    request: WuxingProportionRequest,
    bot_id: Optional[str] = None
):
    """
    五行占比流式分析生成器
    
    先返回完整的五行占比数据，然后流式返回大模型分析
    
    Args:
        request: 五行占比请求（与普通接口相同）
        bot_id: Coze Bot ID（可选）
    
    Yields:
        SSE格式的流式数据
    """
    import traceback
    
    try:
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 2. 获取五行占比数据
        proportion_data = WuxingProportionService.calculate_proportion(
            final_solar_date, final_solar_time, request.gender
        )
        
        if not proportion_data.get('success'):
            error_msg = {
                'type': 'error',
                'content': proportion_data.get('error', '计算失败')
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 3. 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            proportion_data['conversion_info'] = conversion_info
        
        # 4. 构建响应数据（与普通接口一致）
        response_data = {
            'success': True,
            'data': proportion_data
        }
        
        # 5. 先发送完整的五行占比数据（type: "data"）
        data_msg = {
            'type': 'data',
            'content': response_data
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        
        # 6. 构建大模型提示词
        prompt = WuxingProportionService.build_llm_prompt(proportion_data)
        
        if not prompt:
            # 没有提示词，直接返回完成
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        
        # 7. 确定使用的 bot_id
        actual_bot_id = bot_id or WUXING_PROPORTION_BOT_ID
        
        # 8. 创建Coze流式服务
        try:
            coze_service = CozeStreamService(bot_id=actual_bot_id)
        except ValueError as e:
            # 配置缺失，跳过大模型分析
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        
        # 9. 流式生成大模型分析
        async for chunk in coze_service.stream_custom_analysis(prompt):
            chunk_type = chunk.get('type', 'progress')
            
            if chunk_type == 'progress':
                msg = {
                    'type': 'progress',
                    'content': chunk.get('content', '')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)
            elif chunk_type == 'complete':
                msg = {
                    'type': 'complete',
                    'content': chunk.get('content', '')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return
            elif chunk_type == 'error':
                msg = {
                    'type': 'error',
                    'content': chunk.get('content', '分析失败')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return
                
    except Exception as e:
        error_msg = {
            'type': 'error',
            'content': f"流式生成五行占比分析失败: {str(e)}\n{traceback.format_exc()}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


@router.post("/bazi/wuxing-proportion/stream", summary="五行占比流式分析")
async def stream_wuxing_proportion(request: WuxingProportionRequest):
    """
    五行占比流式分析接口
    
    与 /bazi/wuxing-proportion 接口相同的输入，但以SSE流式方式返回数据：
    1. 首先返回完整的五行占比数据（type: "data"）
    2. 然后流式返回大模型分析（type: "progress"）
    3. 最后返回完成标记（type: "complete"）
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD（当calendar_type=lunar时，可为农历日期）
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    - **calendar_type**: 历法类型：solar(阳历) 或 lunar(农历)，默认solar
    - **location**: 出生地点（用于时区转换，优先级1）
    - **latitude**: 纬度（用于时区转换，优先级2）
    - **longitude**: 经度（用于时区转换和真太阳时计算，优先级2）
    
    **返回格式**：
    SSE流式响应，每行格式：`data: {"type": "data|progress|complete|error", "content": ...}`
    
    **示例**：
    ```
    data: {"type": "data", "content": {"success": true, "data": {...}}}
    data: {"type": "progress", "content": "五行分析："}
    data: {"type": "progress", "content": "您的八字..."}
    data: {"type": "complete", "content": "完整的大模型分析内容"}
    ```
    """
    try:
        return StreamingResponse(
            wuxing_proportion_stream_generator(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"流式查询五行占比异常: {str(e)}\n{traceback.format_exc()}"
        )


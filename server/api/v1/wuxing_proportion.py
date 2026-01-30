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
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any

from server.services.wuxing_proportion_service import WuxingProportionService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
        
        # >>> 缓存检查（五行占比固定，不随时间变化）<<<
        cache_key = generate_cache_key("wuxing", final_solar_date, final_solar_time, request.gender)
        cached = get_cached_result(cache_key, "wuxing-proportion")
        if cached:
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                cached['conversion_info'] = conversion_info
            return WuxingProportionResponse(success=True, data=cached)
        # >>> 缓存检查结束 <<<
        
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
        
        # >>> 缓存写入 <<<
        set_cached_result(cache_key, result, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        # 添加转换信息到结果
        if result and isinstance(result, dict) and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
            result['conversion_info'] = conversion_info
        
        return WuxingProportionResponse(
            success=True,
            data=result
        )
    except Exception as e:
        import traceback
        logger.error(f"❌ 五行占比查询失败: {e}", exc_info=True)
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
    import time
    
    # 记录开始时间和前端输入
    api_start_time = time.time()
    frontend_input = {
        'solar_date': request.solar_date,
        'solar_time': request.solar_time,
        'gender': request.gender,
        'calendar_type': request.calendar_type,
        'location': request.location,
        'latitude': request.latitude,
        'longitude': request.longitude
    }
    llm_first_token_time = None
    llm_output_chunks = []
    llm_start_time = None
    
    try:
        # ✅ 性能优化：立即返回首条消息，让用户感知到连接已建立
        # 这个优化将首次响应时间从 24秒 降低到 <1秒
        # ✅ 架构优化：移除无意义的进度消息，直接开始数据处理
        # 详见：docs/standards/08_数据编排架构规范.md
        
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 3. 使用统一数据服务获取数据
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'wuxing_proportion': True  # 统一数据服务会自动组装
        }
        
        unified_data = await BaziDataOrchestrator.fetch_data(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            modules=modules,
            use_cache=True,
            parallel=True,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            preprocessed=True
        )
        
        # 4. 提取已组装好的数据
        proportion_data = unified_data.get('wuxing_proportion')
        if not proportion_data or not proportion_data.get('success'):
            error_msg = {
                'type': 'error',
                'content': '获取五行占比数据失败'
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 5. 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            proportion_data['conversion_info'] = conversion_info
        
        # 6. 构建响应数据（与普通接口一致）
        response_data = {
            'success': True,
            'data': proportion_data
        }
        
        # 7. 先发送完整的五行占比数据（type: "data"）
        data_msg = {
            'type': 'data',
            'content': response_data
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        
        # 8. 构建 input_data（结构化数据，传递给 Coze Bot）
        input_data = {
            "proportions": proportion_data.get('proportions', {}),
            "element_relations": proportion_data.get('element_relations', {}),
            "ten_gods": proportion_data.get('ten_gods', {}),
            "wangshuai": proportion_data.get('wangshuai', {})
        }
        
        # 9. 格式化数据（JSON字符串，传递给 Coze Bot）
        formatted_data = json.dumps(input_data, ensure_ascii=False, indent=2)
        
        # 10. 确定使用的 bot_id（百炼平台不使用，但保留以兼容）
        # 注意：现在通过数据库配置选择平台，bot_id 主要用于 Coze 平台
        actual_bot_id = bot_id
        
        # 11. 创建 LLM 流式服务（根据数据库配置选择平台：coze 或 bailian）
        # 配置方式：在 service_configs 表中设置 WUXING_PROPORTION_LLM_PLATFORM = "bailian" 使用千问模型
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            from server.services.bailian_stream_service import BailianStreamService
            llm_service = LLMServiceFactory.get_service(scene="wuxing_proportion", bot_id=actual_bot_id)
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
        
        # 12. 流式生成大模型分析（传递 formatted_data，根据配置的平台生成内容）
        llm_start_time = time.time()
        has_content = False
        
        # 百炼平台不需要 bot_id，Coze 平台需要
        stream_kwargs = {}
        if hasattr(llm_service, 'bot_id') and llm_service.bot_id:
            stream_kwargs['bot_id'] = actual_bot_id
        
        async for chunk in llm_service.stream_analysis(formatted_data, **stream_kwargs):
            chunk_type = chunk.get('type', 'progress')
            
            # 记录第一个token时间
            if llm_first_token_time is None and chunk_type == 'progress':
                llm_first_token_time = time.time()
            
            if chunk_type == 'progress':
                content = chunk.get('content', '')
                if content:
                    llm_output_chunks.append(content)
                    has_content = True
                msg = {
                    'type': 'progress',
                    'content': content
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)
            elif chunk_type == 'complete':
                complete_content = chunk.get('content', '')
                if complete_content:
                    llm_output_chunks.append(complete_content)
                    has_content = True
                msg = {
                    'type': 'complete',
                    'content': complete_content
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
        
        # 13. 记录交互数据到数据库（异步，不阻塞）
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
        llm_output = ''.join(llm_output_chunks)
        
        try:
            from server.services.user_interaction_logger import get_user_interaction_logger
            logger_instance = get_user_interaction_logger()
            logger_instance.log_function_usage_async(
                function_type='wuxing',
                function_name='八字命理-五行占比分析',
                frontend_api='/api/v1/bazi/wuxing-proportion/stream',
                frontend_input=frontend_input,
                input_data=input_data,
                llm_output=llm_output,
                api_response_time_ms=api_response_time_ms,
                llm_first_token_time_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
                llm_total_time_ms=llm_total_time_ms,
                round_number=1,
                bot_id=actual_bot_id,
                llm_api='bailian_api' if isinstance(llm_service, BailianStreamService) else 'coze_api',
                status='success' if has_content else 'failed',
                streaming=True
            )
        except Exception as e:
            logger.warning(f"[五行占比流式] 数据库记录失败: {e}", exc_info=True)
                
    except Exception as e:
        error_msg = {
            'type': 'error',
            'content': f"流式生成五行占比分析失败: {str(e)}\n{traceback.format_exc()}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        try:
            api_end_time = time.time()
            api_response_time_ms = int((api_end_time - api_start_time) * 1000)
            from server.services.user_interaction_logger import get_user_interaction_logger
            logger_instance = get_user_interaction_logger()
            logger_instance.log_function_usage_async(
                function_type='wuxing',
                function_name='八字命理-五行占比分析',
                frontend_api='/api/v1/bazi/wuxing-proportion/stream',
                frontend_input=frontend_input,
                input_data={},
                llm_output='',
                api_response_time_ms=api_response_time_ms,
                llm_first_token_time_ms=None,
                llm_total_time_ms=None,
                round_number=1,
                bot_id=actual_bot_id,
                llm_api='coze_api',  # 默认值
                status='failed',
                error_message=str(e),
                streaming=True
            )
        except Exception as log_error:
            logger.warning(f"[五行占比流式] 错误记录失败: {log_error}", exc_info=True)


@router.post("/bazi/wuxing-proportion/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def wuxing_proportion_test(request: WuxingProportionRequest):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot）
    
    返回与流式接口相同格式的结构化数据（JSON），供评测脚本使用。
    确保 Coze 和百炼平台使用相同的输入数据。
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    
    **返回格式**：
    {
        "success": true,
        "input_data": {...},  # 结构化数据
        "formatted_data": "JSON字符串",  # 格式化后的JSON字符串
        "formatted_data_length": 1234
    }
    """
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
        
        # 2. 使用统一数据服务获取数据（与流式接口一致）
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'wuxing_proportion': True
        }
        
        unified_data = await BaziDataOrchestrator.fetch_data(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            modules=modules,
            use_cache=True,
            parallel=True,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            preprocessed=True
        )
        
        proportion_data = unified_data.get('wuxing_proportion')
        if not proportion_data or not proportion_data.get('success'):
            return {
                "success": False,
                "error": "获取五行占比数据失败"
            }
        
        # 4. 构建 input_data（结构化数据，与流式接口一致）
        input_data = {
            "proportions": proportion_data.get('proportions', {}),
            "element_relations": proportion_data.get('element_relations', {}),
            "ten_gods": proportion_data.get('ten_gods', {}),
            "wangshuai": proportion_data.get('wangshuai', {})
        }
        
        # 5. 格式化数据（JSON字符串，与流式接口一致）
        formatted_data = json.dumps(input_data, ensure_ascii=False, indent=2)
        
        # 6. 返回格式化后的数据
        return {
            "success": True,
            "input_data": input_data,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "usage": {
                "description": "此接口返回的结构化数据可以直接用于 Coze Bot 或百炼智能体的输入（使用 {{input}} 占位符）",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/bazi/wuxing-proportion/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}", "calendar_type": "{request.calendar_type or "solar"}"}}\''
            }
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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


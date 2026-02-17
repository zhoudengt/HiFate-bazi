#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行占比分析API接口
提供五行占比查询和大模型流式分析功能
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.api.base.stream_handler import BaseAnalysisStreamHandler
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)
from server.services.wuxing_proportion_service import WuxingProportionService

router = APIRouter()
logger = logging.getLogger(__name__)


class WuxingStreamHandler(BaseAnalysisStreamHandler):
    """五行占比流式分析 - 继承 BaseAnalysisStreamHandler"""

    scene = "wuxing_proportion"
    function_type = "wuxing"
    function_name = "八字命理-五行占比分析"
    frontend_api = "/api/v1/bazi/wuxing-proportion/stream"

    def get_modules(self, request: Any) -> Dict[str, Any]:
        return {'bazi': True, 'wangshuai': True, 'wuxing_proportion': True}

    def extract_and_validate(self, unified_data: Dict[str, Any], request: Any) -> Any:
        proportion_data = unified_data.get('wuxing_proportion')
        if not proportion_data or not proportion_data.get('success'):
            raise ValueError('获取五行占比数据失败')
        return proportion_data

    def get_initial_data_chunk(
        self,
        extracted_data: Any,
        conversion_info: Dict[str, Any],
        request: Any
    ) -> Optional[Dict[str, Any]]:
        proportion_data = extracted_data.copy()
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            proportion_data['conversion_info'] = conversion_info
        return {'success': True, 'data': proportion_data}

    def format_for_llm(self, extracted_data: Any) -> str:
        return _format_wuxing_for_llm(extracted_data)

    def get_llm_cache_key(self, formatted_text: str, input_data_for_log: Dict) -> str:
        return f"llm_wuxing:{hashlib.md5(formatted_text.encode()).hexdigest()}"

    def get_cache_namespace(self) -> str:
        return "llm-wuxing"

    def set_cached_llm(self, key: str, content: str, ttl: Optional[int] = None) -> None:
        try:
            set_cached_result(key, {'content': content}, L2_TTL * 24)
        except Exception as e:
            logger.warning(f"[五行占比] LLM 缓存写入失败: {e}")


def _format_wuxing_for_llm(proportion_data: Dict[str, Any]) -> str:
    """
    将五行占比数据格式化为人类可读的中文描述（用于传给大模型）
    
    优化点：
    1. 去除重复的喜神/忌神数据（原数据中重复3次）
    2. 去除冗余的反向关系（produced_by/controlled_by）
    3. 将 JSON 转换为简洁的中文描述，减少 token 数量
    
    Args:
        proportion_data: 五行占比完整数据
        
    Returns:
        str: 格式化后的中文描述（约300字符，原JSON约2700字符）
    """
    lines = []
    
    # 1. 五行占比
    proportions = proportion_data.get('proportions', {})
    if proportions:
        # 按占比从高到低排序
        sorted_elements = sorted(
            proportions.items(),
            key=lambda x: x[1].get('percentage', 0),
            reverse=True
        )
        parts = []
        for element, data in sorted_elements:
            pct = data.get('percentage', 0)
            details = ''.join(data.get('details', []))
            parts.append(f"{element}{pct}%({details})")
        lines.append(f"【五行占比】{'、'.join(parts)}")
    
    # 2. 旺衰和喜忌（只取一次，避免重复）
    wangshuai = proportion_data.get('wangshuai', {})
    if wangshuai:
        ws_level = wangshuai.get('wangshuai', '')
        total_score = wangshuai.get('total_score', 0)
        
        # 优先使用 final_xi_ji 中的五行喜忌（最终结果）
        final_xi_ji = wangshuai.get('final_xi_ji', {})
        xi_elements = final_xi_ji.get('xi_shen_elements') or wangshuai.get('xi_shen_elements', [])
        ji_elements = final_xi_ji.get('ji_shen_elements') or wangshuai.get('ji_shen_elements', [])
        
        xi_str = ''.join(xi_elements) if xi_elements else '无'
        ji_str = ''.join(ji_elements) if ji_elements else '无'
        
        lines.append(f"【旺衰】{ws_level}({total_score}分)，喜用五行：{xi_str}，忌讳五行：{ji_str}")
        
        # 调候信息
        tiaohou = wangshuai.get('tiaohou', {})
        if tiaohou:
            season = tiaohou.get('season', '')
            desc = tiaohou.get('description', '')
            if season and desc:
                lines.append(f"【调候】{desc}")
    
    # 3. 十神
    ten_gods = proportion_data.get('ten_gods', {})
    if ten_gods:
        pillar_names = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
        parts = []
        for pillar in ['year', 'month', 'day', 'hour']:
            pillar_data = ten_gods.get(pillar, {})
            main_star = pillar_data.get('main_star', '')
            if main_star:
                parts.append(f"{pillar_names[pillar]}{main_star}")
        if parts:
            lines.append(f"【十神】{'、'.join(parts)}")
    
    # 4. 五行关系（只取生克，去除反向的被生被克）
    element_relations = proportion_data.get('element_relations', {})
    if element_relations:
        # 生关系
        produces = element_relations.get('produces', [])
        if produces:
            produce_parts = [f"{r['from']}生{r['to']}" for r in produces]
            lines.append(f"【相生】{'、'.join(produce_parts)}")
        
        # 克关系
        controls = element_relations.get('controls', [])
        if controls:
            control_parts = [f"{r['from']}克{r['to']}" for r in controls]
            lines.append(f"【相克】{'、'.join(control_parts)}")
    
    return '\n'.join(lines)


class WuxingProportionRequest(BaziBaseRequest):
    """五行占比查询请求模型"""
    pass


class WuxingProportionResponse(BaseModel):
    """五行占比查询响应模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None



_WUXING_HANDLER = WuxingStreamHandler()


async def wuxing_proportion_stream_generator(
    request: WuxingProportionRequest,
    bot_id: Optional[str] = None
):
    """
    五行占比流式分析生成器（基于 BaseAnalysisStreamHandler）
    
    先返回完整的五行占比数据，然后流式返回大模型分析
    """
    async for chunk in _WUXING_HANDLER.stream_generator(request, bot_id=bot_id):
        yield chunk


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


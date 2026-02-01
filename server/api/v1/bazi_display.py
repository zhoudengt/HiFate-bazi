#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字前端展示 API - 提供前端友好的数据格式
"""

import sys
import os
import logging
import json
from fastapi import APIRouter, HTTPException, Request, Body, Depends
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError
from typing import Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_display_service import (
    BaziDisplayService, 
    _determine_current_dayun_by_jiaoyun,
    _calculate_default_liunian
)
from server.services.shensha_sort_service import sort_shensha
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result,
    L2_TTL, get_current_date_str
)
from server.utils.api_error_handler import api_error_handler
from server.utils.async_executor import get_executor
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.orchestrators.modules_config import get_modules_config

router = APIRouter()


class BaziDisplayRequest(BaziBaseRequest):
    """八字展示请求模型"""
    pass


class FortuneDisplayRequest(BaziDisplayRequest):
    """大运流年流月统一请求模型"""
    current_time: Optional[str] = Field(None, description="当前时间（可选），格式：YYYY-MM-DD HH:MM 或 '今'")
    dayun_index: Optional[int] = Field(None, description="大运索引（可选，已废弃，优先使用dayun_year_start和dayun_year_end）")
    dayun_year_start: Optional[int] = Field(None, description="大运起始年份（可选），指定要显示的大运的起始年份")
    dayun_year_end: Optional[int] = Field(None, description="大运结束年份（可选），指定要显示的大运的结束年份")
    target_year: Optional[int] = Field(None, description="目标年份（可选），用于计算该年份的流月")
    quick_mode: Optional[bool] = Field(True, description="快速模式，只计算当前大运，其他大运异步预热（默认True）")
    async_warmup: Optional[bool] = Field(True, description="是否触发异步预热（默认True）")
    
    @field_validator('current_time', mode='before')
    @classmethod
    def validate_current_time(cls, v):
        """验证当前时间格式 - 支持 '今' 参数（mode='before' 确保在类型转换前处理）"""
        if v is None:
            return v
        # ✅ 支持 "今" 参数（在类型转换前检查）
        if isinstance(v, str) and v.strip() == "今":
            # 转换为当前时间字符串，避免后续验证失败
            from datetime import datetime
            converted = datetime.now().strftime("%Y-%m-%d %H:%M")
            return converted  # 返回转换后的时间字符串
        # 保留原有验证逻辑
        if isinstance(v, str):
            try:
                from datetime import datetime
                datetime.strptime(v, '%Y-%m-%d %H:%M')
            except ValueError:
                raise ValueError("current_time 参数格式错误，应为 '今' 或 'YYYY-MM-DD HH:MM' 格式")
        return v


@dataclass
class FortuneDisplayRequestWithMode:
    """包装类：包含请求模型和是否为'今'模式"""
    request: FortuneDisplayRequest
    use_jin_mode: bool = False


@router.post("/bazi/pan/display", summary="排盘展示（前端优化）")
@api_error_handler
async def get_pan_display(request: BaziDisplayRequest):
    """
    获取排盘数据（前端优化格式）
    
    返回数组格式的四柱数据，便于前端 v-for 渲染
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    
    返回前端友好的排盘数据，包括：
    - 基本信息
    - 四柱数组（便于前端循环渲染）
    - 五行统计（包含百分比）
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    
    架构：通过 BaziDataOrchestrator 统一获取数据（数据总线设计）
    """
    # 处理农历输入和时区转换
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request.solar_date,
        request.solar_time,
        request.calendar_type or "solar",
        request.location,
        request.latitude,
        request.longitude
    )

    cache_key = generate_cache_key("pan", final_solar_date, final_solar_time, request.gender)
    cached = get_cached_result(cache_key, "pan/display")
    if cached:
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            cached['conversion_info'] = conversion_info
        return cached

    try:
        # ✅ 通过编排层统一获取数据（数据总线设计）
        modules = get_modules_config('pan_display')
        orchestrator_data = await BaziDataOrchestrator.fetch_data(
            final_solar_date,
            final_solar_time,
            request.gender,
            modules=modules,
            preprocessed=True,  # 已经过 process_input 处理
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # ✅ 从编排层数据组装响应（保持响应结构完全不变）
        result = _assemble_pan_display_response(orchestrator_data)
        
    except BrokenPipeError:
        logger.warning("客户端断开连接，计算中断")
        return {
            "success": False,
            "error": "客户端连接已断开",
            "error_type": "client_disconnected"
        }
    except OSError as e:
        if e.errno == 32:  # Broken pipe
            logger.warning("客户端断开连接，计算中断")
            return {
                "success": False,
                "error": "客户端连接已断开",
                "error_type": "client_disconnected"
            }
        raise
    except Exception as e:
        logger.error(f"pan/display 计算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")

    if result.get('success'):
        set_cached_result(cache_key, result, L2_TTL)
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            result['conversion_info'] = conversion_info
        return result
    raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))


def _assemble_pan_display_response(orchestrator_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从编排层数据组装 pan/display 响应
    
    保持与原 BaziDisplayService.get_pan_display() 返回格式完全一致
    
    Args:
        orchestrator_data: 编排层返回的数据
        
    Returns:
        dict: 与原接口完全一致的响应结构
    """
    bazi_data_raw = orchestrator_data.get('bazi', {})
    
    # ✅ 修复：处理嵌套结构 {'bazi': {...}, 'rizhu': '...', 'matched_rules': [...]}
    # BaziService.calculate_bazi_full 返回嵌套结构，内层 'bazi' 才是实际的八字数据
    if isinstance(bazi_data_raw, dict) and 'bazi' in bazi_data_raw and isinstance(bazi_data_raw.get('bazi'), dict):
        # 嵌套结构：提取内层 bazi 数据
        bazi_data = bazi_data_raw.get('bazi', {})
        # 同时提取嵌套结构中的 rizhu 和 matched_rules（如果存在）
        rizhu_from_bazi = bazi_data_raw.get('rizhu')
        rules_from_bazi = bazi_data_raw.get('matched_rules', [])
    else:
        # 非嵌套结构（兼容旧格式）
        bazi_data = bazi_data_raw
        rizhu_from_bazi = None
        rules_from_bazi = []
    
    rizhu_data = orchestrator_data.get('rizhu', {}) or rizhu_from_bazi
    rules_data = orchestrator_data.get('rules', []) or rules_from_bazi
    personality_data = orchestrator_data.get('personality', {})
    
    if not bazi_data:
        return {"success": False, "error": "八字计算失败"}
    
    # 复用现有格式化逻辑
    formatted_pillars = BaziDisplayService._format_pillars_for_display(bazi_data)
    wuxing_data = BaziDisplayService._format_wuxing_for_display(bazi_data, formatted_pillars)
    
    # ✅ 处理日柱解析：优先使用 personality 数据，其次使用 rizhu 数据
    rizhu_analysis = None
    if personality_data and personality_data.get('has_data'):
        rizhu_analysis = {
            "rizhu": personality_data.get('rizhu', ''),
            "gender": personality_data.get('gender', ''),
            "descriptions": personality_data.get('descriptions', []),
            "summary": personality_data.get('summary', '')
        }
    elif rizhu_data:
        # rizhu 模块返回的是 RizhuLiujiaziService 的数据，格式不同
        rizhu_analysis = rizhu_data
    
    # ✅ 筛选婚姻规则（与原逻辑一致）
    marriage_rules_all = [
        rule for rule in rules_data 
        if 'marriage' in str(rule.get('rule_type', '')).lower() or '婚' in str(rule.get('rule_type', ''))
    ]
    # 按优先级排序
    marriage_rules = sorted(
        marriage_rules_all, 
        key=lambda x: x.get('priority', 0), 
        reverse=True
    )
    
    return {
        "success": True,
        "pan": {
            "basic": bazi_data.get('basic_info', {}),
            "pillars": formatted_pillars,
            "wuxing": wuxing_data,
            "rizhu_analysis": rizhu_analysis,
            "marriage_rules": marriage_rules
        }
    }


# ✅ 依赖函数：预处理请求体，处理 "今" 参数
async def parse_fortune_request(request: Request) -> FortuneDisplayRequestWithMode:
    """
    解析请求体，支持 '今' 参数（从 request.state 获取 body，避免重复读取）
    
    Returns:
        FortuneDisplayRequestWithMode: 包含请求模型和是否为"今"模式的包装对象
    """
    # 尝试从 request.state 获取已解析的 JSON（SecurityMiddleware 已解析）
    if hasattr(request.state, 'body_json') and request.state.body_json is not None:
        request_data = request.state.body_json.copy()  # 复制，避免修改原始数据
    elif hasattr(request.state, 'body') and request.state.body:
        # 如果 state 中有 body 但未解析，则解析
        try:
            if isinstance(request.state.body, bytes):
                request_data = json.loads(request.state.body.decode('utf-8'))
            else:
                request_data = json.loads(request.state.body)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"请求体 JSON 解析失败: {e}")
            raise HTTPException(status_code=400, detail=f"请求体格式错误: {str(e)}")
    else:
        # 如果 state 中没有，尝试直接读取（可能失败，因为中间件已读取）
        try:
            body_bytes = await request.body()
            request_data = json.loads(body_bytes.decode('utf-8'))
        except (RuntimeError, AttributeError) as e:
            logger.error(f"无法读取请求体: {e}")
            raise HTTPException(status_code=400, detail="无法读取请求体，请检查中间件配置")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"请求体 JSON 解析失败: {e}")
            raise HTTPException(status_code=400, detail=f"请求体格式错误: {str(e)}")
    
    # ✅ 检查是否为"今"模式（SecurityMiddleware 或 validator 已处理）
    use_jin_mode = getattr(request.state, 'use_jin_mode', False)
    # 如果 SecurityMiddleware 已处理，use_jin_mode 已在 request.state 中设置
    # 如果 validator 已处理，current_time 已是时间字符串，通过时间差判断
    if not use_jin_mode and isinstance(request_data, dict) and request_data.get('current_time'):
        current_time_str = request_data.get('current_time')
        if isinstance(current_time_str, str) and len(current_time_str) == 16:  # YYYY-MM-DD HH:MM 格式
            try:
                parsed_time = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M")
                now = datetime.now()
                # 如果时间差在1分钟内，认为是"今"模式
                if abs((parsed_time - now).total_seconds()) < 60:
                    use_jin_mode = True
                    request.state.use_jin_mode = True
            except ValueError:
                pass
    
    # 创建请求模型对象（此时 current_time 已经是时间字符串，不会触发验证错误）
    try:
        request_model = FortuneDisplayRequest(**request_data)
        return FortuneDisplayRequestWithMode(request=request_model, use_jin_mode=use_jin_mode)
    except ValidationError as e:
        logger.error(f"创建请求模型失败: {e}", exc_info=True)
        # 提取更友好的错误信息
        errors = []
        for error in e.errors():
            errors.append(f"{'.'.join(str(x) for x in error.get('loc', []))}: {error.get('msg', '')}")
        raise HTTPException(status_code=400, detail=f"请求参数验证失败: {', '.join(errors)}")
    except Exception as e:
        logger.error(f"创建请求模型异常: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")


@router.post("/bazi/fortune/display", summary="大运流年流月统一接口（性能优化）")
@api_error_handler
async def get_fortune_display(request_wrapper: FortuneDisplayRequestWithMode = Depends(parse_fortune_request)):
    """
    获取大运流年流月数据（统一接口，一次返回所有数据）
    
    **性能优化**：通过统一编排层获取数据，复用缓存，减少重复计算
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当calendar_type=lunar时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    - **current_time**: 当前时间（可选）(YYYY-MM-DD HH:MM) 或 '今'
    - **dayun_index**: 大运索引（可选），指定要显示的大运，只返回该大运范围内的流年（性能优化）
    - **dayun_year_start**: 大运起始年份（可选）
    - **dayun_year_end**: 大运结束年份（可选）
    - **target_year**: 目标年份（可选），用于计算该年份的流月
    
    返回前端友好的数据，包括：
    - 大运数据（当前大运、大运列表、起运交运信息）
    - 流年数据（当前流年、流年列表）
    - 流月数据（当前流月、流月列表）
    - conversion_info: 转换信息（如果进行了农历转换或时区转换）
    
    架构：通过 BaziDataOrchestrator 统一获取数据（数据总线设计）
    """
    request = request_wrapper.request
    use_jin_mode = request_wrapper.use_jin_mode

    # 处理农历输入和时区转换
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
        request.longitude
    )

    # 解析 current_time（如果使用"今"模式，使用当前时间的 datetime 对象）
    current_time = None
    if request.current_time:
        if use_jin_mode:
            current_time = datetime.now()
        else:
            try:
                current_time = datetime.strptime(str(request.current_time), "%Y-%m-%d %H:%M")
            except ValueError as e:
                logger.error(f"时间解析失败: {request.current_time}, 错误: {e}")
                raise ValueError(f"current_time 参数格式错误，应为 '今' 或 'YYYY-MM-DD HH:MM' 格式，但收到: {request.current_time}")
    
    # 如果没有提供 current_time，使用当前系统时间
    if current_time is None:
        current_time = datetime.now()

    current_date = get_current_date_str()
    cache_key = generate_cache_key(
        "fortune", final_solar_date, final_solar_time, request.gender, current_date,
        dayun_index=request.dayun_index,
        dayun_year_start=request.dayun_year_start,
        dayun_year_end=request.dayun_year_end,
        target_year=request.target_year
    )
    cached = get_cached_result(cache_key, "fortune/display")
    if cached:
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            cached['conversion_info'] = conversion_info
        return cached

    try:
        # ✅ 通过编排层统一获取数据（数据总线设计）
        modules = get_modules_config('fortune_display')
        orchestrator_data = await BaziDataOrchestrator.fetch_data(
            final_solar_date,
            final_solar_time,
            request.gender,
            modules=modules,
            current_time=current_time,
            preprocessed=True,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # ✅ 从编排层数据组装响应（保持响应结构完全不变）
        result = _assemble_fortune_display_response(
            orchestrator_data,
            final_solar_date,
            current_time,
            request.dayun_index,
            request.dayun_year_start,
            request.dayun_year_end,
            request.target_year
        )
        
    except BrokenPipeError:
        logger.warning("客户端断开连接，计算中断")
        return {
            "success": False,
            "error": "客户端连接已断开",
            "error_type": "client_disconnected"
        }
    except OSError as e:
        if e.errno == 32:  # Broken pipe
            logger.warning("客户端断开连接，计算中断")
            return {
                "success": False,
                "error": "客户端连接已断开",
                "error_type": "client_disconnected"
            }
        raise
    except Exception as e:
        logger.error(f"fortune/display 计算失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")

    if result.get('success'):
        set_cached_result(cache_key, result, L2_TTL)
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            result['conversion_info'] = conversion_info
        return result
    raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))


def _assemble_fortune_display_response(
    orchestrator_data: Dict[str, Any],
    solar_date: str,
    current_time: datetime,
    dayun_index: Optional[int] = None,
    dayun_year_start: Optional[int] = None,
    dayun_year_end: Optional[int] = None,
    target_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    从编排层数据组装 fortune/display 响应
    
    保持与原 BaziDisplayService.get_fortune_display() 返回格式完全一致
    
    Args:
        orchestrator_data: 编排层返回的数据
        solar_date: 阳历日期
        current_time: 当前时间
        dayun_index: 大运索引（可选）
        dayun_year_start: 大运起始年份（可选）
        dayun_year_end: 大运结束年份（可选）
        target_year: 目标年份（可选）
        
    Returns:
        dict: 与原接口完全一致的响应结构
    """
    # 1. 提取编排层数据
    bazi_data = orchestrator_data.get('bazi', {})
    interface_data = orchestrator_data.get('bazi_interface', {})
    detail_data = orchestrator_data.get('detail', {})
    dayun_sequence = orchestrator_data.get('dayun', [])
    liunian_sequence = orchestrator_data.get('liunian', [])
    liuyue_sequence = orchestrator_data.get('liuyue', [])
    
    if not bazi_data:
        return {"success": False, "error": "八字计算失败"}
    
    # 2. 提取 detail 中的信息
    details = detail_data.get('details', {}) if detail_data else {}
    qiyun_info = details.get('qiyun', {})
    jiaoyun_info = details.get('jiaoyun', {})
    dayun_info = details.get('dayun', {})
    
    # 如果 dayun_sequence 为空，从 details 中获取
    if not dayun_sequence:
        dayun_sequence = details.get('dayun_sequence', [])
    
    # 3. 确定当前大运
    birth_year = int(solar_date.split('-')[0])
    current_dayun = None
    
    if jiaoyun_info:
        # 优先使用交运日期判断
        current_dayun = _determine_current_dayun_by_jiaoyun(
            current_time, dayun_sequence, jiaoyun_info, birth_year
        )
    
    # 如果交运日期判断失败，降级到虚岁判断
    if current_dayun is None:
        current_year = current_time.year
        current_age = current_year - birth_year + 1  # 虚岁计算
        
        for dayun in dayun_sequence:
            age_range = dayun.get('age_range', {})
            if age_range:
                age_start = age_range.get('start', 0)
                age_end = age_range.get('end', 0)
                if age_start <= current_age <= age_end:
                    current_dayun = dayun
                    break
    
    # 4. 确定要显示的大运
    target_dayun = None
    resolved_dayun_index = dayun_index
    
    # 如果提供了年份范围，根据年份范围查找大运索引
    if dayun_year_start is not None and dayun_year_end is not None and dayun_index is None:
        for dayun in dayun_sequence:
            dayun_year_start_actual = dayun.get('year_start')
            dayun_year_end_actual = dayun.get('year_end')
            step = dayun.get('step')
            
            # 精确匹配
            if dayun_year_start_actual == dayun_year_start and dayun_year_end_actual == dayun_year_end:
                resolved_dayun_index = step
                break
            # 包含匹配
            elif dayun_year_start_actual and dayun_year_end_actual:
                if dayun_year_start_actual <= dayun_year_start <= dayun_year_end_actual:
                    resolved_dayun_index = step
                    break
    
    if resolved_dayun_index is not None:
        for dayun in dayun_sequence:
            if dayun.get('step') == resolved_dayun_index:
                target_dayun = dayun
                break
    else:
        target_dayun = current_dayun
    
    if not target_dayun:
        target_dayun = current_dayun or (dayun_sequence[0] if dayun_sequence else None)
    
    # 5. 格式化大运列表
    formatted_dayun_list = []
    for dayun in dayun_sequence:
        formatted = BaziDisplayService._format_dayun_item(dayun)
        if current_dayun and dayun.get('step') == current_dayun.get('step'):
            formatted['is_current'] = True
        formatted_dayun_list.append(formatted)
    
    # 6. 处理流年数据
    current_year = current_time.year
    
    # 优先使用当前大运下的流年序列
    if current_dayun and not current_dayun.get('is_xiaoyun', False):
        liunian_sequence = current_dayun.get('liunian_sequence', liunian_sequence)
    elif not liunian_sequence:
        liunian_sequence = details.get('liunian_sequence', [])
    
    # 确定当前流年
    current_liunian = None
    for liunian in liunian_sequence:
        if liunian.get('year') == current_year:
            current_liunian = liunian
            break
    
    # 如果流年序列中没有当前年份，计算默认流年数据
    if current_liunian is None:
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        day_stem = bazi_pillars.get('day', {}).get('stem', '')
        current_liunian = _calculate_default_liunian(current_year, birth_year, day_stem)
    
    # 格式化流年列表
    formatted_liunian_list = []
    for liunian in liunian_sequence:
        formatted = BaziDisplayService._format_liunian_item(liunian)
        if liunian.get('year') == current_year:
            formatted['is_current'] = True
        formatted_liunian_list.append(formatted)
    
    # 7. 处理流月数据
    target_year_for_liuyue = target_year or (current_liunian.get('year') if current_liunian else current_year)
    
    # 从流年序列中获取流月
    target_liunian = None
    for liunian in liunian_sequence:
        if liunian.get('year') == target_year_for_liuyue:
            target_liunian = liunian
            break
    
    if target_liunian:
        liuyue_sequence = target_liunian.get('liuyue_sequence', liuyue_sequence)
    elif not liuyue_sequence:
        liuyue_sequence = details.get('liuyue_sequence', [])
    
    # 确定当前流月
    current_month = current_time.month
    current_liuyue = None
    for liuyue in liuyue_sequence:
        if liuyue.get('month') == current_month:
            current_liuyue = liuyue
            break
    
    # 格式化流月列表
    formatted_liuyue_list = []
    for liuyue in liuyue_sequence:
        formatted = BaziDisplayService._format_liuyue_item(liuyue)
        if current_liuyue and liuyue.get('month') == current_liuyue.get('month'):
            formatted['is_current'] = True
        formatted_liuyue_list.append(formatted)
    
    # 8. 格式化四柱详细信息
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    bazi_details = bazi_data.get('details', {})
    formatted_pillars = {}
    for pillar_type in ['year', 'month', 'day', 'hour']:
        pillar_details = bazi_details.get(pillar_type, {})
        formatted_pillars[pillar_type] = {
            "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
            "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
            "main_star": pillar_details.get('main_star', ''),
            "hidden_stars": pillar_details.get('hidden_stars', []),
            "sub_stars": pillar_details.get('sub_stars', pillar_details.get('hidden_stars', [])),
            "hidden_stems": pillar_details.get('hidden_stems', []),
            "star_fortune": pillar_details.get('star_fortune', ''),
            "self_sitting": pillar_details.get('self_sitting', ''),
            "kongwang": pillar_details.get('kongwang', ''),
            "nayin": pillar_details.get('nayin', ''),
            "deities": sort_shensha(pillar_details.get('deities', []))
        }
    
    # 9. 获取司令字段（从 interface_data 中提取）
    commander = ''
    if interface_data:
        other_info = interface_data.get('other_info', {})
        if isinstance(other_info, dict):
            commander_element = other_info.get('commander_element', '')
            if commander_element:
                commander = commander_element[0] if len(commander_element) > 0 else ''
    
    # 10. 组装响应
    return {
        "success": True,
        "pillars": formatted_pillars,
        "commander": commander,
        "dayun": {
            "current": BaziDisplayService._format_dayun_item(current_dayun or dayun_info),
            "list": formatted_dayun_list,
            "qiyun": {
                "date": qiyun_info.get('date', ''),
                "age_display": qiyun_info.get('age_display', ''),
                "description": qiyun_info.get('description', '')
            },
            "jiaoyun": {
                "date": jiaoyun_info.get('date', ''),
                "age_display": jiaoyun_info.get('age_display', ''),
                "description": jiaoyun_info.get('description', '')
            }
        },
        "liunian": {
            "current": BaziDisplayService._format_liunian_item(current_liunian) if current_liunian else None,
            "list": formatted_liunian_list
        },
        "liuyue": {
            "current": BaziDisplayService._format_liuyue_item(current_liuyue or (liuyue_sequence[0] if liuyue_sequence else {})),
            "list": formatted_liuyue_list,
            "target_year": target_year_for_liuyue
        },
        "details": {
            "dayun_sequence": dayun_sequence
        }
    }


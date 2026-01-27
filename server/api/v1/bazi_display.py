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
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_display_service import BaziDisplayService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result,
    L2_TTL, get_current_date_str
)

router = APIRouter()

# 线程池
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


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
        
        # >>> 缓存检查 <<<
        cache_key = generate_cache_key("pan", final_solar_date, final_solar_time, request.gender)
        cached = get_cached_result(cache_key, "pan/display")
        if cached:
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                cached['conversion_info'] = conversion_info
            return cached
        # >>> 缓存检查结束 <<<
        
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                executor,
                BaziDisplayService.get_pan_display,
                final_solar_date,
                final_solar_time,
                request.gender
            )
        except BrokenPipeError:
            # 客户端断开连接，返回友好的错误响应
            logger.warning("客户端断开连接，计算中断")
            return {
                "success": False,
                "error": "客户端连接已断开",
                "error_type": "client_disconnected"
            }
        except OSError as e:
            # 处理其他可能的 Broken pipe 相关错误
            if e.errno == 32:  # Broken pipe
                logger.warning("客户端断开连接，计算中断")
                return {
                    "success": False,
                    "error": "客户端连接已断开",
                    "error_type": "client_disconnected"
                }
            raise  # 其他 OSError 继续抛出
        
        if result.get('success'):
            # >>> 缓存写入 <<<
            set_cached_result(cache_key, result, L2_TTL)
            # >>> 缓存写入结束 <<<
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")


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
async def get_fortune_display(request_wrapper: FortuneDisplayRequestWithMode = Depends(parse_fortune_request)):
    """
    获取大运流年流月数据（统一接口，一次返回所有数据）
    
    **性能优化**：只计算一次，避免重复调用
    
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
    """
    try:
        # 从依赖函数获取 request 和 use_jin_mode
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
        
        # ✅ 解析 current_time（如果使用"今"模式，使用当前时间的 datetime 对象）
        current_time = None
        if request.current_time:
            if use_jin_mode:
                # "今"模式：直接使用当前时间
                current_time = datetime.now()
            else:
                # 正常模式：解析时间字符串
                try:
                    current_time = datetime.strptime(str(request.current_time), "%Y-%m-%d %H:%M")
                except ValueError as e:
                    logger.error(f"时间解析失败: {request.current_time}, 错误: {e}")
                    raise ValueError(f"current_time 参数格式错误，应为 '今' 或 'YYYY-MM-DD HH:MM' 格式，但收到: {request.current_time}")
        
        # >>> 缓存检查（fortune 按天+参数缓存）<<<
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
        # >>> 缓存检查结束 <<<
        
        # ✅ 使用统一数据服务（内部适配，接口层完全不动）
        from server.orchestrators.bazi_data_service import BaziDataService
        
        # 使用 BaziDisplayService 直接调用（传递快速模式参数）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDisplayService.get_fortune_display,
            final_solar_date,
            final_solar_time,
            request.gender,
            current_time,
            request.dayun_index,
            request.dayun_year_start,
            request.dayun_year_end,
            request.target_year,
            request.quick_mode if request.quick_mode is not None else True,  # quick_mode
            request.async_warmup if request.async_warmup is not None else True  # async_warmup
        )
        
        if result.get('success'):
            # >>> 缓存写入 <<<
            set_cached_result(cache_key, result, L2_TTL)
            # >>> 缓存写入结束 <<<
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                result['conversion_info'] = conversion_info
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get('error', '计算失败'))
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"计算异常: {str(e)}\n{traceback.format_exc()}")


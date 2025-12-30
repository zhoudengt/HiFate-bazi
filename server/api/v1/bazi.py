#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算API接口
"""

import sys
import os
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.utils.data_validator import validate_bazi_data
from server.services.bazi_interface_service import BaziInterfaceService
from server.services.bazi_detail_service import BaziDetailService
from server.utils import bazi_cache
from src.tool.LunarConverter import LunarConverter
from server.utils.timezone_converter import convert_local_to_solar_time, format_datetime_for_bazi
from server.utils.bazi_input_processor import BaziInputProcessor
from server.api.v1.models.bazi_base_models import BaziBaseRequest

router = APIRouter()

# 根据CPU核心数动态调整线程池大小（优化高并发性能）
import os
cpu_count = os.cpu_count() or 4
# 线程池大小 = CPU核心数 * 2，但不超过100
max_workers = min(cpu_count * 2, 100)
executor = ThreadPoolExecutor(max_workers=max_workers)


# 向后兼容：保留原函数，内部调用公共方法
def process_date_time_input(solar_date: str, 
                            solar_time: str,
                            calendar_type: str = "solar",
                            location: Optional[str] = None,
                            latitude: Optional[float] = None,
                            longitude: Optional[float] = None) -> Tuple[str, str, dict]:
    """
    处理日期时间输入（支持农历输入和时区转换）
    
    向后兼容函数，内部调用 BaziInputProcessor.process_input()
    
    Args:
        solar_date: 日期字符串（阳历或农历）
        solar_time: 时间字符串
        calendar_type: 历法类型（solar/lunar）
        location: 地点字符串（可选）
        latitude: 纬度（可选）
        longitude: 经度（可选）
    
    Returns:
        (final_solar_date, final_solar_time, conversion_info) - 最终用于计算的阳历日期、时间和转换信息
    """
    return BaziInputProcessor.process_input(
        solar_date=solar_date,
        solar_time=solar_time,
        calendar_type=calendar_type,
        location=location,
        latitude=latitude,
        longitude=longitude
    )

# 尝试导入限流装饰器（如果可用）
try:
    from slowapi import Limiter
    limiter = None  # 将在路由中从 app.state 获取
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False


class BaziRequest(BaziBaseRequest):
    """八字计算请求模型"""
    pass
    
    @validator('solar_time')
    def validate_time(cls, v):
        """验证时间格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        """验证性别"""
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v
    
    @validator('calendar_type')
    def validate_calendar_type(cls, v):
        """验证历法类型"""
        if v not in ['solar', 'lunar']:
            raise ValueError('历法类型必须为 solar 或 lunar')
        return v


class BaziResponse(BaseModel):
    """八字计算响应模型"""
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None


@router.post("/bazi/calculate", response_model=BaziResponse, summary="计算生辰八字")
async def calculate_bazi(request: BaziRequest, http_request: Request):
    """
    计算生辰八字（带缓存优化）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当 calendar_type=lunar 时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认 solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    
    返回完整的八字信息和匹配的规则
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = process_date_time_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 检查缓存（使用转换后的日期时间）
        cache_key_parts = [
            final_solar_date,
            final_solar_time,
            request.gender,
            request.calendar_type or "solar",
            request.location or "",
            str(request.latitude or ""),
            str(request.longitude or "")
        ]
        cached_result = bazi_cache.get(
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        if cached_result is not None:
            # 验证缓存数据的格式
            if not isinstance(cached_result, dict):
                # 缓存数据格式错误，清除缓存
                bazi_cache.clear()
                cached_result = None
            else:
                # 添加转换信息到结果
                if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                    cached_result['conversion_info'] = conversion_info
                # 返回缓存结果
                return BaziResponse(
                    success=True,
                    data=cached_result
                )
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziService.calculate_bazi_full,
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        # ✅ 统一类型验证：确保所有字段类型正确（防止gRPC序列化问题）
        result = validate_bazi_data(result.get('bazi', result)) if isinstance(result, dict) else result
        
        # 验证结果格式
        if not isinstance(result, dict):
            raise ValueError(f"计算结果格式错误: 期望字典类型，实际是 {type(result)}")
        
        # 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            result['conversion_info'] = conversion_info
        
        # 缓存结果
        bazi_cache.set(
            final_solar_date,
            final_solar_time,
            request.gender,
            result
        )
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"计算失败: {str(e)}\n{error_trace}")
        error_detail = f"计算失败: {str(e)}\n{error_trace}"
        raise HTTPException(status_code=500, detail=error_detail)


class BaziInterfaceRequest(BaziBaseRequest):
    """八字界面信息请求模型"""
    name: Optional[str] = Field(None, description="姓名", example="张三")


@router.post("/bazi/interface", response_model=BaziResponse, summary="生成八字界面信息")
async def generate_bazi_interface(request: BaziInterfaceRequest, http_request: Request):
    """
    生成八字界面信息（包含命宫、身宫、胎元、胎息、命卦等）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当 calendar_type=lunar 时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **name**: 姓名（可选）
    - **calendar_type**: 历法类型 (solar/lunar)，默认 solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    
    返回完整的八字界面信息（JSON格式）
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = process_date_time_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 检查缓存（包含位置信息）
        cached_result = bazi_cache.get(
            final_solar_date,
            final_solar_time,
            request.gender,
            name=request.name or "",
            location=request.location or "未知地",
            latitude=request.latitude or 39.00,
            longitude=request.longitude or 120.00
        )
        
        if cached_result is not None:
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                cached_result['conversion_info'] = conversion_info
            return BaziResponse(
                success=True,
                data=cached_result
            )
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziInterfaceService.generate_interface_full,
            final_solar_date,
            final_solar_time,
            request.gender,
            request.name or "",
            request.location or "未知地",
            request.latitude or 39.00,
            request.longitude or 120.00
        )
        
        # 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            result['conversion_info'] = conversion_info
        
        # 缓存结果
        bazi_cache.set(
            final_solar_date,
            final_solar_time,
            request.gender,
            result,
            name=request.name or "",
            location=request.location or "未知地",
            latitude=request.latitude or 39.00,
            longitude=request.longitude or 120.00
        )
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"生成失败: {str(e)}\n{error_trace}")
        error_detail = f"生成失败: {str(e)}\n{error_trace}"
        raise HTTPException(status_code=500, detail=error_detail)


class BaziDetailRequest(BaziBaseRequest):
    """八字详细计算请求模型"""
    current_time: Optional[str] = Field(None, description="当前时间，格式：YYYY-MM-DD HH:MM，用于计算大运流年，默认为当前系统时间", example="2024-01-01 12:00")
    
    @validator('current_time')
    def validate_current_time(cls, v):
        """验证当前时间格式"""
        if v is None:
            return v
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d %H:%M')
        except ValueError:
            raise ValueError('当前时间格式错误，应为 YYYY-MM-DD HH:MM')
        return v


@router.post("/bazi/detail", response_model=BaziResponse, summary="计算详细八字信息（包含大运流年）")
async def calculate_bazi_detail(request: BaziDetailRequest, http_request: Request):
    """
    计算详细八字信息（包含大运流年、流月、流日、流时等）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当 calendar_type=lunar 时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **current_time**: 当前时间 (YYYY-MM-DD HH:MM)，用于计算大运流年，可选
    - **calendar_type**: 历法类型 (solar/lunar)，默认 solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    
    返回完整的详细八字信息（包含大运流年序列）
    """
    try:
        from datetime import datetime
        
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = process_date_time_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 解析当前时间
        current_time = None
        if request.current_time:
            current_time = datetime.strptime(request.current_time, "%Y-%m-%d %H:%M")
        
        # 检查缓存（包含当前时间）
        current_time_str = request.current_time or datetime.now().strftime("%Y-%m-%d %H:%M")
        cached_result = bazi_cache.get(
            final_solar_date,
            final_solar_time,
            request.gender,
            current_time=current_time_str
        )
        
        if cached_result is not None:
            # 添加转换信息到结果
            if conversion_info.get('converted') or conversion_info.get('timezone_info'):
                cached_result['conversion_info'] = conversion_info
            return BaziResponse(
                success=True,
                data=cached_result
            )
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            BaziDetailService.calculate_detail_full,
            final_solar_date,
            final_solar_time,
            request.gender,
            current_time
        )
        
        # 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            result['conversion_info'] = conversion_info
        
        # 缓存结果
        bazi_cache.set(
            final_solar_date,
            final_solar_time,
            request.gender,
            result,
            current_time=current_time_str
        )
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


class ShengongMinggongRequest(BaziBaseRequest):
    """身宫命宫请求模型"""
    current_time: Optional[str] = Field(None, description="当前时间（可选），格式：YYYY-MM-DD HH:MM", example="2024-01-01 12:00")
    dayun_year_start: Optional[int] = Field(None, description="大运起始年份（可选），指定要显示的大运的起始年份", example=2020)
    dayun_year_end: Optional[int] = Field(None, description="大运结束年份（可选），指定要显示的大运的结束年份", example=2030)
    target_year: Optional[int] = Field(None, description="目标年份（可选），用于计算该年份的流月", example=2024)


@router.post("/bazi/shengong-minggong", response_model=BaziResponse, summary="获取身宫命宫详细信息")
async def get_shengong_minggong(request: ShengongMinggongRequest, http_request: Request):
    """
    获取身宫和命宫的详细信息（主星、藏干、星运、自坐、空亡、纳音、神煞等）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD) 或农历日期（当 calendar_type=lunar 时）
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **calendar_type**: 历法类型 (solar/lunar)，默认 solar
    - **location**: 出生地点（可选，用于时区转换）
    - **latitude**: 纬度（可选，用于时区转换）
    - **longitude**: 经度（可选，用于时区转换和真太阳时计算）
    
    返回身宫、命宫和四柱的详细信息
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = process_date_time_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 处理 current_time 参数
        current_time = None
        if request.current_time:
            from datetime import datetime
            current_time = datetime.strptime(request.current_time, "%Y-%m-%d %H:%M")
        
        # 在线程池中执行CPU密集型计算
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            _calculate_shengong_minggong_details,
            final_solar_date,
            final_solar_time,
            request.gender,
            current_time,
            request.dayun_year_start,
            request.dayun_year_end,
            request.target_year
        )
        
        # 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            result['conversion_info'] = conversion_info
        
        return BaziResponse(
            success=True,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"计算身宫命宫失败: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


def _calculate_shengong_minggong_details(
    solar_date: str, 
    solar_time: str, 
    gender: str,
    current_time: Optional[datetime] = None,
    dayun_year_start: Optional[int] = None,
    dayun_year_end: Optional[int] = None,
    target_year: Optional[int] = None
) -> dict:
    """
    计算身宫、命宫和胎元的详细信息
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        current_time: 当前时间（可选），用于确定当前大运
        dayun_year_start: 大运起始年份（可选），指定要显示的大运的起始年份
        dayun_year_end: 大运结束年份（可选），指定要显示的大运的结束年份
        target_year: 目标年份（可选），用于计算该年份的流月
        
    Returns:
        dict: 包含身宫、命宫、胎元和四柱详细信息的字典
    """
    import logging
    from server.utils.data_validator import DataValidator, ensure_dict
    
    logger = logging.getLogger(__name__)
    
    # ✅ 优化：并行获取身宫命宫和八字基础信息（无依赖关系）
    import concurrent.futures
    import threading
    
    def get_interface_data():
        """获取身宫和命宫的干支"""
        try:
            interface_data = BaziInterfaceService.generate_interface_full(
                solar_date, solar_time, gender, "", "未知地", 39.00, 120.00
            )
            return ensure_dict(interface_data, default={})
        except Exception as e:
            logger.error(f"调用 generate_interface_full 失败: {str(e)}", exc_info=True)
            raise ValueError(f"无法生成界面信息: {str(e)}")
    
    def get_bazi_data():
        """计算八字基础信息"""
        try:
            bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
            bazi_data = ensure_dict(bazi_result.get('bazi', {}), default={})
            bazi_pillars = ensure_dict(bazi_data.get('bazi_pillars', {}), default={})
            day_stem = bazi_pillars.get('day', {}).get('stem', '')
            
            if not day_stem:
                raise ValueError("无法获取日干信息")
            return bazi_data, bazi_pillars, day_stem
        except Exception as e:
            logger.error(f"计算八字基础信息失败: {str(e)}", exc_info=True)
            raise ValueError(f"无法计算八字基础信息: {str(e)}")
    
    # 并行执行（使用线程池）
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            interface_future = executor.submit(get_interface_data)
            bazi_future = executor.submit(get_bazi_data)
            
            # 等待两个任务完成
            interface_data = interface_future.result()
            bazi_data, bazi_pillars, day_stem = bazi_future.result()
            
            logger.info("✅ 并行获取身宫命宫和八字基础信息完成")
    except Exception as e:
        logger.error(f"并行执行失败: {str(e)}", exc_info=True)
        raise
    
    # 3. 获取身宫、命宫和胎元的干支（从格式化后的数据结构中获取）
    palaces = ensure_dict(interface_data.get('palaces', {}), default={})
    shengong_ganzhi = ''
    minggong_ganzhi = ''
    taiyuan_ganzhi = ''
    
    if palaces:
        # 从 palaces.body_palace.ganzhi 获取
        body_palace_info = palaces.get('body_palace', {})
        if isinstance(body_palace_info, dict):
            shengong_ganzhi = body_palace_info.get('ganzhi', '') or ''
        else:
            # 兼容旧格式（直接是字符串）
            shengong_ganzhi = str(body_palace_info) if body_palace_info else ''
        
        # 从 palaces.life_palace.ganzhi 获取
        life_palace_info = palaces.get('life_palace', {})
        if isinstance(life_palace_info, dict):
            minggong_ganzhi = life_palace_info.get('ganzhi', '') or ''
        else:
            # 兼容旧格式（直接是字符串）
            minggong_ganzhi = str(life_palace_info) if life_palace_info else ''
        
        # 从 palaces.fetal_origin.ganzhi 获取胎元
        fetal_origin_info = palaces.get('fetal_origin', {})
        if isinstance(fetal_origin_info, dict):
            taiyuan_ganzhi = fetal_origin_info.get('ganzhi', '') or ''
        else:
            # 兼容旧格式（直接是字符串）
            taiyuan_ganzhi = str(fetal_origin_info) if fetal_origin_info else ''
    
    # 如果从 palaces 中获取失败，尝试直接从顶层获取（兼容旧格式）
    if not shengong_ganzhi:
        shengong_ganzhi = str(interface_data.get('body_palace', '') or '')
    if not minggong_ganzhi:
        minggong_ganzhi = str(interface_data.get('life_palace', '') or '')
    if not taiyuan_ganzhi:
        taiyuan_ganzhi = str(interface_data.get('fetal_origin', '') or '')
    
    # 4. 如果仍然获取失败，尝试重新计算（回退机制）
    if not shengong_ganzhi or not minggong_ganzhi:
        logger.warning(f"无法从 interface_data 获取身宫或命宫，尝试重新计算")
        logger.debug(f"interface_data keys: {list(interface_data.keys())}, palaces: {palaces}")
        
        try:
            from src.analyzers.bazi_interface_analyzer import BaziInterfaceAnalyzer
            from src.tool.LunarConverter import LunarConverter
            
            analyzer = BaziInterfaceAnalyzer()
            converter = LunarConverter()
            
            # 获取农历日期
            lunar_result = converter.solar_to_lunar(solar_date, solar_time)
            lunar_date = ensure_dict(lunar_result.get('lunar_date', {}), default={})
            lunar_year = lunar_date.get('year', '')
            lunar_month = lunar_date.get('month', '')
            lunar_day = lunar_date.get('day', '')
            
            # 获取时支和月支
            bazi_pillars_result = ensure_dict(lunar_result.get('bazi_pillars', {}), default={})
            hour_pillar = ensure_dict(bazi_pillars_result.get('hour', {}), default={})
            month_pillar = ensure_dict(bazi_pillars_result.get('month', {}), default={})
            hour_branch = hour_pillar.get('branch', '')
            month_branch = month_pillar.get('branch', '')
            
            # 验证数据完整性
            if not lunar_year:
                raise ValueError(f"农历年份无效: {lunar_year}")
            if not lunar_month:
                raise ValueError(f"农历月份无效: {lunar_month}")
            if not lunar_day:
                raise ValueError(f"农历日期无效: {lunar_day}")
            if not hour_branch:
                raise ValueError(f"时支无效: {hour_branch}")
            if not month_branch:
                raise ValueError(f"月支无效: {month_branch}")
            
            # 转换为数字类型
            try:
                if isinstance(lunar_year, str):
                    lunar_year = int(lunar_year.strip()) if lunar_year.strip() else 0
                elif not isinstance(lunar_year, int):
                    lunar_year = int(lunar_year)
                
                if isinstance(lunar_month, str):
                    lunar_month = int(lunar_month.strip()) if lunar_month.strip() else 0
                elif not isinstance(lunar_month, int):
                    lunar_month = int(lunar_month)
                
                if isinstance(lunar_day, str):
                    lunar_day = int(lunar_day.strip()) if lunar_day.strip() else 0
                elif not isinstance(lunar_day, int):
                    lunar_day = int(lunar_day)
            except (ValueError, TypeError) as e:
                raise ValueError(f"农历日期转换失败: {e}")
            
            if lunar_year <= 0 or lunar_month <= 0 or lunar_day <= 0:
                raise ValueError(f"农历日期无效: {lunar_year}年{lunar_month}月{lunar_day}日")
            
            # 重新计算身宫和命宫
            logger.info(f"重新计算身宫命宫: lunar_year={lunar_year}, lunar_month={lunar_month}, lunar_day={lunar_day}, hour_branch={hour_branch}, month_branch={month_branch}")
            shengong_ganzhi = analyzer.get_body_palace(lunar_year, lunar_month, lunar_day, hour_branch, month_branch)
            minggong_ganzhi = analyzer.get_life_palace(lunar_year, lunar_month, lunar_day, hour_branch, month_branch)
            
            logger.info(f"重新计算成功: 身宫={shengong_ganzhi}, 命宫={minggong_ganzhi}")
            
        except Exception as e:
            logger.error(f"重新计算身宫命宫失败: {str(e)}", exc_info=True)
            raise ValueError(f"无法计算身宫或命宫。身宫: {shengong_ganzhi}, 命宫: {minggong_ganzhi}。错误: {str(e)}")
    
    # 5. 获取胎元干支（如果未获取到，则从月柱计算）
    if not taiyuan_ganzhi:
        try:
            # 获取月柱干支
            month_pillar = bazi_pillars.get('month', {})
            month_stem = month_pillar.get('stem', '')
            month_branch_char = month_pillar.get('branch', '')
            
            if month_stem and month_branch_char:
                month_stem_branch = month_stem + month_branch_char
                # 使用 BaziInterfaceAnalyzer 计算胎元
                from src.analyzers.bazi_interface_analyzer import BaziInterfaceAnalyzer
                analyzer = BaziInterfaceAnalyzer()
                taiyuan_ganzhi = analyzer.get_fetal_origin(month_stem_branch)
                logger.info(f"从月柱计算胎元: 月柱={month_stem_branch}, 胎元={taiyuan_ganzhi}")
            else:
                logger.warning(f"无法获取月柱信息，无法计算胎元: month_stem={month_stem}, month_branch={month_branch_char}")
        except Exception as e:
            logger.warning(f"计算胎元失败: {str(e)}", exc_info=True)
    
    # 6. 验证干支格式（应该是2个字符）
    if not shengong_ganzhi or len(shengong_ganzhi) != 2:
        raise ValueError(f"身宫干支格式错误: {shengong_ganzhi}（应为2个字符）")
    if not minggong_ganzhi or len(minggong_ganzhi) != 2:
        raise ValueError(f"命宫干支格式错误: {minggong_ganzhi}（应为2个字符）")
    if not taiyuan_ganzhi or len(taiyuan_ganzhi) != 2:
        logger.warning(f"胎元干支格式错误或为空: {taiyuan_ganzhi}，将尝试重新计算")
        # 如果胎元格式错误，尝试重新计算
        try:
            month_pillar = bazi_pillars.get('month', {})
            month_stem = month_pillar.get('stem', '')
            month_branch_char = month_pillar.get('branch', '')
            if month_stem and month_branch_char:
                month_stem_branch = month_stem + month_branch_char
                from src.analyzers.bazi_interface_analyzer import BaziInterfaceAnalyzer
                analyzer = BaziInterfaceAnalyzer()
                taiyuan_ganzhi = analyzer.get_fetal_origin(month_stem_branch)
                if not taiyuan_ganzhi or len(taiyuan_ganzhi) != 2:
                    raise ValueError(f"胎元计算失败: {taiyuan_ganzhi}")
            else:
                raise ValueError(f"无法获取月柱信息: month_stem={month_stem}, month_branch={month_branch_char}")
        except Exception as e:
            logger.error(f"重新计算胎元失败: {str(e)}", exc_info=True)
            raise ValueError(f"胎元干支格式错误: {taiyuan_ganzhi}（应为2个字符）。错误: {str(e)}")
    
    # 7. 导入计算所需的模块
    from src.bazi_config.ten_gods_config import TenGodsCalculator
    from src.bazi_config.star_fortune_config import StarFortuneCalculator
    from src.bazi_config.deities_config import DeitiesCalculator
    from src.data.constants import HIDDEN_STEMS, NAYIN_MAP
    
    # 创建 WenZhenBazi 实例用于主星计算（与基本信息页面保持一致）
    from src.bazi_calculator import WenZhenBazi
    bazi_calc = WenZhenBazi(solar_date, solar_time, gender)
    
    # 5. 计算身宫详细信息
    shengong_stem = shengong_ganzhi[0]
    shengong_branch = shengong_ganzhi[1]
    
    ten_gods_calc = TenGodsCalculator()
    star_fortune_calc = StarFortuneCalculator()
    deities_calc = DeitiesCalculator()
    
    # 8. 计算身宫详细信息
    # 主星（使用与基本信息页面相同的计算方法，基于五行生克关系和阴阳属性）
    shengong_main_star = bazi_calc.get_main_star(day_stem, shengong_stem, 'month')
    
    # 藏干
    shengong_hidden_stems = HIDDEN_STEMS.get(shengong_branch, [])
    
    # 星运
    shengong_star_fortune = star_fortune_calc.get_stem_fortune(day_stem, shengong_branch)
    
    # 自坐
    shengong_self_sitting = star_fortune_calc.get_stem_fortune(shengong_stem, shengong_branch)
    
    # 空亡
    shengong_kongwang = star_fortune_calc.get_kongwang(shengong_ganzhi)
    
    # 纳音
    shengong_nayin = NAYIN_MAP.get((shengong_stem, shengong_branch), '')
    
    # 神煞（使用日柱神煞的计算方法，因为身宫通常与日柱相关）
    shengong_deities = deities_calc.calculate_day_deities(
        shengong_stem, shengong_branch, bazi_pillars
    )
    
    # 9. 计算命宫详细信息
    minggong_stem = minggong_ganzhi[0]
    minggong_branch = minggong_ganzhi[1]
    
    # 主星（使用与基本信息页面相同的计算方法，基于五行生克关系和阴阳属性）
    minggong_main_star = bazi_calc.get_main_star(day_stem, minggong_stem, 'month')
    
    # 藏干
    minggong_hidden_stems = HIDDEN_STEMS.get(minggong_branch, [])
    
    # 星运
    minggong_star_fortune = star_fortune_calc.get_stem_fortune(day_stem, minggong_branch)
    
    # 自坐
    minggong_self_sitting = star_fortune_calc.get_stem_fortune(minggong_stem, minggong_branch)
    
    # 空亡
    minggong_kongwang = star_fortune_calc.get_kongwang(minggong_ganzhi)
    
    # 纳音
    minggong_nayin = NAYIN_MAP.get((minggong_stem, minggong_branch), '')
    
    # 神煞
    minggong_deities = deities_calc.calculate_day_deities(
        minggong_stem, minggong_branch, bazi_pillars
    )
    
    # 10. 计算胎元详细信息（与身宫相同的字段结构）
    taiyuan_stem = taiyuan_ganzhi[0]
    taiyuan_branch = taiyuan_ganzhi[1]
    
    # 主星（使用与基本信息页面相同的计算方法，基于五行生克关系和阴阳属性）
    taiyuan_main_star = bazi_calc.get_main_star(day_stem, taiyuan_stem, 'month')
    
    # 藏干
    taiyuan_hidden_stems = HIDDEN_STEMS.get(taiyuan_branch, [])
    
    # 星运
    taiyuan_star_fortune = star_fortune_calc.get_stem_fortune(day_stem, taiyuan_branch)
    
    # 自坐
    taiyuan_self_sitting = star_fortune_calc.get_stem_fortune(taiyuan_stem, taiyuan_branch)
    
    # 空亡
    taiyuan_kongwang = star_fortune_calc.get_kongwang(taiyuan_ganzhi)
    
    # 纳音
    taiyuan_nayin = NAYIN_MAP.get((taiyuan_stem, taiyuan_branch), '')
    
    # 神煞
    taiyuan_deities = deities_calc.calculate_day_deities(
        taiyuan_stem, taiyuan_branch, bazi_pillars
    )
    
    # 11. 格式化四柱数据（与前端期望格式一致）
    details = bazi_data.get('details', {})
    formatted_pillars = {}
    for pillar_type in ['year', 'month', 'day', 'hour']:
        pillar_data = details.get(pillar_type, {})
        pillar_info = bazi_pillars.get(pillar_type, {})
        formatted_pillars[pillar_type] = {
            "stem": {"char": pillar_info.get('stem', '')},
            "branch": {"char": pillar_info.get('branch', '')},
            "main_star": pillar_data.get('main_star', ''),
            "hidden_stems": pillar_data.get('hidden_stems', []),
            "star_fortune": pillar_data.get('star_fortune', ''),
            "self_sitting": pillar_data.get('self_sitting', ''),
            "kongwang": pillar_data.get('kongwang', ''),
            "nayin": pillar_data.get('nayin', ''),
            "deities": pillar_data.get('deities', [])
        }
    
    # 12. 获取大运流年流月数据（支持参数传递）
    dayun_data = {}
    liunian_data = {}
    liuyue_data = {}
    
    try:
        from server.services.bazi_display_service import BaziDisplayService
        from datetime import datetime
        
        # 使用传入的 current_time，如果没有则使用系统当前时间
        if current_time is None:
            current_time = datetime.now()
        
        # 调用 BaziDisplayService.get_fortune_display 获取大运流年流月数据
        # 支持参数传递：dayun_year_start, dayun_year_end, target_year
        fortune_result = BaziDisplayService.get_fortune_display(
            solar_date,
            solar_time,
            gender,
            current_time=current_time,
            dayun_index=None,
            dayun_year_start=dayun_year_start,
            dayun_year_end=dayun_year_end,
            target_year=target_year
        )
        
        if fortune_result.get('success'):
            # 提取大运数据（当前大运、大运列表、起运、交运）- 与 /bazi/fortune/display 格式一致
            dayun_info = fortune_result.get('dayun', {})
            dayun_data = {
                "current": dayun_info.get('current'),
                "list": dayun_info.get('list', []),  # ✅ 添加大运列表
                "qiyun": dayun_info.get('qiyun', {}),
                "jiaoyun": dayun_info.get('jiaoyun', {})
            }
            
            # 提取流年数据（当前流年、当前大运范围内的流年列表）- 与 /bazi/fortune/display 格式一致
            liunian_info = fortune_result.get('liunian', {})
            liunian_data = {
                "current": liunian_info.get('current'),
                "list": liunian_info.get('list', [])
            }
            
            # 提取流月数据（当前流月、当前年份的流月列表）- 与 /bazi/fortune/display 格式一致
            liuyue_info = fortune_result.get('liuyue', {})
            liuyue_data = {
                "current": liuyue_info.get('current'),
                "list": liuyue_info.get('list', []),
                "target_year": liuyue_info.get('target_year')  # ✅ 添加目标年份
            }
            
            logger.info(f"成功获取大运流年流月数据: 当前大运={dayun_data.get('current', {}).get('ganzhi', 'N/A')}, "
                       f"流年数量={len(liunian_data.get('list', []))}, 流月数量={len(liuyue_data.get('list', []))}")
        else:
            logger.warning(f"获取大运流年流月数据失败: {fortune_result.get('error', '未知错误')}")
            
    except Exception as e:
        # 如果获取大运流年流月数据失败，记录错误但不影响身宫命宫数据的返回
        logger.error(f"获取大运流年流月数据异常: {str(e)}", exc_info=True)
        # 返回空数据，保持向后兼容（格式与 /bazi/fortune/display 一致）
        dayun_data = {
            "current": None,
            "list": [],  # ✅ 添加空列表，保持格式一致
            "qiyun": {},
            "jiaoyun": {}
        }
        liunian_data = {
            "current": None,
            "list": []
        }
        liuyue_data = {
            "current": None,
            "list": [],
            "target_year": None  # ✅ 添加目标年份字段
        }
    
    # 13. 格式化返回数据
    return {
        "shengong": {
            "stem": {"char": shengong_stem},
            "branch": {"char": shengong_branch},
            "main_star": shengong_main_star,
            "hidden_stems": shengong_hidden_stems,
            "star_fortune": shengong_star_fortune,
            "self_sitting": shengong_self_sitting,
            "kongwang": shengong_kongwang,
            "nayin": shengong_nayin,
            "deities": shengong_deities
        },
        "minggong": {
            "stem": {"char": minggong_stem},
            "branch": {"char": minggong_branch},
            "main_star": minggong_main_star,
            "hidden_stems": minggong_hidden_stems,
            "star_fortune": minggong_star_fortune,
            "self_sitting": minggong_self_sitting,
            "kongwang": minggong_kongwang,
            "nayin": minggong_nayin,
            "deities": minggong_deities
        },
        "taiyuan": {
            "stem": {"char": taiyuan_stem},
            "branch": {"char": taiyuan_branch},
            "main_star": taiyuan_main_star,
            "hidden_stems": taiyuan_hidden_stems,
            "star_fortune": taiyuan_star_fortune,
            "self_sitting": taiyuan_self_sitting,
            "kongwang": taiyuan_kongwang,
            "nayin": taiyuan_nayin,
            "deities": taiyuan_deities
        },
        "pillars": formatted_pillars,
        "dayun": dayun_data,
        "liunian": liunian_data,
        "liuyue": liuyue_data
    }


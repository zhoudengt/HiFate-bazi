#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字统一数据服务 - 统一管理大运流年、特殊流年数据的获取
支持7个标准参数，确保数据一致性
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_detail_service import BaziDetailService
from server.services.special_liunian_service import SpecialLiunianService
from server.services.bazi_display_service import BaziDisplayService
from server.utils.bazi_input_processor import BaziInputProcessor
from server.models.bazi_detail import BaziDetailModel
from server.models.dayun import DayunModel
from server.models.liunian import LiunianModel
from server.models.special_liunian import SpecialLiunianModel

logger = logging.getLogger(__name__)


class BaziDataService:
    """八字统一数据服务 - 统一管理大运流年、特殊流年数据的获取"""
    
    # 统一的大运模式（用于5个分析接口）
    DEFAULT_DAYUN_MODE = 'current_with_neighbors'  # 当前大运及前后各一个（共3个）
    
    # 统一的年份范围（用于5个分析接口）
    DEFAULT_TARGET_YEARS = [2025, 2026, 2027]  # 默认查询未来3年
    
    @staticmethod
    async def get_dayun_sequence(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: str = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        mode: str = "current",
        count: Optional[int] = None,
        indices: Optional[List[int]] = None,
        current_time: Optional[datetime] = None
    ) -> List[DayunModel]:
        """
        获取大运序列（支持7个标准参数）
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别（male/female）
            calendar_type: 历法类型（solar/lunar）
            location: 出生地点（可选）
            latitude: 纬度（可选）
            longitude: 经度（可选）
            mode: 查询模式（'count', 'current', 'current_with_neighbors', 'indices'）
            count: 数量（仅用于 count 模式）
            indices: 索引列表（用于 indices 模式）
            current_time: 当前时间（可选）
            
        Returns:
            List[DayunModel]: 大运序列
        """
        # ✅ 优化：使用缓存（减少重复计算）
        try:
            from server.utils.cache_key_generator import CacheKeyGenerator
            from server.utils.cache_multi_level import get_multi_cache
            
            cache_key = CacheKeyGenerator.generate_dayun_key(
                solar_date, solar_time, gender,
                calendar_type, location, latitude, longitude,
                mode, count
            )
            
            cache = get_multi_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"[BaziDataService] 大运序列缓存命中")
                return cached_result
        except Exception as e:
            logger.debug(f"[BaziDataService] 缓存查询失败（继续计算）: {e}")
        
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type, location, latitude, longitude
        )
        
        # 2. 调用底层服务获取数据
        loop = asyncio.get_event_loop()
        executor = None
        
        detail_result = await loop.run_in_executor(
            executor,
            BaziDetailService.calculate_detail_full,
            final_solar_date,
            final_solar_time,
            gender,
            current_time,
            None,  # dayun_index（不指定，获取所有大运）
            None   # target_year
        )
        
        if not detail_result:
            logger.warning("calculate_detail_full() 返回空结果，无法获取大运序列")
            return []
        
        # 3. 提取大运序列
        details = detail_result.get('details', {})
        dayun_sequence_raw = details.get('dayun_sequence', [])
        
        # 4. 根据模式筛选大运
        if current_time is None:
            current_time = datetime.now()
        
        birth_year = int(final_solar_date.split('-')[0])
        filtered_dayuns = BaziDataService._filter_dayuns_by_mode(
            dayun_sequence_raw, current_time, birth_year, mode, count, indices
        )
        
        # 5. 转换为模型
        dayun_models = []
        for dayun in filtered_dayuns:
            dayun_model = DayunModel(
                step=dayun.get('step', 0),
                stem=dayun.get('stem', ''),
                branch=dayun.get('branch', ''),
                ganzhi=f"{dayun.get('stem', '')}{dayun.get('branch', '')}",
                year_start=dayun.get('year_start'),
                year_end=dayun.get('year_end'),
                age_range=dayun.get('age_range'),
                age_display=dayun.get('age_display'),
                nayin=dayun.get('nayin'),
                main_star=dayun.get('main_star'),
                hidden_stems=dayun.get('hidden_stems', []),
                hidden_stars=dayun.get('hidden_stars', []),
                star_fortune=dayun.get('star_fortune'),
                self_sitting=dayun.get('self_sitting'),
                kongwang=dayun.get('kongwang'),
                deities=dayun.get('deities', []),
                details=dayun
            )
            dayun_models.append(dayun_model)
        
        # ✅ 优化：写入缓存
        try:
            from server.utils.cache_key_generator import CacheKeyGenerator
            from server.utils.cache_multi_level import get_multi_cache
            
            cache_key = CacheKeyGenerator.generate_dayun_key(
                solar_date, solar_time, gender,
                calendar_type, location, latitude, longitude,
                mode, count
            )
            
            cache = get_multi_cache()
            # 设置缓存TTL（24小时）
            cache.l2.ttl = 86400
            cache.set(cache_key, dayun_models)
            # 恢复默认TTL
            cache.l2.ttl = 3600
        except Exception as e:
            logger.debug(f"[BaziDataService] 缓存写入失败（不影响业务）: {e}")
        
        return dayun_models
    
    @staticmethod
    async def get_liunian_sequence(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: str = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        dayun_mode: str = "current",
        target_years: Optional[List[int]] = None,
        current_time: Optional[datetime] = None,
        detail_result: Optional[Dict[str, Any]] = None  # ✅ 优化：允许传入已计算的 detail_result，避免重复计算
    ) -> List[LiunianModel]:
        """
        获取流年序列（支持7个标准参数）
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别（male/female）
            calendar_type: 历法类型（solar/lunar）
            location: 出生地点（可选）
            latitude: 纬度（可选）
            longitude: 经度（可选）
            dayun_mode: 大运模式（用于筛选流年）
            target_years: 目标年份列表（可选，用于筛选流年）
            current_time: 当前时间（可选）
            
        Returns:
            List[LiunianModel]: 流年序列
        """
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type, location, latitude, longitude
        )
        
        # 2. 调用底层服务获取数据
        loop = asyncio.get_event_loop()
        executor = None
        
        detail_result = await loop.run_in_executor(
            executor,
            BaziDetailService.calculate_detail_full,
            final_solar_date,
            final_solar_time,
            gender,
            current_time,
            None,  # dayun_index（不指定，获取所有大运）
            None   # target_year
        )
        
        if not detail_result:
            logger.warning("calculate_detail_full() 返回空结果，无法获取流年序列")
            return []
        
        # 3. 提取流年序列
        details = detail_result.get('details', {})
        liunian_sequence_raw = details.get('liunian_sequence', [])
        
        # 4. 根据大运模式筛选流年（如果需要）
        if dayun_mode != "all":
            # 获取对应的大运
            dayuns = await BaziDataService.get_dayun_sequence(
                solar_date, solar_time, gender, calendar_type, location, latitude, longitude,
                mode=dayun_mode, current_time=current_time
            )
            
            # 筛选属于这些大运的流年
            if dayuns:
                dayun_year_ranges = []
                for dayun in dayuns:
                    if dayun.year_start and dayun.year_end:
                        dayun_year_ranges.append((dayun.year_start, dayun.year_end))
                
                filtered_liunians = []
                for liunian in liunian_sequence_raw:
                    year = liunian.get('year', 0)
                    for year_start, year_end in dayun_year_ranges:
                        if year_start <= year <= year_end:
                            filtered_liunians.append(liunian)
                            break
                liunian_sequence_raw = filtered_liunians
        
        # 5. 根据目标年份筛选（如果需要）
        if target_years:
            liunian_sequence_raw = [
                liunian for liunian in liunian_sequence_raw
                if liunian.get('year') in target_years
            ]
        
        # 6. 转换为模型
        liunian_models = []
        for liunian in liunian_sequence_raw:
            liunian_model = LiunianModel(
                year=liunian.get('year', 0),
                stem=liunian.get('stem', ''),
                branch=liunian.get('branch', ''),
                ganzhi=f"{liunian.get('stem', '')}{liunian.get('branch', '')}",
                age=liunian.get('age'),
                age_display=liunian.get('age_display'),
                nayin=liunian.get('nayin'),
                main_star=liunian.get('main_star'),
                hidden_stems=liunian.get('hidden_stems', []),
                hidden_stars=liunian.get('hidden_stars', []),
                star_fortune=liunian.get('star_fortune'),
                self_sitting=liunian.get('self_sitting'),
                kongwang=liunian.get('kongwang'),
                deities=liunian.get('deities', []),
                relations=liunian.get('relations', []),
                liuyue_sequence=liunian.get('liuyue_sequence', []),
                details=liunian
            )
            liunian_models.append(liunian_model)
        
        # ✅ 优化：写入缓存
        try:
            from server.utils.cache_key_generator import CacheKeyGenerator
            from server.utils.cache_multi_level import get_multi_cache
            
            cache_key = CacheKeyGenerator.generate_liunian_key(
                solar_date, solar_time, gender,
                calendar_type, location, latitude, longitude,
                target_years
            )
            
            cache = get_multi_cache()
            cache.l2.ttl = 86400
            cache.set(cache_key, liunian_models)
            cache.l2.ttl = 3600
        except Exception as e:
            logger.debug(f"[BaziDataService] 流年序列缓存写入失败（不影响业务）: {e}")
        
        return liunian_models
    
    @staticmethod
    async def get_special_liunians(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: str = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        dayun_mode: str = DEFAULT_DAYUN_MODE,
        dayun_count: int = 8,
        current_time: Optional[datetime] = None
    ) -> List[SpecialLiunianModel]:
        """
        获取特殊流年（有关系的流年：冲合刑害、岁运并临等）
        支持7个标准参数，确保数据一致性
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别（male/female）
            calendar_type: 历法类型（solar/lunar）
            location: 出生地点（可选）
            latitude: 纬度（可选）
            longitude: 经度（可选）
            dayun_mode: 大运模式（默认：current_with_neighbors）
            dayun_count: 要查询的大运数量（默认8个）
            current_time: 当前时间（可选）
            
        Returns:
            List[SpecialLiunianModel]: 特殊流年列表
        """
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type, location, latitude, longitude
        )
        
        # 2. 获取大运序列（根据模式）
        dayuns = await BaziDataService.get_dayun_sequence(
            solar_date, solar_time, gender, calendar_type, location, latitude, longitude,
            mode=dayun_mode, current_time=current_time
        )
        
        if not dayuns:
            logger.warning("无法获取大运序列，无法获取特殊流年")
            return []
        
        # 3. 转换为字典格式（用于 SpecialLiunianService）
        dayun_sequence_dict = []
        for dayun in dayuns:
            dayun_sequence_dict.append({
                'step': dayun.step,
                'stem': dayun.stem,
                'branch': dayun.branch,
                'year_start': dayun.year_start,
                'year_end': dayun.year_end,
                'age_range': dayun.age_range,
                'age_display': dayun.age_display,
                'nayin': dayun.nayin,
                'main_star': dayun.main_star,
                'hidden_stems': dayun.hidden_stems,
                'hidden_stars': dayun.hidden_stars,
                'star_fortune': dayun.star_fortune,
                'self_sitting': dayun.self_sitting,
                'kongwang': dayun.kongwang,
                'deities': dayun.deities,
                'details': dayun.details
            })
        
        # 4. 调用特殊流年服务
        special_liunians_raw = await SpecialLiunianService.get_special_liunians_batch(
            final_solar_date,
            final_solar_time,
            gender,
            dayun_sequence_dict,
            dayun_count,
            current_time
        )
        
        # 5. 转换为模型
        special_liunian_models = []
        for liunian in special_liunians_raw:
            special_liunian_model = SpecialLiunianModel(
                year=liunian.get('year', 0),
                stem=liunian.get('stem', ''),
                branch=liunian.get('branch', ''),
                ganzhi=liunian.get('ganzhi', f"{liunian.get('stem', '')}{liunian.get('branch', '')}"),
                age=liunian.get('age'),
                age_display=liunian.get('age_display'),
                nayin=liunian.get('nayin'),
                main_star=liunian.get('main_star'),
                hidden_stems=liunian.get('hidden_stems', []),
                hidden_stars=liunian.get('hidden_stars', []),
                star_fortune=liunian.get('star_fortune'),
                self_sitting=liunian.get('self_sitting'),
                kongwang=liunian.get('kongwang'),
                deities=liunian.get('deities', []),
                relations=liunian.get('relations', []),
                liuyue_sequence=liunian.get('liuyue_sequence', []),
                details=liunian,
                dayun_step=liunian.get('dayun_step'),
                dayun_ganzhi=liunian.get('dayun_ganzhi')
            )
            special_liunian_models.append(special_liunian_model)
        
        # ✅ 优化：写入缓存
        try:
            from server.utils.cache_key_generator import CacheKeyGenerator
            from server.utils.cache_multi_level import get_multi_cache
            
            dayun_steps = [d.step for d in dayuns] if dayuns else None
            cache_key = CacheKeyGenerator.generate_special_liunian_key(
                solar_date, solar_time, gender,
                calendar_type, location, latitude, longitude,
                dayun_steps, dayun_count
            )
            
            cache = get_multi_cache()
            cache.l2.ttl = 86400
            cache.set(cache_key, special_liunian_models)
            cache.l2.ttl = 3600
        except Exception as e:
            logger.debug(f"[BaziDataService] 特殊流年缓存写入失败（不影响业务）: {e}")
        
        return special_liunian_models
    
    @staticmethod
    async def get_fortune_display(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: str = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        current_time: Optional[datetime] = None,
        dayun_index: Optional[int] = None,
        dayun_year_start: Optional[int] = None,
        dayun_year_end: Optional[int] = None,
        target_year: Optional[int] = None,
        quick_mode: bool = True,
        async_warmup: bool = True
    ) -> Dict[str, Any]:
        """
        获取大运流年流月数据（用于7个前端接口）
        支持7个标准参数，接口层完全不动，只做内部适配
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别（male/female）
            calendar_type: 历法类型（solar/lunar）
            location: 出生地点（可选）
            latitude: 纬度（可选）
            longitude: 经度（可选）
            current_time: 当前时间（可选）
            dayun_index: 大运索引（可选）
            dayun_year_start: 大运起始年份（可选）
            dayun_year_end: 大运结束年份（可选）
            target_year: 目标年份（可选，用于计算流月）
            
        Returns:
            Dict[str, Any]: 大运流年流月数据（旧格式，确保兼容性）
        """
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type, location, latitude, longitude
        )
        
        # 2. 调用现有服务（不修改核心逻辑）
        result = BaziDisplayService.get_fortune_display(
            final_solar_date,
            final_solar_time,
            gender,
            current_time=current_time,
            dayun_index=dayun_index,
            dayun_year_start=dayun_year_start,
            dayun_year_end=dayun_year_end,
            target_year=target_year,
            quick_mode=quick_mode,
            async_warmup=async_warmup
        )
        
        return result
    
    @staticmethod
    async def get_fortune_data(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: str = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        include_dayun: bool = True,
        include_liunian: bool = True,
        include_special_liunian: bool = True,
        dayun_mode: str = DEFAULT_DAYUN_MODE,
        target_years: Optional[List[int]] = None,
        current_time: Optional[datetime] = None
    ) -> BaziDetailModel:
        """
        获取完整的运势数据（用于5个分析接口）
        
        ⚠️ 重要：数据源与排盘接口 /api/v1/bazi/fortune/display 完全一致
        使用 BaziDetailService.calculate_detail_full() 作为唯一数据源
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别（male/female）
            calendar_type: 历法类型（solar/lunar）
            location: 出生地点（可选）
            latitude: 纬度（可选）
            longitude: 经度（可选）
            include_dayun: 是否包含大运序列
            include_liunian: 是否包含流年序列
            include_special_liunian: 是否包含特殊流年
            dayun_mode: 大运模式（默认：current_with_neighbors）
            target_years: 目标年份列表（可选）
            current_time: 当前时间（可选）
            
        Returns:
            BaziDetailModel: 完整的运势数据模型
        """
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type, location, latitude, longitude
        )
        
        if current_time is None:
            current_time = datetime.now()
        
        # 2. ⚠️ 核心：使用 BaziDetailService.calculate_detail_full() 作为唯一数据源
        #    与排盘接口 /api/v1/bazi/fortune/display 完全一致
        loop = asyncio.get_event_loop()
        executor = None
        detail_result = await loop.run_in_executor(
            executor,
            BaziDetailService.calculate_detail_full,
            final_solar_date,
            final_solar_time,
            gender,
            current_time,
            None,  # dayun_index（不指定，获取所有大运）
            None   # target_year
        )
        
        if not detail_result:
            logger.warning("[BaziDataService] calculate_detail_full() 返回空结果")
            return BaziDetailModel(
                dayun_sequence=[],
                liunian_sequence=[],
                special_liunians=[],
                current_dayun=None,
                current_liunian=None,
                qiyun={},
                jiaoyun={},
                details={}
            )
        
        # 3. 从 detail_result 中提取数据（与排盘完全一致）
        details = detail_result.get('details', {})
        raw_dayun_sequence = details.get('dayun_sequence', [])
        raw_liunian_sequence = details.get('liunian_sequence', [])
        qiyun = details.get('qiyun', {})
        jiaoyun = details.get('jiaoyun', {})
        
        logger.info(f"[BaziDataService] 从排盘数据源获取: dayun={len(raw_dayun_sequence)}, liunian={len(raw_liunian_sequence)}")
        
        # 4. 根据 dayun_mode 筛选大运
        birth_year = int(final_solar_date.split('-')[0])
        current_year = current_time.year
        current_age = current_year - birth_year + 1  # 虚岁
        
        filtered_dayun_sequence = []
        if include_dayun:
            filtered_dayun_sequence = BaziDataService._filter_dayuns_by_mode(
                raw_dayun_sequence, current_time, birth_year, dayun_mode, None, None
            )
        
        # ⚠️ 保存原始大运序列，用于后续特殊流年的归属查找
        # 这确保特殊流年可以正确归属到任何大运，即使该大运不在筛选范围内
        all_dayun_sequence = raw_dayun_sequence
        
        # 5. 根据筛选后的大运和 target_years 筛选流年
        filtered_liunian_sequence = []
        if include_liunian:
            # 获取筛选后大运的年份范围
            dayun_year_ranges = []
            for dayun in filtered_dayun_sequence:
                year_start = dayun.get('year_start')
                year_end = dayun.get('year_end')
                if year_start and year_end:
                    dayun_year_ranges.append((year_start, year_end))
            
            # 筛选流年
            for liunian in raw_liunian_sequence:
                year = liunian.get('year', 0)
                
                # 根据大运范围筛选
                in_dayun_range = False
                if dayun_year_ranges:
                    for year_start, year_end in dayun_year_ranges:
                        if year_start <= year <= year_end:
                            in_dayun_range = True
                            break
                else:
                    in_dayun_range = True  # 如果没有大运筛选，保留所有流年
                
                # 根据 target_years 筛选
                in_target_years = True
                if target_years:
                    in_target_years = year in target_years
                
                if in_dayun_range and in_target_years:
                    filtered_liunian_sequence.append(liunian)
        
        # 6. ⚠️ 核心：直接调用排盘接口获取特殊流年数据，确保与排盘完全一致
        #    使用 BaziDisplayService.get_fortune_display() 获取排盘数据，从中提取有 relations 的流年
        special_liunians_raw = []
        if include_special_liunian:
            # ✅ 直接调用排盘接口获取数据（与前端显示的完全一致）
            from server.services.bazi_display_service import BaziDisplayService
            
            fortune_display_result = BaziDisplayService.get_fortune_display(
                final_solar_date,
                final_solar_time,
                gender,
                current_time=current_time,
                dayun_index=None,  # 获取所有大运
                dayun_year_start=None,
                dayun_year_end=None,
                target_year=None,
                quick_mode=False  # 完整模式，获取所有流年
            )
            
            if fortune_display_result.get('success'):
                # 从排盘接口返回的流年列表中提取有 relations 的流年
                liunian_list = fortune_display_result.get('liunian', {}).get('list', [])
                
                for liunian_formatted in liunian_list:
                    relations = liunian_formatted.get('relations', [])
                    if relations and len(relations) > 0:
                        year = liunian_formatted.get('year', 0)
                        ganzhi = liunian_formatted.get('ganzhi', '')
                        
                        # 从原始流年序列中查找完整数据
                        original_liunian = None
                        for liunian in raw_liunian_sequence:
                            if liunian.get('year') == year:
                                original_liunian = liunian.copy()
                                break
                        
                        if original_liunian:
                            # 查找该流年属于哪个大运
                            dayun_step = None
                            dayun_ganzhi = ''
                            for dayun in raw_dayun_sequence:
                                d_year_start = dayun.get('year_start', 0)
                                d_year_end = dayun.get('year_end', 0)
                                d_stem = dayun.get('stem', '')
                                d_branch = dayun.get('branch', '')
                                d_is_xiaoyun = dayun.get('is_xiaoyun', False)
                                
                                # 跳过小运
                                if d_stem == '小运' or d_is_xiaoyun:
                                    continue
                                
                                if d_year_start <= year <= d_year_end:
                                    dayun_step = dayun.get('step')
                                    dayun_ganzhi = f"{d_stem}{d_branch}"
                                    break
                            
                            # 构建特殊流年数据
                            special_liunian = original_liunian.copy()
                            special_liunian['dayun_step'] = dayun_step
                            special_liunian['dayun_ganzhi'] = dayun_ganzhi
                            if 'ganzhi' not in special_liunian:
                                special_liunian['ganzhi'] = ganzhi
                            
                            special_liunians_raw.append(special_liunian)
            
            # 按年份排序
            special_liunians_raw.sort(key=lambda x: (x.get('dayun_step', 0) or 0, x.get('year', 0)))
            logger.info(f"[BaziDataService] 从排盘接口提取特殊流年: {len(special_liunians_raw)}个")
            
            # 打印前10个特殊流年详情（调试用）
            if special_liunians_raw:
                for sl in special_liunians_raw[:10]:
                    logger.info(f"  - {sl.get('year')}年 {sl.get('ganzhi')} (大运{sl.get('dayun_step')}): {sl.get('relations', [])}")
        
        # 6.1 ⚠️ 关键修复：确保大运序列包含所有特殊流年所属的大运
        #     这样 build_enhanced_dayun_structure 才能正确将特殊流年归属到大运
        if include_special_liunian and special_liunians_raw:
            # 收集所有特殊流年所属的大运 step
            special_dayun_steps = set()
            for sl in special_liunians_raw:
                dayun_step = sl.get('dayun_step')
                if dayun_step is not None:
                    special_dayun_steps.add(dayun_step)
            
            # 获取筛选后大运的 step
            filtered_steps = {d.get('step') for d in filtered_dayun_sequence}
            
            # 添加缺失的大运（特殊流年所属但不在筛选范围内的大运）
            missing_steps = special_dayun_steps - filtered_steps
            if missing_steps:
                logger.info(f"[BaziDataService] 添加缺失的大运: {missing_steps}")
                for dayun in all_dayun_sequence:
                    step = dayun.get('step')
                    if step in missing_steps:
                        filtered_dayun_sequence.append(dayun)
                
                # 按 step 排序，确保大运顺序正确
                filtered_dayun_sequence.sort(key=lambda x: x.get('step', 0) or 0)
                logger.info(f"[BaziDataService] 合并后大运数量: {len(filtered_dayun_sequence)}")
        
        # 7. 确定当前大运和流年
        current_dayun = None
        current_liunian = None
        
        for dayun in filtered_dayun_sequence:
            age_range = dayun.get('age_range', {})
            if age_range:
                age_start = age_range.get('start', 0)
                age_end = age_range.get('end', 0)
                if age_start <= current_age <= age_end:
                    current_dayun = dayun
                    break
        
        for liunian in filtered_liunian_sequence:
            if liunian.get('year') == current_year:
                current_liunian = liunian
                break
        
        # 8. 转换为模型
        def _dict_to_dayun_model(d: Dict[str, Any]) -> DayunModel:
            """将字典转换为 DayunModel"""
            return DayunModel(
                step=d.get('step'),
                stem=d.get('stem', ''),
                branch=d.get('branch', ''),
                ganzhi=d.get('ganzhi', f"{d.get('stem', '')}{d.get('branch', '')}"),
                year_start=d.get('year_start'),
                year_end=d.get('year_end'),
                age_range=d.get('age_range', {}),
                age_display=d.get('age_display'),
                nayin=d.get('nayin'),
                main_star=d.get('main_star'),
                hidden_stems=d.get('hidden_stems', []),
                hidden_stars=d.get('hidden_stars', []),
                star_fortune=d.get('star_fortune'),
                self_sitting=d.get('self_sitting'),
                kongwang=d.get('kongwang'),
                deities=d.get('deities', []),
                details=d.get('details', {})
            )
        
        def _dict_to_liunian_model(d: Dict[str, Any]) -> LiunianModel:
            """将字典转换为 LiunianModel"""
            return LiunianModel(
                year=d.get('year', 0),
                stem=d.get('stem', ''),
                branch=d.get('branch', ''),
                ganzhi=d.get('ganzhi', f"{d.get('stem', '')}{d.get('branch', '')}"),
                age=d.get('age'),
                age_display=d.get('age_display'),
                nayin=d.get('nayin'),
                main_star=d.get('main_star'),
                hidden_stems=d.get('hidden_stems', []),
                hidden_stars=d.get('hidden_stars', []),
                star_fortune=d.get('star_fortune'),
                self_sitting=d.get('self_sitting'),
                kongwang=d.get('kongwang'),
                deities=d.get('deities', []),
                relations=d.get('relations', []),
                dayun_step=d.get('dayun_step'),
                dayun_ganzhi=d.get('dayun_ganzhi'),
                details=d.get('details', {})
            )
        
        def _dict_to_special_liunian_model(d: Dict[str, Any]) -> SpecialLiunianModel:
            """将字典转换为 SpecialLiunianModel"""
            return SpecialLiunianModel(
                year=d.get('year', 0),
                stem=d.get('stem', ''),
                branch=d.get('branch', ''),
                ganzhi=d.get('ganzhi', f"{d.get('stem', '')}{d.get('branch', '')}"),
                age=d.get('age'),
                age_display=d.get('age_display'),
                nayin=d.get('nayin'),
                main_star=d.get('main_star'),
                hidden_stems=d.get('hidden_stems', []),
                hidden_stars=d.get('hidden_stars', []),
                star_fortune=d.get('star_fortune'),
                self_sitting=d.get('self_sitting'),
                kongwang=d.get('kongwang'),
                deities=d.get('deities', []),
                relations=d.get('relations', []),
                dayun_step=d.get('dayun_step'),
                dayun_ganzhi=d.get('dayun_ganzhi'),
                details=d.get('details', {})
            )
        
        # 转换为模型列表
        dayun_sequence_models = [_dict_to_dayun_model(d) for d in filtered_dayun_sequence]
        liunian_sequence_models = [_dict_to_liunian_model(l) for l in filtered_liunian_sequence]
        special_liunian_models = [_dict_to_special_liunian_model(s) for s in special_liunians_raw]
        
        # 转换当前大运和流年
        current_dayun_model = _dict_to_dayun_model(current_dayun) if current_dayun else None
        current_liunian_model = _dict_to_liunian_model(current_liunian) if current_liunian else None
        
        # 9. 构建完整数据模型
        fortune_data = BaziDetailModel(
            dayun_sequence=dayun_sequence_models,
            liunian_sequence=liunian_sequence_models,
            special_liunians=special_liunian_models,
            current_dayun=current_dayun_model,
            current_liunian=current_liunian_model,
            qiyun=qiyun,
            jiaoyun=jiaoyun,
            details=details
        )
        
        return fortune_data
    
    @staticmethod
    def _filter_dayuns_by_mode(
        dayun_sequence: List[Dict[str, Any]],
        current_time: datetime,
        birth_year: int,
        mode: str,
        count: Optional[int],
        indices: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """
        根据模式筛选大运
        
        Args:
            dayun_sequence: 完整的大运序列
            current_time: 当前时间
            birth_year: 出生年份
            mode: 查询模式
            count: 数量（仅用于 count 模式）
            indices: 索引列表（用于 indices 模式）
            
        Returns:
            List[Dict[str, Any]]: 筛选后的大运列表
        """
        if not dayun_sequence:
            return []
        
        # 确定当前大运
        current_age = current_time.year - birth_year + 1  # 虚岁
        current_dayun_index = None
        
        for idx, dayun in enumerate(dayun_sequence):
            age_range = dayun.get('age_range', {})
            if age_range:
                age_start = age_range.get('start', 0)
                age_end = age_range.get('end', 0)
                if age_start <= current_age <= age_end:
                    current_dayun_index = idx
                    break
        
        # 根据模式筛选
        if mode == 'current':
            # 仅当前大运
            if current_dayun_index is not None:
                return [dayun_sequence[current_dayun_index]]
            return []
        
        elif mode == 'current_with_neighbors':
            # 当前大运及前后各一个（共3个）
            if current_dayun_index is None:
                return []
            
            result = []
            # 前一个大运
            if current_dayun_index > 0:
                result.append(dayun_sequence[current_dayun_index - 1])
            # 当前大运
            result.append(dayun_sequence[current_dayun_index])
            # 后一个大运
            if current_dayun_index < len(dayun_sequence) - 1:
                result.append(dayun_sequence[current_dayun_index + 1])
            
            return result
        
        elif mode == 'indices' and indices:
            # 索引模式：返回指定索引的大运
            result = []
            for idx in indices:
                if 0 <= idx < len(dayun_sequence):
                    result.append(dayun_sequence[idx])
            return result
        
        elif mode == 'count' or mode is None:
            # 数量模式：返回前N个大运
            count = count or 8
            return dayun_sequence[:count] if count <= len(dayun_sequence) else dayun_sequence
        
        return []


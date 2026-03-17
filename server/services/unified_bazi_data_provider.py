#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一八字数据提供者

设计原则：
1. 以排盘接口为准（BaziDisplayService.get_fortune_display）
2. 所有数据一次获取，统一结构
3. 各流式接口按需选择字段
4. 不修改任何底层服务

核心约束：
- 只读调用底层服务，不做任何修改
- 特殊年份直接从排盘透传，不做任何计算或过滤
- 大运流年序列与排盘完全一致

使用方式：
    from server.services.unified_bazi_data_provider import UnifiedBaziDataProvider
    
    # 获取统一数据
    unified_data = await UnifiedBaziDataProvider.get_unified_data(
        solar_date="1985-11-21",
        solar_time="06:30",
        gender="female"
    )
    
    # 数据与排盘完全一致
    assert unified_data.special_liunians == display_result['liunian']['list'] 中有 relations 的项
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from server.utils.async_executor import get_executor
from server.models.stream_input_data import (
    UnifiedBaziData, 
    BasicInfoModel, 
    BaziPillarsModel, 
    WangShuaiModel
)
from server.models.dayun import DayunModel
from server.models.liunian import LiunianModel
from server.models.special_liunian import SpecialLiunianModel

logger = logging.getLogger(__name__)


class DataInconsistencyError(Exception):
    """数据不一致错误"""
    pass


class UnifiedBaziDataProvider:
    """
    统一八字数据提供者
    
    这是所有流式接口的唯一数据源。
    
    数据来源层级：
    1. BaziDisplayService.get_fortune_display() - 排盘数据（主要来源）
    2. WangShuaiService.calculate_wangshuai() - 旺衰数据
    3. BaziDetailService.calculate_detail_full() - 详细数据（五行统计等）
    
    设计原则：
    - 只读调用，不修改底层
    - 特殊年份直接透传，不做任何计算
    - 数据验证确保一致性
    """
    
    # 是否启用数据验证（开发环境启用，生产环境可关闭以提高性能）
    ENABLE_VERIFICATION = True
    
    @staticmethod
    async def get_unified_data(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: str = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        current_time: Optional[datetime] = None
    ) -> UnifiedBaziData:
        """
        获取统一的八字数据（唯一入口）
        
        Args:
            solar_date: 阳历日期（如 "1985-11-21"）
            solar_time: 出生时间（如 "06:30"）
            gender: 性别（"male" 或 "female"）
            calendar_type: 历法类型（默认 "solar"）
            location: 出生地点（可选）
            latitude: 纬度（可选）
            longitude: 经度（可选）
            current_time: 当前时间（可选，用于确定当前大运）
            
        Returns:
            UnifiedBaziData: 统一的八字数据
            
        Raises:
            DataInconsistencyError: 数据不一致时抛出
        """
        logger.info(f"🔍 [UnifiedBaziDataProvider] 开始获取统一数据: {solar_date} {solar_time} {gender}")
        
        # 处理农历输入
        final_solar_date = solar_date
        final_solar_time = solar_time
        
        if calendar_type == "lunar":
            from server.utils.bazi_input_processor import BaziInputProcessor
            final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
                solar_date, solar_time, calendar_type, location, latitude, longitude
            )
        
        # 1. 并行获取所有数据
        loop = asyncio.get_event_loop()
        executor = get_executor()
        
        # 导入服务（延迟导入避免循环依赖）
        from server.services.bazi_display_service import BaziDisplayService
        from server.services.wangshuai_service import WangShuaiService
        from server.services.bazi_detail_service import BaziDetailService
        
        # 并行调用三个服务
        display_task = loop.run_in_executor(
            executor,
            lambda: BaziDisplayService.get_fortune_display(
                final_solar_date, final_solar_time, gender,
                current_time=current_time,
                quick_mode=False  # 获取完整数据
            )
        )
        
        wangshuai_task = loop.run_in_executor(
            executor,
            lambda: WangShuaiService.calculate_wangshuai(
                final_solar_date, final_solar_time, gender
            )
        )
        
        detail_task = loop.run_in_executor(
            executor,
            lambda: BaziDetailService.calculate_detail_full(
                final_solar_date, final_solar_time, gender
            )
        )
        
        display_result, wangshuai_result, detail_result = await asyncio.gather(
            display_task, wangshuai_task, detail_task
        )
        
        # 2. 验证数据获取成功
        if not display_result or not display_result.get('success'):
            raise ValueError(f"排盘数据获取失败: {display_result}")
        
        if not wangshuai_result or not wangshuai_result.get('success'):
            logger.warning(f"旺衰数据获取失败: {wangshuai_result.get('error', '未知错误')}")
            wangshuai_data = {}
        else:
            wangshuai_data = wangshuai_result.get('data', {})
        
        if not detail_result:
            logger.warning("详细数据获取失败")
            detail_result = {}
        
        # 3. 提取并整合数据
        unified_data = UnifiedBaziDataProvider._build_unified_data(
            display_result=display_result,
            wangshuai_data=wangshuai_data,
            detail_result=detail_result,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=gender
        )
        
        # 4. 数据验证（确保与排盘一致）
        if UnifiedBaziDataProvider.ENABLE_VERIFICATION:
            UnifiedBaziDataProvider._verify_consistency(display_result, unified_data)
        
        logger.info(f"✅ [UnifiedBaziDataProvider] 统一数据获取成功: "
                   f"大运={len(unified_data.dayun_sequence)}个, "
                   f"特殊年份={len(unified_data.special_liunians)}个")
        
        return unified_data
    
    @staticmethod
    def _build_unified_data(
        display_result: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        detail_result: Dict[str, Any],
        solar_date: str,
        solar_time: str,
        gender: str
    ) -> UnifiedBaziData:
        """
        构建统一数据结构
        
        关键：特殊年份直接从排盘透传，不做任何计算或过滤
        """
        
        # === 1. 基础信息 ===
        basic_info = BasicInfoModel(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender
        )
        
        # === 2. 四柱数据（从排盘获取）===
        pillars_raw = display_result.get('pillars', {})
        bazi_pillars = BaziPillarsModel(
            year=pillars_raw.get('year', {}),
            month=pillars_raw.get('month', {}),
            day=pillars_raw.get('day', {}),
            hour=pillars_raw.get('hour', {})
        )
        
        # === 3. 五行统计（从详情获取）===
        element_counts = detail_result.get('element_counts', {})
        
        # === 4. 旺衰数据（统一结构）===
        wangshuai = WangShuaiModel(
            wangshuai=wangshuai_data.get('wangshuai', ''),
            wangshuai_degree=wangshuai_data.get('wangshuai_degree'),
            total_score=wangshuai_data.get('total_score'),
            xi_shen=wangshuai_data.get('xi_shen', []) if isinstance(wangshuai_data.get('xi_shen'), list) else [],
            ji_shen=wangshuai_data.get('ji_shen', []) if isinstance(wangshuai_data.get('ji_shen'), list) else [],
            # 关键！直接使用底层返回的字段名
            xi_shen_elements=wangshuai_data.get('xi_shen_elements', []),
            ji_shen_elements=wangshuai_data.get('ji_shen_elements', []),
            tiaohou=wangshuai_data.get('tiaohou'),
            final_xi_ji=wangshuai_data.get('final_xi_ji')
        )
        
        # === 5. 大运序列（从排盘获取）===
        dayun_list_raw = display_result.get('dayun', {}).get('list', [])
        dayun_sequence = []
        current_dayun = None
        
        for dayun_raw in dayun_list_raw:
            dayun_model = DayunModel(
                step=dayun_raw.get('step', 0),
                stem=dayun_raw.get('stem', {}).get('char', '') if isinstance(dayun_raw.get('stem'), dict) else dayun_raw.get('stem', ''),
                branch=dayun_raw.get('branch', {}).get('char', '') if isinstance(dayun_raw.get('branch'), dict) else dayun_raw.get('branch', ''),
                ganzhi=dayun_raw.get('ganzhi', ''),
                year_start=dayun_raw.get('year_start'),
                year_end=dayun_raw.get('year_end'),
                age_range=dayun_raw.get('age_range'),
                age_display=dayun_raw.get('age_display'),
                nayin=dayun_raw.get('nayin'),
                main_star=dayun_raw.get('main_star'),
                hidden_stems=dayun_raw.get('hidden_stems'),
                hidden_stars=dayun_raw.get('hidden_stars'),
                star_fortune=dayun_raw.get('star_fortune'),
                self_sitting=dayun_raw.get('self_sitting'),
                kongwang=dayun_raw.get('kongwang'),
                deities=dayun_raw.get('deities')
            )
            dayun_sequence.append(dayun_model)
            
            if dayun_raw.get('is_current'):
                current_dayun = dayun_model
        
        # === 6. 特殊流年（关键！直接从排盘透传）===
        special_liunians = UnifiedBaziDataProvider._extract_special_liunians(
            display_result, dayun_list_raw
        )
        
        # === 7. 十神统计 ===
        ten_gods_stats = detail_result.get('ten_gods_stats')
        
        # === 8. 构建统一数据 ===
        unified_data = UnifiedBaziData(
            basic_info=basic_info,
            bazi_pillars=bazi_pillars,
            element_counts=element_counts,
            wangshuai=wangshuai,
            dayun_sequence=dayun_sequence,
            current_dayun=current_dayun,
            special_liunians=special_liunians,
            ten_gods_stats=ten_gods_stats,
            details=detail_result.get('details')
        )
        
        # 保存原始排盘数据（用于验证和调试）
        unified_data.raw_display_result = display_result
        
        return unified_data
    
    @staticmethod
    def _extract_special_liunians(
        display_result: Dict[str, Any],
        dayun_list_raw: List[Dict[str, Any]]
    ) -> List[SpecialLiunianModel]:
        """
        从排盘结果中提取特殊流年
        
        关键设计：
        1. 直接从 display_result['liunian']['list'] 提取
        2. 只提取有 relations 的流年
        3. 不做任何计算或过滤，完全透传
        
        数据来源：BaziDisplayService.get_fortune_display().liunian.list[].relations
        """
        special_liunians = []
        
        # 获取流年列表
        liunian_list = display_result.get('liunian', {}).get('list', [])
        
        # 构建大运年份映射（用于确定流年所属大运）
        dayun_year_map = {}
        for dayun in dayun_list_raw:
            year_start = dayun.get('year_start')
            year_end = dayun.get('year_end')
            step = dayun.get('step', 0)
            ganzhi = dayun.get('ganzhi', '')
            
            if year_start and year_end:
                for year in range(year_start, year_end + 1):
                    dayun_year_map[year] = {'step': step, 'ganzhi': ganzhi}
        
        # 遍历所有流年，提取有 relations 的
        for liunian in liunian_list:
            relations = liunian.get('relations', [])
            
            # 只提取有特殊关系的流年
            if relations and len(relations) > 0:
                year = liunian.get('year', 0)
                dayun_info = dayun_year_map.get(year, {})
                
                # 提取天干地支（处理不同的数据结构）
                stem_raw = liunian.get('stem', {})
                branch_raw = liunian.get('branch', {})
                
                if isinstance(stem_raw, dict):
                    stem = stem_raw.get('char', '')
                else:
                    stem = stem_raw
                    
                if isinstance(branch_raw, dict):
                    branch = branch_raw.get('char', '')
                else:
                    branch = branch_raw
                
                special_liunian = SpecialLiunianModel(
                    year=year,
                    stem=stem,
                    branch=branch,
                    ganzhi=liunian.get('ganzhi', f"{stem}{branch}"),
                    age=liunian.get('age'),
                    age_display=liunian.get('age_display'),
                    nayin=liunian.get('nayin'),
                    main_star=liunian.get('main_star'),
                    hidden_stems=liunian.get('hidden_stems'),
                    hidden_stars=liunian.get('hidden_stars'),
                    star_fortune=liunian.get('star_fortune'),
                    self_sitting=liunian.get('self_sitting'),
                    kongwang=liunian.get('kongwang'),
                    deities=liunian.get('deities'),
                    relations=relations,  # 直接透传，不做任何处理
                    dayun_step=dayun_info.get('step'),
                    dayun_ganzhi=dayun_info.get('ganzhi')
                )
                special_liunians.append(special_liunian)
        
        # 按年份排序
        special_liunians.sort(key=lambda x: x.year)
        
        logger.debug(f"提取特殊流年: {len(special_liunians)}个")
        for sl in special_liunians:
            logger.debug(f"  {sl.year}年 {sl.ganzhi}: {sl.relations}")
        
        return special_liunians
    
    @staticmethod
    def _verify_consistency(display_result: Dict[str, Any], unified_data: UnifiedBaziData) -> None:
        """
        验证数据一致性
        
        确保统一数据与排盘完全一致，特别是特殊年份
        
        Raises:
            DataInconsistencyError: 数据不一致时抛出
        """
        # 1. 验证特殊年份数量
        liunian_list = display_result.get('liunian', {}).get('list', [])
        display_special_years = [
            ln['year'] for ln in liunian_list 
            if ln.get('relations') and len(ln.get('relations', [])) > 0
        ]
        unified_special_years = [sl.year for sl in unified_data.special_liunians]
        
        if set(display_special_years) != set(unified_special_years):
            logger.error(f"特殊年份不一致！")
            logger.error(f"  排盘: {sorted(display_special_years)}")
            logger.error(f"  统一: {sorted(unified_special_years)}")
            raise DataInconsistencyError(
                f"特殊年份数据不一致: 排盘={sorted(display_special_years)}, "
                f"统一={sorted(unified_special_years)}"
            )
        
        # 2. 验证特殊年份的 relations 内容
        display_relations_map = {
            ln['year']: ln.get('relations', [])
            for ln in liunian_list 
            if ln.get('relations')
        }
        
        for sl in unified_data.special_liunians:
            display_relations = display_relations_map.get(sl.year, [])
            if sl.relations != display_relations:
                logger.error(f"年份 {sl.year} 的 relations 不一致！")
                logger.error(f"  排盘: {display_relations}")
                logger.error(f"  统一: {sl.relations}")
                raise DataInconsistencyError(
                    f"年份 {sl.year} 的 relations 不一致"
                )
        
        logger.debug("✅ 数据一致性验证通过")
    
    @staticmethod
    def get_xi_ji_elements_for_health(wangshuai: WangShuaiModel) -> Dict[str, Any]:
        """
        获取健康分析所需的喜忌五行数据
        
        这是一个适配器方法，将统一的旺衰数据转换为 HealthAnalysisService 期望的格式
        
        Returns:
            dict: {
                'xi_ji_elements': {
                    'xi_shen': ['木', '火', ...],
                    'ji_shen': ['金', '水', ...]
                }
            }
        """
        return {
            'xi_ji_elements': {
                'xi_shen': wangshuai.xi_shen_elements,
                'ji_shen': wangshuai.ji_shen_elements
            }
        }

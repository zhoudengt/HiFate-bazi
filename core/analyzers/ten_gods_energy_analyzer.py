#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十神能量量化分析器
计算十神的能量值，考虑月令、相克关系、生扶关系等因素
"""

import logging
from typing import Dict, List, Any, Optional
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import BRANCH_CHONG, BRANCH_XING

logger = logging.getLogger(__name__)


class TenGodsEnergyAnalyzer:
    """十神能量量化分析器"""
    
    # 十神相克关系
    KE_RELATIONS = {
        '正财': ['比肩', '劫财'],
        '偏财': ['比肩', '劫财'],
        '正印': ['正财', '偏财'],
        '偏印': ['正财', '偏财'],
        '食神': ['正印', '偏印'],
        '伤官': ['正印', '偏印'],
        '正官': ['食神', '伤官'],
        '七杀': ['食神', '伤官'],
        '比肩': ['正官', '七杀'],
        '劫财': ['正官', '七杀']
    }
    
    # 十神相生关系
    SHENG_RELATIONS = {
        '正财': ['食神', '伤官'],
        '偏财': ['食神', '伤官'],
        '正印': ['正官', '七杀'],
        '偏印': ['正官', '七杀'],
        '食神': ['比肩', '劫财'],
        '伤官': ['比肩', '劫财'],
        '正官': ['正印', '偏印'],
        '七杀': ['正印', '偏印'],
        '比肩': ['正印', '偏印'],
        '劫财': ['正印', '偏印']
    }
    
    def __init__(self):
        """初始化分析器"""
        logger.info("✅ 十神能量量化分析器初始化完成")
    
    def calculate_energy(
        self,
        ten_god: str,
        bazi_data: Dict[str, Any],
        ten_gods_stats: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        计算单个十神的能量值
        
        Args:
            ten_god: 十神名称
            bazi_data: 八字数据
            ten_gods_stats: 十神统计信息（可选）
            
        Returns:
            能量值（0-100，值越大能量越强）
        """
        if not ten_gods_stats:
            ten_gods_stats = bazi_data.get('ten_gods_stats', {})
        
        totals = ten_gods_stats.get('totals', {})
        count = totals.get(ten_god, 0)
        
        if count == 0:
            return 0.0
        
        base_energy = count * 10.0  # 基础能量：每个十神10分
        
        # 1. 月令加成（在月令位置能量*2）
        month_pillar = bazi_data.get('bazi_pillars', {}).get('month', {})
        month_main_star = month_pillar.get('main_star', '')
        if month_main_star == ten_god:
            base_energy *= 2.0
            logger.debug(f"   {ten_god}在月令，能量*2")
        
        # 2. 相克关系影响（被克则能量减少）
        ke_gods = self.KE_RELATIONS.get(ten_god, [])
        if ke_gods:
            for ke_god in ke_gods:
                ke_count = totals.get(ke_god, 0)
                if ke_count > 0:
                    # 被克则能量减少（每个克神减少5分）
                    base_energy -= ke_count * 5.0
                    logger.debug(f"   {ten_god}被{ke_god}克，能量-{ke_count * 5.0}")
        
        # 3. 相生关系影响（被生则能量增加）
        sheng_gods = self.SHENG_RELATIONS.get(ten_god, [])
        if sheng_gods:
            for sheng_god in sheng_gods:
                sheng_count = totals.get(sheng_god, 0)
                if sheng_count > 0:
                    # 被生则能量增加（每个生神增加3分）
                    base_energy += sheng_count * 3.0
                    logger.debug(f"   {ten_god}被{sheng_god}生，能量+{sheng_count * 3.0}")
        
        # 限制在0-100之间
        return max(0.0, min(100.0, base_energy))
    
    def calculate_group_energy(
        self,
        ten_gods: List[str],
        bazi_data: Dict[str, Any],
        ten_gods_stats: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        计算一组十神的综合能量值
        
        Args:
            ten_gods: 十神列表
            bazi_data: 八字数据
            ten_gods_stats: 十神统计信息（可选）
            
        Returns:
            综合能量值
        """
        total_energy = 0.0
        
        for ten_god in ten_gods:
            energy = self.calculate_energy(ten_god, bazi_data, ten_gods_stats)
            total_energy += energy
        
        return total_energy
    
    def compare_energy(
        self,
        group_a: List[str],
        group_b: List[str],
        bazi_data: Dict[str, Any],
        ten_gods_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        比较两组十神的能量
        
        Args:
            group_a: 第一组十神
            group_b: 第二组十神
            bazi_data: 八字数据
            ten_gods_stats: 十神统计信息（可选）
            
        Returns:
            比较结果字典
        """
        energy_a = self.calculate_group_energy(group_a, bazi_data, ten_gods_stats)
        energy_b = self.calculate_group_energy(group_b, bazi_data, ten_gods_stats)
        
        return {
            'group_a_energy': energy_a,
            'group_b_energy': energy_b,
            'group_a_stronger': energy_a > energy_b,
            'difference': energy_a - energy_b
        }


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运转折点识别分析器
识别大运转换的关键时间点，分析转折点的吉凶程度
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from core.data.constants import STEM_ELEMENTS
from core.data.relations import BRANCH_CHONG, BRANCH_LIUHE, STEM_HE

logger = logging.getLogger(__name__)


class DayunTurningPointAnalyzer:
    """大运转折点识别分析器"""
    
    def __init__(self):
        """初始化分析器"""
        logger.info("✅ 大运转折点分析器初始化完成")
    
    def identify_turning_points(
        self,
        bazi_data: Dict[str, Any],
        dayun_sequence: List[Dict[str, Any]],
        current_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        识别大运转折点
        
        Args:
            bazi_data: 八字数据
            dayun_sequence: 大运序列
            current_year: 当前年份（可选）
            
        Returns:
            转折点列表
        """
        logger.info("🔍 开始识别大运转折点")
        
        if not dayun_sequence or len(dayun_sequence) < 2:
            return []
        
        turning_points = []
        
        # 获取日干日支
        day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
        day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
        
        # 分析每两个相邻大运之间的转折
        for i in range(len(dayun_sequence) - 1):
            current_dayun = dayun_sequence[i]
            next_dayun = dayun_sequence[i + 1]
            
            # 分析转折点特征
            turning_point = self._analyze_turning_point(
                current_dayun, next_dayun, day_stem, day_branch, i
            )
            
            if turning_point:
                turning_points.append(turning_point)
        
        logger.info(f"✅ 识别到 {len(turning_points)} 个大运转折点")
        return turning_points
    
    def _analyze_turning_point(
        self,
        current_dayun: Dict[str, Any],
        next_dayun: Dict[str, Any],
        day_stem: str,
        day_branch: str,
        index: int
    ) -> Optional[Dict[str, Any]]:
        """
        分析单个转折点
        
        Args:
            current_dayun: 当前大运
            next_dayun: 下一个大运
            day_stem: 日干
            day_branch: 日支
            index: 大运索引
            
        Returns:
            转折点信息字典
        """
        current_stem = current_dayun.get('stem', '')
        current_branch = current_dayun.get('branch', '')
        next_stem = next_dayun.get('stem', '')
        next_branch = next_dayun.get('branch', '')
        
        if not all([current_stem, current_branch, next_stem, next_branch]):
            return None
        
        # 计算转折强度（0-100）
        turning_strength = self._calculate_turning_strength(
            current_stem, current_branch,
            next_stem, next_branch,
            day_stem, day_branch
        )
        
        # 判定转折类型
        turning_type = self._determine_turning_type(
            current_stem, current_branch,
            next_stem, next_branch,
            day_stem, day_branch
        )
        
        # 判定吉凶
        auspicious_level = self._determine_auspicious_level(
            turning_strength, turning_type
        )
        
        # 获取转折时间
        start_year = current_dayun.get('start_year')
        end_year = current_dayun.get('end_year')
        turning_year = end_year if end_year else (start_year + 10 if start_year else None)
        
        return {
            'index': index,
            'turning_year': turning_year,
            'current_dayun': {
                'stem': current_stem,
                'branch': current_branch,
                'ganzhi': f"{current_stem}{current_branch}"
            },
            'next_dayun': {
                'stem': next_stem,
                'branch': next_branch,
                'ganzhi': f"{next_stem}{next_branch}"
            },
            'turning_strength': round(turning_strength, 2),
            'turning_type': turning_type,
            'auspicious_level': auspicious_level,
            'description': self._generate_turning_description(
                turning_type, auspicious_level, turning_strength
            )
        }
    
    def _calculate_turning_strength(
        self,
        current_stem: str, current_branch: str,
        next_stem: str, next_branch: str,
        day_stem: str, day_branch: str
    ) -> float:
        """
        计算转折强度
        
        Args:
            current_stem, current_branch: 当前大运干支
            next_stem, next_branch: 下一个大运干支
            day_stem, day_branch: 日干日支
            
        Returns:
            转折强度（0-100）
        """
        strength = 0.0
        
        # 1. 天干变化（权重40%）
        if current_stem != next_stem:
            strength += 40
            
            # 如果涉及日干，增强
            if current_stem == day_stem or next_stem == day_stem:
                strength += 10
        
        # 2. 地支变化（权重40%）
        if current_branch != next_branch:
            strength += 40
            
            # 如果涉及日支，增强
            if current_branch == day_branch or next_branch == day_branch:
                strength += 10
        
        # 3. 关系变化（权重20%）
        # 检查是否从相冲变为相合，或相反
        current_relation = self._get_relation_to_day(current_stem, current_branch, day_stem, day_branch)
        next_relation = self._get_relation_to_day(next_stem, next_branch, day_stem, day_branch)
        
        if current_relation != next_relation:
            strength += 20
        
        return min(100.0, strength)
    
    def _get_relation_to_day(
        self,
        stem: str, branch: str,
        day_stem: str, day_branch: str
    ) -> str:
        """
        获取大运与日柱的关系
        
        Returns:
            关系类型：'合', '冲', '刑', '害', '生', '克', '同', '无'
        """
        relation = '无'
        
        # 天干五合
        if STEM_HE.get(stem) == day_stem or STEM_HE.get(day_stem) == stem:
            relation = '合'
        # 地支六合
        elif BRANCH_LIUHE.get(branch) == day_branch or BRANCH_LIUHE.get(day_branch) == branch:
            relation = '合'
        # 地支六冲
        elif BRANCH_CHONG.get(branch) == day_branch or BRANCH_CHONG.get(day_branch) == branch:
            relation = '冲'
        # 天干相同
        elif stem == day_stem:
            relation = '同'
        # 地支相同
        elif branch == day_branch:
            relation = '同'
        
        return relation
    
    def _determine_turning_type(
        self,
        current_stem: str, current_branch: str,
        next_stem: str, next_branch: str,
        day_stem: str, day_branch: str
    ) -> str:
        """
        判定转折类型
        
        Returns:
            类型：'天干转折', '地支转折', '干支转折', '关系转折'
        """
        if current_stem != next_stem and current_branch != next_branch:
            return '干支转折'
        elif current_stem != next_stem:
            return '天干转折'
        elif current_branch != next_branch:
            return '地支转折'
        else:
            return '关系转折'
    
    def _determine_auspicious_level(self, strength: float, turning_type: str) -> str:
        """
        判定转折点吉凶
        
        Args:
            strength: 转折强度
            turning_type: 转折类型
            
        Returns:
            吉凶等级：'大吉', '吉', '中平', '凶', '大凶'
        """
        # 简化判定：转折强度越高，变化越大
        # 如果转折强度高，可能是重大转折（可能吉也可能凶）
        if strength >= 80:
            return '重大转折'  # 需要结合具体分析
        elif strength >= 60:
            return '重要转折'
        elif strength >= 40:
            return '一般转折'
        else:
            return '平稳过渡'
    
    def _generate_turning_description(
        self,
        turning_type: str,
        auspicious_level: str,
        strength: float
    ) -> str:
        """
        生成转折点描述
        
        Args:
            turning_type: 转折类型
            auspicious_level: 吉凶等级
            strength: 转折强度
            
        Returns:
            描述文本
        """
        descriptions = {
            '重大转折': '这是一个重大的人生转折点，运势将发生显著变化',
            '重要转折': '这是一个重要的转折点，需要特别关注',
            '一般转折': '这是一个普通的转折点，运势会有一定变化',
            '平稳过渡': '这是一个平稳的过渡期，变化不大'
        }
        
        base_desc = descriptions.get(auspicious_level, '这是一个转折点')
        
        type_descs = {
            '干支转折': '天干地支同时变化，影响全面',
            '天干转折': '天干变化，主要影响外在表现',
            '地支转折': '地支变化，主要影响内在基础',
            '关系转折': '与命局关系发生变化'
        }
        
        type_desc = type_descs.get(turning_type, '')
        
        return f"{base_desc}。{type_desc}转折强度: {strength:.1f}分。"


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年吉凶量化评分分析器
为每个流年计算0-100分的吉凶评分
"""

import logging
from typing import Dict, List, Any, Optional
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import (
    BRANCH_CHONG,
    BRANCH_XING,
    BRANCH_HAI,
    BRANCH_LIUHE,
    STEM_HE,
)

logger = logging.getLogger(__name__)


class LiunianAuspiciousAnalyzer:
    """流年吉凶量化评分分析器"""
    
    # 五行生克关系
    ELEMENT_RELATIONS = {
        '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
        '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
        '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
        '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
        '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
    }
    
    # 十神吉凶分类
    AUSPICIOUS_TEN_GODS = ['正官', '正印', '正财', '食神']  # 吉神
    INAUSPICIOUS_TEN_GODS = ['七杀', '偏印', '偏财', '伤官', '劫财']  # 凶神
    NEUTRAL_TEN_GODS = ['比肩']  # 中性
    
    def __init__(self):
        """初始化分析器"""
        logger.info("✅ 流年吉凶评分分析器初始化完成")
    
    def calculate_auspicious_score(
        self,
        bazi_data: Dict[str, Any],
        liunian_data: Dict[str, Any],
        dayun_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算流年吉凶量化评分（0-100分）
        
        Args:
            bazi_data: 八字数据（包含四柱、十神、五行等）
            liunian_data: 流年数据（包含干支、十神、神煞等）
            dayun_data: 大运数据（可选，用于综合分析）
            
        Returns:
            包含评分和详细分析的字典
        """
        logger.info("🔍 开始计算流年吉凶评分")
        
        base_score = 50.0  # 基础分数50分（中性）
        
        # 1. 流年与日干的关系分析（权重30%）
        day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
        liunian_stem = liunian_data.get('stem', '')
        liunian_branch = liunian_data.get('branch', '')
        
        stem_relation_score = self._analyze_stem_relation(day_stem, liunian_stem, base_score)
        logger.info(f"   天干关系评分: {stem_relation_score:.2f}")
        
        # 2. 流年与日支的关系分析（权重25%）
        day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
        branch_relation_score = self._analyze_branch_relation(day_branch, liunian_branch, base_score)
        logger.info(f"   地支关系评分: {branch_relation_score:.2f}")
        
        # 3. 流年十神分析（权重20%）
        liunian_main_star = liunian_data.get('main_star', '')
        ten_gods_score = self._analyze_ten_gods(liunian_main_star, base_score)
        logger.info(f"   十神评分: {ten_gods_score:.2f}")
        
        # 4. 流年神煞分析（权重15%）
        liunian_deities = liunian_data.get('deities', [])
        deities_score = self._analyze_deities(liunian_deities, base_score)
        logger.info(f"   神煞评分: {deities_score:.2f}")
        
        # 5. 流年与命局五行平衡（权重10%）
        element_balance_score = self._analyze_element_balance(bazi_data, liunian_data, base_score)
        logger.info(f"   五行平衡评分: {element_balance_score:.2f}")
        
        # 6. 大运影响（如果有大运数据，额外调整）
        dayun_adjustment = 0.0
        if dayun_data:
            dayun_adjustment = self._analyze_dayun_influence(dayun_data, liunian_data, base_score)
            logger.info(f"   大运影响调整: {dayun_adjustment:.2f}")
        
        # 综合评分（加权平均）
        final_score = (
            stem_relation_score * 0.30 +
            branch_relation_score * 0.25 +
            ten_gods_score * 0.20 +
            deities_score * 0.15 +
            element_balance_score * 0.10
        ) + dayun_adjustment
        
        # 限制在0-100之间
        final_score = max(0.0, min(100.0, final_score))
        
        # 判定吉凶等级
        auspicious_level = self._determine_auspicious_level(final_score)
        
        result = {
            'auspicious_score': round(final_score, 2),
            'auspicious_level': auspicious_level,
            'score_breakdown': {
                'stem_relation': round(stem_relation_score, 2),
                'branch_relation': round(branch_relation_score, 2),
                'ten_gods': round(ten_gods_score, 2),
                'deities': round(deities_score, 2),
                'element_balance': round(element_balance_score, 2),
                'dayun_adjustment': round(dayun_adjustment, 2)
            },
            'analysis': self._generate_analysis_text(
                final_score, auspicious_level, stem_relation_score,
                branch_relation_score, ten_gods_score, deities_score
            )
        }
        
        logger.info(f"✅ 流年吉凶评分完成: {final_score:.2f}分 ({auspicious_level})")
        return result
    
    def _analyze_stem_relation(self, day_stem: str, liunian_stem: str, base_score: float) -> float:
        """
        分析流年天干与日干的关系
        
        Args:
            day_stem: 日干
            liunian_stem: 流年天干
            base_score: 基础分数
            
        Returns:
            评分（0-100）
        """
        if not day_stem or not liunian_stem:
            return base_score
        
        day_element = STEM_ELEMENTS.get(day_stem, '')
        liunian_element = STEM_ELEMENTS.get(liunian_stem, '')
        
        if not day_element or not liunian_element:
            return base_score
        
        relations = self.ELEMENT_RELATIONS.get(day_element, {})
        
        # 同五行（比和）
        if day_element == liunian_element:
            return base_score + 10  # 比和，平稳偏吉
        
        # 生我者（印绶）
        if relations.get('produced_by') == liunian_element:
            return base_score + 20  # 得生，大吉
        
        # 我生者（食伤）
        if relations.get('produces') == liunian_element:
            return base_score - 5  # 泄气，稍弱
        
        # 我克者（财）
        if relations.get('controls') == liunian_element:
            return base_score + 15  # 得财，吉利
        
        # 克我者（官杀）
        if relations.get('controlled_by') == liunian_element:
            return base_score - 10  # 受克，不利
        
        return base_score
    
    def _analyze_branch_relation(self, day_branch: str, liunian_branch: str, base_score: float) -> float:
        """
        分析流年地支与日支的关系
        
        Args:
            day_branch: 日支
            liunian_branch: 流年地支
            base_score: 基础分数
            
        Returns:
            评分（0-100）
        """
        if not day_branch or not liunian_branch:
            return base_score
        
        score = base_score
        
        # 六合（吉利）
        if BRANCH_LIUHE.get(day_branch) == liunian_branch:
            score += 15
            logger.debug(f"   日支{day_branch}与流年{liunian_branch}六合，+15分")
        
        # 六冲（不利）
        if BRANCH_CHONG.get(day_branch) == liunian_branch:
            score -= 20
            logger.debug(f"   日支{day_branch}与流年{liunian_branch}六冲，-20分")
        
        # 三刑（不利）
        xing_list = BRANCH_XING.get(day_branch, [])
        if liunian_branch in xing_list:
            score -= 15
            logger.debug(f"   日支{day_branch}与流年{liunian_branch}相刑，-15分")
        
        # 六害（不利）
        hai_list = BRANCH_HAI.get(day_branch, [])
        if liunian_branch in hai_list:
            score -= 10
            logger.debug(f"   日支{day_branch}与流年{liunian_branch}相害，-10分")
        
        # 同支（伏吟，不利）
        if day_branch == liunian_branch:
            score -= 5
            logger.debug(f"   日支{day_branch}与流年{liunian_branch}相同（伏吟），-5分")
        
        return max(0.0, min(100.0, score))
    
    def _analyze_ten_gods(self, liunian_main_star: str, base_score: float) -> float:
        """
        分析流年十神的吉凶
        
        Args:
            liunian_main_star: 流年主星（十神）
            base_score: 基础分数
            
        Returns:
            评分（0-100）
        """
        if not liunian_main_star:
            return base_score
        
        if liunian_main_star in self.AUSPICIOUS_TEN_GODS:
            # 吉神，加分
            bonus = {
                '正官': 20,
                '正印': 18,
                '正财': 15,
                '食神': 12
            }.get(liunian_main_star, 10)
            return base_score + bonus
        elif liunian_main_star in self.INASPICIOUS_TEN_GODS:
            # 凶神，减分
            penalty = {
                '七杀': -20,
                '偏印': -15,
                '偏财': -10,
                '伤官': -12,
                '劫财': -15
            }.get(liunian_main_star, -10)
            return base_score + penalty
        else:
            # 中性
            return base_score
    
    def _analyze_deities(self, liunian_deities: List[str], base_score: float) -> float:
        """
        分析流年神煞的吉凶
        
        Args:
            liunian_deities: 流年神煞列表
            base_score: 基础分数
            
        Returns:
            评分（0-100）
        """
        if not liunian_deities:
            return base_score
        
        score = base_score
        
        # 吉神煞
        auspicious_deities = ['天乙贵人', '天德', '月德', '文昌', '学堂', '金舆', '禄神']
        # 凶神煞
        inauspicious_deities = ['空亡', '羊刃', '劫煞', '灾煞', '天罗', '地网']
        
        for deity in liunian_deities:
            if deity in auspicious_deities:
                score += 5  # 每个吉神煞+5分
            elif deity in inauspicious_deities:
                score -= 5  # 每个凶神煞-5分
        
        return max(0.0, min(100.0, score))
    
    def _analyze_element_balance(
        self,
        bazi_data: Dict[str, Any],
        liunian_data: Dict[str, Any],
        base_score: float
    ) -> float:
        """
        分析流年对命局五行平衡的影响
        
        Args:
            bazi_data: 八字数据
            liunian_data: 流年数据
            base_score: 基础分数
            
        Returns:
            评分（0-100）
        """
        # 获取命局五行统计
        element_counts = bazi_data.get('element_counts', {})
        if not element_counts:
            return base_score
        
        # 获取流年五行
        liunian_stem = liunian_data.get('stem', '')
        liunian_branch = liunian_data.get('branch', '')
        
        liunian_stem_element = STEM_ELEMENTS.get(liunian_stem, '')
        liunian_branch_element = BRANCH_ELEMENTS.get(liunian_branch, '')
        
        # 计算流年带来的五行
        liunian_elements = {}
        if liunian_stem_element:
            liunian_elements[liunian_stem_element] = liunian_elements.get(liunian_stem_element, 0) + 1
        if liunian_branch_element:
            liunian_elements[liunian_branch_element] = liunian_elements.get(liunian_branch_element, 0) + 1
        
        # 分析流年五行是否有助于平衡命局
        # 如果命局某五行过弱，流年补强则吉
        # 如果命局某五行过强，流年再加强则可能不利
        
        score = base_score
        
        # 简化分析：如果流年五行与日干五行相生，加分
        day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
        day_element = STEM_ELEMENTS.get(day_stem, '')
        
        if day_element and liunian_stem_element:
            relations = self.ELEMENT_RELATIONS.get(day_element, {})
            if relations.get('produced_by') == liunian_stem_element:
                score += 10  # 流年生我，有利
        
        return max(0.0, min(100.0, score))
    
    def _analyze_dayun_influence(
        self,
        dayun_data: Dict[str, Any],
        liunian_data: Dict[str, Any],
        base_score: float
    ) -> float:
        """
        分析大运对流年的影响
        
        Args:
            dayun_data: 大运数据
            liunian_data: 流年数据
            base_score: 基础分数
            
        Returns:
            调整分数（可为正负）
        """
        # 如果大运与流年相合，增强影响
        dayun_stem = dayun_data.get('stem', '')
        dayun_branch = dayun_data.get('branch', '')
        liunian_stem = liunian_data.get('stem', '')
        liunian_branch = liunian_data.get('branch', '')
        
        adjustment = 0.0
        
        # 天干五合
        if dayun_stem and liunian_stem:
            if STEM_HE.get(dayun_stem) == liunian_stem:
                adjustment += 5  # 天干合，增强影响
        
        # 地支六合
        if dayun_branch and liunian_branch:
            if BRANCH_LIUHE.get(dayun_branch) == liunian_branch:
                adjustment += 5  # 地支合，增强影响
        
        # 地支六冲
        if dayun_branch and liunian_branch:
            if BRANCH_CHONG.get(dayun_branch) == liunian_branch:
                adjustment -= 10  # 地支冲，不利
        
        return adjustment
    
    def _determine_auspicious_level(self, score: float) -> str:
        """
        判定吉凶等级
        
        Args:
            score: 评分（0-100）
            
        Returns:
            等级：'大吉', '吉', '中平', '凶', '大凶'
        """
        if score >= 80:
            return '大吉'
        elif score >= 65:
            return '吉'
        elif score >= 45:
            return '中平'
        elif score >= 30:
            return '凶'
        else:
            return '大凶'
    
    def _generate_analysis_text(
        self,
        final_score: float,
        auspicious_level: str,
        stem_score: float,
        branch_score: float,
        ten_gods_score: float,
        deities_score: float
    ) -> str:
        """
        生成分析文本
        
        Args:
            final_score: 最终评分
            auspicious_level: 吉凶等级
            其他参数: 各项评分
            
        Returns:
            分析文本
        """
        lines = []
        lines.append(f"流年吉凶评分: {final_score:.1f}分 ({auspicious_level})")
        lines.append("")
        lines.append("评分构成:")
        lines.append(f"  - 天干关系: {stem_score:.1f}分")
        lines.append(f"  - 地支关系: {branch_score:.1f}分")
        lines.append(f"  - 十神影响: {ten_gods_score:.1f}分")
        lines.append(f"  - 神煞影响: {deities_score:.1f}分")
        
        return "\n".join(lines)


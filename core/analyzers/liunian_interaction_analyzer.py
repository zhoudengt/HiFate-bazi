#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年与命局互动分析器
分析流年干支与命局四柱的互动关系，计算生克、合化等影响
"""

import logging
from typing import Dict, List, Any, Optional
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import (
    BRANCH_CHONG, BRANCH_XING, BRANCH_HAI, BRANCH_LIUHE,
    BRANCH_SANHE_GROUPS, BRANCH_SANHUI_GROUPS,
    STEM_HE
)

logger = logging.getLogger(__name__)


class LiunianInteractionAnalyzer:
    """流年与命局互动分析器"""
    
    # 五行生克关系
    ELEMENT_RELATIONS = {
        '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
        '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
        '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
        '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
        '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
    }
    
    def __init__(self):
        """初始化分析器"""
        logger.info("✅ 流年与命局互动分析器初始化完成")
    
    def analyze_interaction(
        self,
        bazi_data: Dict[str, Any],
        liunian_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析流年与命局的互动关系
        
        Args:
            bazi_data: 八字数据（包含四柱）
            liunian_data: 流年数据
            
        Returns:
            互动分析结果
        """
        logger.info("🔍 开始分析流年与命局互动")
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        liunian_stem = liunian_data.get('stem', '')
        liunian_branch = liunian_data.get('branch', '')
        
        if not liunian_stem or not liunian_branch:
            return {'error': '流年数据不完整'}
        
        interactions = []
        
        # 分析流年与四柱的互动
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            if not pillar:
                continue
            
            pillar_stem = pillar.get('stem', '')
            pillar_branch = pillar.get('branch', '')
            
            if not pillar_stem or not pillar_branch:
                continue
            
            # 分析流年与这一柱的互动
            interaction = self._analyze_pillar_interaction(
                pillar_type, pillar_stem, pillar_branch,
                liunian_stem, liunian_branch
            )
            
            if interaction:
                interactions.append(interaction)
        
        # 综合分析
        summary = self._generate_summary(interactions)
        
        result = {
            'liunian': {
                'stem': liunian_stem,
                'branch': liunian_branch,
                'ganzhi': f"{liunian_stem}{liunian_branch}"
            },
            'interactions': interactions,
            'summary': summary,
            'key_findings': self._extract_key_findings(interactions)
        }
        
        logger.info(f"✅ 互动分析完成，共 {len(interactions)} 个互动关系")
        return result
    
    def _analyze_pillar_interaction(
        self,
        pillar_type: str,
        pillar_stem: str, pillar_branch: str,
        liunian_stem: str, liunian_branch: str
    ) -> Optional[Dict[str, Any]]:
        """
        分析流年与单柱的互动
        
        Args:
            pillar_type: 柱类型（year/month/day/hour）
            pillar_stem, pillar_branch: 柱的干支
            liunian_stem, liunian_branch: 流年干支
            
        Returns:
            互动关系字典
        """
        interactions = []
        
        # 1. 天干关系
        stem_relation = self._analyze_stem_relation(pillar_stem, liunian_stem)
        if stem_relation:
            interactions.append(stem_relation)
        
        # 2. 地支关系
        branch_relation = self._analyze_branch_relation(pillar_branch, liunian_branch)
        if branch_relation:
            interactions.append(branch_relation)
        
        # 3. 特殊组合（三合、三会等）
        special_combinations = self._analyze_special_combinations(
            pillar_branch, liunian_branch
        )
        if special_combinations:
            interactions.extend(special_combinations)
        
        if not interactions:
            return None
        
        return {
            'pillar': pillar_type,
            'pillar_ganzhi': f"{pillar_stem}{pillar_branch}",
            'interactions': interactions,
            'impact_level': self._calculate_impact_level(interactions)
        }
    
    def _analyze_stem_relation(self, pillar_stem: str, liunian_stem: str) -> Optional[Dict[str, Any]]:
        """分析天干关系"""
        if not pillar_stem or not liunian_stem:
            return None
        
        relation_type = None
        description = None
        impact = 'neutral'
        
        # 天干五合
        if STEM_HE.get(pillar_stem) == liunian_stem:
            relation_type = '合'
            description = f'流年{liunian_stem}与{pillar_stem}天干五合'
            impact = 'positive'
        elif pillar_stem == liunian_stem:
            relation_type = '同'
            description = f'流年{liunian_stem}与{pillar_stem}相同（伏吟）'
            impact = 'negative'
        else:
            # 五行生克关系
            pillar_element = STEM_ELEMENTS.get(pillar_stem, '')
            liunian_element = STEM_ELEMENTS.get(liunian_stem, '')
            
            if pillar_element and liunian_element:
                relations = self.ELEMENT_RELATIONS.get(pillar_element, {})
                
                if relations.get('produced_by') == liunian_element:
                    relation_type = '生'
                    description = f'流年{liunian_stem}生{pillar_stem}'
                    impact = 'positive'
                elif relations.get('produces') == liunian_element:
                    relation_type = '泄'
                    description = f'流年{liunian_stem}泄{pillar_stem}'
                    impact = 'neutral'
                elif relations.get('controls') == liunian_element:
                    relation_type = '克出'
                    description = f'流年{liunian_stem}被{pillar_stem}克'
                    impact = 'positive'
                elif relations.get('controlled_by') == liunian_element:
                    relation_type = '受克'
                    description = f'流年{liunian_stem}克{pillar_stem}'
                    impact = 'negative'
        
        if relation_type:
            return {
                'type': 'stem',
                'relation': relation_type,
                'description': description,
                'impact': impact
            }
        
        return None
    
    def _analyze_branch_relation(self, pillar_branch: str, liunian_branch: str) -> Optional[Dict[str, Any]]:
        """分析地支关系"""
        if not pillar_branch or not liunian_branch:
            return None
        
        relation_type = None
        description = None
        impact = 'neutral'
        
        # 六合
        if BRANCH_LIUHE.get(pillar_branch) == liunian_branch:
            relation_type = '合'
            description = f'流年{liunian_branch}与{pillar_branch}地支六合'
            impact = 'positive'
        # 六冲
        elif BRANCH_CHONG.get(pillar_branch) == liunian_branch:
            relation_type = '冲'
            description = f'流年{liunian_branch}与{pillar_branch}地支六冲'
            impact = 'negative'
        # 三刑
        elif liunian_branch in BRANCH_XING.get(pillar_branch, []):
            relation_type = '刑'
            description = f'流年{liunian_branch}与{pillar_branch}相刑'
            impact = 'negative'
        # 六害
        elif liunian_branch in BRANCH_HAI.get(pillar_branch, []):
            relation_type = '害'
            description = f'流年{liunian_branch}与{pillar_branch}相害'
            impact = 'negative'
        # 相同（伏吟）
        elif pillar_branch == liunian_branch:
            relation_type = '同'
            description = f'流年{liunian_branch}与{pillar_branch}相同（伏吟）'
            impact = 'negative'
        
        if relation_type:
            return {
                'type': 'branch',
                'relation': relation_type,
                'description': description,
                'impact': impact
            }
        
        return None
    
    def _analyze_special_combinations(
        self,
        pillar_branch: str,
        liunian_branch: str
    ) -> List[Dict[str, Any]]:
        """分析特殊组合（三合、三会等）"""
        combinations = []
        
        # 检查三合局
        for sanhe_group in BRANCH_SANHE_GROUPS:
            if pillar_branch in sanhe_group and liunian_branch in sanhe_group:
                combinations.append({
                    'type': 'special',
                    'relation': '三合',
                    'description': f'流年{liunian_branch}与{pillar_branch}形成三合局',
                    'impact': 'positive'
                })
        
        # 检查三会局
        for sanhui_group in BRANCH_SANHUI_GROUPS:
            if pillar_branch in sanhui_group and liunian_branch in sanhui_group:
                combinations.append({
                    'type': 'special',
                    'relation': '三会',
                    'description': f'流年{liunian_branch}与{pillar_branch}形成三会局',
                    'impact': 'positive'
                })
        
        return combinations
    
    def _calculate_impact_level(self, interactions: List[Dict[str, Any]]) -> str:
        """计算影响程度"""
        positive_count = sum(1 for i in interactions if i.get('impact') == 'positive')
        negative_count = sum(1 for i in interactions if i.get('impact') == 'negative')
        
        if positive_count > negative_count * 2:
            return 'strong_positive'
        elif positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count * 2:
            return 'strong_negative'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _generate_summary(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成综合分析摘要"""
        total_interactions = len(interactions)
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for interaction in interactions:
            for rel in interaction.get('interactions', []):
                impact = rel.get('impact', 'neutral')
                if impact == 'positive':
                    positive_count += 1
                elif impact == 'negative':
                    negative_count += 1
                else:
                    neutral_count += 1
        
        return {
            'total_interactions': total_interactions,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'overall_impact': 'positive' if positive_count > negative_count else ('negative' if negative_count > positive_count else 'neutral')
        }
    
    def _extract_key_findings(self, interactions: List[Dict[str, Any]]) -> List[str]:
        """提取关键发现"""
        findings = []
        
        for interaction in interactions:
            pillar = interaction.get('pillar', '')
            impact_level = interaction.get('impact_level', '')
            
            if impact_level in ['strong_positive', 'strong_negative']:
                findings.append(
                    f"{pillar}柱与流年互动强烈，影响程度：{impact_level}"
                )
        
        return findings


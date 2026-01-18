#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十神关系深度分析器
分析十神之间的生克关系、组合吉凶程度、特殊格局识别
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class TenGodsAnalyzer:
    """十神关系深度分析器"""
    
    # 十神生克关系
    TEN_GODS_RELATIONS = {
        '比肩': {'produces': [], 'controls': ['偏财', '正财'], 'produced_by': ['偏印', '正印'], 'controlled_by': ['七杀', '正官']},
        '劫财': {'produces': [], 'controls': ['偏财', '正财'], 'produced_by': ['偏印', '正印'], 'controlled_by': ['七杀', '正官']},
        '食神': {'produces': ['偏财', '正财'], 'controls': ['七杀'], 'produced_by': ['比肩', '劫财'], 'controlled_by': ['偏印', '正印']},
        '伤官': {'produces': ['偏财', '正财'], 'controls': ['正官'], 'produced_by': ['比肩', '劫财'], 'controlled_by': ['偏印', '正印']},
        '偏财': {'produces': ['七杀', '正官'], 'controls': ['偏印', '正印'], 'produced_by': ['食神', '伤官'], 'controlled_by': ['比肩', '劫财']},
        '正财': {'produces': ['七杀', '正官'], 'controls': ['偏印', '正印'], 'produced_by': ['食神', '伤官'], 'controlled_by': ['比肩', '劫财']},
        '七杀': {'produces': ['偏印', '正印'], 'controls': ['比肩', '劫财'], 'produced_by': ['偏财', '正财'], 'controlled_by': ['食神']},
        '正官': {'produces': ['偏印', '正印'], 'controls': ['比肩', '劫财'], 'produced_by': ['偏财', '正财'], 'controlled_by': ['伤官']},
        '偏印': {'produces': ['比肩', '劫财'], 'controls': ['食神', '伤官'], 'produced_by': ['七杀', '正官'], 'controlled_by': ['偏财', '正财']},
        '正印': {'produces': ['比肩', '劫财'], 'controls': ['食神', '伤官'], 'produced_by': ['七杀', '正官'], 'controlled_by': ['偏财', '正财']},
    }
    
    # 十神吉凶分类
    AUSPICIOUS_TEN_GODS = ['正官', '正印', '正财', '食神']  # 吉神
    INAUSPICIOUS_TEN_GODS = ['七杀', '偏印', '偏财', '伤官', '劫财']  # 凶神
    NEUTRAL_TEN_GODS = ['比肩']  # 中性
    
    # 特殊格局模式
    SPECIAL_PATTERNS = {
        '食神制杀': {
            'required': ['食神', '七杀'],
            'description': '食神制杀：食神克制七杀，化凶为吉',
            'auspicious_degree': 0.8
        },
        '伤官见官': {
            'required': ['伤官', '正官'],
            'description': '伤官见官：伤官克制正官，可能不利',
            'auspicious_degree': 0.3
        },
        '财生官': {
            'required': ['偏财', '正官'],
            'description': '财生官：财生官，富贵格局',
            'auspicious_degree': 0.9
        },
        '印绶护身': {
            'required': ['正印', '比肩'],
            'description': '印绶护身：印生比肩，护身有力',
            'auspicious_degree': 0.7
        },
        '比劫夺财': {
            'required': ['比肩', '正财'],
            'description': '比劫夺财：比肩克制正财，可能破财',
            'auspicious_degree': 0.4
        },
    }
    
    def __init__(self):
        """初始化分析器"""
        logger.info("✅ 十神关系分析器初始化完成")
    
    def analyze(self, bazi_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析十神关系
        
        Args:
            bazi_data: 八字数据（包含details中的十神信息）
            
        Returns:
            十神关系分析结果
        """
        logger.info("🔍 开始十神关系分析")
        
        # 1. 提取所有十神
        all_ten_gods = self._extract_all_ten_gods(bazi_data)
        logger.info(f"   提取的十神: {all_ten_gods}")
        
        # 2. 分析十神生克关系
        relations = self._analyze_relations(all_ten_gods)
        logger.info(f"   生克关系: {len(relations)} 条")
        
        # 3. 计算十神组合吉凶程度
        auspicious_degree = self._calculate_auspicious_degree(all_ten_gods, relations)
        logger.info(f"   吉凶程度: {auspicious_degree:.2f}")
        
        # 4. 识别特殊格局
        special_patterns = self._identify_special_patterns(all_ten_gods)
        logger.info(f"   特殊格局: {len(special_patterns)} 个")
        
        # 5. 分析十神平衡度
        balance = self._analyze_balance(all_ten_gods)
        logger.info(f"   平衡度: {balance:.2f}")
        
        result = {
            'all_ten_gods': all_ten_gods,
            'ten_gods_count': dict(Counter(all_ten_gods)),
            'relations': relations,
            'auspicious_degree': auspicious_degree,
            'special_patterns': special_patterns,
            'balance': balance,
            'analysis': self._generate_analysis_text(all_ten_gods, relations, special_patterns, auspicious_degree)
        }
        
        logger.info("✅ 十神关系分析完成")
        return result
    
    def _extract_all_ten_gods(self, bazi_data: Dict[str, Any]) -> List[str]:
        """
        从八字数据中提取所有十神
        
        Args:
            bazi_data: 八字数据
            
        Returns:
            十神列表
        """
        ten_gods = []
        details = bazi_data.get('details', {})
        
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_detail = details.get(pillar_type, {})
            
            # 提取主星
            main_star = pillar_detail.get('main_star')
            if main_star and main_star in self.TEN_GODS_RELATIONS:
                ten_gods.append(main_star)
            
            # 提取副星（hidden_stars）
            hidden_stars = pillar_detail.get('hidden_stars', [])
            if isinstance(hidden_stars, list):
                for star in hidden_stars:
                    if star in self.TEN_GODS_RELATIONS:
                        ten_gods.append(star)
            elif isinstance(hidden_stars, str) and hidden_stars in self.TEN_GODS_RELATIONS:
                ten_gods.append(hidden_stars)
        
        return ten_gods
    
    def _analyze_relations(self, ten_gods: List[str]) -> List[Dict[str, Any]]:
        """
        分析十神之间的生克关系
        
        Args:
            ten_gods: 十神列表
            
        Returns:
            关系列表
        """
        relations = []
        ten_gods_set = set(ten_gods)
        
        for ten_god in ten_gods_set:
            relation_info = self.TEN_GODS_RELATIONS.get(ten_god, {})
            
            # 检查生我者
            produces = relation_info.get('produces', [])
            for produced in produces:
                if produced in ten_gods_set:
                    relations.append({
                        'type': 'produces',
                        'from': ten_god,
                        'to': produced,
                        'description': f'{ten_god}生{produced}'
                    })
            
            # 检查克我者
            controls = relation_info.get('controls', [])
            for controlled in controls:
                if controlled in ten_gods_set:
                    relations.append({
                        'type': 'controls',
                        'from': ten_god,
                        'to': controlled,
                        'description': f'{ten_god}克{controlled}'
                    })
        
        return relations
    
    def _calculate_auspicious_degree(self, ten_gods: List[str], relations: List[Dict[str, Any]]) -> float:
        """
        计算十神组合的吉凶程度（0-1，越高越吉）
        
        Args:
            ten_gods: 十神列表
            relations: 关系列表
            
        Returns:
            吉凶程度（0-1）
        """
        if not ten_gods:
            return 0.5  # 中性
        
        # 统计吉神和凶神数量
        auspicious_count = sum(1 for tg in ten_gods if tg in self.AUSPICIOUS_TEN_GODS)
        inauspicious_count = sum(1 for tg in ten_gods if tg in self.INASPICIOUS_TEN_GODS)
        neutral_count = sum(1 for tg in ten_gods if tg in self.NEUTRAL_TEN_GODS)
        
        total = len(ten_gods)
        
        # 基础分数：吉神越多越好，凶神越多越差
        base_score = (auspicious_count * 1.0 + neutral_count * 0.5 - inauspicious_count * 0.5) / total
        
        # 根据关系调整分数
        relation_bonus = 0.0
        for relation in relations:
            if relation['type'] == 'controls':
                # 吉神克制凶神，加分
                if relation['from'] in self.AUSPICIOUS_TEN_GODS and relation['to'] in self.INASPICIOUS_TEN_GODS:
                    relation_bonus += 0.1
                # 凶神克制吉神，减分
                elif relation['from'] in self.INASPICIOUS_TEN_GODS and relation['to'] in self.AUSPICIOUS_TEN_GODS:
                    relation_bonus -= 0.1
        
        # 归一化到0-1
        final_score = max(0.0, min(1.0, base_score + relation_bonus))
        
        return final_score
    
    def _identify_special_patterns(self, ten_gods: List[str]) -> List[Dict[str, Any]]:
        """
        识别特殊十神格局
        
        Args:
            ten_gods: 十神列表
            
        Returns:
            特殊格局列表
        """
        patterns = []
        ten_gods_set = set(ten_gods)
        
        for pattern_name, pattern_info in self.SPECIAL_PATTERNS.items():
            required = pattern_info['required']
            
            # 检查是否包含所有必需的十神
            if all(tg in ten_gods_set for tg in required):
                patterns.append({
                    'name': pattern_name,
                    'description': pattern_info['description'],
                    'auspicious_degree': pattern_info['auspicious_degree'],
                    'required_ten_gods': required
                })
        
        return patterns
    
    def _analyze_balance(self, ten_gods: List[str]) -> float:
        """
        分析十神平衡度（0-1，越高越平衡）
        
        Args:
            ten_gods: 十神列表
            
        Returns:
            平衡度（0-1）
        """
        if not ten_gods:
            return 0.5
        
        # 统计各类十神数量
        counter = Counter(ten_gods)
        
        # 计算分布的均匀度（使用熵的概念）
        total = len(ten_gods)
        unique_count = len(counter)
        
        # 如果十神种类多且分布均匀，平衡度高
        if unique_count == 0:
            return 0.0
        
        # 计算熵（信息熵）
        entropy = 0.0
        for count in counter.values():
            p = count / total
            if p > 0:
                entropy -= p * (p.bit_length() - 1)  # 简化版熵计算
        
        # 归一化到0-1（最大熵为log2(unique_count)）
        max_entropy = (unique_count.bit_length() - 1) if unique_count > 0 else 1
        balance = entropy / max_entropy if max_entropy > 0 else 0.5
        
        return max(0.0, min(1.0, balance))
    
    def _generate_analysis_text(self, ten_gods: List[str], relations: List[Dict[str, Any]], 
                                special_patterns: List[Dict[str, Any]], auspicious_degree: float) -> str:
        """
        生成分析文本
        
        Args:
            ten_gods: 十神列表
            relations: 关系列表
            special_patterns: 特殊格局列表
            auspicious_degree: 吉凶程度
            
        Returns:
            分析文本
        """
        lines = []
        
        # 十神统计
        counter = Counter(ten_gods)
        lines.append(f"十神统计: {dict(counter)}")
        
        # 吉凶程度
        if auspicious_degree >= 0.7:
            lines.append("整体格局：较为吉利")
        elif auspicious_degree >= 0.5:
            lines.append("整体格局：中性偏吉")
        elif auspicious_degree >= 0.3:
            lines.append("整体格局：中性偏凶")
        else:
            lines.append("整体格局：较为不利")
        
        # 特殊格局
        if special_patterns:
            lines.append("特殊格局:")
            for pattern in special_patterns:
                lines.append(f"  - {pattern['name']}: {pattern['description']}")
        
        # 重要关系
        important_relations = [r for r in relations if r['type'] == 'controls']
        if important_relations:
            lines.append("重要生克关系:")
            for rel in important_relations[:5]:  # 只显示前5个
                lines.append(f"  - {rel['description']}")
        
        return "\n".join(lines)


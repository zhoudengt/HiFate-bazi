# -*- coding: utf-8 -*-
"""
面相知识库V2微服务
"""

import logging
from typing import List, Dict
import pymysql
from pathlib import Path
from .rule_matcher import RuleMatcher
from .face_rules_config import get_all_rules

logger = logging.getLogger(__name__)
project_root = Path(__file__).parent.parent.parent


class FaceKnowledgeService:
    """面相知识库服务"""
    
    def __init__(self):
        self.rules_cache = {}
        self.rule_matcher = RuleMatcher()
        self._load_rules_from_config()
    
    def _load_rules_from_config(self):
        """从内置配置加载规则（不再读取外部文件）"""
        try:
            all_rules = get_all_rules()
            self.rules_cache = all_rules
            logger.info(f"✅ 面相规则加载完成（使用内置配置），共 {len(all_rules)} 类规则")
        except Exception as e:
            logger.error(f"❌ 加载面相规则失败: {e}")
            self.rules_cache = {}
    
    def query_rules(self, rule_type: str, position: str = None) -> List[Dict]:
        """
        查询规则
        
        Args:
            rule_type: 规则类型
            position: 位置（可选）
        
        Returns:
            规则列表
        """
        rules = self.rules_cache.get(f'{rule_type}_rules', [])
        
        if position:
            rules = [r for r in rules if r.get('position') == position]
        
        return rules
    
    def match_rules(self, rule_type: str, features: Dict) -> List[Dict]:
        """
        匹配规则
        
        Args:
            rule_type: 规则类型
            features: 特征字典
        
        Returns:
            匹配的规则列表
        """
        all_rules = self.query_rules(rule_type)
        matched = []
        
        for rule in all_rules:
            if self._check_rule_match(rule, features):
                matched.append({
                    'rule': rule,
                    'confidence': 0.8,  # 简化处理
                    'matched_features': features
                })
        
        return matched
    
    def _check_rule_match(self, rule: Dict, features: Dict) -> bool:
        """检查规则是否匹配"""
        # 简化的匹配逻辑
        # 实际应该根据规则的conditions进行详细匹配
        
        rule_conditions = rule.get('conditions', {})
        
        # 如果没有条件，匹配所有
        if not rule_conditions:
            return True
        
        # 简单匹配：检查位置
        if 'position' in features and 'position' in rule:
            return features['position'] == rule['position']
        
        return True
    
    def get_interpretation(self, rule_type: str, position: str, 
                          features: Dict = None, confidence_scores: Dict = None) -> List[str]:
        """
        获取断语（应用互斥和去重逻辑）
        
        Args:
            rule_type: 规则类型
            position: 位置
            features: 识别到的特征字典
            confidence_scores: 置信度分数
        
        Returns:
            去重合并后的断语列表（字符串列表）
        """
        rules = self.query_rules(rule_type, position)
        
        if not rules:
            return []
        
        # 使用规则匹配器进行过滤和合并
        matched_rules = self.rule_matcher.match_and_filter(
            rules, 
            features or {}, 
            confidence_scores
        )
        
        # matched_rules 中每个位置只有一条合并后的规则
        # 每条规则的 interpretations 字段已经是去重后的字符串列表
        
        # 提取断语（使用set去重，避免重复）
        interpretations_set = set()
        interpretations_list = []
        
        for rule in matched_rules:
            rule_interps = rule.get('interpretations', [])
            
            # 确保是列表
            if not isinstance(rule_interps, list):
                rule_interps = [rule_interps] if rule_interps else []
            
            # 去重添加
            for interp in rule_interps:
                if interp and interp not in interpretations_set:
                    interpretations_set.add(interp)
                    interpretations_list.append(interp)
        
        return interpretations_list


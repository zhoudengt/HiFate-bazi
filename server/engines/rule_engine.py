#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的规则引擎 - 支持高性能规则匹配
支持：年柱、月柱、日柱、时柱、四柱神煞、组合条件等
"""

import json
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import os

from .rule_condition import EnhancedRuleCondition


class EnhancedRuleEngine:
    """增强的规则引擎（带索引优化）"""
    
    def __init__(self, rules: List[Dict] = None, use_index: bool = True):
        """
        初始化规则引擎
        
        Args:
            rules: 规则列表
            use_index: 是否使用索引优化
        """
        self.rules = rules or []
        self.use_index = use_index
        self._index = {}
        if use_index:
            self._build_advanced_index()
    
    def _build_advanced_index(self):
        """构建高级索引以提高匹配性能"""
        self._index = {
            'by_year_pillar': {},      # 年柱索引
            'by_month_pillar': {},     # 月柱索引
            'by_day_pillar': {},       # 日柱索引
            'by_hour_pillar': {},      # 时柱索引
            'by_deity': {},            # 神煞索引
            'by_rule_type': {},        # 规则类型索引
        }
        
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
                
            conditions = rule.get('conditions', {})
            rule_type = rule.get('rule_type', 'default')
            
            # 索引规则类型
            if rule_type not in self._index['by_rule_type']:
                self._index['by_rule_type'][rule_type] = []
            self._index['by_rule_type'][rule_type].append(rule)
            
            # 索引年柱
            if 'year_pillar' in conditions:
                year_pillar = conditions['year_pillar']
                if isinstance(year_pillar, list):
                    for yp in year_pillar:
                        if yp not in self._index['by_year_pillar']:
                            self._index['by_year_pillar'][yp] = []
                        self._index['by_year_pillar'][yp].append(rule)
                else:
                    if year_pillar not in self._index['by_year_pillar']:
                        self._index['by_year_pillar'][year_pillar] = []
                    self._index['by_year_pillar'][year_pillar].append(rule)
            
            # 索引日柱
            if 'day_pillar' in conditions or 'rizhu' in conditions:
                day_pillar = conditions.get('day_pillar') or conditions.get('rizhu')
                if isinstance(day_pillar, list):
                    for dp in day_pillar:
                        if dp not in self._index['by_day_pillar']:
                            self._index['by_day_pillar'][dp] = []
                        self._index['by_day_pillar'][dp].append(rule)
                else:
                    if day_pillar not in self._index['by_day_pillar']:
                        self._index['by_day_pillar'][day_pillar] = []
                    self._index['by_day_pillar'][day_pillar].append(rule)
            
            # 索引神煞
            for key in ['deities_in_any_pillar', 'deities_in_year', 'deities_in_month', 
                       'deities_in_day', 'deities_in_hour']:
                if key in conditions:
                    deities = conditions[key]
                    if isinstance(deities, list):
                        for deity in deities:
                            if deity not in self._index['by_deity']:
                                self._index['by_deity'][deity] = []
                            self._index['by_deity'][deity].append(rule)
                    else:
                        if deities not in self._index['by_deity']:
                            self._index['by_deity'][deities] = []
                        self._index['by_deity'][deities].append(rule)
    
    def match_rules(self, bazi_data: Dict, rule_types: List[str] = None) -> List[Dict]:
        """
        匹配规则
        
        Args:
            bazi_data: 八字数据
            rule_types: 要匹配的规则类型列表，None表示匹配所有类型
            
        Returns:
            List[Dict]: 匹配的规则列表，按优先级排序
        """
        if self.use_index:
            return self._match_rules_fast(bazi_data, rule_types)
        else:
            return self._match_rules_simple(bazi_data, rule_types)
    
    def _match_rules_fast(self, bazi_data: Dict, rule_types: List[str] = None) -> List[Dict]:
        """快速匹配（使用索引）"""
        # 1. 从索引中快速筛选候选规则
        # 使用字典来去重（key为rule_id），因为字典不能作为set的元素
        candidates_dict = {}
        
        # 优化：先获取 bazi_pillars 和 details，避免重复访问
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        details = bazi_data.get('details', {})
        
        # 根据年柱筛选
        year_pillar_data = bazi_pillars.get('year', {})
        year_pillar = f"{year_pillar_data.get('stem', '')}{year_pillar_data.get('branch', '')}"
        for rule in self._index['by_year_pillar'].get(year_pillar, []):
            rule_id = rule.get('rule_id', id(rule))
            candidates_dict[rule_id] = rule
        
        # 根据日柱筛选
        day_pillar_data = bazi_pillars.get('day', {})
        day_pillar = f"{day_pillar_data.get('stem', '')}{day_pillar_data.get('branch', '')}"
        for rule in self._index['by_day_pillar'].get(day_pillar, []):
            rule_id = rule.get('rule_id', id(rule))
            candidates_dict[rule_id] = rule
        
        # 根据规则类型筛选（如果指定了规则类型）- 优化：优先使用规则类型索引
        # ⚠️ 修复：确保所有指定的规则类型都被正确索引和筛选
        if rule_types:
            rule_types_set = set(rule_types)  # 转换为 set 提高查找速度
            for rule_type in rule_types:
                indexed_rules = self._index['by_rule_type'].get(rule_type, [])
                # 直接添加该类型的所有规则，不需要再次检查 rule_type（已经在索引中）
                for rule in indexed_rules:
                    rule_id = rule.get('rule_id', id(rule))
                    candidates_dict[rule_id] = rule
        else:
            # 如果没有指定规则类型，从所有规则类型索引中获取
            for rule_type, rules in self._index['by_rule_type'].items():
                for rule in rules:
                    rule_id = rule.get('rule_id', id(rule))
                    candidates_dict[rule_id] = rule
        
        # 根据神煞筛选（优化：减少重复访问）
        all_deities = []
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_detail = details.get(pillar_type, {})
            if isinstance(pillar_detail, dict):
                deities = pillar_detail.get('deities', [])
                if isinstance(deities, list):
                    all_deities.extend(deities)
                elif deities:
                    all_deities.append(deities)
        
        # 去重神煞列表，避免重复索引查找
        unique_deities = list(set(all_deities))
        for deity in unique_deities:
            for rule in self._index['by_deity'].get(deity, []):
                rule_id = rule.get('rule_id', id(rule))
                candidates_dict[rule_id] = rule
        
        # 转换为列表
        candidates = list(candidates_dict.values())
        
        # ⚠️ 修复：如果指定了规则类型，进一步筛选（确保只包含指定类型的规则）
        # 注意：这里需要再次筛选，因为候选规则可能来自多个索引（年柱、日柱、神煞等）
        if rule_types:
            rule_types_set = set(rule_types)
            candidates = [r for r in candidates if r.get('rule_type') in rule_types_set and r.get('enabled', True)]
        else:
            # 如果没有指定规则类型，也要过滤掉未启用的规则
            candidates = [r for r in candidates if r.get('enabled', True)]
        
        # 调试：检查候选规则中的十神命格规则
        if rule_types and 'shishen' in rule_types:
            shishen_candidates = [r for r in candidates if r.get('rule_type') == 'shishen']
            if shishen_candidates:
                import logging
                logging.debug(f"候选规则中的十神命格规则数: {len(shishen_candidates)}")
        
        # 2. 对候选规则进行精确匹配
        # ⚠️ 修复：并行处理时超时导致规则被跳过，改为串行处理确保所有规则都能匹配
        matched_rules = []
        
        for rule in candidates:
            try:
                if self._match_single_rule(rule, bazi_data):
                    matched_rules.append(rule)
            except Exception as e:
                # 如果匹配出错，记录日志但不跳过
                import logging
                logging.warning(f"规则匹配出错: {rule.get('rule_id')}: {e}")
        
        # 3. 按优先级排序
        matched_rules.sort(key=lambda r: r.get('priority', 100), reverse=True)
        
        return matched_rules
    
    def _match_rules_simple(self, bazi_data: Dict, rule_types: List[str] = None) -> List[Dict]:
        """简单匹配（不使用索引，遍历所有规则）"""
        matched_rules = []
        
        # 如果指定了规则类型，只匹配这些类型（优化：使用 set 提高查找速度）
        if rule_types:
            rule_types_set = set(rule_types)
            rules_to_check = [r for r in self.rules 
                            if r.get('rule_type') in rule_types_set and r.get('enabled', True)]
        else:
            rules_to_check = [r for r in self.rules if r.get('enabled', True)]
        
        # 并行匹配规则（提高性能）- 优化：增加超时控制
        cpu_count = os.cpu_count() or 4
        max_workers = min(cpu_count * 2, 20)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for rule in rules_to_check:
                future = executor.submit(self._match_single_rule, rule, bazi_data)
                futures.append((future, rule))
            
            for future, rule in futures:
                try:
                    # 每个规则最多1秒超时，避免单个规则阻塞整个匹配过程
                    if future.result(timeout=1.0):
                        matched_rules.append(rule)
                except Exception:
                    # 如果匹配超时或出错，跳过该规则
                    pass
        
        # 按优先级排序
        matched_rules.sort(key=lambda r: r.get('priority', 100), reverse=True)
        
        return matched_rules
    
    def _match_single_rule(self, rule: Dict, bazi_data: Dict) -> bool:
        """匹配单个规则"""
        conditions = rule.get('conditions', {})
        return EnhancedRuleCondition.match(conditions, bazi_data)
    
    def add_rule(self, rule: Dict):
        """添加规则"""
        self.rules.append(rule)
        if self.use_index:
            self._build_advanced_index()
    
    def load_from_file(self, file_path: str):
        """
        从JSON文件加载规则
        
        ⚠️ 已废弃：此方法仅用于向后兼容
        所有规则必须存储在数据库中，禁止从文件读取！
        新代码请使用 RuleService，它会自动从数据库加载规则。
        """
        import warnings
        warnings.warn(
            f"⚠️  load_from_file() 已废弃，规则应从数据库加载\n"
            f"文件路径: {file_path}\n"
            f"请使用 RuleService.match_rules() 替代",
            DeprecationWarning,
            stacklevel=2
        )
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.rules = data.get('rules', [])
            if self.use_index:
                self._build_advanced_index()
    
    def load_from_db(self, db_connection):
        """从数据库加载规则（需要实现数据库连接）"""
        # TODO: 实现数据库加载逻辑
        pass


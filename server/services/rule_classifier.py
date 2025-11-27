#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则分类映射模块

职责：
1. 将数据库中的 rule_type 映射到用户意图（intent）
2. 按意图分组匹配到的规则
3. 为 LLM 提供结构化的规则内容

设计原则：
- 模块化：独立的分类逻辑，不影响现有代码
- 可扩展：易于添加新的规则类型
- 清晰：明确的映射关系
"""

from typing import Dict, List, Any
import re


class RuleClassifier:
    """规则分类器"""
    
    # 规则类型到意图的映射
    # 格式：rule_type_pattern -> intent
    RULE_TYPE_TO_INTENT = {
        # 婚姻相关
        'marriage': 'marriage',
        'marriage_ten_gods': 'marriage',
        'marriage_element': 'marriage',
        'marriage_day_stem': 'marriage',
        'marriage_day_branch': 'marriage',
        'marriage_day_pillar': 'marriage',
        'marriage_stem_pattern': 'marriage',
        'marriage_branch_pattern': 'marriage',
        'marriage_bazi_pattern': 'marriage',
        'marriage_deity': 'marriage',
        'marriage_month_branch': 'marriage',
        'marriage_year_branch': 'marriage',
        'marriage_year_stem': 'marriage',
        'marriage_year_pillar': 'marriage',
        'marriage_nayin': 'marriage',
        'marriage_lunar_birthday': 'marriage',
        'marriage_hour_pillar': 'marriage',
        'marriage_year_event': 'marriage',
        'marriage_luck_cycle': 'marriage',
        'marriage_general': 'marriage',
        'taohua_general': 'marriage',  # 桃花归入婚姻
        
        # 财富相关
        'wealth': 'wealth',
        'wealth_ten_gods': 'wealth',
        'wealth_element': 'wealth',
        'wealth_pattern': 'wealth',
        
        # 健康/身体相关
        'health': 'health',
        'health_element': 'health',
        'health_pattern': 'health',
        
        # 性格相关
        'character': 'character',
        'personality': 'character',
        'career': 'character',  # 事业归入性格（性格影响事业）
        'shishen': 'character',  # 十神命格归入性格
        'shishen_destiny': 'character',
        'rizhu_gender': 'character',  # 日柱性格分析
        'rizhu_gender_dynamic': 'character',
        
        # 综合/通用
        'general': 'general',
        'summary': 'general',
    }
    
    # 意图中文名称
    INTENT_NAMES = {
        'marriage': '婚姻',
        'wealth': '财富',
        'health': '健康',
        'character': '性格',
        'general': '综合',
    }
    
    @classmethod
    def classify_rule(cls, rule: Dict[str, Any]) -> str:
        """
        分类单个规则到意图
        
        Args:
            rule: 规则对象，包含 rule_type、rule_code 等
            
        Returns:
            intent: 'marriage' | 'wealth' | 'health' | 'character' | 'general'
        """
        rule_type = rule.get('rule_type', '').lower()
        rule_code = rule.get('rule_code', '').upper()
        
        # 1. 精确匹配 rule_type
        if rule_type in cls.RULE_TYPE_TO_INTENT:
            return cls.RULE_TYPE_TO_INTENT[rule_type]
        
        # 2. 前缀匹配（支持动态规则）
        for pattern, intent in cls.RULE_TYPE_TO_INTENT.items():
            if rule_type.startswith(pattern):
                return intent
        
        # 3. 通过 rule_code 推断（兜底逻辑）
        # FORMULA_HEALTH_* -> health
        if 'HEALTH' in rule_code or 'FORMULA_HEALTH' in rule_code:
            return 'health'
        
        # FORMULA_WEALTH_* -> wealth
        if 'WEALTH' in rule_code or 'FORMULA_WEALTH' in rule_code:
            return 'wealth'
        
        # FORMULA_MARRIAGE_* -> marriage
        if 'MARRIAGE' in rule_code or 'FORMULA_MARRIAGE' in rule_code:
            return 'marriage'
        
        # FORMULA_CHARACTER_* -> character
        if 'CHARACTER' in rule_code or 'FORMULA_CHARACTER' in rule_code:
            return 'character'
        
        # RZ_* (日柱规则) -> character
        if rule_code.startswith('RZ_'):
            return 'character'
        
        # 默认归入 general
        return 'general'
    
    @classmethod
    def group_rules_by_intent(
        cls,
        rules: List[Dict[str, Any]],
        target_intents: List[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        按意图分组规则
        
        Args:
            rules: 规则列表
            target_intents: 目标意图列表，None 表示所有意图
            
        Returns:
            {
                'marriage': [rule1, rule2, ...],
                'wealth': [...],
                'character': [...],
                'health': [...],
                'general': [...]
            }
        """
        grouped = {
            'marriage': [],
            'wealth': [],
            'health': [],
            'character': [],
            'general': []
        }
        
        for rule in rules:
            intent = cls.classify_rule(rule)
            
            # 如果指定了目标意图，只保留目标意图的规则
            if target_intents and intent not in target_intents:
                continue
            
            if intent in grouped:
                grouped[intent].append(rule)
        
        # 删除空列表（减少数据传输）
        return {k: v for k, v in grouped.items() if v}
    
    @classmethod
    def extract_rule_summaries(
        cls,
        rules: List[Dict[str, Any]],
        max_length: int = 200,
        max_rules_per_intent: int = 10
    ) -> List[str]:
        """
        提取规则摘要（用于传递给 LLM）
        
        支持两种规则格式：
        1. content（单数）：普通规则使用 {"content": {"text": "..."}}
        2. contents（复数）：日柱规则使用 {"contents": [{"text": "..."}]}
        
        Args:
            rules: 规则列表
            max_length: 每条规则的最大长度
            max_rules_per_intent: 每个意图最多提取多少条规则
            
        Returns:
            规则摘要列表
        """
        summaries = []
        
        for i, rule in enumerate(rules[:max_rules_per_intent]):
            text = ''
            rule_code = rule.get('rule_code', '')
            rule_type = rule.get('rule_type', '')
            
            # ⭐ 修复：优先处理 contents（复数）- 日柱规则使用这种格式
            contents = rule.get('contents', [])
            if contents and isinstance(contents, list):
                # 合并所有 contents 中的文本
                text_parts = []
                for item in contents:
                    if isinstance(item, dict):
                        item_text = item.get('text', '')
                        if item_text:
                            text_parts.append(item_text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                
                if text_parts:
                    text = ' '.join(text_parts)
            
            # 如果没有 contents，尝试 content（单数）- 普通规则使用这种格式
            if not text:
                content = rule.get('content', {})
                if content:
                    if isinstance(content, dict):
                        text = content.get('text', '')
                    else:
                        text = str(content) if content else ''
            
            # 限制长度
            if len(text) > max_length:
                text = text[:max_length] + '...'
            
            if text:
                # 添加规则编号和内容
                rule_name = rule.get('rule_name', f'规则{i+1}')
                summaries.append(f"{rule_name}: {text}")
        
        return summaries
    
    @classmethod
    def build_rules_for_llm(
        cls,
        matched_rules: List[Dict[str, Any]],
        target_intents: List[str] = None,
        max_rules_per_intent: int = 10
    ) -> Dict[str, Any]:
        """
        为 LLM 构建结构化的规则数据
        
        Args:
            matched_rules: 匹配到的规则列表
            target_intents: 目标意图列表（只传递这些意图的规则）
            max_rules_per_intent: 每个意图最多传递多少条规则
            
        Returns:
            {
                'rules_by_intent': {
                    'character': ['规则1: ...', '规则2: ...'],
                    'wealth': [...]
                },
                'rules_count': {
                    'character': 5,
                    'wealth': 3,
                    'total': 8
                }
            }
        """
        # 1. 按意图分组
        grouped_rules = cls.group_rules_by_intent(matched_rules, target_intents)
        
        # 2. 提取摘要
        rules_by_intent = {}
        rules_count = {'total': 0}
        
        for intent, rules in grouped_rules.items():
            summaries = cls.extract_rule_summaries(
                rules,
                max_length=200,
                max_rules_per_intent=max_rules_per_intent
            )
            
            if summaries:
                rules_by_intent[intent] = summaries
                rules_count[intent] = len(summaries)
                rules_count['total'] += len(summaries)
        
        return {
            'rules_by_intent': rules_by_intent,
            'rules_count': rules_count
        }


# 便捷函数
def classify_rule(rule: Dict[str, Any]) -> str:
    """分类单个规则"""
    return RuleClassifier.classify_rule(rule)


def group_rules_by_intent(
    rules: List[Dict[str, Any]],
    target_intents: List[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """按意图分组规则"""
    return RuleClassifier.group_rules_by_intent(rules, target_intents)


def build_rules_for_llm(
    matched_rules: List[Dict[str, Any]],
    target_intents: List[str] = None,
    max_rules_per_intent: int = 10
) -> Dict[str, Any]:
    """为 LLM 构建规则数据"""
    return RuleClassifier.build_rules_for_llm(
        matched_rules,
        target_intents,
        max_rules_per_intent
    )


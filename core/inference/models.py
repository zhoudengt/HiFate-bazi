#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理引擎通用数据模型

所有领域推理引擎共用的输入/输出数据结构。
与 WangShuaiAnalyzer 等分析器解耦——通过适配器将分析器输出映射为 InferenceInput。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class InferenceInput:
    """
    推理引擎标准化输入。
    
    通过适配器从 bazi_data / wangshuai_result / detail_result 构建。
    如果 WangShuaiAnalyzer 输出格式变化，只需修改适配器，不需改推理引擎。
    """
    day_stem: str = ''
    day_branch: str = ''
    gender: str = 'male'
    bazi_pillars: Dict[str, Dict[str, str]] = field(default_factory=dict)
    wangshuai: str = ''
    wuxing_power: Dict[str, float] = field(default_factory=dict)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    ten_gods: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    branch_relations: Dict[str, Any] = field(default_factory=dict)
    deities: Dict[str, List[str]] = field(default_factory=dict)
    xi_ji_elements: Dict[str, List[str]] = field(default_factory=dict)
    dayun_sequence: List[Dict[str, Any]] = field(default_factory=list)
    special_liunians: List[Dict[str, Any]] = field(default_factory=list)
    matched_bazi_rules: List[Dict[str, Any]] = field(default_factory=list)

    def get_spouse_star_type(self) -> str:
        """根据性别确定配偶星类型：男看财星，女看官杀"""
        if self.gender == 'male':
            return '财'
        return '官杀'

    def get_all_branches(self) -> List[str]:
        """获取四柱所有地支"""
        branches = []
        for pillar in ['year', 'month', 'day', 'hour']:
            p = self.bazi_pillars.get(pillar, {})
            if p.get('branch'):
                branches.append(p['branch'])
        return branches


@dataclass
class CausalChain:
    """
    因果推理链条——推理引擎的核心输出单元。
    
    每条链条表示一个完整的推理过程：
    条件（命局中观察到什么）→ 机制（命理原理是什么）→ 结论（推导出什么）
    """
    category: str = ''
    condition: str = ''
    mechanism: str = ''
    conclusion: str = ''
    time_range: str = ''
    confidence: float = 0.8
    source: str = ''
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """推理引擎输出结果，包含多条因果链条"""
    domain: str = ''
    chains: List[CausalChain] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_chains_by_category(self, category: str) -> List[CausalChain]:
        return [c for c in self.chains if c.category == category]

    def has_conclusions(self) -> bool:
        return len(self.chains) > 0

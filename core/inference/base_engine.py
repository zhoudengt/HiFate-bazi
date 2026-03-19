#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理引擎抽象基类

所有领域推理引擎（婚姻/健康/事业/财富等）继承此基类。
提供：规则加载、适配器接口、降级保护、单例管理。
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from core.inference.models import InferenceInput, InferenceResult, CausalChain

logger = logging.getLogger(__name__)


class BaseInferenceEngine(ABC):
    """
    推理引擎抽象基类。
    
    子类只需实现:
    - domain 属性
    - _run_inference() 方法
    
    基类提供:
    - 单例管理 (get_instance)
    - 适配器 (build_input) 将各种格式的原始数据映射为 InferenceInput
    - 安全推理 (infer) 带 try/except 降级保护
    - 规则加载 (load_rules)
    """

    _instances: Dict[str, 'BaseInferenceEngine'] = {}

    @property
    @abstractmethod
    def domain(self) -> str:
        """领域标识，如 'marriage', 'health', 'career'"""
        ...

    @classmethod
    def get_instance(cls) -> 'BaseInferenceEngine':
        key = cls.__name__
        if key not in cls._instances:
            cls._instances[key] = cls()
        return cls._instances[key]

    @classmethod
    def reset_instance(cls):
        key = cls.__name__
        cls._instances.pop(key, None)

    def __init__(self):
        self._rules: List[Dict[str, Any]] = []
        self._rules_loaded = False

    def load_rules(self) -> List[Dict[str, Any]]:
        if self._rules_loaded:
            return self._rules
        try:
            from core.inference.rule_loader import InferenceRuleLoader
            self._rules = InferenceRuleLoader.load_rules(self.domain)
            self._rules_loaded = True
            logger.info(f"推理引擎 [{self.domain}] 加载 {len(self._rules)} 条规则")
        except Exception as e:
            logger.warning(f"推理引擎 [{self.domain}] 加载规则失败: {e}")
            self._rules = []
        return self._rules

    def reload_rules(self):
        self._rules_loaded = False
        self._rules = []
        return self.load_rules()

    def get_rules_by_category(self, category: str) -> List[Dict[str, Any]]:
        if not self._rules_loaded:
            self.load_rules()
        return [r for r in self._rules if r.get('category') == category]

    def build_input(
        self,
        bazi_data: Dict[str, Any],
        wangshuai_result: Dict[str, Any],
        detail_result: Dict[str, Any],
        gender: str,
        matched_rules: Optional[List[Dict[str, Any]]] = None
    ) -> InferenceInput:
        """
        适配器：将各种原始数据格式映射为 InferenceInput。
        
        如果 WangShuaiAnalyzer 输出格式变化，只需修改此方法。
        matched_rules: 编排器已匹配的 bazi_rules 规则结果列表
        """
        ws_data = wangshuai_result
        if isinstance(ws_data, dict) and ws_data.get('success') and 'data' in ws_data:
            ws_data = ws_data['data']

        bazi_pillars = bazi_data.get('bazi_pillars', {})
        pillars = {}
        for p_name in ['year', 'month', 'day', 'hour']:
            pv = bazi_pillars.get(p_name)
            if isinstance(pv, str) and len(pv) == 2:
                pillars[p_name] = {'stem': pv[0], 'branch': pv[1]}
            elif isinstance(pv, dict):
                pillars[p_name] = pv
            else:
                pillars[p_name] = {}

        ten_gods = {}
        for src in [detail_result, bazi_data]:
            tg = src.get('ten_gods', {})
            if tg and isinstance(tg, dict) and len(tg) > 0:
                ten_gods = tg
                break
            details = src.get('details', {})
            if details:
                for pn in ['year', 'month', 'day', 'hour']:
                    pd = details.get(pn, {})
                    if isinstance(pd, dict) and pd.get('main_star'):
                        ten_gods[pn] = {
                            'main_star': pd.get('main_star', ''),
                            'hidden_stars': pd.get('hidden_stars', []),
                            'hidden_stems': pd.get('hidden_stems', []),
                        }
                if ten_gods:
                    break

        # 补充 hidden_stems：如果 ten_gods 来自 data_assembler 缺少此字段，从 details 中取
        all_details = detail_result.get('details', {}) or bazi_data.get('details', {})
        if all_details:
            for pn in ['year', 'month', 'day', 'hour']:
                tg_pn = ten_gods.get(pn)
                if isinstance(tg_pn, dict) and 'hidden_stems' not in tg_pn:
                    pd = all_details.get(pn, {})
                    tg_pn['hidden_stems'] = pd.get('hidden_stems', [])

        deities = {}
        details = bazi_data.get('details', {})
        for pn in ['year', 'month', 'day', 'hour']:
            pd = details.get(pn, {})
            d = pd.get('deities', [])
            if d:
                deities[pn] = d

        branch_relations = bazi_data.get('relationships', {}).get('branch_relations', {})

        xi_ji_elements = ws_data.get('xi_ji_elements', {})
        if not xi_ji_elements:
            final = ws_data.get('final_xi_ji', {})
            if final:
                xi_ji_elements = {
                    'xi_shen': final.get('xi_shen_elements', []),
                    'ji_shen': final.get('ji_shen_elements', [])
                }

        element_counts = bazi_data.get('element_counts', {})
        if not element_counts:
            element_counts = bazi_data.get('elements', {})
        wuxing_power = {}
        for elem in ['木', '火', '土', '金', '水']:
            wuxing_power[elem] = float(element_counts.get(elem, 0))

        day_pillar = pillars.get('day', {})
        dayun_seq = detail_result.get('dayun_sequence', [])

        return InferenceInput(
            day_stem=day_pillar.get('stem', ''),
            day_branch=day_pillar.get('branch', ''),
            gender=gender,
            bazi_pillars=pillars,
            wangshuai=ws_data.get('wangshuai', ''),
            wuxing_power=wuxing_power,
            score_breakdown=ws_data.get('score_breakdown', {}),
            ten_gods=ten_gods,
            branch_relations=branch_relations,
            deities=deities,
            xi_ji_elements=xi_ji_elements,
            dayun_sequence=dayun_seq,
            special_liunians=[],
            matched_bazi_rules=matched_rules or [],
        )

    def infer(self, inp: InferenceInput) -> InferenceResult:
        """安全推理入口，带降级保护"""
        try:
            if not self._rules_loaded:
                self.load_rules()
            return self._run_inference(inp)
        except Exception as e:
            logger.warning(f"推理引擎 [{self.domain}] 推理失败: {e}", exc_info=True)
            return InferenceResult(domain=self.domain)

    @abstractmethod
    def _run_inference(self, inp: InferenceInput) -> InferenceResult:
        """子类实现：执行具体的推理逻辑"""
        ...

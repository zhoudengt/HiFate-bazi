#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理结论质量过滤器（通用，所有领域共享）

四层过滤流水线：
1. 置信度门槛：低于阈值的结论降级或丢弃
2. 矛盾检测：互相冲突的结论只保留高置信度方
3. 增强去重：同类别下语义相似的结论只保留最优
4. 分类限数：每个类别保留 Top-N 条

设计原则：
- 每层过滤独立、可配置
- 领域特有的矛盾规则通过配置注入，无需改框架
"""

from __future__ import annotations
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field

from core.inference.models import CausalChain

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """过滤器配置"""
    confidence_threshold: float = 0.5
    category_top_n: int = 8
    dedup_prefix_len: int = 15
    category_limits: Dict[str, int] = field(default_factory=dict)
    contradiction_pairs: List[Tuple[str, str]] = field(default_factory=list)


# ═══ 默认矛盾对（婚姻领域）═══════════════════════════

MARRIAGE_CONTRADICTIONS: List[Tuple[str, str]] = [
    ('婚姻稳固', '婚姻不稳'),
    ('感情专一', '感情不专'),
    ('配偶忠诚', '配偶不忠'),
    ('利于婚恋', '不利婚恋'),
    ('婚姻宫安稳', '婚姻宫不安稳'),
    ('配偶可靠', '配偶不可靠'),
    ('早婚', '晚婚'),
    ('婚姻根基稳固', '婚姻根基不稳'),
]


class InferenceQualityFilter:
    """
    推理结论质量过滤器。

    用法：
        config = FilterConfig(confidence_threshold=0.5, category_top_n=6)
        filtered = InferenceQualityFilter.apply(chains, config)
    """

    @classmethod
    def apply(cls, chains: List[CausalChain], config: Optional[FilterConfig] = None) -> List[CausalChain]:
        if config is None:
            config = FilterConfig()

        original_count = len(chains)
        result = chains

        result = cls._filter_confidence(result, config.confidence_threshold)
        result = cls._detect_contradictions(result, config.contradiction_pairs)
        result = cls._deduplicate(result, config.dedup_prefix_len)
        result = cls._limit_by_category(result, config.category_top_n, config.category_limits)

        logger.info(
            f"质量过滤: {original_count} → {len(result)} 条 "
            f"(门槛={config.confidence_threshold}, Top-N={config.category_top_n})"
        )
        return result

    @staticmethod
    def _filter_confidence(chains: List[CausalChain], threshold: float) -> List[CausalChain]:
        return [c for c in chains if c.confidence >= threshold]

    @classmethod
    def _detect_contradictions(
        cls,
        chains: List[CausalChain],
        extra_pairs: List[Tuple[str, str]],
    ) -> List[CausalChain]:
        pairs = list(MARRIAGE_CONTRADICTIONS) + list(extra_pairs)
        if not pairs:
            return chains

        to_remove: Set[int] = set()
        for i in range(len(chains)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(chains)):
                if j in to_remove:
                    continue
                if chains[i].category != chains[j].category:
                    continue
                ci_text = chains[i].conclusion
                cj_text = chains[j].conclusion
                for pos_kw, neg_kw in pairs:
                    i_has_pos = pos_kw in ci_text
                    i_has_neg = neg_kw in ci_text
                    j_has_pos = pos_kw in cj_text
                    j_has_neg = neg_kw in cj_text

                    if (i_has_pos and j_has_neg) or (i_has_neg and j_has_pos):
                        loser = i if chains[i].confidence < chains[j].confidence else j
                        to_remove.add(loser)
                        logger.debug(
                            f"矛盾检测: 移除低置信度结论 [{chains[loser].category}] "
                            f"'{chains[loser].conclusion[:30]}...'"
                        )
                        break

        return [c for idx, c in enumerate(chains) if idx not in to_remove]

    @staticmethod
    def _deduplicate(chains: List[CausalChain], prefix_len: int) -> List[CausalChain]:
        seen: Dict[str, CausalChain] = {}
        for chain in chains:
            conclusion_core = chain.conclusion[:prefix_len] if chain.conclusion else ''
            dedup_key = f"{chain.category}::{conclusion_core}"
            existing = seen.get(dedup_key)
            if existing is None or chain.confidence > existing.confidence:
                seen[dedup_key] = chain
        return list(seen.values())

    @staticmethod
    def _limit_by_category(
        chains: List[CausalChain],
        default_top_n: int,
        category_limits: Dict[str, int],
    ) -> List[CausalChain]:
        by_cat: Dict[str, List[CausalChain]] = {}
        for c in chains:
            by_cat.setdefault(c.category, []).append(c)

        result = []
        for cat, cat_chains in by_cat.items():
            limit = category_limits.get(cat, default_top_n)
            sorted_chains = sorted(cat_chains, key=lambda x: x.confidence, reverse=True)
            result.extend(sorted_chains[:limit])

        return result

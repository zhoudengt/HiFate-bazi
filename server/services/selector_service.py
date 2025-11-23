#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精选选择器服务（不改变现有匹配逻辑，仅作为可选后处理）
功能：
- 评分：基于可选元数据与简单启发式（字段不存在时安全回退）
- 冲突消解：互斥组与显式矛盾ID
- 多样化：按 tags 控制冗余，确保覆盖
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import math
import itertools
from collections import Counter, defaultdict


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _calc_match_strength(rule: Dict[str, Any]) -> float:
    """
    将匹配强度枚举映射为分数；若不存在则给中性值
    """
    mapping = {"exact": 1.0, "strong": 0.8, "medium": 0.6, "weak": 0.3}
    level = rule.get("match_strength")
    if isinstance(level, str):
        return mapping.get(level.lower(), 0.5)
    return 0.5


def _segment_weight_for_user(rule: Dict[str, Any], user_profile: Dict[str, Any]) -> float:
    """
    基于简单画像字段（性别 gender）取权重；字段缺失则返回中性值
    """
    seg = rule.get("segment_weights") or {}
    gender = (user_profile or {}).get("gender")
    if isinstance(seg, dict) and gender in seg:
        return _safe_float(seg.get(gender), 0.5)
    return 0.5


def _history_score(rule: Dict[str, Any]) -> float:
    """
    历史效果分：若无统计，回退中性值
    可后续由数据库回填 CTR/好评率经贝叶斯平滑后的值
    """
    hist = rule.get("history_score")
    return _safe_float(hist, 0.5)


def _biz_weight(rule: Dict[str, Any]) -> float:
    return _safe_float(rule.get("biz_impact_weight"), 1.0)


def score_rule(rule: Dict[str, Any], user_profile: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> float:
    """
    安全的多因子评分；字段缺失不会报错
    """
    w = {
        "match": 0.35,
        "prior": 0.25,
        "segment": 0.15,
        "history": 0.15,
        "biz": 0.10,
    }
    if isinstance(weights, dict):
        w.update(weights)

    prior = _safe_float(rule.get("confidence_prior"), 0.6)
    match_strength = _calc_match_strength(rule)
    segment = _segment_weight_for_user(rule, user_profile)
    history = _history_score(rule)
    biz = _biz_weight(rule)

    score = (
        w["match"] * match_strength
        + w["prior"] * prior
        + w["segment"] * segment
        + w["history"] * history
        + w["biz"] * biz
    )
    return float(score)


def _is_conflicting(candidate: Dict[str, Any], selected: List[Dict[str, Any]]) -> bool:
    """
    冲突条件：
    - mutually_exclusive_group 相同
    - 显式 contradicts 列表交叉
    字段缺失则不判冲
    """
    group = candidate.get("mutually_exclusive_group")
    contradicts: Set[str] = set(candidate.get("contradicts") or [])
    cand_id = candidate.get("rule_id") or candidate.get("rule_code")

    used_groups: Set[Any] = set()
    selected_ids: Set[str] = set()
    for r in selected:
        if r.get("mutually_exclusive_group"):
            used_groups.add(r.get("mutually_exclusive_group"))
        rid = r.get("rule_id") or r.get("rule_code")
        if rid:
            selected_ids.add(str(rid))
        rc = r.get("contradicts") or []
        for x in rc:
            selected_ids.add(str(x))

    if group and group in used_groups:
        return True
    if contradicts and any(str(x) in selected_ids for x in contradicts):
        return True
    # 对称考虑：若已选里声明与我冲突
    my_id = str(cand_id) if cand_id is not None else None
    if my_id:
        for r in selected:
            rc = r.get("contradicts") or []
            if my_id in [str(x) for x in rc]:
                return True
    return False


def _tags(rule: Dict[str, Any]) -> List[str]:
    tags = rule.get("tags")
    if isinstance(tags, list):
        return [str(t) for t in tags]
    if isinstance(tags, str) and tags:
        return [tags]
    return []


def select_curated(
    candidates: List[Dict[str, Any]],
    user_profile: Optional[Dict[str, Any]] = None,
    k: int = 8,
    min_per_tag: Optional[Dict[str, int]] = None,
    max_per_tag: Optional[Dict[str, int]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    从候选规则中精选 Top-K（去冲突+多样化）。缺字段时安全退化为简单高分选择。
    """
    user_profile = user_profile or {}
    # 计算分数（不修改原对象）
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for r in candidates or []:
        s = score_rule(r, user_profile, weights)
        rr = dict(r)
        rr["_score"] = s
        scored.append((s, rr))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected: List[Dict[str, Any]] = []
    by_tag_count: Counter = Counter()

    # 快速贪心选择（带冲突与配额）
    for _, rule in scored:
        if len(selected) >= k:
            break
        if _is_conflicting(rule, selected):
            continue
        # tag上限
        if max_per_tag:
            rule_tags = _tags(rule)
            exceeded = False
            for t in rule_tags:
                cap = max_per_tag.get(t)
                if cap is not None and by_tag_count.get(t, 0) >= cap:
                    exceeded = True
                    break
            if exceeded:
                continue
        selected.append(rule)
        for t in _tags(rule):
            by_tag_count[t] += 1

    # 补齐下限（宽松补位，不打破冲突约束）
    if min_per_tag:
        for tag, need in min_per_tag.items():
            while by_tag_count.get(tag, 0) < need:
                # 找一个未选且带该tag且不冲突的最高分
                for s, rule in scored:
                    if rule in selected:
                        continue
                    if tag not in _tags(rule):
                        continue
                    if _is_conflicting(rule, selected):
                        continue
                    selected.append(rule)
                    for t in _tags(rule):
                        by_tag_count[t] += 1
                    break
                else:
                    # 找不到可补位则跳过
                    break

    return selected[:k]



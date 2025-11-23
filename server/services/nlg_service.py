#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLG 输出服务（最小可用实现）
- 模板化拼装（简化版）：将精选规则按分组和顺序组织为易读文本
- 文本安全与风格：基础禁语/绝对化词弱化
注意：该模块可选调用，不改变原有逻辑
"""
from typing import List, Dict, Any
import re


ABSOLUTE_WORDS = [
    "必然", "一定", "注定", "绝对", "毫无疑问", "百分之百", "铁定", "唯一结论"
]


def _soften_absolute_words(text: str) -> str:
    """
    将绝对化词替换为更温和表达
    """
    softened = text
    replacements = {
        "必然": "更可能",
        "一定": "大概率",
        "注定": "多有倾向",
        "绝对": "较为明确",
        "毫无疑问": "总体判断较为明确",
        "百分之百": "很大概率",
        "铁定": "大体上看",
        "唯一结论": "较为可靠的判断"
    }
    for k, v in replacements.items():
        softened = softened.replace(k, v)
    return softened


def _sanitize(text: str) -> str:
    """
    文本安全与简单清洗
    """
    text = text or ""
    text = _soften_absolute_words(text)
    # 去除多余空白
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def render_curated_as_text(curated_rules: List[Dict[str, Any]]) -> str:
    """
    将精选规则按主题拼成易读文本；若无标签则按序罗列
    """
    if not curated_rules:
        return ""

    # 组装段落
    parts: List[str] = []
    # 优先按 tags 简单分组
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in curated_rules:
        tags = r.get("tags") or ["综合"]
        if isinstance(tags, str):
            tags = [tags]
        for t in tags:
            grouped.setdefault(str(t), []).append(r)

    for tag, rules in grouped.items():
        parts.append(f"【{tag}】")
        for idx, r in enumerate(rules, 1):
            # content 兼容多格式
            content = r.get("content") or {}
            line = ""
            if isinstance(content, dict):
                line = content.get("text") or content.get("description") or str(content)
            elif isinstance(content, str):
                line = content
            else:
                line = str(content)
            # 回退：若文本为空，尝试 title
            if not line:
                line = r.get("title") or ""
            # 兜底
            if not line:
                rid = r.get("rule_code") or r.get("rule_id") or "规则"
                line = f"{rid}"
            parts.append(f"{idx}. {line}")
        parts.append("")  # 空行分隔

    text = "\n".join(parts)
    return _sanitize(text)



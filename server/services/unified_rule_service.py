#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一规则服务 - 向后兼容硬编码和数据库两种来源。
优先从数据库加载，无数据时降级到硬编码（迁移期间）。
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 表名
FORTUNE_RULES_TABLE = "fortune_rules"


def _load_from_database(rule_type: str) -> Dict[str, Any]:
    """从数据库加载规则。返回 {} 表示无数据或失败。"""
    try:
        from server.db.mysql_connector import MySQLConnector
        db = MySQLConnector()
        rows = db.execute_query(
            "SELECT category, content FROM {} WHERE rule_type = %s AND enabled = 1".format(
                FORTUNE_RULES_TABLE
            ),
            (rule_type,),
        )
        if not rows:
            return {}
        result = {}
        for row in rows:
            category = row.get("category")
            content = row.get("content")
            if category is not None:
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        content = {}
                result[category] = content or {}
        return result
    except Exception as e:
        logger.warning("UnifiedRuleService: load from db failed for %s: %s", rule_type, e)
        return {}


def _load_from_hardcode(rule_type: str) -> Dict[str, Any]:
    """从硬编码加载规则（降级）。"""
    try:
        if rule_type == "hand":
            from services.fortune_rule.rule_engine import get_hand_rules_static
            return get_hand_rules_static()
        if rule_type == "face":
            from services.fortune_rule.rule_engine import get_face_rules_static
            return get_face_rules_static()
    except Exception as e:
        logger.warning("UnifiedRuleService: hardcode fallback failed for %s: %s", rule_type, e)
    return {}


class UnifiedRuleService:
    """统一规则服务 - 向后兼容硬编码和数据库两种来源。"""

    @staticmethod
    def get_rules(rule_type: str, category: str = None) -> Any:
        """
        获取规则。rule_type 为 'hand' 或 'face'。
        category 可选；不传时返回该类型的完整字典（与 FortuneRuleEngine 一致）。
        """
        db_rules = _load_from_database(rule_type)
        if db_rules:
            if category is not None:
                return db_rules.get(category, {})
            return db_rules
        hardcode_rules = _load_from_hardcode(rule_type)
        if category is not None:
            return hardcode_rules.get(category, {}) if isinstance(hardcode_rules, dict) else {}
        return hardcode_rules

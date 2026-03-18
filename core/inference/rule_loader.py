#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理规则 MySQL 加载器

按 domain 从 inference_rules 表加载规则，支持缓存和热更新。
所有领域共用此加载器。
"""

from __future__ import annotations
import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

_cache: Dict[str, List[Dict[str, Any]]] = {}
_cache_ts: Dict[str, float] = {}
_CACHE_TTL = 300  # 5 分钟缓存


class InferenceRuleLoader:
    """推理规则加载器（静态方法，无状态）"""

    @staticmethod
    def load_rules(domain: str, force_reload: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        if not force_reload and domain in _cache:
            if now - _cache_ts.get(domain, 0) < _CACHE_TTL:
                return _cache[domain]

        rules = InferenceRuleLoader._load_from_db(domain)
        _cache[domain] = rules
        _cache_ts[domain] = now
        return rules

    @staticmethod
    def _load_from_db(domain: str) -> List[Dict[str, Any]]:
        try:
            from server.db.mysql_connector import get_db_connection
            import json as _json

            db = get_db_connection()
            rows = db.execute_query(
                "SELECT * FROM bazi_stream_inference_rules WHERE domain = %s AND enabled = 1 ORDER BY priority DESC",
                (domain,)
            )
            if not rows:
                logger.info(f"bazi_stream_inference_rules 表中无 domain={domain} 的启用规则")
                return []

            rules = []
            for row in rows:
                conditions = row.get('conditions', '{}')
                conclusions = row.get('conclusions', '{}')
                if isinstance(conditions, str):
                    conditions = _json.loads(conditions)
                if isinstance(conclusions, str):
                    conclusions = _json.loads(conclusions)
                rules.append({
                    'rule_code': row['rule_code'],
                    'domain': row['domain'],
                    'category': row['category'],
                    'rule_name': row['rule_name'],
                    'conditions': conditions,
                    'conclusions': conclusions,
                    'priority': row.get('priority', 100),
                    'source': row.get('source', ''),
                    'description': row.get('description', ''),
                })
            logger.info(f"从 MySQL 加载 {len(rules)} 条推理规则 (domain={domain})")
            return rules
        except Exception as e:
            logger.warning(f"从 MySQL 加载推理规则失败 (domain={domain}): {e}")
            return []

    @staticmethod
    def reload_all():
        _cache.clear()
        _cache_ts.clear()
        logger.info("推理规则缓存已清空")

    @staticmethod
    def reload_domain(domain: str):
        _cache.pop(domain, None)
        _cache_ts.pop(domain, None)
        logger.info(f"推理规则缓存已清空 (domain={domain})")

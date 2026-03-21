#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务缓存模式常量

热更新 CacheReloader 与部署脚本 gate_clear_business_cache 应使用一致的 Redis 清理模式。
任一新增业务缓存 key 前缀，需同步到此列表，避免热更新后旧缓存残留导致数据不一致。

参考：gate_check.sh gate_clear_business_cache 中的 for p in "bazi*" ...
"""

# Redis 业务缓存 key 模式（用于 SCAN + DEL 清理）
# 部署脚本 gate_clear_business_cache 使用更宽泛的 bazi* fortune* 等；热更新需覆盖所有细分模式
REDIS_BUSINESS_CACHE_PATTERNS = [
    # BaziService（24h TTL，热更新此前遗漏导致腐化）
    "bazi_full:*",
    # BaziInterfaceService
    "bazi_interface:*",
    # BaziDetailService
    "bazi_detail:*",
    # BaziDataOrchestrator / BaziDataService
    "bazi_data:*",
    # BaziCacheService
    "bazi:base:*",
    "bazi:dayun:*",
    "bazi:full:*",
    "bazi:ready:*",
    # BaziDisplayService
    "fortune_display:*",
    # 特殊流年
    "special_liunians:*",
    # API 层缓存
    "pan:*",
    "wangshuai:*",
    "xishen:*",
    "formula:*",
    "rizhu:*",
    "dailycalendar:*",
    "wannianli:*",
    # LLM 结果缓存
    "llm_*",
    "llm_xishen*",
    "llm_wuxing*",
    # 其他业务
    "desk_fengshui_rules*",
    "cache:*",
    "daily_fortune:service:*",
    "daily_fortune:action:*",
]


def get_redis_clear_patterns() -> list:
    """
    获取 Redis 清理模式列表。
    当 ENABLE_CACHE_VERSION 启用时，需同时匹配带版本前缀的 key（如 v1:bazi_full:*）。
    """
    from server.utils.cache_multi_level import _is_cache_version_enabled

    patterns = list(REDIS_BUSINESS_CACHE_PATTERNS)
    if _is_cache_version_enabled():
        patterns.extend(f"v*:{p}" for p in REDIS_BUSINESS_CACHE_PATTERNS)
    return patterns

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理 Admin API

用于手动排查和清理缓存，无需重启或重新部署。
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/admin/cache/clear", summary="清理所有业务缓存")
async def cache_clear() -> Dict[str, Any]:
    """
    清理 L1 内存缓存 + Redis 业务缓存。
    与热更新 CacheReloader 使用相同的模式列表。
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        cache.clear()

        total_deleted = 0
        try:
            from shared.config.redis import get_redis_client
            from server.utils.cache_patterns import get_redis_clear_patterns

            redis_client = get_redis_client()
            if redis_client:
                for pattern in get_redis_clear_patterns():
                    cursor = 0
                    while True:
                        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            redis_client.delete(*keys)
                            total_deleted += len(keys)
                        if cursor == 0:
                            break
        except Exception as e:
            logger.warning(f"Redis 清理失败: {e}")

        return {"success": True, "message": "缓存已清理", "redis_deleted": total_deleted}
    except Exception as e:
        logger.exception("缓存清理失败")
        return {"success": False, "error": str(e)}


@router.post("/admin/cache/bump-version", summary="增加缓存版本号")
async def cache_bump_version() -> Dict[str, Any]:
    """
    增加缓存版本号，使所有旧缓存自动失效。
    需 ENABLE_CACHE_VERSION=true 时生效。
    """
    try:
        from server.utils.cache_multi_level import bump_cache_version, _is_cache_version_enabled

        if not _is_cache_version_enabled():
            return {
                "success": False,
                "error": "ENABLE_CACHE_VERSION 未启用，请设置环境变量为 true",
                "version": "none",
            }

        ver = bump_cache_version()
        return {"success": True, "version": ver, "message": f"缓存版本已更新为 {ver}"}
    except Exception as e:
        logger.exception("bump_version 失败")
        return {"success": False, "error": str(e)}


@router.get("/admin/cache/stats", summary="缓存统计")
async def cache_stats() -> Dict[str, Any]:
    """查看缓存命中率、版本号等"""
    try:
        from server.utils.cache_multi_level import (
            get_multi_cache,
            _is_cache_version_enabled,
            _get_cache_version,
        )

        cache = get_multi_cache()
        stats = cache.stats()

        version_enabled = _is_cache_version_enabled()
        version = "none"
        if version_enabled:
            try:
                from shared.config.redis import get_redis_client
                version = _get_cache_version(get_redis_client())
            except Exception:
                version = "unknown"

        return {
            "success": True,
            "cache_version_enabled": version_enabled,
            "cache_version": version,
            "stats": stats,
        }
    except Exception as e:
        logger.exception("获取缓存统计失败")
        return {"success": False, "error": str(e)}

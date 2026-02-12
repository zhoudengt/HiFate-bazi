#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 全局 conftest —— 共享 fixtures
"""

import os
import sys
import json
import time
import asyncio
import tempfile
import threading
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# 确保项目根目录在 sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# ──────────────────── Redis Mock ────────────────────



# ──────────────────── 排除不兼容 pytest 的独立脚本 ────────────────────
# 这些文件使用 argparse / 自定义参数，不是标准 pytest 测试

collect_ignore_glob = [
    # 独立脚本（含 sys.exit / argparse / 非 fixture 参数）
    "test_optimization_*.py",
    "e2e_*_test.py",
]

@pytest.fixture
def mock_redis():
    """Mock Redis 客户端（模拟 get/setex/delete/scan/info）"""
    redis = MagicMock()
    _store = {}

    def _get(key):
        item = _store.get(key)
        if item is None:
            return None
        val, expire = item
        if expire and time.time() > expire:
            del _store[key]
            return None
        return json.dumps(val, ensure_ascii=False)

    def _setex(key, ttl, data):
        _store[key] = (json.loads(data), time.time() + ttl)
        return True

    def _delete(*keys):
        count = 0
        for k in keys:
            if k in _store:
                del _store[k]
                count += 1
        return count

    def _scan(cursor, match="*", count=100):
        import fnmatch
        matched = [k for k in _store if fnmatch.fnmatch(k, match)]
        return (0, matched)

    def _info():
        return {"used_memory_human": "1M", "connected_clients": 1, "db0": {}}

    redis.get = MagicMock(side_effect=_get)
    redis.setex = MagicMock(side_effect=_setex)
    redis.delete = MagicMock(side_effect=_delete)
    redis.scan = MagicMock(side_effect=_scan)
    redis.info = MagicMock(side_effect=_info)
    redis._store = _store  # 暴露给测试方便检查
    return redis


# ──────────────────── Cache Fixtures ────────────────────


@pytest.fixture
def l1_cache():
    """新建一个小容量的 L1MemoryCache（测试专用）"""
    from server.utils.cache_multi_level import L1MemoryCache
    return L1MemoryCache(max_size=100, ttl=5)


@pytest.fixture
def multi_cache(mock_redis):
    """创建带 mock Redis 的 MultiLevelCache"""
    from server.utils.cache_multi_level import MultiLevelCache
    return MultiLevelCache(
        l1_max_size=100,
        l1_ttl=5,
        redis_client=mock_redis,
        redis_ttl=60,
    )


# ──────────────────── Sample Bazi Data ────────────────────


@pytest.fixture
def sample_bazi_params():
    """标准八字测试参数"""
    return {
        "solar_date": "1992-01-15",
        "solar_time": "12:00",
        "gender": "male",
    }


@pytest.fixture
def sample_bazi_result():
    """模拟的八字排盘返回结果"""
    return {
        "year_pillar": {"stem": "辛", "branch": "未"},
        "month_pillar": {"stem": "辛", "branch": "丑"},
        "day_pillar": {"stem": "丁", "branch": "酉"},
        "hour_pillar": {"stem": "丙", "branch": "午"},
        "five_elements": {"金": 3, "木": 0, "水": 0, "火": 2, "土": 3},
    }

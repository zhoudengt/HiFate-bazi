#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_cache_multi_level.py
L1MemoryCache / L2RedisCache / MultiLevelCache 单元测试
"""

import time
import json
import threading
import pytest
from unittest.mock import MagicMock


# ════════════════════ L1MemoryCache ════════════════════


class TestL1MemoryCache:

    def test_set_and_get(self, l1_cache):
        l1_cache.set("k1", {"a": 1})
        assert l1_cache.get("k1") == {"a": 1}

    def test_get_miss_returns_none(self, l1_cache):
        assert l1_cache.get("nonexist") is None

    def test_ttl_expiry(self):
        """TTL 过期后应返回 None（含 0-10% 随机偏移）"""
        from server.utils.cache_multi_level import L1MemoryCache
        # TTL=1, jitter = randint(0, max(1, int(1*0.1))) = randint(0,1) → 最大有效 TTL=2s
        cache = L1MemoryCache(max_size=10, ttl=1)
        cache.set("k", "v")
        assert cache.get("k") == "v"
        time.sleep(2.5)  # 等待超过 max(TTL+jitter) = 2s
        assert cache.get("k") is None

    def test_custom_ttl_per_key(self):
        """单条 set 指定 TTL 优先于实例默认"""
        from server.utils.cache_multi_level import L1MemoryCache
        # 使用独立实例，避免 fixture 默认 TTL 干扰
        # TTL=2, jitter = randint(0, max(1, int(2*0.1))) = randint(0,1) → 最大 3s
        cache = L1MemoryCache(max_size=10, ttl=300)
        cache.set("short", "val", ttl=2)
        assert cache.get("short") == "val"
        time.sleep(3.5)
        assert cache.get("short") is None

    def test_max_size_eviction(self):
        from server.utils.cache_multi_level import L1MemoryCache
        cache = L1MemoryCache(max_size=3, ttl=300)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_clear(self, l1_cache):
        l1_cache.set("x", 1)
        l1_cache.set("y", 2)
        l1_cache.clear()
        assert l1_cache.get("x") is None
        assert l1_cache.get("y") is None

    def test_stats(self, l1_cache):
        l1_cache.get("miss1")
        l1_cache.set("hit1", 100)
        l1_cache.get("hit1")
        stats = l1_cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0
        assert stats["size"] == 1

    def test_thread_safety(self, l1_cache):
        errors = []
        def writer(cache, start):
            try:
                for i in range(100):
                    cache.set(f"key_{start + i}", i)
            except Exception as e:
                errors.append(e)
        def reader(cache):
            try:
                for i in range(100):
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)
        threads = [
            threading.Thread(target=writer, args=(l1_cache, 0)),
            threading.Thread(target=writer, args=(l1_cache, 100)),
            threading.Thread(target=reader, args=(l1_cache,)),
            threading.Thread(target=reader, args=(l1_cache,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert errors == []


# ════════════════════ L2RedisCache ════════════════════


class TestL2RedisCache:

    def test_unavailable_returns_none(self):
        from server.utils.cache_multi_level import L2RedisCache
        cache = L2RedisCache(redis_client=None)
        assert cache.get("any_key") is None

    def test_set_and_get(self, mock_redis):
        from server.utils.cache_multi_level import L2RedisCache
        cache = L2RedisCache(redis_client=mock_redis, ttl=60)
        cache.set("k1", {"foo": "bar"})
        result = cache.get("k1")
        assert result == {"foo": "bar"}

    def test_delete(self, mock_redis):
        from server.utils.cache_multi_level import L2RedisCache
        cache = L2RedisCache(redis_client=mock_redis, ttl=60)
        cache.set("k1", "val")
        cache.delete("k1")
        assert cache.get("k1") is None

    def test_stats_unavailable(self):
        from server.utils.cache_multi_level import L2RedisCache
        cache = L2RedisCache(redis_client=None)
        assert cache.stats()["status"] == "unavailable"

    def test_stats_available(self, mock_redis):
        from server.utils.cache_multi_level import L2RedisCache
        cache = L2RedisCache(redis_client=mock_redis, ttl=60)
        cache.get("miss")
        cache.set("hit", 1)
        cache.get("hit")
        stats = cache.stats()
        assert stats["status"] == "available"
        assert stats["hits"] == 1
        assert stats["misses"] == 1


# ════════════════════ MultiLevelCache ════════════════════


class TestMultiLevelCache:

    def test_set_populates_both_levels(self, multi_cache, mock_redis):
        multi_cache.set("k", "v")
        assert multi_cache.l1.get("k") == "v"
        mock_redis.setex.assert_called()

    def test_get_l1_hit(self, multi_cache):
        multi_cache.l1.set("k", "v")
        assert multi_cache.get("k") == "v"

    def test_get_l2_backfill_l1(self, multi_cache, mock_redis):
        mock_redis._store["k2"] = ({"x": 1}, time.time() + 600)
        result = multi_cache.get("k2")
        assert result == {"x": 1}
        assert multi_cache.l1.get("k2") == {"x": 1}

    def test_set_null_prevents_penetration(self, multi_cache):
        multi_cache.set_null("empty_key")
        assert multi_cache.get("empty_key") is None
        raw = multi_cache.l1.get("empty_key")
        assert raw == multi_cache.NULL_VALUE

    def test_delete(self, multi_cache, mock_redis):
        multi_cache.set("to_del", 123)
        multi_cache.delete("to_del")
        assert multi_cache.get("to_del") is None

    def test_clear(self, multi_cache):
        multi_cache.set("a", 1)
        multi_cache.set("b", 2)
        multi_cache.clear()
        assert multi_cache.l1.get("a") is None

    def test_invalidate_pattern(self, multi_cache, mock_redis):
        multi_cache.l1.set("bazi:1992:m", "x")
        multi_cache.l1.set("bazi:1993:f", "y")
        multi_cache.l1.set("other:key", "z")
        multi_cache.invalidate_pattern("bazi:*")
        assert multi_cache.l1.get("bazi:1992:m") is None
        assert multi_cache.l1.get("bazi:1993:f") is None
        assert multi_cache.l1.get("other:key") == "z"

    def test_generate_key_deterministic(self, multi_cache):
        k1 = multi_cache._generate_key("1992-01-15", "12:00", "male")
        k2 = multi_cache._generate_key("1992-01-15", "12:00", "male")
        assert k1 == k2

    def test_generate_key_unique(self, multi_cache):
        k1 = multi_cache._generate_key("1992-01-15", "12:00", "male")
        k2 = multi_cache._generate_key("1992-01-15", "12:00", "female")
        assert k1 != k2

    def test_set_with_custom_ttl(self, multi_cache, mock_redis):
        multi_cache.set("custom_ttl", "val", ttl=120)
        assert multi_cache.l1.get("custom_ttl") == "val"
        mock_redis.setex.assert_called()

    def test_stats(self, multi_cache):
        multi_cache.get("miss")
        multi_cache.set("hit", 1)
        multi_cache.get("hit")
        stats = multi_cache.stats()
        assert "l1" in stats
        assert "l2" in stats
        assert "overall" in stats
        assert stats["overall"]["total_requests"] > 0

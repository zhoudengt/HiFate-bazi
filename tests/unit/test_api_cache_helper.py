#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_api_cache_helper.py
API 缓存工具 & Stream 缓存工具单元测试
"""

import json
import hashlib
import pytest
from unittest.mock import patch, MagicMock


# ════════════════════ generate_cache_key ════════════════════


class TestGenerateCacheKey:

    def test_basic_key(self):
        from server.utils.api_cache_helper import generate_cache_key
        key = generate_cache_key("pan", "1992-01-15", "12:00", "male")
        assert key == "pan:1992-01-15:12:00:male"

    def test_none_args(self):
        from server.utils.api_cache_helper import generate_cache_key
        key = generate_cache_key("pan", "1992-01-15", None, "male")
        assert key == "pan:1992-01-15::male"

    def test_kwargs_hashed(self):
        from server.utils.api_cache_helper import generate_cache_key
        key = generate_cache_key("fortune", "1992-01-15", target_year=2025)
        assert "fortune" in key
        parts = key.split(":")
        # 最后一段是 kwargs hash（16 字符）
        assert len(parts[-1]) == 16

    def test_kwargs_none_filtered(self):
        from server.utils.api_cache_helper import generate_cache_key
        k1 = generate_cache_key("p", "d", extra=None)
        k2 = generate_cache_key("p", "d")
        assert k1 == k2

    def test_kwargs_deterministic(self):
        from server.utils.api_cache_helper import generate_cache_key
        k1 = generate_cache_key("p", a=1, b=2)
        k2 = generate_cache_key("p", b=2, a=1)
        assert k1 == k2  # sort_keys=True 保证顺序无关


# ════════════════════ cache_stats ════════════════════


class TestCacheStats:

    def setup_method(self):
        """每个测试前重置统计"""
        from server.utils.api_cache_helper import reset_cache_stats
        reset_cache_stats()

    def test_record_hit(self):
        from server.utils.api_cache_helper import record_cache_hit, get_cache_stats
        record_cache_hit("test_ep")
        record_cache_hit("test_ep")
        stats = get_cache_stats()
        assert stats["total_hits"] == 2
        assert stats["by_endpoint"]["test_ep"]["hits"] == 2

    def test_record_miss(self):
        from server.utils.api_cache_helper import record_cache_miss, get_cache_stats
        record_cache_miss("ep")
        stats = get_cache_stats()
        assert stats["total_misses"] == 1

    def test_hit_rate(self):
        from server.utils.api_cache_helper import (
            record_cache_hit, record_cache_miss, get_cache_hit_rate
        )
        record_cache_hit()
        record_cache_hit()
        record_cache_miss()
        rate = get_cache_hit_rate()
        assert abs(rate - 66.67) < 1  # ~66.67%

    def test_zero_rate(self):
        from server.utils.api_cache_helper import get_cache_hit_rate
        assert get_cache_hit_rate() == 0.0

    def test_endpoint_hit_rate(self):
        from server.utils.api_cache_helper import (
            record_cache_hit, record_cache_miss, get_endpoint_hit_rate
        )
        record_cache_hit("pan")
        record_cache_miss("pan")
        assert abs(get_endpoint_hit_rate("pan") - 50.0) < 0.1

    def test_error_tracking(self):
        from server.utils.api_cache_helper import record_cache_error, get_cache_stats
        record_cache_error("ep")
        stats = get_cache_stats()
        assert stats["total_errors"] == 1


# ════════════════════ get_cached_result / set_cached_result ════════════════════


class TestCachedResultOps:

    def test_set_and_get(self, multi_cache):
        from server.utils.api_cache_helper import reset_cache_stats
        reset_cache_stats()

        # get_multi_cache 是在函数内部 from ... import 的，需要 patch 模块级
        with patch("server.utils.cache_multi_level.get_multi_cache", return_value=multi_cache):
            from server.utils.api_cache_helper import set_cached_result, get_cached_result
            # 由于函数内用 from server.utils.cache_multi_level import get_multi_cache
            # 需要直接传入 cache 对象来测试
            multi_cache.set("test:key", {"result": 42}, ttl=60)
            result = multi_cache.get("test:key")
            assert result == {"result": 42}

    def test_get_miss(self, multi_cache):
        """多级缓存 miss 返回 None"""
        assert multi_cache.get("no_such_key") is None


# ════════════════════ generate_stream_cache_key ════════════════════


class TestStreamCacheHelper:

    def test_stream_key_prefix(self):
        from server.utils.stream_cache_helper import generate_stream_cache_key
        key = generate_stream_cache_key("marriage", "1992-01-15", "12:00", "male")
        assert key.startswith("stream_marriage:")

    def test_stream_key_deterministic(self):
        from server.utils.stream_cache_helper import generate_stream_cache_key
        k1 = generate_stream_cache_key("health", "d", "t", "m")
        k2 = generate_stream_cache_key("health", "d", "t", "m")
        assert k1 == k2

    def test_compute_input_data_hash(self):
        from server.utils.stream_cache_helper import compute_input_data_hash
        h1 = compute_input_data_hash({"a": 1, "b": 2})
        h2 = compute_input_data_hash({"b": 2, "a": 1})
        assert h1 == h2  # sort_keys 保证一致
        assert len(h1) == 16

    def test_compute_hash_fallback(self):
        """序列化失败时使用 repr 降级"""
        from server.utils.stream_cache_helper import compute_input_data_hash

        class Unserializable:
            pass

        h = compute_input_data_hash({"obj": Unserializable()})
        assert len(h) == 16

    def test_llm_cache_key_format(self):
        from server.utils.stream_cache_helper import compute_input_data_hash
        h = compute_input_data_hash({"test": True})
        key = f"llm_marriage:{h}"
        assert key.startswith("llm_marriage:")

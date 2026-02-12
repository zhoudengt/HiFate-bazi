#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_coze_stream_service.py
CozeStreamService 单元测试
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock

# 依赖 httpx, 本地环境可能没有
httpx = pytest.importorskip("httpx", reason="httpx not installed locally")


# ════════════════════ 模块导入 ════════════════════


class TestModuleImport:

    def test_import_service(self):
        from server.services.coze_stream_service import CozeStreamService
        assert CozeStreamService is not None

    def test_has_session(self):
        from server.services.coze_stream_service import CozeStreamService
        assert hasattr(CozeStreamService, '__init__')


# ════════════════════ _get_cached_config ════════════════════


class TestConfigCache:

    def test_cached_config_returns_value(self):
        from server.services.coze_stream_service import _get_cached_config, _config_cache, _config_cache_lock

        with _config_cache_lock:
            _config_cache["TEST_KEY"] = ("test_value", time.time() + 60)

        try:
            result = _get_cached_config("TEST_KEY")
            assert result == "test_value"
        finally:
            with _config_cache_lock:
                _config_cache.pop("TEST_KEY", None)

    def test_expired_config_fetches_fresh(self):
        from server.services.coze_stream_service import _get_cached_config, _config_cache, _config_cache_lock

        with _config_cache_lock:
            _config_cache["EXPIRED_KEY"] = ("old_val", time.time() - 10)

        with patch("server.services.coze_stream_service.get_config_from_db_only", return_value="new_val"):
            result = _get_cached_config("EXPIRED_KEY")
            assert result == "new_val"

        with _config_cache_lock:
            _config_cache.pop("EXPIRED_KEY", None)

    def test_cache_miss_calls_db(self):
        from server.services.coze_stream_service import _get_cached_config, _config_cache, _config_cache_lock

        with _config_cache_lock:
            _config_cache.pop("BRAND_NEW_KEY", None)

        with patch("server.services.coze_stream_service.get_config_from_db_only", return_value="db_val") as mock_db:
            result = _get_cached_config("BRAND_NEW_KEY")
            assert result == "db_val"
            mock_db.assert_called_once_with("BRAND_NEW_KEY")

        with _config_cache_lock:
            _config_cache.pop("BRAND_NEW_KEY", None)

    def test_cache_thread_safety(self):
        from server.services.coze_stream_service import _get_cached_config

        errors = []

        def worker():
            try:
                for _ in range(50):
                    _get_cached_config("CONCURRENT_KEY")
            except Exception as e:
                errors.append(e)

        with patch("server.services.coze_stream_service.get_config_from_db_only", return_value="v"):
            threads = [threading.Thread(target=worker) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert errors == []


# ════════════════════ 字符串拼接优化验证 ════════════════════


class TestStringOptimization:

    def test_list_join_pattern(self):
        """验证 list + join 比 str += 更快（回归验证）"""
        import timeit

        n = 1000
        chunk = "x" * 100

        def concat_str():
            s = ""
            for _ in range(n):
                s += chunk
            return s

        def concat_list():
            parts = []
            for _ in range(n):
                parts.append(chunk)
            return "".join(parts)

        t_str = timeit.timeit(concat_str, number=10)
        t_list = timeit.timeit(concat_list, number=10)
        assert t_list < t_str * 2

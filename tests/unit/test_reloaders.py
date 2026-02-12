#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_reloaders.py
热更新 reloaders 模块的单元测试
"""

import sys
import os
import time
import importlib
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


# ════════════════════ is_reload_in_progress / get_reload_history ════════════════════


class TestReloadGlobals:

    def test_initial_state(self):
        from server.hot_reload.reloaders import is_reload_in_progress
        # 正常情况下不在重载中
        assert is_reload_in_progress() is False

    def test_history_returns_list(self):
        from server.hot_reload.reloaders import get_reload_history
        history = get_reload_history()
        assert isinstance(history, list)


# ════════════════════ SingletonReloader ════════════════════


class TestSingletonReloader:

    def test_reload_resets_registered_singletons(self):
        """已注册的单例属性应被置为 None"""
        from server.hot_reload.reloaders import SingletonReloader

        # 创建一个模拟的单例类
        mock_module = MagicMock()
        mock_class = MagicMock()
        mock_class._instance = "old_instance"
        mock_module.FakeService = mock_class

        # 临时注入到 sys.modules
        sys.modules["test.fake_service"] = mock_module

        # 临时注册
        original = list(SingletonReloader.SINGLETON_CLASSES)
        SingletonReloader.SINGLETON_CLASSES.append(
            ("test.fake_service", "FakeService", ["_instance"])
        )

        try:
            SingletonReloader.reload()
            # _instance 应被重置
            assert mock_class._instance is None
        finally:
            SingletonReloader.SINGLETON_CLASSES[:] = original
            del sys.modules["test.fake_service"]

    def test_register_singleton(self):
        from server.hot_reload.reloaders import SingletonReloader

        original_len = len(SingletonReloader.SINGLETON_CLASSES)
        SingletonReloader.register_singleton("a.b", "C", ["_inst"])

        try:
            assert len(SingletonReloader.SINGLETON_CLASSES) == original_len + 1
            assert SingletonReloader.SINGLETON_CLASSES[-1] == ("a.b", "C", ["_inst"])
        finally:
            SingletonReloader.SINGLETON_CLASSES.pop()

    def test_skip_unloaded_module(self):
        """未加载模块应跳过而不报错"""
        from server.hot_reload.reloaders import SingletonReloader

        original = list(SingletonReloader.SINGLETON_CLASSES)
        SingletonReloader.SINGLETON_CLASSES.append(
            ("nonexistent.module.path", "Cls", ["_instance"])
        )
        try:
            result = SingletonReloader.reload()
            assert result is True or result is False  # 不抛异常
        finally:
            SingletonReloader.SINGLETON_CLASSES[:] = original


# ════════════════════ RELOAD_ORDER ════════════════════


class TestReloadOrder:

    def test_order_singleton_after_source(self):
        """singleton 必须在 source 之后"""
        from server.hot_reload.reloaders import RELOAD_ORDER
        src_idx = RELOAD_ORDER.index("source")
        sing_idx = RELOAD_ORDER.index("singleton")
        assert sing_idx > src_idx

    def test_order_config_first(self):
        from server.hot_reload.reloaders import RELOAD_ORDER
        assert RELOAD_ORDER[0] == "config"

    def test_order_cache_last(self):
        from server.hot_reload.reloaders import RELOAD_ORDER
        assert RELOAD_ORDER[-1] == "cache"

    def test_all_reloaders_registered(self):
        from server.hot_reload.reloaders import RELOAD_ORDER, RELOADERS
        for name in RELOAD_ORDER:
            assert name in RELOADERS, f"重载器 {name} 未在 RELOADERS 中注册"


# ════════════════════ reload_all_modules ════════════════════


class TestReloadAllModules:

    def test_sets_and_clears_progress_flag(self):
        """执行期间 _reload_in_progress 为 True，结束后为 False"""
        import server.hot_reload.reloaders as mod

        captured = []

        # mock 所有 reloaders
        for name in mod.RELOAD_ORDER:
            reloader = MagicMock()
            reloader.reload.side_effect = lambda: captured.append(mod._reload_in_progress) or True
            mod.RELOADERS[name] = reloader

        try:
            results = mod.reload_all_modules()
            # 执行期间应为 True
            assert all(v is True for v in captured)
            # 执行后应为 False
            assert mod.is_reload_in_progress() is False
        finally:
            # 重新 import 恢复原始 reloaders
            importlib.reload(mod)

    def test_records_history(self):
        import server.hot_reload.reloaders as mod

        for name in mod.RELOAD_ORDER:
            reloader = MagicMock()
            reloader.reload.return_value = True
            mod.RELOADERS[name] = reloader

        try:
            mod._reload_history.clear()
            mod.reload_all_modules()
            assert len(mod._reload_history) == 1
            event = mod._reload_history[0]
            assert "timestamp" in event
            assert event["all_success"] is True
        finally:
            importlib.reload(mod)

    def test_failure_does_not_block(self):
        """单个 reloader 失败不应阻塞整体"""
        import server.hot_reload.reloaders as mod

        for i, name in enumerate(mod.RELOAD_ORDER):
            reloader = MagicMock()
            if i == 0:
                reloader.reload.side_effect = RuntimeError("boom")
            else:
                reloader.reload.return_value = True
            mod.RELOADERS[name] = reloader

        try:
            results = mod.reload_all_modules()
            assert results[mod.RELOAD_ORDER[0]] is False
            assert mod.is_reload_in_progress() is False
        finally:
            importlib.reload(mod)


# ════════════════════ CacheReloader (部分) ════════════════════


class TestCacheReloader:

    def test_reload_succeeds(self):
        """CacheReloader.reload 不应抛异常（内部 catch）"""
        from server.hot_reload.reloaders import CacheReloader
        # 可能因为没有全局 cache 实例而返回 True（空操作）
        result = CacheReloader.reload()
        assert isinstance(result, bool)

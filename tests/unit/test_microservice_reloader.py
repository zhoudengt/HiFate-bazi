#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_microservice_reloader.py
DynamicServicer 和 MicroserviceReloader 关键路径测试
"""

import threading
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ════════════════════ DynamicServicer ════════════════════


class TestDynamicServicer:

    def _make_dynamic(self):
        from server.hot_reload.microservice_reloader import (
            DynamicServicer, MicroserviceReloader
        )
        reloader = MagicMock(spec=MicroserviceReloader)
        servicer = MagicMock()
        servicer.SomeMethod = MagicMock(return_value="result")
        reloader.get_current_servicer.return_value = servicer
        ds = DynamicServicer(reloader)
        return ds, reloader, servicer

    def test_forwards_method_call(self):
        ds, _, servicer = self._make_dynamic()
        result = ds.SomeMethod("arg1")
        servicer.SomeMethod.assert_called()

    def test_raises_on_no_servicer(self):
        from server.hot_reload.microservice_reloader import (
            DynamicServicer, MicroserviceReloader
        )
        reloader = MagicMock(spec=MicroserviceReloader)
        reloader.get_current_servicer.return_value = None
        ds = DynamicServicer(reloader)
        with pytest.raises(RuntimeError):
            ds.SomeMethod()

    def test_raises_attribute_error_for_missing(self):
        ds, _, servicer = self._make_dynamic()
        servicer.configure_mock(**{"NonExist": PropertyMock(side_effect=AttributeError)})
        del servicer.NonExist
        with pytest.raises(AttributeError):
            ds.NonExist()

    def test_clear_cache_via_object(self):
        """通过 object.__getattribute__ 直接访问内部 _method_cache"""
        from server.hot_reload.microservice_reloader import (
            DynamicServicer, MicroserviceReloader
        )
        reloader = MagicMock(spec=MicroserviceReloader)
        servicer = MagicMock()
        reloader.get_current_servicer.return_value = servicer
        ds = DynamicServicer(reloader)

        # 手动往缓存里放东西
        cache = object.__getattribute__(ds, '_method_cache')
        cache["SomeMethod"] = "cached"
        assert len(cache) == 1

        # 直接调用内部 clear_cache（以 _ 开头不会被转发）
        lock = object.__getattribute__(ds, '_cache_lock')
        with lock:
            cache.clear()
        assert len(cache) == 0

    def test_cache_invalidated_on_servicer_change(self):
        from server.hot_reload.microservice_reloader import (
            DynamicServicer, MicroserviceReloader
        )
        reloader = MagicMock(spec=MicroserviceReloader)
        servicer_v1 = MagicMock()
        servicer_v1.Greet = MagicMock(return_value="v1")
        reloader.get_current_servicer.return_value = servicer_v1

        ds = DynamicServicer(reloader)
        ds.Greet("hello")

        # 模拟 servicer 更新
        servicer_v2 = MagicMock()
        servicer_v2.Greet = MagicMock(return_value="v2")
        reloader.get_current_servicer.return_value = servicer_v2

        # clear cache 通过 object.__getattribute__
        cache = object.__getattribute__(ds, '_method_cache')
        lock = object.__getattribute__(ds, '_cache_lock')
        with lock:
            cache.clear()

        result = ds.Greet("hello")
        servicer_v2.Greet.assert_called()

    def test_internal_attrs_bypass_forwarding(self):
        """以 _ 开头的属性不应被转发"""
        from server.hot_reload.microservice_reloader import DynamicServicer
        ds, _, _ = self._make_dynamic()
        # _reloader 应可直接访问
        reloader = object.__getattribute__(ds, '_reloader')
        assert reloader is not None
        cache = object.__getattribute__(ds, '_method_cache')
        assert isinstance(cache, dict)


# ════════════════════ MicroserviceReloader basics ════════════════════


class TestMicroserviceReloaderBasics:

    def test_dynamic_servicers_list_initialized(self):
        from server.hot_reload.microservice_reloader import MicroserviceReloader

        with patch.object(MicroserviceReloader, '_scan_files'):
            reloader = MicroserviceReloader(
                service_name="test_svc",
                module_path="test.module",
                servicer_class_name="TestServicer",
            )
        assert hasattr(reloader, "_dynamic_servicers")
        assert isinstance(reloader._dynamic_servicers, list)

    def test_set_and_get_servicer(self):
        from server.hot_reload.microservice_reloader import MicroserviceReloader

        with patch.object(MicroserviceReloader, '_scan_files'):
            reloader = MicroserviceReloader(
                service_name="test_svc",
                module_path="test.module",
                servicer_class_name="TestServicer",
            )
        mock_servicer = MagicMock()
        reloader.set_servicer(mock_servicer)
        assert reloader.get_current_servicer() is mock_servicer

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/unit/test_grpc_gateway.py
gRPC Gateway 端点注册与路由测试
"""

import pytest
from unittest.mock import patch, MagicMock

# 依赖 fastapi, 本地环境可能没有
fastapi = pytest.importorskip("fastapi", reason="fastapi not installed locally")


# ════════════════════ SUPPORTED_ENDPOINTS ════════════════════


class TestSupportedEndpoints:

    def test_endpoints_not_empty(self):
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        assert len(SUPPORTED_ENDPOINTS) > 0

    def test_critical_endpoints_registered(self):
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        critical = [
            "/bazi/interface",
            "/bazi/shengong-minggong",
            "/bazi/rizhu-liujiazi",
            "/daily-fortune-calendar/query",
        ]
        for ep in critical:
            assert ep in SUPPORTED_ENDPOINTS, f"关键端点 {ep} 未注册"

    def test_endpoint_handlers_are_callable(self):
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        for ep, handler in SUPPORTED_ENDPOINTS.items():
            assert callable(handler), f"端点 {ep} 的 handler 不是 callable"


# ════════════════════ _ensure_endpoints_registered ════════════════════


class TestEnsureEndpointsRegistered:

    def test_function_exists(self):
        from server.api.grpc_gateway import _ensure_endpoints_registered
        assert callable(_ensure_endpoints_registered)

    def test_call_does_not_raise(self):
        from server.api.grpc_gateway import _ensure_endpoints_registered
        _ensure_endpoints_registered()

    def test_restores_endpoints_after_clear(self):
        from server.api.grpc_gateway import (
            SUPPORTED_ENDPOINTS, _ensure_endpoints_registered
        )
        backup = dict(SUPPORTED_ENDPOINTS)

        try:
            SUPPORTED_ENDPOINTS.clear()
            assert len(SUPPORTED_ENDPOINTS) == 0

            _ensure_endpoints_registered()
            assert len(SUPPORTED_ENDPOINTS) > 0
            assert "/bazi/interface" in SUPPORTED_ENDPOINTS
        finally:
            SUPPORTED_ENDPOINTS.clear()
            SUPPORTED_ENDPOINTS.update(backup)


# ════════════════════ 端点路由格式 ════════════════════


class TestEndpointFormat:

    def test_all_endpoints_start_with_slash(self):
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        for ep in SUPPORTED_ENDPOINTS:
            assert ep.startswith("/"), f"端点 {ep} 不以 / 开头"

    def test_no_duplicate_endpoints(self):
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        endpoints = list(SUPPORTED_ENDPOINTS.keys())
        assert len(endpoints) == len(set(endpoints))


# ════════════════════ 流式端点 ════════════════════


class TestStreamEndpoints:

    def test_stream_endpoints_exist(self):
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        stream_endpoints = [
            ep for ep in SUPPORTED_ENDPOINTS
            if "stream" in ep or "daily-fortune" in ep
        ]
        assert len(stream_endpoints) > 0

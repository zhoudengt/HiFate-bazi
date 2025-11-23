#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gRPC client for calling the bazi-fortune-service."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import grpc

# 导入生成的 gRPC 代码
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "proto", "generated"))

import bazi_fortune_pb2
import bazi_fortune_pb2_grpc

logger = logging.getLogger(__name__)


class BaziFortuneClient:
    """gRPC client for the bazi-fortune-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        # base_url 格式: host:port 或 [host]:port
        base_url = base_url or os.getenv("BAZI_FORTUNE_SERVICE_URL", "")
        if not base_url:
            raise RuntimeError("BAZI_FORTUNE_SERVICE_URL is not configured")
        
        # 解析地址（移除 http:// 前缀）
        if base_url.startswith("http://"):
            base_url = base_url[7:]
        elif base_url.startswith("https://"):
            base_url = base_url[8:]
        
        # 如果没有端口，添加默认端口
        if ":" not in base_url:
            base_url = f"{base_url}:9002"
        
        self.address = base_url
        self.timeout = timeout

    def calculate_detail(self, solar_date: str, solar_time: str, gender: str, current_time: Optional[str] = None) -> Dict[str, Any]:
        """计算大运流年详情"""
        request = bazi_fortune_pb2.BaziFortuneRequest(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            current_time=current_time or "",
        )

        logger.debug("Calling bazi-fortune-service (gRPC): %s request=%s", self.address, request)

        # 设置连接选项，避免 "Too many pings" 错误
        options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟，减少 ping 频率
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
            ('grpc.keepalive_permit_without_calls', False),  # 没有调用时不发送 ping
            ('grpc.http2.max_pings_without_data', 2),  # 允许最多2个 ping
            ('grpc.http2.min_time_between_pings_ms', 60000),  # ping 之间至少间隔60秒
        ]
        
        with grpc.insecure_channel(self.address, options=options) as channel:
            stub = bazi_fortune_pb2_grpc.BaziFortuneServiceStub(channel)
            try:
                response = stub.CalculateDayunLiunian(request, timeout=self.timeout)
                
                if not response.detail_json:
                    raise RuntimeError("bazi-fortune-service response missing 'detail_json'")
                
                detail = json.loads(response.detail_json)
                return detail
                
            except grpc.RpcError as e:
                logger.error("bazi-fortune-service gRPC error: %s", e)
                raise

    def health_check(self) -> bool:
        """健康检查"""
        request = bazi_fortune_pb2.HealthCheckRequest()
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = bazi_fortune_pb2_grpc.BaziFortuneServiceStub(channel)
                response = stub.HealthCheck(request, timeout=5.0)
                return response.status == "ok"
        except grpc.RpcError:
            logger.exception("bazi-fortune-service health check failed")
            return False


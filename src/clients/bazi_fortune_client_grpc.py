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

# 导入公共工具函数和基类
sys.path.insert(0, os.path.join(project_root, "server", "utils"))
from grpc_config import get_standard_grpc_options
from grpc_helpers import parse_grpc_address
from src.clients.base_grpc_client import BaseGrpcClient

logger = logging.getLogger(__name__)


class BaziFortuneClient(BaseGrpcClient):
    """gRPC client for the bazi-fortune-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        # 调用基类初始化方法
        super().__init__(
            service_name="bazi-fortune-service",
            env_key="BAZI_FORTUNE_SERVICE_URL",
            default_port=9002,
            base_url=base_url,
            timeout=timeout
        )

    def calculate_detail(self, solar_date: str, solar_time: str, gender: str, current_time: Optional[str] = None) -> Dict[str, Any]:
        """计算大运流年详情"""
        request = bazi_fortune_pb2.BaziFortuneRequest(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            current_time=current_time or "",
        )

        logger.debug("Calling bazi-fortune-service (gRPC): %s request=%s", self.address, request)

        # 使用基类方法获取标准 gRPC 配置
        options = self.get_grpc_options()
        
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
        return super().health_check(
            stub_class=bazi_fortune_pb2_grpc.BaziFortuneServiceStub,
            request_class=bazi_fortune_pb2.HealthCheckRequest
        )


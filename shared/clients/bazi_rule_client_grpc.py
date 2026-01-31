#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gRPC client for calling the bazi-rule-service."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import grpc

# 导入生成的 gRPC 代码
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "proto", "generated"))

import bazi_rule_pb2
import bazi_rule_pb2_grpc

# 导入公共工具函数和基类
sys.path.insert(0, os.path.join(project_root, "server", "utils"))
from grpc_config import get_grpc_options_with_message_size
from grpc_helpers import parse_grpc_address
from shared.clients.base_grpc_client import BaseGrpcClient

logger = logging.getLogger(__name__)


class BaziRuleClient(BaseGrpcClient):
    """gRPC client for the bazi-rule-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 60.0) -> None:
        # 调用基类初始化方法
        super().__init__(
            service_name="bazi-rule-service",
            env_key="BAZI_RULE_SERVICE_URL",
            default_port=9004,
            base_url=base_url,
            timeout=timeout
        )

    def match_rules(
        self,
        solar_date: str,
        solar_time: str,
        gender: str,
        rule_types: Optional[List[str]] = None,
        use_cache: bool = False,
    ) -> Dict[str, Any]:
        """匹配规则"""
        request = bazi_rule_pb2.BaziRuleMatchRequest(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            rule_types=list(rule_types) if rule_types else [],
            use_cache=use_cache,
        )

        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rule_types_str = ", ".join(rule_types) if rule_types else "全部"
        logger.info(f"[{request_time}] 🔵 调用 bazi-rule-service (gRPC): {self.address}, solar_date={solar_date}, solar_time={solar_time}, gender={gender}, rule_types=[{rule_types_str}], use_cache={use_cache}")
        logger.debug("Calling bazi-rule-service (gRPC): %s request=%s", self.address, request)

        # 使用基类 Channel 连接池复用连接（含消息大小限制）
        options = self.get_grpc_options(include_message_size=True, max_message_size_mb=50)
        channel = self.get_channel(self.address, options)
        stub = bazi_rule_pb2_grpc.BaziRuleServiceStub(channel)
        try:
            response = stub.MatchRules(request, timeout=self.timeout)

            import datetime
            response_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            matched_data = json.loads(response.matched_json) if response.matched_json else []
            matched_count = len(matched_data)

            # 处理 unmatched 数据（可能是完整列表或只包含 count）
            unmatched_json = response.unmatched_json if response.unmatched_json else '{}'
            unmatched_data = json.loads(unmatched_json)
            if isinstance(unmatched_data, dict) and 'count' in unmatched_data:
                unmatched_list = []
            else:
                unmatched_list = unmatched_data if isinstance(unmatched_data, list) else []

            logger.info(f"[{response_time}] ✅ bazi-rule-service (gRPC): 调用成功，匹配 {matched_count} 条规则")
            return {
                "matched": matched_data,
                "unmatched": unmatched_list,
                "context": json.loads(response.context_json) if response.context_json else {},
            }

        except grpc.RpcError as e:
            import datetime
            error_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f"[{error_time}] ❌ bazi-rule-service (gRPC): 调用失败 - {e}")
            raise

    def health_check(self) -> bool:
        """健康检查"""
        return super().health_check(
            stub_class=bazi_rule_pb2_grpc.BaziRuleServiceStub,
            request_class=bazi_rule_pb2.HealthCheckRequest
        )


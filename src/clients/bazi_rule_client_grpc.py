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

logger = logging.getLogger(__name__)


class BaziRuleClient:
    """gRPC client for the bazi-rule-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 60.0) -> None:
        # base_url 格式: host:port 或 [host]:port
        base_url = base_url or os.getenv("BAZI_RULE_SERVICE_URL", "")
        if not base_url:
            raise RuntimeError("BAZI_RULE_SERVICE_URL is not configured")
        
        # 解析地址（移除 http:// 前缀）
        if base_url.startswith("http://"):
            base_url = base_url[7:]
        elif base_url.startswith("https://"):
            base_url = base_url[8:]
        
        # 如果没有端口，添加默认端口
        if ":" not in base_url:
            base_url = f"{base_url}:9004"
        
        self.address = base_url
        self.timeout = timeout

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

        # 设置连接选项，避免 "Too many pings" 错误
        # 配置消息大小限制，支持大响应（462条规则可能产生较大的响应）
        options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟，减少 ping 频率
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
            ('grpc.keepalive_permit_without_calls', False),  # 没有调用时不发送 ping
            ('grpc.http2.max_pings_without_data', 2),  # 允许最多2个 ping
            ('grpc.http2.min_time_between_pings_ms', 60000),  # ping 之间至少间隔60秒
            # 增加消息大小限制（默认4MB，增加到50MB以支持大量规则）
            ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
        ]
        
        with grpc.insecure_channel(self.address, options=options) as channel:
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
                    # 只返回 count，不返回完整列表
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
        request = bazi_rule_pb2.HealthCheckRequest()
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = bazi_rule_pb2_grpc.BaziRuleServiceStub(channel)
                response = stub.HealthCheck(request, timeout=5.0)
                return response.status == "ok"
        except grpc.RpcError:
            logger.exception("bazi-rule-service health check failed")
            return False


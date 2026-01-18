#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gRPC client for calling the bazi-core-service."""

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

import bazi_core_pb2
import bazi_core_pb2_grpc

# 导入公共工具函数和基类
sys.path.insert(0, os.path.join(project_root, "server", "utils"))
from grpc_config import get_standard_grpc_options
from grpc_helpers import parse_grpc_address
from shared.clients.base_grpc_client import BaseGrpcClient

logger = logging.getLogger(__name__)


class BaziCoreClient(BaseGrpcClient):
    """gRPC client for the bazi-core-service."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        # 调用基类初始化方法
        super().__init__(
            service_name="bazi-core-service",
            env_key="BAZI_CORE_SERVICE_URL",
            default_port=9001,
            base_url=base_url,
            timeout=timeout
        )

    def calculate_bazi(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """计算八字排盘"""
        request = bazi_core_pb2.BaziCoreRequest(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
        )

        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{request_time}] 🔵 调用 bazi-core-service (gRPC): {self.address}, solar_date={solar_date}, solar_time={solar_time}, gender={gender}")
        logger.debug("Calling bazi-core-service (gRPC): %s request=%s", self.address, request)

        # 使用基类方法获取标准 gRPC 配置
        options = self.get_grpc_options()
        
        with grpc.insecure_channel(self.address, options=options) as channel:
            stub = bazi_core_pb2_grpc.BaziCoreServiceStub(channel)
            try:
                response = stub.CalculateBazi(request, timeout=self.timeout)
                
                # 转换为字典格式
                result: Dict[str, Any] = {}
                
                # 基本信息（安全地转换为字典，需要反序列化 lunar_date）
                basic_info_dict = {}
                if response.basic_info:
                    for key, value in response.basic_info.items():
                        if key == "lunar_date" and isinstance(value, str):
                            # lunar_date 是 JSON 字符串，需要反序列化
                            try:
                                basic_info_dict[key] = json.loads(value) if value else {}
                            except (json.JSONDecodeError, TypeError):
                                basic_info_dict[key] = {}
                        else:
                            basic_info_dict[key] = value
                result["basic_info"] = basic_info_dict
                
                # 四柱信息（安全地获取）
                result["bazi_pillars"] = {
                    "year": {
                        "stem": response.year_pillar.stem if response.year_pillar else "",
                        "branch": response.year_pillar.branch if response.year_pillar else "",
                    },
                    "month": {
                        "stem": response.month_pillar.stem if response.month_pillar else "",
                        "branch": response.month_pillar.branch if response.month_pillar else "",
                    },
                    "day": {
                        "stem": response.day_pillar.stem if response.day_pillar else "",
                        "branch": response.day_pillar.branch if response.day_pillar else "",
                    },
                    "hour": {
                        "stem": response.hour_pillar.stem if response.hour_pillar else "",
                        "branch": response.hour_pillar.branch if response.hour_pillar else "",
                    },
                }
                
                # 四柱详情（安全地获取）
                result["details"] = {}
                if response.details:
                    for pillar_name, detail in response.details.items():
                        if detail:
                            result["details"][pillar_name] = {
                                "main_star": detail.main_star if hasattr(detail, 'main_star') else "",
                                "hidden_stars": list(detail.hidden_stars) if hasattr(detail, 'hidden_stars') and detail.hidden_stars else [],
                                "hidden_stems": list(detail.hidden_stems) if hasattr(detail, 'hidden_stems') and detail.hidden_stems else [],
                                "star_fortune": detail.star_fortune if hasattr(detail, 'star_fortune') else "",
                                "self_sitting": detail.self_sitting if hasattr(detail, 'self_sitting') else "",
                                "nayin": detail.nayin if hasattr(detail, 'nayin') else "",
                                "kongwang": detail.kongwang if hasattr(detail, 'kongwang') else "",
                                "deities": list(detail.deities) if hasattr(detail, 'deities') and detail.deities else [],
                            }
                        else:
                            result["details"][pillar_name] = {
                                "main_star": "",
                                "hidden_stars": [],
                                "hidden_stems": [],
                                "star_fortune": "",
                                "self_sitting": "",
                                "nayin": "",
                                "kongwang": "",
                                "deities": [],
                            }
                
                # 十神统计（需要反序列化 JSON 字符串）
                ten_gods_stats = {}
                if response.ten_gods_stats:
                    for key, value_json in response.ten_gods_stats.items():
                        try:
                            if isinstance(value_json, str):
                                ten_gods_stats[key] = json.loads(value_json) if value_json else {}
                            else:
                                ten_gods_stats[key] = value_json
                        except (json.JSONDecodeError, TypeError):
                            ten_gods_stats[key] = value_json if value_json else {}
                result["ten_gods_stats"] = ten_gods_stats
                
                # 五行信息（需要反序列化 JSON 字符串或Python字典字符串）
                elements = {}
                if response.elements:
                    for key, value_json in response.elements.items():
                        # DEBUG: 打印原始值
                        logger.info(f"DEBUG: elements['{key}'] raw value type={type(value_json).__name__}, value={repr(value_json)[:200]}")
                        try:
                            if isinstance(value_json, str):
                                # 先尝试 ast.literal_eval（支持Python字典格式，单引号）
                                try:
                                    import ast
                                    parsed = ast.literal_eval(value_json) if value_json else {}
                                    logger.info(f"DEBUG: ast.literal_eval success for '{key}': {parsed}")
                                except (ValueError, SyntaxError) as e1:
                                    logger.info(f"DEBUG: ast.literal_eval failed for '{key}': {e1}, trying json.loads...")
                                    # 如果失败，尝试 json.loads（标准JSON，双引号）
                                    parsed = json.loads(value_json) if value_json else {}
                                    logger.info(f"DEBUG: json.loads success for '{key}': {parsed}")
                                # 确保解析结果是字典，不是字符串
                                if isinstance(parsed, dict):
                                    elements[key] = parsed
                                else:
                                    logger.warning(f"DEBUG: parsed result for '{key}' is not dict (type={type(parsed)}), using empty dict")
                                    elements[key] = {}
                            elif isinstance(value_json, dict):
                                # 如果已经是字典，直接使用
                                logger.info(f"DEBUG: elements['{key}'] is already dict: {value_json}")
                                elements[key] = value_json
                            else:
                                # 其他类型（不应该出现），使用空字典
                                logger.warning(f"DEBUG: elements['{key}'] is unexpected type: {type(value_json)}")
                                elements[key] = {}
                        except (json.JSONDecodeError, TypeError, ValueError, SyntaxError) as e:
                            # 解析失败，使用空字典而不是保留错误的字符串值
                            logger.warning(f"Failed to parse elements['{key}']: {repr(value_json)[:100]}, error: {e}")
                            elements[key] = {}
                result["elements"] = elements
                
                # 五行计数（直接是 int32）
                result["element_counts"] = dict(response.element_counts) if response.element_counts else {}
                
                # 关系信息（需要反序列化 JSON 字符串）
                relationships = {}
                if response.relationships:
                    for key, value_json in response.relationships.items():
                        try:
                            if isinstance(value_json, str):
                                relationships[key] = json.loads(value_json) if value_json else {}
                            else:
                                relationships[key] = value_json
                        except (json.JSONDecodeError, TypeError):
                            relationships[key] = value_json if value_json else {}
                result["relationships"] = relationships
                
                # 元数据
                if response.metadata_json:
                    result["metadata"] = json.loads(response.metadata_json)
                
                return result
                
            except grpc.RpcError as e:
                import datetime
                error_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.error(f"[{error_time}] ❌ bazi-core-service (gRPC): 调用失败 - {e}")
                raise

    def health_check(self) -> bool:
        """健康检查"""
        return super().health_check(
            stub_class=bazi_core_pb2_grpc.BaziCoreServiceStub,
            request_class=bazi_core_pb2.HealthCheckRequest
        )


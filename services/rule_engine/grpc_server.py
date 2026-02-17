#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule-engine 合并服务 - 将 bazi-rule(9004) + fortune-rule(9007) 合并为单进程。

对外保持兼容：两个 proto 的 RPC 接口不变，客户端代码零改动。
所有 Servicer 注册到同一个 gRPC server，监听单一端口。
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

import os
import sys
from concurrent import futures

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))

# 复用原有 Servicer 实现
from services.bazi_rule.grpc_server import BaziRuleServicer
from services.fortune_rule.grpc_server import FortuneRuleServicer

import bazi_rule_pb2_grpc
import fortune_rule_pb2_grpc


def serve(port: int = 9004):
    """启动合并的规则 gRPC 服务器"""

    server_options = [
        ('grpc.keepalive_time_ms', 300000),
        ('grpc.keepalive_timeout_ms', 20000),
        ('grpc.keepalive_permit_without_calls', False),
        ('grpc.http2.max_pings_without_data', 2),
        ('grpc.http2.min_time_between_pings_ms', 60000),
        ('grpc.http2.min_ping_interval_without_data_ms', 300000),
    ]

    try:
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server,
            register_microservice_reloader
        )

        server, reloader = create_hot_reload_server(
            service_name="rule_engine",
            module_path="services.rule_engine.grpc_server",
            servicer_class_name="BaziRuleServicer",
            add_servicer_to_server_func=bazi_rule_pb2_grpc.add_BaziRuleServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=20,
            check_interval=30,
            listen_addr=f"localhost:{port}"
        )

        # 额外注册 fortune-rule servicer
        fortune_rule_pb2_grpc.add_FortuneRuleServiceServicer_to_server(
            FortuneRuleServicer(), server
        )

        register_microservice_reloader("rule_engine", reloader)
        reloader.start()

        server.start()
        logger.info(f"✅ Rule Engine 合并服务已启动（热更新），监听端口: {port}")
        logger.info(f"   包含: BaziRule + FortuneRule")

        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            reloader.stop()
            server.stop(grace=5)
            logger.info("✅ 服务已停止")

    except ImportError as e:
        logger.info(f"⚠️ 热更新模块不可用，使用传统模式: {e}")

        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=20),
            options=server_options
        )

        bazi_rule_pb2_grpc.add_BaziRuleServiceServicer_to_server(BaziRuleServicer(), server)
        fortune_rule_pb2_grpc.add_FortuneRuleServiceServicer_to_server(FortuneRuleServicer(), server)

        listen_addr = f"localhost:{port}"
        server.add_insecure_port(listen_addr)

        server.start()
        logger.info(f"✅ Rule Engine 合并服务已启动（传统模式），监听端口: {port}")

        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            server.stop(grace=5)
            logger.info("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Rule Engine 合并 gRPC 服务")
    parser.add_argument("--port", type=int, default=9004, help="服务端口（默认: 9004）")
    args = parser.parse_args()
    serve(args.port)

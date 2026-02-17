#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bazi-compute 合并服务 - 将 bazi-core(9001) + bazi-fortune(9002) + bazi-analyzer(9003) 合并为单进程。

对外保持兼容：三个 proto 的 RPC 接口不变，客户端代码零改动。
所有三个 Servicer 注册到同一个 gRPC server，监听单一端口。
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

import json
import os
import sys
from concurrent import futures

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))

# --- 导入四个服务的 Servicer（复用原有实现） ---
from services.bazi_core.grpc_server import BaziCoreServicer
from services.bazi_fortune.grpc_server import BaziFortuneServicer
from services.bazi_analyzer.grpc_server import BaziAnalyzerServicer
from services.fortune_analysis.grpc_server import FortuneAnalysisServicer

# --- 导入四个服务的 pb2_grpc（用于注册） ---
import bazi_core_pb2_grpc
import bazi_fortune_pb2_grpc
import bazi_analyzer_pb2_grpc
import fortune_analysis_pb2_grpc


def serve(port: int = 9001):
    """启动合并的 gRPC 服务器（支持热更新）"""

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

        # 用 bazi_core 的热更新框架创建 server
        server, reloader = create_hot_reload_server(
            service_name="bazi_compute",
            module_path="services.bazi_compute.grpc_server",
            servicer_class_name="BaziCoreServicer",
            add_servicer_to_server_func=bazi_core_pb2_grpc.add_BaziCoreServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=20,
            check_interval=30,
            listen_addr=f"[::]:{port}"
        )

        # 额外注册 fortune、analyzer、fortune-analysis servicer
        bazi_fortune_pb2_grpc.add_BaziFortuneServiceServicer_to_server(
            BaziFortuneServicer(), server
        )
        bazi_analyzer_pb2_grpc.add_BaziAnalyzerServiceServicer_to_server(
            BaziAnalyzerServicer(), server
        )
        fortune_analysis_pb2_grpc.add_FortuneAnalysisServiceServicer_to_server(
            FortuneAnalysisServicer(), server
        )

        register_microservice_reloader("bazi_compute", reloader)
        reloader.start()

        server.start()
        logger.info(f"✅ Bazi Compute 合并服务已启动（热更新），监听端口: {port}")
        logger.info(f"   包含: BaziCore + BaziFortune + BaziAnalyzer")

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

        # 注册全部四个 servicer
        bazi_core_pb2_grpc.add_BaziCoreServiceServicer_to_server(BaziCoreServicer(), server)
        bazi_fortune_pb2_grpc.add_BaziFortuneServiceServicer_to_server(BaziFortuneServicer(), server)
        bazi_analyzer_pb2_grpc.add_BaziAnalyzerServiceServicer_to_server(BaziAnalyzerServicer(), server)
        fortune_analysis_pb2_grpc.add_FortuneAnalysisServiceServicer_to_server(FortuneAnalysisServicer(), server)

        listen_addr = f"[::]:{port}"
        server.add_insecure_port(listen_addr)

        server.start()
        logger.info(f"✅ Bazi Compute 合并服务已启动（传统模式），监听端口: {port}")

        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            server.stop(grace=5)
            logger.info("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Bazi Compute 合并 gRPC 服务")
    parser.add_argument("--port", type=int, default=9001, help="服务端口（默认: 9001）")
    args = parser.parse_args()
    serve(args.port)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for bazi-analyzer-service.
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

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))
import bazi_analyzer_pb2
import bazi_analyzer_pb2_grpc

# 双轨支持：优先使用 gRPC 客户端，降级到本地计算
USE_GRPC_BAZI_CORE = os.environ.get("USE_GRPC_BAZI_CORE", "true").lower() == "true"

# 延迟导入，仅在需要时加载
def _get_bazi_core_client():
    """获取 BaziCoreClient 实例"""
    try:
        from shared.clients.bazi_core_client_grpc import BaziCoreClient
        return BaziCoreClient()
    except Exception as e:
        logger.warning(f"BaziCoreClient 初始化失败，降级到本地计算: {e}")
        return None

def _get_local_calculator():
    """获取本地 BaziCalculator（降级方案）"""
    from core.calculators.BaziCalculator import BaziCalculator
    return BaziCalculator

def _get_rizhu_analyzer():
    """获取 RizhuGenderAnalyzer"""
    from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
    return RizhuGenderAnalyzer


class BaziAnalyzerServicer(bazi_analyzer_pb2_grpc.BaziAnalyzerServiceServicer):
    """实现 BaziAnalyzerService 的 gRPC 服务"""

    def __init__(self):
        """初始化服务"""
        self._bazi_core_client = None
        if USE_GRPC_BAZI_CORE:
            self._bazi_core_client = _get_bazi_core_client()

    def RunAnalyzers(self, request: bazi_analyzer_pb2.BaziAnalyzerRequest, context: grpc.ServicerContext) -> bazi_analyzer_pb2.BaziAnalyzerResponse:
        """执行分析"""
        try:
            # 双轨支持：优先使用 gRPC 客户端调用 bazi-core 服务
            bazi_pillars = None
            if USE_GRPC_BAZI_CORE and self._bazi_core_client:
                try:
                    bazi_result = self._bazi_core_client.calculate_bazi(
                        request.solar_date, request.solar_time, request.gender
                    )
                    if bazi_result:
                        bazi_pillars = bazi_result.get('bazi_pillars', {})
                        logger.info(f"✅ 通过 gRPC 获取八字数据成功")
                except Exception as e:
                    logger.warning(f"gRPC 调用失败，降级到本地计算: {e}")
            
            # 降级方案：本地计算
            if not bazi_pillars:
                BaziCalculator = _get_local_calculator()
                calculator = BaziCalculator(request.solar_date, request.solar_time, request.gender)
                bazi_result = calculator.calculate()
                
                if not bazi_result:
                    context.set_code(grpc.StatusCode.INTERNAL)
                    context.set_details("八字排盘失败")
                    return bazi_analyzer_pb2.BaziAnalyzerResponse()
                
                bazi_pillars = bazi_result.get('bazi_pillars', {})
                logger.info(f"✅ 通过本地计算获取八字数据成功（降级模式）")

            results: dict = {}
            RizhuGenderAnalyzer = _get_rizhu_analyzer()

            for analyzer_type in request.analysis_types:
                if analyzer_type == "rizhu_gender":
                    analyzer = RizhuGenderAnalyzer(bazi_pillars, request.gender)
                    analysis = analyzer.analyze_rizhu_gender()
                    analysis["formatted_text"] = analyzer.get_formatted_output()
                    results[analyzer_type] = analysis
                else:
                    results[analyzer_type] = {
                        "error": f"unsupported analyzer type: {analyzer_type}"
                    }

            response = bazi_analyzer_pb2.BaziAnalyzerResponse()
            response.results_json = json.dumps(results, ensure_ascii=False)
            
            metadata = {
                "service": "bazi-analyzer-service",
                "version": "1.0.0",
            }
            response.metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            return response
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"分析失败: {str(e)}")
            return bazi_analyzer_pb2.BaziAnalyzerResponse()

    def HealthCheck(self, request: bazi_analyzer_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> bazi_analyzer_pb2.HealthCheckResponse:
        """健康检查"""
        return bazi_analyzer_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9003):
    """启动 gRPC 服务器（支持热更新）"""
    try:
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server,
            register_microservice_reloader
        )
        
        server_options = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
        ]
        
        server, reloader = create_hot_reload_server(
            service_name="bazi_analyzer",
            module_path="services.bazi_analyzer.grpc_server",
            servicer_class_name="BaziAnalyzerServicer",
            add_servicer_to_server_func=bazi_analyzer_pb2_grpc.add_BaziAnalyzerServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=10,
            check_interval=30
        )
        
        register_microservice_reloader("bazi_analyzer", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口，不需要再次绑定
        server.start()
        logger.info(f"✅ Bazi Analyzer gRPC 服务已启动（热更新已启用），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            reloader.stop()
            server.stop(grace=5)
            logger.info("✅ 服务已停止")
            
    except ImportError:
        # 降级到传统模式
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        bazi_analyzer_pb2_grpc.add_BaziAnalyzerServiceServicer_to_server(BaziAnalyzerServicer(), server)
        
        listen_addr = f"[::]:{port}"
        server.add_insecure_port(listen_addr)
        
        server.start()
        logger.info(f"✅ Bazi Analyzer gRPC 服务已启动（传统模式），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            server.stop(grace=5)
            logger.info("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Bazi Analyzer gRPC 服务")
    parser.add_argument("--port", type=int, default=9003, help="服务端口（默认: 9003）")
    args = parser.parse_args()
    serve(args.port)


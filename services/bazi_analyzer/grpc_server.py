#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for bazi-analyzer-service.
"""

from __future__ import annotations

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

from src.tool.BaziCalculator import BaziCalculator
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer


class BaziAnalyzerServicer(bazi_analyzer_pb2_grpc.BaziAnalyzerServiceServicer):
    """实现 BaziAnalyzerService 的 gRPC 服务"""

    def RunAnalyzers(self, request: bazi_analyzer_pb2.BaziAnalyzerRequest, context: grpc.ServicerContext) -> bazi_analyzer_pb2.BaziAnalyzerResponse:
        """执行分析"""
        try:
            calculator = BaziCalculator(request.solar_date, request.solar_time, request.gender)
            bazi_result = calculator.calculate()
            
            if not bazi_result:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("八字排盘失败")
                return bazi_analyzer_pb2.BaziAnalyzerResponse()

            results: dict = {}

            for analyzer_type in request.analysis_types:
                if analyzer_type == "rizhu_gender":
                    analyzer = RizhuGenderAnalyzer(calculator.bazi_pillars, calculator.gender)
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
    """启动 gRPC 服务器"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bazi_analyzer_pb2_grpc.add_BaziAnalyzerServiceServicer_to_server(BaziAnalyzerServicer(), server)
    
    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    
    server.start()
    print(f"✅ Bazi Analyzer gRPC 服务已启动，监听端口: {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n>>> 正在停止服务...")
        server.stop(grace=5)
        print("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Bazi Analyzer gRPC 服务")
    parser.add_argument("--port", type=int, default=9003, help="服务端口（默认: 9003）")
    args = parser.parse_args()
    serve(args.port)


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for fortune-analysis-service.
面相手相命理分析服务
"""

from __future__ import annotations

import os
import sys
from concurrent import futures

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))
import fortune_analysis_pb2
import fortune_analysis_pb2_grpc

from services.fortune_analysis.hand_analyzer_core import HandAnalyzerCore
from services.fortune_analysis.face_analyzer_core import FaceAnalyzerCore


class FortuneAnalysisServicer(fortune_analysis_pb2_grpc.FortuneAnalysisServiceServicer):
    """实现 FortuneAnalysisService 的 gRPC 服务"""

    def __init__(self):
        # 使用独立的手相和面相分析器，互不影响
        self.hand_analyzer = HandAnalyzerCore()
        self.face_analyzer = FaceAnalyzerCore()

    def AnalyzeHand(self, request: fortune_analysis_pb2.HandAnalysisRequest, context: grpc.ServicerContext) -> fortune_analysis_pb2.HandAnalysisResponse:
        """手相分析"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] 📥 fortune-analysis-service: 收到手相分析请求", flush=True)
        
        try:
            # 调用手相分析器（独立模块）
            result = self.hand_analyzer.analyze_hand(
                image_bytes=request.image.image_bytes,
                image_format=request.image.image_format or "jpg",
                bazi_info=request.bazi_info if request.bazi_info.use_bazi else None
            )
            
            # 构建响应
            response = fortune_analysis_pb2.HandAnalysisResponse()
            response.success = result.get("success", False)
            
            if not response.success:
                response.error_message = result.get("error", "分析失败")
                return response
            
            # 填充特征
            features = result.get("features", {})
            response.features.hand_shape = features.get("hand_shape", "")
            if features.get("finger_lengths"):
                response.features.finger_lengths.update(features["finger_lengths"])
            if features.get("palm_lines"):
                response.features.palm_lines.update(features["palm_lines"])
            if features.get("measurements"):
                response.features.measurements.update(features["measurements"])
            
            # 填充洞察
            for insight in result.get("insights", []):
                insight_pb = fortune_analysis_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "hand")
                )
                response.insights.append(insight_pb)
            
            # 填充融合洞察
            for insight in result.get("integrated_insights", []):
                insight_pb = fortune_analysis_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "integrated")
                )
                response.integrated_insights.append(insight_pb)
            
            # 填充建议
            response.recommendations.extend(result.get("recommendations", []))
            response.confidence = result.get("confidence", 0.0)
            
            # 完整报告（JSON）
            import json
            response.report_json = json.dumps(result, ensure_ascii=False)
            
            print(f"[{request_time}] ✅ fortune-analysis-service: 手相分析完成", flush=True)
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"手相分析失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ fortune-analysis-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"手相分析失败: {str(e)}")
            response = fortune_analysis_pb2.HandAnalysisResponse()
            response.success = False
            response.error_message = str(e)
            return response

    def AnalyzeFace(self, request: fortune_analysis_pb2.FaceAnalysisRequest, context: grpc.ServicerContext) -> fortune_analysis_pb2.FaceAnalysisResponse:
        """面相分析"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] 📥 fortune-analysis-service: 收到面相分析请求", flush=True)
        
        try:
            # 调用面相分析器（独立模块）
            result = self.face_analyzer.analyze_face(
                image_bytes=request.image.image_bytes,
                image_format=request.image.image_format or "jpg",
                bazi_info=request.bazi_info if request.bazi_info.use_bazi else None
            )
            
            # 构建响应
            response = fortune_analysis_pb2.FaceAnalysisResponse()
            response.success = result.get("success", False)
            
            if not response.success:
                response.error_message = result.get("error", "分析失败")
                return response
            
            # 填充特征
            features = result.get("features", {})
            if features.get("san_ting_ratio"):
                response.features.san_ting_ratio.update(features["san_ting_ratio"])
            if features.get("facial_attributes"):
                response.features.facial_attributes.update(features["facial_attributes"])
            if features.get("feature_measurements"):
                response.features.feature_measurements.update(features["feature_measurements"])
            response.features.special_features.extend(features.get("special_features", []))
            
            # 填充洞察
            for insight in result.get("insights", []):
                insight_pb = fortune_analysis_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "face")
                )
                response.insights.append(insight_pb)
            
            # 填充融合洞察
            for insight in result.get("integrated_insights", []):
                insight_pb = fortune_analysis_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "integrated")
                )
                response.integrated_insights.append(insight_pb)
            
            # 填充建议
            response.recommendations.extend(result.get("recommendations", []))
            response.confidence = result.get("confidence", 0.0)
            
            # 完整报告（JSON）
            import json
            response.report_json = json.dumps(result, ensure_ascii=False)
            
            print(f"[{request_time}] ✅ fortune-analysis-service: 面相分析完成", flush=True)
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"面相分析失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ fortune-analysis-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"面相分析失败: {str(e)}")
            response = fortune_analysis_pb2.FaceAnalysisResponse()
            response.success = False
            response.error_message = str(e)
            return response

    def HealthCheck(self, request: fortune_analysis_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> fortune_analysis_pb2.HealthCheckResponse:
        """健康检查"""
        return fortune_analysis_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9005):
    """启动 gRPC 服务器（支持热更新）"""
    try:
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server,
            register_microservice_reloader
        )
        
        server_options = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
        ]
        
        server, reloader = create_hot_reload_server(
            service_name="fortune_analysis",
            module_path="services.fortune_analysis.grpc_server",
            servicer_class_name="FortuneAnalysisServicer",
            add_servicer_to_server_func=fortune_analysis_pb2_grpc.add_FortuneAnalysisServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=10,
            check_interval=30
        )
        
        register_microservice_reloader("fortune_analysis", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口，不需要再次绑定
        server.start()
        print(f"✅ Fortune Analysis gRPC 服务已启动（热更新已启用），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            print("\n>>> 正在停止服务...")
            reloader.stop()
            server.stop(grace=5)
            print("✅ 服务已停止")
            
    except ImportError:
        # 降级到传统模式
        server_options = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
        ]
        
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=server_options
        )
        fortune_analysis_pb2_grpc.add_FortuneAnalysisServiceServicer_to_server(FortuneAnalysisServicer(), server)
        
        listen_addr = f"[::]:{port}"
        server.add_insecure_port(listen_addr)
        
        server.start()
        print(f"✅ Fortune Analysis gRPC 服务已启动（传统模式），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            print("\n>>> 正在停止服务...")
            server.stop(grace=5)
            print("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Fortune Analysis gRPC 服务")
    parser.add_argument("--port", type=int, default=9005, help="服务端口（默认: 9005）")
    args = parser.parse_args()
    serve(args.port)


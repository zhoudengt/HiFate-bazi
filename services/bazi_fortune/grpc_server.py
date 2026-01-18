#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for bazi-fortune-service.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent import futures
from datetime import datetime

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))
import bazi_fortune_pb2
import bazi_fortune_pb2_grpc

from core.calculators.helpers import compute_local_detail


class BaziFortuneServicer(bazi_fortune_pb2_grpc.BaziFortuneServiceServicer):
    """实现 BaziFortuneService 的 gRPC 服务"""

    def CalculateDayunLiunian(self, request: bazi_fortune_pb2.BaziFortuneRequest, context: grpc.ServicerContext) -> bazi_fortune_pb2.BaziFortuneResponse:
        """计算大运流年"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] 📥 bazi-fortune-service: 收到请求 - solar_date={request.solar_date}, solar_time={request.solar_time}, gender={request.gender}, current_time={request.current_time}", flush=True)
        
        try:
            # 解析当前时间
            current_time = None
            if request.current_time:
                try:
                    current_time = datetime.datetime.fromisoformat(request.current_time)
                except ValueError:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details("current_time 格式错误，应为 ISO 8601 格式")
                    return bazi_fortune_pb2.BaziFortuneResponse()

            detail = compute_local_detail(
                solar_date=request.solar_date,
                solar_time=request.solar_time,
                gender=request.gender,
                current_time=current_time,
            )

            response = bazi_fortune_pb2.BaziFortuneResponse()
            response.detail_json = json.dumps(detail, ensure_ascii=False)
            
            metadata = {
                "service": "bazi-fortune-service",
                "version": "1.0.0",
            }
            response.metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            print(f"[{request_time}] ✅ bazi-fortune-service: 响应已返回", flush=True)
            return response
            
        except ValueError as e:
            print(f"[{request_time}] ❌ bazi-fortune-service: 参数错误 - {str(e)}", flush=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return bazi_fortune_pb2.BaziFortuneResponse()
        except Exception as e:
            import traceback
            error_msg = f"运势计算失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ bazi-fortune-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"运势计算失败: {str(e)}")
            return bazi_fortune_pb2.BaziFortuneResponse()

    def HealthCheck(self, request: bazi_fortune_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> bazi_fortune_pb2.HealthCheckResponse:
        """健康检查"""
        return bazi_fortune_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9002):
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
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
        ]
        
        server, reloader = create_hot_reload_server(
            service_name="bazi_fortune",
            module_path="services.bazi_fortune.grpc_server",
            servicer_class_name="BaziFortuneServicer",
            add_servicer_to_server_func=bazi_fortune_pb2_grpc.add_BaziFortuneServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=20,
            check_interval=30
        )
        
        register_microservice_reloader("bazi_fortune", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口，不需要再次绑定
        server.start()
        print(f"✅ Bazi Fortune gRPC 服务已启动（热更新已启用），监听端口: {port}")
        
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
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
        ]
        
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=20),
            options=server_options
        )
        bazi_fortune_pb2_grpc.add_BaziFortuneServiceServicer_to_server(BaziFortuneServicer(), server)
        
        listen_addr = f"[::]:{port}"
        server.add_insecure_port(listen_addr)
        
        server.start()
        print(f"✅ Bazi Fortune gRPC 服务已启动（传统模式），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            print("\n>>> 正在停止服务...")
            server.stop(grace=5)
            print("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Bazi Fortune gRPC 服务")
    parser.add_argument("--port", type=int, default=9002, help="服务端口（默认: 9002）")
    args = parser.parse_args()
    serve(args.port)


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for bazi-core-service.
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
import bazi_core_pb2
import bazi_core_pb2_grpc

from src.bazi_core.calculator import BaziCoreCalculator


class BaziCoreServicer(bazi_core_pb2_grpc.BaziCoreServiceServicer):
    """实现 BaziCoreService 的 gRPC 服务"""

    def CalculateBazi(self, request: bazi_core_pb2.BaziCoreRequest, context: grpc.ServicerContext) -> bazi_core_pb2.BaziCoreResponse:
        """计算八字排盘"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] 📥 bazi-core-service: 收到请求 - solar_date={request.solar_date}, solar_time={request.solar_time}, gender={request.gender}", flush=True)
        
        try:
            calculator = BaziCoreCalculator(
                solar_date=request.solar_date,
                solar_time=request.solar_time,
                gender=request.gender,
            )
            result = calculator.calculate()
            print(f"[{request_time}] ✅ bazi-core-service: 计算完成", flush=True)
            
            if result is None:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("八字排盘失败")
                return bazi_core_pb2.BaziCoreResponse()

            # 转换结果为 protobuf 格式
            response = bazi_core_pb2.BaziCoreResponse()
            
            # 基本信息（需要特殊处理 lunar_date，它是字典）
            if "basic_info" in result:
                basic_info = result["basic_info"]
                for key, value in basic_info.items():
                    if key == "lunar_date" and isinstance(value, dict):
                        # lunar_date 是字典，需要序列化为 JSON
                        response.basic_info[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        response.basic_info[key] = str(value)
            
            # 四柱信息
            if "bazi_pillars" in result:
                pillars = result["bazi_pillars"]
                for pillar_name, pillar_data in pillars.items():
                    pillar = bazi_core_pb2.Pillar(
                        stem=pillar_data.get("stem", ""),
                        branch=pillar_data.get("branch", "")
                    )
                    if pillar_name == "year":
                        response.year_pillar.CopyFrom(pillar)
                    elif pillar_name == "month":
                        response.month_pillar.CopyFrom(pillar)
                    elif pillar_name == "day":
                        response.day_pillar.CopyFrom(pillar)
                    elif pillar_name == "hour":
                        response.hour_pillar.CopyFrom(pillar)
            
            # 四柱详情
            if "details" in result:
                for pillar_name, detail_data in result["details"].items():
                    detail = bazi_core_pb2.PillarDetail(
                        main_star=detail_data.get("main_star", ""),
                        nayin=detail_data.get("nayin", ""),
                        kongwang=detail_data.get("kongwang", ""),
                    )
                    if "deities" in detail_data:
                        detail.deities.extend(detail_data["deities"])
                    response.details[pillar_name].CopyFrom(detail)
            
            # 十神统计
            if "ten_gods_stats" in result:
                for key, value in result["ten_gods_stats"].items():
                    response.ten_gods_stats[key] = str(value)
            
            # 五行信息
            if "elements" in result:
                for key, value in result["elements"].items():
                    # 使用 json.dumps 而不是 str()，确保格式正确
                    response.elements[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value)
            
            # 五行计数
            if "element_counts" in result:
                for key, value in result["element_counts"].items():
                    response.element_counts[key] = int(value)
            
            # 关系信息
            if "relationships" in result:
                for key, value in result["relationships"].items():
                    response.relationships[key] = str(value)
            
            # 元数据（JSON 字符串）
            metadata = {
                "service": "bazi-core-service",
                "version": "1.0.0",
            }
            response.metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            print(f"[{request_time}] ✅ bazi-core-service: 响应已返回", flush=True)
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"计算失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ bazi-core-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"计算失败: {str(e)}")
            return bazi_core_pb2.BaziCoreResponse()

    def HealthCheck(self, request: bazi_core_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> bazi_core_pb2.HealthCheckResponse:
        """健康检查"""
        return bazi_core_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9001):
    """启动 gRPC 服务器"""
    # 增加线程池大小以处理更多并发请求
    # 配置 keepalive 选项，避免 "Too many pings" 错误
    server_options = [
        ('grpc.keepalive_time_ms', 300000),  # 5分钟
        ('grpc.keepalive_timeout_ms', 20000),  # 20秒
        ('grpc.keepalive_permit_without_calls', False),
        ('grpc.http2.max_pings_without_data', 2),
        ('grpc.http2.min_time_between_pings_ms', 60000),  # 60秒
        ('grpc.http2.min_ping_interval_without_data_ms', 300000),  # 5分钟
    ]
    
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=20),
        options=server_options
    )
    bazi_core_pb2_grpc.add_BaziCoreServiceServicer_to_server(BaziCoreServicer(), server)
    
    listen_addr = f"localhost:{port}"  # 使用 localhost 避免权限问题
    server.add_insecure_port(listen_addr)
    
    server.start()
    print(f"✅ Bazi Core gRPC 服务已启动，监听端口: {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n>>> 正在停止服务...")
        server.stop(grace=5)
        print("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Bazi Core gRPC 服务")
    parser.add_argument("--port", type=int, default=9001, help="服务端口（默认: 9001）")
    args = parser.parse_args()
    serve(args.port)


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for bazi-rule-service.
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
import bazi_rule_pb2
import bazi_rule_pb2_grpc

from core.calculators.BaziCalculator import BaziCalculator


class BaziRuleServicer(bazi_rule_pb2_grpc.BaziRuleServiceServicer):
    """实现 BaziRuleService 的 gRPC 服务"""

    def MatchRules(self, request: bazi_rule_pb2.BaziRuleMatchRequest, context: grpc.ServicerContext) -> bazi_rule_pb2.BaziRuleMatchResponse:
        """匹配规则"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rule_types_str = ", ".join(request.rule_types) if request.rule_types else "全部"
        logger.info(f"[{request_time}] 📥 bazi-rule-service: 收到请求 - solar_date={request.solar_date}, solar_time={request.solar_time}, gender={request.gender}, rule_types=[{rule_types_str}], use_cache={request.use_cache}", flush=True)
        
        try:
            import time
            total_start = time.time()
            
            # 1. 八字计算（使用本地计算，和本地匹配逻辑完全一致）
            calc_start = time.time()
            calculator = BaziCalculator(request.solar_date, request.solar_time, request.gender)
            # 直接本地计算，不调用微服务（避免循环调用和性能问题）
            calculator.calculate()
            calc_time = time.time() - calc_start
            logger.info(f"[{request_time}] ✅ bazi-rule-service: 八字计算完成（耗时 {calc_time:.2f}秒）", flush=True)
            
            # 2. 构建规则输入（和本地匹配逻辑完全一致）
            build_start = time.time()
            bazi_data = calculator.build_rule_input()
            build_time = time.time() - build_start
            
            # 3. 规则匹配（直接使用本地匹配逻辑，和 _match_rules_locally 完全一样）
            # 关键：不调用 calculator.match_rules()，因为它会先尝试调用微服务，导致性能问题
            # 直接调用 RuleService.match_rules()，和本地匹配逻辑完全一致
            match_start = time.time()
            rule_types = list(request.rule_types) if request.rule_types else None
            # 强制启用缓存，除非明确指定 use_cache=False
            use_cache_optimized = request.use_cache if request.use_cache is False else True
            
            # 直接调用 RuleService.match_rules，和本地匹配逻辑完全一致
            from server.services.rule_service import RuleService
            matched = RuleService.match_rules(
                bazi_data,
                rule_types=rule_types,
                use_cache=use_cache_optimized
            )
            
            # 获取未匹配的规则（和本地匹配逻辑一致）
            engine = RuleService.get_engine()
            all_rules = [r for r in engine.rules if r.get('enabled', True)]
            if rule_types:
                rule_types_set = set(rule_types)
                all_rules = [r for r in all_rules if r.get('rule_type') in rule_types_set]
            matched_rule_ids = {r.get('rule_id') or r.get('rule_code') for r in matched if isinstance(r, dict)}
            unmatched = [r for r in all_rules if (r.get('rule_id') or r.get('rule_code')) not in matched_rule_ids]
            
            match_time = time.time() - match_start
            logger.info(f"[{request_time}] ✅ bazi-rule-service: 规则匹配完成 - 匹配 {len(matched)} 条，未匹配 {len(unmatched)} 条（耗时 {match_time:.2f}秒，构建 {build_time:.2f}秒，缓存={use_cache_optimized}）", flush=True)

            # 将对象转换为可序列化的 dict（优化：只序列化必要字段，减少数据量）
            matched_serializable = []
            for rule in matched:
                if isinstance(rule, dict):
                    # 只保留必要字段，减少序列化数据量
                    rule_dict = {
                        'rule_id': rule.get('rule_id'),
                        'rule_code': rule.get('rule_code'),
                        'rule_name': rule.get('rule_name'),
                        'rule_type': rule.get('rule_type'),
                        'content': rule.get('content'),
                        'priority': rule.get('priority'),
                    }
                    matched_serializable.append(rule_dict)
                else:
                    matched_serializable.append(dict(rule) if hasattr(rule, '__dict__') else {})
            
            # 优化：不返回 unmatched 数据，减少响应大小
            # unmatched 数据通常很大（436条），但客户端通常只需要 matched 数据
            unmatched_serializable = []
            # 如果需要 unmatched 数据，可以后续通过单独的接口获取
            # 这里只返回一个统计信息
            unmatched_count = len(unmatched)
            
            # 优化：减少 context 数据量（只保留匹配的规则）
            context_optimized = {}
            if isinstance(calculator.last_rule_context, dict):
                # 只保留匹配规则的 context
                matched_rule_ids = {rule.get('rule_id') or rule.get('rule_code') for rule in matched if isinstance(rule, dict)}
                for rule_id, context_value in calculator.last_rule_context.items():
                    if rule_id in matched_rule_ids:
                        context_optimized[rule_id] = context_value

            response = bazi_rule_pb2.BaziRuleMatchResponse()
            
            # 序列化前记录时间
            serialize_start = datetime.datetime.now()
            matched_json_str = json.dumps(matched_serializable, ensure_ascii=False, default=str)
            # unmatched_json_str 不再需要，因为只返回 count
            context_json_str = json.dumps(context_optimized, ensure_ascii=False, default=str)
            serialize_end = datetime.datetime.now()
            serialize_time = (serialize_end - serialize_start).total_seconds()
            
            # 记录响应数据大小
            matched_size = len(matched_json_str.encode('utf-8'))
            unmatched_size = 0  # 不再返回 unmatched 数据
            context_size = len(context_json_str.encode('utf-8'))
            total_size = matched_size + unmatched_size + context_size
            
            response.matched_json = matched_json_str
            # 只返回 unmatched 数量，不返回完整数据
            response.unmatched_json = json.dumps({'count': unmatched_count}, ensure_ascii=False)
            response.context_json = context_json_str
            
            metadata = {
                "service": "bazi-rule-service",
                "version": "1.0.0",
            }
            response.metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            total_time = time.time() - total_start
            logger.info(f"[{request_time}] ✅ bazi-rule-service: 响应已返回（总耗时 {total_time:.2f}秒，计算 {calc_time:.2f}秒，匹配 {match_time:.2f}秒，序列化 {serialize_time:.2f}秒，响应大小: matched={matched_size/1024/1024:.2f}MB, unmatched={unmatched_size/1024/1024:.2f}MB, context={context_size/1024/1024:.2f}MB, 总计={total_size/1024/1024:.2f}MB）", flush=True)
            
            # 强制刷新输出，确保日志及时写入
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
            
            return response
            
        except ValueError as e:
            logger.info(f"[{request_time}] ❌ bazi-rule-service: 参数错误 - {str(e)}", flush=True)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return bazi_rule_pb2.BaziRuleMatchResponse()
        except Exception as e:
            import traceback
            error_msg = f"规则匹配失败: {str(e)}\n{traceback.format_exc()}"
            logger.info(f"[{request_time}] ❌ bazi-rule-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"规则匹配失败: {str(e)}")
            return bazi_rule_pb2.BaziRuleMatchResponse()

    def HealthCheck(self, request: bazi_rule_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> bazi_rule_pb2.HealthCheckResponse:
        """健康检查"""
        return bazi_rule_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9004):
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
            # 增加消息大小限制（默认4MB，增加到50MB以支持大量规则）
            ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
        ]
        
        server, reloader = create_hot_reload_server(
            service_name="bazi_rule",
            module_path="services.bazi_rule.grpc_server",
            servicer_class_name="BaziRuleServicer",
            add_servicer_to_server_func=bazi_rule_pb2_grpc.add_BaziRuleServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=20,
            check_interval=30
        )
        
        register_microservice_reloader("bazi_rule", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口，不需要再次绑定
        server.start()
        logger.info(f"✅ Bazi Rule gRPC 服务已启动（热更新已启用），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            reloader.stop()
            server.stop(grace=5)
            logger.info("✅ 服务已停止")
            
    except ImportError:
        # 降级到传统模式
        server_options = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
        ]
        
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=20),
            options=server_options
        )
        bazi_rule_pb2_grpc.add_BaziRuleServiceServicer_to_server(BaziRuleServicer(), server)
        
        listen_addr = f"[::]:{port}"
        server.add_insecure_port(listen_addr)
        
        server.start()
        logger.info(f"✅ Bazi Rule gRPC 服务已启动（传统模式），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            server.stop(grace=5)
            logger.info("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Bazi Rule gRPC 服务")
    parser.add_argument("--port", type=int, default=9004, help="服务端口（默认: 9004）")
    args = parser.parse_args()
    serve(args.port)


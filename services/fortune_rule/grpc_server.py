#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for fortune-rule-service.
面相手相规则匹配和八字融合分析服务
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
import fortune_rule_pb2
import fortune_rule_pb2_grpc

from services.fortune_rule.rule_engine import FortuneRuleEngine


class FortuneRuleServicer(fortune_rule_pb2_grpc.FortuneRuleServiceServicer):
    """实现 FortuneRuleService 的 gRPC 服务"""

    def __init__(self):
        self.rule_engine = FortuneRuleEngine()

    def MatchHandRules(self, request: fortune_rule_pb2.HandRuleMatchRequest, context: grpc.ServicerContext) -> fortune_rule_pb2.RuleMatchResponse:
        """手相规则匹配和八字融合"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{request_time}] 📥 fortune-rule-service: 收到手相规则匹配请求", flush=True)
        logger.info(f"[{request_time}] 📋 请求详情:", flush=True)
        logger.info(f"  手相特征: hand_shape={request.hand_features.hand_shape if request.hand_features else 'N/A'}", flush=True)
        logger.info(f"  八字信息: use_bazi={request.bazi_info.use_bazi if request.bazi_info else False}, date={request.bazi_info.solar_date if request.bazi_info else 'N/A'}", flush=True)
        
        try:
            # 转换手相特征
            hand_features = {}
            if request.hand_features:
                # 安全地转换 map 字段
                finger_lengths = {}
                for k, v in request.hand_features.finger_lengths.items():
                    finger_lengths[str(k)] = str(v)
                
                finger_ratios = {}
                for k, v in request.hand_features.finger_ratios.items():
                    finger_ratios[str(k)] = float(v)
                
                palm_lines = {}
                for k, v in request.hand_features.palm_lines.items():
                    palm_lines[str(k)] = str(v)
                
                measurements = {}
                for k, v in request.hand_features.measurements.items():
                    measurements[str(k)] = float(v)
                
                finger_thickness = {}
                for k, v in request.hand_features.finger_thickness.items():
                    finger_thickness[str(k)] = float(v)
                
                palm_texture = {}
                for k, v in request.hand_features.palm_texture.items():
                    palm_texture[str(k)] = str(v)
                
                hand_features = {
                    "hand_shape": request.hand_features.hand_shape,
                    "hand_shape_ratio": float(request.hand_features.hand_shape_ratio),
                    "hand_shape_confidence": float(request.hand_features.hand_shape_confidence),
                    "finger_lengths": finger_lengths,
                    "finger_ratios": finger_ratios,
                    "palm_lines": palm_lines,
                    "measurements": measurements,
                    "finger_thickness": finger_thickness,
                    "palm_texture": palm_texture,
                    "special_marks": [json.loads(m) if isinstance(m, str) and m.startswith('{') else m for m in request.hand_features.special_marks],
                    "hand_orientation": request.hand_features.hand_orientation
                }
            
            # 转换八字数据
            bazi_data = None
            if request.bazi_data and request.bazi_data.element_counts:
                # 安全地转换 map 字段
                element_counts = {}
                for k, v in request.bazi_data.element_counts.items():
                    element_counts[str(k)] = int(v)
                
                ten_gods_stats = {}
                for k, v in request.bazi_data.ten_gods_stats.items():
                    ten_gods_stats[str(k)] = int(v)
                
                bazi_data = {
                    "element_counts": element_counts,
                    "ten_gods_stats": ten_gods_stats,
                    "bazi_pillars": json.loads(request.bazi_data.bazi_pillars) if request.bazi_data.bazi_pillars else {},
                    "metadata_json": request.bazi_data.metadata_json
                }
                # 如果 metadata_json 存在，解析完整数据
                if bazi_data.get("metadata_json"):
                    try:
                        metadata = json.loads(bazi_data["metadata_json"])
                        bazi_data.update(metadata)
                    except:
                        pass
            
            # 如果提供了八字信息但还没有八字数据，需要获取
            if request.bazi_info and request.bazi_info.use_bazi and not bazi_data:
                logger.info(f"[{request_time}] 📥 开始获取八字数据...", flush=True)
                logger.info(f"[{request_time}]   日期: {request.bazi_info.solar_date}, 时间: {request.bazi_info.solar_time}, 性别: {request.bazi_info.gender}", flush=True)
                bazi_data = self._get_bazi_data(
                    request.bazi_info.solar_date,
                    request.bazi_info.solar_time,
                    request.bazi_info.gender
                )
                if bazi_data:
                    logger.info(f"[{request_time}] ✅ 八字数据获取成功", flush=True)
                    logger.info(f"[{request_time}]   五行统计: {bazi_data.get('element_counts', {})}", flush=True)
                    logger.info(f"[{request_time}]   十神统计: {bazi_data.get('ten_gods_stats', {})}", flush=True)
                else:
                    logger.info(f"[{request_time}] ⚠️  八字数据获取失败", flush=True)
            
            # 1. 手相规则匹配
            logger.info(f"[{request_time}] 🔍 开始手相规则匹配...", flush=True)
            hand_insights = self.rule_engine.match_hand_rules(hand_features)
            logger.info(f"[{request_time}] ✅ 手相规则匹配完成，匹配到 {len(hand_insights)} 条规则", flush=True)
            
            # 2. 八字融合分析
            logger.info(f"[{request_time}] 🔍 开始八字融合分析...", flush=True)
            integrated_insights = []
            if bazi_data:
                logger.info(f"[{request_time}] 📊 八字数据已获取，开始融合分析", flush=True)
                integrated_insights = self.rule_engine.integrate_with_bazi(
                    hand_features,
                    None,  # 面相特征（手相分析时为空）
                    bazi_data
                )
                logger.info(f"[{request_time}] ✅ 八字融合分析完成，匹配到 {len(integrated_insights)} 条融合规则", flush=True)
            else:
                logger.info(f"[{request_time}] ⚠️  八字数据为空，跳过融合分析", flush=True)
            
            # 3. 生成建议
            recommendations = self.rule_engine.generate_recommendations(
                hand_insights,
                [],  # 面相洞察（手相分析时为空）
                integrated_insights
            )
            
            # 构建响应
            response = fortune_rule_pb2.RuleMatchResponse()
            response.success = True
            
            # 填充手相洞察
            for insight in hand_insights:
                insight_pb = fortune_rule_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "hand"),
                    feature=insight.get("feature", "")
                )
                response.hand_insights.append(insight_pb)
            
            # 填充融合洞察
            for insight in integrated_insights:
                insight_pb = fortune_rule_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "integrated"),
                    feature=insight.get("feature", "")
                )
                response.integrated_insights.append(insight_pb)
            
            # 填充建议
            response.recommendations.extend(recommendations)
            
            # 填充八字数据（如果获取了）
            if bazi_data:
                bazi_data_pb = fortune_rule_pb2.BaziData()
                # 安全地填充 element_counts（确保值是 int）
                element_counts = bazi_data.get("element_counts", {})
                for k, v in element_counts.items():
                    try:
                        bazi_data_pb.element_counts[str(k)] = int(v)
                    except (ValueError, TypeError):
                        pass
                # 安全地填充 ten_gods_stats
                # 注意：ten_gods_stats 可能是复杂结构，不是简单的 map<string, int32>
                # 如果它是字符串（JSON），则解析；如果是字典，尝试转换
                ten_gods_stats = bazi_data.get("ten_gods_stats", {})
                if isinstance(ten_gods_stats, str):
                    try:
                        ten_gods_stats = json.loads(ten_gods_stats)
                    except:
                        ten_gods_stats = {}
                
                # 如果 ten_gods_stats 是字典，尝试提取简单的键值对
                # 但 protobuf 定义是 map<string, int32>，所以只能存储简单的整数统计
                # 复杂结构存储在 metadata_json 中
                if isinstance(ten_gods_stats, dict):
                    # 只存储简单的整数统计，跳过复杂结构
                    for k, v in ten_gods_stats.items():
                        try:
                            # 如果值是整数，直接存储
                            if isinstance(v, int):
                                bazi_data_pb.ten_gods_stats[str(k)] = v
                            # 如果值是字符串且可以转换为整数，存储
                            elif isinstance(v, str) and v.isdigit():
                                bazi_data_pb.ten_gods_stats[str(k)] = int(v)
                        except (ValueError, TypeError):
                            pass
                # 安全地填充 bazi_pillars（map<string, string>）
                bazi_pillars = bazi_data.get("bazi_pillars", {})
                if isinstance(bazi_pillars, str):
                    try:
                        bazi_pillars = json.loads(bazi_pillars)
                    except:
                        bazi_pillars = {}
                
                if isinstance(bazi_pillars, dict):
                    for k, v in bazi_pillars.items():
                        # 如果值是字典或其他复杂结构，转为 JSON 字符串
                        if isinstance(v, (dict, list)):
                            bazi_data_pb.bazi_pillars[str(k)] = json.dumps(v, ensure_ascii=False)
                        else:
                            bazi_data_pb.bazi_pillars[str(k)] = str(v)
                
                bazi_data_pb.metadata_json = json.dumps(bazi_data, ensure_ascii=False)
                response.bazi_data.CopyFrom(bazi_data_pb)
            
            logger.info(f"[{request_time}] ✅ fortune-rule-service: 手相规则匹配完成", flush=True)
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"手相规则匹配失败: {str(e)}\n{traceback.format_exc()}"
            logger.info(f"[{request_time}] ❌ fortune-rule-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"手相规则匹配失败: {str(e)}")
            response = fortune_rule_pb2.RuleMatchResponse()
            response.success = False
            response.error_message = str(e)
            return response

    def MatchFaceRules(self, request: fortune_rule_pb2.FaceRuleMatchRequest, context: grpc.ServicerContext) -> fortune_rule_pb2.RuleMatchResponse:
        """面相规则匹配和八字融合"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{request_time}] 📥 fortune-rule-service: 收到面相规则匹配请求", flush=True)
        logger.info(f"[{request_time}] 📋 请求详情:", flush=True)
        logger.info(f"  面相特征: san_ting={dict(request.face_features.san_ting_ratio) if request.face_features else 'N/A'}", flush=True)
        logger.info(f"  八字信息: use_bazi={request.bazi_info.use_bazi if request.bazi_info else False}, date={request.bazi_info.solar_date if request.bazi_info else 'N/A'}", flush=True)
        
        try:
            # 转换面相特征
            face_features = {}
            if request.face_features:
                # 安全地转换 map 字段
                san_ting_ratio = {}
                for k, v in request.face_features.san_ting_ratio.items():
                    san_ting_ratio[str(k)] = float(v)
                
                facial_attributes = {}
                for k, v in request.face_features.facial_attributes.items():
                    facial_attributes[str(k)] = str(v)
                
                feature_measurements = {}
                for k, v in request.face_features.feature_measurements.items():
                    feature_measurements[str(k)] = float(v)
                
                face_features = {
                    "san_ting_ratio": san_ting_ratio,
                    "facial_attributes": facial_attributes,
                    "feature_measurements": feature_measurements,
                    "special_features": [str(f) for f in request.face_features.special_features]
                }
            
            # 转换八字数据
            bazi_data = None
            if request.bazi_data and request.bazi_data.element_counts:
                # 安全地转换 map 字段
                element_counts = {}
                for k, v in request.bazi_data.element_counts.items():
                    element_counts[str(k)] = int(v)
                
                ten_gods_stats = {}
                for k, v in request.bazi_data.ten_gods_stats.items():
                    ten_gods_stats[str(k)] = int(v)
                
                bazi_data = {
                    "element_counts": element_counts,
                    "ten_gods_stats": ten_gods_stats,
                    "bazi_pillars": json.loads(request.bazi_data.bazi_pillars) if request.bazi_data.bazi_pillars else {},
                    "metadata_json": request.bazi_data.metadata_json
                }
                # 如果 metadata_json 存在，解析完整数据
                if bazi_data.get("metadata_json"):
                    try:
                        metadata = json.loads(bazi_data["metadata_json"])
                        bazi_data.update(metadata)
                    except:
                        pass
            
            # 如果提供了八字信息但还没有八字数据，需要获取
            if request.bazi_info and request.bazi_info.use_bazi and not bazi_data:
                logger.info(f"[{request_time}] 📥 开始获取八字数据...", flush=True)
                logger.info(f"[{request_time}]   日期: {request.bazi_info.solar_date}, 时间: {request.bazi_info.solar_time}, 性别: {request.bazi_info.gender}", flush=True)
                bazi_data = self._get_bazi_data(
                    request.bazi_info.solar_date,
                    request.bazi_info.solar_time,
                    request.bazi_info.gender
                )
                if bazi_data:
                    logger.info(f"[{request_time}] ✅ 八字数据获取成功", flush=True)
                    logger.info(f"[{request_time}]   五行统计: {bazi_data.get('element_counts', {})}", flush=True)
                    logger.info(f"[{request_time}]   十神统计: {bazi_data.get('ten_gods_stats', {})}", flush=True)
                else:
                    logger.info(f"[{request_time}] ⚠️  八字数据获取失败", flush=True)
            
            # 1. 面相规则匹配
            logger.info(f"[{request_time}] 🔍 开始面相规则匹配...", flush=True)
            face_insights = self.rule_engine.match_face_rules(face_features)
            logger.info(f"[{request_time}] ✅ 面相规则匹配完成，匹配到 {len(face_insights)} 条规则", flush=True)
            
            # 2. 八字融合分析
            logger.info(f"[{request_time}] 🔍 开始八字融合分析...", flush=True)
            integrated_insights = []
            if bazi_data:
                logger.info(f"[{request_time}] 📊 八字数据已获取，开始融合分析", flush=True)
                integrated_insights = self.rule_engine.integrate_with_bazi(
                    None,  # 手相特征（面相分析时为空）
                    face_features,
                    bazi_data
                )
                logger.info(f"[{request_time}] ✅ 八字融合分析完成，匹配到 {len(integrated_insights)} 条融合规则", flush=True)
            else:
                logger.info(f"[{request_time}] ⚠️  八字数据为空，跳过融合分析", flush=True)
            
            # 3. 生成建议
            recommendations = self.rule_engine.generate_recommendations(
                [],  # 手相洞察（面相分析时为空）
                face_insights,
                integrated_insights
            )
            
            # 构建响应
            response = fortune_rule_pb2.RuleMatchResponse()
            response.success = True
            
            # 填充面相洞察
            for insight in face_insights:
                insight_pb = fortune_rule_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "face"),
                    feature=insight.get("feature", "")
                )
                response.face_insights.append(insight_pb)
            
            # 填充融合洞察
            for insight in integrated_insights:
                insight_pb = fortune_rule_pb2.AnalysisInsight(
                    category=insight.get("category", ""),
                    content=insight.get("content", ""),
                    confidence=insight.get("confidence", 0.0),
                    source=insight.get("source", "integrated"),
                    feature=insight.get("feature", "")
                )
                response.integrated_insights.append(insight_pb)
            
            # 填充建议
            response.recommendations.extend(recommendations)
            
            # 填充八字数据（如果获取了）
            if bazi_data:
                bazi_data_pb = fortune_rule_pb2.BaziData()
                # 安全地填充 element_counts（确保值是 int）
                element_counts = bazi_data.get("element_counts", {})
                for k, v in element_counts.items():
                    try:
                        bazi_data_pb.element_counts[str(k)] = int(v)
                    except (ValueError, TypeError):
                        pass
                # 安全地填充 ten_gods_stats
                # 注意：ten_gods_stats 可能是复杂结构，不是简单的 map<string, int32>
                # 如果它是字符串（JSON），则解析；如果是字典，尝试转换
                ten_gods_stats = bazi_data.get("ten_gods_stats", {})
                if isinstance(ten_gods_stats, str):
                    try:
                        ten_gods_stats = json.loads(ten_gods_stats)
                    except:
                        ten_gods_stats = {}
                
                # 如果 ten_gods_stats 是字典，尝试提取简单的键值对
                # 但 protobuf 定义是 map<string, int32>，所以只能存储简单的整数统计
                # 复杂结构存储在 metadata_json 中
                if isinstance(ten_gods_stats, dict):
                    # 只存储简单的整数统计，跳过复杂结构
                    for k, v in ten_gods_stats.items():
                        try:
                            # 如果值是整数，直接存储
                            if isinstance(v, int):
                                bazi_data_pb.ten_gods_stats[str(k)] = v
                            # 如果值是字符串且可以转换为整数，存储
                            elif isinstance(v, str) and v.isdigit():
                                bazi_data_pb.ten_gods_stats[str(k)] = int(v)
                        except (ValueError, TypeError):
                            pass
                # 安全地填充 bazi_pillars（map<string, string>）
                bazi_pillars = bazi_data.get("bazi_pillars", {})
                if isinstance(bazi_pillars, str):
                    try:
                        bazi_pillars = json.loads(bazi_pillars)
                    except:
                        bazi_pillars = {}
                
                if isinstance(bazi_pillars, dict):
                    for k, v in bazi_pillars.items():
                        # 如果值是字典或其他复杂结构，转为 JSON 字符串
                        if isinstance(v, (dict, list)):
                            bazi_data_pb.bazi_pillars[str(k)] = json.dumps(v, ensure_ascii=False)
                        else:
                            bazi_data_pb.bazi_pillars[str(k)] = str(v)
                
                bazi_data_pb.metadata_json = json.dumps(bazi_data, ensure_ascii=False)
                response.bazi_data.CopyFrom(bazi_data_pb)
            
            logger.info(f"[{request_time}] ✅ fortune-rule-service: 面相规则匹配完成", flush=True)
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"面相规则匹配失败: {str(e)}\n{traceback.format_exc()}"
            logger.info(f"[{request_time}] ❌ fortune-rule-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"面相规则匹配失败: {str(e)}")
            response = fortune_rule_pb2.RuleMatchResponse()
            response.success = False
            response.error_message = str(e)
            return response

    def HealthCheck(self, request: fortune_rule_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> fortune_rule_pb2.HealthCheckResponse:
        """健康检查"""
        return fortune_rule_pb2.HealthCheckResponse(status="ok")
    
    def _get_bazi_data(self, solar_date: str, solar_time: str, gender: str):
        """获取八字数据"""
        try:
            # 优先使用 BaziService
            try:
                from server.services.bazi_service import BaziService
                bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
                
                if bazi_result and isinstance(bazi_result, dict):
                    # 如果返回的数据有 "bazi" 字段，使用它；否则直接使用返回的数据
                    if "bazi" in bazi_result:
                        bazi_data = bazi_result["bazi"]
                    else:
                        bazi_data = bazi_result
                    
                    # 确保 element_counts 和 ten_gods_stats 是字典类型
                    # 如果它们是字符串（JSON），则解析它们
                    if isinstance(bazi_data.get("element_counts"), str):
                        try:
                            bazi_data["element_counts"] = json.loads(bazi_data["element_counts"])
                        except:
                            bazi_data["element_counts"] = {}
                    
                    if isinstance(bazi_data.get("ten_gods_stats"), str):
                        try:
                            bazi_data["ten_gods_stats"] = json.loads(bazi_data["ten_gods_stats"])
                        except:
                            bazi_data["ten_gods_stats"] = {}
                    
                    # 确保 element_counts 的值是整数
                    if isinstance(bazi_data.get("element_counts"), dict):
                        element_counts = {}
                        for k, v in bazi_data["element_counts"].items():
                            try:
                                element_counts[str(k)] = int(v)
                            except (ValueError, TypeError):
                                pass
                        bazi_data["element_counts"] = element_counts
                    
                    # ten_gods_stats 可能是复杂结构，保持原样（在填充 protobuf 时处理）
                    return bazi_data
            except ImportError:
                pass
            except Exception as e:
                logger.info(f"⚠️  BaziService 调用失败: {e}")
            
            # 降级方案：使用 BaziCoreClient
            try:
                from shared.clients.bazi_core_client_grpc import BaziCoreClient
                client = BaziCoreClient()
                bazi_result = client.calculate_bazi(solar_date, solar_time, gender)
                
                # 确保 element_counts 的值是整数
                element_counts = {}
                for k, v in bazi_result.get("element_counts", {}).items():
                    try:
                        element_counts[str(k)] = int(v)
                    except (ValueError, TypeError):
                        pass
                
                return {
                    "basic_info": bazi_result.get("basic_info", {}),
                    "bazi_pillars": bazi_result.get("bazi_pillars", {}),
                    "element_counts": element_counts,
                    "ten_gods_stats": bazi_result.get("ten_gods_stats", {}),
                    "elements": bazi_result.get("elements", {})
                }
            except Exception as e:
                logger.info(f"⚠️  BaziCoreClient 调用失败: {e}")
                return None
                
        except Exception as e:
            logger.info(f"⚠️  获取八字数据失败: {e}")
            return None


def serve(port: int = 9007):
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
            service_name="fortune_rule",
            module_path="services.fortune_rule.grpc_server",
            servicer_class_name="FortuneRuleServicer",
            add_servicer_to_server_func=fortune_rule_pb2_grpc.add_FortuneRuleServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=10,
            check_interval=30
        )
        
        register_microservice_reloader("fortune_rule", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口，不需要再次绑定
        server.start()
        logger.info(f"✅ Fortune Rule gRPC 服务已启动（热更新已启用），监听端口: {port}")
        
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
        ]
        
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=server_options
        )
        fortune_rule_pb2_grpc.add_FortuneRuleServiceServicer_to_server(FortuneRuleServicer(), server)
        
        listen_addr = f"[::]:{port}"
        server.add_insecure_port(listen_addr)
        
        server.start()
        logger.info(f"✅ Fortune Rule gRPC 服务已启动（传统模式），监听端口: {port}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("\n>>> 正在停止服务...")
            server.stop(grace=5)
            logger.info("✅ 服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动 Fortune Rule gRPC 服务")
    parser.add_argument("--port", type=int, default=9007, help="服务端口（默认: 9007）")
    args = parser.parse_args()
    serve(args.port)


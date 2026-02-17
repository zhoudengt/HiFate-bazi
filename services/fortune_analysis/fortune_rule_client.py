#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fortune Rule Service gRPC Client
面相手相规则匹配服务客户端
"""

import json
import logging

logger = logging.getLogger(__name__)
import os
import sys
from typing import Dict, Any, List, Optional

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))
import fortune_rule_pb2
import fortune_rule_pb2_grpc


class FortuneRuleClient:
    """Fortune Rule Service 客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化客户端
        
        Args:
            base_url: gRPC 服务地址，格式：host:port，默认从环境变量获取
        """
        if base_url:
            self.base_url = base_url
        else:
            # 从环境变量获取
            self.base_url = os.getenv("FORTUNE_RULE_SERVICE_URL", "127.0.0.1:9004")  # 已合并到 rule-engine
    
    def match_hand_rules(
        self,
        hand_features: Dict[str, Any],
        bazi_info: Optional[Dict[str, Any]] = None,
        bazi_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        手相规则匹配和八字融合
        
        Args:
            hand_features: 手相特征
            bazi_info: 八字信息（可选）
            bazi_data: 八字数据（可选，如果已获取）
        
        Returns:
            dict: 包含 insights, integrated_insights, recommendations, bazi_data
        """
        try:
            with grpc.insecure_channel(self.base_url) as channel:
                stub = fortune_rule_pb2_grpc.FortuneRuleServiceStub(channel)
                
                # 构建请求
                request = fortune_rule_pb2.HandRuleMatchRequest()
                
                # 填充手相特征
                if hand_features:
                    request.hand_features.hand_shape = str(hand_features.get("hand_shape", ""))
                    request.hand_features.hand_shape_ratio = float(hand_features.get("hand_shape_ratio", 0.0))
                    request.hand_features.hand_shape_confidence = float(hand_features.get("hand_shape_confidence", 0.5))
                    
                    # 填充字典字段（需要确保值是字符串类型）
                    finger_lengths = hand_features.get("finger_lengths", {})
                    if isinstance(finger_lengths, dict):
                        for k, v in finger_lengths.items():
                            request.hand_features.finger_lengths[str(k)] = str(v)
                    
                    finger_ratios = hand_features.get("finger_ratios", {})
                    if isinstance(finger_ratios, dict):
                        for k, v in finger_ratios.items():
                            request.hand_features.finger_ratios[str(k)] = float(v) if isinstance(v, (int, float)) else 0.0
                    
                    palm_lines = hand_features.get("palm_lines", {})
                    if isinstance(palm_lines, dict):
                        for k, v in palm_lines.items():
                            request.hand_features.palm_lines[str(k)] = str(v)
                    
                    measurements = hand_features.get("measurements", {})
                    if isinstance(measurements, dict):
                        for k, v in measurements.items():
                            request.hand_features.measurements[str(k)] = float(v) if isinstance(v, (int, float)) else 0.0
                    
                    finger_thickness = hand_features.get("finger_thickness", {})
                    if isinstance(finger_thickness, dict):
                        for k, v in finger_thickness.items():
                            request.hand_features.finger_thickness[str(k)] = float(v) if isinstance(v, (int, float)) else 0.0
                    
                    palm_texture = hand_features.get("palm_texture", {})
                    if isinstance(palm_texture, dict):
                        for k, v in palm_texture.items():
                            request.hand_features.palm_texture[str(k)] = str(v)
                    
                    # 特殊标记转为 JSON 字符串
                    for mark in hand_features.get("special_marks", []):
                        if isinstance(mark, dict):
                            request.hand_features.special_marks.append(json.dumps(mark, ensure_ascii=False))
                        else:
                            request.hand_features.special_marks.append(str(mark))
                    request.hand_features.hand_orientation = str(hand_features.get("hand_orientation", ""))
                
                # 填充八字信息
                if bazi_info:
                    request.bazi_info.solar_date = bazi_info.get("solar_date", "")
                    request.bazi_info.solar_time = bazi_info.get("solar_time", "")
                    request.bazi_info.gender = bazi_info.get("gender", "")
                    request.bazi_info.use_bazi = bazi_info.get("use_bazi", False)
                
                # 填充八字数据（如果已获取）
                if bazi_data:
                    request.bazi_data.element_counts.update(bazi_data.get("element_counts", {}))
                    request.bazi_data.ten_gods_stats.update(bazi_data.get("ten_gods_stats", {}))
                    request.bazi_data.bazi_pillars = json.dumps(bazi_data.get("bazi_pillars", {}), ensure_ascii=False)
                    request.bazi_data.metadata_json = json.dumps(bazi_data, ensure_ascii=False)
                
                # 调用服务
                response = stub.MatchHandRules(request, timeout=30.0)
                
                if not response.success:
                    return {
                        "success": False,
                        "error": response.error_message,
                        "insights": [],
                        "integrated_insights": [],
                        "recommendations": [],
                        "bazi_data": None
                    }
                
                # 转换响应
                hand_insights = []
                for insight_pb in response.hand_insights:
                    hand_insights.append({
                        "category": insight_pb.category,
                        "content": insight_pb.content,
                        "confidence": insight_pb.confidence,
                        "source": insight_pb.source,
                        "feature": insight_pb.feature
                    })
                
                integrated_insights = []
                for insight_pb in response.integrated_insights:
                    integrated_insights.append({
                        "category": insight_pb.category,
                        "content": insight_pb.content,
                        "confidence": insight_pb.confidence,
                        "source": insight_pb.source,
                        "feature": insight_pb.feature
                    })
                
                # 解析八字数据
                result_bazi_data = None
                if response.bazi_data and response.bazi_data.element_counts:
                    try:
                        result_bazi_data = json.loads(response.bazi_data.metadata_json) if response.bazi_data.metadata_json else {
                            "element_counts": dict(response.bazi_data.element_counts),
                            "ten_gods_stats": dict(response.bazi_data.ten_gods_stats),
                            "bazi_pillars": json.loads(response.bazi_data.bazi_pillars) if response.bazi_data.bazi_pillars else {}
                        }
                    except:
                        result_bazi_data = {
                            "element_counts": dict(response.bazi_data.element_counts),
                            "ten_gods_stats": dict(response.bazi_data.ten_gods_stats),
                            "bazi_pillars": json.loads(response.bazi_data.bazi_pillars) if response.bazi_data.bazi_pillars else {}
                        }
                
                return {
                    "success": True,
                    "insights": hand_insights,
                    "integrated_insights": integrated_insights,
                    "recommendations": list(response.recommendations),
                    "bazi_data": result_bazi_data
                }
                
        except Exception as e:
            import traceback
            error_msg = f"调用 fortune-rule-service 失败: {str(e)}\n{traceback.format_exc()}"
            logger.info(f"❌ {error_msg}")
            return {
                "success": False,
                "error": str(e),
                "insights": [],
                "integrated_insights": [],
                "recommendations": [],
                "bazi_data": None
            }
    
    def match_face_rules(
        self,
        face_features: Dict[str, Any],
        bazi_info: Optional[Dict[str, Any]] = None,
        bazi_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        面相规则匹配和八字融合
        
        Args:
            face_features: 面相特征
            bazi_info: 八字信息（可选）
            bazi_data: 八字数据（可选，如果已获取）
        
        Returns:
            dict: 包含 insights, integrated_insights, recommendations, bazi_data
        """
        try:
            with grpc.insecure_channel(self.base_url) as channel:
                stub = fortune_rule_pb2_grpc.FortuneRuleServiceStub(channel)
                
                # 构建请求
                request = fortune_rule_pb2.FaceRuleMatchRequest()
                
                # 填充面相特征
                if face_features:
                    san_ting_ratio = face_features.get("san_ting_ratio", {})
                    if isinstance(san_ting_ratio, dict):
                        for k, v in san_ting_ratio.items():
                            request.face_features.san_ting_ratio[str(k)] = float(v) if isinstance(v, (int, float)) else 0.0
                    
                    facial_attributes = face_features.get("facial_attributes", {})
                    if isinstance(facial_attributes, dict):
                        for k, v in facial_attributes.items():
                            request.face_features.facial_attributes[str(k)] = str(v)
                    
                    feature_measurements = face_features.get("feature_measurements", {})
                    if isinstance(feature_measurements, dict):
                        for k, v in feature_measurements.items():
                            request.face_features.feature_measurements[str(k)] = float(v) if isinstance(v, (int, float)) else 0.0
                    
                    special_features = face_features.get("special_features", [])
                    if isinstance(special_features, list):
                        request.face_features.special_features.extend([str(f) for f in special_features])
                
                # 填充八字信息
                if bazi_info:
                    request.bazi_info.solar_date = bazi_info.get("solar_date", "")
                    request.bazi_info.solar_time = bazi_info.get("solar_time", "")
                    request.bazi_info.gender = bazi_info.get("gender", "")
                    request.bazi_info.use_bazi = bazi_info.get("use_bazi", False)
                
                # 填充八字数据（如果已获取）
                if bazi_data:
                    request.bazi_data.element_counts.update(bazi_data.get("element_counts", {}))
                    request.bazi_data.ten_gods_stats.update(bazi_data.get("ten_gods_stats", {}))
                    request.bazi_data.bazi_pillars = json.dumps(bazi_data.get("bazi_pillars", {}), ensure_ascii=False)
                    request.bazi_data.metadata_json = json.dumps(bazi_data, ensure_ascii=False)
                
                # 调用服务
                response = stub.MatchFaceRules(request, timeout=30.0)
                
                if not response.success:
                    return {
                        "success": False,
                        "error": response.error_message,
                        "insights": [],
                        "integrated_insights": [],
                        "recommendations": [],
                        "bazi_data": None
                    }
                
                # 转换响应
                face_insights = []
                for insight_pb in response.face_insights:
                    face_insights.append({
                        "category": insight_pb.category,
                        "content": insight_pb.content,
                        "confidence": insight_pb.confidence,
                        "source": insight_pb.source,
                        "feature": insight_pb.feature
                    })
                
                integrated_insights = []
                for insight_pb in response.integrated_insights:
                    integrated_insights.append({
                        "category": insight_pb.category,
                        "content": insight_pb.content,
                        "confidence": insight_pb.confidence,
                        "source": insight_pb.source,
                        "feature": insight_pb.feature
                    })
                
                # 解析八字数据
                result_bazi_data = None
                if response.bazi_data and response.bazi_data.element_counts:
                    try:
                        result_bazi_data = json.loads(response.bazi_data.metadata_json) if response.bazi_data.metadata_json else {
                            "element_counts": dict(response.bazi_data.element_counts),
                            "ten_gods_stats": dict(response.bazi_data.ten_gods_stats),
                            "bazi_pillars": json.loads(response.bazi_data.bazi_pillars) if response.bazi_data.bazi_pillars else {}
                        }
                    except:
                        result_bazi_data = {
                            "element_counts": dict(response.bazi_data.element_counts),
                            "ten_gods_stats": dict(response.bazi_data.ten_gods_stats),
                            "bazi_pillars": json.loads(response.bazi_data.bazi_pillars) if response.bazi_data.bazi_pillars else {}
                        }
                
                return {
                    "success": True,
                    "insights": face_insights,
                    "integrated_insights": integrated_insights,
                    "recommendations": list(response.recommendations),
                    "bazi_data": result_bazi_data
                }
                
        except Exception as e:
            import traceback
            error_msg = f"调用 fortune-rule-service 失败: {str(e)}\n{traceback.format_exc()}"
            logger.info(f"❌ {error_msg}")
            return {
                "success": False,
                "error": str(e),
                "insights": [],
                "integrated_insights": [],
                "recommendations": [],
                "bazi_data": None
            }


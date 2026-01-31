#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面相分析核心逻辑（独立模块，不影响手相）
"""

import os
import logging

logger = logging.getLogger(__name__)
import sys
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 添加服务目录到路径
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

from face_analyzer import FaceAnalyzer
# 改为调用 fortune_rule 微服务，不再使用本地 rule_engine
from fortune_rule_client import FortuneRuleClient
from coze_integration import CozeIntegration


class FaceAnalyzerCore:
    """面相分析核心类（独立模块，不影响手相）"""
    
    def __init__(self):
        self.face_analyzer = FaceAnalyzer()
        # 使用 fortune_rule 微服务客户端
        self.rule_client = FortuneRuleClient()
        self.coze_integration = CozeIntegration()
    
    def analyze_face(
        self,
        image_bytes: bytes,
        image_format: str = "jpg",
        bazi_info: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        分析面相
        
        Args:
            image_bytes: 图像字节数据
            image_format: 图像格式
            bazi_info: 八字信息（protobuf 对象）
            
        Returns:
            分析结果
        """
        try:
            import datetime
            request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info("\n" + "="*80)
            logger.info("🔮 面相分析流程开始")
            logger.info("="*80)
            logger.info(f"[{request_time}] 📸 开始面相分析", flush=True)
            
            # 1. 提取面部特征（性能优化：默认关闭特殊特征检测）
            logger.info(f"[{request_time}] 📋 步骤1: 提取面部特征...", flush=True)
            face_result = self.face_analyzer.analyze(image_bytes, image_format, enable_special_features=False)
            
            if not face_result.get("success"):
                logger.info(f"[{request_time}] ❌ 面部特征提取失败: {face_result.get('error', '未知错误')}", flush=True)
                return face_result
            
            face_features = face_result.get("features", {})
            logger.info(f"[{request_time}] ✅ 面部特征提取完成", flush=True)
            
            # 2. 规则匹配和八字融合（调用 fortune_rule 微服务）
            logger.info(f"\n[{request_time}] 📋 步骤2: 规则匹配和八字融合...", flush=True)
            bazi_info_dict = None
            if bazi_info and bazi_info.use_bazi:
                bazi_info_dict = {
                    "solar_date": bazi_info.solar_date,
                    "solar_time": bazi_info.solar_time,
                    "gender": bazi_info.gender,
                    "use_bazi": True
                }
                logger.info(f"[{request_time}] 📅 八字信息: {bazi_info.solar_date} {bazi_info.solar_time} {bazi_info.gender}", flush=True)
            else:
                logger.info(f"[{request_time}] ⚠️  未提供八字信息，仅进行面相规则匹配", flush=True)
            
            # 调用 fortune_rule 微服务
            logger.info(f"[{request_time}] 🔍 调用 fortune_rule 微服务进行规则匹配...", flush=True)
            rule_result = self.rule_client.match_face_rules(
                face_features=face_features,
                bazi_info=bazi_info_dict,
                bazi_data=None  # 让微服务内部获取八字数据
            )
            
            if not rule_result.get("success"):
                logger.info(f"[{request_time}] ❌ 规则匹配失败: {rule_result.get('error', '未知错误')}", flush=True)
                return {
                    "success": False,
                    "error": rule_result.get("error", "规则匹配失败")
                }
            
            face_insights = rule_result.get("insights", [])
            integrated_insights = rule_result.get("integrated_insights", [])
            recommendations = rule_result.get("recommendations", [])
            bazi_data = rule_result.get("bazi_data")
            
            logger.info(f"[{request_time}] ✅ 规则匹配完成", flush=True)
            logger.info(f"[{request_time}] 📊 匹配结果:", flush=True)
            logger.info(f"   面相规则洞察: {len(face_insights)}条", flush=True)
            logger.info(f"   八字融合洞察: {len(integrated_insights)}条", flush=True)
            logger.info(f"   建议: {len(recommendations)}条", flush=True)
            
            # 3. AI 增强（可选，默认关闭以提升性能）
            ai_enhanced_insights = []
            # 如果需要AI增强，可以通过环境变量启用：ENABLE_AI_ENHANCEMENT=true
            enable_ai = os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"
            if enable_ai:
                logger.info(f"\n[{request_time}] 📋 步骤3: AI 增强分析...", flush=True)
                try:
                    # 准备数据
                    analysis_data = {
                        "type": "face",
                        "features": face_features,
                        "insights": face_insights,
                        "bazi_data": bazi_data
                    }
                    
                    # 调用 Coze API
                    logger.info(f"[{request_time}] 🤖 调用 Coze API 进行AI增强...", flush=True)
                    ai_result = self.coze_integration.enhance_analysis(analysis_data)
                    if ai_result:
                        ai_enhanced_insights = ai_result.get("enhanced_insights", [])
                        logger.info(f"[{request_time}] ✅ AI增强完成，新增 {len(ai_enhanced_insights)} 条洞察", flush=True)
                    else:
                        logger.info(f"[{request_time}] ⚠️  AI增强未返回结果", flush=True)
                except Exception as e:
                    logger.info(f"[{request_time}] ⚠️  Coze API 调用失败: {e}", flush=True)
            else:
                logger.info(f"[{request_time}] ⏭️  跳过AI增强（默认关闭以提升性能）", flush=True)
            
            # 4. 合并所有洞察（去重）
            logger.info(f"\n[{request_time}] 📋 步骤4: 合并所有洞察并去重...", flush=True)
            all_insights = face_insights + integrated_insights + ai_enhanced_insights
            
            # 对合并后的insights进行去重和提炼
            from services.fortune_rule.rule_engine import FortuneRuleEngine
            rule_engine = FortuneRuleEngine()
            all_insights = rule_engine._merge_and_refine_insights(all_insights)
            
            logger.info(f"[{request_time}] ✅ 合并完成，共 {len(all_insights)} 条洞察（已去重）", flush=True)
            
            # 5. 计算置信度
            logger.info(f"[{request_time}] 📋 步骤5: 计算置信度...", flush=True)
            confidence = self._calculate_confidence(face_features, len(all_insights))
            logger.info(f"[{request_time}] ✅ 置信度计算完成: {confidence:.2%}", flush=True)
            
            # 6. 构建完整报告
            logger.info(f"\n[{request_time}] 📋 步骤6: 构建完整报告...", flush=True)
            report = {
                "success": True,
                "features": face_features,
                "insights": all_insights,
                "integrated_insights": integrated_insights, # Keep for debugging if needed, but frontend uses 'insights'
                "bazi_data": bazi_data,
                "recommendations": recommendations,
                "confidence": confidence
            }
            
            return report
            
        except Exception as e:
            import traceback
            error_msg = f"面相分析失败: {str(e)}"
            logger.info(f"❌ {error_msg}\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def _calculate_confidence(self, features: Dict[str, Any], insights_count: int) -> float:
        """
        计算分析置信度（面相专用）
        
        Args:
            features: 面相特征
            insights_count: 洞察数量
            
        Returns:
            置信度（0-1之间）
        """
        base_confidence = 0.6
        
        # 基于特征完整性
        san_ting = features.get("san_ting_ratio", {})
        if san_ting.get("upper", 0) > 0 and san_ting.get("middle", 0) > 0 and san_ting.get("lower", 0) > 0:
            base_confidence += 0.15
        
        measurements = features.get("feature_measurements", {})
        if measurements.get("eye_width", 0) > 0:
            base_confidence += 0.05
        if measurements.get("nose_height", 0) > 0:
            base_confidence += 0.05
        if measurements.get("mouth_width", 0) > 0:
            base_confidence += 0.05
        
        # 基于洞察数量
        if insights_count > 15:
            base_confidence += 0.1
        elif insights_count > 10:
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)


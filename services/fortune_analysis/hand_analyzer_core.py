#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手相分析核心逻辑（独立模块，不影响面相）
"""

import os
import sys
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 添加服务目录到路径
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

from hand_analyzer import HandAnalyzer
# 改为调用 fortune_rule 微服务，不再使用本地 rule_engine
from fortune_rule_client import FortuneRuleClient
from coze_integration import CozeIntegration


class HandAnalyzerCore:
    """手相分析核心类（独立模块，不影响面相）"""
    
    def __init__(self):
        self.hand_analyzer = HandAnalyzer()
        # 使用 fortune_rule 微服务客户端
        self.rule_client = FortuneRuleClient()
        self.coze_integration = CozeIntegration()
    
    def analyze_hand(
        self,
        image_bytes: bytes,
        image_format: str = "jpg",
        bazi_info: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        分析手相
        
        Args:
            image_bytes: 图像字节数据
            image_format: 图像格式
            bazi_info: 八字信息（protobuf 对象）
            
        Returns:
            分析结果
        """
        try:
            # 1. 提取手部特征
            hand_result = self.hand_analyzer.analyze(image_bytes, image_format)
            
            if not hand_result.get("success"):
                return hand_result
            
            hand_features = hand_result.get("features", {})
            
            # 2. 规则匹配和八字融合（调用 fortune_rule 微服务）
            bazi_info_dict = None
            if bazi_info and bazi_info.use_bazi:
                bazi_info_dict = {
                    "solar_date": bazi_info.solar_date,
                    "solar_time": bazi_info.solar_time,
                    "gender": bazi_info.gender,
                    "use_bazi": True
                }
            
            # 调用 fortune_rule 微服务
            rule_result = self.rule_client.match_hand_rules(
                hand_features=hand_features,
                bazi_info=bazi_info_dict,
                bazi_data=None  # 让微服务内部获取八字数据
            )
            
            if not rule_result.get("success"):
                return {
                    "success": False,
                    "error": rule_result.get("error", "规则匹配失败")
                }
            
            hand_insights = rule_result.get("insights", [])
            integrated_insights = rule_result.get("integrated_insights", [])
            recommendations = rule_result.get("recommendations", [])
            bazi_data = rule_result.get("bazi_data")
            
            # 6. AI 增强（使用 Coze API）
            ai_enhanced_insights = []
            try:
                # 准备数据
                analysis_data = {
                    "type": "hand",
                    "features": hand_features,
                    "insights": hand_insights,
                    "bazi_data": bazi_data
                }
                
                # 调用 Coze API
                ai_result = self.coze_integration.enhance_analysis(analysis_data)
                if ai_result:
                    ai_enhanced_insights = ai_result.get("enhanced_insights", [])
            except Exception as e:
                print(f"⚠️  Coze API 调用失败: {e}")
            
            # 7. 合并所有洞察（去重）
            all_insights = hand_insights + integrated_insights + ai_enhanced_insights
            
            # 对合并后的insights进行去重和提炼
            from services.fortune_rule.rule_engine import FortuneRuleEngine
            rule_engine = FortuneRuleEngine()
            all_insights = rule_engine._merge_and_refine_insights(all_insights)
            
            # 8. 计算置信度
            confidence = self._calculate_confidence(hand_features, len(all_insights))
            
            # 9. 构建完整报告
            report = {
                "success": True,
                "features": hand_features,
                "insights": all_insights,
                "integrated_insights": integrated_insights,
                "bazi_data": bazi_data,
                "recommendations": recommendations,
                "confidence": confidence
            }
            
            return report
            
        except Exception as e:
            import traceback
            error_msg = f"手相分析失败: {str(e)}\n{traceback.format_exc()}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_confidence(self, features: Dict[str, Any], insights_count: int) -> float:
        """
        计算分析置信度（手相专用）
        
        Args:
            features: 手相特征
            insights_count: 洞察数量
            
        Returns:
            置信度（0-1之间）
        """
        base_confidence = 0.6
        
        # 基于特征完整性
        if features.get("hand_shape") and features.get("hand_shape") != "未知":
            base_confidence += 0.1
        
        if features.get("palm_lines") and len(features.get("palm_lines", {})) > 0:
            base_confidence += 0.1
        
        if features.get("finger_lengths") and len(features.get("finger_lengths", {})) > 0:
            base_confidence += 0.1
        
        # 基于洞察数量
        if insights_count > 10:
            base_confidence += 0.1
        elif insights_count > 5:
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)


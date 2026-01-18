#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主分析器
整合图像分析、规则引擎、八字融合、AI 增强
"""

import os
import sys
from typing import Dict, Any, Optional
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 添加服务目录到路径
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

from hand_analyzer import HandAnalyzer
from face_analyzer import FaceAnalyzer
# 改为调用 fortune_rule 微服务，不再使用本地 rule_engine
from fortune_rule_client import FortuneRuleClient
from coze_integration import CozeIntegration

# 导入八字客户端
try:
    from shared.clients.bazi_core_client_grpc import BaziCoreClient
    BAZI_CLIENT_AVAILABLE = True
except ImportError:
    BAZI_CLIENT_AVAILABLE = False
    print("⚠️  八字客户端未找到，八字融合功能将受限")


class FortuneAnalyzer:
    """命理分析器主类"""
    
    def __init__(self):
        self.hand_analyzer = HandAnalyzer()
        self.face_analyzer = FaceAnalyzer()
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
            
            print("\n" + "="*80)
            print("🔮 面相分析流程开始")
            print("="*80)
            print(f"[{request_time}] 📸 开始面相分析", flush=True)
            
            # 1. 提取面部特征（性能优化：默认关闭特殊特征检测）
            print(f"[{request_time}] 📋 步骤1: 提取面部特征...", flush=True)
            face_result = self.face_analyzer.analyze(image_bytes, image_format, enable_special_features=False)
            
            if not face_result.get("success"):
                print(f"[{request_time}] ❌ 面部特征提取失败: {face_result.get('error', '未知错误')}", flush=True)
                return face_result
            
            face_features = face_result.get("features", {})
            print(f"[{request_time}] ✅ 面部特征提取完成", flush=True)
            print(f"[{request_time}] 📊 提取的特征:", flush=True)
            san_ting = face_features.get("san_ting_ratio", {})
            measurements = face_features.get("feature_measurements", {})
            print(f"   三停比例: 上停={san_ting.get('upper', 0):.2%}, 中停={san_ting.get('middle', 0):.2%}, 下停={san_ting.get('lower', 0):.2%}", flush=True)
            if measurements:
                print(f"   五官特征:", flush=True)
                if measurements.get("forehead_width", 0) > 0:
                    print(f"     额头: 宽度={measurements.get('forehead_width', 0):.1f}, 比例={measurements.get('forehead_ratio', 0):.2f}", flush=True)
                if measurements.get("nose_height", 0) > 0:
                    print(f"     鼻子: 高度={measurements.get('nose_height', 0):.1f}, 比例={measurements.get('nose_ratio', 0):.2f}", flush=True)
                if measurements.get("eye_width", 0) > 0:
                    print(f"     眼睛: 宽度={measurements.get('eye_width', 0):.1f}, 对称性={measurements.get('eye_symmetry', 0):.2f}", flush=True)
                if measurements.get("mouth_width", 0) > 0:
                    print(f"     嘴巴: 宽度={measurements.get('mouth_width', 0):.1f}", flush=True)
                if measurements.get("face_ratio", 0) > 0:
                    print(f"     面部: 宽高比={measurements.get('face_ratio', 0):.2f}", flush=True)
            special_features = face_features.get("special_features", [])
            if special_features:
                print(f"   特殊特征: {len(special_features)}个", flush=True)
            
            # 2. 规则匹配和八字融合（调用 fortune_rule 微服务）
            print(f"\n[{request_time}] 📋 步骤2: 规则匹配和八字融合...", flush=True)
            bazi_info_dict = None
            if bazi_info and bazi_info.use_bazi:
                bazi_info_dict = {
                    "solar_date": bazi_info.solar_date,
                    "solar_time": bazi_info.solar_time,
                    "gender": bazi_info.gender,
                    "use_bazi": True
                }
                print(f"[{request_time}] 📅 八字信息: {bazi_info.solar_date} {bazi_info.solar_time} {bazi_info.gender}", flush=True)
            else:
                print(f"[{request_time}] ⚠️  未提供八字信息，仅进行面相规则匹配", flush=True)
            
            # 调用 fortune_rule 微服务
            print(f"[{request_time}] 🔍 调用 fortune_rule 微服务进行规则匹配...", flush=True)
            rule_result = self.rule_client.match_face_rules(
                face_features=face_features,
                bazi_info=bazi_info_dict,
                bazi_data=None  # 让微服务内部获取八字数据
            )
            
            if not rule_result.get("success"):
                print(f"[{request_time}] ❌ 规则匹配失败: {rule_result.get('error', '未知错误')}", flush=True)
                return {
                    "success": False,
                    "error": rule_result.get("error", "规则匹配失败")
                }
            
            face_insights = rule_result.get("insights", [])
            integrated_insights = rule_result.get("integrated_insights", [])
            recommendations = rule_result.get("recommendations", [])
            bazi_data = rule_result.get("bazi_data")
            
            print(f"[{request_time}] ✅ 规则匹配完成", flush=True)
            print(f"[{request_time}] 📊 匹配结果:", flush=True)
            print(f"   面相规则洞察: {len(face_insights)}条", flush=True)
            print(f"   八字融合洞察: {len(integrated_insights)}条", flush=True)
            print(f"   建议: {len(recommendations)}条", flush=True)
            
            # 打印八字信息（如果有）
            if bazi_data:
                self._print_bazi_info(bazi_data, 
                                     bazi_info.solar_date if bazi_info else None,
                                     bazi_info.solar_time if bazi_info else None,
                                     bazi_info.gender if bazi_info else None)
            
            # 3. AI 增强（可选，默认关闭以提升性能）
            # 注意：AI增强会显著增加响应时间，默认关闭
            ai_enhanced_insights = []
            # 如果需要AI增强，可以通过环境变量启用：ENABLE_AI_ENHANCEMENT=true
            enable_ai = os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"
            if enable_ai:
                print(f"\n[{request_time}] 📋 步骤3: AI 增强分析...", flush=True)
                try:
                    # 准备数据
                    analysis_data = {
                        "type": "face",
                        "features": face_features,
                        "insights": face_insights,
                        "bazi_data": bazi_data
                    }
                    
                    # 调用 Coze API
                    print(f"[{request_time}] 🤖 调用 Coze API 进行AI增强...", flush=True)
                    ai_result = self.coze_integration.enhance_analysis(analysis_data)
                    if ai_result:
                        ai_enhanced_insights = ai_result.get("enhanced_insights", [])
                        print(f"[{request_time}] ✅ AI增强完成，新增 {len(ai_enhanced_insights)} 条洞察", flush=True)
                    else:
                        print(f"[{request_time}] ⚠️  AI增强未返回结果", flush=True)
                except Exception as e:
                    print(f"[{request_time}] ⚠️  Coze API 调用失败: {e}", flush=True)
            else:
                print(f"[{request_time}] ⏭️  跳过AI增强（默认关闭以提升性能）", flush=True)
            
            # 4. 合并所有洞察（去重）
            print(f"\n[{request_time}] 📋 步骤4: 合并所有洞察并去重...", flush=True)
            all_insights = face_insights + integrated_insights + ai_enhanced_insights
            
            # 对合并后的insights进行去重和提炼
            from services.fortune_rule.rule_engine import FortuneRuleEngine
            rule_engine = FortuneRuleEngine()
            all_insights = rule_engine._merge_and_refine_insights(all_insights)
            
            print(f"[{request_time}] ✅ 合并完成，共 {len(all_insights)} 条洞察（已去重）", flush=True)
            
            # 5. 计算置信度
            print(f"[{request_time}] 📋 步骤5: 计算置信度...", flush=True)
            confidence = self._calculate_confidence(face_features, len(all_insights))
            print(f"[{request_time}] ✅ 置信度计算完成: {confidence:.2%}", flush=True)
            
            # 6. 构建完整报告
            print(f"\n[{request_time}] 📋 步骤6: 构建完整报告...", flush=True)
            report = {
                "success": True,
                "features": face_features,
                "insights": all_insights,
                "integrated_insights": integrated_insights,
                "bazi_data": bazi_data,
                "recommendations": recommendations,
                "confidence": confidence
            }
            
            print(f"[{request_time}] ✅ 面相分析完成！", flush=True)
            print(f"[{request_time}] 📊 最终结果:", flush=True)
            print(f"   总洞察数: {len(all_insights)}", flush=True)
            print(f"   建议数: {len(recommendations)}", flush=True)
            print(f"   置信度: {confidence:.2%}", flush=True)
            print("="*80 + "\n", flush=True)
            
            return report
            
        except Exception as e:
            import traceback
            error_msg = f"面相分析失败: {str(e)}\n{traceback.format_exc()}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_bazi_data(self, bazi_info: Any) -> Optional[Dict[str, Any]]:
        """获取八字数据（使用 BaziService 确保数据完整）"""
        try:
            # 从 protobuf 对象获取信息
            solar_date = bazi_info.solar_date
            solar_time = bazi_info.solar_time
            gender = bazi_info.gender
            
            print(f"📊 获取八字数据: {solar_date} {solar_time} {gender}")
            
            # 优先使用 BaziService（更完整的数据）
            try:
                from server.services.bazi_service import BaziService
                bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
                
                if bazi_result:
                    print(f"✅ 使用 BaziService 获取八字数据成功")
                    # BaziService 返回的数据格式是 {"bazi": {...}, "rizhu": "...", "matched_rules": [...]}
                    # 需要提取 bazi 字段
                    if isinstance(bazi_result, dict) and "bazi" in bazi_result:
                        bazi_data = bazi_result["bazi"]
                        # 确保包含所有必要字段
                        if not bazi_data.get("elements"):
                            bazi_data["elements"] = bazi_data.get("five_elements", {})
                        
                        # 打印详细的八字信息到日志
                        self._print_bazi_info(bazi_data, solar_date, solar_time, gender)
                        
                        return bazi_data
                    else:
                        # 如果已经是标准格式，直接返回
                        # 打印八字信息
                        self._print_bazi_info(bazi_result, solar_date, solar_time, gender)
                        return bazi_result
            except ImportError:
                print("⚠️  BaziService 不可用，使用 BaziCoreClient")
            except Exception as e:
                print(f"⚠️  BaziService 调用失败: {e}，尝试使用 BaziCoreClient")
            
            # 降级方案：使用 BaziCoreClient
            if BAZI_CLIENT_AVAILABLE:
                client = BaziCoreClient()
                bazi_result = client.calculate_bazi(solar_date, solar_time, gender)
                
                # 转换为字典格式
                bazi_data = {
                    "basic_info": bazi_result.get("basic_info", {}),
                    "bazi_pillars": bazi_result.get("bazi_pillars", {}),
                    "element_counts": bazi_result.get("element_counts", {}),
                    "ten_gods_stats": bazi_result.get("ten_gods_stats", {}),
                    "elements": bazi_result.get("elements", {}),
                    "five_elements": bazi_result.get("elements", {})  # 兼容字段
                }
                
                print(f"✅ 使用 BaziCoreClient 获取八字数据成功")
                
                # 打印详细的八字信息到日志
                self._print_bazi_info(bazi_data, solar_date, solar_time, gender)
                
                return bazi_data
            
            return None
            
        except Exception as e:
            import traceback
            print(f"⚠️  获取八字数据失败: {e}")
            print(f"详细错误: {traceback.format_exc()}")
            return None
    
    def _print_bazi_info(self, bazi_data: Dict[str, Any], solar_date: str, solar_time: str, gender: str):
        """打印详细的八字信息到日志"""
        try:
            print("\n" + "="*80)
            print("📋 八字详细信息")
            print("="*80)
            print(f"出生日期: {solar_date} {solar_time}")
            print(f"性别: {gender}")
            print("-"*80)
            
            # 基本信息
            basic_info = bazi_data.get("basic_info", {})
            if basic_info:
                print("【基本信息】")
                print(f"  农历日期: {basic_info.get('lunar_date', '未知')}")
                print(f"  时辰: {basic_info.get('time_ganzhi', '未知')}")
                print()
            
            # 八字四柱（优先从 bazi_pillars 获取，如果为空则从 elements 中提取）
            bazi_pillars = bazi_data.get("bazi_pillars", {})
            elements = bazi_data.get("elements", {}) or bazi_data.get("five_elements", {})
            
            # 如果 bazi_pillars 为空或格式不对，尝试从 elements 中提取
            if not bazi_pillars or not isinstance(bazi_pillars, dict) or not bazi_pillars.get("year"):
                if elements and isinstance(elements, dict):
                    # 从 elements 中提取四柱信息
                    year_elem = elements.get("year", {})
                    month_elem = elements.get("month", {})
                    day_elem = elements.get("day", {})
                    hour_elem = elements.get("hour", {})
                    
                    if year_elem and isinstance(year_elem, dict):
                        bazi_pillars = {
                            "year": {
                                "gan": year_elem.get("stem", ""),
                                "zhi": year_elem.get("branch", ""),
                                "gan_element": year_elem.get("stem_element", ""),
                                "zhi_element": year_elem.get("branch_element", "")
                            },
                            "month": {
                                "gan": month_elem.get("stem", "") if month_elem else "",
                                "zhi": month_elem.get("branch", "") if month_elem else "",
                                "gan_element": month_elem.get("stem_element", "") if month_elem else "",
                                "zhi_element": month_elem.get("branch_element", "") if month_elem else ""
                            },
                            "day": {
                                "gan": day_elem.get("stem", "") if day_elem else "",
                                "zhi": day_elem.get("branch", "") if day_elem else "",
                                "gan_element": day_elem.get("stem_element", "") if day_elem else "",
                                "zhi_element": day_elem.get("branch_element", "") if day_elem else ""
                            },
                            "hour": {
                                "gan": hour_elem.get("stem", "") if hour_elem else "",
                                "zhi": hour_elem.get("branch", "") if hour_elem else "",
                                "gan_element": hour_elem.get("stem_element", "") if hour_elem else "",
                                "zhi_element": hour_elem.get("branch_element", "") if hour_elem else ""
                            }
                        }
            
            if bazi_pillars and isinstance(bazi_pillars, dict):
                print("【八字四柱】")
                year = bazi_pillars.get("year", {})
                month = bazi_pillars.get("month", {})
                day = bazi_pillars.get("day", {})
                hour = bazi_pillars.get("hour", {})
                
                # 兼容不同的字段名（gan/zhi 或 stem/branch）
                year_gan = year.get('gan') or year.get('stem', '')
                year_zhi = year.get('zhi') or year.get('branch', '')
                year_gan_elem = year.get('gan_element') or year.get('stem_element', '')
                year_zhi_elem = year.get('zhi_element') or year.get('branch_element', '')
                
                month_gan = month.get('gan') or month.get('stem', '')
                month_zhi = month.get('zhi') or month.get('branch', '')
                month_gan_elem = month.get('gan_element') or month.get('stem_element', '')
                month_zhi_elem = month.get('zhi_element') or month.get('branch_element', '')
                
                day_gan = day.get('gan') or day.get('stem', '')
                day_zhi = day.get('zhi') or day.get('branch', '')
                day_gan_elem = day.get('gan_element') or day.get('stem_element', '')
                day_zhi_elem = day.get('zhi_element') or day.get('branch_element', '')
                
                hour_gan = hour.get('gan') or hour.get('stem', '')
                hour_zhi = hour.get('zhi') or hour.get('branch', '')
                hour_gan_elem = hour.get('gan_element') or hour.get('stem_element', '')
                hour_zhi_elem = hour.get('zhi_element') or hour.get('branch_element', '')
                
                print(f"  年柱: {year_gan}{year_zhi} ({year_gan_elem}{year_zhi_elem})")
                print(f"  月柱: {month_gan}{month_zhi} ({month_gan_elem}{month_zhi_elem})")
                print(f"  日柱: {day_gan}{day_zhi} ({day_gan_elem}{day_zhi_elem})")
                print(f"  时柱: {hour_gan}{hour_zhi} ({hour_gan_elem}{hour_zhi_elem})")
                print()
            
            # 五行统计
            element_counts = bazi_data.get("element_counts", {})
            if element_counts:
                print("【五行统计】")
                elements = ["木", "火", "土", "金", "水"]
                for elem in elements:
                    count = element_counts.get(elem, 0)
                    bar = "█" * count if count > 0 else ""
                    print(f"  {elem}: {count} {bar}")
                print()
            
            # 十神统计
            ten_gods = bazi_data.get("ten_gods_stats", {})
            if ten_gods:
                print("【十神统计】")
                ten_gods_list = ["比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"]
                for god in ten_gods_list:
                    count = ten_gods.get(god, 0)
                    if count > 0:
                        print(f"  {god}: {count}")
                print()
            
            # 日主信息
            rizhu = bazi_data.get("rizhu", "")
            if rizhu:
                print(f"【日主】{rizhu}")
                print()
            
            # 五行元素详情
            elements = bazi_data.get("elements", {}) or bazi_data.get("five_elements", {})
            if elements:
                print("【五行元素详情】")
                for key, value in elements.items():
                    if isinstance(value, dict):
                        print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
                print()
            
            print("="*80 + "\n")
        except Exception as e:
            print(f"⚠️  打印八字信息时出错: {e}")
            import traceback
            print(traceback.format_exc())
    
    def _calculate_confidence(self, features: Dict[str, Any], insight_count: int) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度
        
        # 根据特征完整性调整
        if features:
            confidence += 0.2
        
        # 根据洞察数量调整
        if insight_count > 5:
            confidence += 0.2
        elif insight_count > 3:
            confidence += 0.1
        
        # 限制在 0-1 之间
        return min(1.0, max(0.0, confidence))


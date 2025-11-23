#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手相流式分析器
支持进度回调，实现真正的流式响应
"""

import os
import sys
from typing import Dict, Any, Optional, Callable, AsyncGenerator
import json
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 添加服务目录到路径
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

from hand_analyzer import HandAnalyzer
from hand_analyzer_core import HandAnalyzerCore
# 改为调用 fortune_rule 微服务
from fortune_rule_client import FortuneRuleClient
from coze_integration import CozeIntegration


class HandAnalyzerStream:
    """手相流式分析器（独立模块，不影响面相）"""
    
    def __init__(self):
        self.hand_analyzer = HandAnalyzer()
        self.analyzer_core = HandAnalyzerCore()
        # 使用 fortune_rule 微服务客户端
        self.rule_client = FortuneRuleClient()
        self.coze_integration = CozeIntegration()
    
    async def analyze_hand_stream(
        self,
        image_bytes: bytes,
        image_format: str = "jpg",
        solar_date: Optional[str] = None,
        solar_time: Optional[str] = None,
        gender: Optional[str] = None,
        use_bazi: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式分析手相
        
        Args:
            image_bytes: 图像字节数据
            image_format: 图像格式
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            use_bazi: 是否使用八字
            progress_callback: 进度回调函数
            
        Yields:
            分析结果字典
        """
        try:
            # 步骤0: 验证图像（必须在分析前验证）
            yield {
                "type": "progress",
                "statusText": "正在验证图像...",
                "showGrid": True,
                "showStatus": True,
                "showPlayButton": True
            }
            await asyncio.sleep(0.05)
            
            # 导入验证器
            try:
                from image_validator import ImageValidator
                validator = ImageValidator()
                is_valid, error_msg = validator.validate_hand_image(image_bytes)
                if not is_valid:
                    yield {
                        "type": "error",
                        "error": error_msg,
                        "statusText": "图像验证失败",
                        "showGrid": False,
                        "showStatus": False,
                        "showPlayButton": False
                    }
                    return
            except Exception as e:
                print(f"⚠️  图像验证失败: {e}，继续分析")
            
            # 步骤1: 提取手部特征
            yield {
                "type": "progress",
                "statusText": "正在识别掌纹...",
                "showGrid": True,
                "showStatus": True,
                "showPlayButton": True
            }
            await asyncio.sleep(0.05)
            
            loop = asyncio.get_event_loop()
            hand_result = await loop.run_in_executor(
                None,
                self.hand_analyzer.analyze,
                image_bytes,
                image_format
            )
            
            if not hand_result.get("success"):
                yield {
                    "type": "error",
                    "error": hand_result.get("error", "手相分析失败"),
                    "statusText": "分析失败"
                }
                return
            
            hand_features = hand_result.get("features", {})
            
            # 步骤2: 规则匹配和八字融合（调用 fortune_rule 微服务）
            yield {
                "type": "progress",
                "statusText": "正在匹配规则和融合八字分析...",
                "showGrid": True,
                "showStatus": True,
                "showPlayButton": True
            }
            await asyncio.sleep(0.05)
            
            # 准备八字信息
            bazi_info_dict = None
            if use_bazi and solar_date and solar_time and gender:
                bazi_info_dict = {
                    "solar_date": solar_date,
                    "solar_time": solar_time,
                    "gender": gender,
                    "use_bazi": True
                }
            
            # 调用 fortune_rule 微服务
            loop = asyncio.get_event_loop()
            rule_result = await loop.run_in_executor(
                None,
                self.rule_client.match_hand_rules,
                hand_features,
                bazi_info_dict,
                None  # 让微服务内部获取八字数据
            )
            
            if not rule_result.get("success"):
                yield {
                    "type": "error",
                    "error": rule_result.get("error", "规则匹配失败"),
                    "statusText": "分析失败",
                    "showGrid": False,
                    "showStatus": False,
                    "showPlayButton": False
                }
                return
            
            hand_insights = rule_result.get("insights", [])
            integrated_insights = rule_result.get("integrated_insights", [])
            recommendations = rule_result.get("recommendations", [])
            bazi_data = rule_result.get("bazi_data")
            
            # 步骤5: AI 增强（异步，可选，不阻塞）
            ai_enhanced_insights = []
            # AI 增强在后台执行，不等待
            try:
                yield {
                    "type": "progress",
                    "statusText": "正在进行 AI 增强分析...",
                    "showGrid": True,
                    "showStatus": True,
                    "showPlayButton": True
                }
                await asyncio.sleep(0.05)
                
                # 在后台任务中执行 AI 增强，不阻塞主流程
                async def ai_enhance_task():
                    try:
                        analysis_data = {
                            "type": "hand",
                            "features": hand_features,
                            "insights": hand_insights,
                            "bazi_data": bazi_data
                        }
                        loop = asyncio.get_event_loop()
                        ai_result = await loop.run_in_executor(
                            None,
                            self.coze_integration.enhance_analysis,
                            analysis_data
                        )
                        return ai_result.get("enhanced_insights", []) if ai_result else []
                    except Exception as e:
                        print(f"⚠️  Coze API 调用失败: {e}")
                        return []
                
                # 创建后台任务，但不等待
                ai_task = asyncio.create_task(ai_enhance_task())
                # 继续执行，不等待 AI 结果（AI 增强在后台执行）
                ai_enhanced_insights = []
            except Exception as e:
                print(f"⚠️  AI 增强任务创建失败: {e}")
            
            # 步骤6: 合并所有洞察
            yield {
                "type": "progress",
                "statusText": "正在生成最终报告...",
                "showGrid": True,
                "showStatus": True,
                "showPlayButton": True
            }
            await asyncio.sleep(0.05)
            
            try:
                all_insights = hand_insights + integrated_insights + ai_enhanced_insights
                
                # 对合并后的insights进行去重和提炼
                try:
                    from services.fortune_rule.rule_engine import FortuneRuleEngine
                    rule_engine = FortuneRuleEngine()
                    all_insights = rule_engine._merge_and_refine_insights(all_insights)
                except Exception as merge_error:
                    print(f"⚠️  合并insights失败: {merge_error}，使用原始insights")
                    # 合并失败时使用原始insights，不中断流程
                
                # 计算置信度
                try:
                    confidence = self.analyzer_core._calculate_confidence(hand_features, len(all_insights))
                except Exception as conf_error:
                    print(f"⚠️  计算置信度失败: {conf_error}，使用默认值")
                    confidence = 0.7  # 默认置信度
                
                # 构建完整报告
                report = {
                    "success": True,
                    "features": hand_features,
                    "insights": all_insights,
                    "integrated_insights": integrated_insights,
                    "bazi_data": bazi_data,
                    "recommendations": recommendations,
                    "confidence": confidence
                }
                
                # 确保发送complete消息
                print(f"✅ 手相分析完成，准备发送complete消息，insights数量: {len(all_insights)}")
                yield {
                    "type": "complete",
                    "data": report,
                    "statusText": "分析完成"
                }
                print(f"✅ complete消息已发送")
                
            except Exception as final_error:
                import traceback
                error_msg = f"生成最终报告失败: {str(final_error)}"
                print(f"❌ {error_msg}\n{traceback.format_exc()}")
                # 即使生成报告失败，也要发送一个包含部分数据的complete消息
                try:
                    fallback_report = {
                        "success": True,
                        "features": hand_features,
                        "insights": hand_insights + integrated_insights,
                        "integrated_insights": integrated_insights,
                        "bazi_data": bazi_data,
                        "recommendations": recommendations,
                        "confidence": 0.7,
                        "warning": "报告生成过程中出现部分错误，但分析已完成"
                    }
                    yield {
                        "type": "complete",
                        "data": fallback_report,
                        "statusText": "分析完成（部分数据）"
                    }
                except:
                    # 如果连fallback都失败，发送error消息
                    yield {
                        "type": "error",
                        "error": error_msg,
                        "statusText": "分析失败"
                    }
            
        except Exception as e:
            import traceback
            error_msg = f"手相分析失败: {str(e)}"
            print(f"❌ {error_msg}\n{traceback.format_exc()}")
            yield {
                "type": "error",
                "error": error_msg,
                "statusText": "分析失败",
                "showGrid": False,
                "showStatus": False,
                "showPlayButton": False
            }


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则引擎模块
基于传统命理学规则进行匹配
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class FortuneRuleEngine:
    """命理规则引擎"""
    
    def __init__(self):
        self.hand_rules = self._load_hand_rules()
        self.face_rules = self._load_face_rules()
    
    def _load_hand_rules(self) -> Dict[str, Any]:
        """加载手相规则"""
        return {
            "hand_shape": {
                "方形手": {
                    "insights": [
                        "手型方正，性格务实稳重，适合管理类工作",
                        "做事有条理，执行力强，适合从事需要细致规划的职业"
                    ],
                    "career": "管理、工程、金融",
                    "personality": "务实、稳重、有条理"
                },
                "圆形手": {
                    "insights": [
                        "手型圆润，性格灵活适应性强，适合创意类工作",
                        "思维活跃，善于变通，适合从事需要创新的职业"
                    ],
                    "career": "艺术、设计、营销",
                    "personality": "灵活、创新、适应性强"
                },
                "尖形手": {
                    "insights": [
                        "手型尖细，性格理想主义，适合艺术类工作",
                        "追求完美，有艺术天赋，适合从事创作类职业"
                    ],
                    "career": "艺术、文学、教育",
                    "personality": "理想主义、追求完美、有艺术天赋"
                },
                "长方形手": {
                    "insights": [
                        "手型修长，性格理性分析，适合技术类工作",
                        "逻辑思维强，适合从事需要分析思考的职业"
                    ],
                    "career": "技术、科研、法律",
                    "personality": "理性、分析、逻辑思维强"
                }
            },
            "life_line": {
                "深且长": {
                    "insights": [
                        "生命线深长，生命力强，健康运势佳",
                        "体质较好，恢复力强，适合规律作息"
                    ],
                    "health": "健康运势良好"
                },
                "浅短": {
                    "insights": [
                        "生命线浅短，需注意健康，宜规律作息",
                        "建议定期体检，注意饮食和运动"
                    ],
                    "health": "需注意健康管理"
                },
                "分叉": {
                    "insights": [
                        "生命线有分叉，可能有重大转折点",
                        "需注意人生重要节点的选择"
                    ],
                    "health": "注意重大转折"
                },
                "中等": {
                    "insights": [
                        "生命线中等，健康状况一般",
                        "保持规律作息，适当运动"
                    ],
                    "health": "健康状况一般"
                }
            },
            "head_line": {
                "深且长": {
                    "insights": [
                        "智慧线清晰深长，思维敏捷，适合学习研究",
                        "学习能力强，适合从事需要思考的职业"
                    ],
                    "intelligence": "思维敏捷"
                },
                "浅短": {
                    "insights": [
                        "智慧线浅短，需加强学习",
                        "建议多读书，提升思维能力"
                    ],
                    "intelligence": "需加强学习"
                }
            },
            "heart_line": {
                "向下弯": {
                    "insights": [
                        "感情线向下弯，情绪敏感，宜多与人沟通缓解压力",
                        "情感丰富，需注意情绪管理"
                    ],
                    "emotion": "情绪敏感"
                },
                "向上弯": {
                    "insights": [
                        "感情线向上弯，性格乐观，人际关系良好",
                        "善于与人相处，人缘较好"
                    ],
                    "emotion": "性格乐观"
                }
            }
        }
    
    def _load_face_rules(self) -> Dict[str, Any]:
        """加载面相规则"""
        return {
            "san_ting": {
                "upper_long": {
                    "threshold": 0.35,
                    "insights": [
                        "上停较长，早年运势佳，学习能力强",
                        "适合早年开始积累，打好基础"
                    ],
                    "fortune": "早年运势佳"
                },
                "middle_long": {
                    "threshold": 0.35,
                    "insights": [
                        "中停较长，中年运势佳，事业发展好",
                        "中年是事业发展的黄金期"
                    ],
                    "fortune": "中年运势佳"
                },
                "lower_long": {
                    "threshold": 0.35,
                    "insights": [
                        "下停较长，晚年运势佳，福气深厚",
                        "晚年生活幸福，有福气"
                    ],
                    "fortune": "晚年运势佳"
                }
            },
            "nose": {
                "high": {
                    "insights": [
                        "鼻梁高挺，财运佳，适合投资理财",
                        "有财运，但需稳健理财"
                    ],
                    "wealth": "财运佳"
                },
                "low": {
                    "insights": [
                        "鼻梁较低，需注意理财规划",
                        "建议稳健理财，避免高风险投资"
                    ],
                    "wealth": "需注意理财"
                }
            },
            "forehead": {
                "wide": {
                    "insights": [
                        "额头宽阔，智慧过人，适合学习研究",
                        "学习能力强，适合从事需要思考的职业"
                    ],
                    "intelligence": "智慧过人"
                },
                "narrow": {
                    "insights": [
                        "额头较窄，需加强学习",
                        "建议多读书，提升思维能力"
                    ],
                    "intelligence": "需加强学习"
                }
            }
        }
    
    def match_hand_rules(self, hand_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """匹配手相规则（增强版：支持连续值和更多特征）"""
        insights = []
        
        # 手型规则（支持连续值）
        hand_shape = hand_features.get("hand_shape", "")
        hand_shape_ratio = hand_features.get("hand_shape_ratio", 0.0)
        hand_shape_confidence = hand_features.get("hand_shape_confidence", 0.5)
        
        if hand_shape in self.hand_rules["hand_shape"]:
            rule = self.hand_rules["hand_shape"][hand_shape]
            confidence = 0.7 * hand_shape_confidence  # 根据手型识别置信度调整
            for insight_text in rule.get("insights", []):
                insights.append({
                    "category": "性格",
                    "content": insight_text,
                    "confidence": confidence,
                    "source": "hand",
                    "feature": f"手型:{hand_shape}(ratio:{hand_shape_ratio:.2f})"
                })
        
        # 指长规则（使用连续值）
        finger_ratios = hand_features.get("finger_ratios", {})
        finger_lengths = hand_features.get("finger_lengths", {})
        
        # 分析指长特征组合
        if finger_ratios:
            # 食指长于无名指（领导力）
            if finger_ratios.get("index", 0) > finger_ratios.get("ring", 0) * 1.05:
                insights.append({
                    "category": "性格",
                    "content": "食指长于无名指，具有领导才能和决策能力",
                    "confidence": 0.75,
                    "source": "hand",
                    "feature": f"指长比例:食指({finger_ratios.get('index', 0):.2f}) > 无名指({finger_ratios.get('ring', 0):.2f})"
                })
            
            # 无名指长于食指（艺术天赋）
            if finger_ratios.get("ring", 0) > finger_ratios.get("index", 0) * 1.05:
                insights.append({
                    "category": "天赋",
                    "content": "无名指长于食指，具有艺术天赋和创造力",
                    "confidence": 0.75,
                    "source": "hand",
                    "feature": f"指长比例:无名指({finger_ratios.get('ring', 0):.2f}) > 食指({finger_ratios.get('index', 0):.2f})"
                })
        
        # 掌纹规则（增强版：支持更多分类）
        palm_lines = hand_features.get("palm_lines", {})
        
        # 生命线（支持更多分类）
        life_line = palm_lines.get("life_line", "")
        if life_line and life_line != "无法检测":
            # 匹配规则（支持部分匹配）
            matched_rule = None
            for key in self.hand_rules["life_line"].keys():
                if key in life_line or life_line in key:
                    matched_rule = self.hand_rules["life_line"][key]
                    break
            
            if matched_rule:
                for insight_text in matched_rule.get("insights", []):
                    insights.append({
                        "category": "健康",
                        "content": insight_text,
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"生命线:{life_line}"
                    })
        
        # 智慧线（支持更多分类）
        head_line = palm_lines.get("head_line", "")
        if head_line and head_line != "无法检测":
            matched_rule = None
            for key in self.hand_rules["head_line"].keys():
                if key in head_line or head_line in key:
                    matched_rule = self.hand_rules["head_line"][key]
                    break
            
            if matched_rule:
                for insight_text in matched_rule.get("insights", []):
                    insights.append({
                        "category": "智慧",
                        "content": insight_text,
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"智慧线:{head_line}"
                    })
        
        # 感情线
        heart_line = palm_lines.get("heart_line", "")
        if heart_line and heart_line != "无法检测":
            matched_rule = None
            for key in self.hand_rules["heart_line"].keys():
                if key in heart_line or heart_line in key:
                    matched_rule = self.hand_rules["heart_line"][key]
                    break
            
            if matched_rule:
                for insight_text in matched_rule.get("insights", []):
                    insights.append({
                        "category": "感情",
                        "content": insight_text,
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"感情线:{heart_line}"
                    })
        
        # 事业线（新增）
        fate_line = palm_lines.get("fate_line", "")
        if fate_line == "明显":
            insights.append({
                "category": "事业",
                "content": "事业线明显，事业发展顺利，有较强的职业规划能力",
                "confidence": 0.7,
                "source": "hand",
                "feature": f"事业线:{fate_line}"
            })
        
        # 手掌纹理特征
        palm_texture = hand_features.get("palm_texture", {})
        if palm_texture:
            roughness = palm_texture.get("roughness", "")
            if roughness == "细腻":
                insights.append({
                    "category": "性格",
                    "content": "手掌纹理细腻，性格温和，注重细节",
                    "confidence": 0.65,
                    "source": "hand",
                    "feature": f"纹理:{roughness}"
                })
            elif roughness == "粗糙":
                insights.append({
                    "category": "性格",
                    "content": "手掌纹理较粗糙，性格豪爽，做事果断",
                    "confidence": 0.65,
                    "source": "hand",
                    "feature": f"纹理:{roughness}"
                })
        
        # 特殊标记
        special_marks = hand_features.get("special_marks", [])
        if len(special_marks) > 0:
            insights.append({
                "category": "特殊",
                "content": f"检测到 {len(special_marks)} 个特殊标记，可能有特殊的命理意义",
                "confidence": 0.6,
                "source": "hand",
                "feature": f"特殊标记数量:{len(special_marks)}"
            })
        
        return insights
    
    def match_face_rules(self, face_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """匹配面相规则"""
        insights = []
        
        # 三停规则
        san_ting = face_features.get("san_ting_ratio", {})
        upper = san_ting.get("upper", 0.33)
        middle = san_ting.get("middle", 0.33)
        lower = san_ting.get("lower", 0.34)
        
        if upper > 0.35:
            rule = self.face_rules["san_ting"]["upper_long"]
            for insight_text in rule.get("insights", []):
                insights.append({
                    "category": "运势",
                    "content": insight_text,
                    "confidence": 0.7,
                    "source": "face"
                })
        
        if middle > 0.35:
            rule = self.face_rules["san_ting"]["middle_long"]
            for insight_text in rule.get("insights", []):
                insights.append({
                    "category": "运势",
                    "content": insight_text,
                    "confidence": 0.7,
                    "source": "face"
                })
        
        if lower > 0.35:
            rule = self.face_rules["san_ting"]["lower_long"]
            for insight_text in rule.get("insights", []):
                insights.append({
                    "category": "运势",
                    "content": insight_text,
                    "confidence": 0.7,
                    "source": "face"
                })
        
        # 五官规则（简化）
        measurements = face_features.get("feature_measurements", {})
        nose_height = measurements.get("nose_height", 0)
        if nose_height > 50:  # 阈值需要根据实际情况调整
            rule = self.face_rules["nose"]["high"]
            for insight_text in rule.get("insights", []):
                insights.append({
                    "category": "财运",
                    "content": insight_text,
                    "confidence": 0.6,
                    "source": "face"
                })
        
        forehead_width = measurements.get("forehead_width", 0)
        if forehead_width > 100:  # 阈值需要根据实际情况调整
            rule = self.face_rules["forehead"]["wide"]
            for insight_text in rule.get("insights", []):
                insights.append({
                    "category": "智慧",
                    "content": insight_text,
                    "confidence": 0.6,
                    "source": "face"
                })
        
        return insights
    
    def integrate_with_bazi(
        self,
        hand_features: Optional[Dict[str, Any]],
        face_features: Optional[Dict[str, Any]],
        bazi_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """融合八字信息进行分析（增强版：详细日志）"""
        integrated_insights = []
        
        if not bazi_data:
            logger.info("⚠️  八字数据为空，跳过融合分析")
            return integrated_insights
        
        # 打印八字数据
        logger.info("\n" + "="*80)
        logger.info("🔮 八字与手相面相融合分析")
        logger.info("="*80)
        
        # 获取八字信息
        five_elements = bazi_data.get("element_counts", {})
        ten_gods = bazi_data.get("ten_gods_stats", {})
        bazi_pillars = bazi_data.get("bazi_pillars", {})
        
        logger.info("\n【八字数据】")
        logger.info(f"  五行统计: {five_elements}")
        logger.info(f"  十神统计: {ten_gods}")
        if bazi_pillars:
            year = bazi_pillars.get("year", {})
            month = bazi_pillars.get("month", {})
            day = bazi_pillars.get("day", {})
            hour = bazi_pillars.get("hour", {})
            year_gan = year.get('gan') or year.get('stem', '')
            year_zhi = year.get('zhi') or year.get('branch', '')
            month_gan = month.get('gan') or month.get('stem', '')
            month_zhi = month.get('zhi') or month.get('branch', '')
            day_gan = day.get('gan') or day.get('stem', '')
            day_zhi = day.get('zhi') or day.get('branch', '')
            hour_gan = hour.get('gan') or hour.get('stem', '')
            hour_zhi = hour.get('zhi') or hour.get('branch', '')
            logger.info(f"  八字四柱: {year_gan}{year_zhi} {month_gan}{month_zhi} {day_gan}{day_zhi} {hour_gan}{hour_zhi}")
        
        # 打印手相特征
        if hand_features:
            logger.info("\n【手相特征】")
            hand_shape = hand_features.get("hand_shape", "")
            hand_shape_ratio = hand_features.get("hand_shape_ratio", 0.0)
            palm_lines = hand_features.get("palm_lines", {})
            finger_ratios = hand_features.get("finger_ratios", {})
            logger.info(f"  手型: {hand_shape} (ratio: {hand_shape_ratio:.2f})")
            logger.info(f"  掌纹: {palm_lines}")
            logger.info(f"  指长比例: {finger_ratios}")
        
        # 打印面相特征
        if face_features:
            logger.info("\n【面相特征】")
            san_ting = face_features.get("san_ting_ratio", {})
            logger.info(f"  三停比例: {san_ting}")
        
        logger.info("\n【规则匹配过程】")
        logger.info("-"*80)
        
        # 五行对应关系
        element_mapping = {
            "木": {"organs": "肝胆", "color": "绿色", "direction": "东方"},
            "火": {"organs": "心脏", "color": "红色", "direction": "南方"},
            "土": {"organs": "脾胃", "color": "黄色", "direction": "中央"},
            "金": {"organs": "肺", "color": "白色", "direction": "西方"},
            "水": {"organs": "肾", "color": "黑色", "direction": "北方"}
        }
        
        # 手相 + 八字融合（增强版）
        if hand_features:
            hand_shape = hand_features.get("hand_shape", "")
            hand_shape_ratio = hand_features.get("hand_shape_ratio", 0.0)
            life_line = hand_features.get("palm_lines", {}).get("life_line", "")
            head_line = hand_features.get("palm_lines", {}).get("head_line", "")
            heart_line = hand_features.get("palm_lines", {}).get("heart_line", "")
            finger_ratios = hand_features.get("finger_ratios", {})
            
            # 手型 + 五行融合
            logger.info(f"\n规则1: 手型 + 五行融合")
            logger.info(f"  检查: hand_shape='{hand_shape}', 金元素={five_elements.get('金', 0)}")
            if hand_shape == "方形手" and five_elements.get("金", 0) > 0:
                insight = {
                    "category": "财运",
                    "content": f"手相显示财运佳（方形手，ratio:{hand_shape_ratio:.2f}），结合八字金旺（{five_elements.get('金', 0)}个），建议从事金融、投资相关行业",
                    "confidence": 0.8,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 条件不满足")
            
            logger.info(f"\n规则2: 圆形手 + 水元素")
            logger.info(f"  检查: hand_shape='{hand_shape}', 水元素={five_elements.get('水', 0)}")
            if hand_shape == "圆形手" and five_elements.get("水", 0) > 0:
                insight = {
                    "category": "性格",
                    "content": f"手相显示性格灵活（圆形手），结合八字水旺（{five_elements.get('水', 0)}个），适应能力强，适合从事需要变通的职业",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 条件不满足")
            
            # 生命线 + 八字健康（增强版）
            logger.info(f"\n规则3: 生命线 + 八字健康分析")
            logger.info(f"  检查: life_line='{life_line}', 土元素={five_elements.get('土', 0)}")
            if "深" in life_line or "长" in life_line:
                if five_elements.get("土", 0) < 2:
                    insight = {
                        "category": "健康",
                        "content": f"手相显示健康运势佳（生命线{life_line}），但八字土弱（{five_elements.get('土', 0)}个），建议注意脾胃健康，规律饮食",
                        "confidence": 0.75,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（土弱）: {insight['content']}")
                elif five_elements.get("土", 0) >= 3:
                    insight = {
                        "category": "健康",
                        "content": f"手相显示健康运势佳（生命线{life_line}），八字土旺（{five_elements.get('土', 0)}个），体质较好，但需注意消化系统",
                        "confidence": 0.8,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（土旺）: {insight['content']}")
                else:
                    logger.info(f"  ⚠️  生命线深长，但土元素数量为 {five_elements.get('土', 0)}，未匹配特定规则")
            else:
                logger.info(f"  ❌ 未匹配: 生命线不满足条件（需包含'深'或'长'）")
            
            # 智慧线 + 八字学习运
            logger.info(f"\n规则4: 智慧线 + 八字学习运")
            logger.info(f"  检查: head_line='{head_line}', 木元素={five_elements.get('木', 0)}")
            if "清晰" in head_line or "深长" in head_line:
                if five_elements.get("木", 0) > 0:
                    insight = {
                        "category": "学习",
                        "content": f"手相显示思维敏捷（智慧线{head_line}），结合八字木旺（{five_elements.get('木', 0)}个），学习能力强，适合早年开始积累",
                        "confidence": 0.75,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功: {insight['content']}")
                else:
                    logger.info(f"  ❌ 未匹配: 智慧线满足条件，但木元素为 {five_elements.get('木', 0)}（需 > 0）")
            else:
                logger.info(f"  ❌ 未匹配: 智慧线不满足条件（需包含'清晰'或'深长'）")
            
            # 感情线 + 八字感情运
            logger.info(f"\n规则5: 感情线 + 八字感情运")
            logger.info(f"  检查: heart_line='{heart_line}', 正官={ten_gods.get('正官', 0)}, 正财={ten_gods.get('正财', 0)}")
            if "明显" in heart_line or "深长" in heart_line:
                if ten_gods.get("正官", 0) > 0 or ten_gods.get("正财", 0) > 0:
                    insight = {
                        "category": "感情",
                        "content": f"手相显示感情丰富（感情线{heart_line}），结合八字正官/正财，感情稳定，婚姻和谐",
                        "confidence": 0.75,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功: {insight['content']}")
                else:
                    logger.info(f"  ❌ 未匹配: 感情线满足条件，但正官={ten_gods.get('正官', 0)}, 正财={ten_gods.get('正财', 0)}（需至少一个 > 0）")
            else:
                logger.info(f"  ❌ 未匹配: 感情线不满足条件（需包含'明显'或'深长'）")
            
            # 指长 + 八字天赋
            logger.info(f"\n规则6: 指长比例 + 八字天赋")
            if finger_ratios:
                index_ratio = finger_ratios.get("index", 0)
                ring_ratio = finger_ratios.get("ring", 0)
                logger.info(f"  检查: 食指比例={index_ratio:.2f}, 无名指比例={ring_ratio:.2f}, 金元素={five_elements.get('金', 0)}, 木元素={five_elements.get('木', 0)}")
                
                if index_ratio > ring_ratio * 1.05 and five_elements.get("金", 0) > 0:
                    insight = {
                        "category": "天赋",
                        "content": f"手相显示领导才能（食指长于无名指），结合八字金旺，适合管理、金融类工作",
                        "confidence": 0.7,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（食指长）: {insight['content']}")
                elif ring_ratio > index_ratio * 1.05 and five_elements.get("木", 0) > 0:
                    insight = {
                        "category": "天赋",
                        "content": f"手相显示艺术天赋（无名指长于食指），结合八字木旺，适合艺术、创意类工作",
                        "confidence": 0.7,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（无名指长）: {insight['content']}")
                else:
                    logger.info(f"  ❌ 未匹配: 指长比例或五行元素不满足条件")
            else:
                logger.info(f"  ❌ 未匹配: 指长比例数据为空")
        
        # 面相 + 八字融合（增强版）
        if face_features:
            san_ting = face_features.get("san_ting_ratio", {})
            upper = san_ting.get("upper", 0.33)
            middle = san_ting.get("middle", 0.33)
            lower = san_ting.get("lower", 0.34)
            
            # 上停长 + 八字学习运
            logger.info(f"\n规则7: 上停 + 八字学习运")
            logger.info(f"  检查: 上停比例={upper:.2%}, 木元素={five_elements.get('木', 0)}")
            if upper > 0.35 and five_elements.get("木", 0) > 0:
                insight = {
                    "category": "学习",
                    "content": f"面相显示早年学习运佳（上停比例{upper:.2%}），结合八字木旺（{five_elements.get('木', 0)}个），建议早年开始积累，打好基础",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 上停比例={upper:.2%}（需 > 35%）或木元素={five_elements.get('木', 0)}（需 > 0）")
            
            # 中停长 + 八字事业运
            logger.info(f"\n规则8: 中停 + 八字事业运")
            logger.info(f"  检查: 中停比例={middle:.2%}, 火元素={five_elements.get('火', 0)}")
            if middle > 0.35 and five_elements.get("火", 0) > 0:
                insight = {
                    "category": "事业",
                    "content": f"面相显示中年运势佳（中停比例{middle:.2%}），结合八字火旺（{five_elements.get('火', 0)}个），中年是事业发展的黄金期",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 中停比例={middle:.2%}（需 > 35%）或火元素={five_elements.get('火', 0)}（需 > 0）")
            
            # 下停长 + 八字晚年运
            logger.info(f"\n规则9: 下停 + 八字晚年运")
            logger.info(f"  检查: 下停比例={lower:.2%}, 土元素={five_elements.get('土', 0)}")
            if lower > 0.35 and five_elements.get("土", 0) > 0:
                insight = {
                    "category": "运势",
                    "content": f"面相显示晚年运势佳（下停比例{lower:.2%}），结合八字土旺（{five_elements.get('土', 0)}个），晚年生活幸福，有福气",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 下停比例={lower:.2%}（需 > 35%）或土元素={five_elements.get('土', 0)}（需 > 0）")
        
        # 打印最终结果
        logger.info("\n" + "-"*80)
        logger.info(f"【融合分析结果】")
        logger.info(f"  匹配到的规则数量: {len(integrated_insights)}")
        for i, insight in enumerate(integrated_insights, 1):
            logger.info(f"  {i}. [{insight['category']}] {insight['content']} (置信度: {insight['confidence']})")
        logger.info("="*80 + "\n")
        
        return integrated_insights
    
    def generate_recommendations(
        self,
        hand_insights: List[Dict[str, Any]],
        face_insights: List[Dict[str, Any]],
        integrated_insights: List[Dict[str, Any]]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 从洞察中提取建议
        all_insights = hand_insights + face_insights + integrated_insights
        
        # 按类别分组
        categories = {}
        for insight in all_insights:
            category = insight.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(insight.get("content", ""))
        
        # 生成建议
        if "健康" in categories:
            recommendations.append("健康：注意规律作息，适当运动，定期体检")
        
        if "财运" in categories:
            recommendations.append("财运：建议稳健理财，避免高风险投资")
        
        if "事业" in categories or "性格" in categories:
            recommendations.append("事业：根据性格特点选择适合的职业方向")
        
        if "学习" in categories:
            recommendations.append("学习：多读书，提升思维能力，早年开始积累")
        
        if "感情" in categories:
            recommendations.append("感情：注意情绪管理，多与人沟通")
        
        return recommendations


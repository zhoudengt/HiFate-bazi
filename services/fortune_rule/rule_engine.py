#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则引擎模块
基于传统命理学规则进行匹配
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
import json


class FortuneRuleEngine:
    """命理规则引擎（支持从数据库或硬编码加载规则）"""

    def __init__(self):
        try:
            from server.services.unified_rule_service import UnifiedRuleService
            self.hand_rules = UnifiedRuleService.get_rules("hand") or FortuneRuleEngine._load_hand_rules()
            self.face_rules = UnifiedRuleService.get_rules("face") or FortuneRuleEngine._load_face_rules()
        except Exception:
            self.hand_rules = FortuneRuleEngine._load_hand_rules()
            self.face_rules = FortuneRuleEngine._load_face_rules()

    @staticmethod
    def _load_hand_rules() -> Dict[str, Any]:
        """加载手相规则（硬编码兜底）"""
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

    @staticmethod
    def _load_face_rules() -> Dict[str, Any]:
        """加载面相规则（硬编码兜底）"""
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
        logger.info("\n" + "="*80)
        logger.info("🔍 手相规则匹配")
        logger.info("="*80)
        logger.info(f"手相特征: {hand_features}")
        insights = []
        
        # 手型规则（支持连续值，根据ratio和confidence个性化）
        hand_shape = hand_features.get("hand_shape", "")
        hand_shape_ratio = hand_features.get("hand_shape_ratio", 0.0)
        hand_shape_confidence = hand_features.get("hand_shape_confidence", 0.5)
        
        if hand_shape in self.hand_rules["hand_shape"]:
            rule = self.hand_rules["hand_shape"][hand_shape]
            base_confidence = 0.7 * hand_shape_confidence  # 根据手型识别置信度调整
            
            # 根据ratio和confidence调整内容详细程度
            if hand_shape_confidence > 0.8 and hand_shape_ratio > 0:  # 高置信度，详细分析
                for insight_text in rule.get("insights", []):
                    # 个性化内容：加入具体数值
                    personalized_content = f"{insight_text}（手型比例{hand_shape_ratio:.2f}，识别置信度{hand_shape_confidence:.1%}，特征明显）"
                    insights.append({
                        "category": "性格",
                        "content": personalized_content,
                        "confidence": base_confidence,
                        "source": "hand",
                        "feature": f"手型:{hand_shape}(ratio:{hand_shape_ratio:.2f},conf:{hand_shape_confidence:.2f})"
                    })
            else:  # 中低置信度，一般分析
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "性格",
                        "content": insight_text,
                        "confidence": base_confidence * 0.9,  # 降低置信度
                        "source": "hand",
                        "feature": f"手型:{hand_shape}(ratio:{hand_shape_ratio:.2f})"
                    })
        
        # 指长规则（使用连续值，根据数值差异生成个性化内容）
        finger_ratios = hand_features.get("finger_ratios", {})
        finger_lengths = hand_features.get("finger_lengths", {})
        
        # 分析指长特征组合（个性化内容生成）
        if finger_ratios:
            index_ratio = finger_ratios.get("index", 0)
            ring_ratio = finger_ratios.get("ring", 0)
            middle_ratio = finger_ratios.get("middle", 1.0)
            pinky_ratio = finger_ratios.get("pinky", 0)
            thumb_ratio = finger_ratios.get("thumb", 0)
            
            # 食指长于无名指（领导力）- 根据差异程度个性化
            if index_ratio > ring_ratio * 1.15:  # 差异很大（>15%）
                insights.append({
                    "category": "性格",
                    "content": f"食指明显长于无名指（比例{index_ratio:.2f} vs {ring_ratio:.2f}，差异{((index_ratio/ring_ratio-1)*100):.1f}%），领导才能突出，决策果断，适合担任管理职位或自主创业",
                    "confidence": 0.85,
                    "source": "hand",
                    "feature": f"指长比例:食指({index_ratio:.2f}) > 无名指({ring_ratio:.2f})"
                })
            elif index_ratio > ring_ratio * 1.05:  # 差异中等（5-15%）
                insights.append({
                    "category": "性格",
                    "content": f"食指略长于无名指（比例{index_ratio:.2f} vs {ring_ratio:.2f}，差异{((index_ratio/ring_ratio-1)*100):.1f}%），具有一定的领导潜质和决策能力，适合在团队中承担协调角色",
                    "confidence": 0.75,
                    "source": "hand",
                    "feature": f"指长比例:食指({index_ratio:.2f}) > 无名指({ring_ratio:.2f})"
                })
            
            # 无名指长于食指（艺术天赋）- 根据差异程度个性化
            if ring_ratio > index_ratio * 1.15:  # 差异很大（>15%）
                insights.append({
                    "category": "天赋",
                    "content": f"无名指明显长于食指（比例{ring_ratio:.2f} vs {index_ratio:.2f}，差异{((ring_ratio/index_ratio-1)*100):.1f}%），艺术天赋突出，创造力强，适合从事艺术、设计、创作类工作",
                    "confidence": 0.85,
                    "source": "hand",
                    "feature": f"指长比例:无名指({ring_ratio:.2f}) > 食指({index_ratio:.2f})"
                })
            elif ring_ratio > index_ratio * 1.05:  # 差异中等（5-15%）
                insights.append({
                    "category": "天赋",
                    "content": f"无名指略长于食指（比例{ring_ratio:.2f} vs {index_ratio:.2f}，差异{((ring_ratio/index_ratio-1)*100):.1f}%），具有一定的艺术天赋和创造力，适合从事创意类工作",
                    "confidence": 0.75,
                    "source": "hand",
                    "feature": f"指长比例:无名指({ring_ratio:.2f}) > 食指({index_ratio:.2f})"
                })
            
            # 中指分析（智慧、理性）
            if middle_ratio > 1.1:  # 中指明显长
                insights.append({
                    "category": "智慧",
                    "content": f"中指较长（比例{middle_ratio:.2f}），思维理性，逻辑分析能力强，适合从事技术、科研、法律等需要严谨思维的职业",
                    "confidence": 0.7,
                    "source": "hand",
                    "feature": f"中指比例:{middle_ratio:.2f}"
                })
            elif middle_ratio < 0.95:  # 中指较短
                insights.append({
                    "category": "性格",
                    "content": f"中指相对较短（比例{middle_ratio:.2f}），性格较为感性，注重直觉和感受，适合从事需要情感共鸣的工作",
                    "confidence": 0.65,
                    "source": "hand",
                    "feature": f"中指比例:{middle_ratio:.2f}"
                })
            
            # 小指分析（沟通能力）
            if pinky_ratio > 0.9:  # 小指较长
                insights.append({
                    "category": "性格",
                    "content": f"小指较长（比例{pinky_ratio:.2f}），沟通能力强，善于表达，适合从事销售、公关、教育等需要沟通的工作",
                    "confidence": 0.7,
                    "source": "hand",
                    "feature": f"小指比例:{pinky_ratio:.2f}"
                })
            elif pinky_ratio < 0.75:  # 小指较短
                insights.append({
                    "category": "性格",
                    "content": f"小指相对较短（比例{pinky_ratio:.2f}），性格较为内向，更注重实际行动而非言语表达",
                    "confidence": 0.65,
                    "source": "hand",
                    "feature": f"小指比例:{pinky_ratio:.2f}"
                })
            
            # 拇指分析（意志力）
            if thumb_ratio > 1.1:  # 拇指较长
                insights.append({
                    "category": "性格",
                    "content": f"拇指较长（比例{thumb_ratio:.2f}），意志力强，执行力好，做事有始有终，适合从事需要坚持和毅力的工作",
                    "confidence": 0.7,
                    "source": "hand",
                    "feature": f"拇指比例:{thumb_ratio:.2f}"
                })
            elif thumb_ratio < 0.9:  # 拇指较短
                insights.append({
                    "category": "性格",
                    "content": f"拇指相对较短（比例{thumb_ratio:.2f}），性格较为灵活，适应能力强，但需注意培养坚持力",
                    "confidence": 0.65,
                    "source": "hand",
                    "feature": f"拇指比例:{thumb_ratio:.2f}"
                })
        
        # 掌纹规则（增强版：支持更多分类，个性化内容）
        palm_lines = hand_features.get("palm_lines", {})
        line_count = palm_lines.get("line_count", "0")
        line_density = palm_lines.get("line_density", "")
        
        # 生命线（支持更多分类，个性化内容）
        life_line = palm_lines.get("life_line", "")
        if life_line and life_line != "无法检测":
            # 匹配规则（支持部分匹配）
            matched_rule = None
            for key in self.hand_rules["life_line"].keys():
                if key in life_line or life_line in key:
                    matched_rule = self.hand_rules["life_line"][key]
                    break
            
            if matched_rule:
                # 根据生命线特征强度个性化内容
                if "深且长" in life_line:
                    intensity = "非常"
                    confidence = 0.8
                elif "深" in life_line or "长" in life_line:
                    intensity = "较为"
                    confidence = 0.75
                else:
                    intensity = "一般"
                    confidence = 0.7
                
                for insight_text in matched_rule.get("insights", []):
                    personalized_content = f"{insight_text}（生命线特征：{life_line}，{intensity}明显）"
                    insights.append({
                        "category": "健康",
                        "content": personalized_content,
                        "confidence": confidence,
                        "source": "hand",
                        "feature": f"生命线:{life_line}"
                    })
        
        # 智慧线（支持更多分类，个性化内容）
        head_line = palm_lines.get("head_line", "")
        if head_line and head_line != "无法检测":
            matched_rule = None
            for key in self.hand_rules["head_line"].keys():
                if key in head_line or head_line in key:
                    matched_rule = self.hand_rules["head_line"][key]
                    break
            
            if matched_rule:
                # 根据智慧线特征强度个性化内容
                if "清晰" in head_line and ("深长" in head_line or "深" in head_line):
                    intensity = "非常"
                    confidence = 0.8
                elif "清晰" in head_line or "深长" in head_line:
                    intensity = "较为"
                    confidence = 0.75
                else:
                    intensity = "一般"
                    confidence = 0.7
                
                for insight_text in matched_rule.get("insights", []):
                    personalized_content = f"{insight_text}（智慧线特征：{head_line}，{intensity}明显）"
                    insights.append({
                        "category": "智慧",
                        "content": personalized_content,
                        "confidence": confidence,
                        "source": "hand",
                        "feature": f"智慧线:{head_line}"
                    })
        
        # 感情线（个性化内容）
        heart_line = palm_lines.get("heart_line", "")
        if heart_line and heart_line != "无法检测":
            matched_rule = None
            for key in self.hand_rules["heart_line"].keys():
                if key in heart_line or heart_line in key:
                    matched_rule = self.hand_rules["heart_line"][key]
                    break
            
            if matched_rule:
                # 根据感情线特征强度个性化内容
                if "明显深长" in heart_line or ("明显" in heart_line and "深长" in heart_line):
                    intensity = "非常"
                    confidence = 0.8
                elif "明显" in heart_line or "深长" in heart_line:
                    intensity = "较为"
                    confidence = 0.75
                else:
                    intensity = "一般"
                    confidence = 0.7
                
                for insight_text in matched_rule.get("insights", []):
                    personalized_content = f"{insight_text}（感情线特征：{heart_line}，{intensity}明显）"
                    insights.append({
                        "category": "感情",
                        "content": personalized_content,
                        "confidence": confidence,
                        "source": "hand",
                        "feature": f"感情线:{heart_line}"
                    })
        
        # 事业线（个性化内容）
        fate_line = palm_lines.get("fate_line", "")
        if fate_line and fate_line != "无法检测":
            if "明显" in fate_line or "深长" in fate_line:
                if "明显深长" in fate_line:
                    intensity = "非常"
                    confidence = 0.8
                else:
                    intensity = "较为"
                    confidence = 0.75
                
            insights.append({
                "category": "事业",
                    "content": f"事业线{intensity}明显（特征：{fate_line}），事业发展顺利，有较强的职业规划能力和执行力",
                    "confidence": confidence,
                "source": "hand",
                "feature": f"事业线:{fate_line}"
            })
        
        # 婚姻线（个性化内容）
        marriage_line = palm_lines.get("marriage_line", "")
        if marriage_line and marriage_line != "无法检测":
            if "明显" in marriage_line or "深长" in marriage_line:
                insights.append({
                    "category": "感情",
                    "content": f"婚姻线明显（特征：{marriage_line}），感情稳定，婚姻和谐，适合早婚",
                    "confidence": 0.7,
                    "source": "hand",
                    "feature": f"婚姻线:{marriage_line}"
                })
            elif "中等" in marriage_line:
                insights.append({
                    "category": "感情",
                    "content": f"婚姻线中等（特征：{marriage_line}），感情较为稳定，需注意沟通和理解",
                    "confidence": 0.65,
                    "source": "hand",
                    "feature": f"婚姻线:{marriage_line}"
                })
        
        # 掌纹密度分析（个性化）
        if line_count and line_count != "0":
            try:
                count = int(line_count)
                if count > 200:
                    insights.append({
                        "category": "性格",
                        "content": f"掌纹密集（共{count}条），思维活跃，想法较多，但需注意避免思虑过度，建议适当放松",
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"掌纹数量:{count}"
                    })
                elif count < 100:
                    insights.append({
                        "category": "性格",
                        "content": f"掌纹较少（共{count}条），性格较为简单直接，思维清晰，但需注意培养细致观察力",
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"掌纹数量:{count}"
                    })
            except:
                pass
        
        # 手掌纹理特征（个性化内容）
        palm_texture = hand_features.get("palm_texture", {})
        if palm_texture:
            roughness = palm_texture.get("roughness", "")
            wrinkle_density_raw = palm_texture.get("wrinkle_density", 0)
            
            # 确保 wrinkle_density 是数值类型
            try:
                if isinstance(wrinkle_density_raw, str):
                    wrinkle_density = float(wrinkle_density_raw)
                else:
                    wrinkle_density = float(wrinkle_density_raw)
            except (ValueError, TypeError):
                wrinkle_density = 0.0
            
            if roughness == "细腻":
                if wrinkle_density < 0.2:
                    insights.append({
                        "category": "性格",
                        "content": f"手掌纹理非常细腻（皱纹密度{wrinkle_density:.2f}），性格温和细致，注重细节，适合从事需要精细操作的工作",
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"纹理:{roughness},密度:{wrinkle_density:.2f}"
                    })
                else:
                    insights.append({
                        "category": "性格",
                        "content": f"手掌纹理细腻（皱纹密度{wrinkle_density:.2f}），性格温和，注重细节",
                        "confidence": 0.65,
                        "source": "hand",
                        "feature": f"纹理:{roughness}"
                    })
            elif roughness == "粗糙":
                if wrinkle_density > 0.5:
                    insights.append({
                        "category": "性格",
                        "content": f"手掌纹理较粗糙（皱纹密度{wrinkle_density:.2f}），性格豪爽直接，做事果断，适合从事需要决断力的工作",
                        "confidence": 0.7,
                        "source": "hand",
                        "feature": f"纹理:{roughness},密度:{wrinkle_density:.2f}"
                    })
                else:
                    insights.append({
                        "category": "性格",
                        "content": f"手掌纹理较粗糙（皱纹密度{wrinkle_density:.2f}），性格豪爽，做事果断",
                        "confidence": 0.65,
                        "source": "hand",
                        "feature": f"纹理:{roughness}"
                    })
        
        # 特殊标记（个性化内容）
        special_marks = hand_features.get("special_marks", [])
        if len(special_marks) > 0:
            mark_types = []
            for mark in special_marks:
                if isinstance(mark, dict):
                    mark_type = mark.get("type", "未知")
                    mark_types.append(mark_type)
                else:
                    mark_types.append(str(mark))
            
            if len(special_marks) >= 3:
                insights.append({
                    "category": "特殊",
                    "content": f"检测到 {len(special_marks)} 个特殊标记（类型：{', '.join(mark_types[:3])}），可能有特殊的命理意义，建议结合具体位置和类型进行详细分析",
                    "confidence": 0.7,
                    "source": "hand",
                    "feature": f"特殊标记数量:{len(special_marks)},类型:{mark_types}"
                })
            else:
                insights.append({
                    "category": "特殊",
                    "content": f"检测到 {len(special_marks)} 个特殊标记（类型：{', '.join(mark_types)}），可能有特殊的命理意义",
                    "confidence": 0.6,
                    "source": "hand",
                    "feature": f"特殊标记数量:{len(special_marks)}"
                })
        
        # ========== 组合规则：多特征组合分析（增加个性化）==========
        
        # 组合规则1: 手型 + 指长 + 掌纹组合
        if hand_shape and finger_ratios and palm_lines:
            # 长方形手 + 食指长 + 智慧线清晰 = 技术管理型
            if (hand_shape == "长方形手" and 
                finger_ratios.get("index", 0) > finger_ratios.get("ring", 0) * 1.05 and
                ("清晰" in palm_lines.get("head_line", "") or "深长" in palm_lines.get("head_line", ""))):
                insights.append({
                    "category": "事业",
                    "content": f"手型（{hand_shape}，ratio:{hand_shape_ratio:.2f}）+ 指长特征（食指长）+ 智慧线清晰，形成技术管理型特征，适合从事技术管理、项目管理、技术咨询等工作",
                    "confidence": 0.8,
                    "source": "hand",
                    "feature": f"组合:手型+指长+智慧线"
                })
            
            # 方形手 + 拇指长 + 生命线深长 = 稳健务实型
            if (hand_shape == "方形手" and
                finger_ratios.get("thumb", 0) > 1.0 and
                ("深" in palm_lines.get("life_line", "") or "长" in palm_lines.get("life_line", ""))):
                insights.append({
                    "category": "性格",
                    "content": f"手型（{hand_shape}，ratio:{hand_shape_ratio:.2f}）+ 拇指长（比例{finger_ratios.get('thumb', 0):.2f}）+ 生命线深长，形成稳健务实型特征，执行力强，适合从事工程、建筑、管理等需要坚持的工作",
                    "confidence": 0.8,
                    "source": "hand",
                    "feature": f"组合:手型+拇指+生命线"
                })
            
            # 圆形手 + 无名指长 + 感情线明显 = 艺术创意型
            if (hand_shape == "圆形手" and
                finger_ratios.get("ring", 0) > finger_ratios.get("index", 0) * 1.05 and
                ("明显" in palm_lines.get("heart_line", "") or "深长" in palm_lines.get("heart_line", ""))):
                insights.append({
                    "category": "天赋",
                    "content": f"手型（{hand_shape}）+ 无名指长（比例{finger_ratios.get('ring', 0):.2f}）+ 感情线明显，形成艺术创意型特征，情感丰富，创造力强，适合从事艺术、设计、创作类工作",
                    "confidence": 0.8,
                    "source": "hand",
                    "feature": f"组合:手型+无名指+感情线"
                })
        
        logger.info(f"✅ 手相规则匹配完成，共匹配到 {len(insights)} 条规则")
        logger.info("="*80 + "\n")
        return insights
    
    def match_face_rules(self, face_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """匹配面相规则（优化版：规则明确化，性能优化，内容丰富化）"""
        logger.info("\n" + "="*80)
        logger.info("🔍 面相规则匹配")
        logger.info("="*80)
        logger.info(f"面相特征: {face_features}")
        insights = []
        scanned_rules = []  # 记录所有扫描的规则
        max_insights = 25  # 性能优化：最多匹配25条规则
        
        # ========== 规则组1: 三停与运势 ==========
        san_ting = face_features.get("san_ting_ratio", {})
        upper = san_ting.get("upper", 0.33)
        middle = san_ting.get("middle", 0.33)
        lower = san_ting.get("lower", 0.34)
        
        # 规则1.1: 上停 + 早年运势（优化：降低阈值，增加中等情况分析）
        rule_name = "规则1.1: 上停 + 早年运势"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 上停对应早年运势，上停长则早年运势佳，学习能力强")
        logger.info(f"  检查: 上停比例={upper:.2%}")
        if len(insights) < max_insights:
            if upper > 0.38:  # 非常长
                intensity = "非常长"
                confidence = 0.85
                rule = self.face_rules["san_ting"]["upper_long"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "运势",
                        "content": f"{insight_text}（上停比例{upper:.2%}，{intensity}，早年运势极佳，学习能力突出，建议在20-30岁重点学习积累，打好基础）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"上停:{upper:.2%}"
                    })
                logger.info(f"  ✅ 匹配成功: 上停非常长，早年运势极佳")
            elif upper > 0.33:  # 较长（降低阈值从0.35到0.33）
                intensity = "较长"
                confidence = 0.75
                rule = self.face_rules["san_ting"]["upper_long"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "运势",
                        "content": f"{insight_text}（上停比例{upper:.2%}，{intensity}，早年运势较好，学习能力较强，建议在20-30岁重点学习积累）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"上停:{upper:.2%}"
                    })
                logger.info(f"  ✅ 匹配成功: 上停较长，早年运势较好")
            elif upper < 0.28:  # 较短
                insights.append({
                    "category": "运势",
                    "content": f"上停较短（比例{upper:.2%}），早年运势一般，建议通过学习和努力弥补，打好基础，可考虑在20-30岁重点学习，提升能力",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"上停:{upper:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 上停较短，需注意早年运势")
            else:  # 中等（28%-33%之间，添加托底分析）
                insights.append({
                    "category": "运势",
                    "content": f"上停比例适中（比例{upper:.2%}），早年运势平稳，建议在20-30岁通过学习和努力积累经验，为未来发展打好基础",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"上停:{upper:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 上停适中，早年运势平稳")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则1.2: 中停 + 中年运势（优化：降低阈值，增加中等情况分析）
        rule_name = "规则1.2: 中停 + 中年运势"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 中停对应中年运势，中停长则中年运势佳，事业发展好")
        logger.info(f"  检查: 中停比例={middle:.2%}")
        if len(insights) < max_insights:
            if middle > 0.38:  # 非常长
                intensity = "非常长"
                confidence = 0.85
                rule = self.face_rules["san_ting"]["middle_long"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "运势",
                        "content": f"{insight_text}（中停比例{middle:.2%}，{intensity}，中年运势极佳，事业发展顺利，建议在30-45岁重点发展事业，抓住机遇）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"中停:{middle:.2%}"
                    })
                logger.info(f"  ✅ 匹配成功: 中停非常长，中年运势极佳")
            elif middle > 0.33:  # 较长（降低阈值从0.35到0.33）
                intensity = "较长"
                confidence = 0.75
                rule = self.face_rules["san_ting"]["middle_long"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "运势",
                        "content": f"{insight_text}（中停比例{middle:.2%}，{intensity}，中年运势较好，事业发展顺利，建议在30-45岁重点发展事业）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"中停:{middle:.2%}"
                    })
                logger.info(f"  ✅ 匹配成功: 中停较长，中年运势较好")
            elif middle < 0.28:  # 较短
                insights.append({
                    "category": "运势",
                    "content": f"中停较短（比例{middle:.2%}），中年运势一般，建议在30-40岁重点发展事业，抓住机遇，持续学习和提升专业能力",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"中停:{middle:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 中停较短，需注意中年运势")
            else:  # 中等（28%-33%之间，添加托底分析）
                insights.append({
                    "category": "运势",
                    "content": f"中停比例适中（比例{middle:.2%}），中年运势平稳，建议在30-45岁重点发展事业，抓住机遇，持续学习和提升专业能力",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"中停:{middle:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 中停适中，中年运势平稳")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则1.3: 下停 + 晚年运势（优化：降低阈值，增加中等情况分析）
        rule_name = "规则1.3: 下停 + 晚年运势"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 下停对应晚年运势，下停长则晚年运势佳，福气深厚")
        logger.info(f"  检查: 下停比例={lower:.2%}")
        if len(insights) < max_insights:
            if lower > 0.38:  # 非常长
                intensity = "非常长"
                confidence = 0.85
                rule = self.face_rules["san_ting"]["lower_long"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "运势",
                        "content": f"{insight_text}（下停比例{lower:.2%}，{intensity}，晚年运势极佳，生活幸福，有福气，建议在年轻时多积累，为晚年做准备）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"下停:{lower:.2%}"
                    })
                logger.info(f"  ✅ 匹配成功: 下停非常长，晚年运势极佳")
            elif lower > 0.33:  # 较长（降低阈值从0.35到0.33）
                intensity = "较长"
                confidence = 0.75
                rule = self.face_rules["san_ting"]["lower_long"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "运势",
                        "content": f"{insight_text}（下停比例{lower:.2%}，{intensity}，晚年运势较好，生活幸福，建议在年轻时多积累，为晚年做准备）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"下停:{lower:.2%}"
                    })
                logger.info(f"  ✅ 匹配成功: 下停较长，晚年运势较好")
            elif lower < 0.28:  # 较短
                insights.append({
                    "category": "运势",
                    "content": f"下停较短（比例{lower:.2%}），晚年运势一般，建议在年轻时多积累，为晚年做准备，注重健康管理和财务规划",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"下停:{lower:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 下停较短，需注意晚年运势")
            else:  # 中等（28%-33%之间，添加托底分析）
                insights.append({
                    "category": "运势",
                    "content": f"下停比例适中（比例{lower:.2%}），晚年运势平稳，建议在年轻时多积累，为晚年做准备，注重健康管理和财务规划",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"下停:{lower:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 下停适中，晚年运势平稳")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组2: 五官与财运 ==========
        measurements = face_features.get("feature_measurements", {})
        
        # 规则2.1: 鼻子高挺 + 财运
        rule_name = "规则2.1: 鼻子高挺 + 财运"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        nose_height = measurements.get("nose_height", 0)
        nose_ratio = measurements.get("nose_ratio", 0)
        logger.info(f"  原理: 鼻子对应财运，鼻梁高挺则财运佳，适合投资理财")
        logger.info(f"  检查: 鼻子高度={nose_height:.1f}, 比例={nose_ratio:.2f}")
        if len(insights) < max_insights and nose_height > 0:
            # 根据面部高度归一化（更准确）
            face_height = measurements.get("face_height", 100)
            nose_relative = nose_height / max(face_height, 1.0) if face_height > 0 else 0
            
            if nose_relative > 0.15 or (nose_height > 60 and nose_ratio > 2.0):  # 高鼻梁
                if nose_ratio > 2.5:
                    intensity = "非常高挺"
                    confidence = 0.8
                elif nose_ratio > 2.0:
                    intensity = "高挺"
                    confidence = 0.75
                else:
                    intensity = "较高"
                    confidence = 0.7
                
                rule = self.face_rules["nose"]["high"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "财运",
                        "content": f"{insight_text}（鼻梁{intensity}，高度{nose_height:.1f}，比例{nose_ratio:.2f}）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"鼻子:高度{nose_height:.1f},比例{nose_ratio:.2f}"
                    })
                logger.info(f"  ✅ 匹配成功: 鼻梁{intensity}，财运佳")
            elif nose_relative < 0.10 or (nose_height < 40 and nose_ratio < 1.5):  # 低鼻梁
                rule = self.face_rules["nose"]["low"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "财运",
                        "content": f"{insight_text}（鼻梁较低，高度{nose_height:.1f}，比例{nose_ratio:.2f}）",
                        "confidence": 0.65,
                        "source": "face",
                        "feature": f"鼻子:高度{nose_height:.1f},比例{nose_ratio:.2f}"
                    })
                logger.info(f"  ✅ 匹配成功: 鼻梁较低，需注意理财")
            else:
                logger.info(f"  ❌ 未匹配: 鼻子特征不满足条件")
        elif nose_height == 0:
            logger.info(f"  ❌ 未匹配: 鼻子高度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组3: 五官与智慧 ==========
        
        # 规则3.1: 额头宽阔 + 智慧
        rule_name = "规则3.1: 额头宽阔 + 智慧"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        forehead_width = measurements.get("forehead_width", 0)
        forehead_ratio = measurements.get("forehead_ratio", 0)
        forehead_height = measurements.get("forehead_height", 0)
        logger.info(f"  原理: 额头对应智慧，额头宽阔则智慧过人，适合学习研究")
        logger.info(f"  检查: 额头宽度={forehead_width:.1f}, 比例={forehead_ratio:.2f}")
        if len(insights) < max_insights and forehead_width > 0:
            # 根据面部宽度归一化
            face_width = measurements.get("face_width", 100)
            forehead_relative = forehead_width / max(face_width, 1.0) if face_width > 0 else 0
            
            if forehead_relative > 0.85 or (forehead_width > 120 and forehead_ratio > 1.2):  # 宽阔额头
                if forehead_ratio > 1.5:
                    intensity = "非常宽阔"
                    confidence = 0.8
                elif forehead_ratio > 1.2:
                    intensity = "宽阔"
                    confidence = 0.75
                else:
                    intensity = "较宽"
                    confidence = 0.7
                
                rule = self.face_rules["forehead"]["wide"]
                for insight_text in rule.get("insights", []):
                    insights.append({
                        "category": "智慧",
                        "content": f"{insight_text}（额头{intensity}，宽度{forehead_width:.1f}，比例{forehead_ratio:.2f}）",
                        "confidence": confidence,
                        "source": "face",
                        "feature": f"额头:宽度{forehead_width:.1f},比例{forehead_ratio:.2f}"
                    })
                logger.info(f"  ✅ 匹配成功: 额头{intensity}，智慧过人")
            elif forehead_relative < 0.70 or (forehead_width < 80 and forehead_ratio < 0.9):  # 狭窄额头
                insights.append({
                    "category": "智慧",
                    "content": f"额头较窄（宽度{forehead_width:.1f}，比例{forehead_ratio:.2f}），建议多学习思考，提升思维能力",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"额头:宽度{forehead_width:.1f},比例{forehead_ratio:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 额头较窄，需加强学习")
            else:
                logger.info(f"  ❌ 未匹配: 额头特征不满足条件")
        elif forehead_width == 0:
            logger.info(f"  ❌ 未匹配: 额头宽度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组4: 五官与性格 ==========
        
        # 规则4.1: 眼睛大小 + 性格
        rule_name = "规则4.1: 眼睛大小 + 性格"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        eye_width = measurements.get("eye_width", 0)
        eye_symmetry = measurements.get("eye_symmetry", 0)
        logger.info(f"  原理: 眼睛对应性格和观察能力，眼睛大则性格开朗，善于观察")
        logger.info(f"  检查: 眼睛宽度={eye_width:.1f}, 对称性={eye_symmetry:.2f}")
        if len(insights) < max_insights and eye_width > 0:
            face_width = measurements.get("face_width", 100)
            eye_relative = eye_width / max(face_width, 1.0) if face_width > 0 else 0
            
            if eye_relative > 0.20:  # 大眼睛
                symmetry_desc = "对称" if eye_symmetry < 0.1 else "略不对称"
                insights.append({
                    "category": "性格",
                    "content": f"眼睛较大（宽度{eye_width:.1f}，相对比例{eye_relative:.2%}，{symmetry_desc}），性格开朗，善于观察，适合从事需要细致观察的工作",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"眼睛:宽度{eye_width:.1f},对称性{eye_symmetry:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 眼睛较大，性格开朗")
            elif eye_relative < 0.12:  # 小眼睛
                insights.append({
                    "category": "性格",
                    "content": f"眼睛较小（宽度{eye_width:.1f}，相对比例{eye_relative:.2%}），性格较为内敛，注重细节，适合从事需要专注的工作",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"眼睛:宽度{eye_width:.1f}"
                })
                logger.info(f"  ✅ 匹配成功: 眼睛较小，性格内敛")
            else:
                logger.info(f"  ❌ 未匹配: 眼睛特征不满足条件")
        elif eye_width == 0:
            logger.info(f"  ❌ 未匹配: 眼睛宽度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则4.2: 嘴巴大小 + 性格
        rule_name = "规则4.2: 嘴巴大小 + 性格"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        mouth_width = measurements.get("mouth_width", 0)
        logger.info(f"  原理: 嘴巴对应性格和表达能力，嘴巴大则性格外向，善于表达")
        logger.info(f"  检查: 嘴巴宽度={mouth_width:.1f}")
        if len(insights) < max_insights and mouth_width > 0:
            face_width = measurements.get("face_width", 100)
            mouth_relative = mouth_width / max(face_width, 1.0) if face_width > 0 else 0
            
            if mouth_relative > 0.45:  # 大嘴巴
                insights.append({
                    "category": "性格",
                    "content": f"嘴巴较大（宽度{mouth_width:.1f}，相对比例{mouth_relative:.2%}），性格外向，善于表达，适合从事需要沟通的工作",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"嘴巴:宽度{mouth_width:.1f}"
                })
                logger.info(f"  ✅ 匹配成功: 嘴巴较大，性格外向")
            elif mouth_relative < 0.30:  # 小嘴巴
                insights.append({
                    "category": "性格",
                    "content": f"嘴巴较小（宽度{mouth_width:.1f}，相对比例{mouth_relative:.2%}），性格较为内敛，注重实际，适合从事需要专注的工作",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"嘴巴:宽度{mouth_width:.1f}"
                })
                logger.info(f"  ✅ 匹配成功: 嘴巴较小，性格内敛")
            else:
                logger.info(f"  ❌ 未匹配: 嘴巴特征不满足条件")
        elif mouth_width == 0:
            logger.info(f"  ❌ 未匹配: 嘴巴宽度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则4.3: 面部比例 + 性格
        rule_name = "规则4.3: 面部比例 + 性格"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        face_ratio = measurements.get("face_ratio", 0)
        logger.info(f"  原理: 面部比例对应性格，圆脸温和，长脸理性")
        logger.info(f"  检查: 面部宽高比={face_ratio:.2f}")
        if len(insights) < max_insights and face_ratio > 0:
            if face_ratio > 0.75:  # 圆脸
                insights.append({
                    "category": "性格",
                    "content": f"面部较圆（宽高比{face_ratio:.2f}），性格温和，人际关系好，适合从事需要协调的工作",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"面部比例:{face_ratio:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 面部较圆，性格温和")
            elif face_ratio < 0.60:  # 长脸
                insights.append({
                    "category": "性格",
                    "content": f"面部较长（宽高比{face_ratio:.2f}），性格较为理性，思维严谨，适合从事需要分析的工作",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"面部比例:{face_ratio:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 面部较长，性格理性")
            else:
                logger.info(f"  ❌ 未匹配: 面部比例不满足条件")
        elif face_ratio == 0:
            logger.info(f"  ❌ 未匹配: 面部比例数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组5: 健康相关（新增）==========
        
        # 规则5.1: 面部对称性 + 健康
        rule_name = "规则5.1: 面部对称性 + 健康"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 面部对称性好则健康运势佳，对称性差则需注意健康")
        eye_symmetry = measurements.get("eye_symmetry", 0)
        face_width = measurements.get("face_width", 0)
        face_height = measurements.get("face_height", 0)
        logger.info(f"  检查: 眼睛对称性={eye_symmetry:.2f}, 面部宽度={face_width:.1f}, 高度={face_height:.1f}")
        if len(insights) < max_insights:
            # 计算面部对称性（简化：使用眼睛对称性作为参考）
            if eye_symmetry < 0.05:  # 非常对称
                insights.append({
                    "category": "健康",
                    "content": f"面部对称性良好（眼睛对称性{eye_symmetry:.2f}），健康运势佳，体质较好，建议保持规律作息和适当运动",
                    "confidence": 0.75,
                    "source": "face",
                    "feature": f"对称性:{eye_symmetry:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 面部对称性良好，健康运势佳")
            elif eye_symmetry > 0.15:  # 不对称
                insights.append({
                    "category": "健康",
                    "content": f"面部对称性一般（眼睛对称性{eye_symmetry:.2f}），需注意健康管理，建议定期体检，保持规律作息",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"对称性:{eye_symmetry:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 面部对称性一般，需注意健康")
            else:
                logger.info(f"  ❌ 未匹配: 对称性不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则5.2: 面部比例协调 + 健康
        rule_name = "规则5.2: 面部比例协调 + 健康"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 面部比例协调则健康运势好，比例失衡则需注意健康")
        face_ratio = measurements.get("face_ratio", 0)
        logger.info(f"  检查: 面部宽高比={face_ratio:.2f}")
        if len(insights) < max_insights and face_ratio > 0:
            if 0.60 <= face_ratio <= 0.75:  # 比例协调
                insights.append({
                    "category": "健康",
                    "content": f"面部比例协调（宽高比{face_ratio:.2f}），健康运势较好，体质均衡，建议保持规律作息和适当运动",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"面部比例:{face_ratio:.2f}"
                })
                logger.info(f"  ✅ 匹配成功: 面部比例协调，健康运势好")
            else:
                logger.info(f"  ❌ 未匹配: 面部比例不协调")
        elif face_ratio == 0:
            logger.info(f"  ❌ 未匹配: 面部比例数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组6: 学习相关（新增）==========
        
        # 规则6.1: 上停 + 额头 + 学习能力
        rule_name = "规则6.1: 上停 + 额头 + 学习能力"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 上停和额头对应学习能力，上停长且额头宽则学习能力强")
        forehead_relative = forehead_width / max(face_width, 1.0) if face_width > 0 and forehead_width > 0 else 0
        logger.info(f"  检查: 上停比例={upper:.2%}, 额头相对宽度={forehead_relative:.2%}")
        if len(insights) < max_insights:
            if upper > 0.35 and forehead_relative > 0.80:
                insights.append({
                    "category": "学习",
                    "content": f"上停较长（{upper:.2%}）且额头宽阔（相对宽度{forehead_relative:.2%}），学习能力极强，思维敏捷，适合早年开始积累，建议在20-30岁重点学习",
                    "confidence": 0.85,
                    "source": "face",
                    "feature": f"上停:{upper:.2%},额头:{forehead_relative:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 上停长且额头宽，学习能力极强")
            elif upper > 0.35 or forehead_relative > 0.80:
                insights.append({
                    "category": "学习",
                    "content": f"上停较长或额头宽阔，学习能力较强，建议多读书，提升思维能力，早年开始积累",
                    "confidence": 0.75,
                    "source": "face",
                    "feature": f"上停:{upper:.2%},额头:{forehead_relative:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 上停长或额头宽，学习能力较强")
            else:
                logger.info(f"  ❌ 未匹配: 上停或额头不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则6.2: 眼睛 + 观察能力 + 学习
        rule_name = "规则6.2: 眼睛 + 观察能力 + 学习"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 眼睛大则观察能力强，有助于学习")
        eye_relative = eye_width / max(face_width, 1.0) if face_width > 0 and eye_width > 0 else 0
        logger.info(f"  检查: 眼睛相对宽度={eye_relative:.2%}")
        if len(insights) < max_insights and eye_width > 0:
            if eye_relative > 0.20:
                insights.append({
                    "category": "学习",
                    "content": f"眼睛较大（相对宽度{eye_relative:.2%}），观察能力强，善于发现细节，有助于学习，建议多观察思考，提升学习效率",
                    "confidence": 0.7,
                    "source": "face",
                    "feature": f"眼睛:{eye_relative:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 眼睛较大，观察能力强")
            else:
                logger.info(f"  ❌ 未匹配: 眼睛不满足条件")
        elif eye_width == 0:
            logger.info(f"  ❌ 未匹配: 眼睛宽度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组7: 天赋相关（新增）==========
        
        # 规则7.1: 五官特征组合 + 艺术天赋
        rule_name = "规则7.1: 五官特征组合 + 艺术天赋"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 眼睛大、嘴巴适中、面部圆润则具有艺术天赋")
        eye_relative = eye_width / max(face_width, 1.0) if face_width > 0 and eye_width > 0 else 0
        mouth_relative = mouth_width / max(face_width, 1.0) if face_width > 0 and mouth_width > 0 else 0
        logger.info(f"  检查: 眼睛相对宽度={eye_relative:.2%}, 嘴巴相对宽度={mouth_relative:.2%}, 面部比例={face_ratio:.2f}")
        if len(insights) < max_insights:
            if (eye_relative > 0.18 and 0.30 < mouth_relative < 0.45 and face_ratio > 0.70):
                insights.append({
                    "category": "天赋",
                    "content": f"眼睛较大（{eye_relative:.2%}）+ 嘴巴适中（{mouth_relative:.2%}）+ 面部圆润（{face_ratio:.2f}），形成艺术天赋型特征，具有艺术天赋和创造力，适合从事艺术、设计、创作类工作",
                    "confidence": 0.8,
                    "source": "face",
                    "feature": f"组合:眼睛+嘴巴+面部"
                })
                logger.info(f"  ✅ 匹配成功: 艺术天赋型特征")
            else:
                logger.info(f"  ❌ 未匹配: 五官特征组合不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则7.2: 鼻子 + 额头 + 管理天赋
        rule_name = "规则7.2: 鼻子 + 额头 + 管理天赋"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 鼻子高挺且额头宽阔则具有管理天赋")
        nose_relative = nose_height / max(face_height, 1.0) if face_height > 0 and nose_height > 0 else 0
        forehead_relative = forehead_width / max(face_width, 1.0) if face_width > 0 and forehead_width > 0 else 0
        logger.info(f"  检查: 鼻子相对高度={nose_relative:.2%}, 额头相对宽度={forehead_relative:.2%}")
        if len(insights) < max_insights:
            if (nose_relative > 0.12 and nose_ratio > 2.0 and forehead_relative > 0.80):
                insights.append({
                    "category": "天赋",
                    "content": f"鼻梁高挺（相对高度{nose_relative:.2%}，比例{nose_ratio:.2f}）+ 额头宽阔（相对宽度{forehead_relative:.2%}），形成管理天赋型特征，具有管理才能和决策能力，适合从事管理、投资、创业等工作",
                    "confidence": 0.8,
                    "source": "face",
                    "feature": f"组合:鼻子+额头"
                })
                logger.info(f"  ✅ 匹配成功: 管理天赋型特征")
            else:
                logger.info(f"  ❌ 未匹配: 鼻子或额头不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组8: 感情相关（新增）==========
        
        # 规则8.1: 眼睛 + 感情
        rule_name = "规则8.1: 眼睛 + 感情"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 眼睛大则感情丰富，善于表达情感")
        eye_relative = eye_width / max(face_width, 1.0) if face_width > 0 and eye_width > 0 else 0
        logger.info(f"  检查: 眼睛相对宽度={eye_relative:.2%}")
        if len(insights) < max_insights and eye_width > 0:
            if eye_relative > 0.20:
                insights.append({
                    "category": "感情",
                    "content": f"眼睛较大（相对宽度{eye_relative:.2%}），感情丰富，善于表达情感，人际关系好，适合早婚，建议在25-30岁重点考虑感情问题",
                    "confidence": 0.75,
                    "source": "face",
                    "feature": f"眼睛:{eye_relative:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 眼睛较大，感情丰富")
            else:
                logger.info(f"  ❌ 未匹配: 眼睛不满足条件")
        elif eye_width == 0:
            logger.info(f"  ❌ 未匹配: 眼睛宽度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则8.2: 嘴巴 + 感情
        rule_name = "规则8.2: 嘴巴 + 感情"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 嘴巴适中则感情稳定，善于沟通")
        mouth_relative = mouth_width / max(face_width, 1.0) if face_width > 0 and mouth_width > 0 else 0
        logger.info(f"  检查: 嘴巴相对宽度={mouth_relative:.2%}")
        if len(insights) < max_insights and mouth_width > 0:
            if 0.30 < mouth_relative < 0.45:  # 适中
                insights.append({
                    "category": "感情",
                    "content": f"嘴巴适中（相对宽度{mouth_relative:.2%}），感情稳定，善于沟通，婚姻和谐，适合早婚，建议在25-30岁重点考虑婚姻",
                    "confidence": 0.75,
                    "source": "face",
                    "feature": f"嘴巴:{mouth_relative:.2%}"
                })
                logger.info(f"  ✅ 匹配成功: 嘴巴适中，感情稳定")
            else:
                logger.info(f"  ❌ 未匹配: 嘴巴不满足条件")
        elif mouth_width == 0:
            logger.info(f"  ❌ 未匹配: 嘴巴宽度数据为空")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # ========== 规则组9: 组合规则（完善）==========
        
        # 规则9.1: 上停长 + 额头宽 + 眼睛大 = 智慧学习型
        rule_name = "规则9.1: 上停+额头+眼睛 = 智慧学习型"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 上停长、额头宽、眼睛大形成智慧学习型特征")
        forehead_relative = forehead_width / max(face_width, 1.0) if face_width > 0 and forehead_width > 0 else 0
        eye_relative = eye_width / max(face_width, 1.0) if face_width > 0 and eye_width > 0 else 0
        logger.info(f"  检查: 上停={upper:.2%}, 额头={forehead_relative:.2%}, 眼睛={eye_relative:.2%}")
        if len(insights) < max_insights:
            if (upper > 0.35 and forehead_relative > 0.80 and eye_relative > 0.18):
                insights.append({
                    "category": "智慧",
                    "content": f"上停较长（{upper:.2%}）+ 额头宽阔（相对宽度{forehead_relative:.2%}）+ 眼睛较大（相对宽度{eye_relative:.2%}），形成智慧学习型特征，学习能力强，思维敏捷，适合从事教育、科研、技术等需要思考的职业",
                    "confidence": 0.85,
                    "source": "face",
                    "feature": f"组合:上停+额头+眼睛"
                })
                logger.info(f"  ✅ 匹配成功: 智慧学习型特征")
            else:
                logger.info(f"  ❌ 未匹配: 特征组合不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则9.2: 中停长 + 鼻子高 + 面部比例好 = 事业财运型
        rule_name = "规则9.2: 中停+鼻子+面部比例 = 事业财运型"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 中停长、鼻子高、面部比例协调形成事业财运型特征")
        nose_relative = nose_height / max(face_height, 1.0) if face_height > 0 and nose_height > 0 else 0
        logger.info(f"  检查: 中停={middle:.2%}, 鼻子相对高度={nose_relative:.2%}, 面部比例={face_ratio:.2f}")
        if len(insights) < max_insights:
            if (middle > 0.35 and nose_relative > 0.12 and 0.60 < face_ratio < 0.75):
                insights.append({
                    "category": "事业",
                    "content": f"中停较长（{middle:.2%}）+ 鼻梁高挺（相对高度{nose_relative:.2%}，比例{nose_ratio:.2f}）+ 面部比例协调（{face_ratio:.2f}），形成事业财运型特征，中年运势佳，事业发展顺利，适合从事管理、投资、创业等工作",
                    "confidence": 0.85,
                    "source": "face",
                    "feature": f"组合:中停+鼻子+面部比例"
                })
                logger.info(f"  ✅ 匹配成功: 事业财运型特征")
            else:
                logger.info(f"  ❌ 未匹配: 特征组合不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 规则9.3: 下停长 + 嘴巴适中 + 面部圆润 = 晚年福气型
        rule_name = "规则9.3: 下停+嘴巴+面部 = 晚年福气型"
        scanned_rules.append(rule_name)
        logger.info(f"\n{rule_name}")
        logger.info(f"  原理: 下停长、嘴巴适中、面部圆润形成晚年福气型特征")
        mouth_relative = mouth_width / max(face_width, 1.0) if face_width > 0 and mouth_width > 0 else 0
        logger.info(f"  检查: 下停={lower:.2%}, 嘴巴相对宽度={mouth_relative:.2%}, 面部比例={face_ratio:.2f}")
        if len(insights) < max_insights:
            if (lower > 0.35 and 0.30 < mouth_relative < 0.45 and face_ratio > 0.70):
                insights.append({
                    "category": "运势",
                    "content": f"下停较长（{lower:.2%}）+ 嘴巴适中（相对宽度{mouth_relative:.2%}）+ 面部圆润（{face_ratio:.2f}），形成晚年福气型特征，晚年运势佳，生活幸福，有福气，建议在年轻时多积累，为晚年做准备",
                    "confidence": 0.8,
                    "source": "face",
                    "feature": f"组合:下停+嘴巴+面部"
                })
                logger.info(f"  ✅ 匹配成功: 晚年福气型特征")
            else:
                logger.info(f"  ❌ 未匹配: 特征组合不满足条件")
        else:
            logger.info(f"  ⏭️  跳过: 已达到最大规则数限制")
        
        # 特殊特征分析（如果有）
        special_features = face_features.get("special_features", [])
        if len(special_features) > 0 and len(insights) < max_insights:
            rule_name = "规则10.1: 特殊特征分析"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 特殊特征可能有特殊的命理意义")
            # 按区域分组
            regions = {}
            for feature in special_features:
                if isinstance(feature, dict):
                    region = feature.get("region", "未知")
                    if region not in regions:
                        regions[region] = []
                    regions[region].append(feature)
            
            for region, features_list in regions.items():
                if len(features_list) >= 2:
                    insights.append({
                        "category": "特殊",
                        "content": f"{region}检测到{len(features_list)}个特殊特征，可能有特殊的命理意义，建议结合具体位置和类型进行详细分析",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"特殊特征:{region},{len(features_list)}个"
                    })
                    logger.info(f"  ✅ 匹配成功: {region}检测到{len(features_list)}个特殊特征")
                else:
                    insights.append({
                        "category": "特殊",
                        "content": f"{region}检测到特殊特征，可能有特殊的命理意义",
                    "confidence": 0.6,
                        "source": "face",
                        "feature": f"特殊特征:{region}"
                })
                    logger.info(f"  ✅ 匹配成功: {region}检测到特殊特征")
        
        # 托底方案：如果匹配到的规则太少，生成基础分析
        if len(insights) < 5:
            logger.info(f"\n⚠️  匹配到的规则较少（{len(insights)}条），启用托底方案生成基础分析...")
            
            # 基于三停比例生成基础分析
            if upper > 0 and middle > 0 and lower > 0:
                # 分析三停平衡度
                balance_score = 1.0 - (max(upper, middle, lower) - min(upper, middle, lower))
                if balance_score > 0.95:
                    insights.append({
                        "category": "运势",
                        "content": f"三停比例均衡（上停{upper:.2%}，中停{middle:.2%}，下停{lower:.2%}），整体运势平稳，早年、中年、晚年运势较为均衡，建议在各个阶段都保持积极向上的心态，持续学习和提升自己",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"三停均衡:上{upper:.2%},中{middle:.2%},下{lower:.2%}"
                    })
                    logger.info(f"  ✅ 托底分析: 三停比例均衡")
                elif upper > middle and upper > lower:
                    insights.append({
                        "category": "运势",
                        "content": f"上停相对较长（上停{upper:.2%}，中停{middle:.2%}，下停{lower:.2%}），早年运势较好，学习能力较强，建议在20-30岁重点学习积累，打好基础，为未来发展做准备",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"上停较长:上{upper:.2%},中{middle:.2%},下{lower:.2%}"
                    })
                    logger.info(f"  ✅ 托底分析: 上停相对较长")
                elif middle > upper and middle > lower:
                    insights.append({
                        "category": "运势",
                        "content": f"中停相对较长（上停{upper:.2%}，中停{middle:.2%}，下停{lower:.2%}），中年运势较好，事业发展顺利，建议在30-45岁重点发展事业，抓住机遇，持续学习和提升专业能力",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"中停较长:上{upper:.2%},中{middle:.2%},下{lower:.2%}"
                    })
                    logger.info(f"  ✅ 托底分析: 中停相对较长")
                elif lower > upper and lower > middle:
                    insights.append({
                        "category": "运势",
                        "content": f"下停相对较长（上停{upper:.2%}，中停{middle:.2%}，下停{lower:.2%}），晚年运势较好，生活幸福，有福气，建议在年轻时多积累，为晚年做准备，注重健康管理和财务规划",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"下停较长:上{upper:.2%},中{middle:.2%},下{lower:.2%}"
                    })
                    logger.info(f"  ✅ 托底分析: 下停相对较长")
            
            # 基于面部比例生成基础分析
            face_ratio = measurements.get("face_ratio", 0)
            if face_ratio > 0:
                if face_ratio > 0.75:
                    insights.append({
                        "category": "性格",
                        "content": f"面部较圆（宽高比{face_ratio:.2f}），性格温和，人际关系好，善于协调，适合从事需要团队合作和协调的工作，建议在人际交往中发挥优势，建立良好的人脉关系",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"面部比例:{face_ratio:.2f}"
                    })
                elif face_ratio < 0.60:
                    insights.append({
                        "category": "性格",
                        "content": f"面部较长（宽高比{face_ratio:.2f}），性格较为理性，思维严谨，适合从事需要分析和思考的工作，建议在工作中发挥逻辑思维优势，注重细节和规划",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"面部比例:{face_ratio:.2f}"
                    })
                else:
                    insights.append({
                        "category": "性格",
                        "content": f"面部比例协调（宽高比{face_ratio:.2f}），性格平衡，既有理性思维也有感性表达，适合从事需要综合能力的工作，建议在工作中发挥综合优势，注重平衡发展",
                        "confidence": 0.7,
                        "source": "face",
                        "feature": f"面部比例:{face_ratio:.2f}"
                    })
            
            # 如果还是没有足够的洞察，生成通用分析
            if len(insights) < 3:
                insights.append({
                    "category": "综合",
                    "content": f"根据面相分析，三停比例较为均衡（上停{upper:.2%}，中停{middle:.2%}，下停{lower:.2%}），整体运势平稳，建议在各个阶段都保持积极向上的心态，持续学习和提升自己，注重健康管理，抓住机遇，为未来发展做好准备",
                    "confidence": 0.65,
                    "source": "face",
                    "feature": f"综合:上{upper:.2%},中{middle:.2%},下{lower:.2%}"
                })
                logger.info(f"  ✅ 托底分析: 生成通用综合分析")
        
        # 合并和提炼重复内容
        insights = self._merge_and_refine_insights(insights)
        
        # 打印最终结果
        logger.info("\n" + "-"*80)
        logger.info(f"【面相规则匹配结果】")
        logger.info(f"  扫描的规则总数: {len(scanned_rules)}")
        logger.info(f"  匹配成功的规则数（合并前）: {len(insights)}")
        logger.info(f"  合并后的规则数: {len(insights)}")
        logger.info(f"\n  扫描的规则列表:")
        for i, rule in enumerate(scanned_rules, 1):
            logger.info(f"    {i}. {rule}")
        logger.info(f"\n  匹配成功的规则（合并后）:")
        for i, insight in enumerate(insights, 1):
            logger.info(f"    {i}. [{insight['category']}] {insight['content']} (置信度: {insight['confidence']})")
        logger.info("="*80)
        logger.info(f"✅ 面相规则匹配完成，共扫描 {len(scanned_rules)} 条规则，匹配到 {len(insights)} 条规则（已合并去重）\n")
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
        ten_gods_raw = bazi_data.get("ten_gods_stats", {})
        bazi_pillars = bazi_data.get("bazi_pillars", {})
        
        # 解析十神统计（ten_gods_stats 可能是嵌套结构，包含 JSON 字符串）
        ten_gods = {}
        if isinstance(ten_gods_raw, dict):
            # 尝试从 totals 字段解析（最常见的情况）
            if "totals" in ten_gods_raw:
                totals_str = ten_gods_raw.get("totals", "")
                if isinstance(totals_str, str):
                    try:
                        # 将单引号替换为双引号，然后解析 JSON
                        totals_dict = json.loads(totals_str.replace("'", '"'))
                        # 提取每个十神的 count
                        for god_name, god_info in totals_dict.items():
                            if isinstance(god_info, dict) and "count" in god_info:
                                ten_gods[god_name] = god_info["count"]
                    except Exception as e:
                        logger.info(f"  ⚠️  解析 totals 失败: {e}")
            
            # 如果 totals 解析失败，尝试从 ten_gods_total 解析
            if not ten_gods and "ten_gods_total" in ten_gods_raw:
                total_str = ten_gods_raw.get("ten_gods_total", "")
                if isinstance(total_str, str):
                    try:
                        total_dict = json.loads(total_str.replace("'", '"'))
                        for god_name, god_info in total_dict.items():
                            if isinstance(god_info, dict) and "count" in god_info:
                                ten_gods[god_name] = god_info["count"]
                    except Exception as e:
                        logger.info(f"  ⚠️  解析 ten_gods_total 失败: {e}")
            
            # 如果还是解析失败，尝试直接使用（可能是简单字典）
            if not ten_gods:
                for k, v in ten_gods_raw.items():
                    if isinstance(v, (int, float)):
                        ten_gods[k] = int(v)
                    elif isinstance(v, str) and v.isdigit():
                        ten_gods[k] = int(v)
        
        logger.info("\n【八字数据】")
        logger.info(f"  五行统计: {five_elements}")
        logger.info(f"  十神统计（原始）: {ten_gods_raw}")
        logger.info(f"  十神统计（解析后）: {ten_gods}")
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
        
        # 五行对应关系（传统命理学）
        element_mapping = {
            "木": {"organs": "肝胆", "color": "绿色", "direction": "东方", "nature": "生发、向上"},
            "火": {"organs": "心脏", "color": "红色", "direction": "南方", "nature": "热情、向上"},
            "土": {"organs": "脾胃", "color": "黄色", "direction": "中央", "nature": "稳定、承载"},
            "金": {"organs": "肺", "color": "白色", "direction": "西方", "nature": "收敛、刚强"},
            "水": {"organs": "肾", "color": "黑色", "direction": "北方", "nature": "流动、智慧"}
        }
        
        # 记录所有扫描的规则
        scanned_rules = []
        
        # 手相 + 八字融合（基于传统命理学原理）
        if hand_features:
            hand_shape = hand_features.get("hand_shape", "")
            hand_shape_ratio = hand_features.get("hand_shape_ratio", 0.0)
            life_line = hand_features.get("palm_lines", {}).get("life_line", "")
            head_line = hand_features.get("palm_lines", {}).get("head_line", "")
            heart_line = hand_features.get("palm_lines", {}).get("heart_line", "")
            finger_ratios = hand_features.get("finger_ratios", {})
            
            # ========== 规则组1: 手型与五行融合（基于传统命理学对应关系）==========
            
            # 规则1.1: 方形手 + 金元素（金主收敛、刚强，方形手主稳重，同属性增强）
            rule_name = "规则1.1: 方形手 + 金元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 方形手对应金、土，金旺则财运佳，适合金融、管理")
            logger.info(f"  检查: hand_shape='{hand_shape}', 金元素={five_elements.get('金', 0)}, ratio={hand_shape_ratio:.2f}")
            if hand_shape == "方形手" and five_elements.get("金", 0) > 0:
                gold_count = five_elements.get("金", 0)
                if gold_count >= 3:
                    gold_desc = f"金元素非常旺（{gold_count}个）"
                    career_advice = "强烈建议从事金融、投资、银行、证券等与金相关的行业，财运极佳"
                    confidence = 0.9
                elif gold_count >= 2:
                    gold_desc = f"金元素较旺（{gold_count}个）"
                    career_advice = "建议从事金融、投资、管理相关行业，财运较好"
                    confidence = 0.85
                else:
                    gold_desc = f"金元素一般（{gold_count}个）"
                    career_advice = "可以考虑从事金融、管理相关行业，有一定财运"
                    confidence = 0.8
                
                if hand_shape_ratio >= 0.75:
                    shape_desc = "非常方正"
                elif hand_shape_ratio >= 0.7:
                    shape_desc = "较为方正"
                else:
                    shape_desc = "略为方正"
                
                insight = {
                    "category": "财运",
                    "content": f"手相显示财运佳（{shape_desc}的方形手，ratio:{hand_shape_ratio:.2f}），结合八字{gold_desc}，金主收敛刚强，{career_advice}，建议在35-50岁重点发展财运",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='方形手'且金元素 > 0")
            
            # 规则1.2: 方形手 + 土元素（土主稳定、承载，方形手主稳重，同属性增强）
            rule_name = "规则1.2: 方形手 + 土元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 方形手对应金、土，土旺则稳定务实，适合工程、建筑")
            logger.info(f"  检查: hand_shape='{hand_shape}', 土元素={five_elements.get('土', 0)}")
            if hand_shape == "方形手" and five_elements.get("土", 0) >= 2:
                insight = {
                    "category": "事业",
                    "content": f"手相显示性格稳重（方形手，ratio:{hand_shape_ratio:.2f}），结合八字土旺（{five_elements.get('土', 0)}个），土主稳定承载，适合从事工程、建筑、管理类工作",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='方形手'且土元素 >= 2")
            
            # 规则1.3: 长方形手 + 木元素（木主生发、向上，长方形手主理性分析，同属性增强）
            rule_name = "规则1.3: 长方形手 + 木元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 长方形手对应木、金，木旺则思维活跃，适合技术、科研")
            logger.info(f"  检查: hand_shape='{hand_shape}', 木元素={five_elements.get('木', 0)}, ratio={hand_shape_ratio:.2f}")
            if hand_shape == "长方形手" and five_elements.get("木", 0) > 0:
                wood_count = five_elements.get("木", 0)
                if wood_count >= 3:
                    wood_desc = f"木元素非常旺（{wood_count}个）"
                    learning_advice = "学习能力极强，思维非常活跃"
                    confidence = 0.9
                elif wood_count >= 2:
                    wood_desc = f"木元素较旺（{wood_count}个）"
                    learning_advice = "学习能力较强，思维活跃"
                    confidence = 0.85
                else:
                    wood_desc = f"木元素一般（{wood_count}个）"
                    learning_advice = "学习能力较好，思维较为活跃"
                    confidence = 0.8
                
                if hand_shape_ratio < 0.5:
                    shape_desc = "非常修长"
                elif hand_shape_ratio < 0.55:
                    shape_desc = "较为修长"
                else:
                    shape_desc = "略为修长"
                
                insight = {
                    "category": "学习",
                    "content": f"手相显示理性分析（{shape_desc}的长方形手，ratio:{hand_shape_ratio:.2f}），结合八字{wood_desc}，木主生发向上，{learning_advice}，适合从事技术、科研、法律类工作，建议在25-40岁重点发展专业技能",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='长方形手'且木元素 > 0")
            
            # 规则1.4: 长方形手 + 金元素（金主收敛、刚强，长方形手主理性，同属性增强）
            rule_name = "规则1.4: 长方形手 + 金元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 长方形手对应木、金，金旺则逻辑思维强，适合金融、技术")
            logger.info(f"  检查: hand_shape='{hand_shape}', 金元素={five_elements.get('金', 0)}, ratio={hand_shape_ratio:.2f}")
            if hand_shape == "长方形手" and five_elements.get("金", 0) > 0:
                gold_count = five_elements.get("金", 0)
                if gold_count >= 3:
                    gold_desc = f"金元素非常旺（{gold_count}个）"
                    logic_desc = "逻辑思维极强"
                    confidence = 0.85
                elif gold_count >= 2:
                    gold_desc = f"金元素较旺（{gold_count}个）"
                    logic_desc = "逻辑思维较强"
                    confidence = 0.8
                else:
                    gold_desc = f"金元素一般（{gold_count}个）"
                    logic_desc = "逻辑思维较好"
                    confidence = 0.75
                
                insight = {
                    "category": "财运",
                    "content": f"手相显示{logic_desc}（长方形手，ratio:{hand_shape_ratio:.2f}），结合八字{gold_desc}，金主收敛刚强，适合从事金融分析、技术分析、投资研究等需要逻辑思维的工作，建议在30-45岁重点发展",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='长方形手'且金元素 > 0")
            
            # 规则1.5: 圆形手 + 水元素（水主流动、智慧，圆形手主灵活，同属性增强）
            rule_name = "规则1.5: 圆形手 + 水元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 圆形手对应水、木，水旺则适应能力强，适合创意、营销")
            logger.info(f"  检查: hand_shape='{hand_shape}', 水元素={five_elements.get('水', 0)}")
            if hand_shape == "圆形手" and five_elements.get("水", 0) > 0:
                insight = {
                    "category": "性格",
                    "content": f"手相显示性格灵活（圆形手），结合八字水旺（{five_elements.get('水', 0)}个），水主流动智慧，适应能力强，适合从事创意、营销、设计类职业",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='圆形手'且水元素 > 0")
            
            # 规则1.6: 圆形手 + 木元素（木主生发、向上，圆形手主灵活，相生关系）
            rule_name = "规则1.6: 圆形手 + 木元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 圆形手对应水、木，木旺则思维活跃，适合艺术、设计")
            logger.info(f"  检查: hand_shape='{hand_shape}', 木元素={five_elements.get('木', 0)}")
            if hand_shape == "圆形手" and five_elements.get("木", 0) > 0:
                insight = {
                    "category": "天赋",
                    "content": f"手相显示思维活跃（圆形手），结合八字木旺（{five_elements.get('木', 0)}个），木主生发向上，适合从事艺术、设计、创意类工作",
                    "confidence": 0.7,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='圆形手'且木元素 > 0")
            
            # 规则1.7: 尖形手 + 火元素（火主热情、向上，尖形手主理想主义，同属性增强）
            rule_name = "规则1.7: 尖形手 + 火元素"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 尖形手对应火，火旺则热情向上，适合艺术、教育")
            logger.info(f"  检查: hand_shape='{hand_shape}', 火元素={five_elements.get('火', 0)}")
            if hand_shape == "尖形手" and five_elements.get("火", 0) > 0:
                insight = {
                    "category": "天赋",
                    "content": f"手相显示理想主义（尖形手），结合八字火旺（{five_elements.get('火', 0)}个），火主热情向上，适合从事艺术、教育、创作类职业",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需手型='尖形手'且火元素 > 0")
            
            # ========== 规则组2: 掌纹与五行融合（基于传统命理学对应关系）==========
            
            # 规则2.1: 生命线 + 土元素（生命线对应土，土主稳定承载，健康根基）
            rule_name = "规则2.1: 生命线 + 土元素（健康根基）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 生命线对应土，土旺则健康根基稳固，土弱则需注意脾胃")
            logger.info(f"  检查: life_line='{life_line}', 土元素={five_elements.get('土', 0)}")
            if "深" in life_line or "长" in life_line:
                earth_count = five_elements.get("土", 0)
                
                # 判断生命线强度
                if "深且长" in life_line or ("深" in life_line and "长" in life_line):
                    line_intensity = "非常深长"
                    line_confidence = 0.85
                elif "深" in life_line:
                    line_intensity = "较深"
                    line_confidence = 0.8
                else:
                    line_intensity = "较长"
                    line_confidence = 0.75
                
                if earth_count < 2:
                    insight = {
                        "category": "健康",
                        "content": f"手相显示健康运势佳（生命线{line_intensity}，特征：{life_line}），但八字土弱（{earth_count}个），土主脾胃，建议特别注意脾胃健康，规律饮食，避免暴饮暴食，建议每年体检时重点检查消化系统",
                        "confidence": line_confidence * 0.9,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（土弱）: {insight['content']}")
                elif earth_count >= 3:
                    insight = {
                        "category": "健康",
                        "content": f"手相显示健康运势佳（生命线{line_intensity}，特征：{life_line}），八字土旺（{earth_count}个），土主稳定承载，体质较好，健康根基稳固，但需注意消化系统，建议规律作息，适当运动",
                        "confidence": line_confidence,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（土旺）: {insight['content']}")
                else:
                    insight = {
                        "category": "健康",
                        "content": f"手相显示健康运势较好（生命线{line_intensity}，特征：{life_line}），八字土元素适中（{earth_count}个），建议保持规律作息，适当运动，注意脾胃保养",
                        "confidence": line_confidence * 0.85,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（土适中）: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 生命线不满足条件（需包含'深'或'长'）")
            
            # 规则2.2: 智慧线 + 木元素（智慧线对应木，木主生发向上，学习思维）
            rule_name = "规则2.2: 智慧线 + 木元素（学习思维）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 智慧线对应木，木旺则学习能力强，思维敏捷")
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
            
            # 规则2.3: 感情线 + 十神（感情线对应水、火，正官正财主稳定和谐）
            rule_name = "规则2.3: 感情线 + 十神（感情婚姻）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 感情线对应水、火，正官正财主感情稳定，婚姻和谐")
            logger.info(f"  检查: heart_line='{heart_line}', 正官={ten_gods.get('正官', 0)}, 正财={ten_gods.get('正财', 0)}")
            if "明显" in heart_line or "深长" in heart_line:
                zheng_guan = ten_gods.get("正官", 0)
                zheng_cai = ten_gods.get("正财", 0)
                
                # 判断感情线强度
                if "明显深长" in heart_line or ("明显" in heart_line and "深长" in heart_line):
                    line_intensity = "非常明显深长"
                    line_confidence = 0.85
                elif "明显" in heart_line:
                    line_intensity = "较为明显"
                    line_confidence = 0.8
                else:
                    line_intensity = "较长"
                    line_confidence = 0.75
                
                if zheng_guan > 0 or zheng_cai > 0:
                    # 根据十神数量个性化
                    if zheng_guan >= 2 and zheng_cai >= 1:
                        god_desc = f"正官较旺（{zheng_guan}个）且正财有（{zheng_cai}个）"
                        marriage_desc = "感情非常稳定，婚姻极其和谐，适合早婚"
                        confidence = 0.9
                    elif zheng_guan >= 2:
                        god_desc = f"正官较旺（{zheng_guan}个）"
                        marriage_desc = "感情稳定，婚姻和谐，适合早婚"
                        confidence = 0.85
                    elif zheng_cai >= 2:
                        god_desc = f"正财较旺（{zheng_cai}个）"
                        marriage_desc = "感情稳定，婚姻和谐，适合早婚"
                        confidence = 0.85
                    elif zheng_guan > 0:
                        god_desc = f"正官有（{zheng_guan}个）"
                        marriage_desc = "感情较为稳定，婚姻和谐"
                        confidence = 0.8
                    else:
                        god_desc = f"正财有（{zheng_cai}个）"
                        marriage_desc = "感情较为稳定，婚姻和谐"
                        confidence = 0.8
                    
                    insight = {
                        "category": "感情",
                        "content": f"手相显示感情丰富（感情线{line_intensity}，特征：{heart_line}），结合八字{god_desc}，{marriage_desc}，建议在25-30岁重点考虑婚姻，婚后注意沟通和理解",
                        "confidence": confidence,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功: {insight['content']}")
                else:
                    logger.info(f"  ❌ 未匹配: 感情线满足条件，但正官={zheng_guan}, 正财={zheng_cai}（需至少一个 > 0）")
            else:
                logger.info(f"  ❌ 未匹配: 感情线不满足条件（需包含'明显'或'深长'）")
            
            # 规则2.4: 事业线 + 金元素（事业线对应金、火，金主收敛刚强，事业成就）
            rule_name = "规则2.4: 事业线 + 金元素（事业成就）"
            scanned_rules.append(rule_name)
            fate_line = hand_features.get("palm_lines", {}).get("fate_line", "")
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 事业线对应金、火，金旺则事业有成，适合管理、金融")
            logger.info(f"  检查: fate_line='{fate_line}', 金元素={five_elements.get('金', 0)}")
            if ("明显" in fate_line or "深长" in fate_line) and five_elements.get("金", 0) > 0:
                insight = {
                    "category": "事业",
                    "content": f"手相显示事业运势佳（事业线{fate_line}），结合八字金旺（{five_elements.get('金', 0)}个），金主收敛刚强，事业有成，适合从事管理、金融、投资相关行业",
                    "confidence": 0.75,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需事业线包含'明显'或'深长'且金元素 > 0")
            
            # ========== 规则组3: 指长与五行融合（基于传统命理学对应关系）==========
            
            # 规则3.1: 指长比例 + 五行天赋（个性化内容）
            rule_name = "规则3.1: 指长比例 + 五行天赋"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            if finger_ratios:
                index_ratio = finger_ratios.get("index", 0)
                ring_ratio = finger_ratios.get("ring", 0)
                middle_ratio = finger_ratios.get("middle", 1.0)
                gold_count = five_elements.get("金", 0)
                wood_count = five_elements.get("木", 0)
                logger.info(f"  检查: 食指比例={index_ratio:.2f}, 无名指比例={ring_ratio:.2f}, 中指比例={middle_ratio:.2f}, 金元素={gold_count}, 木元素={wood_count}")
                
                # 食指长 + 金元素（根据差异程度个性化）
                if index_ratio > ring_ratio * 1.05 and gold_count > 0:
                    diff_pct = ((index_ratio / ring_ratio - 1) * 100)
                    if diff_pct > 15:
                        intensity = "非常突出"
                        confidence = 0.85
                    elif diff_pct > 10:
                        intensity = "较为明显"
                        confidence = 0.8
                    else:
                        intensity = "略为明显"
                        confidence = 0.75
                    
                    if gold_count >= 3:
                        gold_desc = f"金元素很旺（{gold_count}个）"
                    elif gold_count >= 2:
                        gold_desc = f"金元素较旺（{gold_count}个）"
                    else:
                        gold_desc = f"金元素一般（{gold_count}个）"
                    
                    insight = {
                        "category": "天赋",
                        "content": f"手相显示领导才能{intensity}（食指长于无名指{diff_pct:.1f}%），结合八字{gold_desc}，金主收敛刚强，适合管理、金融、投资类工作，建议在30-40岁重点发展事业",
                        "confidence": confidence,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（食指长）: {insight['content']}")
                
                # 无名指长 + 木元素（根据差异程度个性化）
                elif ring_ratio > index_ratio * 1.05 and wood_count > 0:
                    diff_pct = ((ring_ratio / index_ratio - 1) * 100)
                    if diff_pct > 15:
                        intensity = "非常突出"
                        confidence = 0.85
                    elif diff_pct > 10:
                        intensity = "较为明显"
                        confidence = 0.8
                    else:
                        intensity = "略为明显"
                        confidence = 0.75
                    
                    if wood_count >= 3:
                        wood_desc = f"木元素很旺（{wood_count}个）"
                    elif wood_count >= 2:
                        wood_desc = f"木元素较旺（{wood_count}个）"
                    else:
                        wood_desc = f"木元素一般（{wood_count}个）"
                    
                    insight = {
                        "category": "天赋",
                        "content": f"手相显示艺术天赋{intensity}（无名指长于食指{diff_pct:.1f}%），结合八字{wood_desc}，木主生发向上，适合艺术、设计、创意类工作，建议在25-35岁重点发展创作能力",
                        "confidence": confidence,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（无名指长）: {insight['content']}")
                
                # 中指长 + 木元素（新增）
                elif middle_ratio > 1.1 and wood_count > 0:
                    insight = {
                        "category": "智慧",
                        "content": f"手相显示理性思维强（中指较长，比例{middle_ratio:.2f}），结合八字木旺（{wood_count}个），木主生发向上，学习能力强，适合从事技术、科研、法律等需要严谨思维的职业",
                        "confidence": 0.75,
                        "source": "integrated"
                    }
                    integrated_insights.append(insight)
                    logger.info(f"  ✅ 匹配成功（中指长）: {insight['content']}")
                else:
                    logger.info(f"  ❌ 未匹配: 指长比例或五行元素不满足条件")
            else:
                logger.info(f"  ❌ 未匹配: 指长比例数据为空")
        
        # ========== 规则组4: 面相与五行融合（基于传统命理学对应关系）==========
        if face_features:
            san_ting = face_features.get("san_ting_ratio", {})
            upper = san_ting.get("upper", 0.33)
            middle = san_ting.get("middle", 0.33)
            lower = san_ting.get("lower", 0.34)
            
            measurements = face_features.get("feature_measurements", {})
            
            # 规则4.1: 上停 + 木元素（上停对应早年，木主生发向上，学习运）
            rule_name = "规则4.1: 上停 + 木元素（早年学习运）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 上停对应早年运势，木主生发向上，学习能力强")
            logger.info(f"  检查: 上停比例={upper:.2%}, 木元素={five_elements.get('木', 0)}")
            if upper > 0.35 and five_elements.get("木", 0) > 0:
                wood_count = five_elements.get("木", 0)
                if wood_count >= 3:
                    wood_desc = f"木元素非常旺（{wood_count}个）"
                    learning_desc = "学习能力极强，思维非常活跃"
                    confidence = 0.9
                elif wood_count >= 2:
                    wood_desc = f"木元素较旺（{wood_count}个）"
                    learning_desc = "学习能力较强，思维活跃"
                    confidence = 0.85
                else:
                    wood_desc = f"木元素一般（{wood_count}个）"
                    learning_desc = "学习能力较好，思维较为活跃"
                    confidence = 0.8
                
                if upper > 0.38:
                    ting_desc = "非常长"
                else:
                    ting_desc = "较长"
                
                insight = {
                    "category": "学习",
                    "content": f"面相显示早年学习运佳（上停{ting_desc}，比例{upper:.2%}），结合八字{wood_desc}，木主生发向上，{learning_desc}，建议在20-30岁重点学习积累，打好基础",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 上停比例={upper:.2%}（需 > 35%）或木元素={five_elements.get('木', 0)}（需 > 0）")
            
            # 规则4.2: 中停 + 火元素（中停对应中年，火主热情向上，事业运）
            rule_name = "规则4.2: 中停 + 火元素（中年事业运）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 中停对应中年运势，火主热情向上，事业发展好")
            logger.info(f"  检查: 中停比例={middle:.2%}, 火元素={five_elements.get('火', 0)}")
            if middle > 0.35 and five_elements.get("火", 0) > 0:
                fire_count = five_elements.get("火", 0)
                if fire_count >= 3:
                    fire_desc = f"火元素非常旺（{fire_count}个）"
                    career_desc = "事业运势极佳，发展非常顺利"
                    confidence = 0.9
                elif fire_count >= 2:
                    fire_desc = f"火元素较旺（{fire_count}个）"
                    career_desc = "事业运势佳，发展顺利"
                    confidence = 0.85
                else:
                    fire_desc = f"火元素一般（{fire_count}个）"
                    career_desc = "事业运势较好，发展较为顺利"
                    confidence = 0.8
                
                if middle > 0.38:
                    ting_desc = "非常长"
                else:
                    ting_desc = "较长"
                
                insight = {
                    "category": "事业",
                    "content": f"面相显示中年运势佳（中停{ting_desc}，比例{middle:.2%}），结合八字{fire_desc}，火主热情向上，{career_desc}，建议在30-45岁重点发展事业，抓住机遇",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 中停比例={middle:.2%}（需 > 35%）或火元素={five_elements.get('火', 0)}（需 > 0）")
            
            # 规则4.3: 下停 + 土元素（下停对应晚年，土主稳定承载，晚年运）
            rule_name = "规则4.3: 下停 + 土元素（晚年运势）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            logger.info(f"  原理: 下停对应晚年运势，土主稳定承载，晚年有福")
            logger.info(f"  检查: 下停比例={lower:.2%}, 土元素={five_elements.get('土', 0)}")
            if lower > 0.35 and five_elements.get("土", 0) > 0:
                earth_count = five_elements.get("土", 0)
                if earth_count >= 3:
                    earth_desc = f"土元素非常旺（{earth_count}个）"
                    fortune_desc = "晚年运势极佳，生活非常幸福，有福气"
                    confidence = 0.9
                elif earth_count >= 2:
                    earth_desc = f"土元素较旺（{earth_count}个）"
                    fortune_desc = "晚年运势佳，生活幸福，有福气"
                    confidence = 0.85
                else:
                    earth_desc = f"土元素一般（{earth_count}个）"
                    fortune_desc = "晚年运势较好，生活较为幸福"
                    confidence = 0.8
                
                if lower > 0.38:
                    ting_desc = "非常长"
                else:
                    ting_desc = "较长"
                
                insight = {
                    "category": "运势",
                    "content": f"面相显示晚年运势佳（下停{ting_desc}，比例{lower:.2%}），结合八字{earth_desc}，土主稳定承载，{fortune_desc}，建议在年轻时多积累，为晚年做准备",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 下停比例={lower:.2%}（需 > 35%）或土元素={five_elements.get('土', 0)}（需 > 0）")
            
            # 规则4.4: 鼻子 + 金元素（鼻子对应财运，金主收敛刚强，财运）
            rule_name = "规则4.4: 鼻子 + 金元素（财运）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            nose_height = measurements.get("nose_height", 0)
            nose_ratio = measurements.get("nose_ratio", 0)
            logger.info(f"  原理: 鼻子对应财运，金主收敛刚强，财运佳")
            logger.info(f"  检查: 鼻子高度={nose_height:.1f}, 比例={nose_ratio:.2f}, 金元素={five_elements.get('金', 0)}")
            if (nose_ratio > 2.0 or nose_height > 50) and five_elements.get("金", 0) > 0:
                gold_count = five_elements.get("金", 0)
                if gold_count >= 3:
                    gold_desc = f"金元素非常旺（{gold_count}个）"
                    wealth_desc = "财运极佳"
                    confidence = 0.9
                elif gold_count >= 2:
                    gold_desc = f"金元素较旺（{gold_count}个）"
                    wealth_desc = "财运佳"
                    confidence = 0.85
                else:
                    gold_desc = f"金元素一般（{gold_count}个）"
                    wealth_desc = "财运较好"
                    confidence = 0.8
                
                if nose_ratio > 2.5:
                    nose_desc = "非常高挺"
                elif nose_ratio > 2.0:
                    nose_desc = "高挺"
                else:
                    nose_desc = "较高"
                
                insight = {
                    "category": "财运",
                    "content": f"面相显示财运佳（鼻梁{nose_desc}，高度{nose_height:.1f}，比例{nose_ratio:.2f}），结合八字{gold_desc}，金主收敛刚强，{wealth_desc}，适合从事金融、投资、管理相关行业，建议在35-50岁重点发展财运",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需鼻子高挺（比例>2.0或高度>50）且金元素>0")
            
            # 规则4.5: 额头 + 木元素（额头对应智慧，木主生发向上，学习能力）
            rule_name = "规则4.5: 额头 + 木元素（智慧学习）"
            scanned_rules.append(rule_name)
            logger.info(f"\n{rule_name}")
            forehead_width = measurements.get("forehead_width", 0)
            forehead_ratio = measurements.get("forehead_ratio", 0)
            logger.info(f"  原理: 额头对应智慧，木主生发向上，学习能力强")
            logger.info(f"  检查: 额头宽度={forehead_width:.1f}, 比例={forehead_ratio:.2f}, 木元素={five_elements.get('木', 0)}")
            if (forehead_ratio > 1.2 or forehead_width > 100) and five_elements.get("木", 0) > 0:
                wood_count = five_elements.get("木", 0)
                if wood_count >= 3:
                    wood_desc = f"木元素非常旺（{wood_count}个）"
                    wisdom_desc = "智慧过人，学习能力极强"
                    confidence = 0.9
                elif wood_count >= 2:
                    wood_desc = f"木元素较旺（{wood_count}个）"
                    wisdom_desc = "智慧较高，学习能力强"
                    confidence = 0.85
                else:
                    wood_desc = f"木元素一般（{wood_count}个）"
                    wisdom_desc = "智慧较好，学习能力较强"
                    confidence = 0.8
                
                if forehead_ratio > 1.5:
                    forehead_desc = "非常宽阔"
                elif forehead_ratio > 1.2:
                    forehead_desc = "宽阔"
                else:
                    forehead_desc = "较宽"
                
                insight = {
                    "category": "智慧",
                    "content": f"面相显示智慧过人（额头{forehead_desc}，宽度{forehead_width:.1f}，比例{forehead_ratio:.2f}），结合八字{wood_desc}，木主生发向上，{wisdom_desc}，适合从事教育、科研、技术等需要思考的职业，建议在25-40岁重点发展专业技能",
                    "confidence": confidence,
                    "source": "integrated"
                }
                integrated_insights.append(insight)
                logger.info(f"  ✅ 匹配成功: {insight['content']}")
            else:
                logger.info(f"  ❌ 未匹配: 需额头宽阔（比例>1.2或宽度>100）且木元素>0")
        
        # 托底方案：如果融合分析匹配到的规则太少，生成基础融合分析
        if len(integrated_insights) < 3:
            logger.info(f"\n⚠️  融合分析匹配到的规则较少（{len(integrated_insights)}条），启用托底方案生成基础融合分析...")
            
            # 基于五行生成基础融合分析
            if five_elements:
                # 找出最强的五行
                max_element = max(five_elements.items(), key=lambda x: x[1]) if five_elements else None
                if max_element and max_element[1] > 0:
                    element_name, element_count = max_element
                    element_info = element_mapping.get(element_name, {})
                    
                    # 基于最强五行生成分析
                    if element_name == "金" and element_count >= 2:
                        integrated_insights.append({
                            "category": "财运",
                            "content": f"八字显示金元素较旺（{element_count}个），金主收敛刚强，财运较好，适合从事金融、投资、管理相关行业，建议在35-50岁重点发展财运，可考虑稳健理财和长期投资",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: 金元素较旺，财运分析")
                    elif element_name == "木" and element_count >= 2:
                        integrated_insights.append({
                            "category": "学习",
                            "content": f"八字显示木元素较旺（{element_count}个），木主生发向上，学习能力较强，思维活跃，适合从事技术、科研、教育类工作，建议在25-40岁重点发展专业技能，持续学习提升",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: 木元素较旺，学习分析")
                    elif element_name == "土" and element_count >= 3:
                        integrated_insights.append({
                            "category": "事业",
                            "content": f"八字显示土元素较旺（{element_count}个），土主稳定承载，性格稳重，适合从事工程、建筑、管理类工作，建议在30-45岁重点发展事业，注重团队协作和领导力培养",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: 土元素较旺，事业分析")
                    elif element_name == "火" and element_count >= 2:
                        integrated_insights.append({
                            "category": "性格",
                            "content": f"八字显示火元素较旺（{element_count}个），火主热情向上，性格外向，适合从事销售、营销、教育类工作，建议在人际交往中发挥优势，建立良好的人脉关系",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: 火元素较旺，性格分析")
                    elif element_name == "水" and element_count >= 2:
                        integrated_insights.append({
                            "category": "智慧",
                            "content": f"八字显示水元素较旺（{element_count}个），水主流动智慧，适应能力强，适合从事创意、设计、咨询类工作，建议在工作中发挥灵活性和创造力",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: 水元素较旺，智慧分析")
            
            # 基于十神生成基础融合分析
            if ten_gods and len(integrated_insights) < 3:
                # 找出最强的十神
                max_ten_god = max(ten_gods.items(), key=lambda x: x[1]) if ten_gods else None
                if max_ten_god and max_ten_god[1] >= 2:
                    god_name, god_count = max_ten_god
                    if god_name == "正财" or god_name == "偏财":
                        integrated_insights.append({
                            "category": "财运",
                            "content": f"八字显示{god_name}较旺（{god_count}个），财运较好，适合从事金融、投资、理财相关行业，建议在30-50岁重点发展财运，可考虑稳健理财，避免高风险投资",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: {god_name}较旺，财运分析")
                    elif god_name == "正官" or god_name == "七杀":
                        integrated_insights.append({
                            "category": "事业",
                            "content": f"八字显示{god_name}较旺（{god_count}个），事业运势较好，适合从事管理、领导类工作，建议在30-45岁重点发展管理能力，积累管理经验，提升领导力",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: {god_name}较旺，事业分析")
                    elif god_name == "正印" or god_name == "偏印":
                        integrated_insights.append({
                            "category": "学习",
                            "content": f"八字显示{god_name}较旺（{god_count}个），学习能力较强，适合从事教育、科研、技术类工作，建议在25-40岁重点学习积累，提升专业能力",
                            "confidence": 0.7,
                            "source": "integrated"
                        })
                        logger.info(f"  ✅ 托底融合分析: {god_name}较旺，学习分析")
            
            # 如果还是没有足够的洞察，生成通用融合分析
            if len(integrated_insights) < 2:
                # 基于五行平衡生成通用分析
                total_elements = sum(five_elements.values()) if five_elements else 0
                if total_elements > 0:
                    element_balance = max(five_elements.values()) / total_elements if five_elements else 0
                    if element_balance > 0.4:
                        integrated_insights.append({
                            "category": "综合",
                            "content": f"根据八字分析，五行分布较为集中，建议在关键年龄段重点发展相关能力，结合面相特征，建议在各个阶段都保持积极向上的心态，持续学习和提升自己，注重健康管理，抓住机遇，为未来发展做好准备",
                            "confidence": 0.65,
                            "source": "integrated"
                        })
                    else:
                        integrated_insights.append({
                            "category": "综合",
                            "content": f"根据八字分析，五行分布较为均衡，整体运势平稳，结合面相特征，建议在各个阶段都保持积极向上的心态，持续学习和提升自己，注重健康管理，抓住机遇，为未来发展做好准备",
                            "confidence": 0.65,
                            "source": "integrated"
                        })
                    logger.info(f"  ✅ 托底融合分析: 生成通用融合综合分析")
        
        # 打印最终结果
        logger.info("\n" + "-"*80)
        logger.info(f"【融合分析结果】")
        logger.info(f"  扫描的规则总数: {len(scanned_rules)}")
        logger.info(f"  匹配成功的规则数: {len(integrated_insights)}")
        logger.info(f"\n  扫描的规则列表:")
        for i, rule in enumerate(scanned_rules, 1):
            logger.info(f"    {i}. {rule}")
        logger.info(f"\n  匹配成功的规则:")
        for i, insight in enumerate(integrated_insights, 1):
            logger.info(f"    {i}. [{insight['category']}] {insight['content']} (置信度: {insight['confidence']})")
        logger.info("="*80)
        logger.info(f"✅ 融合分析完成，共扫描 {len(scanned_rules)} 条规则，匹配到 {len(integrated_insights)} 条规则\n")
        
        # 合并和提炼重复内容
        integrated_insights = self._merge_and_refine_insights(integrated_insights)
        
        return integrated_insights
    
    def _merge_and_refine_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并和提炼重复的insights
        
        策略：
        1. 按category分组
        2. 对于同一category的多个insights，识别相似内容并合并
        3. 提炼精华，保留最详细、最有价值的内容
        4. 去除重复
        """
        if not insights:
            return []
        
        import re
        
        # 按category分组
        category_groups = {}
        for insight in insights:
            category = insight.get("category", "综合")
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(insight)
        
        merged_insights = []
        
        for category, group_insights in category_groups.items():
            if len(group_insights) == 1:
                # 只有一个，直接添加
                merged_insights.append(group_insights[0])
            else:
                # 多个，需要合并
                # 按置信度和内容长度排序，优先保留置信度高且详细的
                group_insights.sort(key=lambda x: (
                    x.get("confidence", 0),
                    len(x.get("content", ""))
                ), reverse=True)
                
                # 提取关键特征用于相似度判断
                # 对于三停相关的，提取"上停"、"中停"、"下停"关键词
                # 对于其他，提取主要描述（括号前的内容）
                key_features = {}
                for insight in group_insights:
                    content = insight.get("content", "")
                    # 提取关键特征
                    if "上停" in content:
                        key = "上停"
                    elif "中停" in content:
                        key = "中停"
                    elif "下停" in content:
                        key = "下停"
                    else:
                        # 提取主要描述（括号前的内容）
                        key = re.split(r'[（(]', content)[0].strip()
                        # 简化：只取前20个字符作为关键特征
                        key = key[:20]
                    
                    if key not in key_features:
                        key_features[key] = []
                    key_features[key].append(insight)
                
                # 对于每个关键特征，只保留最详细的那条
                for key, feature_insights in key_features.items():
                    if len(feature_insights) == 1:
                        merged_insights.append(feature_insights[0])
                    else:
                        # 多条，找出最详细的那条
                        best_insight = max(feature_insights, key=lambda x: (
                            len(x.get("content", "")),
                            x.get("confidence", 0)
                        ))
                        merged_insights.append(best_insight)
        
        # 最终去重：如果内容完全相同或高度相似，只保留一个
        seen_contents = set()
        final_insights = []
        for insight in merged_insights:
            content = insight.get("content", "")
            # 标准化内容（去除多余空格和标点）
            normalized_content = re.sub(r'\s+', ' ', content).strip()
            
            # 提取核心内容（去除括号内的详细说明）用于去重
            core_content = re.split(r'[（(]', normalized_content)[0].strip()
            
            # 如果核心内容已存在，跳过（说明是重复的）
            if core_content not in seen_contents:
                seen_contents.add(core_content)
                final_insights.append(insight)
        
        return final_insights
    
    def generate_recommendations(
        self,
        hand_insights: List[Dict[str, Any]],
        face_insights: List[Dict[str, Any]],
        integrated_insights: List[Dict[str, Any]]
    ) -> List[str]:
        """生成个性化建议（增强版：更深入、更高级的分析）"""
        recommendations = []
        
        # 从洞察中提取建议
        all_insights = hand_insights + face_insights + integrated_insights
        
        # 按类别分组，并记录具体内容
        categories = {}
        for insight in all_insights:
            category = insight.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(insight)
        
        # 生成个性化建议（基于具体洞察内容，更深入的分析）
        
        # 1. 健康建议（增强版）
        if "健康" in categories:
            health_insights = categories["健康"]
            health_content = " ".join([i.get("content", "") for i in health_insights])
            
            has_earth_weak = any("土弱" in i.get("content", "") for i in health_insights)
            has_earth_strong = any("土旺" in i.get("content", "") for i in health_insights)
            has_symmetry_good = any("对称性良好" in i.get("content", "") for i in health_insights)
            has_ratio_good = any("比例协调" in i.get("content", "") for i in health_insights)
            
            if has_earth_weak:
                recommendations.append("健康建议：特别注意脾胃健康，规律饮食，避免暴饮暴食，建议每年体检时重点检查消化系统，可适当食用健脾养胃的食物（如山药、小米、红枣等），避免生冷、油腻、辛辣食物")
            elif has_earth_strong:
                recommendations.append("健康建议：体质较好，健康根基稳固，但需注意消化系统，建议规律作息，适当运动（如慢跑、瑜伽、太极），避免过度劳累，保持心情愉悦")
            elif has_symmetry_good and has_ratio_good:
                recommendations.append("健康建议：面部特征显示健康运势良好，建议保持规律作息，适当运动，定期体检，注意身体保养，可适当进行有氧运动增强体质")
            else:
                recommendations.append("健康建议：保持规律作息，适当运动，定期体检，注意身体保养")
        
        # 2. 事业建议（增强版）
        if "事业" in categories:
            career_insights = categories["事业"]
            career_content = " ".join([i.get("content", "") for i in career_insights])
            
            has_management = any("管理" in i.get("content", "") for i in career_insights)
            has_finance = any("金融" in i.get("content", "") or "投资" in i.get("content", "") for i in career_insights)
            has_tech = any("技术" in i.get("content", "") or "科研" in i.get("content", "") for i in career_insights)
            has_creative = any("艺术" in i.get("content", "") or "设计" in i.get("content", "") or "创意" in i.get("content", "") for i in career_insights)
            
            if has_management and has_finance:
                recommendations.append("事业建议：适合从事管理、金融、投资相关行业，建议在30-40岁重点发展事业，可考虑在金融、投资、企业管理等领域深耕，积累经验和人脉资源")
            elif has_management:
                recommendations.append("事业建议：具有管理才能，适合从事管理类工作，建议在25-35岁积累管理经验，在35-45岁争取管理职位，注重团队协作和领导力培养")
            elif has_finance:
                recommendations.append("事业建议：财运佳，适合从事金融、投资、理财相关行业，建议在30-50岁重点发展财运，可考虑学习金融知识，积累投资经验")
            elif has_tech:
                recommendations.append("事业建议：适合从事技术、科研、法律等需要严谨思维的职业，建议在25-40岁重点发展专业技能，持续学习新技术，提升专业能力")
            elif has_creative:
                recommendations.append("事业建议：具有艺术天赋和创造力，适合从事艺术、设计、创作类工作，建议在25-35岁重点发展创作能力，多参与创作项目，积累作品集")
            else:
                recommendations.append("事业建议：根据面相特征，建议在30-40岁重点发展事业，抓住机遇，持续学习和提升专业能力")
        
        # 3. 学习建议（增强版）
        if "学习" in categories:
            learning_insights = categories["学习"]
            has_strong_learning = any("学习能力极强" in i.get("content", "") or "学习能力较强" in i.get("content", "") for i in learning_insights)
            has_observation = any("观察能力强" in i.get("content", "") for i in learning_insights)
            
            if has_strong_learning:
                recommendations.append("学习建议：学习能力极强，建议在20-30岁重点学习积累，打好基础，可考虑深入学习专业知识，考取相关证书，为未来发展奠定基础")
            elif has_observation:
                recommendations.append("学习建议：观察能力强，善于发现细节，建议多观察思考，提升学习效率，可尝试通过实践和观察相结合的方式学习")
            else:
                recommendations.append("学习建议：建议多读书，提升思维能力，早年开始积累，持续学习新知识")
        
        # 4. 感情建议（增强版）
        if "感情" in categories:
            emotion_insights = categories["感情"]
            has_rich_emotion = any("感情丰富" in i.get("content", "") for i in emotion_insights)
            has_stable = any("感情稳定" in i.get("content", "") or "婚姻和谐" in i.get("content", "") for i in emotion_insights)
            has_early_marriage = any("适合早婚" in i.get("content", "") for i in emotion_insights)
            
            if has_rich_emotion and has_stable:
                recommendations.append("感情建议：感情丰富且稳定，人际关系好，适合早婚，建议在25-30岁重点考虑感情问题，婚后注意沟通和理解，保持感情和谐")
            elif has_stable:
                recommendations.append("感情建议：感情稳定，婚姻和谐，建议在25-30岁重点考虑婚姻，注重沟通和理解，建立良好的家庭关系")
            elif has_rich_emotion:
                recommendations.append("感情建议：感情丰富，善于表达情感，建议在25-30岁重点考虑感情问题，注重情感沟通，建立稳定的感情关系")
            else:
                recommendations.append("感情建议：建议在25-30岁重点考虑感情问题，注重沟通和理解，建立良好的感情关系")
        
        # 5. 财运建议（增强版）
        if "财运" in categories:
            wealth_insights = categories["财运"]
            has_strong_wealth = any("财运极佳" in i.get("content", "") or "财运佳" in i.get("content", "") for i in wealth_insights)
            has_finance_suitable = any("金融" in i.get("content", "") or "投资" in i.get("content", "") for i in wealth_insights)
            
            if has_strong_wealth and has_finance_suitable:
                recommendations.append("财运建议：财运极佳，适合从事金融、投资、管理相关行业，建议在35-50岁重点发展财运，可考虑稳健理财和长期投资，积累财富")
            elif has_strong_wealth:
                recommendations.append("财运建议：财运佳，建议在35-50岁重点发展财运，可考虑稳健理财，避免高风险投资，积累财富")
            else:
                recommendations.append("财运建议：建议稳健理财，避免高风险投资，注重财务规划，积累财富")
        
        # 6. 天赋建议（增强版）
        if "天赋" in categories:
            talent_insights = categories["天赋"]
            has_art = any("艺术" in i.get("content", "") or "创作" in i.get("content", "") for i in talent_insights)
            has_management = any("管理" in i.get("content", "") for i in talent_insights)
            
            if has_art:
                recommendations.append("天赋建议：具有艺术天赋和创造力，适合从事艺术、设计、创作类工作，建议在25-35岁重点发展创作能力，多参与创作项目，积累作品集，可考虑参加艺术展览或比赛")
            elif has_management:
                recommendations.append("天赋建议：具有管理才能和决策能力，适合从事管理、投资、创业等工作，建议在30-40岁重点发展管理能力，积累管理经验，提升领导力")
            else:
                recommendations.append("天赋建议：根据面相特征，建议在25-35岁重点发展天赋才能，找到适合自己的发展方向")
        
        # 7. 综合建议（如果没有特定建议，提供通用建议）
        if len(recommendations) == 0:
            recommendations.append("综合建议：根据面相分析，建议保持积极向上的心态，持续学习和提升自己，注重健康管理，抓住机遇，为未来发展做好准备")
        
        return recommendations


def get_hand_rules_static() -> Dict[str, Any]:
    """模块级：返回手相规则（供 UnifiedRuleService 硬编码兜底使用）。"""
    return FortuneRuleEngine._load_hand_rules()


def get_face_rules_static() -> Dict[str, Any]:
    """模块级：返回面相规则（供 UnifiedRuleService 硬编码兜底使用）。"""
    return FortuneRuleEngine._load_face_rules()

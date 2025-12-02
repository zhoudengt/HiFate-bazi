# -*- coding: utf-8 -*-
"""
规则后处理器（10-20ms）
负责时间意图解析、JSON格式化、多意图合并
"""
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.intent_service.logger import logger
from services.intent_service.config import INTENT_TO_RULE_TYPE_MAP


class RulePostProcessor:
    """规则后处理器"""
    
    def __init__(self):
        self.rule_type_map = INTENT_TO_RULE_TYPE_MAP
        self.current_year = datetime.now().year
        logger.info("RulePostProcessor initialized")
    
    def process(
        self,
        question: str,
        base_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        后处理：时间意图解析、JSON格式化
        
        Args:
            question: 用户问题
            base_result: 基础分类结果（来自本地模型或LLM）
        
        Returns:
            完整的分类结果
        """
        start_time = time.time()
        
        # 1. 解析时间意图
        time_intent = self._extract_time_intent(question)
        base_result["time_intent"] = time_intent
        
        # 2. 映射规则类型
        base_result["rule_types"] = [
            self.rule_type_map.get(intent, "ALL")
            for intent in base_result.get("intents", ["general"])
        ]
        
        # 3. 多意图合并和去重
        base_result["intents"] = self._merge_intents(base_result.get("intents", []))
        
        # 4. 置信度校准
        base_result = self._calibrate_confidence(base_result)
        
        # 5. 确保必需字段
        base_result = self._ensure_required_fields(base_result)
        
        # 6. 添加处理时间
        processing_time = int((time.time() - start_time) * 1000)
        if "response_time_ms" in base_result:
            base_result["response_time_ms"] += processing_time
        else:
            base_result["response_time_ms"] = processing_time
        
        return base_result
    
    def _extract_time_intent(self, question: str) -> Dict[str, Any]:
        """
        提取时间意图（规则匹配）
        
        支持的时间表达：
        - 今天/今日 → today
        - 本月/这个月 → this_month
        - 今年/本年 → this_year
        - 明年 → next_year (只有1年)
        - 后N年/未来N年 → future_years (N年)
        - 最近N年 → recent_years
        - XXXX年 → specific_year (单个年份)
        - XXXX-YYYY年 → year_range (年份范围)
        """
        question_lower = question.lower()
        
        # 1. 今天/今日
        if re.search(r'(今天|今日)', question):
            return {
                "type": "today",
                "target_years": [self.current_year],
                "description": "今天",
                "is_explicit": True
            }
        
        # 2. 本月/这个月
        if re.search(r'(本月|这个月)', question):
            return {
                "type": "this_month",
                "target_years": [self.current_year],
                "description": "本月",
                "is_explicit": True
            }
        
        # 3. 后年（特殊处理：后年 = 明年+1 = 当前年份+2）
        if re.search(r'后年', question):
            return {
                "type": "specific_year",
                "target_years": [self.current_year + 2],
                "description": f"后年（{self.current_year + 2}年）",
                "is_explicit": True
            }
        
        # 4. 后N年/未来N年（需要先匹配，避免被"明年"干扰）
        # 支持中文数字和阿拉伯数字
        chinese_numbers = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
        future_years_match = re.search(r'(后|未来)(\d+|[' + ''.join(chinese_numbers.keys()) + ']+)年', question)
        if future_years_match:
            num_str = future_years_match.group(2)
            # 转换中文数字或阿拉伯数字
            if num_str.isdigit():
                n = int(num_str)
            elif num_str in chinese_numbers:
                n = chinese_numbers[num_str]
            else:
                # 尝试解析"十"、"二十"等组合
                if num_str == '十':
                    n = 10
                elif num_str.startswith('十') and len(num_str) == 2:
                    n = 10 + chinese_numbers.get(num_str[1], 0)
                else:
                    n = 3  # 默认值
            target_years = [self.current_year + i + 1 for i in range(n)]
            return {
                "type": "future_years",
                "target_years": target_years,
                "description": f"未来{n}年（{target_years[0]}-{target_years[-1]}年）",
                "is_explicit": True
            }
        
        # 5. 明年（只有1年，需要在"后N年"之后匹配）
        if re.search(r'明年', question):
            return {
                "type": "next_year",
                "target_years": [self.current_year + 1],
                "description": f"明年（{self.current_year + 1}年）",
                "is_explicit": True
            }
        
        # 5. 最近N年
        recent_years_match = re.search(r'最近(\d+)年', question)
        if recent_years_match:
            n = int(recent_years_match.group(1))
            target_years = [self.current_year - i for i in range(n - 1, -1, -1)]
            return {
                "type": "recent_years",
                "target_years": target_years,
                "description": f"最近{n}年（{target_years[0]}-{target_years[-1]}年）",
                "is_explicit": True
            }
        
        # 6. 年份范围（XXXX-YYYY年 或 XXXX到YYYY年）
        year_range_match = re.search(r'(\d{4})[到-](\d{4})年?', question)
        if year_range_match:
            start_year = int(year_range_match.group(1))
            end_year = int(year_range_match.group(2))
            target_years = list(range(start_year, end_year + 1))
            return {
                "type": "year_range",
                "target_years": target_years,
                "description": f"{start_year}-{end_year}年",
                "is_explicit": True
            }
        
        # 7. 单个年份（XXXX年）
        specific_year_match = re.search(r'(\d{4})年', question)
        if specific_year_match:
            year = int(specific_year_match.group(1))
            return {
                "type": "specific_year",
                "target_years": [year],
                "description": f"{year}年",
                "is_explicit": True
            }
        
        # 8. 今年/本年（默认）
        if re.search(r'(今年|本年)', question):
            return {
                "type": "this_year",
                "target_years": [self.current_year],
                "description": f"今年（{self.current_year}年）",
                "is_explicit": True
            }
        
        # 9. 默认：今年
        return {
            "type": "this_year",
            "target_years": [self.current_year],
            "description": f"今年（{self.current_year}年，默认）",
            "is_explicit": False
        }
    
    def _merge_intents(self, intents: List[str]) -> List[str]:
        """合并和去重意图"""
        if not intents:
            return ["general"]
        
        # 去重
        unique_intents = []
        seen = set()
        for intent in intents:
            if intent not in seen:
                unique_intents.append(intent)
                seen.add(intent)
        
        # 如果意图过多（>3），只保留前3个
        if len(unique_intents) > 3:
            unique_intents = unique_intents[:3]
        
        return unique_intents if unique_intents else ["general"]
    
    def _calibrate_confidence(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """置信度校准"""
        confidence = result.get("confidence", 0.7)
        
        # 基于关键词数量调整
        keyword_count = len(result.get("keywords", []))
        if keyword_count == 0:
            confidence *= 0.9
        elif keyword_count >= 3:
            confidence = min(confidence * 1.05, 1.0)
        
        # 基于意图数量调整
        intent_count = len(result.get("intents", []))
        if intent_count > 2:
            confidence *= 0.95
        
        result["confidence"] = max(0.5, min(1.0, confidence))
        
        # 更新模糊性
        result["is_ambiguous"] = confidence < 0.75
        
        return result
    
    def _ensure_required_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """确保必需字段存在"""
        # 意图
        if "intents" not in result or not result["intents"]:
            result["intents"] = ["general"]
        
        # 置信度
        if "confidence" not in result:
            result["confidence"] = 0.7
        
        # 关键词
        if "keywords" not in result:
            result["keywords"] = []
        
        # 推理
        if "reasoning" not in result:
            result["reasoning"] = "Rule-based post-processing"
        
        # 模糊性
        if "is_ambiguous" not in result:
            result["is_ambiguous"] = result["confidence"] < 0.75
        
        # 时间意图
        if "time_intent" not in result:
            result["time_intent"] = {
                "type": "this_year",
                "target_years": [self.current_year],
                "description": f"今年（{self.current_year}年，默认）",
                "is_explicit": False
            }
        
        return result


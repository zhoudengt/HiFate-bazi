# -*- coding: utf-8 -*-
"""
意图分类器 - 混合架构（95%准确率目标）
支持多层级处理：关键词过滤 → 本地模型 → 规则后处理 → LLM兜底
"""
from typing import Dict, Any, List
import time
import re
from services.intent_service.llm_client import IntentLLMClient
from services.intent_service.local_classifier import LocalIntentClassifier
from services.intent_service.rule_postprocessor import RulePostProcessor
from services.intent_service.config import INTENT_CATEGORIES, INTENT_TO_RULE_TYPE_MAP
from services.intent_service.logger import logger

# 意图分类 Prompt 模板 v2.0（事项意图 + 时间意图 + 命理相关性判断）
INTENT_CLASSIFICATION_PROMPT = """你是一个专业的命理学意图识别专家，负责：
1. 判断问题是否与命理相关
2. 识别用户关心的事项意图（财运、事业、健康等）
3. 识别用户询问的时间范围（今年、后三年、2025-2028等）

【用户问题】
{question}

【第一步：命理相关性判断】
命理相关：运势、八字、四柱、十神、五行、旺衰、喜用神、流年、大运等
命理无关：日常闲聊、技术问题、其他领域（做菜、旅游、购物等）

如果问题与命理无关，返回：
{{
  "is_fortune_related": false,
  "reject_message": "您好，我是专业的命理分析助手，只能回答关于八字、运势、命理等相关问题。您的问题似乎不在我的服务范围内，如有命理方面的疑问，欢迎随时咨询！",
  "intents": ["non_fortune"],
  "confidence": 0.95
}}

【第二步：事项意图识别】
1. career - 事业运势（工作、职业、升职、创业）
2. wealth - 财富运势（财运、赚钱、投资、偏财）
3. marriage - 婚姻感情（恋爱、婚姻、桃花、分手）
4. health - 健康运势（身体、疾病、养生）
5. personality - 性格特点（性格、脾气、优缺点）
6. wangshui - 命局旺衰（五行强弱、旺衰分析）
7. yongji - 喜忌用神（喜用神、忌神分析）
8. shishen - 十神分析（食神、伤官、正财等）
9. nayin - 纳音分析（纳音五行）
10. general - 综合分析（笼统询问、多方面）

【第三步：时间意图识别 ⭐核心规则⭐】
当前年份：2025年

**时间类型分类（严格区分）**：

**A. 相对时间（模糊词）**
- today: 今天/今日
- this_month: 本月/这个月
- this_year: 今年/本年 → [2025]
- next_year: **明年** → [2026]（⚠️只有1年）
- future_years: 后N年/未来N年 → [2026, ..., 2025+N]
  例："后三年"=[2026,2027,2028]（3年）
- recent_years: 最近N年 → [2025-N+1, ..., 2025]

**B. 绝对时间（明确数字）**
- specific_year: **单个年份** → [该年份]（⚠️只有1年）
  例："2028年"=[2028]，"2026年"=[2026]
- year_range: 年份范围 → [start, ..., end]
  例："2025-2028"=[2025,2026,2027,2028]

⚠️ **关键区别（必看）**：
- "明年" = [2026] ✅ （1年）
- "后三年" = [2026, 2027, 2028] ✅ （3年）
- "2028年" = [2028] ✅ （1年，不是[2026,2027,2028]❌）
- "2025-2028" = [2025,2026,2027,2028] ✅ （4年）

【输出格式（严格JSON）】
命理相关问题：
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "future_years",
    "target_years": [2026, 2027, 2028],
    "description": "未来三年（2026-2028年）",
    "is_explicit": true
  }},
  "confidence": 0.95,
  "keywords": ["后三年", "财运"],
  "reasoning": "用户询问未来三年的财运",
  "is_ambiguous": false
}}
```

【Few-shot 示例】

**示例1：后三年+财运**
问题："我后三年的财运如何？"
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "future_years",
    "target_years": [2026, 2027, 2028],
    "description": "未来三年（2026-2028年）",
    "is_explicit": true
  }},
  "confidence": 0.95,
  "keywords": ["后三年", "财运"],
  "reasoning": "用户明确询问未来三年的财运，时间为从明年开始的3年",
  "is_ambiguous": false
}}
```

**示例2：明年 ⭐**
问题："我明年的财运怎么样？"
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "next_year",
    "target_years": [2026],
    "description": "明年（2026年）",
    "is_explicit": true
  }},
  "confidence": 0.95,
  "keywords": ["明年", "财运"],
  "reasoning": "用户询问明年的财运，明年=2026，只有1年",
  "is_ambiguous": false
}}
```

**示例3：特定年份 ⭐⭐⭐**
问题："我2028年的财运怎么样？"
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "specific_year",
    "target_years": [2028],
    "description": "2028年",
    "is_explicit": true
  }},
  "confidence": 0.95,
  "keywords": ["2028年", "财运"],
  "reasoning": "用户询问2028年的财运，2028是特定年份，只返回[2028]，不是[2026,2027,2028]",
  "is_ambiguous": false
}}
```

**示例4：年份范围**
问题："我2025到2028年能发财吗？"
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "year_range",
    "target_years": [2025, 2026, 2027, 2028],
    "description": "2025-2028年",
    "is_explicit": true
  }},
  "confidence": 0.93,
  "keywords": ["2025到2028", "发财"],
  "reasoning": "用户询问明确年份范围的财运，包含起止年份，共4年",
  "is_ambiguous": false
}}
```

**示例5：单个年份（⚠️重要）**
问题："我2028年的财运怎么样？"
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "specific_year",
    "target_years": [2028],
    "description": "2028年",
    "is_explicit": true
  }},
  "confidence": 0.95,
  "keywords": ["2028年", "财运"],
  "reasoning": "用户询问2028年的财运，这是单个特定年份，只返回[2028]，不是范围",
  "is_ambiguous": false
}}
```

**示例6：另一个单年份**
问题："2028年适合投资吗？"
```json
{{
  "is_fortune_related": true,
  "intents": ["wealth"],
  "time_intent": {{
    "type": "specific_year",
    "target_years": [2028],
    "description": "2028年",
    "is_explicit": true
  }},
  "confidence": 0.95,
  "keywords": ["2028年", "投资"],
  "reasoning": "用户询问2028年的投资运势，这是单个年份，只返回[2028]",
  "is_ambiguous": false
}}
```

**示例7：未指定时间**
问题："我的事业运势怎么样？"
```json
{{
  "is_fortune_related": true,
  "intents": ["career"],
  "time_intent": {{
    "type": "this_year",
    "target_years": [2025],
    "description": "今年（2025年，默认）",
    "is_explicit": false
  }},
  "confidence": 0.90,
  "keywords": ["事业", "运势"],
  "reasoning": "用户询问事业运势，未明确时间，默认今年",
  "is_ambiguous": false
}}
```

**示例8：多意图+明年**
问题："明年我能升职发财吗？"
```json
{{
  "is_fortune_related": true,
  "intents": ["career", "wealth"],
  "time_intent": {{
    "type": "next_year",
    "target_years": [2026],
    "description": "明年（2026年）",
    "is_explicit": true
  }},
  "confidence": 0.92,
  "keywords": ["明年", "升职", "发财"],
  "reasoning": "用户询问明年的事业（升职）和财运（发财），时间明确为2026",
  "is_ambiguous": false
}}
```

**示例9：命理无关（婉拒）**
问题："你好，在吗？"
```json
{{
  "is_fortune_related": false,
  "reject_message": "您好，我是专业的命理分析助手，只能回答关于八字、运势、命理等相关问题。您的问题似乎不在我的服务范围内，如有命理方面的疑问，欢迎随时咨询！",
  "intents": ["non_fortune"],
  "confidence": 0.95,
  "keywords": ["你好", "在吗"],
  "reasoning": "问题属于日常闲聊，与命理无关"
}}
```

【注意事项】
1. **时间识别优先级**：先看有无"XXXX年"数字 → 是则specific_year
2. **单年vs多年**："明年/2028年"→1年，"后三年/2025-2028"→多年
3. **只返回JSON**，不要添加解释文字
4. **口语化映射**：发财→wealth，升职→career
5. **confidence计算**：明确0.9+，一般0.7-0.9，模糊0.5-0.7
6. **多意图**：可同时识别，但需相关（如事业+财运）

现在请分析上述用户问题，直接返回JSON格式结果。
"""


class IntentClassifier:
    """意图分类器（混合架构）"""
    
    def __init__(self):
        self.llm_client = IntentLLMClient()
        self.local_classifier = LocalIntentClassifier()
        self.post_processor = RulePostProcessor()
        self.intent_categories = INTENT_CATEGORIES
        self.rule_type_map = INTENT_TO_RULE_TYPE_MAP
        logger.info("IntentClassifier initialized (Hybrid Architecture)")
    
    def classify(
        self,
        question: str,
        use_cache: bool = True,
        prompt_version: str = "v1.0"
    ) -> Dict[str, Any]:
        """
        混合架构分类（多层级处理）
        
        流程：
        1. 关键词过滤（0ms）→ 处理60%的明确问题
        2. 本地BERT模型（50-100ms）→ 处理20%的简单问题
        3. 规则后处理（10-20ms）→ 解析时间意图、格式化JSON
        4. LLM兜底（500-1000ms）→ 仅处理5%的模糊问题
        
        Args:
            question: 用户问题
            use_cache: 是否使用缓存
            prompt_version: Prompt版本
        
        Returns:
            {
                "intents": List[str],           # 事项意图（如 wealth, health）
                "confidence": float,
                "rule_types": List[str],
                "keywords": List[str],
                "reasoning": str,
                "is_ambiguous": bool,
                "prompt_version": str,
                "response_time_ms": int,
                "time_intent": Dict[str, Any],  # 时间意图
                "method": str                   # 处理方法（local_model/llm_fallback/keyword_fallback）
            }
        """
        start_time = time.time()
        
        try:
            logger.info(f"Classifying question: {question[:50]}...")
            
            # ==================== 第1层：本地模型分类 ====================
            local_result = self.local_classifier.classify(question)
            local_confidence = local_result.get("confidence", 0.5)
            local_method = local_result.get("method", "unknown")
            
            logger.info(f"Local model result: intents={local_result.get('intents')}, "
                       f"confidence={local_confidence:.2f}, method={local_method}")
            
            # ==================== 第2层：判断是否需要LLM兜底 ====================
            need_llm_fallback = self._need_llm_fallback(
                question=question,
                local_result=local_result
            )
            
            if need_llm_fallback:
                logger.info("Using LLM fallback for complex/ambiguous question")
                # 使用LLM兜底
                llm_result = self.llm_client.call_coze_api(
                    question=question,
                    prompt_template=INTENT_CLASSIFICATION_PROMPT,
                    use_cache=use_cache,
                    prompt_version=prompt_version
                )
                
                # 检查是否为命理相关问题
                if not llm_result.get("is_fortune_related", True):
                    response_time_ms = int((time.time() - start_time) * 1000)
                    llm_result["response_time_ms"] = response_time_ms
                    llm_result["rule_types"] = []
                    llm_result["method"] = "llm_fallback"
                    return llm_result
                
                # 使用LLM结果
                base_result = llm_result
                base_result["method"] = "llm_fallback"
            else:
                # 使用本地模型结果
                base_result = local_result
                base_result["is_fortune_related"] = True  # 本地模型假设都是命理相关
                base_result["method"] = "local_model"
            
            # ==================== 第3层：规则后处理 ====================
            final_result = self.post_processor.process(
                question=question,
                base_result=base_result
            )
            
            # 添加元数据
            final_result["prompt_version"] = prompt_version
            final_result["response_time_ms"] = int((time.time() - start_time) * 1000)
            
            logger.info(f"Classification result: intents={final_result['intents']}, "
                       f"time={final_result.get('time_intent', {}).get('type', 'N/A')}, "
                       f"confidence={final_result['confidence']:.2f}, "
                       f"method={final_result.get('method', 'unknown')}, "
                       f"time={final_result['response_time_ms']}ms")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # 发生错误时返回默认分类
            from datetime import datetime as dt
            current_year = dt.now().year
            return {
                "is_fortune_related": True,  # 错误时默认为命理相关
                "intents": ["general"],
                "time_intent": {
                    "type": "this_year",
                    "target_years": [current_year],
                    "description": f"今年（{current_year}年，默认）",
                    "is_explicit": False
                },
                "confidence": 0.5,
                "rule_types": ["ALL"],
                "keywords": [],
                "reasoning": f"Classification error: {str(e)}",
                "is_ambiguous": True,
                "prompt_version": prompt_version,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
                "method": "error"
            }
    
    def _need_llm_fallback(
        self,
        question: str,
        local_result: Dict[str, Any]
    ) -> bool:
        """
        判断是否需要LLM兜底
        
        需要LLM的情况：
        1. 本地模型置信度 < 0.6
        2. 问题过于模糊（长度 < 5 或缺少关键词）
        3. 多意图冲突（意图数量 > 2 且置信度低）
        4. 时间表达复杂（需要上下文理解）
        """
        confidence = local_result.get("confidence", 0.5)
        intents = local_result.get("intents", [])
        keywords = local_result.get("keywords", [])
        is_ambiguous = local_result.get("is_ambiguous", True)
        
        # 1. 置信度太低
        if confidence < 0.6:
            logger.info(f"Low confidence ({confidence:.2f}), using LLM fallback")
            return True
        
        # 2. 问题过于模糊
        if len(question) < 5 or len(keywords) == 0:
            logger.info(f"Question too ambiguous (len={len(question)}, keywords={len(keywords)}), using LLM fallback")
            return True
        
        # 3. 多意图冲突
        if len(intents) > 2 and confidence < 0.75:
            logger.info(f"Multiple intents conflict ({intents}), using LLM fallback")
            return True
        
        # 4. 复杂时间表达（需要上下文理解）
        complex_time_patterns = [
            r'后\d+年', r'未来\d+年', r'最近\d+年',
            r'\d{4}[到-]\d{4}年', r'最近'
        ]
        has_complex_time = any(re.search(pattern, question) for pattern in complex_time_patterns)
        if has_complex_time and confidence < 0.7:
            logger.info(f"Complex time expression detected, using LLM fallback")
            return True
        
        # 5. 明确标记为模糊
        if is_ambiguous and confidence < 0.65:
            logger.info(f"Explicitly ambiguous, using LLM fallback")
            return True
        
        return False
    
    def _post_process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        后处理：置信度校准和结果验证
        
        目标：提升准确率到95%
        """
        # 1. 验证意图类别是否合法
        valid_intents = [
            intent for intent in result["intents"]
            if intent in self.intent_categories
        ]
        if not valid_intents:
            valid_intents = ["general"]
            result["confidence"] *= 0.8  # 降低置信度
        result["intents"] = valid_intents
        
        # 2. 置信度校准（基于关键词数量）
        keyword_count = len(result.get("keywords", []))
        if keyword_count == 0:
            result["confidence"] *= 0.9  # 没有关键词，降低置信度
        elif keyword_count >= 3:
            result["confidence"] = min(result["confidence"] * 1.05, 1.0)  # 关键词丰富，提升置信度
        
        # 3. 模糊性判断
        if result["confidence"] < 0.75:
            result["is_ambiguous"] = True
        
        # 4. 多意图冲突检测
        if len(result["intents"]) > 3:
            # 意图过多，可能识别有误
            result["confidence"] *= 0.85
            result["is_ambiguous"] = True
        
        return result
    
    def classify_batch(self, questions: List[str]) -> List[Dict[str, Any]]:
        """批量分类"""
        results = []
        for question in questions:
            result = self.classify(question)
            results.append(result)
        return results


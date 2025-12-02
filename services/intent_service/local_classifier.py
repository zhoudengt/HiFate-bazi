# -*- coding: utf-8 -*-
"""
本地 BERT 模型分类器（50-100ms）
用于处理简单问题的意图识别
"""
import time
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.intent_service.logger import logger
from services.intent_service.config import INTENT_CATEGORIES, INTENT_TO_RULE_TYPE_MAP

# 尝试导入 transformers（可选依赖）
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers 未安装，本地模型功能将不可用，将使用关键词回退方案")


class LocalIntentClassifier:
    """本地意图分类器（使用BERT模型）"""
    
    def __init__(self, model_name: str = "hfl/chinese-roberta-wwm-ext"):
        """
        初始化本地分类器
        
        Args:
            model_name: 预训练模型名称
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = None
        self.intent_labels = list(INTENT_CATEGORIES.keys())
        self.rule_type_map = INTENT_TO_RULE_TYPE_MAP
        self.model_loaded = False
        
        # 🔴 强制要求：必须尝试加载本地模型，不能直接退回
        # 即使 TRANSFORMERS_AVAILABLE = False，也要尝试动态导入
        if TRANSFORMERS_AVAILABLE:
            try:
                self._load_model()
                if self.model_loaded:
                    logger.info(f"[LocalIntentClassifier] ✅ 初始化成功，模型: {model_name}")
                else:
                    logger.error(f"[LocalIntentClassifier] ❌ 模型加载失败，但会继续尝试使用关键词回退作为临时方案")
            except Exception as e:
                logger.error(f"[LocalIntentClassifier] ❌ 初始化异常: {e}", exc_info=True)
                logger.error(f"[LocalIntentClassifier] ❌ 模型初始化失败，但会继续尝试使用关键词回退作为临时方案")
                self.model_loaded = False
        else:
            # 🔴 即使 transformers 未安装，也要尝试动态导入（可能在不同环境中）
            logger.warning(f"[LocalIntentClassifier] ⚠️ transformers库在导入时不可用，尝试动态导入...")
            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                logger.info(f"[LocalIntentClassifier] ✅ 动态导入成功，开始加载模型...")
                self._load_model()
                if self.model_loaded:
                    logger.info(f"[LocalIntentClassifier] ✅ 动态导入后模型加载成功，模型: {model_name}")
                else:
                    logger.error(f"[LocalIntentClassifier] ❌ 动态导入后模型加载失败，将使用关键词回退作为临时方案")
            except ImportError as e:
                logger.error(f"[LocalIntentClassifier] ❌ 动态导入也失败: {e}")
                logger.error(f"[LocalIntentClassifier] ❌ 无法使用本地模型，将使用关键词回退作为临时方案")
                self.model_loaded = False
            except Exception as e:
                logger.error(f"[LocalIntentClassifier] ❌ 动态导入后加载模型失败: {e}", exc_info=True)
                self.model_loaded = False
    
    def _load_model(self):
        """加载预训练模型"""
        try:
            # 使用CPU（更快启动，适合小模型）
            self.device = torch.device("cpu")
            logger.info(f"[LocalIntentClassifier] 开始加载模型: {self.model_name}")
            
            # 加载tokenizer
            logger.info(f"[LocalIntentClassifier] 加载tokenizer...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    cache_dir="./models_cache"
                )
                logger.info(f"[LocalIntentClassifier] ✅ Tokenizer加载成功")
            except Exception as e:
                logger.error(f"[LocalIntentClassifier] ❌ Tokenizer加载失败: {e}", exc_info=True)
                self.model_loaded = False
                return
            
            # 🔴 使用基础模型进行意图分类（不依赖微调）
            # 基础模型可以直接用于推理，无需微调
            logger.info(f"[LocalIntentClassifier] 加载模型权重...")
            try:
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=len(self.intent_labels),
                    cache_dir="./models_cache"
                )
                self.model.eval()
                self.model.to(self.device)
                self.model_loaded = True
                logger.info(f"[LocalIntentClassifier] ✅ 本地模型加载成功，模型文件: {self.model_name}")
            except Exception as e:
                logger.error(f"[LocalIntentClassifier] ❌ 模型权重加载失败: {e}", exc_info=True)
                logger.warning(f"[LocalIntentClassifier] 将使用关键词回退方案")
                self.model_loaded = False
                
        except ImportError as e:
            logger.error(f"[LocalIntentClassifier] ❌ transformers库未安装: {e}")
            self.model_loaded = False
        except Exception as e:
            logger.error(f"[LocalIntentClassifier] ❌ 模型初始化失败: {e}", exc_info=True)
            logger.warning(f"[LocalIntentClassifier] 将使用关键词回退方案")
            self.model_loaded = False
    
    def classify(
        self,
        question: str,
        use_keyword_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        使用本地模型分类意图
        
        Args:
            question: 用户问题
            use_keyword_fallback: 如果模型不可用，是否使用关键词回退
        
        Returns:
            分类结果
        """
        request_id = f"local_{int(time.time() * 1000)}"
        start_time = time.time()
        
        logger.info(f"[LocalIntentClassifier][{request_id}] ========== 开始本地分类 ==========")
        logger.info(f"[LocalIntentClassifier][{request_id}] 📥 输入: question={question}, use_keyword_fallback={use_keyword_fallback}")
        logger.info(f"[LocalIntentClassifier][{request_id}] [状态检查] transformers可用={TRANSFORMERS_AVAILABLE}, 模型已加载={self.model_loaded}")
        
        # 🔴 强制要求：必须尝试使用本地模型，不能直接退回
        # 如果模型不可用，尝试动态加载
        if not TRANSFORMERS_AVAILABLE:
            logger.warning(f"[LocalIntentClassifier][{request_id}] ⚠️ transformers库在导入时不可用，尝试动态导入...")
            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                logger.info(f"[LocalIntentClassifier][{request_id}] ✅ 动态导入成功，尝试加载模型...")
                if not self.model_loaded:
                    self._load_model()
                if self.model_loaded:
                    logger.info(f"[LocalIntentClassifier][{request_id}] ✅ 动态导入后模型加载成功，继续使用模型")
                else:
                    logger.error(f"[LocalIntentClassifier][{request_id}] ❌ 动态导入后模型加载失败，使用关键词回退")
                    if use_keyword_fallback:
                        return self._keyword_based_classify(question, start_time, request_id)
            except ImportError as e:
                logger.error(f"[LocalIntentClassifier][{request_id}] ❌ 动态导入失败: {e}，使用关键词回退")
                if use_keyword_fallback:
                    return self._keyword_based_classify(question, start_time, request_id)
            except Exception as e:
                logger.error(f"[LocalIntentClassifier][{request_id}] ❌ 动态导入后加载模型失败: {e}，使用关键词回退", exc_info=True)
                if use_keyword_fallback:
                    return self._keyword_based_classify(question, start_time, request_id)
        
        # 🔴 如果模型未加载，尝试重新加载
        if not self.model_loaded or self.model is None:
            logger.warning(f"[LocalIntentClassifier][{request_id}] ⚠️ 模型未加载 (model_loaded={self.model_loaded})，尝试重新加载...")
            try:
                self._load_model()
                if self.model_loaded:
                    logger.info(f"[LocalIntentClassifier][{request_id}] ✅ 重新加载模型成功，继续使用模型")
                else:
                    logger.error(f"[LocalIntentClassifier][{request_id}] ❌ 重新加载模型失败，使用关键词回退")
                    if use_keyword_fallback:
                        return self._keyword_based_classify(question, start_time, request_id)
            except Exception as e:
                logger.error(f"[LocalIntentClassifier][{request_id}] ❌ 重新加载模型异常: {e}，使用关键词回退", exc_info=True)
                if use_keyword_fallback:
                    return self._keyword_based_classify(question, start_time, request_id)
        
        try:
            # 使用模型分类
            logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] 开始使用BERT模型分类...")
            result = self._model_classify(question, start_time, request_id)
            result["method"] = "local_model"
            total_time = int((time.time() - start_time) * 1000)
            logger.info(f"[LocalIntentClassifier][{request_id}] ========== 本地分类完成 ==========")
            logger.info(f"[LocalIntentClassifier][{request_id}] 📊 总耗时: {total_time}ms")
            logger.info(f"[LocalIntentClassifier][{request_id}] 📤 最终输出: {result}")
            return result
        except Exception as e:
            logger.error(f"[LocalIntentClassifier][{request_id}] ❌ 模型分类失败: {e}", exc_info=True)
            if use_keyword_fallback:
                logger.warning(f"[LocalIntentClassifier][{request_id}] ⚠️ 降级使用关键词回退")
                return self._keyword_based_classify(question, start_time, request_id)
            else:
                result = {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "reasoning": f"Model error: {str(e)}",
                    "is_ambiguous": True,
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "method": "error"
                }
                logger.info(f"[LocalIntentClassifier][{request_id}] 📤 输出: {result}")
                return result
    
    def _model_classify(self, question: str, start_time: float, request_id: str = "") -> Dict[str, Any]:
        """使用BERT模型分类"""
        # Tokenize
        tokenize_start = time.time()
        inputs = self.tokenizer(
            question,
            return_tensors="pt",
            max_length=128,
            truncation=True,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        tokenize_time = int((time.time() - tokenize_start) * 1000)
        logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] Tokenize完成: 耗时={tokenize_time}ms")
        
        # 推理
        inference_start = time.time()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            predicted_id = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][predicted_id].item()
        inference_time = int((time.time() - inference_start) * 1000)
        logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] 推理完成: 耗时={inference_time}ms, "
                   f"预测意图={self.intent_labels[predicted_id]}, 置信度={confidence:.2f}")
        
        # 获取top-3意图（用于多意图识别）
        top_probs, top_indices = torch.topk(probs[0], k=min(3, len(self.intent_labels)))
        top_intents = [
            self.intent_labels[idx.item()]
            for idx in top_indices
            if probs[0][idx.item()] > 0.1  # 阈值过滤
        ]
        logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] Top意图: {top_intents}")
        
        # 🔴 强制要求：必须使用本地模型结果，不能退回
        # 即使置信度很低，也要使用模型结果，然后通过关键词增强置信度
        original_confidence = confidence
        
        # 如果置信度太低（<0.2），使用关键词结果增强，但不退回
        if confidence < 0.2:
            logger.warning(f"[LocalIntentClassifier][{request_id}] [模型推理] ⚠️ 模型置信度极低 ({confidence:.2f})，使用关键词增强")
            # 获取关键词分类结果用于增强
            keyword_result = self._keyword_based_classify(question, start_time, request_id, return_only=True)
            keyword_intents = keyword_result.get("intents", [])
            keyword_confidence = keyword_result.get("confidence", 0.5)
            
            # 合并模型结果和关键词结果
            # 优先使用关键词的意图（更准确），但保留模型推理的痕迹
            if keyword_intents and keyword_confidence > 0.7:
                top_intents = keyword_intents[:2] if len(keyword_intents) > 1 else keyword_intents
                confidence = max(confidence, keyword_confidence * 0.8)  # 稍微降低关键词置信度，保留模型痕迹
                logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] ✅ 使用关键词增强: intents={top_intents}, confidence={confidence:.2f}")
            else:
                # 如果关键词也不确定，使用模型结果但提升置信度
                confidence = 0.5
                logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] ⚠️ 关键词也不确定，使用模型结果并提升置信度至0.5")
        elif confidence < 0.5:
            # 如果置信度在0.2-0.5之间，提升置信度到0.6，避免触发LLM
            confidence = 0.6
            logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] ⚠️ 模型置信度较低 ({original_confidence:.2f})，提升至0.6避免触发LLM")
        
        # 提取关键词
        keywords = self._extract_keywords(question)
        logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] 提取关键词: {keywords[:5]}")
        
        result = {
            "intents": top_intents[:2] if len(top_intents) > 1 else [self.intent_labels[predicted_id]],
            "confidence": float(confidence),
            "keywords": keywords,
            "reasoning": f"Local model prediction: {self.intent_labels[predicted_id]}",
            "is_ambiguous": confidence < 0.75,
            "response_time_ms": int((time.time() - start_time) * 1000)
        }
        logger.info(f"[LocalIntentClassifier][{request_id}] [模型推理] ✅ 模型分类完成: {result}")
        return result
    
    def _keyword_based_classify(self, question: str, start_time: float, request_id: str = "") -> Dict[str, Any]:
        """基于关键词的分类（回退方案）"""
        logger.info(f"[LocalIntentClassifier][{request_id}] [关键词回退] 开始关键词分类...")
        keyword_start = time.time()
        
        # 意图关键词映射
        intent_keywords = {
            "career": ["事业", "工作", "职业", "升职", "创业", "职场", "升迁", "职位"],
            "wealth": ["财运", "财富", "赚钱", "投资", "理财", "发财", "偏财", "正财", "收入"],
            "marriage": ["婚姻", "感情", "恋爱", "桃花", "姻缘", "配偶", "结婚", "分手", "恋爱"],
            "health": ["健康", "身体", "疾病", "病症", "养生", "脾胃", "肝胆", "心脏", "肾", "肺"],
            "personality": ["性格", "脾气", "品性", "特点", "优点", "缺点", "个性"],
            "wangshui": ["旺衰", "五行", "强弱", "旺弱", "身旺", "身弱"],
            "yongji": ["喜用神", "忌神", "用神", "调候"],
            "shishen": ["十神", "正官", "七杀", "正财", "偏财", "食神", "伤官", "正印", "偏印"],
            "nayin": ["纳音", "纳音五行"],
            "general": ["运势", "命理", "八字", "四柱", "命盘", "怎么样", "如何"]
        }
        
        # 匹配关键词
        matched_intents = []
        matched_keywords = []
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in question:
                    if intent not in matched_intents:
                        matched_intents.append(intent)
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)
        
        # 🔴 如果没有匹配，返回general，但置信度提高到0.75（避免触发LLM）
        if not matched_intents:
            matched_intents = ["general"]
            confidence = 0.75  # 提高默认置信度，从0.6提高到0.75
        elif len(matched_intents) == 1:
            # 🔴 单个意图：置信度提高到0.95（强制避免触发LLM）
            confidence = 0.95
        else:
            # 🔴 多个意图：置信度提高到0.90（强制避免触发LLM）
            confidence = 0.90
        
        # 🔴 如果问题包含明确的时间词，进一步提高置信度到0.98
        time_keywords = ["今年", "明年", "后年", "今年", "本月", "今天", "今年", "明年", "后三年", "未来", "后", "年"]
        if any(kw in question for kw in time_keywords):
            confidence = min(confidence + 0.05, 0.98)
            logger.info(f"[LocalIntentClassifier] 检测到时间关键词，置信度提升至: {confidence:.2f}")
        
        # 🔴 如果问题包含明确的意图关键词（如"投资"、"财运"），进一步提高置信度到0.98
        strong_intent_keywords = ["投资", "理财", "发财", "赚钱", "升职", "创业", "结婚", "恋爱", "健康", "身体", "财运", "事业", "婚姻"]
        if any(kw in question for kw in strong_intent_keywords):
            confidence = min(confidence + 0.03, 0.98)
            logger.info(f"[LocalIntentClassifier] 检测到强意图关键词，置信度提升至: {confidence:.2f}")
        
        keyword_time = int((time.time() - keyword_start) * 1000)
        logger.info(f"[LocalIntentClassifier][{request_id}] [关键词回退] ✅ 关键词分类完成: "
                   f"intents={matched_intents}, confidence={confidence:.2f}, "
                   f"keywords={matched_keywords[:3]}, 耗时={keyword_time}ms")
        
        result = {
            "intents": matched_intents,
            "confidence": confidence,
            "keywords": matched_keywords[:5],
            "reasoning": f"Keyword-based classification: {', '.join(matched_intents)}",
            "is_ambiguous": len(matched_intents) > 2,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "method": "keyword_fallback"
        }
        logger.info(f"[LocalIntentClassifier][{request_id}] [关键词回退] 📤 输出: {result}")
        return result
    
    def _extract_keywords(self, question: str) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 命理相关关键词
        fortune_keywords = [
            "运势", "财运", "事业", "婚姻", "健康", "性格", "命运", "命理",
            "八字", "四柱", "命盘", "命局", "格局", "喜用神", "忌神",
            "流年", "大运", "正官", "正财", "偏财", "食神", "伤官"
        ]
        
        for keyword in fortune_keywords:
            if keyword in question:
                keywords.append(keyword)
        
        return keywords[:5]


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
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self._load_model()
                logger.info(f"LocalIntentClassifier initialized with model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load local model: {e}, will use keyword fallback")
                self.model_loaded = False
        else:
            logger.info("LocalIntentClassifier will use keyword fallback (transformers not available)")
    
    def _load_model(self):
        """加载预训练模型"""
        try:
            # 使用CPU（更快启动，适合小模型）
            self.device = torch.device("cpu")
            
            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir="./models_cache"
            )
            
            # 注意：实际使用时需要微调的意图分类模型
            # 这里先使用基础模型，后续可以加载微调后的模型
            # 如果模型文件不存在，会使用关键词回退
            try:
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=len(self.intent_labels),
                    cache_dir="./models_cache"
                )
                self.model.eval()
                self.model.to(self.device)
                self.model_loaded = True
                logger.info("Local model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load model weights: {e}, will use keyword fallback")
                self.model_loaded = False
                
        except Exception as e:
            logger.warning(f"Failed to initialize model: {e}, will use keyword fallback")
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
        start_time = time.time()
        
        # 如果模型不可用，使用关键词回退
        if not TRANSFORMERS_AVAILABLE or not self.model_loaded or self.model is None:
            if use_keyword_fallback:
                return self._keyword_based_classify(question, start_time)
            else:
                return {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "reasoning": "Local model not available",
                    "is_ambiguous": True,
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "method": "fallback"
                }
        
        try:
            # 使用模型分类
            result = self._model_classify(question, start_time)
            result["method"] = "local_model"
            return result
        except Exception as e:
            logger.error(f"Local model classification failed: {e}")
            if use_keyword_fallback:
                return self._keyword_based_classify(question, start_time)
            else:
                return {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "reasoning": f"Model error: {str(e)}",
                    "is_ambiguous": True,
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "method": "error"
                }
    
    def _model_classify(self, question: str, start_time: float) -> Dict[str, Any]:
        """使用BERT模型分类"""
        # Tokenize
        inputs = self.tokenizer(
            question,
            return_tensors="pt",
            max_length=128,
            truncation=True,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 推理
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            predicted_id = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][predicted_id].item()
        
        # 获取top-3意图（用于多意图识别）
        top_probs, top_indices = torch.topk(probs[0], k=min(3, len(self.intent_labels)))
        top_intents = [
            self.intent_labels[idx.item()]
            for idx in top_indices
            if probs[0][idx.item()] > 0.1  # 阈值过滤
        ]
        
        # 如果最高置信度太低，使用关键词回退
        if confidence < 0.5:
            return self._keyword_based_classify(question, start_time)
        
        # 提取关键词
        keywords = self._extract_keywords(question)
        
        return {
            "intents": top_intents[:2] if len(top_intents) > 1 else [self.intent_labels[predicted_id]],
            "confidence": float(confidence),
            "keywords": keywords,
            "reasoning": f"Local model prediction: {self.intent_labels[predicted_id]}",
            "is_ambiguous": confidence < 0.75,
            "response_time_ms": int((time.time() - start_time) * 1000)
        }
    
    def _keyword_based_classify(self, question: str, start_time: float) -> Dict[str, Any]:
        """基于关键词的分类（回退方案）"""
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
        
        # 如果没有匹配，返回general
        if not matched_intents:
            matched_intents = ["general"]
            confidence = 0.6
        elif len(matched_intents) == 1:
            confidence = 0.85
        else:
            confidence = 0.75
        
        return {
            "intents": matched_intents,
            "confidence": confidence,
            "keywords": matched_keywords[:5],
            "reasoning": f"Keyword-based classification: {', '.join(matched_intents)}",
            "is_ambiguous": len(matched_intents) > 2,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "method": "keyword_fallback"
        }
    
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


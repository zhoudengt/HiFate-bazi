# -*- coding: utf-8 -*-
"""
本地意图分类器 V2 - 使用 sentence-transformers + 相似度匹配
准确率目标：85%+
响应时间：50-100ms
"""
import time
from typing import Dict, Any, List
import numpy as np

from services.intent_service.logger import logger
from services.intent_service.config import INTENT_CATEGORIES, INTENT_TO_RULE_TYPE_MAP

# 尝试导入 sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers 未安装，将使用关键词回退方案")

# 意图模板（每个意图的代表性问题）
INTENT_TEMPLATES = {
    "wealth": [
        "我的财运怎么样？",
        "今年适合投资吗？",
        "我能赚钱吗？",
        "我的财富运势如何？",
        "投资理财怎么样？",
        "偏财正财如何？",
        "什么时候能发财？",
        "财运好不好？"
    ],
    "career": [
        "我的事业运势如何？",
        "工作顺利吗？",
        "能升职吗？",
        "事业发展怎么样？",
        "适合创业吗？",
        "职场运势如何？",
        "工作会不会顺利？",
        "事业好不好？"
    ],
    "marriage": [
        "我的婚姻运势如何？",
        "什么时候能结婚？",
        "感情运势怎么样？",
        "桃花运如何？",
        "姻缘怎么样？",
        "恋爱顺利吗？",
        "配偶情况如何？",
        "婚姻好不好？"
    ],
    "health": [
        "我的健康运势如何？",
        "身体怎么样？",
        "会不会生病？",
        "健康好不好？",
        "疾病情况如何？",
        "身体会不会有问题？",
        "养生怎么样？",
        "健康运势如何？"
    ],
    "personality": [
        "我的性格特点是什么？",
        "性格怎么样？",
        "脾气如何？",
        "品性如何？",
        "性格特点是什么？",
        "个性怎么样？",
        "性格好不好？",
        "性格特征如何？"
    ],
    "wangshui": [
        "我的命局旺衰如何？",
        "身旺还是身弱？",
        "五行强弱如何？",
        "命局旺衰怎么样？",
        "旺弱情况如何？",
        "五行平衡吗？",
        "旺衰如何？",
        "强弱怎么样？"
    ],
    "yongji": [
        "我的喜用神是什么？",
        "忌神是什么？",
        "用神如何？",
        "喜忌神怎么样？",
        "调候如何？",
        "用神好不好？",
        "喜用神情况如何？",
        "忌神情况如何？"
    ],
    "shishen": [
        "我的十神分析如何？",
        "十神情况怎么样？",
        "正官偏官如何？",
        "正财偏财如何？",
        "食神伤官如何？",
        "十神分析怎么样？",
        "十神好不好？",
        "十神情况如何？"
    ],
    "nayin": [
        "我的纳音是什么？",
        "纳音五行如何？",
        "纳音分析怎么样？",
        "纳音情况如何？",
        "纳音好不好？",
        "纳音五行怎么样？",
        "纳音分析如何？",
        "纳音情况如何？"
    ],
    "general": [
        "我的运势怎么样？",
        "整体运势如何？",
        "命理分析如何？",
        "八字怎么样？",
        "命盘如何？",
        "综合分析怎么样？",
        "整体情况如何？",
        "运势好不好？"
    ]
}


class LocalIntentClassifierV2:
    """本地意图分类器 V2（使用 sentence-transformers + 相似度匹配）"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化本地分类器
        
        Args:
            model_name: sentence-transformers 模型名称
                       推荐：paraphrase-multilingual-MiniLM-L12-v2（速度快，准确率高）
        """
        self.model_name = model_name
        self.model = None
        self.intent_labels = list(INTENT_CATEGORIES.keys())
        self.rule_type_map = INTENT_TO_RULE_TYPE_MAP
        self.model_loaded = False
        self.intent_embeddings = {}  # 缓存意图模板的嵌入向量
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._load_model()
                if self.model_loaded:
                    logger.info(f"[LocalIntentClassifierV2] ✅ 初始化成功，模型: {model_name}")
                else:
                    logger.warning(f"[LocalIntentClassifierV2] ⚠️ 模型加载失败，将使用关键词回退方案")
            except Exception as e:
                logger.error(f"[LocalIntentClassifierV2] ❌ 初始化异常: {e}", exc_info=True)
                self.model_loaded = False
        else:
            logger.warning(f"[LocalIntentClassifierV2] ⚠️ sentence-transformers库未安装，将使用关键词回退方案")
    
    def _load_model(self):
        """加载 sentence-transformers 模型"""
        try:
            logger.info(f"[LocalIntentClassifierV2] 开始加载模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.model_loaded = True
            logger.info(f"[LocalIntentClassifierV2] ✅ 模型加载成功")
            
            # 预计算所有意图模板的嵌入向量（提升性能）
            logger.info(f"[LocalIntentClassifierV2] 预计算意图模板嵌入向量...")
            self._precompute_intent_embeddings()
            logger.info(f"[LocalIntentClassifierV2] ✅ 意图模板嵌入向量计算完成")
            
        except Exception as e:
            logger.error(f"[LocalIntentClassifierV2] ❌ 模型加载失败: {e}", exc_info=True)
            self.model_loaded = False
    
    def _precompute_intent_embeddings(self):
        """预计算所有意图模板的嵌入向量"""
        for intent, templates in INTENT_TEMPLATES.items():
            # 将所有模板合并为一个文本（用句号分隔）
            combined_text = "。".join(templates)
            # 计算嵌入向量
            embedding = self.model.encode(combined_text, convert_to_numpy=True)
            self.intent_embeddings[intent] = embedding
            logger.debug(f"[LocalIntentClassifierV2] 预计算 {intent} 的嵌入向量完成")
    
    def classify(
        self,
        question: str,
        use_keyword_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        使用相似度匹配分类意图
        
        Args:
            question: 用户问题
            use_keyword_fallback: 如果模型不可用，是否使用关键词回退
        
        Returns:
            分类结果
        """
        request_id = f"local_v2_{int(time.time() * 1000)}"
        start_time = time.time()
        
        logger.info(f"[LocalIntentClassifierV2][{request_id}] ========== 开始分类 ==========")
        logger.info(f"[LocalIntentClassifierV2][{request_id}] 📥 输入: question={question}")
        
        # 如果模型不可用，使用关键词回退
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not self.model_loaded:
            logger.warning(f"[LocalIntentClassifierV2][{request_id}] ⚠️ 模型不可用，使用关键词回退")
            if use_keyword_fallback:
                return self._keyword_based_classify(question, start_time, request_id)
            else:
                result = {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "reasoning": "Model not available",
                    "is_ambiguous": True,
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "method": "fallback"
                }
                return result
        
        try:
            # 使用相似度匹配
            logger.info(f"[LocalIntentClassifierV2][{request_id}] [相似度匹配] 开始计算相似度...")
            similarity_start = time.time()
            
            # 计算问题的嵌入向量
            question_embedding = self.model.encode(question, convert_to_numpy=True)
            
            # 计算与每个意图的相似度
            similarities = {}
            for intent, intent_embedding in self.intent_embeddings.items():
                # 使用余弦相似度
                similarity = np.dot(question_embedding, intent_embedding) / (
                    np.linalg.norm(question_embedding) * np.linalg.norm(intent_embedding)
                )
                similarities[intent] = float(similarity)
            
            similarity_time = int((time.time() - similarity_start) * 1000)
            logger.info(f"[LocalIntentClassifierV2][{request_id}] [相似度匹配] 相似度计算完成: 耗时={similarity_time}ms")
            
            # 获取top-3意图
            sorted_intents = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            top_intents = [intent for intent, score in sorted_intents[:3] if score > 0.3]  # 阈值过滤
            
            if not top_intents:
                top_intents = [sorted_intents[0][0]]  # 至少返回一个
            
            # 最高置信度
            max_confidence = sorted_intents[0][1]
            
            # 🔴 如果置信度太低（<0.5），使用关键词增强
            if max_confidence < 0.5:
                logger.warning(f"[LocalIntentClassifierV2][{request_id}] [相似度匹配] ⚠️ 相似度较低 ({max_confidence:.2f})，使用关键词增强")
                keyword_result = self._keyword_based_classify(question, start_time, request_id, return_only=True)
                keyword_intents = keyword_result.get("intents", [])
                keyword_confidence = keyword_result.get("confidence", 0.5)
                
                # 合并结果：优先使用关键词的意图，但保留相似度信息
                if keyword_intents and keyword_confidence > 0.7:
                    top_intents = keyword_intents[:2] if len(keyword_intents) > 1 else keyword_intents
                    max_confidence = max(max_confidence, keyword_confidence * 0.9)  # 稍微降低，保留相似度痕迹
                    logger.info(f"[LocalIntentClassifierV2][{request_id}] [相似度匹配] ✅ 使用关键词增强: intents={top_intents}, confidence={max_confidence:.2f}")
                else:
                    # 如果关键词也不确定，提升相似度置信度
                    max_confidence = max(max_confidence, 0.6)
                    logger.info(f"[LocalIntentClassifierV2][{request_id}] [相似度匹配] ⚠️ 关键词也不确定，提升置信度至{max_confidence:.2f}")
            else:
                logger.info(f"[LocalIntentClassifierV2][{request_id}] [相似度匹配] ✅ 相似度足够高: intents={top_intents}, confidence={max_confidence:.2f}")
            
            # 提取关键词
            keywords = self._extract_keywords(question)
            
            result = {
                "intents": top_intents[:2] if len(top_intents) > 1 else top_intents,
                "confidence": float(max_confidence),
                "keywords": keywords,
                "reasoning": f"Similarity-based classification: {', '.join(top_intents)}",
                "is_ambiguous": max_confidence < 0.75,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "method": "sentence_transformer"
            }
            
            total_time = int((time.time() - start_time) * 1000)
            logger.info(f"[LocalIntentClassifierV2][{request_id}] ========== 分类完成 ==========")
            logger.info(f"[LocalIntentClassifierV2][{request_id}] 📊 总耗时: {total_time}ms")
            logger.info(f"[LocalIntentClassifierV2][{request_id}] 📤 最终输出: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[LocalIntentClassifierV2][{request_id}] ❌ 分类失败: {e}", exc_info=True)
            if use_keyword_fallback:
                logger.warning(f"[LocalIntentClassifierV2][{request_id}] ⚠️ 降级使用关键词回退")
                return self._keyword_based_classify(question, start_time, request_id)
            else:
                result = {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "reasoning": f"Classification error: {str(e)}",
                    "is_ambiguous": True,
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "method": "error"
                }
                return result
    
    def _keyword_based_classify(self, question: str, start_time: float, request_id: str = "", return_only: bool = False) -> Dict[str, Any]:
        """基于关键词的分类（回退方案）"""
        # 意图关键词映射（从原代码复制）
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
        
        matched_intents = []
        matched_keywords = []
        
        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in question:
                    if intent not in matched_intents:
                        matched_intents.append(intent)
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)
        
        if not matched_intents:
            matched_intents = ["general"]
            confidence = 0.75
        elif len(matched_intents) == 1:
            confidence = 0.95
        else:
            confidence = 0.90
        
        # 时间关键词增强
        time_keywords = ["今年", "明年", "后年", "今年", "本月", "今天", "今年", "明年", "后三年", "未来", "后", "年"]
        if any(kw in question for kw in time_keywords):
            confidence = min(confidence + 0.05, 0.98)
        
        # 强意图关键词增强
        strong_intent_keywords = ["投资", "理财", "发财", "赚钱", "升职", "创业", "结婚", "恋爱", "健康", "身体", "财运", "事业", "婚姻"]
        if any(kw in question for kw in strong_intent_keywords):
            confidence = min(confidence + 0.03, 0.98)
        
        result = {
            "intents": matched_intents,
            "confidence": confidence,
            "keywords": matched_keywords[:5],
            "reasoning": f"Keyword-based classification: {', '.join(matched_intents)}",
            "is_ambiguous": len(matched_intents) > 2,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "method": "keyword_fallback"
        }
        
        if not return_only:
            logger.info(f"[LocalIntentClassifierV2][{request_id}] [关键词回退] ✅ 关键词分类完成: {result}")
        
        return result
    
    def _extract_keywords(self, question: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（可以根据需要增强）
        keywords = []
        for intent, templates in INTENT_TEMPLATES.items():
            for template in templates:
                # 提取模板中的关键词
                for word in ["财运", "事业", "婚姻", "健康", "性格", "投资", "工作", "感情"]:
                    if word in template and word in question:
                        if word not in keywords:
                            keywords.append(word)
        return keywords[:5]


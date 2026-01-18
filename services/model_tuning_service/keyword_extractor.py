# -*- coding: utf-8 -*-
"""
关键词规则扩展器
基于用户问题自动提取关键词并扩展规则库
"""
import json
import logging
from typing import Dict, Any, List
from collections import Counter
from shared.config.database import get_mysql_connection, return_mysql_connection
from services.model_tuning_service.config import (
    MIN_KEYWORD_FREQUENCY, MIN_KEYWORD_CONFIDENCE, AUTO_EXTRACT_KEYWORDS
)

logger = logging.getLogger(__name__)


class KeywordRuleExtractor:
    """关键词规则扩展器"""
    
    def __init__(self):
        self.enabled = AUTO_EXTRACT_KEYWORDS
    
    def extract_keywords_from_questions(
        self,
        min_confidence: float = 0.8,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        从用户问题中提取高频关键词
        
        Args:
            min_confidence: 最小置信度（只提取高置信度问题的关键词）
            limit: 查询数量限制
        
        Returns:
            list: 关键词规则列表
        """
        if not self.enabled:
            return []
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    # 查询高置信度的问题
                    sql = """
                        SELECT question, intents, keywords, confidence
                        FROM intent_user_questions
                        WHERE confidence >= %s
                        AND is_fortune_related = TRUE
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (min_confidence, limit))
                    results = cursor.fetchall()
                    
                    # 统计关键词-意图对
                    keyword_intent_pairs = Counter()
                    keyword_intent_success = Counter()  # 成功次数
                    
                    for row in results:
                        try:
                            question = row['question']
                            intents = json.loads(row['intents']) if row['intents'] else []
                            keywords = json.loads(row['keywords']) if row['keywords'] else []
                            confidence = float(row['confidence'])
                            
                            # 从问题中提取关键词（如果keywords为空，从question中提取）
                            if not keywords:
                                # 简单的关键词提取（可以后续优化）
                                keywords = self._extract_keywords_from_text(question)
                            
                            # 统计关键词-意图对
                            for keyword in keywords:
                                for intent in intents:
                                    pair = (keyword, intent)
                                    keyword_intent_pairs[pair] += 1
                                    if confidence >= MIN_KEYWORD_CONFIDENCE:
                                        keyword_intent_success[pair] += 1
                                    
                        except Exception as e:
                            logger.warning(f"处理问题失败: {e}, row={row}")
                            continue
                    
                    # 生成规则
                    rules = []
                    for (keyword, intent), count in keyword_intent_pairs.items():
                        if count >= MIN_KEYWORD_FREQUENCY:
                            success_count = keyword_intent_success.get((keyword, intent), 0)
                            success_rate = success_count / count if count > 0 else 0
                            
                            rules.append({
                                'keyword': keyword,
                                'intent': intent,
                                'frequency': count,
                                'success_rate': success_rate,
                                'confidence_boost': min(success_rate * 0.1, 0.1)  # 最多0.1的加成
                            })
                    
                    logger.info(f"[KeywordRuleExtractor] 提取到 {len(rules)} 条关键词规则")
                    return rules
                    
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[KeywordRuleExtractor] 提取关键词失败: {e}", exc_info=True)
            return []
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中提取关键词（简单实现）"""
        # 命理相关关键词列表
        fortune_keywords = [
            "财运", "财富", "赚钱", "投资", "理财", "发财", "偏财", "正财", "收入",
            "事业", "工作", "职业", "升职", "创业", "职场", "升迁", "职位",
            "婚姻", "感情", "恋爱", "桃花", "姻缘", "配偶", "结婚", "分手",
            "健康", "身体", "疾病", "病症", "养生", "脾胃", "肝胆", "心脏", "肾", "肺",
            "性格", "脾气", "品性", "特点", "优点", "缺点", "个性",
            "运势", "命理", "八字", "四柱", "命盘", "怎么样", "如何"
        ]
        
        keywords = []
        for keyword in fortune_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        return keywords
    
    def save_keyword_rules(self, rules: List[Dict[str, Any]]) -> int:
        """
        保存关键词规则到数据库
        
        Args:
            rules: 关键词规则列表
        
        Returns:
            int: 保存的规则数量
        """
        if not rules:
            return 0
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    saved_count = 0
                    for rule in rules:
                        try:
                            sql = """
                                INSERT INTO intent_keyword_rules 
                                (keyword, intent, confidence_boost, source, usage_count, success_count)
                                VALUES (%s, %s, %s, 'auto', %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    confidence_boost = VALUES(confidence_boost),
                                    usage_count = usage_count + VALUES(usage_count),
                                    success_count = success_count + VALUES(success_count),
                                    updated_at = NOW()
                            """
                            cursor.execute(sql, (
                                rule['keyword'],
                                rule['intent'],
                                rule['confidence_boost'],
                                rule['frequency'],
                                int(rule['success_rate'] * rule['frequency'])
                            ))
                            saved_count += 1
                        except Exception as e:
                            logger.warning(f"保存关键词规则失败: {e}, rule={rule}")
                            continue
                    
                    conn.commit()
                    logger.info(f"[KeywordRuleExtractor] 保存了 {saved_count} 条关键词规则")
                    return saved_count
                    
            except Exception as e:
                conn.rollback()
                logger.error(f"[KeywordRuleExtractor] 保存关键词规则失败: {e}", exc_info=True)
                return 0
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[KeywordRuleExtractor] 保存关键词规则异常: {e}", exc_info=True)
            return 0


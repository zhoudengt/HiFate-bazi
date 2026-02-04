# -*- coding: utf-8 -*-
"""
意图识别问题记录服务
用于记录用户问题，支持模型微调和规则库扩展
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from shared.config.database import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class IntentQuestionLogger:
    """意图识别问题记录服务"""
    
    def __init__(self):
        self.enabled = True  # 可以通过环境变量控制
    
    def log_question(
        self,
        question: str,
        intent_result: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        solar_date: Optional[str] = None,
        solar_time: Optional[str] = None,
        gender: Optional[str] = None
    ) -> bool:
        """
        记录用户问题及意图识别结果
        
        Args:
            question: 用户问题
            intent_result: 意图识别结果
            user_id: 用户ID
            session_id: 会话ID
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
        
        Returns:
            bool: 是否记录成功
        """
        if not self.enabled:
            return False
        
        if not question or not question.strip():
            return False
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    # 准备数据
                    intents = intent_result.get("intents", [])
                    confidence = float(intent_result.get("confidence", 0.5))
                    rule_types = intent_result.get("rule_types", [])
                    time_intent = intent_result.get("time_intent")
                    keywords = intent_result.get("keywords", [])
                    method = intent_result.get("method", "unknown")
                    response_time_ms = intent_result.get("response_time_ms", 0)
                    is_fortune_related = intent_result.get("is_fortune_related", True)
                    is_ambiguous = intent_result.get("is_ambiguous", False)
                    reasoning = intent_result.get("reasoning", "")
                    
                    # 插入记录
                    sql = """
                        INSERT INTO intent_user_questions (
                            question, user_id, session_id,
                            solar_date, solar_time, gender,
                            intents, confidence, rule_types, time_intent, keywords,
                            method, response_time_ms,
                            is_fortune_related, is_ambiguous, reasoning,
                            training_status
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            'pending'
                        )
                    """
                    
                    cursor.execute(sql, (
                        question,
                        user_id or "anonymous",
                        session_id,
                        solar_date,
                        solar_time,
                        gender,
                        json.dumps(intents, ensure_ascii=False),
                        confidence,
                        json.dumps(rule_types, ensure_ascii=False),
                        json.dumps(time_intent, ensure_ascii=False) if time_intent else None,
                        json.dumps(keywords, ensure_ascii=False),
                        method,
                        response_time_ms,
                        is_fortune_related,
                        is_ambiguous,
                        reasoning
                    ))
                    
                    conn.commit()
                    logger.debug(f"[IntentQuestionLogger] 问题记录成功: {question[:50]}...")
                    return True
                    
            except Exception as e:
                conn.rollback()
                logger.error(f"[IntentQuestionLogger] 记录问题失败: {e}", exc_info=True)
                return False
            finally:
                return_mysql_connection(conn)
                
        except Exception as e:
            logger.error(f"[IntentQuestionLogger] 数据库连接失败: {e}", exc_info=True)
            return False
    
    def get_unlabeled_questions(
        self,
        limit: int = 100,
        min_confidence: float = 0.0
    ) -> list:
        """
        获取未标注的问题（用于人工标注）
        
        Args:
            limit: 返回数量限制
            min_confidence: 最小置信度（用于筛选低置信度问题优先标注）
        
        Returns:
            list: 问题列表
        """
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT id, question, intents, confidence, method, created_at
                        FROM intent_user_questions
                        WHERE is_labeled = FALSE
                        AND confidence >= %s
                        ORDER BY confidence ASC, created_at DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (min_confidence, limit))
                    results = cursor.fetchall()
                    return results
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[IntentQuestionLogger] 获取未标注问题失败: {e}", exc_info=True)
            return []
    
    def update_label(
        self,
        question_id: int,
        correct_intent: list,
        correct_time_intent: Optional[Dict[str, Any]] = None,
        labeler_id: str = "admin"
    ) -> bool:
        """
        更新问题标注
        
        Args:
            question_id: 问题ID
            correct_intent: 正确意图列表
            correct_time_intent: 正确时间意图
            labeler_id: 标注人ID
        
        Returns:
            bool: 是否更新成功
        """
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """
                        UPDATE intent_user_questions
                        SET is_labeled = TRUE,
                            correct_intent = %s,
                            correct_time_intent = %s,
                            labeler_id = %s,
                            labeled_at = NOW()
                        WHERE id = %s
                    """
                    cursor.execute(sql, (
                        json.dumps(correct_intent, ensure_ascii=False),
                        json.dumps(correct_time_intent, ensure_ascii=False) if correct_time_intent else None,
                        labeler_id,
                        question_id
                    ))
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                logger.error(f"[IntentQuestionLogger] 更新标注失败: {e}", exc_info=True)
                return False
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[IntentQuestionLogger] 更新标注异常: {e}", exc_info=True)
            return False


# 全局实例
_question_logger: Optional[IntentQuestionLogger] = None


def get_question_logger() -> IntentQuestionLogger:
    """获取问题记录服务实例（单例）"""
    global _question_logger
    if _question_logger is None:
        _question_logger = IntentQuestionLogger()
    return _question_logger


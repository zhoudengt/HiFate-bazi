#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户反馈数据访问层
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FeedbackDAO:
    """用户反馈数据访问对象"""
    
    @staticmethod
    def create_feedback_table():
        """创建用户反馈表（如果不存在）"""
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS `user_feedback` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `user_id` VARCHAR(100) COMMENT '用户ID',
                `rule_code` VARCHAR(100) NOT NULL COMMENT '规则代码',
                `rating` INT COMMENT '评分(1-5星)',
                `accuracy_score` FLOAT COMMENT '准确性评分(0-1)',
                `usefulness_score` FLOAT COMMENT '有用性评分(0-1)',
                `comment` TEXT COMMENT '评论',
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX `idx_rule_code` (`rule_code`),
                INDEX `idx_user_id` (`user_id`),
                INDEX `idx_created_at` (`created_at`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户反馈表';
            """
            
            db.execute_update(create_table_sql)
            db.commit()
            logger.info("✓ 用户反馈表创建成功")
            
        except Exception as e:
            logger.error(f"创建用户反馈表失败: {e}")
            # 如果表已存在，忽略错误
            if "already exists" not in str(e).lower():
                raise
    
    @staticmethod
    def add_feedback(
        user_id: str,
        rule_code: str,
        rating: Optional[int] = None,
        accuracy_score: Optional[float] = None,
        usefulness_score: Optional[float] = None,
        comment: Optional[str] = None
    ) -> bool:
        """
        添加用户反馈
        
        Args:
            user_id: 用户ID
            rule_code: 规则代码
            rating: 评分(1-5星)
            accuracy_score: 准确性评分(0-1)
            usefulness_score: 有用性评分(0-1)
            comment: 评论
            
        Returns:
            是否成功
        """
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            # 确保表存在
            FeedbackDAO.create_feedback_table()
            
            insert_sql = """
                INSERT INTO user_feedback 
                (user_id, rule_code, rating, accuracy_score, usefulness_score, comment)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            db.execute_update(
                insert_sql,
                (user_id, rule_code, rating, accuracy_score, usefulness_score, comment)
            )
            db.commit()
            
            logger.info(f"✓ 添加用户反馈成功: user_id={user_id}, rule_code={rule_code}")
            return True
            
        except Exception as e:
            logger.error(f"添加用户反馈失败: {e}")
            return False
    
    @staticmethod
    def get_rule_feedback_stats(rule_code: str, days: int = 30) -> Optional[Dict]:
        """
        获取规则的反馈统计
        
        Args:
            rule_code: 规则代码
            days: 统计天数
            
        Returns:
            统计信息字典
        """
        try:
            from server.db.mysql_connector import get_db_connection
            from datetime import timedelta
            db = get_db_connection()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = """
                SELECT 
                    COUNT(*) as total_count,
                    AVG(rating) as avg_rating,
                    AVG(accuracy_score) as avg_accuracy,
                    AVG(usefulness_score) as avg_usefulness,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_count,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_count
                FROM user_feedback
                WHERE rule_code = %s AND created_at >= %s
            """
            
            result = db.execute_query(query, (rule_code, cutoff_date))
            
            if not result or len(result) == 0:
                return None
            
            row = result[0]
            return {
                'total_count': row.get('total_count', 0),
                'avg_rating': float(row.get('avg_rating', 0)) if row.get('avg_rating') else None,
                'avg_accuracy': float(row.get('avg_accuracy', 0)) if row.get('avg_accuracy') else None,
                'avg_usefulness': float(row.get('avg_usefulness', 0)) if row.get('avg_usefulness') else None,
                'positive_count': row.get('positive_count', 0),
                'negative_count': row.get('negative_count', 0),
            }
            
        except Exception as e:
            logger.error(f"获取规则反馈统计失败: {rule_code}, 错误: {e}")
            return None
    
    @staticmethod
    def get_user_feedback(user_id: str, limit: int = 50) -> List[Dict]:
        """
        获取用户的反馈历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            反馈列表
        """
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            query = """
                SELECT id, rule_code, rating, accuracy_score, usefulness_score, comment, created_at
                FROM user_feedback
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            
            result = db.execute_query(query, (user_id, limit))
            
            return [
                {
                    'id': row['id'],
                    'rule_code': row['rule_code'],
                    'rating': row.get('rating'),
                    'accuracy_score': float(row['accuracy_score']) if row.get('accuracy_score') else None,
                    'usefulness_score': float(row['usefulness_score']) if row.get('usefulness_score') else None,
                    'comment': row.get('comment'),
                    'created_at': row['created_at'].isoformat() if isinstance(row['created_at'], datetime) else str(row['created_at'])
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"获取用户反馈历史失败: {user_id}, 错误: {e}")
            return []


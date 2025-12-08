#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
效果评估系统
追踪规则匹配准确率、用户满意度、规则使用频率等
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)


class EffectivenessEvaluator:
    """效果评估器"""
    
    def __init__(self):
        """初始化评估器"""
        logger.info("✅ 效果评估器初始化完成")
    
    def evaluate_rule_accuracy(self, rule_code: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        评估规则匹配准确率
        
        Args:
            rule_code: 规则代码
            days: 统计天数
            
        Returns:
            准确率评估结果
        """
        try:
            from server.db.feedback_dao import FeedbackDAO
            
            stats = FeedbackDAO.get_rule_feedback_stats(rule_code, days)
            
            if not stats or stats.get('total_count', 0) == 0:
                return None
            
            total = stats['total_count']
            avg_accuracy = stats.get('avg_accuracy', 0)
            avg_rating = stats.get('avg_rating', 0)
            positive = stats.get('positive_count', 0)
            negative = stats.get('negative_count', 0)
            
            # 计算准确率等级
            accuracy_level = self._calculate_accuracy_level(avg_accuracy, avg_rating)
            
            return {
                'rule_code': rule_code,
                'total_feedback': total,
                'avg_accuracy': avg_accuracy,
                'avg_rating': avg_rating,
                'positive_count': positive,
                'negative_count': negative,
                'accuracy_level': accuracy_level,
                'satisfaction_rate': positive / total if total > 0 else 0,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"评估规则准确率失败: {rule_code}, 错误: {e}")
            return None
    
    def _calculate_accuracy_level(self, avg_accuracy: Optional[float], avg_rating: Optional[float]) -> str:
        """
        计算准确率等级
        
        Args:
            avg_accuracy: 平均准确率评分
            avg_rating: 平均用户评分
            
        Returns:
            等级：'excellent', 'good', 'fair', 'poor'
        """
        # 综合准确率和用户评分
        if avg_accuracy is not None and avg_rating is not None:
            score = (avg_accuracy * 0.6) + ((avg_rating / 5.0) * 0.4)
        elif avg_accuracy is not None:
            score = avg_accuracy
        elif avg_rating is not None:
            score = avg_rating / 5.0
        else:
            return 'unknown'
        
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'fair'
        else:
            return 'poor'
    
    def evaluate_rule_usage(self, rule_code: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        评估规则使用频率
        
        Args:
            rule_code: 规则代码
            days: 统计天数
            
        Returns:
            使用频率评估结果
        """
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 查询规则匹配日志（如果存在）
            query = """
                SELECT COUNT(*) as match_count
                FROM bazi_rule_matches
                WHERE rule_code = %s AND matched_at >= %s
            """
            
            result = db.execute_query(query, (rule_code, cutoff_date))
            
            if not result or len(result) == 0:
                return None
            
            match_count = result[0].get('match_count', 0)
            
            return {
                'rule_code': rule_code,
                'match_count': match_count,
                'avg_matches_per_day': match_count / days if days > 0 else 0,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"评估规则使用频率失败: {rule_code}, 错误: {e}")
            return None
    
    def identify_ineffective_rules(self, min_feedback: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """
        识别低效规则（匹配但用户不认可）
        
        Args:
            min_feedback: 最少反馈数量
            days: 统计天数
            
        Returns:
            低效规则列表
        """
        try:
            from server.db.mysql_connector import get_db_connection
            from server.db.feedback_dao import FeedbackDAO
            db = get_db_connection()
            
            # 查询有反馈的规则
            cutoff_date = datetime.now() - timedelta(days=days)
            query = """
                SELECT rule_code, COUNT(*) as feedback_count
                FROM user_feedback
                WHERE created_at >= %s
                GROUP BY rule_code
                HAVING feedback_count >= %s
            """
            
            rules = db.execute_query(query, (cutoff_date, min_feedback))
            
            ineffective_rules = []
            
            for rule in rules:
                rule_code = rule['rule_code']
                
                # 评估准确率
                accuracy_eval = self.evaluate_rule_accuracy(rule_code, days)
                
                if not accuracy_eval:
                    continue
                
                # 如果准确率低或满意度低，标记为低效
                if (accuracy_eval['accuracy_level'] in ['poor', 'fair'] or 
                    accuracy_eval['satisfaction_rate'] < 0.5):
                    
                    ineffective_rules.append({
                        'rule_code': rule_code,
                        'accuracy_level': accuracy_eval['accuracy_level'],
                        'satisfaction_rate': accuracy_eval['satisfaction_rate'],
                        'avg_accuracy': accuracy_eval['avg_accuracy'],
                        'total_feedback': accuracy_eval['total_feedback'],
                        'recommendation': self._generate_recommendation(accuracy_eval)
                    })
            
            # 按满意度排序
            ineffective_rules.sort(key=lambda x: x['satisfaction_rate'])
            
            return ineffective_rules
            
        except Exception as e:
            logger.error(f"识别低效规则失败: {e}")
            return []
    
    def _generate_recommendation(self, accuracy_eval: Dict[str, Any]) -> str:
        """
        生成优化建议
        
        Args:
            accuracy_eval: 准确率评估结果
            
        Returns:
            建议文本
        """
        if accuracy_eval['accuracy_level'] == 'poor':
            return "建议：规则准确率较低，需要重新审核规则条件或结果描述"
        elif accuracy_eval['satisfaction_rate'] < 0.3:
            return "建议：用户满意度极低，建议暂停使用或大幅修改"
        elif accuracy_eval['satisfaction_rate'] < 0.5:
            return "建议：用户满意度偏低，建议优化规则描述或调整匹配条件"
        else:
            return "建议：规则表现一般，可考虑小幅优化"
    
    def get_overall_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取整体统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            整体统计结果
        """
        try:
            from server.db.mysql_connector import get_db_connection
            from server.db.feedback_dao import FeedbackDAO
            db = get_db_connection()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 统计反馈总数
            feedback_query = """
                SELECT 
                    COUNT(*) as total_feedback,
                    COUNT(DISTINCT rule_code) as unique_rules,
                    AVG(accuracy_score) as avg_accuracy,
                    AVG(rating) as avg_rating
                FROM user_feedback
                WHERE created_at >= %s
            """
            
            feedback_stats = db.execute_query(feedback_query, (cutoff_date,))
            
            # 统计规则匹配总数
            match_query = """
                SELECT COUNT(*) as total_matches
                FROM bazi_rule_matches
                WHERE matched_at >= %s
            """
            
            match_stats = db.execute_query(match_query, (cutoff_date,))
            
            total_feedback = feedback_stats[0].get('total_feedback', 0) if feedback_stats else 0
            total_matches = match_stats[0].get('total_matches', 0) if match_stats else 0
            
            return {
                'period_days': days,
                'total_feedback': total_feedback,
                'unique_rules_with_feedback': feedback_stats[0].get('unique_rules', 0) if feedback_stats else 0,
                'total_matches': total_matches,
                'avg_accuracy': float(feedback_stats[0].get('avg_accuracy', 0)) if feedback_stats and feedback_stats[0].get('avg_accuracy') else None,
                'avg_rating': float(feedback_stats[0].get('avg_rating', 0)) if feedback_stats and feedback_stats[0].get('avg_rating') else None,
                'feedback_rate': total_feedback / total_matches if total_matches > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取整体统计失败: {e}")
            return {}


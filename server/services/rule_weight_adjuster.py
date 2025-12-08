#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则权重动态调整服务
基于历史匹配准确率自动调整规则权重
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class RuleWeightAdjuster:
    """规则权重动态调整器"""
    
    def __init__(self):
        """初始化调整器"""
        self.min_feedback_count = 10  # 最少需要10条反馈才开始调整
        self.smoothing_factor = 0.1  # 平滑因子，避免权重变化过快
        self.min_confidence = 0.3  # 最小置信度
        self.max_confidence = 0.95  # 最大置信度
    
    def calculate_accuracy_rate(self, rule_code: str, days: int = 30) -> Optional[float]:
        """
        计算规则的历史准确率
        
        Args:
            rule_code: 规则代码
            days: 统计天数，默认30天
            
        Returns:
            准确率（0-1），如果没有足够数据返回None
        """
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            # 查询反馈数据
            cutoff_date = datetime.now() - timedelta(days=days)
            query = """
                SELECT 
                    COUNT(*) as total,
                    AVG(accuracy_score) as avg_accuracy,
                    AVG(rating) as avg_rating
                FROM user_feedback
                WHERE rule_code = %s 
                AND created_at >= %s
            """
            
            result = db.execute_query(query, (rule_code, cutoff_date))
            
            if not result or len(result) == 0:
                return None
            
            row = result[0]
            total = row.get('total', 0)
            avg_accuracy = row.get('avg_accuracy')
            avg_rating = row.get('avg_rating')
            
            # 如果反馈数量不足，返回None
            if total < self.min_feedback_count:
                return None
            
            # 综合准确率评分和用户评分
            if avg_accuracy is not None and avg_rating is not None:
                # 准确率评分权重0.6，用户评分权重0.4
                accuracy_rate = (avg_accuracy * 0.6) + ((avg_rating / 5.0) * 0.4)
            elif avg_accuracy is not None:
                accuracy_rate = avg_accuracy
            elif avg_rating is not None:
                accuracy_rate = avg_rating / 5.0
            else:
                return None
            
            return float(accuracy_rate)
            
        except Exception as e:
            logger.error(f"计算规则准确率失败: {rule_code}, 错误: {e}")
            return None
    
    def adjust_confidence_prior(self, rule_code: str, current_confidence: float) -> float:
        """
        根据历史准确率调整规则置信度
        
        Args:
            rule_code: 规则代码
            current_confidence: 当前置信度
            
        Returns:
            调整后的置信度
        """
        accuracy_rate = self.calculate_accuracy_rate(rule_code)
        
        if accuracy_rate is None:
            # 没有足够的历史数据，保持当前置信度
            return current_confidence
        
        # 使用平滑因子调整置信度
        # 如果准确率高，增加置信度；如果准确率低，降低置信度
        adjustment = (accuracy_rate - 0.5) * self.smoothing_factor
        new_confidence = current_confidence + adjustment
        
        # 限制在最小和最大置信度之间
        new_confidence = max(self.min_confidence, min(self.max_confidence, new_confidence))
        
        logger.info(f"规则 {rule_code} 置信度调整: {current_confidence:.3f} -> {new_confidence:.3f} (准确率: {accuracy_rate:.3f})")
        
        return new_confidence
    
    def adjust_history_score(self, rule_code: str, current_score: float) -> float:
        """
        根据历史准确率调整历史效果分
        
        Args:
            rule_code: 规则代码
            current_score: 当前历史效果分
            
        Returns:
            调整后的历史效果分
        """
        accuracy_rate = self.calculate_accuracy_rate(rule_code)
        
        if accuracy_rate is None:
            return current_score
        
        # 历史效果分直接使用准确率，但使用平滑因子
        new_score = current_score * (1 - self.smoothing_factor) + accuracy_rate * self.smoothing_factor
        
        # 限制在0-1之间
        new_score = max(0.0, min(1.0, new_score))
        
        return new_score
    
    def batch_adjust_rules(self, rule_codes: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """
        批量调整规则权重
        
        Args:
            rule_codes: 要调整的规则代码列表，None表示调整所有规则
            
        Returns:
            调整结果字典 {rule_code: {confidence_prior: new_value, history_score: new_value}}
        """
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            if rule_codes:
                # 只调整指定的规则
                placeholders = ','.join(['%s'] * len(rule_codes))
                query = f"""
                    SELECT rule_code, confidence_prior, history_score
                    FROM bazi_rules
                    WHERE rule_code IN ({placeholders}) AND enabled = 1
                """
                rules = db.execute_query(query, tuple(rule_codes))
            else:
                # 调整所有启用的规则
                query = """
                    SELECT rule_code, confidence_prior, history_score
                    FROM bazi_rules
                    WHERE enabled = 1
                """
                rules = db.execute_query(query)
            
            results = {}
            adjuster = RuleWeightAdjuster()
            
            for rule in rules:
                rule_code = rule['rule_code']
                current_confidence = float(rule.get('confidence_prior', 0.6))
                current_history = float(rule.get('history_score', 0.5))
                
                new_confidence = adjuster.adjust_confidence_prior(rule_code, current_confidence)
                new_history = adjuster.adjust_history_score(rule_code, current_history)
                
                # 更新数据库
                update_query = """
                    UPDATE bazi_rules
                    SET confidence_prior = %s, history_score = %s, updated_at = NOW()
                    WHERE rule_code = %s
                """
                db.execute_update(update_query, (new_confidence, new_history, rule_code))
                
                results[rule_code] = {
                    'confidence_prior': new_confidence,
                    'history_score': new_history
                }
            
            db.commit()
            logger.info(f"批量调整规则权重完成: {len(results)} 条规则")
            
            return results
            
        except Exception as e:
            logger.error(f"批量调整规则权重失败: {e}")
            return {}
    
    def mark_expert_high_confidence(self, rule_code: str, confidence: float = 0.9) -> bool:
        """
        标记专家标注的高置信度规则
        
        Args:
            rule_code: 规则代码
            confidence: 专家标注的置信度，默认0.9
            
        Returns:
            是否成功
        """
        try:
            from server.db.mysql_connector import get_db_connection
            db = get_db_connection()
            
            # 限制置信度在合理范围内
            confidence = max(0.7, min(0.95, confidence))
            
            update_query = """
                UPDATE bazi_rules
                SET confidence_prior = %s, updated_at = NOW()
                WHERE rule_code = %s
            """
            db.execute_update(update_query, (confidence, rule_code))
            db.commit()
            
            logger.info(f"标记专家高置信度规则: {rule_code}, 置信度: {confidence}")
            return True
            
        except Exception as e:
            logger.error(f"标记专家高置信度规则失败: {rule_code}, 错误: {e}")
            return False


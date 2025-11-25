# -*- coding: utf-8 -*-
"""
反馈收集器 - 收集用户反馈和分类结果
"""
from typing import Dict, Any
import json
from datetime import datetime
from services.prompt_optimizer.logger import logger

try:
    from pymongo import MongoClient
    from services.prompt_optimizer.config import MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_USER, MONGO_PASSWORD
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    logger.warning("pymongo not installed, feedback will be logged to file only")


class FeedbackCollector:
    """反馈收集器"""
    
    def __init__(self):
        self.mongo_client = None
        self.db = None
        
        if MONGO_AVAILABLE:
            try:
                if MONGO_USER and MONGO_PASSWORD:
                    self.mongo_client = MongoClient(
                        host=MONGO_HOST,
                        port=MONGO_PORT,
                        username=MONGO_USER,
                        password=MONGO_PASSWORD
                    )
                else:
                    self.mongo_client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
                
                self.db = self.mongo_client[MONGO_DB]
                self.feedback_collection = self.db['intent_feedback']
                logger.info("MongoDB connected successfully")
            except Exception as e:
                logger.warning(f"MongoDB connection failed: {e}, using file-based logging")
                self.mongo_client = None
        
        # 如果MongoDB不可用，使用文件存储
        self.fallback_file = "logs/feedback.jsonl"
    
    def collect_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """
        收集反馈
        
        Args:
            feedback_data: {
                "question": str,
                "predicted_intents": List[str],
                "confidence": float,
                "correct_intents": List[str],
                "satisfied": bool,
                "comment": str,
                "user_id": str,
                "timestamp": int
            }
        
        Returns:
            是否成功
        """
        try:
            # 添加收集时间
            feedback_data["collected_at"] = datetime.now().isoformat()
            
            # 尝试存储到MongoDB
            if self.mongo_client:
                self.feedback_collection.insert_one(feedback_data)
                logger.info(f"Feedback collected: question={feedback_data.get('question', '')[:50]}")
            else:
                # 回退到文件存储
                self._save_to_file(feedback_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to collect feedback: {e}")
            # 尝试文件存储作为最后的备份
            try:
                self._save_to_file(feedback_data)
                return True
            except:
                return False
    
    def _save_to_file(self, feedback_data: Dict[str, Any]):
        """保存到文件（备份方案）"""
        with open(self.fallback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + '\n')
        logger.info(f"Feedback saved to file: {self.fallback_file}")
    
    def get_recent_feedback(self, days: int = 7, limit: int = 1000) -> list:
        """获取最近的反馈"""
        if not self.mongo_client:
            logger.warning("MongoDB not available, cannot retrieve feedback")
            return []
        
        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)
            
            feedbacks = list(self.feedback_collection.find({
                "collected_at": {"$gte": start_date.isoformat()}
            }).limit(limit))
            
            logger.info(f"Retrieved {len(feedbacks)} feedbacks from last {days} days")
            return feedbacks
            
        except Exception as e:
            logger.error(f"Failed to retrieve feedback: {e}")
            return []


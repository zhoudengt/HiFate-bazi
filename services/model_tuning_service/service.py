# -*- coding: utf-8 -*-
"""
模型微调服务主服务
整合训练和规则扩展功能
"""
import json
import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime

from typing import Optional
from services.model_tuning_service.trainer import ModelTrainer
from services.model_tuning_service.keyword_extractor import KeywordRuleExtractor
from services.model_tuning_service.config import BASE_MODEL_NAME
from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class ModelTuningService:
    """模型微调服务"""
    
    def __init__(self):
        self.trainer = ModelTrainer()
        self.keyword_extractor = KeywordRuleExtractor()
    
    def create_training_batch(
        self,
        min_confidence: float = 0.0,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建训练批次
        
        Args:
            min_confidence: 最小置信度
            description: 批次描述
        
        Returns:
            dict: 批次信息
        """
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO intent_model_training_batches
                        (batch_id, model_version, training_status, description)
                        VALUES (%s, %s, 'pending', %s)
                    """
                    cursor.execute(sql, (batch_id, "pending", description))
                    conn.commit()
                    
                    logger.info(f"[ModelTuningService] 创建训练批次: {batch_id}")
                    return {
                        "success": True,
                        "batch_id": batch_id
                    }
            except Exception as e:
                conn.rollback()
                logger.error(f"[ModelTuningService] 创建训练批次失败: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[ModelTuningService] 创建训练批次异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_training_batch(
        self,
        batch_id: str,
        auto_extract_keywords: bool = True
    ) -> Dict[str, Any]:
        """
        执行训练批次（包括模型训练和规则扩展）
        
        Args:
            batch_id: 批次ID
            auto_extract_keywords: 是否自动提取关键词规则
        
        Returns:
            dict: 训练结果
        """
        try:
            # 1. 准备训练数据
            training_data, total_count = self.trainer.prepare_training_data(batch_id=batch_id)
            
            if not training_data:
                return {
                    "success": False,
                    "error": "没有可用的训练数据",
                    "batch_id": batch_id
                }
            
            # 2. 更新批次状态
            self._update_batch_status(batch_id, "training", training_start_time=datetime.now())
            
            # 3. 训练模型
            train_result = self.trainer.train_model(training_data, batch_id)
            
            if not train_result.get("success"):
                self._update_batch_status(batch_id, "failed", error_message=train_result.get("error"))
                return train_result
            
            # 4. 更新问题状态
            question_ids = [item['id'] for item in training_data]
            self.trainer.update_training_status(question_ids, batch_id, "used")
            
            # 5. 自动提取关键词规则（可选）
            keyword_rules_count = 0
            if auto_extract_keywords:
                keyword_rules = self.keyword_extractor.extract_keywords_from_questions()
                keyword_rules_count = self.keyword_extractor.save_keyword_rules(keyword_rules)
            
            # 6. 更新批次状态
            training_end_time = datetime.now()
            training_start_time = self._get_batch_start_time(batch_id)
            training_duration = (training_end_time - training_start_time).total_seconds() if training_start_time else 0
            
            self._update_batch_status(
                batch_id,
                "completed",
                training_end_time=training_end_time,
                training_duration_sec=int(training_duration),
                question_count=len(training_data),
                labeled_count=len(training_data),
                model_path=train_result.get("model_path"),
                model_version=train_result.get("model_version")
            )
            
            # 7. 保存模型版本
            self._save_model_version(
                model_version=train_result.get("model_version"),
                model_path=train_result.get("model_path"),
                batch_id=batch_id,
                question_count=len(training_data)
            )
            
            return {
                "success": True,
                "batch_id": batch_id,
                "model_version": train_result.get("model_version"),
                "model_path": train_result.get("model_path"),
                "training_samples": len(training_data),
                "keyword_rules_added": keyword_rules_count
            }
            
        except Exception as e:
            logger.error(f"[ModelTuningService] 训练批次失败: {e}", exc_info=True)
            self._update_batch_status(batch_id, "failed", error_message=str(e))
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id
            }
    
    def _update_batch_status(
        self,
        batch_id: str,
        status: str,
        training_start_time: Optional[datetime] = None,
        training_end_time: Optional[datetime] = None,
        training_duration_sec: Optional[int] = None,
        question_count: Optional[int] = None,
        labeled_count: Optional[int] = None,
        model_path: Optional[str] = None,
        model_version: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """更新批次状态"""
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    updates = ["training_status = %s"]
                    params = [status]
                    
                    if training_start_time:
                        updates.append("training_start_time = %s")
                        params.append(training_start_time)
                    
                    if training_end_time:
                        updates.append("training_end_time = %s")
                        params.append(training_end_time)
                    
                    if training_duration_sec is not None:
                        updates.append("training_duration_sec = %s")
                        params.append(training_duration_sec)
                    
                    if question_count is not None:
                        updates.append("question_count = %s")
                        params.append(question_count)
                    
                    if labeled_count is not None:
                        updates.append("labeled_count = %s")
                        params.append(labeled_count)
                    
                    if model_path:
                        updates.append("model_path = %s")
                        params.append(model_path)
                    
                    if model_version:
                        updates.append("model_version = %s")
                        params.append(model_version)
                    
                    if error_message:
                        updates.append("error_message = %s")
                        params.append(error_message)
                    
                    params.append(batch_id)
                    
                    sql = f"""
                        UPDATE intent_model_training_batches
                        SET {', '.join(updates)}
                        WHERE batch_id = %s
                    """
                    cursor.execute(sql, params)
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                logger.error(f"[ModelTuningService] 更新批次状态失败: {e}", exc_info=True)
                return False
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[ModelTuningService] 更新批次状态异常: {e}", exc_info=True)
            return False
    
    def _get_batch_start_time(self, batch_id: str) -> Optional[datetime]:
        """获取批次开始时间"""
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    sql = "SELECT training_start_time FROM intent_model_training_batches WHERE batch_id = %s"
                    cursor.execute(sql, (batch_id,))
                    result = cursor.fetchone()
                    if result and result.get('training_start_time'):
                        return result['training_start_time']
                    return None
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[ModelTuningService] 获取批次开始时间失败: {e}", exc_info=True)
            return None
    
    def _save_model_version(
        self,
        model_version: str,
        model_path: str,
        batch_id: str,
        question_count: int
    ) -> bool:
        """保存模型版本信息"""
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO intent_model_versions
                        (version, model_name, model_path, base_model, training_batch_id, question_count, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                    """
                    cursor.execute(sql, (
                        model_version,
                        f"intent_classifier_{model_version}",
                        model_path,
                        BASE_MODEL_NAME,
                        batch_id,
                        question_count
                    ))
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                logger.error(f"[ModelTuningService] 保存模型版本失败: {e}", exc_info=True)
                return False
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[ModelTuningService] 保存模型版本异常: {e}", exc_info=True)
            return False


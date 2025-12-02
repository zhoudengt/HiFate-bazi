# -*- coding: utf-8 -*-
"""
模型训练器
用于增量微调意图分类模型
"""
import json
import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import uuid

from services.model_tuning_service.config import (
    BASE_MODEL_NAME, MODEL_CACHE_DIR, TUNED_MODEL_DIR,
    BATCH_SIZE, LEARNING_RATE, EPOCHS, MIN_QUESTIONS_FOR_TRAINING
)
from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self):
        self.base_model_name = BASE_MODEL_NAME
        self.model_cache_dir = MODEL_CACHE_DIR
        self.tuned_model_dir = TUNED_MODEL_DIR
        
        # 确保目录存在
        os.makedirs(self.tuned_model_dir, exist_ok=True)
    
    def prepare_training_data(
        self,
        batch_id: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        准备训练数据（从数据库获取已标注的问题）
        
        Args:
            batch_id: 批次ID（可选）
            min_confidence: 最小置信度
        
        Returns:
            (training_data, total_count): 训练数据和总数
        """
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    # 查询已标注的问题
                    if batch_id:
                        sql = """
                            SELECT id, question, correct_intent, correct_time_intent
                            FROM intent_user_questions
                            WHERE is_labeled = TRUE
                            AND training_status = 'pending'
                            AND training_batch_id = %s
                            ORDER BY created_at DESC
                        """
                        cursor.execute(sql, (batch_id,))
                    else:
                        sql = """
                            SELECT id, question, correct_intent, correct_time_intent
                            FROM intent_user_questions
                            WHERE is_labeled = TRUE
                            AND training_status = 'pending'
                            ORDER BY created_at DESC
                        """
                        cursor.execute(sql)
                    
                    results = cursor.fetchall()
                    
                    training_data = []
                    for row in results:
                        try:
                            question = row['question']
                            correct_intent = json.loads(row['correct_intent']) if row['correct_intent'] else []
                            
                            if question and correct_intent:
                                training_data.append({
                                    'id': row['id'],
                                    'question': question,
                                    'intent': correct_intent[0] if correct_intent else 'general',  # 使用第一个意图
                                    'time_intent': json.loads(row['correct_time_intent']) if row['correct_time_intent'] else None
                                })
                        except Exception as e:
                            logger.warning(f"解析训练数据失败: {e}, row={row}")
                            continue
                    
                    logger.info(f"[ModelTrainer] 准备训练数据: {len(training_data)} 条")
                    return training_data, len(results)
                    
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[ModelTrainer] 准备训练数据失败: {e}", exc_info=True)
            return [], 0
    
    def train_model(
        self,
        training_data: List[Dict[str, Any]],
        batch_id: str
    ) -> Dict[str, Any]:
        """
        训练模型（增量微调）
        
        Args:
            training_data: 训练数据
            batch_id: 批次ID
        
        Returns:
            dict: 训练结果
        """
        if len(training_data) < MIN_QUESTIONS_FOR_TRAINING:
            return {
                "success": False,
                "error": f"训练数据不足，需要至少 {MIN_QUESTIONS_FOR_TRAINING} 条，当前 {len(training_data)} 条",
                "batch_id": batch_id
            }
        
        try:
            # 尝试导入transformers
            try:
                import torch
                from transformers import (
                    AutoTokenizer, AutoModelForSequenceClassification,
                    TrainingArguments, Trainer, DataCollatorWithPadding
                )
                from datasets import Dataset
            except ImportError:
                return {
                    "success": False,
                    "error": "transformers库未安装，无法进行模型训练",
                    "batch_id": batch_id
                }
            
            logger.info(f"[ModelTrainer] 开始训练模型，数据量: {len(training_data)}")
            
            # 1. 准备数据
            questions = [item['question'] for item in training_data]
            labels = [item['intent'] for item in training_data]
            
            # 2. 加载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_name,
                cache_dir=self.model_cache_dir
            )
            
            # 获取意图类别列表
            from services.intent_service.config import INTENT_CATEGORIES
            intent_labels = list(INTENT_CATEGORIES.keys())
            num_labels = len(intent_labels)
            
            model = AutoModelForSequenceClassification.from_pretrained(
                self.base_model_name,
                num_labels=num_labels,
                cache_dir=self.model_cache_dir
            )
            
            # 3. 准备数据集
            def tokenize_function(examples):
                return tokenizer(
                    examples['question'],
                    truncation=True,
                    padding=True,
                    max_length=128
                )
            
            # 创建标签映射
            label_to_id = {label: idx for idx, label in enumerate(intent_labels)}
            id_to_label = {idx: label for label, idx in label_to_id.items()}
            
            # 转换标签
            label_ids = [label_to_id.get(label, label_to_id['general']) for label in labels]
            
            dataset_dict = {
                'question': questions,
                'label': label_ids
            }
            dataset = Dataset.from_dict(dataset_dict)
            tokenized_dataset = dataset.map(tokenize_function, batched=True)
            
            # 4. 训练参数
            model_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_dir = os.path.join(self.tuned_model_dir, model_version)
            
            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=EPOCHS,
                per_device_train_batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                save_strategy="epoch",
                logging_steps=10,
                load_best_model_at_end=False,
                report_to=None  # 不报告到wandb等
            )
            
            # 5. 训练器
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                data_collator=DataCollatorWithPadding(tokenizer=tokenizer)
            )
            
            # 6. 开始训练
            train_result = trainer.train()
            
            # 7. 保存模型
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
            
            # 8. 保存标签映射
            with open(os.path.join(output_dir, "label_mapping.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "label_to_id": label_to_id,
                    "id_to_label": id_to_label,
                    "intent_labels": intent_labels
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[ModelTrainer] 模型训练完成，保存路径: {output_dir}")
            
            return {
                "success": True,
                "batch_id": batch_id,
                "model_version": model_version,
                "model_path": output_dir,
                "training_samples": len(training_data),
                "training_loss": float(train_result.training_loss) if hasattr(train_result, 'training_loss') else None
            }
            
        except Exception as e:
            logger.error(f"[ModelTrainer] 模型训练失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id
            }
    
    def update_training_status(
        self,
        question_ids: List[int],
        batch_id: str,
        status: str = "used"
    ) -> bool:
        """
        更新问题训练状态
        
        Args:
            question_ids: 问题ID列表
            batch_id: 批次ID
            status: 状态（used/skipped）
        
        Returns:
            bool: 是否更新成功
        """
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    sql = """
                        UPDATE intent_user_questions
                        SET training_status = %s,
                            training_batch_id = %s
                        WHERE id IN (%s)
                    """ % (",".join(["%s"] * len(question_ids)))
                    
                    params = [status, batch_id] + question_ids
                    cursor.execute(sql, params)
                    conn.commit()
                    return True
            except Exception as e:
                conn.rollback()
                logger.error(f"[ModelTrainer] 更新训练状态失败: {e}", exc_info=True)
                return False
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"[ModelTrainer] 更新训练状态异常: {e}", exc_info=True)
            return False


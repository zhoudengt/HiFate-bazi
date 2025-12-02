# -*- coding: utf-8 -*-
"""
模型微调服务 REST API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from services.model_tuning_service.service import ModelTuningService
from services.model_tuning_service.keyword_extractor import KeywordRuleExtractor
from server.services.intent_question_logger import get_question_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/model-tuning", tags=["模型微调"])

# 全局服务实例
_tuning_service: Optional[ModelTuningService] = None
_keyword_extractor: Optional[KeywordRuleExtractor] = None


def get_tuning_service() -> ModelTuningService:
    """获取微调服务实例（单例）"""
    global _tuning_service
    if _tuning_service is None:
        _tuning_service = ModelTuningService()
    return _tuning_service


def get_keyword_extractor() -> KeywordRuleExtractor:
    """获取关键词提取器实例（单例）"""
    global _keyword_extractor
    if _keyword_extractor is None:
        _keyword_extractor = KeywordRuleExtractor()
    return _keyword_extractor


# ==================== 训练批次管理 ====================

class CreateTrainingBatchRequest(BaseModel):
    min_confidence: float = 0.0
    description: str = ""


@router.post("/batches", summary="创建训练批次")
async def create_training_batch(request: CreateTrainingBatchRequest):
    """创建新的训练批次"""
    try:
        service = get_tuning_service()
        result = service.create_training_batch(
            min_confidence=request.min_confidence,
            description=request.description
        )
        
        if result.get("success"):
            return {
                "success": True,
                "batch_id": result.get("batch_id")
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "创建失败"))
    except Exception as e:
        logger.error(f"创建训练批次失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class RunTrainingBatchRequest(BaseModel):
    batch_id: str
    auto_extract_keywords: bool = True


@router.post("/batches/{batch_id}/run", summary="执行训练批次")
async def run_training_batch(batch_id: str, request: RunTrainingBatchRequest):
    """执行训练批次（包括模型训练和规则扩展）"""
    try:
        service = get_tuning_service()
        result = service.run_training_batch(
            batch_id=batch_id,
            auto_extract_keywords=request.auto_extract_keywords
        )
        
        if result.get("success"):
            return {
                "success": True,
                "batch_id": result.get("batch_id"),
                "model_version": result.get("model_version"),
                "model_path": result.get("model_path"),
                "training_samples": result.get("training_samples"),
                "keyword_rules_added": result.get("keyword_rules_added", 0)
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "训练失败"))
    except Exception as e:
        logger.error(f"执行训练批次失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batches", summary="获取训练批次列表")
async def list_training_batches(
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="批次状态: pending/training/completed/failed")
):
    """获取训练批次列表"""
    try:
        from server.config.mysql_config import get_mysql_connection, return_mysql_connection
        
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                if status:
                    sql = """
                        SELECT batch_id, model_version, question_count, labeled_count,
                               training_status, created_at, training_start_time, training_end_time,
                               training_duration_sec
                        FROM intent_model_training_batches
                        WHERE training_status = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (status, limit))
                else:
                    sql = """
                        SELECT batch_id, model_version, question_count, labeled_count,
                               training_status, created_at, training_start_time, training_end_time,
                               training_duration_sec
                        FROM intent_model_training_batches
                        ORDER BY created_at DESC
                        LIMIT %s
                    """
                    cursor.execute(sql, (limit,))
                
                batches = cursor.fetchall()
                return {
                    "success": True,
                    "batches": batches,
                    "total": len(batches)
                }
        finally:
            return_mysql_connection(conn)
    except Exception as e:
        logger.error(f"获取训练批次列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 问题标注管理 ====================

@router.get("/questions/unlabeled", summary="获取未标注问题")
async def get_unlabeled_questions(
    limit: int = Query(100, ge=1, le=1000),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0)
):
    """获取未标注的问题（用于人工标注）"""
    try:
        question_logger = get_question_logger()
        questions = question_logger.get_unlabeled_questions(limit=limit, min_confidence=min_confidence)
        return {
            "success": True,
            "questions": questions,
            "total": len(questions)
        }
    except Exception as e:
        logger.error(f"获取未标注问题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class UpdateQuestionLabelRequest(BaseModel):
    question_id: int
    correct_intent: List[str]
    correct_time_intent: Optional[Dict[str, Any]] = None
    labeler_id: str = "admin"


@router.post("/questions/{question_id}/label", summary="更新问题标注")
async def update_question_label(question_id: int, request: UpdateQuestionLabelRequest):
    """更新问题标注（用于训练）"""
    try:
        question_logger = get_question_logger()
        success = question_logger.update_label(
            question_id=question_id,
            correct_intent=request.correct_intent,
            correct_time_intent=request.correct_time_intent,
            labeler_id=request.labeler_id
        )
        
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="更新标注失败")
    except Exception as e:
        logger.error(f"更新问题标注失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 关键词规则扩展 ====================

@router.post("/keywords/extract", summary="提取关键词规则")
async def extract_keyword_rules(
    min_confidence: float = Query(0.8, ge=0.0, le=1.0),
    limit: int = Query(1000, ge=1, le=10000)
):
    """从用户问题中提取高频关键词规则"""
    try:
        extractor = get_keyword_extractor()
        rules = extractor.extract_keywords_from_questions(
            min_confidence=min_confidence,
            limit=limit
        )
        
        saved_count = extractor.save_keyword_rules(rules)
        
        return {
            "success": True,
            "rules": rules,
            "total_extracted": len(rules),
            "saved_count": saved_count
        }
    except Exception as e:
        logger.error(f"提取关键词规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计信息 ====================

@router.get("/stats", summary="获取统计信息")
async def get_stats():
    """获取训练数据统计信息"""
    try:
        from server.config.mysql_config import get_mysql_connection, return_mysql_connection
        
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # 总问题数
                cursor.execute("SELECT COUNT(*) as total FROM intent_user_questions")
                total_questions = cursor.fetchone()['total']
                
                # 已标注数
                cursor.execute("SELECT COUNT(*) as total FROM intent_user_questions WHERE is_labeled = TRUE")
                labeled_count = cursor.fetchone()['total']
                
                # 未标注数
                unlabeled_count = total_questions - labeled_count
                
                # 训练批次统计
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN training_status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN training_status = 'training' THEN 1 ELSE 0 END) as training,
                        SUM(CASE WHEN training_status = 'failed' THEN 1 ELSE 0 END) as failed
                    FROM intent_model_training_batches
                """)
                batch_stats = cursor.fetchone()
                
                # 关键词规则数
                cursor.execute("SELECT COUNT(*) as total FROM intent_keyword_rules WHERE enabled = TRUE")
                keyword_rules_count = cursor.fetchone()['total']
                
                # 模型版本数
                cursor.execute("SELECT COUNT(*) as total FROM intent_model_versions")
                model_versions_count = cursor.fetchone()['total']
                
                # 激活的模型版本
                cursor.execute("SELECT version FROM intent_model_versions WHERE is_active = TRUE LIMIT 1")
                active_model = cursor.fetchone()
                
                return {
                    "success": True,
                    "questions": {
                        "total": total_questions,
                        "labeled": labeled_count,
                        "unlabeled": unlabeled_count,
                        "labeling_rate": labeled_count / total_questions if total_questions > 0 else 0
                    },
                    "training_batches": {
                        "total": batch_stats['total'],
                        "completed": batch_stats['completed'],
                        "training": batch_stats['training'],
                        "failed": batch_stats['failed']
                    },
                    "keyword_rules": {
                        "total": keyword_rules_count
                    },
                    "model_versions": {
                        "total": model_versions_count,
                        "active": active_model['version'] if active_model else None
                    }
                }
        finally:
            return_mysql_connection(conn)
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# -*- coding: utf-8 -*-
"""
面相分析V2 API接口
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List
import base64
import logging

from services.face_analysis_v2.service import FaceAnalysisService
from services.face_knowledge_v2.service import FaceKnowledgeService

router = APIRouter(prefix="/api/v2/face", tags=["面相分析V2"])
logger = logging.getLogger(__name__)

# 导入流式接口路由
try:
    from server.api.v2.face_analysis_stream import router as face_stream_router
    router.include_router(face_stream_router)
    logger.info("✅ 面相分析流式接口路由已加载")
except ImportError as e:
    logger.warning(f"⚠️  面相分析流式接口路由导入失败（可选功能）: {e}")

# 延迟初始化服务（避免启动时MediaPipe初始化失败）
face_service = None
knowledge_service = None

def get_face_service():
    """获取面相分析服务（延迟初始化）"""
    global face_service
    if face_service is None:
        face_service = FaceAnalysisService()
    return face_service

def get_knowledge_service():
    """获取知识库服务（延迟初始化）"""
    global knowledge_service
    if knowledge_service is None:
        knowledge_service = FaceKnowledgeService()
    return knowledge_service


@router.post("/analyze", summary="面相综合分析")
async def analyze_face(
    image: UploadFile = File(..., description="面相照片"),
    analysis_types: Optional[str] = Form(default="gongwei,liuqin,shishen", description="分析类型（逗号分隔）"),
    birth_year: Optional[int] = Form(default=None, description="出生年份"),
    birth_month: Optional[int] = Form(default=None, description="出生月份"),
    birth_day: Optional[int] = Form(default=None, description="出生日期"),
    birth_hour: Optional[int] = Form(default=None, description="出生时辰"),
    gender: Optional[str] = Form(default=None, description="性别")
):
    """
    面相综合分析接口
    
    - 上传人脸照片进行分析
    - 支持多种分析类型：宫位(gongwei)、六亲(liuqin)、十神(shishen)、特征(features)
    - 可选：提供八字信息进行综合分析
    """
    try:
        # 读取图片数据
        image_data = await image.read()
        
        # 准备生辰信息
        birth_info = None
        if birth_year and birth_month and birth_day:
            birth_info = {
                'year': birth_year,
                'month': birth_month,
                'day': birth_day,
                'hour': birth_hour or 12,
                'gender': gender or 'unknown'
            }
        
        # 调用分析服务
        service = get_face_service()
        result = service.analyze_face_features(
            image_data,
            image_format='jpg'
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])
        
        # 获取宫位断语
        # 注意：analyze_face_features 内部调用了 analyze_gongwei，
        # 而 analyze_gongwei 已经填充了 interpretations，所以这里不需要再次调用
        gongwei_result = result.get('gongwei', {})
        
        # 构建响应
        response_data = {
            'success': True,
            'data': {
                'face_detected': True,
                'landmarks': result.get('landmarks', {}),
                'santing_analysis': result.get('santing', {}),
                'wuyan_analysis': result.get('wuyan', {}),
                'gongwei_analysis': gongwei_result.get('gongwei_list', []),
                'liuqin_analysis': gongwei_result.get('liuqin_list', []),
                'shishen_analysis': gongwei_result.get('shishen_list', []),
                'overall_summary': result.get('overall_summary', ''),
                'birth_info': birth_info
            }
        }
        
        return JSONResponse(content=response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"面相分析错误：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)}")


@router.post("/detect", summary="仅检测关键点")
async def detect_landmarks(
    image: UploadFile = File(..., description="面相照片")
):
    """
    仅检测人脸关键点
    
    - 返回MediaPipe 468个关键点
    - 返回映射的99个面相特征点
    """
    try:
        image_data = await image.read()
        
        service = get_face_service()
        result = service.detect_landmarks(image_data, 'jpg')
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])
        
        return JSONResponse(content={
            'success': True,
            'data': {
                'landmarks_count': len(result['landmarks']),
                'mapped_features_count': len(result['mapped_features']),
                'landmarks': result['landmarks'][:20],  # 返回前20个示例
                'mapped_features': result['mapped_features'][:20],
                'face_bounds': result['face_bounds']
            }
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检测错误：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检测失败：{str(e)}")


@router.get("/rules/{rule_type}", summary="查询面相规则")
async def get_rules(
    rule_type: str,
    position: Optional[str] = None
):
    """
    查询面相规则
    
    - rule_type: gongwei/liuqin/shishen/feature/liunian
    - position: 可选，筛选特定位置的规则
    """
    try:
        knowledge = get_knowledge_service()
        rules = knowledge.query_rules(rule_type, position)
        
        return JSONResponse(content={
            'success': True,
            'data': {
                'rule_type': rule_type,
                'position': position,
                'count': len(rules),
                'rules': rules
            }
        })
    
    except Exception as e:
        logger.error(f"查询规则错误：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/health", summary="健康检查")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "face_analysis_v2"}


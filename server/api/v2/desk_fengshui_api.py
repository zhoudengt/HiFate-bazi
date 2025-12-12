# -*- coding: utf-8 -*-
"""
办公桌风水分析 API
"""

import logging
import sys
import os
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Optional
from pydantic import BaseModel

# 添加服务目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'services', 'desk_fengshui'))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/desk-fengshui", tags=["办公桌风水"])


class DeskAnalysisResponse(BaseModel):
    """办公桌风水分析响应"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/analyze", response_model=DeskAnalysisResponse, summary="分析办公桌风水")
async def analyze_desk_fengshui(
    image: UploadFile = File(..., description="办公桌照片"),
    solar_date: Optional[str] = Form(None, description="用户出生日期 YYYY-MM-DD"),
    solar_time: Optional[str] = Form(None, description="用户出生时间 HH:MM"),
    gender: Optional[str] = Form(None, description="性别 male/female"),
    use_bazi: bool = Form(True, description="是否结合八字分析")
):
    """
    分析办公桌风水布局
    
    **功能说明**：
    1. 上传办公桌照片
    2. AI识别物品和位置
    3. 匹配风水规则
    4. 为每个物品生成详细分析
    5. 结合用户八字（喜神、忌神）深度融合
    6. 提供三级建议体系
    
    **参数**：
    - **image**: 办公桌照片（必需）
    - **solar_date**: 用户出生日期（可选，格式：YYYY-MM-DD）
    - **solar_time**: 用户出生时间（可选，格式：HH:MM）
    - **gender**: 性别（可选，male/female）
    - **use_bazi**: 是否结合八字分析（默认true）
    
    **返回**：
    - **items**: 检测到的物品列表（含位置信息）
    - **item_analyses**: 每个物品的详细风水分析
      - name: 物品名称
      - label: 中文名称
      - current_position: 当前位置
      - is_position_ideal: 位置是否理想
      - analysis: 详细分析（评估、理想位置、禁忌位置、五行、八字相关性等）
      - suggestion: 调整建议（如有）
    - **recommendations**: 三级建议体系
      - must_adjust: 必须调整（违反禁忌）
      - should_add: 建议添加（基于八字喜神）
      - optional_optimize: 可选优化
    - **bazi_analysis**: 八字深度融合分析
      - xishen_analysis: 喜神分析（元素数量、状态、推荐物品/颜色）
      - jishen_analysis: 忌神分析（桌面忌神物品、建议）
      - element_balance: 桌面五行分布
      - overall_compatibility: 整体相容度评分
      - personalized_tips: 个性化建议
      - color_recommendations: 颜色推荐
    - **adjustments**: 调整建议（需要移动的物品）
    - **additions**: 增加建议（建议添加的物品）
    - **removals**: 删除建议（不宜摆放的物品）
    - **score**: 综合评分（0-100）
    - **summary**: 分析总结
    - **xishen**: 喜神（如果use_bazi=true）
    - **jishen**: 忌神（如果use_bazi=true）
    """
    try:
        logger.info(f"收到办公桌风水分析请求: {image.filename}, use_bazi={use_bazi}")
        
        # 1. 验证图片
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")
        
        # 2. 读取图片数据
        image_bytes = await image.read()
        
        # 3. 参数验证
        if use_bazi:
            if not solar_date or not solar_time or not gender:
                logger.warning("use_bazi=True 但缺少八字参数，将不使用八字分析")
                use_bazi = False
        
        # 4. 调用分析服务（异步）
        try:
            from analyzer import DeskFengshuiAnalyzer
            
            analyzer = DeskFengshuiAnalyzer()
            
            # 使用异步方法以提升并发性能
            result = await analyzer.analyze_async(
                image_bytes=image_bytes,
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender,
                use_bazi=use_bazi
            )
            
            if not result.get('success'):
                raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))
            
            logger.info(f"分析成功，评分: {result.get('score', 0)}")
            
            return DeskAnalysisResponse(
                success=True,
                data=result
            )
            
        except ImportError as e:
            logger.error(f"服务模块导入失败: {e}")
            raise HTTPException(status_code=500, detail="服务未就绪，请稍后重试")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"办公桌风水分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/rules", summary="获取风水规则列表")
async def get_fengshui_rules(
    rule_type: Optional[str] = None,
    item_name: Optional[str] = None
):
    """
    获取风水规则列表
    
    **参数**：
    - **rule_type**: 规则类型（可选）basic/element_based/taboo
    - **item_name**: 物品名称（可选）
    
    **返回**：
    规则列表
    """
    try:
        from rule_engine import DeskFengshuiEngine
        
        engine = DeskFengshuiEngine()
        rules = engine.load_rules()
        
        # 过滤规则
        if rule_type:
            rules = [r for r in rules if r.get('rule_type') == rule_type]
        
        if item_name:
            rules = [r for r in rules if r.get('item_name') == item_name]
        
        return {
            'success': True,
            'data': {
                'total': len(rules),
                'rules': rules
            }
        }
        
    except Exception as e:
        logger.error(f"获取规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取规则失败: {str(e)}")


@router.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查"""
    return {
        'status': 'healthy',
        'service': 'desk_fengshui_api',
        'version': '1.0.0'
    }


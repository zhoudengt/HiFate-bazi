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

# 定义调试日志路径（兼容本地和生产环境）
DEBUG_LOG_PATH = os.path.join(BASE_DIR, 'logs', 'debug.log')

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/desk-fengshui", tags=["办公桌风水"])

# 导入流式接口路由
try:
    from server.api.v2.desk_fengshui_stream import router as desk_stream_router
    router.include_router(desk_stream_router)
    logger.info("✅ 办公桌风水流式接口路由已加载")
except ImportError as e:
    logger.warning(f"⚠️  办公桌风水流式接口路由导入失败（可选功能）: {e}")


class DeskAnalysisResponse(BaseModel):
    """办公桌风水分析响应"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/analyze", response_model=DeskAnalysisResponse, summary="分析办公桌风水")
async def analyze_desk_fengshui(
    image: UploadFile = File(..., description="办公桌照片")
):
    """
    分析办公桌风水布局
    
    **功能说明**：
    1. 上传办公桌照片
    2. AI识别物品和位置
    3. 匹配风水规则
    4. 为每个物品生成详细分析
    5. 提供三级建议体系
    
    **参数**：
    - **image**: 办公桌照片（必需）
    
    **返回**：
    - **items**: 检测到的物品列表（含位置信息）
    - **item_analyses**: 每个物品的详细风水分析
      - name: 物品名称
      - label: 中文名称
      - current_position: 当前位置
      - is_position_ideal: 位置是否理想
      - analysis: 详细分析（评估、理想位置、禁忌位置、五行等）
      - suggestion: 调整建议（如有）
    - **recommendations**: 三级建议体系
      - must_adjust: 必须调整（违反禁忌）
      - should_add: 建议添加
      - optional_optimize: 可选优化
    - **adjustments**: 调整建议（需要移动的物品）
    - **additions**: 增加建议（建议添加的物品）
    - **removals**: 删除建议（不宜摆放的物品）
    - **score**: 综合评分（0-100）
    - **summary**: 分析总结
    """
    try:
        logger.info(f"收到办公桌风水分析请求: {image.filename}")
        
        # 1. 验证图片
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")
        
        # 2. 读取图片数据
        image_bytes = await image.read()
        
        # 3. 调用分析服务（异步，带超时）
        try:
            import asyncio
            # 确保从正确的路径导入
            import sys
            desk_fengshui_path = os.path.join(BASE_DIR, 'services', 'desk_fengshui')
            # 确保desk_fengshui路径在最前面，这样相对导入才能工作
            if desk_fengshui_path in sys.path:
                sys.path.remove(desk_fengshui_path)
            sys.path.insert(0, desk_fengshui_path)
            # 切换到desk_fengshui目录以确保相对导入工作
            old_cwd = os.getcwd()
            try:
                os.chdir(desk_fengshui_path)
                from analyzer import DeskFengshuiAnalyzer
            finally:
                os.chdir(old_cwd)
            analyzer = DeskFengshuiAnalyzer()
            
            # 使用异步方法以提升并发性能，添加总超时（90秒）
            result = await asyncio.wait_for(
                analyzer.analyze_async(
                    image_bytes=image_bytes,
                    use_bazi=False
                ),
                timeout=90.0  # 90秒总超时
            )
            
            
            
            # 🔴 防御性检查：确保 result 不为 None
            if result is None:
                logger.error("分析服务返回 None，可能是服务未就绪或内部错误")
                raise HTTPException(
                    status_code=500, 
                    detail="分析服务返回空结果，请稍后重试。如果问题持续，请联系技术支持。"
                )
            
            # 🔴 防御性检查：确保 result 是字典类型
            if not isinstance(result, dict):
                logger.error(f"分析服务返回了非字典类型: {type(result)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"分析服务返回了无效的数据类型: {type(result).__name__}"
                )
            
            # 检查分析是否成功
            if not result.get('success'):
                error_msg = result.get('error', '分析失败')
                # 🔴 防御性检查：确保 error_msg 不为 None
                if error_msg is None:
                    error_msg = '分析失败'
                logger.error(f"分析失败: {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
            
            logger.info(f"分析成功，评分: {result.get('score', 0)}")
            
            return DeskAnalysisResponse(
                success=True,
                data=result
            )
            
        except asyncio.TimeoutError:
            logger.error("分析超时（>90秒）")
            raise HTTPException(
                status_code=504,
                detail="分析超时，请稍后重试。建议：上传更小的图片"
            )
        except ImportError as e:
            logger.error(f"服务模块导入失败: {e}", exc_info=True)
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


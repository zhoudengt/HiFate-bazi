# -*- coding: utf-8 -*-
"""
面相与风水 gRPC-Web 端点处理器
"""

import base64
import json
import logging
from io import BytesIO
from typing import Any, Dict

from fastapi import HTTPException, UploadFile

from server.api.grpc_gateway.endpoints import _register
from server.api.grpc_gateway.utils import _deep_clean_for_serialization

logger = logging.getLogger(__name__)


@_register("/api/v2/face/analyze")
async def _handle_face_analysis_v2(payload: Dict[str, Any]):
    """处理面相分析V2请求（支持文件上传）"""
    from server.api.v2.face_analysis import analyze_face
    from fastapi.responses import JSONResponse

    image_base64 = payload.get("image_base64", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="缺少图片数据")
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片解码失败: {str(e)}")
    image_file = UploadFile(
        file=BytesIO(image_bytes),
        filename=payload.get("filename", "face.jpg"),
        headers={"content-type": payload.get("content_type", "image/jpeg")}
    )
    result = await analyze_face(
        image=image_file,
        analysis_types=payload.get("analysis_types", "gongwei,liuqin,shishen"),
        birth_year=payload.get("birth_year"),
        birth_month=payload.get("birth_month"),
        birth_day=payload.get("birth_day"),
        birth_hour=payload.get("birth_hour"),
        gender=payload.get("gender")
    )
    if isinstance(result, JSONResponse):
        body = result.body
        if isinstance(body, bytes):
            data = json.loads(body.decode('utf-8'))
        else:
            data = body
        return _deep_clean_for_serialization(data)
    return result


@_register("/api/v2/desk-fengshui/analyze")
async def _handle_desk_fengshui(payload: Dict[str, Any]):
    """处理办公桌风水分析请求（支持文件上传）"""
    from server.api.v2.desk_fengshui_api import analyze_desk_fengshui
    from fastapi.responses import JSONResponse

    image_base64 = payload.get("image_base64", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="缺少图片数据")
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片解码失败: {str(e)}")
    image_file = UploadFile(
        file=BytesIO(image_bytes),
        filename=payload.get("filename", "desk.jpg"),
        headers={"content-type": payload.get("content_type", "image/jpeg")}
    )
    try:
        result = await analyze_desk_fengshui(image=image_file)
        if result is None:
            logger.error("办公桌风水分析返回 None")
            return {"success": False, "error": "分析服务返回空结果，请稍后重试"}
        if isinstance(result, JSONResponse):
            body = result.body
            if isinstance(body, bytes):
                data = json.loads(body.decode('utf-8'))
            else:
                data = body
            cleaned = _deep_clean_for_serialization(data)
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (JSONResponse path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif hasattr(result, 'model_dump'):
            data = result.model_dump(exclude_none=False)
            if data is None:
                logger.error("model_dump() 返回了 None")
                return {"success": False, "error": "数据解析失败"}
            if not isinstance(data, dict):
                logger.error(f"model_dump() 返回了非字典类型: {type(data)}")
                return {"success": False, "error": "数据格式错误"}
            cleaned = _deep_clean_for_serialization(data)
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (Pydantic v2 path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif hasattr(result, 'dict'):
            data = result.dict()
            cleaned = _deep_clean_for_serialization(data)
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (Pydantic v1 path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif isinstance(result, dict):
            cleaned = _deep_clean_for_serialization(result)
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        logger.warning(f"办公桌风水分析返回了未知类型: {type(result)}")
        return {"success": False, "error": f"分析服务返回了无效的数据类型: {type(result).__name__}"}
    except Exception as e:
        logger.error(f"办公桌风水分析异常: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            error_detail = e.detail if hasattr(e, 'detail') and e.detail else str(e)
            return {"success": False, "error": f"分析失败: {error_detail}"}
        return {"success": False, "error": f"分析失败: {str(e) if e else '未知错误'}"}

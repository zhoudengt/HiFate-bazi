#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端 gRPC-Web 网关

- 接收浏览器 gRPC-Web 请求
- 解包通用 JSON 载荷
- 调用现有 FastAPI/Pydantic 处理逻辑
- 返回与原 REST 接口一致的 JSON 数据
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Tuple

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder

from server.api.v1.auth import LoginRequest, login
from server.api.v1.bazi_display import (
    BaziDisplayRequest,
    DayunDisplayRequest,
    FortuneDisplayRequest,
    LiunianDisplayRequest,
    LiuyueDisplayRequest,
    get_dayun_display,
    get_fortune_display,
    get_liunian_display,
    get_liuyue_display,
    get_pan_display,
)
from server.api.v1.wangshuai import WangShuaiRequest, calculate_wangshuai
from server.api.v1.yigua import YiGuaRequest, divinate
from server.api.v1.payment import (
    CreatePaymentSessionRequest,
    VerifyPaymentRequest,
    create_payment_session,
    verify_payment,
)
from server.api.v1.smart_fortune import smart_analyze
from server.api.v1.formula_analysis import (
    FormulaAnalysisRequest,
    analyze_formula_rules,
)
from server.api.v1.daily_fortune import (
    DailyFortuneRequest,
    get_daily_fortune,
)
from server.api.v1.monthly_fortune import (
    MonthlyFortuneRequest,
    calculate_monthly_fortune,
)
from server.api.v1.unified_payment import (
    CreatePaymentRequest,
    VerifyPaymentRequest,
    create_unified_payment,
    verify_unified_payment,
    get_payment_providers,
)
from server.api.v1.calendar_api import (
    CalendarRequest,
    query_calendar,
)
from server.api.v1.bazi import BaziInterfaceRequest, ShengongMinggongRequest, get_shengong_minggong
from server.services.bazi_interface_service import BaziInterfaceService

# 文件上传相关
import base64
from io import BytesIO
from fastapi import UploadFile, File, Form

logger = logging.getLogger(__name__)
router = APIRouter()

# 在模块加载时打印已注册的端点（调试用）
def _log_registered_endpoints():
    """在模块加载完成后打印已注册的端点"""
    import atexit
    def log_on_exit():
        if SUPPORTED_ENDPOINTS:
            logger.info(f"已注册的 gRPC 端点数量: {len(SUPPORTED_ENDPOINTS)}")
            logger.debug(f"已注册的端点列表: {list(SUPPORTED_ENDPOINTS.keys())}")
    atexit.register(log_on_exit)


GrpcResult = Tuple[Dict[str, Any], int]

# 支持的前端接口列表
SUPPORTED_ENDPOINTS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}


def _clear_endpoints():
    """清空已注册的端点（用于热更新）"""
    global SUPPORTED_ENDPOINTS
    SUPPORTED_ENDPOINTS.clear()
    logger.info("已清空 gRPC 端点注册表（热更新）")


def _reload_endpoints():
    """重新注册所有端点（用于热更新后恢复端点）"""
    global SUPPORTED_ENDPOINTS
    # 注意：由于装饰器 @_register 在模块加载时执行，
    # 当使用 importlib.reload() 重新加载模块时，装饰器会自动重新执行
    # 所以这里不需要手动重新注册，只需要确保模块被重新加载即可
    # 这个函数主要用于日志记录和验证
    endpoint_count = len(SUPPORTED_ENDPOINTS)
    logger.info(f"gRPC 端点已重新注册，当前端点数量: {endpoint_count}")
    if endpoint_count > 0:
        logger.debug(f"已注册的端点: {list(SUPPORTED_ENDPOINTS.keys())[:10]}...")
    return endpoint_count > 0


def _register(endpoint: str):
    """装饰器：注册 endpoint -> handler"""

    def decorator(func: Callable[[Dict[str, Any]], Any]):
        SUPPORTED_ENDPOINTS[endpoint] = func
        logger.debug(f"注册 gRPC 端点: {endpoint}")
        return func

    return decorator


@_register("/bazi/pan/display")
async def _handle_pan(payload: Dict[str, Any]):
    request_model = BaziDisplayRequest(**payload)
    return await get_pan_display(request_model)


@_register("/bazi/fortune/display")
async def _handle_fortune(payload: Dict[str, Any]):
    request_model = FortuneDisplayRequest(**payload)
    return await get_fortune_display(request_model)


@_register("/bazi/dayun/display")
async def _handle_dayun(payload: Dict[str, Any]):
    request_model = DayunDisplayRequest(**payload)
    return await get_dayun_display(request_model)


@_register("/bazi/liunian/display")
async def _handle_liunian(payload: Dict[str, Any]):
    request_model = LiunianDisplayRequest(**payload)
    return await get_liunian_display(request_model)


@_register("/bazi/liuyue/display")
async def _handle_liuyue(payload: Dict[str, Any]):
    request_model = LiuyueDisplayRequest(**payload)
    return await get_liuyue_display(request_model)


@_register("/bazi/wangshuai")
async def _handle_wangshuai(payload: Dict[str, Any]):
    request_model = WangShuaiRequest(**payload)
    return await calculate_wangshuai(request_model)


@_register("/bazi/yigua/divinate")
async def _handle_yigua(payload: Dict[str, Any]):
    request_model = YiGuaRequest(**payload)
    return await divinate(request_model)


@_register("/auth/login")
async def _handle_login(payload: Dict[str, Any]):
    request_model = LoginRequest(**payload)
    return await login(request_model)


@_register("/payment/create-session")
async def _handle_payment_create(payload: Dict[str, Any]):
    request_model = CreatePaymentSessionRequest(**payload)
    return create_payment_session(request_model)


@_register("/payment/verify")
async def _handle_payment_verify(payload: Dict[str, Any]):
    request_model = VerifyPaymentRequest(**payload)
    return verify_payment(request_model)


@_register("/smart-analyze")
async def _handle_smart_analyze(payload: Dict[str, Any]):
    """处理智能分析请求（将 POST body 转换为 GET query 参数格式）"""
    # smart_analyze 是 GET 接口，需要将 payload 转换为函数参数
    question = payload.get("question", "")
    year = payload.get("year", 0)
    month = payload.get("month", 1)
    day = payload.get("day", 1)
    hour = payload.get("hour", 12)
    gender = payload.get("gender", "male")
    user_id = payload.get("user_id")
    include_fortune_context = payload.get("include_fortune_context", False)
    
    # 调用原函数（需要手动传递参数，因为它是 GET 接口）
    return await smart_analyze(
        question=question,
        year=year,
        month=month,
        day=day,
        hour=hour,
        gender=gender,
        user_id=user_id,
        include_fortune_context=include_fortune_context
    )


@_register("/bazi/formula-analysis")
async def _handle_formula_analysis(payload: Dict[str, Any]):
    """处理算法公式分析请求"""
    request_model = FormulaAnalysisRequest(**payload)
    return await analyze_formula_rules(request_model)


@_register("/bazi/daily-fortune")
async def _handle_daily_fortune(payload: Dict[str, Any]):
    """处理今日运势分析请求"""
    request_model = DailyFortuneRequest(**payload)
    return await get_daily_fortune(request_model)


@_register("/bazi/monthly-fortune")
async def _handle_monthly_fortune(payload: Dict[str, Any]):
    """处理当月运势分析请求"""
    request_model = MonthlyFortuneRequest(**payload)
    return await calculate_monthly_fortune(request_model)


@_register("/bazi/interface")
async def _handle_bazi_interface(payload: Dict[str, Any]):
    """处理八字界面信息请求（包含命宫、身宫、胎元、胎息、命卦等）"""
    import asyncio
    request_model = BaziInterfaceRequest(**payload)
    
    # 在线程池中执行CPU密集型计算
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # 使用默认线程池
        BaziInterfaceService.generate_interface_full,
        request_model.solar_date,
        request_model.solar_time,
        request_model.gender,
        request_model.name or "",
        request_model.location or "未知地",
        request_model.latitude or 39.00,
        request_model.longitude or 120.00
    )
    
    # 返回格式与 REST API 一致
    return {
        "success": True,
        "data": result
    }


@_register("/bazi/shengong-minggong")
async def _handle_shengong_minggong(payload: Dict[str, Any]):
    """处理身宫命宫详细信息请求"""
    from fastapi import Request
    from unittest.mock import MagicMock
    
    request_model = ShengongMinggongRequest(**payload)
    # 创建一个模拟的Request对象（gRPC网关不需要真实的Request）
    mock_request = MagicMock(spec=Request)
    result = await get_shengong_minggong(request_model, mock_request)
    
    # 处理 BaziResponse 对象
    if hasattr(result, 'model_dump'):
        return result.model_dump()
    elif hasattr(result, 'dict'):
        return result.dict()
    return result


@_register("/payment/unified/create")
async def _handle_unified_payment_create(payload: Dict[str, Any]):
    """处理统一支付创建请求"""
    request_model = CreatePaymentRequest(**payload)
    return create_unified_payment(request_model)


@_register("/payment/unified/verify")
async def _handle_unified_payment_verify(payload: Dict[str, Any]):
    """处理统一支付验证请求"""
    request_model = VerifyPaymentRequest(**payload)
    return verify_unified_payment(request_model)


@_register("/payment/providers")
async def _handle_payment_providers(payload: Dict[str, Any]):
    """处理获取支付渠道列表请求（GET 转 POST）"""
    # payment/providers 是 GET 接口，但 gRPC-Web 只支持 POST
    # 这里忽略 payload，直接调用原函数
    return get_payment_providers()


@_register("/calendar/query")
async def _handle_calendar_query(payload: Dict[str, Any]):
    """处理万年历查询请求"""
    request_model = CalendarRequest(**payload)
    return await query_calendar(request_model)


@_register("/api/v2/face/analyze")
async def _handle_face_analysis_v2(payload: Dict[str, Any]):
    """处理面相分析V2请求（支持文件上传）"""
    from server.api.v2.face_analysis import analyze_face
    from fastapi.responses import JSONResponse
    
    # 处理 base64 编码的图片
    image_base64 = payload.get("image_base64", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="缺少图片数据")
    
    # 解码 base64
    try:
        # 移除 data:image/xxx;base64, 前缀（如果有）
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片解码失败: {str(e)}")
    
    # 创建 UploadFile 对象
    image_file = UploadFile(
        file=BytesIO(image_bytes),
        filename=payload.get("filename", "face.jpg"),
        headers={"content-type": payload.get("content_type", "image/jpeg")}
    )
    
    # 调用原始接口
    result = await analyze_face(
        image=image_file,
        analysis_types=payload.get("analysis_types", "gongwei,liuqin,shishen"),
        birth_year=payload.get("birth_year"),
        birth_month=payload.get("birth_month"),
        birth_day=payload.get("birth_day"),
        birth_hour=payload.get("birth_hour"),
        gender=payload.get("gender")
    )
    
    # JSONResponse 对象需要提取 body 内容
    if isinstance(result, JSONResponse):
        body = result.body
        if isinstance(body, bytes):
            data = json.loads(body.decode('utf-8'))
        else:
            data = body
        # 深度清理，确保可以序列化（修复 Maximum call stack exceeded）
        return _deep_clean_for_serialization(data)
    
    return result


@_register("/api/v2/desk-fengshui/analyze")
async def _handle_desk_fengshui(payload: Dict[str, Any]):
    """处理办公桌风水分析请求（支持文件上传）"""
    # #region agent log
    import json as json_lib
    with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "grpc_gateway.py:339", "message": "_handle_desk_fengshui entry", "data": {"has_image_base64": bool(payload.get("image_base64")), "use_bazi": payload.get("use_bazi")}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
    # #endregion
    from server.api.v2.desk_fengshui_api import analyze_desk_fengshui
    from fastapi.responses import JSONResponse
    
    # 处理 base64 编码的图片
    image_base64 = payload.get("image_base64", "")
    if not image_base64:
        raise HTTPException(status_code=400, detail="缺少图片数据")
    
    # 解码 base64
    try:
        # 移除 data:image/xxx;base64, 前缀（如果有）
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片解码失败: {str(e)}")
    
    # 创建 UploadFile 对象
    image_file = UploadFile(
        file=BytesIO(image_bytes),
        filename=payload.get("filename", "desk.jpg"),
        headers={"content-type": payload.get("content_type", "image/jpeg")}
    )
    
    # 调用原始接口
    try:
        # #region agent log
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "B", "location": "grpc_gateway.py:367", "message": "before analyze_desk_fengshui call", "data": {"image_size": len(image_bytes), "solar_date": payload.get("solar_date"), "use_bazi": payload.get("use_bazi")}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        result = await analyze_desk_fengshui(
            image=image_file,
            solar_date=payload.get("solar_date"),
            solar_time=payload.get("solar_time"),
            gender=payload.get("gender"),
            use_bazi=payload.get("use_bazi", True)
        )
        
        # #region agent log
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C", "location": "grpc_gateway.py:376", "message": "after analyze_desk_fengshui call", "data": {"result_is_none": result is None, "result_type": str(type(result)), "has_success": hasattr(result, 'success') if result else False, "is_dict": isinstance(result, dict) if result else False}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        
        # 🔴 防御性检查：确保 result 不为 None
        if result is None:
            logger.error("办公桌风水分析返回 None")
            # #region agent log
            with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
                f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "grpc_gateway.py:378", "message": "result is None - returning error", "data": {}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
            # #endregion
            return {"success": False, "error": "分析服务返回空结果，请稍后重试"}
        
        # JSONResponse 对象需要提取 body 内容
        if isinstance(result, JSONResponse):
            body = result.body
            if isinstance(body, bytes):
                data = json.loads(body.decode('utf-8'))
            else:
                data = body
            # #region agent log
            with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
                f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "grpc_gateway.py:388", "message": "JSONResponse path", "data": {"data_type": str(type(data)), "data_is_none": data is None}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
            # #endregion
            # 深度清理，确保可以序列化（修复 Maximum call stack exceeded）
            cleaned = _deep_clean_for_serialization(data)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (JSONResponse path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif hasattr(result, 'model_dump'):
            # Pydantic v2 模型
            data = result.model_dump()
            
            # 🔴 防御性检查：确保 data 不为 None
            if data is None:
                logger.error("model_dump() 返回了 None")
                return {"success": False, "error": "数据解析失败"}
            
            # 🔴 防御性检查：确保 data 是字典类型
            if not isinstance(data, dict):
                logger.error(f"model_dump() 返回了非字典类型: {type(data)}")
                return {"success": False, "error": "数据格式错误"}
            
            # #region agent log
            import json as json_lib
            with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
                f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "grpc_gateway.py:393", "message": "Pydantic v2 path", "data": {"data_type": str(type(data)), "data_is_none": data is None, "has_data_key": 'data' in data if data else False}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
            # #endregion
            
            # 深度清理，确保可以序列化
            cleaned = _deep_clean_for_serialization(data)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (Pydantic v2 path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif hasattr(result, 'dict'):
            # Pydantic v1 模型
            data = result.dict()
            # #region agent log
            with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
                f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "grpc_gateway.py:398", "message": "Pydantic v1 path", "data": {"data_type": str(type(data)), "data_is_none": data is None}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
            # #endregion
            # 深度清理，确保可以序列化
            cleaned = _deep_clean_for_serialization(data)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None (Pydantic v1 path)")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        elif isinstance(result, dict):
            # 普通字典，直接返回
            # #region agent log
            with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
                f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "grpc_gateway.py:402", "message": "dict path", "data": {"result_keys": list(result.keys()) if result else [], "has_success": "success" in result if result else False}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
            # #endregion
            cleaned = _deep_clean_for_serialization(result)
            # 🔴 防御性检查：确保 cleaned 不为 None
            if cleaned is None:
                logger.error("_deep_clean_for_serialization 返回了 None")
                return {"success": False, "error": "数据清理失败"}
            return cleaned
        
        # 未知类型，尝试转换
        logger.warning(f"办公桌风水分析返回了未知类型: {type(result)}")
        # #region agent log
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "grpc_gateway.py:407", "message": "unknown result type", "data": {"result_type": str(type(result))}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        return {"success": False, "error": f"分析服务返回了无效的数据类型: {type(result).__name__}"}
        
    except Exception as e:
        logger.error(f"办公桌风水分析异常: {e}", exc_info=True)
        # #region agent log
        import json as json_lib
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "D", "location": "grpc_gateway.py:410", "message": "exception caught", "data": {"error_type": str(type(e)), "error_msg": str(e)}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        
        # 🔴 修复：正确处理 HTTPException，提取 detail 字段
        if isinstance(e, HTTPException):
            error_detail = e.detail if hasattr(e, 'detail') and e.detail else str(e)
            return {"success": False, "error": f"分析失败: {error_detail}"}
        else:
            error_msg = str(e) if e else "未知错误"
            return {"success": False, "error": f"分析失败: {error_msg}"}


def _deep_clean_for_serialization(obj: Any, visited: set = None) -> Any:
    """深度清理对象，确保可以 JSON 序列化
    
    递归清理字典、列表和对象，将无法序列化的类型转换为字符串。
    用于修复面相分析V2和办公桌风水的 Maximum call stack exceeded 错误。
    
    Args:
        obj: 要清理的对象
        visited: 已访问对象的ID集合，用于检测循环引用
    """
    if visited is None:
        visited = set()
    
    # 🔴 防御性检查：如果 obj 是 None，直接返回 None
    if obj is None:
        return None
    
    # 检测循环引用
    obj_id = id(obj)
    if obj_id in visited:
        return "[循环引用]"
    visited.add(obj_id)
    
    try:
        if isinstance(obj, dict):
            return {k: _deep_clean_for_serialization(v, visited) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_deep_clean_for_serialization(item, visited) for item in obj]
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif hasattr(obj, '__dict__'):
            # 对象，转换为字典
            return _deep_clean_for_serialization(obj.__dict__, visited)
        else:
            # 其他类型（如 numpy 数组、PIL 图片等），转换为字符串
            return str(obj)
    finally:
        visited.discard(obj_id)


def _grpc_cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": (
            "content-type,x-grpc-web,x-user-agent,grpc-timeout,authorization"
        ),
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Expose-Headers": "grpc-status,grpc-message",
    }


@router.options("/grpc-web/{path:path}")
async def grpc_web_options(path: str):
    """处理 gRPC-Web 预检请求"""
    return Response(status_code=204, headers=_grpc_cors_headers())


@router.post("/grpc-web/frontend.gateway.FrontendGateway/Call")
async def grpc_web_gateway(request: Request):
    """
    gRPC-Web 入口：
    - 解包 gRPC-Web 帧
    - 解析 protobuf payload（手写解析器，避免运行时生成代码）
    - 调度到已有业务 handler
    - 将响应再编码为 gRPC-Web 帧
    """
    # #region agent log
    import json as json_lib
    import time as time_module
    try:
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C,D,E", "location": "grpc_gateway.py:508", "message": "grpc_web_gateway entry", "data": {"method": request.method, "url": str(request.url)}, "timestamp": int(time_module.time() * 1000)}) + '\n')
    except Exception as log_err:
        logger.error(f"日志写入失败: {log_err}")
    # #endregion
    raw_body = await request.body()

    try:
        message_bytes = _extract_grpc_web_message(raw_body)
        frontend_request = _decode_frontend_request(message_bytes)
    except ValueError as exc:
        logger.error("gRPC-Web 请求解析失败: %s", exc, exc_info=True)
        return _build_error_response(str(exc), http_status=400, grpc_status=3)
    except Exception as exc:
        logger.error("gRPC-Web 请求解析异常: %s", exc, exc_info=True)
        return _build_error_response(f"请求解析异常: {str(exc)}", http_status=500, grpc_status=13)

    endpoint = frontend_request["endpoint"]
    payload_json = frontend_request["payload_json"]

    try:
        payload = json.loads(payload_json) if payload_json else {}
    except json.JSONDecodeError as exc:
        error_msg = f"payload_json 解析失败: {exc}"
        logger.warning(error_msg)
        return _build_error_response(error_msg, http_status=400, grpc_status=3)

    handler = SUPPORTED_ENDPOINTS.get(endpoint)
    if not handler:
        # 调试信息：列出所有已注册的端点
        available_endpoints = list(SUPPORTED_ENDPOINTS.keys())
        logger.warning(f"未找到端点: {endpoint}, 已注册的端点: {available_endpoints}")
        error_msg = f"Unsupported endpoint: {endpoint}. Available endpoints: {', '.join(available_endpoints[:10])}"
        return _build_error_response(error_msg, http_status=404, grpc_status=12)

    # #region agent log
    import json as json_lib
    with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C,D", "location": "grpc_gateway.py:546", "message": "before handler call", "data": {"endpoint": endpoint, "has_handler": handler is not None, "payload_keys": list(payload.keys()) if isinstance(payload, dict) else []}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
    # #endregion

    try:
        result = await handler(payload)
        
        # #region agent log
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C", "location": "grpc_gateway.py:550", "message": "after handler call", "data": {"result_is_none": result is None, "result_type": str(type(result)) if result else "None", "is_dict": isinstance(result, dict) if result else False}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        
        # 🔴 防御性检查：确保 result 不为 None
        if result is None:
            logger.error(f"Handler 返回了 None，endpoint: {endpoint}")
            # #region agent log
            with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
                f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "grpc_gateway.py:562", "message": "result is None from handler", "data": {"endpoint": endpoint}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
            # #endregion
            data = {"detail": "服务返回空结果，请稍后重试"}
            status_code = 500
        else:
            # 如果 handler 已经处理了 JSONResponse，result 应该是字典
            # 但为了安全，仍然检查 JSONResponse 对象
            from fastapi.responses import JSONResponse
            if isinstance(result, JSONResponse):
                body = result.body
                if isinstance(body, bytes):
                    data = json.loads(body.decode('utf-8'))
                else:
                    data = body
                # 🔴 防御性检查：确保 data 不为 None
                if data is None:
                    logger.error("JSONResponse body 解析后为 None")
                    data = {"error": "响应解析失败", "detail": "JSONResponse body 为空"}
            else:
                # 处理 Pydantic 模型和普通字典
                try:
                    # 检查是否为 Pydantic BaseModel
                    if hasattr(result, 'model_dump'):
                        # Pydantic v2
                        data = result.model_dump()
                        # 🔴 防御性检查：确保 model_dump 返回值不为 None
                        if data is None:
                            logger.error("Pydantic v2 model_dump 返回了 None")
                            data = {"error": "数据解析失败", "detail": "model_dump 返回空结果"}
                    elif hasattr(result, 'dict'):
                        # Pydantic v1
                        data = result.dict()
                        # 🔴 防御性检查：确保 dict() 返回值不为 None
                        if data is None:
                            logger.error("Pydantic v1 dict() 返回了 None")
                            data = {"error": "数据解析失败", "detail": "dict() 返回空结果"}
                    else:
                        # 普通对象，尝试 JSON 序列化
                        json_str = json.dumps(result, default=str, ensure_ascii=False)
                        data = json.loads(json_str)
                        # 🔴 防御性检查：确保 json.loads 返回值不为 None
                        if data is None:
                            logger.error("json.loads 返回了 None")
                            data = {"error": "数据解析失败", "detail": "JSON 解析返回空结果"}
                except (RecursionError, ValueError, TypeError) as json_err:
                    logger.error(f"JSON 序列化失败（可能是循环引用或数据过大）: {json_err}", exc_info=True)
                    # 降级方案：使用 jsonable_encoder
                    try:
                        data = jsonable_encoder(result)
                        # 🔴 防御性检查：确保 jsonable_encoder 返回值不为 None
                        if data is None:
                            logger.error("jsonable_encoder 返回了 None")
                            data = {"error": "数据序列化失败", "detail": "jsonable_encoder 返回空结果"}
                    except Exception as encoder_err:
                        logger.error(f"jsonable_encoder 也失败: {encoder_err}", exc_info=True)
                        data = {"error": "数据序列化失败", "detail": str(json_err)}
            
            # 🔴 防御性检查：确保 data 在 try 块中被设置
            if 'data' not in locals() or data is None:
                logger.error("data 变量未初始化或为 None")
                data = {"error": "数据处理失败", "detail": "数据变量未正确初始化"}
                status_code = 500
            else:
                status_code = 200
    except HTTPException as exc:
        status_code = exc.status_code
        data = {"detail": exc.detail}
    except Exception as exc:  # noqa: BLE001
        logger.exception("gRPC-Web handler 执行失败 (%s): %s", endpoint, exc)
        status_code = 500
        data = {"detail": f"Internal error: {exc}"}

    # #region agent log
    import json as json_lib
    with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C,E", "location": "grpc_gateway.py:545", "message": "before data None check", "data": {"data_is_none": data is None, "data_type": str(type(data)) if data else "None", "endpoint": endpoint, "status_code": status_code}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
    # #endregion

    # 🔴 防御性检查：确保 data 不为 None
    if data is None:
        logger.error(f"gRPC-Web handler 返回了 None，endpoint: {endpoint}")
        # #region agent log
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "grpc_gateway.py:550", "message": "data is None - setting default", "data": {"endpoint": endpoint}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        data = {"detail": "服务返回空结果，请稍后重试"}
        status_code = 500
    
    # 🔴 防御性检查：确保 data 是字典类型
    if not isinstance(data, dict):
        logger.error(f"gRPC-Web handler 返回了非字典类型: {type(data)}, endpoint: {endpoint}")
        # #region agent log
        with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
            f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "grpc_gateway.py:557", "message": "data is not dict - converting", "data": {"data_type": str(type(data)), "endpoint": endpoint}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
        # #endregion
        data = {"detail": f"服务返回了无效的数据类型: {type(data).__name__}"}
        status_code = 500
    
    # #region agent log
    with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C,E", "location": "grpc_gateway.py:562", "message": "before building response", "data": {"data_keys": list(data.keys()) if isinstance(data, dict) else [], "has_detail": "detail" in data if isinstance(data, dict) else False, "status_code": status_code}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
    # #endregion
    
    # 🔴 最终防御性检查：确保 data 是字典且不为 None（双重保险）
    if not isinstance(data, dict) or data is None:
        logger.error(f"最终检查：data 不是有效字典，endpoint: {endpoint}, type: {type(data)}")
        data = {"detail": "服务返回了无效的数据"}
        status_code = 500
    
    success = 200 <= status_code < 300
    # 🔴 安全获取 detail：确保 data 是字典
    detail_value = data.get("detail", "") if isinstance(data, dict) else "未知错误"
    
    response_payload = _encode_frontend_response(
        success=success,
        data_json=json.dumps(data, ensure_ascii=False) if data is not None else "",
        error="" if success else str(detail_value),
        status_code=status_code,
    )

    grpc_status = 0 if success else _map_http_to_grpc_status(status_code)
    grpc_message = "" if success else str(detail_value)
    # #region agent log
    with open('/Users/zhoudt/Downloads/project/HiFate-bazi/.cursor/debug.log', 'a') as f:
        f.write(json_lib.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "grpc_gateway.py:572", "message": "response built", "data": {"success": success, "grpc_status": grpc_status, "has_grpc_message": bool(grpc_message)}, "timestamp": int(__import__('time').time() * 1000)}) + '\n')
    # #endregion
    return _build_grpc_web_response(response_payload, grpc_status, grpc_message)


def _map_http_to_grpc_status(status_code: int) -> int:
    mapping = {
        400: 3,  # INVALID_ARGUMENT
        401: 16,  # UNAUTHENTICATED
        403: 7,  # PERMISSION_DENIED
        404: 12,  # UNIMPLEMENTED
        422: 3,
    }
    return mapping.get(status_code, 13)  # INTERNAL


def _extract_grpc_web_message(body: bytes) -> bytes:
    """解析 gRPC-Web 帧，返回第一帧的 payload"""
    if len(body) < 5:
        raise ValueError("gRPC-Web 帧长度不足")

    flag = body[0]
    if flag & 0x80:
        raise ValueError("首帧不应为 trailer")

    length = int.from_bytes(body[1:5], byteorder="big")
    payload = body[5 : 5 + length]
    if len(payload) != length:
        raise ValueError("gRPC-Web payload 长度不匹配")

    return payload


def _decode_frontend_request(message: bytes) -> Dict[str, str]:
    """手动解析 FrontendJsonRequest"""
    endpoint = ""
    payload_json = ""
    auth_token = ""

    idx = 0
    length = len(message)

    while idx < length:
        key = message[idx]
        idx += 1
        field_number = key >> 3
        wire_type = key & 0x07

        if wire_type == 2:  # length-delimited
            str_len, idx = _read_varint(message, idx)
            value_bytes = message[idx : idx + str_len]
            idx += str_len
            value = value_bytes.decode("utf-8")

            if field_number == 1:
                endpoint = value
            elif field_number == 2:
                payload_json = value
            elif field_number == 3:
                auth_token = value
        else:
            raise ValueError(f"不支持的 wire_type: {wire_type}")

    return {"endpoint": endpoint, "payload_json": payload_json, "auth_token": auth_token}


def _encode_frontend_response(
    *, success: bool, data_json: str, error: str, status_code: int
) -> bytes:
    """手动编码 FrontendJsonResponse"""
    buffer = bytearray()

    # bool success = 1;
    buffer.extend(_write_varint((1 << 3) | 0))
    buffer.extend(_write_varint(1 if success else 0))

    # string data_json = 2;
    if data_json:
        data_bytes = data_json.encode("utf-8")
        buffer.extend(_write_varint((2 << 3) | 2))
        buffer.extend(_write_varint(len(data_bytes)))
        buffer.extend(data_bytes)

    # string error = 3;
    if error:
        error_bytes = error.encode("utf-8")
        buffer.extend(_write_varint((3 << 3) | 2))
        buffer.extend(_write_varint(len(error_bytes)))
        buffer.extend(error_bytes)

    # int32 status_code = 4;
    buffer.extend(_write_varint((4 << 3) | 0))
    buffer.extend(_write_varint(status_code))

    return bytes(buffer)


def _build_grpc_web_response(message: bytes, grpc_status: int, grpc_message: str) -> Response:
    data_frame = _wrap_frame(0x00, message)
    
    # 修复：grpc-message 在 trailer 中需要使用 URL 编码来支持非 ASCII 字符
    # 根据 gRPC-Web 规范，grpc-message 应该使用 URL 编码
    import urllib.parse
    encoded_message = urllib.parse.quote(grpc_message, safe='')
    
    # trailer payload 使用 ASCII 编码（因为已经 URL 编码了）
    trailer_payload = f"grpc-status:{grpc_status}\r\ngrpc-message:{encoded_message}\r\n".encode(
        "ascii", errors="ignore"
    )
    trailer_frame = _wrap_frame(0x80, trailer_payload)
    body = data_frame + trailer_frame

    headers = {
        **_grpc_cors_headers(),
        "grpc-status": str(grpc_status),
        # HTTP header 中的 grpc-message 也需要 URL 编码
        "grpc-message": encoded_message,
        "Content-Type": "application/grpc-web+proto",
    }

    return Response(content=body, media_type="application/grpc-web+proto", headers=headers)


def _build_error_response(message: str, http_status: int, grpc_status: int) -> Response:
    payload = _encode_frontend_response(
        success=False,
        data_json=json.dumps({"detail": message}, ensure_ascii=False),
        error=message,
        status_code=http_status,
    )
    return _build_grpc_web_response(payload, grpc_status, message)


def _wrap_frame(flag: int, payload: bytes) -> bytes:
    header = bytes([flag]) + len(payload).to_bytes(4, byteorder="big")
    return header + payload


def _read_varint(data: bytes, idx: int) -> Tuple[int, int]:
    """读取 protobuf varint"""
    shift = 0
    result = 0

    while idx < len(data):
        byte = data[idx]
        idx += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, idx
        shift += 7

    raise ValueError("varint 解析失败")


def _write_varint(value: int) -> bytes:
    """写 protobuf varint"""
    buffer = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            buffer.append(to_write | 0x80)
        else:
            buffer.append(to_write)
            break
    return bytes(buffer)




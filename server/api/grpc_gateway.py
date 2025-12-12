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

# 文件上传相关
import base64
from io import BytesIO
from fastapi import UploadFile, File, Form

logger = logging.getLogger(__name__)
router = APIRouter()


GrpcResult = Tuple[Dict[str, Any], int]

# 支持的前端接口列表
SUPPORTED_ENDPOINTS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}


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
    result = await analyze_desk_fengshui(
        image=image_file,
        solar_date=payload.get("solar_date"),
        solar_time=payload.get("solar_time"),
        gender=payload.get("gender"),
        use_bazi=payload.get("use_bazi", True)
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
    elif hasattr(result, 'model_dump'):
        # Pydantic v2 模型
        data = result.model_dump()
        # 深度清理，确保可以序列化
        return _deep_clean_for_serialization(data)
    elif hasattr(result, 'dict'):
        # Pydantic v1 模型
        data = result.dict()
        # 深度清理，确保可以序列化
        return _deep_clean_for_serialization(data)
    
    return result


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
        elif isinstance(obj, (str, int, float, bool, type(None))):
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
        error_msg = f"Unsupported endpoint: {endpoint}"
        return _build_error_response(error_msg, http_status=404, grpc_status=12)

    try:
        result = await handler(payload)
        
        # 如果 handler 已经处理了 JSONResponse，result 应该是字典
        # 但为了安全，仍然检查 JSONResponse 对象
        from fastapi.responses import JSONResponse
        if isinstance(result, JSONResponse):
            body = result.body
            if isinstance(body, bytes):
                data = json.loads(body.decode('utf-8'))
            else:
                data = body
        else:
            # 处理 Pydantic 模型和普通字典
            try:
                # 检查是否为 Pydantic BaseModel
                if hasattr(result, 'model_dump'):
                    # Pydantic v2
                    data = result.model_dump()
                elif hasattr(result, 'dict'):
                    # Pydantic v1
                    data = result.dict()
                else:
                    # 普通对象，尝试 JSON 序列化
                    json_str = json.dumps(result, default=str, ensure_ascii=False)
                    data = json.loads(json_str)
            except (RecursionError, ValueError, TypeError) as json_err:
                logger.error(f"JSON 序列化失败（可能是循环引用或数据过大）: {json_err}", exc_info=True)
                # 降级方案：使用 jsonable_encoder
                try:
                    data = jsonable_encoder(result)
                except Exception as encoder_err:
                    logger.error(f"jsonable_encoder 也失败: {encoder_err}", exc_info=True)
                    data = {"error": "数据序列化失败", "detail": str(json_err)}
        
        status_code = 200
    except HTTPException as exc:
        status_code = exc.status_code
        data = {"detail": exc.detail}
    except Exception as exc:  # noqa: BLE001
        logger.exception("gRPC-Web handler 执行失败 (%s): %s", endpoint, exc)
        status_code = 500
        data = {"detail": f"Internal error: {exc}"}

    success = 200 <= status_code < 300
    response_payload = _encode_frontend_response(
        success=success,
        data_json=json.dumps(data, ensure_ascii=False) if data is not None else "",
        error="" if success else str(data.get("detail", "")),
        status_code=status_code,
    )

    grpc_status = 0 if success else _map_http_to_grpc_status(status_code)
    grpc_message = "" if success else str(data.get("detail", ""))
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
    trailer_payload = f"grpc-status:{grpc_status}\r\ngrpc-message:{grpc_message}\r\n".encode(
        "ascii", errors="ignore"
    )
    trailer_frame = _wrap_frame(0x80, trailer_payload)
    body = data_frame + trailer_frame

    headers = {
        **_grpc_cors_headers(),
        "grpc-status": str(grpc_status),
        "grpc-message": grpc_message,
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




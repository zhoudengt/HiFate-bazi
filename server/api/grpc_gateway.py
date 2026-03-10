#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端 gRPC-Web 网关

- 接收浏览器 gRPC-Web 请求
- 解包通用 JSON 载荷
- 调用现有 FastAPI/Pydantic 处理逻辑
- 返回与原 REST 接口一致的 JSON 数据

模块化结构：
- server/api/grpc_gateway/protocol/   - 协议编解码
- server/api/grpc_gateway/endpoints.py - 端点注册表与 @_register 装饰器
- server/api/grpc_gateway/utils/       - 流式收集、序列化工具
- server/api/grpc_gateway/handlers/    - 各类处理器（8 个模块）
- server/api/grpc_gateway/recovery.py  - 热更新恢复 / 动态注册

此文件保留：路由入口、handler 模块 import 触发注册、响应序列化。
"""

from __future__ import annotations

import json
from json import JSONDecodeError
import logging
from typing import Any, Dict, Tuple

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder

from server.api.grpc_gateway.endpoints import SUPPORTED_ENDPOINTS, _register  # noqa: F401
from server.api.grpc_gateway.protocol import (
    extract_grpc_web_message,
    decode_frontend_request,
    encode_frontend_response,
    build_grpc_web_response,
    build_error_response,
    map_http_to_grpc_status,
    grpc_cors_headers,
)
from server.api.grpc_gateway.recovery import (
    _reload_endpoints,
    _ensure_endpoints_registered,
    _try_dynamic_register,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 加载 handler 模块以触发 @_register 注册
# ---------------------------------------------------------------------------
_handler_modules = [
    "server.api.grpc_gateway.handlers.payment_handlers",
    "server.api.grpc_gateway.handlers.homepage_handlers",
    "server.api.grpc_gateway.handlers.calendar_handlers",
    "server.api.grpc_gateway.handlers.smart_handlers",
    "server.api.grpc_gateway.handlers.media_handlers",
    "server.api.grpc_gateway.handlers.admin_handlers",
    "server.api.grpc_gateway.handlers.bazi_handlers",
    "server.api.grpc_gateway.handlers.stream_handlers",
]

for _module_name in _handler_modules:
    try:
        __import__(_module_name)
        logger.debug(f"✅ 加载 handler: {_module_name}")
    except Exception as e:
        logger.critical(f"🚨🚨 加载 handler 失败: {_module_name}, 错误: {e}", exc_info=True)

logger.info(f"✅ Handler 加载完成，当前端点数: {len(SUPPORTED_ENDPOINTS)}")

# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------
GrpcResult = Tuple[Dict[str, Any], int]


# ---------------------------------------------------------------------------
# 端点管理（供热更新模块调用）
# ---------------------------------------------------------------------------

def _clear_endpoints():
    """清空已注册的端点（用于热更新）"""
    SUPPORTED_ENDPOINTS.clear()
    logger.info("已清空 gRPC 端点注册表（热更新）")


# ---------------------------------------------------------------------------
# payload_json 容错解析
# ---------------------------------------------------------------------------

def _parse_payload_json(payload_json: str) -> Dict[str, Any]:
    """
    容错解析 payload_json，兼容：
    1. 尾部多余字符（Extra data）：提取第一个完整 JSON 对象
    2. 双编码 JSON：外层为字符串时再解析一次
    3. 确保返回 dict，供 handler 使用
    """
    if not payload_json or not isinstance(payload_json, str):
        return {}
    s = payload_json.strip()
    if not s:
        return {}

    payload: Any = None
    try:
        payload = json.loads(s)
    except JSONDecodeError as exc:
        if "Extra data" in str(exc):
            # 提取第一个完整 JSON 对象（兼容前端 payload 尾部多余字符）
            start = s.find("{")
            if start >= 0:
                depth = 0
                in_str = False
                escape = False
                q = None
                for i in range(start, len(s)):
                    c = s[i]
                    if escape:
                        escape = False
                        continue
                    if in_str:
                        if c == "\\":
                            escape = True
                        elif c == q:
                            in_str = False
                        continue
                    if c in "\"'":
                        in_str = True
                        q = c
                    elif c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                payload = json.loads(s[start : i + 1])
                                break
                            except JSONDecodeError:
                                pass
                if payload is None:
                    raise exc
            else:
                raise exc
        else:
            raise exc

    # 双编码：payload 为 str 时再解析一次（前端误传 JSON 字符串）
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except JSONDecodeError:
            logger.warning("payload_json 双编码解析失败，期望 dict 得到 str")
            return {}

    if not isinstance(payload, dict):
        logger.warning("payload_json 解析结果非 dict: type=%s", type(payload).__name__)
        return {}
    return payload


# ---------------------------------------------------------------------------
# 路由入口
# ---------------------------------------------------------------------------

@router.options("/grpc-web/{path:path}")
async def grpc_web_options(path: str):
    """处理 gRPC-Web 预检请求"""
    return Response(status_code=204, headers=grpc_cors_headers())


@router.post("/grpc-web/frontend.gateway.FrontendGateway/Call")
async def grpc_web_gateway(request: Request):
    """
    gRPC-Web 入口：解包帧 → 解析 protobuf → 调度 handler → 编码响应
    """
    raw_body = await request.body()

    # ---- 1. 解帧 & 解析 ----
    try:
        message_bytes = extract_grpc_web_message(raw_body)
        frontend_request = decode_frontend_request(message_bytes)
    except ValueError as exc:
        logger.error("gRPC-Web 请求解析失败: %s", exc, exc_info=True)
        return build_error_response(str(exc), http_status=400, grpc_status=3)
    except Exception as exc:
        logger.error("gRPC-Web 请求解析异常: %s", exc, exc_info=True)
        return build_error_response(f"请求解析异常: {str(exc)}", http_status=500, grpc_status=13)

    raw_endpoint = frontend_request.get("endpoint") or ""
    endpoint = raw_endpoint.strip().rstrip(".") if isinstance(raw_endpoint, str) else str(raw_endpoint)
    # 兼容前端网关多种 path 前缀（元气八字 destiny 网关、双节点等）
    for prefix in ("/destiny/frontend/api/v1", "/api/v1"):
        if endpoint.startswith(prefix):
            endpoint = "/" + endpoint[len(prefix) :].lstrip("/")
            break
    if endpoint and not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    payload_json = frontend_request["payload_json"]

    try:
        payload = _parse_payload_json(payload_json)
    except JSONDecodeError as exc:
        error_msg = f"payload_json 解析失败: {exc}"
        logger.warning(error_msg)
        return build_error_response(error_msg, http_status=400, grpc_status=3)

    # 注入 request_id（供流式接口评价功能使用，不影响非流式接口）
    from server.api.base.stream_handler import generate_request_id
    payload["_request_id"] = generate_request_id(request.headers)

    # ---- 2. 查找 handler ----
    handler = SUPPORTED_ENDPOINTS.get(endpoint)
    if not handler and endpoint:
        # 回退：按后缀匹配（兼容 /api/v1/bazi/pan/display、bazi/pan/display 等）
        ep_clean = endpoint.rstrip(".").strip()
        for reg in SUPPORTED_ENDPOINTS:
            if ep_clean == reg or ep_clean.endswith(reg) or ("/" + ep_clean.lstrip("/")) == reg:
                handler = SUPPORTED_ENDPOINTS.get(reg)
                if handler:
                    endpoint = reg
                    break
    logger.debug(
        f"🔍 查找端点处理器: {endpoint}, "
        f"是否存在: {handler is not None}, "
        f"总端点数: {len(SUPPORTED_ENDPOINTS)}"
    )

    # 端点列表为空 → 热更新后装饰器未执行，立即恢复
    if len(SUPPORTED_ENDPOINTS) == 0:
        logger.critical(f"🚨🚨 端点列表为空！端点: {endpoint}, 立即恢复所有端点...")
        try:
            _ensure_endpoints_registered()
            handler = SUPPORTED_ENDPOINTS.get(endpoint)
            logger.critical(
                f"🚨 端点恢复完成，当前端点数量: {len(SUPPORTED_ENDPOINTS)}, "
                f"目标端点: {endpoint}, 是否存在: {handler is not None}"
            )
        except Exception as e:
            logger.critical(f"🚨 端点恢复失败: {e}", exc_info=True)
    
    # 仍未找到 → 尝试动态注册
    if not handler:
        handler = _try_dynamic_register(endpoint)

    if not handler:
        available = list(SUPPORTED_ENDPOINTS.keys())
        logger.warning(f"未找到端点: 原始={repr(raw_endpoint)}, 规范化后={endpoint}, 已注册: {available[:15]}")
        error_msg = f"Unsupported endpoint: {endpoint}. Available endpoints: {', '.join(available[:10])}"
        return build_error_response(error_msg, http_status=404, grpc_status=12)

    # ---- 3. 执行 handler ----
    data, status_code = await _execute_handler(handler, endpoint, payload)

    # ---- 4. 编码 & 返回 ----
    success = 200 <= status_code < 300
    detail_value = data.get("detail", "") if isinstance(data, dict) else "未知错误"

    response_payload = encode_frontend_response(
        success=success,
        data_json=json.dumps(data, ensure_ascii=False) if data is not None else "",
        error="" if success else str(detail_value),
        status_code=status_code,
    )

    grpc_status = 0 if success else map_http_to_grpc_status(status_code)
    grpc_message = "" if success else str(detail_value)

    return build_grpc_web_response(response_payload, grpc_status, grpc_message)


# ---------------------------------------------------------------------------
# handler 执行 + 响应序列化
# ---------------------------------------------------------------------------

async def _execute_handler(
    handler, endpoint: str, payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """
    执行 handler 并将结果标准化为 (data_dict, status_code)。
    包含多层防御性检查，确保不会返回 None / 非字典。
    """
    data: Dict[str, Any] = {}
    status_code = 200

    try:
        result = await handler(payload)

        if result is None:
            logger.error(f"Handler 返回了 None，endpoint: {endpoint}")
            return {"detail": "服务返回空结果，请稍后重试"}, 500

        from fastapi.responses import JSONResponse
        if isinstance(result, JSONResponse):
            body = result.body
            if isinstance(body, bytes):
                data = json.loads(body.decode("utf-8"))
            else:
                data = body
            if data is None:
                logger.error("JSONResponse body 解析后为 None")
                return {"error": "响应解析失败", "detail": "JSONResponse body 为空"}, 500
        elif isinstance(result, dict):
            data = result
        elif hasattr(result, "model_dump"):
            data = result.model_dump(exclude_none=False)
            if data is None:
                logger.error("Pydantic v2 model_dump 返回了 None")
                data = {"error": "数据解析失败", "detail": "model_dump 返回空结果"}
        elif hasattr(result, "dict"):
            data = result.dict()
            if data is None:
                logger.error("Pydantic v1 dict() 返回了 None")
                data = {"error": "数据解析失败", "detail": "dict() 返回空结果"}
        else:
            try:
                json_str = json.dumps(result, default=str, ensure_ascii=False)
                data = json.loads(json_str)
                if data is None:
                    logger.error("json.loads 返回了 None")
                    data = {"error": "数据解析失败", "detail": "JSON 解析返回空结果"}
            except (RecursionError, ValueError, TypeError) as json_err:
                logger.error(f"JSON 序列化失败: {json_err}", exc_info=True)
                try:
                    from fastapi.encoders import jsonable_encoder
                    data = jsonable_encoder(result)
                    if data is None:
                        data = {"error": "数据序列化失败", "detail": "jsonable_encoder 返回空结果"}
                except Exception as encoder_err:
                    logger.error(f"jsonable_encoder 也失败: {encoder_err}", exc_info=True)
                    data = {"error": "数据序列化失败", "detail": str(json_err)}

    except HTTPException as exc:
        return {"detail": exc.detail}, exc.status_code
    except Exception as exc:
        logger.exception("gRPC-Web handler 执行失败 (%s): %s", endpoint, exc)
        return {"detail": f"Internal error: {exc}"}, 500

    # 最终防御
    if not isinstance(data, dict) or data is None:
        logger.error(f"最终检查：data 不是有效字典，endpoint: {endpoint}, type: {type(data)}")
        return {"detail": "服务返回了无效的数据"}, 500

    return data, status_code


# ---------------------------------------------------------------------------
# 模块加载时确保端点已注册
# ---------------------------------------------------------------------------
try:
    logger.info("🔧 模块加载时检查端点注册状态...")
    _ensure_endpoints_registered()
    _key = [
        "/daily-fortune-calendar/query", "/bazi/interface",
        "/bazi/shengong-minggong", "/bazi/rizhu-liujiazi",
        "/api/v2/desk-fengshui/analyze",
    ]
    _missing = [ep for ep in _key if ep not in SUPPORTED_ENDPOINTS]
    if _missing:
        logger.warning(f"⚠️  模块加载后关键端点缺失: {_missing}，当前端点数量: {len(SUPPORTED_ENDPOINTS)}")
    else:
        logger.info(f"✅ 所有关键端点已注册（总端点数: {len(SUPPORTED_ENDPOINTS)}）")
except Exception as e:
    logger.error(f"❌ 初始化端点注册检查失败: {e}", exc_info=True)

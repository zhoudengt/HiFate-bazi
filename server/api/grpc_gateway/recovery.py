#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 端点恢复模块

提供热更新后的端点恢复、动态注册和模块重载功能。
从 grpc_gateway.py 中提取，降低主文件体积。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from server.api.grpc_gateway.endpoints import SUPPORTED_ENDPOINTS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 热更新：模块级重载
# ---------------------------------------------------------------------------

def _reload_endpoints() -> bool:
    """
    重新注册所有端点（用于热更新后恢复）。

    流程：
    1. 备份旧端点
    2. 清空并 importlib.reload 所有 handler 模块以触发 @_register 装饰器
    3. 若重载后端点数量 < 40，回滚到旧端点（防止热更新导致端点丢失）
    4. 若关键端点仍缺失，降级手动注册
    """
    old_count = len(SUPPORTED_ENDPOINTS)
    old_endpoints = dict(SUPPORTED_ENDPOINTS)  # 备份旧端点
    SUPPORTED_ENDPOINTS.clear()
    logger.info(f"已清空 gRPC 端点注册表（旧端点数: {old_count}）")

    try:
        import importlib
        import sys

        # 重新加载所有 handler 模块（关键！）
        handler_modules = [
            "server.api.grpc_gateway.handlers.payment_handlers",
            "server.api.grpc_gateway.handlers.homepage_handlers",
            "server.api.grpc_gateway.handlers.calendar_handlers",
            "server.api.grpc_gateway.handlers.smart_handlers",
            "server.api.grpc_gateway.handlers.media_handlers",
            "server.api.grpc_gateway.handlers.admin_handlers",
            "server.api.grpc_gateway.handlers.bazi_handlers",
            "server.api.grpc_gateway.handlers.stream_handlers",
            "server.api.grpc_gateway.handlers.liuyao_handlers",
        ]
        
        failed_modules = []
        for module_name in handler_modules:
            if module_name in sys.modules:
                try:
                    importlib.reload(sys.modules[module_name])
                    logger.debug(f"✓ 重新加载: {module_name}")
                except Exception as e:
                    logger.error(f"🚨 重新加载 {module_name} 失败: {e}", exc_info=True)
                    failed_modules.append(module_name)
            else:
                try:
                    __import__(module_name)
                    logger.debug(f"✓ 首次加载: {module_name}")
                except Exception as e:
                    logger.error(f"🚨 加载 {module_name} 失败: {e}", exc_info=True)
                    failed_modules.append(module_name)

        endpoint_count = len(SUPPORTED_ENDPOINTS)
        logger.info(f"重新加载后端点数量: {endpoint_count}（失败模块: {failed_modules}）")

        # 如果重载后端点数量不足，回滚到旧端点
        if endpoint_count < 40 and old_count >= 40:
            logger.error(f"🚨 重载后端点数量不足（{endpoint_count} < 40），回滚到旧端点（{old_count}）")
            SUPPORTED_ENDPOINTS.clear()
            SUPPORTED_ENDPOINTS.update(old_endpoints)
            logger.info(f"✅ 已回滚到旧端点，当前端点数: {len(SUPPORTED_ENDPOINTS)}")
            return False

        key_endpoints = ["/bazi/interface", "/bazi/shengong-minggong", "/bazi/rizhu-liujiazi"]
        missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]

        if endpoint_count == 0 or missing:
            logger.warning(f"⚠️  端点未正确注册（总数: {endpoint_count}, 缺失: {missing}），尝试手动注册...")
            _manual_register_core_endpoints()

        endpoint_count = len(SUPPORTED_ENDPOINTS)
        logger.info(f"✅ gRPC 端点已重新注册，当前端点数量: {endpoint_count}")

        if endpoint_count > 0:
            logger.debug(f"已注册的端点: {list(SUPPORTED_ENDPOINTS.keys())[:10]}...")
            missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
            if missing:
                logger.warning(f"⚠️  关键端点未注册: {missing}")
            else:
                logger.info(f"✅ 关键端点验证通过: {key_endpoints}")
        else:
            logger.error("❌ 端点重新注册后数量为0，可能存在模块加载问题")

        return endpoint_count > 0
    except Exception as e:
        logger.error(f"❌ gRPC 端点重新注册失败: {e}", exc_info=True)
        # 发生异常时回滚
        if old_count > 0:
            SUPPORTED_ENDPOINTS.clear()
            SUPPORTED_ENDPOINTS.update(old_endpoints)
            logger.info(f"✅ 异常回滚到旧端点，当前端点数: {len(SUPPORTED_ENDPOINTS)}")
        return False


# ---------------------------------------------------------------------------
# 启动 / 热更新：确保关键端点存在
# ---------------------------------------------------------------------------

def _ensure_endpoints_registered() -> None:
    """确保所有关键端点已注册（模块加载 + 热更新后调用）。"""
    global SUPPORTED_ENDPOINTS  # noqa: PLW0603

    key_endpoints = [
        "/bazi/interface",
        "/bazi/shengong-minggong",
        "/bazi/rizhu-liujiazi",
        "/api/v2/desk-fengshui/analyze",
        "/daily-fortune-calendar/query",
    ]

    if len(SUPPORTED_ENDPOINTS) == 0:
        logger.error("🚨 端点列表为空！直接手动注册所有关键端点...")
        missing_endpoints = key_endpoints
    else:
        missing_endpoints = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]

    logger.debug(
        f"检查关键端点注册状态: key_endpoints={key_endpoints}, "
        f"missing_endpoints={missing_endpoints}, "
        f"supported_endpoints_count={len(SUPPORTED_ENDPOINTS)}"
    )

    if not missing_endpoints:
        return

    logger.error(f"🚨 检测到缺失端点: {missing_endpoints}，尝试手动注册...")
    try:
        _register_missing_endpoints(missing_endpoints)
    except Exception as e:
        logger.error(f"手动注册端点失败: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# 请求级动态注册（endpoint 未命中时的 fallback）
# ---------------------------------------------------------------------------

def _try_dynamic_register(endpoint: str) -> Optional[Callable]:
    """
    当请求到达但 SUPPORTED_ENDPOINTS 中找不到时，尝试即时注册。
    返回 handler 函数，或 None。
    """
    registry = _DYNAMIC_REGISTRY.get(endpoint)
    if registry is None:
        return None

    try:
        handler = registry()
        if handler:
            SUPPORTED_ENDPOINTS[endpoint] = handler
            logger.info(f"✅ 动态注册端点: {endpoint}")
        return handler
    except Exception as e:
        logger.error(f"动态注册端点失败 ({endpoint}): {e}", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _manual_register_core_endpoints() -> None:
    """手动注册 3 个核心端点（_reload_endpoints 的降级路径）。"""
    try:
        from server.api.v1.bazi import BaziInterfaceRequest, ShengongMinggongRequest
        from server.services.bazi_interface_service import BaziInterfaceService
        from server.utils.bazi_input_processor import BaziInputProcessor
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        from server.orchestrators.modules_config import get_modules_config
        from server.api.v1.bazi_display import _assemble_shengong_minggong_response

        async def _handle_bazi_interface(payload: Dict[str, Any]):
            import asyncio
            request_model = BaziInterfaceRequest(**payload)
            loop = asyncio.get_event_loop()
            from server.utils.async_executor import get_executor
            result = await loop.run_in_executor(
                get_executor(),
                BaziInterfaceService.generate_interface_full,
                request_model.solar_date,
                request_model.solar_time,
                request_model.gender,
                request_model.name or "",
                request_model.location or "未知地",
                request_model.latitude or 39.00,
                request_model.longitude or 120.00,
            )
            return {"success": True, "data": result}

        async def _handle_shengong_minggong(payload: Dict[str, Any]):
            from datetime import datetime
            request_model = ShengongMinggongRequest(**payload)
            final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
                request_model.solar_date, request_model.solar_time,
                request_model.calendar_type or "solar",
                request_model.location, request_model.latitude, request_model.longitude,
            )
            current_time = datetime.now()
            if request_model.current_time:
                try:
                    current_time = datetime.strptime(request_model.current_time, "%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            modules = get_modules_config("shengong_minggong")
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                final_solar_date, final_solar_time, request_model.gender,
                modules=modules, current_time=current_time, preprocessed=True,
                calendar_type=request_model.calendar_type or "solar",
                location=request_model.location, latitude=request_model.latitude,
                longitude=request_model.longitude,
                dayun_year_start=request_model.dayun_year_start,
                dayun_year_end=request_model.dayun_year_end,
                target_year=request_model.target_year,
            )
            return _assemble_shengong_minggong_response(
                orchestrator_data, final_solar_date, final_solar_time,
                request_model.gender, current_time,
                request_model.dayun_year_start, request_model.dayun_year_end,
                request_model.target_year,
            )

        from server.api.v1.rizhu_liujiazi import RizhuLiujiaziRequest, get_rizhu_liujiazi

        async def _handle_rizhu_liujiazi(payload: Dict[str, Any]):
            request_model = RizhuLiujiaziRequest(**payload)
            return await get_rizhu_liujiazi(request_model)

        SUPPORTED_ENDPOINTS["/bazi/interface"] = _handle_bazi_interface
        SUPPORTED_ENDPOINTS["/bazi/shengong-minggong"] = _handle_shengong_minggong
        SUPPORTED_ENDPOINTS["/bazi/rizhu-liujiazi"] = _handle_rizhu_liujiazi
        logger.info("✅ 手动注册核心端点成功（包含 /bazi/rizhu-liujiazi）")
    except Exception as e:
        logger.error(f"❌ 手动注册核心端点失败: {e}", exc_info=True)


def _register_missing_endpoints(missing_endpoints: list) -> None:
    """按需注册 _ensure_endpoints_registered 中发现的缺失端点。"""

    if "/daily-fortune-calendar/query" in missing_endpoints:
        try:
            from server.api.v1.daily_fortune_calendar import DailyFortuneCalendarRequest, query_daily_fortune_calendar

            async def _h_daily_fortune_query(payload: Dict[str, Any]):
                request_model = DailyFortuneCalendarRequest(**payload)
                result = await query_daily_fortune_calendar(request_model)
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                return result

            SUPPORTED_ENDPOINTS["/daily-fortune-calendar/query"] = _h_daily_fortune_query
            logger.info("✅ 手动注册端点: /daily-fortune-calendar/query")
        except Exception as e:
            logger.error(f"❌ 手动注册 /daily-fortune-calendar/query 失败: {e}", exc_info=True)

    if "/bazi/interface" in missing_endpoints:
        try:
            from server.api.v1.bazi import BaziInterfaceRequest, generate_bazi_interface
            from fastapi import Request as _Req
            from unittest.mock import MagicMock

            async def _h_bazi_interface(payload: Dict[str, Any]):
                request_model = BaziInterfaceRequest(**payload)
                mock_request = MagicMock(spec=_Req)
                result = await generate_bazi_interface(request_model, mock_request)
                if hasattr(result, "model_dump"):
                    return result.model_dump()
                elif hasattr(result, "dict"):
                    return result.dict()
                return result

            SUPPORTED_ENDPOINTS["/bazi/interface"] = _h_bazi_interface
            logger.error("🚨 手动注册端点: /bazi/interface")
        except Exception as e:
            logger.error(f"❌ 手动注册 /bazi/interface 端点失败: {e}", exc_info=True)

    if "/bazi/shengong-minggong" in missing_endpoints:
        try:
            from server.api.v1.bazi import ShengongMinggongRequest
            from server.utils.bazi_input_processor import BaziInputProcessor
            from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
            from server.orchestrators.modules_config import get_modules_config
            from server.api.v1.bazi_display import _assemble_shengong_minggong_response

            async def _h_shengong(payload: Dict[str, Any]):
                from datetime import datetime as dt_m
                request_model = ShengongMinggongRequest(**payload)
                final_sd, final_st, _ = BaziInputProcessor.process_input(
                    request_model.solar_date, request_model.solar_time,
                    request_model.calendar_type or "solar",
                    request_model.location, request_model.latitude, request_model.longitude,
                )
                ct = dt_m.now()
                if request_model.current_time:
                    try:
                        ct = dt_m.strptime(request_model.current_time, "%Y-%m-%d %H:%M")
                    except ValueError:
                        pass
                mods = get_modules_config("shengong_minggong")
                odata = await BaziDataOrchestrator.fetch_data(
                    final_sd, final_st, request_model.gender,
                    modules=mods, current_time=ct, preprocessed=True,
                    calendar_type=request_model.calendar_type or "solar",
                    location=request_model.location, latitude=request_model.latitude,
                    longitude=request_model.longitude,
                    dayun_year_start=request_model.dayun_year_start,
                    dayun_year_end=request_model.dayun_year_end,
                    target_year=request_model.target_year,
                )
                return _assemble_shengong_minggong_response(
                    odata, final_sd, final_st, request_model.gender, ct,
                    request_model.dayun_year_start, request_model.dayun_year_end,
                    request_model.target_year,
                )

            SUPPORTED_ENDPOINTS["/bazi/shengong-minggong"] = _h_shengong
            logger.error("🚨 手动注册端点: /bazi/shengong-minggong")
        except Exception as e:
            logger.error(f"❌ 手动注册 /bazi/shengong-minggong 端点失败: {e}", exc_info=True)

    if "/bazi/rizhu-liujiazi" in missing_endpoints:
        try:
            from server.api.v1.rizhu_liujiazi import RizhuLiujiaziRequest, get_rizhu_liujiazi

            async def _h_rizhu(payload: Dict[str, Any]):
                request_model = RizhuLiujiaziRequest(**payload)
                return await get_rizhu_liujiazi(request_model)

            SUPPORTED_ENDPOINTS["/bazi/rizhu-liujiazi"] = _h_rizhu
            logger.error("🚨 手动注册端点: /bazi/rizhu-liujiazi")
        except Exception as e:
            logger.error(f"❌ 手动注册 /bazi/rizhu-liujiazi 端点失败: {e}", exc_info=True)

    if "/api/v2/desk-fengshui/analyze" in missing_endpoints:
        try:
            from server.api.v2.desk_fengshui_api import analyze_desk_fengshui
            from fastapi import UploadFile
            from fastapi.responses import JSONResponse
            import base64
            from io import BytesIO

            async def _h_desk_fengshui(payload: Dict[str, Any]):
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
                    headers={"content-type": payload.get("content_type", "image/jpeg")},
                )
                result = await analyze_desk_fengshui(image=image_file)
                if isinstance(result, JSONResponse):
                    body = result.body
                    return json.loads(body.decode("utf-8")) if isinstance(body, bytes) else body
                return result

            SUPPORTED_ENDPOINTS["/api/v2/desk-fengshui/analyze"] = _h_desk_fengshui
            logger.error("🚨 手动注册端点: /api/v2/desk-fengshui/analyze")
        except Exception as e:
            logger.error(f"❌ 手动注册 /api/v2/desk-fengshui/analyze 端点失败: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# 动态注册表：endpoint -> factory（返回 handler 的无参函数）
# ---------------------------------------------------------------------------

def _make_rizhu_liujiazi() -> Callable:
    from server.api.v1.rizhu_liujiazi import RizhuLiujiaziRequest, get_rizhu_liujiazi

    async def handler(payload: Dict[str, Any]):
        return await get_rizhu_liujiazi(RizhuLiujiaziRequest(**payload))
    return handler


def _make_desk_fengshui() -> Callable:
    from server.api.v2.desk_fengshui_api import analyze_desk_fengshui
    from fastapi import UploadFile
    from fastapi.responses import JSONResponse
    import base64
    from io import BytesIO

    async def handler(payload: Dict[str, Any]):
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
            headers={"content-type": payload.get("content_type", "image/jpeg")},
        )
        result = await analyze_desk_fengshui(image=image_file)
        if isinstance(result, JSONResponse):
            body = result.body
            return json.loads(body.decode("utf-8")) if isinstance(body, bytes) else body
        return result
    return handler


def _make_wuxing_proportion_test() -> Callable:
    from server.api.v1.wuxing_proportion import WuxingProportionRequest, wuxing_proportion_test

    async def handler(payload: Dict[str, Any]):
        return await wuxing_proportion_test(WuxingProportionRequest(**payload))
    return handler


def _make_xishen_jishen_test() -> Callable:
    from server.api.v1.xishen_jishen import XishenJishenRequest, xishen_jishen_test

    async def handler(payload: Dict[str, Any]):
        return await xishen_jishen_test(XishenJishenRequest(**payload))
    return handler


def _make_daily_fortune_calendar_test() -> Callable:
    from server.api.v1.daily_fortune_calendar import DailyFortuneCalendarRequest, daily_fortune_calendar_test

    async def handler(payload: Dict[str, Any]):
        return await daily_fortune_calendar_test(DailyFortuneCalendarRequest(**payload))
    return handler


def _make_daily_fortune_calendar_query() -> Callable:
    from server.api.v1.daily_fortune_calendar import DailyFortuneCalendarRequest, query_daily_fortune_calendar

    async def handler(payload: Dict[str, Any]):
        result = await query_daily_fortune_calendar(DailyFortuneCalendarRequest(**payload))
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    return handler


_DYNAMIC_REGISTRY: Dict[str, Callable[[], Callable]] = {
    "/bazi/rizhu-liujiazi": _make_rizhu_liujiazi,
    "/api/v2/desk-fengshui/analyze": _make_desk_fengshui,
    "/bazi/wuxing-proportion/test": _make_wuxing_proportion_test,
    "/bazi/xishen-jishen/test": _make_xishen_jishen_test,
    "/daily-fortune-calendar/test": _make_daily_fortune_calendar_test,
    "/daily-fortune-calendar/query": _make_daily_fortune_calendar_query,
}

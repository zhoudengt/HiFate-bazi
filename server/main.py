#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口（精简版）

路由注册、生命周期、健康检查已拆分到独立模块：
- server/lifecycle.py          - 启动/关闭逻辑
- server/router_registry.py    - 路由导入与注册
- server/health.py             - 健康检查端点
- server/middleware/utf8_json.py - UTF8 JSON 响应
"""

import sys
import os
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from fastapi.staticfiles import StaticFiles

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 配置日志
_log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        logger.info(f"✓ 已加载环境变量文件: {env_path}")
        try:
            from server.config.config_loader import get_config_from_db_only
            coze_token = get_config_from_db_only("COZE_ACCESS_TOKEN")
            coze_bot_id = get_config_from_db_only("COZE_BOT_ID")
            daily_fortune_action_bot_id = get_config_from_db_only("DAILY_FORTUNE_ACTION_BOT_ID")
            if coze_token:
                logger.info(f"✓ COZE_ACCESS_TOKEN (数据库): {coze_token[:20]}...")
            else:
                logger.warning("⚠️ COZE_ACCESS_TOKEN 未在数据库中配置")
            if coze_bot_id:
                logger.info(f"✓ COZE_BOT_ID (数据库): {coze_bot_id}")
            else:
                logger.warning("⚠️ COZE_BOT_ID 未在数据库中配置")
            if daily_fortune_action_bot_id:
                logger.info(f"✓ DAILY_FORTUNE_ACTION_BOT_ID (数据库): {daily_fortune_action_bot_id}")
            else:
                logger.warning("⚠️ DAILY_FORTUNE_ACTION_BOT_ID 未在数据库中配置")
        except Exception as e:
            logger.warning(f"⚠️ 无法从数据库读取配置: {e}")
except ImportError:
    logger.warning("⚠ python-dotenv 未安装，将使用系统环境变量")
except Exception as e:
    logger.warning(f"⚠ 加载 .env 文件失败: {e}")

# --- 导入拆分模块 ---
from server.middleware.utf8_json import UTF8JSONResponse
from server.middleware.gzip_sse import SSEAwareGZipMiddleware
from server.lifecycle import lifespan
from server.health import health_router

# 限流（可选）
RATE_LIMIT_AVAILABLE = False
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMIT_AVAILABLE = True
    logger.info("✓ 限流中间件已加载")
except ImportError:
    logger.info("ℹ slowapi 未安装，限流功能已禁用")
except Exception as e:
    logger.warning(f"⚠ 限流初始化失败: {e}")

# ==================== 创建 FastAPI 应用 ====================

app = FastAPI(
    title="HiFateAPI",
    description="八字计算与命理分析API服务",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=UTF8JSONResponse
)

# 初始化路由管理器
from server.utils.router_manager import RouterManager
router_manager = RouterManager(app)

# 限流器
if RATE_LIMIT_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ==================== 中间件 ====================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    response.headers["X-Process-Time"] = str(process_time)
    return response

# CORS
try:
    from server.utils.cors_config import get_cors_config
    cors_config = get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allow_origins"],
        allow_credentials=cors_config["allow_credentials"],
        allow_methods=cors_config["allow_methods"],
        allow_headers=cors_config["allow_headers"],
    )
    logger.info(f"✓ CORS 中间件已配置，允许来源: {cors_config['allow_origins']}")
except Exception as e:
    logger.warning(f"⚠ CORS 配置加载失败，使用默认配置: {e}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# GZip（SSE 除外）
app.add_middleware(SSEAwareGZipMiddleware, minimum_size=1000)

# 异常处理
try:
    from server.utils.exception_handler import ExceptionHandlerMiddleware
    app.add_middleware(ExceptionHandlerMiddleware)
    logger.info("✓ 统一异常处理中间件已启用")
except ImportError as e:
    logger.warning(f"⚠ 异常处理中间件导入失败（可选功能）: {e}")
except Exception as e:
    logger.warning(f"⚠ 异常处理中间件启用失败: {e}")

# ==================== 路由注册 ====================

from server.router_registry import _register_all_routers_to_manager
_register_all_routers_to_manager(router_manager)
router_manager.register_all_routers()

# 健康检查路由
app.include_router(health_router)

# 静态文件
local_frontend_dir = os.path.join(project_root, "local_frontend")
if os.path.isdir(local_frontend_dir):
    app.mount("/frontend", StaticFiles(directory=local_frontend_dir, html=True), name="frontend")
    logger.info(f"✓ 静态文件目录已挂载: {local_frontend_dir}")

# ==================== 入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        workers=1
    )

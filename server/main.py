#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口
"""

import sys
import os
import time
import logging
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager


# 自定义UTF-8 JSONResponse类，确保中文正确编码 + 强制不缓存
class UTF8JSONResponse(Response):
    media_type = "application/json; charset=utf-8"
    
    def __init__(self, content, **kwargs):
        super().__init__(content, **kwargs)
        # 强制禁用所有缓存
        self.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        self.headers["Pragma"] = "no-cache"
        self.headers["Expires"] = "0"
    
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,  # 关键：不转义非ASCII字符
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 优先加载 .env 文件（必须在导入其他模块之前）
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)  # override=True 确保覆盖已存在的环境变量
        print(f"✓ 已加载环境变量文件: {env_path}")
        # 验证关键环境变量
        coze_token = os.getenv("COZE_ACCESS_TOKEN")
        coze_bot_id = os.getenv("COZE_BOT_ID")
        if coze_token:
            print(f"✓ COZE_ACCESS_TOKEN: {coze_token[:20]}...")
        if coze_bot_id:
            print(f"✓ COZE_BOT_ID: {coze_bot_id}")
except ImportError:
    print("⚠ python-dotenv 未安装，将使用系统环境变量")
except Exception as e:
    print(f"⚠ 加载 .env 文件失败: {e}")

# 配置日志（必须在导入路由之前初始化，以便在导入失败时可以使用logger）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from server.api.v1.bazi import router as bazi_router

# 新增：旺衰分析路由（可选功能）
try:
    from server.api.v1.wangshuai import router as wangshuai_router
    WANGSHUAI_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"旺衰分析路由导入失败（可选功能）: {e}")
    wangshuai_router = None
    WANGSHUAI_ROUTER_AVAILABLE = False
from server.api.v1.bazi_ai import router as bazi_ai_router
from server.api.v1.auth import router as auth_router
try:
    from server.api.v1.oauth import router as oauth_router
    OAUTH_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OAuth 路由导入失败（可选功能）: {e}")
    oauth_router = None
    OAUTH_ROUTER_AVAILABLE = False
from server.api.grpc_gateway import router as grpc_gateway_router

# 新增：支付路由（魔方西元）
try:
    from server.api.v1.payment import router as payment_router
    PAYMENT_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"支付路由导入失败（可选功能）: {e}")
    payment_router = None
    PAYMENT_ROUTER_AVAILABLE = False

from mianxiang_hand_fengshui.api.routers import (
    face_router as mx_face_router,
    hand_router as mx_hand_router,
    fengshui_router as mx_fengshui_router,
    bazi_router as mx_bazi_router,
)

# 新增：规则匹配路由（不影响现有功能）
try:
    from server.api.v1.bazi_rules import router as bazi_rules_router
    RULES_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"规则匹配路由导入失败（可选功能）: {e}")
    bazi_rules_router = None
    RULES_ROUTER_AVAILABLE = False

# 新增：规则管理路由（管理员接口）
try:
    from server.api.v1.admin_rules import router as admin_rules_router
    ADMIN_RULES_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"规则管理路由导入失败（可选功能）: {e}")
    admin_rules_router = None
    ADMIN_RULES_ROUTER_AVAILABLE = False

# 新增：热更新路由
try:
    from server.hot_reload.api import router as hot_reload_router
    HOT_RELOAD_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"热更新路由导入失败（可选功能）: {e}")
    hot_reload_router = None
    HOT_RELOAD_ROUTER_AVAILABLE = False

# 新增：LLM 生成路由（类似 FateTell）
try:
    from server.api.v1.llm_generate import router as llm_generate_router
    LLM_GENERATE_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LLM 生成路由导入失败（可选功能）: {e}")
    llm_generate_router = None
    LLM_GENERATE_ROUTER_AVAILABLE = False

# 新增：对话路由（24/7 AI 对话）
try:
    from server.api.v1.chat import router as chat_router
    CHAT_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"对话路由导入失败（可选功能）: {e}")
    chat_router = None
    CHAT_ROUTER_AVAILABLE = False

# 新增：一事一卦路由
try:
    from server.api.v1.yigua import router as yigua_router
    YIGUA_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"一事一卦路由导入失败（可选功能）: {e}")

# 新增：面相分析V2路由（独立系统）
try:
    from server.api.v2.face_analysis import router as face_analysis_v2_router
    FACE_ANALYSIS_V2_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"面相分析V2路由导入失败（可选功能）: {e}")
    face_analysis_v2_router = None
    FACE_ANALYSIS_V2_ROUTER_AVAILABLE = False

# 新增：今日运势分析路由（类似 FateTell 的日运日签）
try:
    from server.api.v1.daily_fortune import router as daily_fortune_router
    DAILY_FORTUNE_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"今日运势分析路由导入失败（可选功能）: {e}")
    daily_fortune_router = None
    DAILY_FORTUNE_ROUTER_AVAILABLE = False

# 新增：运势API路由（调用第三方API）
try:
    from server.api.v1.fortune_api import router as fortune_api_router
    FORTUNE_API_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"运势API路由导入失败（可选功能）: {e}")
    fortune_api_router = None
    FORTUNE_API_ROUTER_AVAILABLE = False

# 新增：万年历API路由（调用第三方API）
try:
    from server.api.v1.calendar_api import router as calendar_api_router
    CALENDAR_API_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"万年历API路由导入失败（可选功能）: {e}")
    calendar_api_router = None
    CALENDAR_API_ROUTER_AVAILABLE = False

# 新增：月运势分析路由（基于八字）
try:
    from server.api.v1.monthly_fortune import router as monthly_fortune_router
    MONTHLY_FORTUNE_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"月运势分析路由导入失败（可选功能）: {e}")
    monthly_fortune_router = None
    MONTHLY_FORTUNE_ROUTER_AVAILABLE = False

# 新增：算法公式规则分析路由（808条规则）
try:
    from server.api.v1.formula_analysis import router as formula_analysis_router
    FORMULA_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"算法公式规则分析路由导入失败（可选功能）: {e}")
    formula_analysis_router = None
    FORMULA_ANALYSIS_ROUTER_AVAILABLE = False

# 新增：用户反馈路由
try:
    from server.api.v1.feedback import router as feedback_router
    FEEDBACK_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"用户反馈路由导入失败（可选功能）: {e}")
    feedback_router = None
    FEEDBACK_ROUTER_AVAILABLE = False

# 新增：算法公式分析路由（基于2025.11.20规则）
try:
    from server.api.v1.formula_analysis import router as formula_analysis_router
    FORMULA_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"算法公式分析路由导入失败（可选功能）: {e}")
    formula_analysis_router = None
    FORMULA_ANALYSIS_ROUTER_AVAILABLE = False

# 新增：前端展示路由（前端优化格式）
try:
    from server.api.v1.bazi_display import router as bazi_display_router
    BAZI_DISPLAY_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"前端展示路由导入失败（可选功能）: {e}")
    bazi_display_router = None
    BAZI_DISPLAY_ROUTER_AVAILABLE = False

# 新增：统一支付路由（Stripe+PayPal+支付宝+微信）
try:
    from server.api.v1.unified_payment import router as unified_payment_router
    UNIFIED_PAYMENT_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"统一支付路由导入失败（可选功能）: {e}")
    unified_payment_router = None
    UNIFIED_PAYMENT_ROUTER_AVAILABLE = False

# 新增：模型微调路由
try:
    from server.api.v1.model_tuning import router as model_tuning_router
    MODEL_TUNING_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"模型微调路由导入失败（可选功能）: {e}")
    model_tuning_router = None
    MODEL_TUNING_ROUTER_AVAILABLE = False

# 推送服务和数据分析路由已废弃，已删除

# 尝试导入限流中间件（可选，如果安装失败也不影响主流程）
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    logger.warning("slowapi 未安装，限流功能将不可用。运行 'pip install slowapi' 以启用限流。")
    limiter = None
    RATE_LIMIT_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    try:
        # 打印所有已注册的 gRPC 端点
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        logger.info(f"✓ 已注册 {len(SUPPORTED_ENDPOINTS)} 个 gRPC 端点:")
        for endpoint in sorted(SUPPORTED_ENDPOINTS.keys()):
            logger.info(f"  - {endpoint}")
    except Exception as e:
        logger.warning(f"⚠ 打印 gRPC 端点失败: {e}")
    
    try:
        # 启动统一的热更新管理器（替代原来的规则热加载）
        from server.hot_reload.hot_reload_manager import HotReloadManager
        manager = HotReloadManager.get_instance(interval=60)  # 1分钟检查一次（减少延迟）
        manager.start()
        logger.info("✓ 热更新管理器已启动")
    except Exception as e:
        logger.warning(f"⚠ 热更新管理器启动失败: {e}")
        # 降级到原来的规则热加载
        try:
            from server.services.rule_service import RuleService
            RuleService.start_auto_reload(interval=300)
            logger.info("✓ 规则热加载机制已启动（降级模式）")
        except Exception as e2:
            logger.warning(f"⚠ 规则热加载启动失败: {e2}")
    
    # 启动集群同步器（双机同步）
    try:
        from server.hot_reload.cluster_synchronizer import start_cluster_sync
        start_cluster_sync()
        logger.info("✓ 集群同步器已启动")
    except Exception as e:
        logger.warning(f"⚠ 集群同步器启动失败（单机模式）: {e}")
    
    yield
    # 关闭时执行
    # 停止集群同步器
    try:
        from server.hot_reload.cluster_synchronizer import stop_cluster_sync
        stop_cluster_sync()
        logger.info("✓ 集群同步器已停止")
    except Exception as e:
        logger.warning(f"⚠ 集群同步器停止失败: {e}")
    
    try:
        from server.hot_reload.hot_reload_manager import HotReloadManager
        manager = HotReloadManager.get_instance()
        manager.stop()
        logger.info("✓ 热更新管理器已停止")
    except Exception as e:
        logger.warning(f"⚠ 热更新管理器停止失败: {e}")
        # 停止原来的规则热加载
        try:
            from server.services.rule_service import RuleService
            if RuleService._reloader:
                RuleService._reloader.stop()
                logger.info("✓ 规则热加载机制已停止")
        except Exception as e2:
            logger.warning(f"⚠ 规则热加载停止失败: {e2}")


app = FastAPI(
    title="HiFateAPI",
    description="八字计算与命理分析API服务",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=UTF8JSONResponse  # 使用UTF-8编码的JSON响应
)

# 如果限流可用，初始化限流器
if RATE_LIMIT_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志，包括处理时间"""
    start_time = time.time()
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录日志
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加GZip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ✅ 添加 OAuth 2.0 认证中间件（在异常处理之前，确保认证错误能被正确处理）
# ⚠️ 注意：中间件在应用启动时实例化，修改代码后必须重启服务才能生效
try:
    from server.middleware.auth_middleware import AuthMiddleware, WHITELIST_PREFIXES
    # ⚠️ 临时禁用: app.add_middleware(AuthMiddleware)
    logger.warning("⚠ 认证中间件已临时禁用（紧急修复）")
    logger.info(f"   白名单前缀: {list(WHITELIST_PREFIXES)}")
except ImportError as e:
    logger.warning(f"⚠ 认证中间件导入失败（可选功能）: {e}")
except Exception as e:
    logger.warning(f"⚠ 认证中间件启用失败: {e}")

# ✅ 添加统一异常处理中间件（最后添加，确保能捕获所有异常）
try:
    from server.utils.exception_handler import ExceptionHandlerMiddleware
    app.add_middleware(ExceptionHandlerMiddleware)
    logger.info("✓ 统一异常处理中间件已启用")
except ImportError as e:
    logger.warning(f"⚠ 异常处理中间件导入失败（可选功能）: {e}")
except Exception as e:
    logger.warning(f"⚠ 异常处理中间件启用失败: {e}")

# 注册路由
app.include_router(bazi_router, prefix="/api/v1", tags=["八字计算"])
app.include_router(bazi_ai_router, prefix="/api/v1", tags=["AI分析"])
app.include_router(auth_router, prefix="/api/v1", tags=["鉴权"])
if OAUTH_ROUTER_AVAILABLE and oauth_router:
    app.include_router(oauth_router, prefix="/api/v1", tags=["OAuth 2.0"])
    logger.info("✓ OAuth 2.0 路由已注册")
app.include_router(grpc_gateway_router, prefix="/api", tags=["gRPC-Web"])

# 注册旺衰分析路由（新增，可选功能）
if WANGSHUAI_ROUTER_AVAILABLE and wangshuai_router:
    app.include_router(wangshuai_router, prefix="/api/v1", tags=["旺衰分析"])
    logger.info("✓ 旺衰分析路由已注册")
app.include_router(
    mx_face_router.router,
    prefix="/api/v1/mianxiang/analysis/face",
    tags=["面相分析"],
)
app.include_router(
    mx_hand_router.router,
    prefix="/api/v1/mianxiang/analysis/hand",
    tags=["手相分析"],
)
app.include_router(
    mx_bazi_router.router,
    prefix="/api/v1/mianxiang/analysis/bazi",
    tags=["八字扩展分析"],
)
app.include_router(
    mx_fengshui_router.router,
    prefix="/api/v1/mianxiang/recommendations/fengshui",
    tags=["办公室摆件建议"],
)

# 注册规则匹配路由（新增，不影响现有功能）
if RULES_ROUTER_AVAILABLE and bazi_rules_router:
    app.include_router(bazi_rules_router, prefix="/api/v1", tags=["规则匹配"])

# 注册规则管理路由（新增，管理员接口）
if ADMIN_RULES_ROUTER_AVAILABLE and admin_rules_router:
    app.include_router(admin_rules_router, prefix="/api/v1", tags=["规则管理"])

# 注册热更新路由（新增）
if HOT_RELOAD_ROUTER_AVAILABLE and hot_reload_router:
    app.include_router(hot_reload_router, prefix="/api/v1", tags=["热更新"])

# 注册 LLM 生成路由（新增，类似 FateTell）
if LLM_GENERATE_ROUTER_AVAILABLE and llm_generate_router:
    app.include_router(llm_generate_router, prefix="/api/v1", tags=["LLM生成"])

# 注册对话路由（新增，24/7 AI 对话）
if CHAT_ROUTER_AVAILABLE and chat_router:
    app.include_router(chat_router, prefix="/api/v1", tags=["AI对话"])

# 注册一事一卦路由（新增）
if YIGUA_ROUTER_AVAILABLE and yigua_router:
    app.include_router(yigua_router, prefix="/api/v1", tags=["一事一卦"])

# 注册今日运势分析路由（新增，类似 FateTell 的日运日签）
if DAILY_FORTUNE_ROUTER_AVAILABLE and daily_fortune_router:
    app.include_router(daily_fortune_router, prefix="/api/v1", tags=["今日运势"])

# 注册运势API路由（新增，调用第三方API）
if FORTUNE_API_ROUTER_AVAILABLE and fortune_api_router:
    app.include_router(fortune_api_router, prefix="/api/v1", tags=["运势API"])

# 注册万年历API路由（新增，调用第三方API）
if CALENDAR_API_ROUTER_AVAILABLE and calendar_api_router:
    app.include_router(calendar_api_router, prefix="/api/v1", tags=["万年历API"])
    logger.info("✓ 万年历API路由已注册")

# 注册月运势分析路由（新增，基于八字）
if MONTHLY_FORTUNE_ROUTER_AVAILABLE and monthly_fortune_router:
    app.include_router(monthly_fortune_router, prefix="/api/v1", tags=["月运势"])
    logger.info("✓ 月运势分析路由已注册")

# 算法公式规则分析路由（808条规则）
if FORMULA_ANALYSIS_ROUTER_AVAILABLE and formula_analysis_router:
    app.include_router(formula_analysis_router, prefix="/api/v1", tags=["算法公式规则"])

# 注册用户反馈路由
if FEEDBACK_ROUTER_AVAILABLE and feedback_router:
    app.include_router(feedback_router, prefix="/api/v1", tags=["用户反馈"])
    logger.info("✓ 用户反馈路由已注册")

# 新增：流年大运增强分析路由
try:
    from server.api.v1.liunian_enhanced import router as liunian_enhanced_router
    LIUNIAN_ENHANCED_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"流年大运增强分析路由导入失败（可选功能）: {e}")
    liunian_enhanced_router = None
    LIUNIAN_ENHANCED_ROUTER_AVAILABLE = False

# 注册流年大运增强分析路由
if LIUNIAN_ENHANCED_ROUTER_AVAILABLE and liunian_enhanced_router:
    app.include_router(liunian_enhanced_router, prefix="/api/v1", tags=["流年大运增强分析"])
    logger.info("✓ 流年大运增强分析路由已注册")
    logger.info("✓ 算法公式规则分析路由已注册")

if FORMULA_ANALYSIS_ROUTER_AVAILABLE and formula_analysis_router:
    app.include_router(formula_analysis_router, prefix="/api/v1", tags=["算法公式"])
    logger.info("✓ 算法公式分析路由已注册")

# 统一支付路由
if UNIFIED_PAYMENT_ROUTER_AVAILABLE and unified_payment_router:
    app.include_router(unified_payment_router, prefix="/api/v1", tags=["统一支付"])

# 注册模型微调路由（可选功能）
if MODEL_TUNING_ROUTER_AVAILABLE and model_tuning_router:
    app.include_router(model_tuning_router, prefix="/api/v1", tags=["模型微调"])
    logger.info("✓ 模型微调路由已注册")
    logger.info("✓ 统一支付路由已注册")

# 推送服务和数据分析路由已废弃，已删除

# 注册前端展示路由（新增，前端优化格式）
if BAZI_DISPLAY_ROUTER_AVAILABLE and bazi_display_router:
    app.include_router(bazi_display_router, prefix="/api/v1", tags=["前端展示"])

# 注册面相手相分析路由（新增）
try:
    from server.api.v1.fortune_analysis import router as fortune_analysis_router
    FORTUNE_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"面相手相分析路由导入失败（可选功能）: {e}")
    fortune_analysis_router = None
    FORTUNE_ANALYSIS_ROUTER_AVAILABLE = False

if FORTUNE_ANALYSIS_ROUTER_AVAILABLE and fortune_analysis_router:
    app.include_router(fortune_analysis_router, prefix="/api/v1", tags=["面相手相分析"])

# 注册流式分析路由
try:
    from server.api.v1.fortune_analysis_stream import router as fortune_analysis_stream_router
    FORTUNE_ANALYSIS_STREAM_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"面相手相分析流式路由导入失败（可选功能）: {e}")
    fortune_analysis_stream_router = None
    FORTUNE_ANALYSIS_STREAM_ROUTER_AVAILABLE = False

if FORTUNE_ANALYSIS_STREAM_ROUTER_AVAILABLE and fortune_analysis_stream_router:
    app.include_router(fortune_analysis_stream_router, prefix="/api/v1", tags=["面相手相分析（流式）"])

# 注册支付路由（新增，魔方西元）
if PAYMENT_ROUTER_AVAILABLE and payment_router:
    app.include_router(payment_router, prefix="/api/v1", tags=["支付"])

# 注册十神命格调试路由
try:
    from server.api.v1.shishen_debug import router as shishen_debug_router
    app.include_router(shishen_debug_router, prefix="/api/v1", tags=["十神命格调试"])
    logger.info("✓ 十神命格调试路由已注册")
except ImportError as e:
    logger.warning(f"十神命格调试路由导入失败: {e}")

# 注册智能运势分析路由（Intent Service）
try:
    from server.api.v1.smart_fortune import router as smart_fortune_router
    app.include_router(smart_fortune_router, prefix="/api/v1/smart-fortune", tags=["智能运势分析"])
    logger.info("✓ 智能运势分析路由已注册")
except ImportError as e:
    logger.warning(f"智能运势分析路由导入失败: {e}")

# 注册面相分析V2路由（独立系统）
if FACE_ANALYSIS_V2_ROUTER_AVAILABLE and face_analysis_v2_router:
    app.include_router(face_analysis_v2_router, tags=["面相分析V2"])
    logger.info("✓ 面相分析V2路由已注册")

# 注册办公桌风水分析路由
try:
    from server.api.v2.desk_fengshui_api import router as desk_fengshui_router
    app.include_router(desk_fengshui_router, tags=["办公桌风水"])
    logger.info("✓ 办公桌风水分析路由已注册")
except ImportError as e:
    logger.warning(f"办公桌风水分析路由导入失败: {e}")

# 注册服务治理路由
try:
    from server.api.v1.service_governance import router as governance_router
    app.include_router(governance_router, prefix="/api/v1", tags=["服务治理"])
    logger.info("✓ 服务治理路由已注册")
except ImportError as e:
    logger.warning(f"服务治理路由导入失败: {e}")

# 注册可观测性路由
try:
    from server.api.v1.observability import router as observability_router
    app.include_router(observability_router, prefix="/api/v1", tags=["可观测性"])
    logger.info("✓ 可观测性路由已注册")
except ImportError as e:
    logger.warning(f"可观测性路由导入失败: {e}")

# 挂载静态文件目录（本地前端文件）
local_frontend_dir = os.path.join(project_root, "local_frontend")
if os.path.exists(local_frontend_dir):
    app.mount("/local_frontend", StaticFiles(directory=local_frontend_dir, html=True), name="local_frontend")
    logger.info(f"✓ 本地前端目录已挂载: /local_frontend -> {local_frontend_dir}")
    # 同时挂载 /frontend 作为别名（兼容旧路径）
    app.mount("/frontend", StaticFiles(directory=local_frontend_dir, html=True), name="frontend")
    logger.info(f"✓ 前端目录别名已挂载: /frontend -> {local_frontend_dir}")
else:
    logger.warning(f"⚠ 本地前端目录不存在: {local_frontend_dir}")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "HiFateAPI服务",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    增强的健康检查接口
    检查系统资源和服务状态
    """
    import psutil
    import platform
    
    try:
        # 获取系统资源信息
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                }
            },
            "cache": {
                "status": "enabled"
            }
        }
        
        # 检查缓存状态
        try:
            from server.utils import bazi_cache
            health_data["cache"].update(bazi_cache.stats())
        except Exception as e:
            health_data["cache"]["status"] = f"error: {str(e)}"
        
        # 如果资源使用过高，返回警告状态
        if cpu_percent > 90 or memory.percent > 90:
            health_data["status"] = "warning"
            health_data["message"] = "系统资源使用率较高"
        
        return health_data
        
    except ImportError:
        # psutil 未安装时返回基础健康检查
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "message": "基础健康检查（psutil未安装，无法获取详细系统信息）"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# 健康检查别名（部署脚本使用）
@app.get("/api/v1/health")
async def health_check_api():
    """健康检查 API 别名"""
    return await health_check()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        workers=1  # 开发环境使用1个worker，生产环境可以增加
    )


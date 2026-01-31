#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口
# 2026-01-07: 触发 Docker 镜像重新构建（包含 pytz 依赖）
"""

import sys
import os
import time
import logging
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
import gzip
import io


class SSEAwareGZipMiddleware(BaseHTTPMiddleware):
    """
    自定义 GZip 中间件，对 SSE (text/event-stream) 响应禁用压缩。
    SSE 流需要实时传输数据，gzip 压缩会导致浏览器无法正确读取流。
    """
    def __init__(self, app, minimum_size: int = 1000):
        super().__init__(app)
        self.minimum_size = minimum_size
    
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        
        # 检查是否是 SSE 响应，如果是则跳过压缩
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return response
        
        # 检查响应头中是否已设置 Content-Encoding: identity
        if response.headers.get("content-encoding") == "identity":
            return response
        
        # 其他响应使用默认 GZip 压缩逻辑
        # 这里简化处理，不实现完整的 gzip 压缩
        # 交给 FastAPI 默认的 GZipMiddleware 处理
        return response
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

# 配置日志（必须在导入路由之前初始化，以便在导入失败时可以使用logger）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 优先加载 .env 文件（必须在导入其他模块之前）
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)  # override=True 确保覆盖已存在的环境变量
        logger.info(f"✓ 已加载环境变量文件: {env_path}")
        # 验证关键配置（从数据库读取）
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

# 新增：面相分析V2路由（独立系统）
try:
    from server.api.v2.face_analysis import router as face_analysis_v2_router
    FACE_ANALYSIS_V2_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"面相分析V2路由导入失败（可选功能）: {e}")
    face_analysis_v2_router = None
    FACE_ANALYSIS_V2_ROUTER_AVAILABLE = False

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

# 新增：日元-六十甲子路由
try:
    from server.api.v1.rizhu_liujiazi import router as rizhu_liujiazi_router
    RIZHU_LIUJIAZI_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"日元-六十甲子路由导入失败（可选功能）: {e}")
    rizhu_liujiazi_router = None
    RIZHU_LIUJIAZI_ROUTER_AVAILABLE = False

# 五行占比路由（条件可用）
try:
    from server.api.v1.wuxing_proportion import router as wuxing_proportion_router
    WUXING_PROPORTION_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"五行占比路由导入失败（可选功能）: {e}")
    wuxing_proportion_router = None
    WUXING_PROPORTION_ROUTER_AVAILABLE = False

# 喜神忌神路由（条件可用）
try:
    from server.api.v1.xishen_jishen import router as xishen_jishen_router
    XISHEN_JISHEN_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"喜神忌神路由导入失败（可选功能）: {e}")
    xishen_jishen_router = None
    XISHEN_JISHEN_ROUTER_AVAILABLE = False

# 感情婚姻分析路由（条件可用）
try:
    from server.api.v1.marriage_analysis import router as marriage_analysis_router
    MARRIAGE_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"感情婚姻分析路由导入失败（可选功能）: {e}")
    marriage_analysis_router = None
    MARRIAGE_ANALYSIS_ROUTER_AVAILABLE = False

# 事业财富分析路由（条件可用）
try:
    from server.api.v1.career_wealth_analysis import router as career_wealth_analysis_router
    CAREER_WEALTH_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"事业财富分析路由导入失败（可选功能）: {e}")
    career_wealth_analysis_router = None
    CAREER_WEALTH_ANALYSIS_ROUTER_AVAILABLE = False

# 子女学习分析路由（条件可用）
try:
    from server.api.v1.children_study_analysis import router as children_study_analysis_router
    CHILDREN_STUDY_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"子女学习分析路由导入失败（可选功能）: {e}")
    children_study_analysis_router = None
    CHILDREN_STUDY_ANALYSIS_ROUTER_AVAILABLE = False

# 身体健康分析路由（条件可用）
try:
    from server.api.v1.health_analysis import router as health_analysis_router
    HEALTH_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"身体健康分析路由导入失败（可选功能）: {e}")
    health_analysis_router = None
    HEALTH_ANALYSIS_ROUTER_AVAILABLE = False

# 总评分析路由（条件可用）
try:
    from server.api.v1.general_review_analysis import router as general_review_analysis_router
    GENERAL_REVIEW_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"总评分析路由导入失败（可选功能）: {e}")
    general_review_analysis_router = None
    GENERAL_REVIEW_ANALYSIS_ROUTER_AVAILABLE = False

# 年运报告路由（条件可用）
try:
    from server.api.v1.annual_report_analysis import router as annual_report_analysis_router
    ANNUAL_REPORT_ANALYSIS_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"年运报告路由导入失败（可选功能）: {e}")
    annual_report_analysis_router = None
    ANNUAL_REPORT_ANALYSIS_ROUTER_AVAILABLE = False

# 统一数据获取路由（新增，增量开发）
try:
    from server.api.v1.bazi_data import router as bazi_data_router
    BAZI_DATA_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"统一数据获取路由导入失败（可选功能）: {e}")
    bazi_data_router = None
    BAZI_DATA_ROUTER_AVAILABLE = False

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

# 新增：支付 Webhook 路由（Stripe Webhook等）
try:
    from server.api.v1.payment_webhook import router as payment_webhook_router
    PAYMENT_WEBHOOK_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"支付Webhook路由导入失败（可选功能）: {e}")
    payment_webhook_router = None
    PAYMENT_WEBHOOK_ROUTER_AVAILABLE = False

# 新增：支付区域配置管理路由
try:
    from server.api.v1.payment_region_config import router as payment_region_config_router
    PAYMENT_REGION_CONFIG_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"支付区域配置路由导入失败（可选功能）: {e}")
    payment_region_config_router = None
    PAYMENT_REGION_CONFIG_ROUTER_AVAILABLE = False

# 新增：支付白名单管理路由
try:
    from server.api.v1.payment_whitelist import router as payment_whitelist_router
    PAYMENT_WHITELIST_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"支付白名单路由导入失败（可选功能）: {e}")
    payment_whitelist_router = None
    PAYMENT_WHITELIST_ROUTER_AVAILABLE = False

# 新增：模型微调路由
try:
    from server.api.v1.model_tuning import router as model_tuning_router
    MODEL_TUNING_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"模型微调路由导入失败（可选功能）: {e}")
    model_tuning_router = None
    MODEL_TUNING_ROUTER_AVAILABLE = False

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
    
    # ⭐ 第一层防护：服务启动时强制注册所有端点（不依赖装饰器）
    try:
        from server.api.grpc_gateway import _ensure_endpoints_registered, SUPPORTED_ENDPOINTS
        _ensure_endpoints_registered()
        
        # 验证关键端点
        key_endpoints = ["/daily-fortune-calendar/query", "/bazi/interface", "/bazi/shengong-minggong", "/bazi/rizhu-liujiazi"]
        missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
        if missing:
            logger.error(f"🚨 服务启动后关键端点缺失: {missing}，当前端点数量: {len(SUPPORTED_ENDPOINTS)}")
            # 再次尝试注册
            _ensure_endpoints_registered()
            missing_after = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
            if missing_after:
                logger.critical(f"🚨🚨 服务启动后关键端点仍然缺失: {missing_after}，系统可能无法正常工作！")
            else:
                logger.info(f"✅ 关键端点已恢复（总端点数: {len(SUPPORTED_ENDPOINTS)}）")
        else:
            logger.info(f"✅ 所有关键端点已注册（总端点数: {len(SUPPORTED_ENDPOINTS)}）")
    except Exception as e:
        logger.critical(f"🚨🚨 端点注册失败: {e}", exc_info=True)
    
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
    
    # 启动缓存同步订阅器（双机缓存同步）
    try:
        from server.utils.cache_sync_subscriber import start_cache_sync_subscriber
        start_cache_sync_subscriber()
        logger.info("✓ 缓存同步订阅器已启动")
    except Exception as e:
        logger.warning(f"⚠ 缓存同步订阅器启动失败（单机模式）: {e}")
    
    # ✅ 性能优化：预热节气表缓存（服务启动时预计算常用年份）
    try:
        from datetime import datetime
        from core.calculators.bazi_calculator_docs import BaziCalculator as DocsBaziCalculator
        
        current_year = datetime.now().year
        # 预热当前年份前后各5年的节气表（共11年）
        warmup_years = list(range(current_year - 5, current_year + 6))
        
        # 使用一个临时计算器实例来预热缓存
        temp_calc = DocsBaziCalculator("2000-01-01", "12:00", "male")
        
        from lunar_python import Solar
        for year in warmup_years:
            if year not in DocsBaziCalculator._jieqi_table_cache:
                base_solar = Solar.fromYmdHms(year, 1, 1, 0, 0, 0)
                lunar_year = base_solar.getLunar()
                jieqi_table = lunar_year.getJieQiTable()
                DocsBaziCalculator._jieqi_table_cache[year] = jieqi_table
        
        logger.info(f"✓ 节气表缓存预热完成（{len(warmup_years)}年: {warmup_years[0]}-{warmup_years[-1]}）")
    except Exception as e:
        logger.warning(f"⚠ 节气表缓存预热失败（不影响正常使用）: {e}")

    # 启动时预热 API 缓存（每日运势 + 热门八字组合，后台执行不阻塞）
    try:
        import asyncio
        from server.utils.cache_warmer import warmup_on_startup
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, warmup_on_startup)
        logger.info("✓ 缓存预热任务已提交（后台执行）")
    except Exception as e:
        logger.warning(f"⚠ 缓存预热任务提交失败（不影响正常使用）: {e}")

    # 启动MySQL连接清理任务（定期清理空闲连接）
    try:
        import asyncio
        from server.config.mysql_config import cleanup_idle_mysql_connections
        
        async def connection_cleanup_task():
            """定期清理空闲MySQL连接（每60秒清理一次）"""
            while True:
                await asyncio.sleep(60)  # 每60秒清理一次
                try:
                    cleaned = cleanup_idle_mysql_connections(max_idle_time=300)
                    if cleaned > 0:
                        logger.info(f"✓ 清理了 {cleaned} 个空闲MySQL连接")
                except Exception as e:
                    logger.error(f"⚠ 清理MySQL连接失败: {e}")
        
        # 启动后台任务
        cleanup_task = asyncio.create_task(connection_cleanup_task())
        logger.info("✓ MySQL连接清理任务已启动（每60秒清理一次）")
    except Exception as e:
        logger.warning(f"⚠ MySQL连接清理任务启动失败: {e}")
    
    yield
    # 关闭时执行
    # 停止缓存同步订阅器
    try:
        from server.utils.cache_sync_subscriber import stop_cache_sync_subscriber
        stop_cache_sync_subscriber()
        logger.info("✓ 缓存同步订阅器已停止")
    except Exception as e:
        logger.warning(f"⚠ 缓存同步订阅器停止失败: {e}")
    
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
    
    # 停止告警管理器
    try:
        from server.observability.alert_manager import AlertManager
        alert_manager = AlertManager.get_instance()
        alert_manager.stop()
        logger.info("✓ 告警管理器已停止")
    except Exception as e:
        logger.warning(f"⚠ 告警管理器停止失败: {e}")
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

# 初始化路由管理器（支持热更新）
from server.utils.router_manager import RouterManager
router_manager = RouterManager(app)

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

# 添加GZip压缩中间件（SSE响应除外）
# 使用自定义中间件，对 text/event-stream 响应禁用压缩
app.add_middleware(SSEAwareGZipMiddleware, minimum_size=1000)

# 认证中间件已移除，所有接口无需认证即可访问

# ✅ 添加统一异常处理中间件（最后添加，确保能捕获所有异常）
try:
    from server.utils.exception_handler import ExceptionHandlerMiddleware
    app.add_middleware(ExceptionHandlerMiddleware)
    logger.info("✓ 统一异常处理中间件已启用")
except ImportError as e:
    logger.warning(f"⚠ 异常处理中间件导入失败（可选功能）: {e}")
except Exception as e:
    logger.warning(f"⚠ 异常处理中间件启用失败: {e}")

# ==================== 路由注册（支持热更新） ====================
# 使用 RouterManager 统一管理路由注册，支持热更新时重新注册

def _register_all_routers_to_manager():
    """将所有路由注册信息添加到 RouterManager"""
    
    # 基础路由（总是可用）
    router_manager.register_router(
        "bazi",
        lambda: bazi_router,
        prefix="/api/v1",
        tags=["八字计算"]
    )
    router_manager.register_router(
        "bazi_ai",
        lambda: bazi_ai_router,
        prefix="/api/v1",
        tags=["AI分析"]
    )
    router_manager.register_router(
        "grpc_gateway",
        lambda: grpc_gateway_router,
        prefix="/api",
        tags=["gRPC-Web"]
    )
    
    # 旺衰分析路由（条件可用）
    router_manager.register_router(
        "wangshuai",
        lambda: wangshuai_router,
        prefix="/api/v1",
        tags=["旺衰分析"],
        enabled_getter=lambda: WANGSHUAI_ROUTER_AVAILABLE and wangshuai_router is not None
    )
    
    # 面相手相路由（总是可用）
    router_manager.register_router(
        "mx_face",
        lambda: mx_face_router.router,
        prefix="/api/v1/mianxiang/analysis/face",
        tags=["面相分析"]
    )
    router_manager.register_router(
        "mx_hand",
        lambda: mx_hand_router.router,
        prefix="/api/v1/mianxiang/analysis/hand",
        tags=["手相分析"]
    )
    router_manager.register_router(
        "mx_bazi",
        lambda: mx_bazi_router.router,
        prefix="/api/v1/mianxiang/analysis/bazi",
        tags=["八字扩展分析"]
    )
    router_manager.register_router(
        "mx_fengshui",
        lambda: mx_fengshui_router.router,
        prefix="/api/v1/mianxiang/recommendations/fengshui",
        tags=["办公室摆件建议"]
    )
    
    # 规则匹配路由（条件可用）
    router_manager.register_router(
        "bazi_rules",
        lambda: bazi_rules_router,
        prefix="/api/v1",
        tags=["规则匹配"],
        enabled_getter=lambda: RULES_ROUTER_AVAILABLE and bazi_rules_router is not None
    )
    
    # 规则管理路由（条件可用）
    router_manager.register_router(
        "admin_rules",
        lambda: admin_rules_router,
        prefix="/api/v1",
        tags=["规则管理"],
        enabled_getter=lambda: ADMIN_RULES_ROUTER_AVAILABLE and admin_rules_router is not None
    )
    
    # 热更新路由（条件可用）
    router_manager.register_router(
        "hot_reload",
        lambda: hot_reload_router,
        prefix="/api/v1",
        tags=["热更新"],
        enabled_getter=lambda: HOT_RELOAD_ROUTER_AVAILABLE and hot_reload_router is not None
    )
    
    # 安全监控路由（可选）
    try:
        from server.api.v1.security_monitor import router as security_monitor_router
        router_manager.register_router(
            "security_monitor",
            lambda: security_monitor_router,
            prefix="/api/v1",
            tags=["安全监控"]
        )
        logger.info("✓ 安全监控路由已注册")
    except ImportError as e:
        logger.warning(f"⚠ 安全监控路由未注册（可选功能）: {e}")
    
    # Proto 文件服务路由（可选）
    try:
        from server.api.v1.proto_service import router as proto_service_router
        router_manager.register_router(
            "proto_service",
            lambda: proto_service_router,
            prefix="/api/v1",
            tags=["Proto 文件服务"]
        )
        logger.info("✓ Proto 文件服务路由已注册")
    except ImportError as e:
        logger.warning(f"⚠ Proto 文件服务路由未注册（可选功能）: {e}")
    
    # 首页内容管理路由（可选）
    try:
        from server.api.v1.homepage_content import router as homepage_content_router
        router_manager.register_router(
            "homepage_content",
            lambda: homepage_content_router,
            prefix="/api/v1",
            tags=["首页内容管理"]
        )
        logger.info("✓ 首页内容管理路由已注册")
    except ImportError as e:
        logger.warning(f"⚠ 首页内容管理路由未注册（可选功能）: {e}")
    
    # LLM 生成路由（条件可用）
    router_manager.register_router(
        "llm_generate",
        lambda: llm_generate_router,
        prefix="/api/v1",
        tags=["LLM生成"],
        enabled_getter=lambda: LLM_GENERATE_ROUTER_AVAILABLE and llm_generate_router is not None
    )
    
    # 对话路由（条件可用）
    router_manager.register_router(
        "chat",
        lambda: chat_router,
        prefix="/api/v1",
        tags=["AI对话"],
        enabled_getter=lambda: CHAT_ROUTER_AVAILABLE and chat_router is not None
    )
    
    # 今日运势路由（条件可用）
    # 运势API路由（条件可用）
    router_manager.register_router(
        "fortune_api",
        lambda: fortune_api_router,
        prefix="/api/v1",
        tags=["运势API"],
        enabled_getter=lambda: FORTUNE_API_ROUTER_AVAILABLE and fortune_api_router is not None
    )
    
    # 万年历API路由（条件可用）
    router_manager.register_router(
        "calendar_api",
        lambda: calendar_api_router,
        prefix="/api/v1",
        tags=["万年历API"],
        enabled_getter=lambda: CALENDAR_API_ROUTER_AVAILABLE and calendar_api_router is not None
    )
    
    # 每日运势日历路由（动态导入，条件可用）
    def get_daily_fortune_calendar_router():
        try:
            from server.api.v1.daily_fortune_calendar import router as daily_fortune_calendar_router
            return daily_fortune_calendar_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "daily_fortune_calendar",
        get_daily_fortune_calendar_router,
        prefix="/api/v1",
        tags=["每日运势日历"],
        enabled_getter=lambda: get_daily_fortune_calendar_router() is not None
    )
    
    # 算法公式分析路由（条件可用，注意有重复注册的情况）
    router_manager.register_router(
        "formula_analysis",
        lambda: formula_analysis_router,
        prefix="/api/v1",
        tags=["算法公式规则"],
        enabled_getter=lambda: FORMULA_ANALYSIS_ROUTER_AVAILABLE and formula_analysis_router is not None
    )
    
    # 五行占比路由（条件可用）
    router_manager.register_router(
        "wuxing_proportion",
        lambda: wuxing_proportion_router,
        prefix="/api/v1",
        tags=["五行占比"],
        enabled_getter=lambda: WUXING_PROPORTION_ROUTER_AVAILABLE and wuxing_proportion_router is not None
    )
    
    # 喜神忌神路由（条件可用）
    router_manager.register_router(
        "xishen_jishen",
        lambda: xishen_jishen_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: XISHEN_JISHEN_ROUTER_AVAILABLE and xishen_jishen_router is not None
    )
    
    # 感情婚姻分析路由（条件可用）
    router_manager.register_router(
        "marriage_analysis",
        lambda: marriage_analysis_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: MARRIAGE_ANALYSIS_ROUTER_AVAILABLE and marriage_analysis_router is not None
    )
    
    # 事业财富分析路由（条件可用）
    router_manager.register_router(
        "career_wealth_analysis",
        lambda: career_wealth_analysis_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: CAREER_WEALTH_ANALYSIS_ROUTER_AVAILABLE and career_wealth_analysis_router is not None
    )
    
    # 子女学习分析路由（条件可用）
    router_manager.register_router(
        "children_study_analysis",
        lambda: children_study_analysis_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: CHILDREN_STUDY_ANALYSIS_ROUTER_AVAILABLE and children_study_analysis_router is not None
    )
    
    # 身体健康分析路由（条件可用）
    router_manager.register_router(
        "health_analysis",
        lambda: health_analysis_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: HEALTH_ANALYSIS_ROUTER_AVAILABLE and health_analysis_router is not None
    )
    
    # 总评分析路由（条件可用）
    router_manager.register_router(
        "general_review_analysis",
        lambda: general_review_analysis_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: GENERAL_REVIEW_ANALYSIS_ROUTER_AVAILABLE and general_review_analysis_router is not None
    )
    
    # 年运报告路由（条件可用）
    router_manager.register_router(
        "annual_report_analysis",
        lambda: annual_report_analysis_router,
        prefix="/api/v1",
        tags=["八字命理"],
        enabled_getter=lambda: ANNUAL_REPORT_ANALYSIS_ROUTER_AVAILABLE and annual_report_analysis_router is not None
    )
    
    # 用户反馈路由（条件可用）
    router_manager.register_router(
        "feedback",
        lambda: feedback_router,
        prefix="/api/v1",
        tags=["用户反馈"],
        enabled_getter=lambda: FEEDBACK_ROUTER_AVAILABLE and feedback_router is not None
    )
    
    # 统一支付路由（条件可用）
    router_manager.register_router(
        "unified_payment",
        lambda: unified_payment_router,
        prefix="/api/v1",
        tags=["统一支付"],
        enabled_getter=lambda: UNIFIED_PAYMENT_ROUTER_AVAILABLE and unified_payment_router is not None
    )
    
    # 支付 Webhook 路由（条件可用）
    router_manager.register_router(
        "payment_webhook",
        lambda: payment_webhook_router,
        prefix="/api/v1",
        tags=["支付Webhook"],
        enabled_getter=lambda: PAYMENT_WEBHOOK_ROUTER_AVAILABLE and payment_webhook_router is not None
    )
    
    # 支付区域配置管理路由
    router_manager.register_router(
        "payment_region_config",
        lambda: payment_region_config_router,
        prefix="/api/v1",
        tags=["支付区域配置"],
        enabled_getter=lambda: PAYMENT_REGION_CONFIG_ROUTER_AVAILABLE and payment_region_config_router is not None
    )
    
    # 支付白名单管理路由
    router_manager.register_router(
        "payment_whitelist",
        lambda: payment_whitelist_router,
        prefix="/api/v1",
        tags=["支付白名单"],
        enabled_getter=lambda: PAYMENT_WHITELIST_ROUTER_AVAILABLE and payment_whitelist_router is not None
    )
    
    # 模型微调路由（条件可用）
    router_manager.register_router(
        "model_tuning",
        lambda: model_tuning_router,
        prefix="/api/v1",
        tags=["模型微调"],
        enabled_getter=lambda: MODEL_TUNING_ROUTER_AVAILABLE and model_tuning_router is not None
    )
    
    # 前端展示路由（条件可用）
    router_manager.register_router(
        "bazi_display",
        lambda: bazi_display_router,
        prefix="/api/v1",
        tags=["前端展示"],
        enabled_getter=lambda: BAZI_DISPLAY_ROUTER_AVAILABLE and bazi_display_router is not None
    )
    
    # 流式分析路由（动态导入，条件可用）
    def get_fortune_analysis_stream_router():
        try:
            from server.api.v1.fortune_analysis_stream import router as fortune_analysis_stream_router
            return fortune_analysis_stream_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "fortune_analysis_stream",
        get_fortune_analysis_stream_router,
        prefix="/api/v1",
        tags=["面相手相分析（流式）"],
        enabled_getter=lambda: get_fortune_analysis_stream_router() is not None
    )
    
    # 支付路由（条件可用）
    router_manager.register_router(
        "payment",
        lambda: payment_router,
        prefix="/api/v1",
        tags=["支付"],
        enabled_getter=lambda: PAYMENT_ROUTER_AVAILABLE and payment_router is not None
    )
    
    # 十神命格调试路由（动态导入）
    def get_shishen_debug_router():
        try:
            from server.api.v1.shishen_debug import router as shishen_debug_router
            return shishen_debug_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "shishen_debug",
        get_shishen_debug_router,
        prefix="/api/v1",
        tags=["十神命格调试"],
        enabled_getter=lambda: get_shishen_debug_router() is not None
    )
    
    # 智能运势分析路由（动态导入）
    def get_smart_fortune_router():
        try:
            from server.api.v1.smart_fortune import router as smart_fortune_router
            return smart_fortune_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "smart_fortune",
        get_smart_fortune_router,
        prefix="/api/v1/smart-fortune",
        tags=["智能运势分析"],
        enabled_getter=lambda: get_smart_fortune_router() is not None
    )
    
    # 面相分析V2路由（条件可用）
    router_manager.register_router(
        "face_analysis_v2",
        lambda: face_analysis_v2_router,
        prefix="",
        tags=["面相分析V2"],
        enabled_getter=lambda: FACE_ANALYSIS_V2_ROUTER_AVAILABLE and face_analysis_v2_router is not None
    )
    
    # 办公桌风水分析路由（动态导入）
    def get_desk_fengshui_router():
        try:
            from server.api.v2.desk_fengshui_api import router as desk_fengshui_router
            return desk_fengshui_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "desk_fengshui",
        get_desk_fengshui_router,
        prefix="",
        tags=["办公桌风水"],
        enabled_getter=lambda: get_desk_fengshui_router() is not None
    )
    
    # 服务治理路由（动态导入）
    def get_governance_router():
        try:
            from server.api.v1.service_governance import router as governance_router
            return governance_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "governance",
        get_governance_router,
        prefix="/api/v1",
        tags=["服务治理"],
        enabled_getter=lambda: get_governance_router() is not None
    )
    
    # 可观测性路由（动态导入）
    def get_observability_router():
        try:
            from server.api.v1.observability import router as observability_router
            return observability_router
        except ImportError:
            return None
    
    router_manager.register_router(
        "observability",
        get_observability_router,
        prefix="/api/v1",
        tags=["可观测性"],
        enabled_getter=lambda: get_observability_router() is not None
    )
    
    # 日元-六十甲子路由（条件可用）
    router_manager.register_router(
        "rizhu_liujiazi",
        lambda: rizhu_liujiazi_router,
        prefix="/api/v1",
        tags=["日元-六十甲子"],
        enabled_getter=lambda: RIZHU_LIUJIAZI_ROUTER_AVAILABLE and rizhu_liujiazi_router is not None
    )
    
    # 统一数据获取路由（新增，增量开发）
    router_manager.register_router(
        "bazi_data",
        lambda: bazi_data_router,
        prefix="/api/v1",
        tags=["统一数据获取"],
        enabled_getter=lambda: BAZI_DATA_ROUTER_AVAILABLE and bazi_data_router is not None
    )


# 注册所有路由信息到管理器
_register_all_routers_to_manager()

# 实际注册所有路由到 FastAPI 应用
router_manager.register_all_routers()

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
        
        # 检查MySQL连接池状态
        try:
            from server.config.mysql_config import get_connection_pool_stats
            health_data["mysql_pool"] = get_connection_pool_stats()
        except Exception as e:
            health_data["mysql_pool"] = {
                "status": "error",
                "error": str(e)
            }
        
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


# 生产诊断：流式问题排查用，立即返回，不经过流式逻辑
@app.get("/api/v1/diagnose-stream")
async def diagnose_stream():
    """
    流式问题诊断端点：立即返回 JSON，用于区分「直连 8001 可达」与「经 Nginx 无响应」。
    不写业务逻辑，仅返回当前环境信息。
    """
    return {
        "ok": True,
        "endpoint": "diagnose-stream",
        "message": "stream diagnostic endpoint reachable",
        "timestamp": time.time(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        workers=1  # 开发环境使用1个worker，生产环境可以增加
    )


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路由注册（从 main.py 提取）"""

import logging

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
from server.api.grpc_gateway import router as grpc_gateway_router

# [DEPRECATED] v1 支付路由已下线，统一走 unified_payment。
# 保留注释供追溯，下个版本可删除。

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


def _register_all_routers_to_manager(router_manager):
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
    
    # [DEPRECATED] v1 支付路由已下线，统一走 unified_payment。
    
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


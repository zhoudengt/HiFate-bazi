# -*- coding: utf-8 -*-
"""
Intent Service 配置
"""
import os
import sys
from typing import Optional

# 添加项目根目录到路径（用于导入配置加载器）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 9008))
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

# Coze API 配置（只从数据库读取，不降级到环境变量）
COZE_ACCESS_TOKEN = get_config_from_db_only("COZE_ACCESS_TOKEN")
if not COZE_ACCESS_TOKEN:
    raise ValueError("数据库配置缺失: COZE_ACCESS_TOKEN，请在 service_configs 表中配置")

INTENT_BOT_ID = get_config_from_db_only("INTENT_BOT_ID")
if not INTENT_BOT_ID:
    raise ValueError("数据库配置缺失: INTENT_BOT_ID，请在 service_configs 表中配置")

# Prompt 版本管理
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1.0")

# Redis 缓存配置
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 16379))
REDIS_DB = 3  # 使用DB3专门存储意图识别缓存
REDIS_CACHE_TTL = int(os.getenv("PROMPT_CACHE_TTL", "3600"))

# MySQL 配置（用于存储Prompt版本历史）
# ⚠️ 安全规范：密码必须通过环境变量配置，不允许硬编码
MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "localhost"),
    'port': int(os.getenv("MYSQL_PORT", 3306)),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", "")),
    'database': os.getenv("MYSQL_DATABASE", "bazi_system"),
    'charset': 'utf8mb4',
    'use_unicode': True
}

# 意图分类配置
INTENT_CATEGORIES = {
    "career": "事业运势",
    "wealth": "财富运势",
    "marriage": "婚姻感情",
    "health": "健康运势",
    "personality": "性格特点",
    "wangshui": "命局旺衰",
    "yongji": "喜忌用神",
    "shishen": "十神分析",
    "nayin": "纳音分析",
    "general": "综合分析"
}

# 规则类型映射
INTENT_TO_RULE_TYPE_MAP = {
    "career": "FORMULA_CAREER",
    "wealth": "FORMULA_WEALTH",
    "marriage": "FORMULA_MARRIAGE",
    "health": "FORMULA_HEALTH",
    "personality": "FORMULA_CHARACTER",
    "wangshui": "WANGSHUI",
    "yongji": "YONGJI",
    "shishen": "SHISHEN",
    "nayin": "NAYIN",
    "general": "ALL"
}

# 日志配置
LOG_FILE = "logs/intent_service.log"
LOG_LEVEL = "INFO"

# 混合架构配置
HYBRID_ARCHITECTURE_ENABLED = os.getenv("HYBRID_ARCHITECTURE_ENABLED", "true").lower() == "true"
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "hfl/chinese-roberta-wwm-ext")
LLM_FALLBACK_THRESHOLD = float(os.getenv("LLM_FALLBACK_THRESHOLD", "0.6"))  # 置信度阈值


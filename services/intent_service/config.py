# -*- coding: utf-8 -*-
"""
Intent Service 配置
"""
import os

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 9008))
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

# Coze API 配置
COZE_ACCESS_TOKEN = os.getenv("COZE_ACCESS_TOKEN", "")
INTENT_BOT_ID = os.getenv("INTENT_BOT_ID", "PLACEHOLDER_INTENT_BOT_ID")

# Prompt 版本管理
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1.0")

# Redis 缓存配置
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 16379))
REDIS_DB = 3  # 使用DB3专门存储意图识别缓存
REDIS_CACHE_TTL = int(os.getenv("PROMPT_CACHE_TTL", "3600"))

# MySQL 配置（用于存储Prompt版本历史）
MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "127.0.0.1"),
    'port': int(os.getenv("MYSQL_PORT", 13306)),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", "root123"),
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


# -*- coding: utf-8 -*-
"""
Prompt Optimizer 配置
"""
import os

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 9009))
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

# MongoDB 配置（存储反馈和报告）
MONGO_HOST = "127.0.0.1"
MONGO_PORT = 27017
MONGO_DB = "bazi_feedback"
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")

# MySQL 配置（Prompt版本管理）
MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "127.0.0.1"),
    'port': int(os.getenv("MYSQL_PORT", 13306)),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", "root123"),
    'database': os.getenv("MYSQL_DATABASE", "bazi_system"),
    'charset': 'utf8mb4',
    'use_unicode': True
}

# Coze API 配置（用于生成优化建议）
COZE_ACCESS_TOKEN = os.getenv("COZE_ACCESS_TOKEN", "")
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "")

# 优化策略配置
ACCURACY_THRESHOLD = 0.95  # 目标准确率
MIN_SAMPLES_FOR_OPTIMIZATION = 100  # 最少样本数
OPTIMIZATION_INTERVAL_DAYS = 7  # 优化周期（天）
AB_TEST_TRAFFIC_PERCENTAGE = 0.2  # A/B测试流量百分比

# 日志配置
LOG_FILE = "logs/prompt_optimizer.log"
LOG_LEVEL = "INFO"


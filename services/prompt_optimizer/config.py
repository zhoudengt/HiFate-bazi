# -*- coding: utf-8 -*-
"""
Prompt Optimizer 配置
"""
import os
import logging

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 9009))
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

# 判断环境（本地开发 or 生产）
env_value = os.getenv("ENV", os.getenv("APP_ENV", "local")).lower()
is_local_dev = env_value in ["local", "development"]

# ============================================================
# MongoDB 配置（存储反馈和报告）
# ⚠️ 安全规范：生产环境必须通过 MONGO_HOST 环境变量指定，禁止硬编码 IP
# ============================================================
if is_local_dev:
    MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
else:
    MONGO_HOST = os.getenv("MONGO_HOST", "")
    if not MONGO_HOST:
        logging.getLogger(__name__).error("❌ 生产环境必须配置 MONGO_HOST 环境变量")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "bazi_feedback")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")

# ============================================================
# MySQL 配置（Prompt版本管理）
# ⚠️ 安全规范：密码和主机地址必须通过环境变量配置，禁止硬编码
# ============================================================
if is_local_dev:
    DEFAULT_MYSQL_HOST = "localhost"
else:
    DEFAULT_MYSQL_HOST = os.getenv("MYSQL_HOST", "")
    if not DEFAULT_MYSQL_HOST:
        logging.getLogger(__name__).error("❌ 生产环境必须配置 MYSQL_HOST 环境变量")
DEFAULT_MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))

MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", DEFAULT_MYSQL_HOST),
    'port': int(os.getenv("MYSQL_PORT", "3306")),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", DEFAULT_MYSQL_PASSWORD),
    'database': os.getenv("MYSQL_DATABASE", "hifate_bazi"),
    'charset': 'utf8mb4',
    'use_unicode': True
}

# Coze API 配置（用于生成优化建议，只从数据库读取）
try:
    from shared.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str):
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")

COZE_ACCESS_TOKEN = get_config_from_db_only("COZE_ACCESS_TOKEN")
if not COZE_ACCESS_TOKEN:
    raise ValueError("数据库配置缺失: COZE_ACCESS_TOKEN，请在 service_configs 表中配置")

COZE_BOT_ID = get_config_from_db_only("COZE_BOT_ID")
if not COZE_BOT_ID:
    raise ValueError("数据库配置缺失: COZE_BOT_ID，请在 service_configs 表中配置")

# 优化策略配置
ACCURACY_THRESHOLD = 0.95  # 目标准确率
MIN_SAMPLES_FOR_OPTIMIZATION = 100  # 最少样本数
OPTIMIZATION_INTERVAL_DAYS = 7  # 优化周期（天）
AB_TEST_TRAFFIC_PERCENTAGE = 0.2  # A/B测试流量百分比

# 日志配置
LOG_FILE = "logs/prompt_optimizer.log"
LOG_LEVEL = "INFO"

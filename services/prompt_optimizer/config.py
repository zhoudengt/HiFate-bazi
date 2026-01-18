# -*- coding: utf-8 -*-
"""
Prompt Optimizer 配置
"""
import os

# 服务配置
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 9009))
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")

# MongoDB 配置（存储反馈和报告）
# ⚠️ 重要：所有环境统一连接生产Node1 Docker MongoDB，确保数据一致性
# 生产Node1 Docker MongoDB: 8.210.52.217:27017 (公网) / 172.18.121.222:27017 (内网)
MONGO_HOST = os.getenv("MONGO_HOST", "8.210.52.217")  # 默认连接生产Node1公网IP
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "bazi_feedback")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")

# MySQL 配置（Prompt版本管理）
# ⚠️ 重要：根据环境自动选择默认配置
# 本地开发：localhost:3306，密码: 123456
# 生产环境：8.210.52.217:3306 (公网) / 172.18.121.222:3306 (内网)，密码: Yuanqizhan@163
# 判断环境（本地开发 or 生产）
env_value = os.getenv("ENV", os.getenv("APP_ENV", "local")).lower()
is_local_dev = env_value in ["local", "development"]

# 根据环境设置默认值
# ⚠️ 安全规范：密码必须通过环境变量配置，不允许硬编码
if is_local_dev:
    # 本地开发：使用本地MySQL
    DEFAULT_MYSQL_HOST = "localhost"
    DEFAULT_MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))
else:
    # 生产环境：使用生产MySQL
    DEFAULT_MYSQL_HOST = "8.210.52.217"  # 生产Node1公网IP
    DEFAULT_MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))

MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", DEFAULT_MYSQL_HOST),
    'port': int(os.getenv("MYSQL_PORT", "3306")),  # 默认使用标准端口
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


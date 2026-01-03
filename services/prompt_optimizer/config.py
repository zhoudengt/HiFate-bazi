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
# ⚠️ 重要：所有环境统一连接生产Node1 Docker MySQL，确保数据一致性
# 生产Node1 Docker MySQL: 8.210.52.217:3306 (公网) / 172.18.121.222:3306 (内网)
MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "8.210.52.217"),  # 默认连接生产Node1公网IP
    'port': int(os.getenv("MYSQL_PORT", "3306")),  # 默认使用标准端口
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", "Yuanqizhan@163"),  # 默认使用生产密码
    'database': os.getenv("MYSQL_DATABASE", "hifate_bazi"),  # 默认使用生产数据库
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


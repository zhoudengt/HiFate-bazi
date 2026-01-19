#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置模块 - 支持本地开发和生产环境
本地开发连接本地MySQL，生产环境连接Node1内网IP
"""

import os
import logging

logger = logging.getLogger(__name__)

# 判断环境（本地开发 or 生产）
# 通过环境变量 ENV 判断，local 表示本地开发，其他表示生产环境
# 使用统一环境配置
from server.config.env_config import is_local_dev
IS_LOCAL_DEV = is_local_dev()

# MySQL配置
# ⚠️ 安全规范：密码必须通过环境变量配置，不允许硬编码
if IS_LOCAL_DEV:
    # 本地开发：连接本地MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    DEFAULT_MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))
    logger.info(f"[DatabaseConfig] 本地开发模式：MySQL连接 {MYSQL_HOST}")
else:
    # 生产环境：连接Node1内网IP
    MYSQL_HOST = os.getenv("MYSQL_HOST", "172.18.121.222")
    DEFAULT_MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", ""))
    logger.info(f"[DatabaseConfig] 生产环境模式：MySQL连接 {MYSQL_HOST}")

MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", DEFAULT_MYSQL_PASSWORD))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "hifate_bazi")

# MongoDB配置
if IS_LOCAL_DEV:
    # 本地开发：连接Node1公网IP
    MONGO_HOST = os.getenv("MONGO_HOST", "8.210.52.217")
    logger.info(f"[DatabaseConfig] 本地开发模式：MongoDB连接 {MONGO_HOST}")
else:
    # 生产环境：连接Node1内网IP
    MONGO_HOST = os.getenv("MONGO_HOST", "172.18.121.222")
    logger.info(f"[DatabaseConfig] 生产环境模式：MongoDB连接 {MONGO_HOST}")

MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USER = os.getenv("MONGO_USER", "admin")
# ⚠️ 安全规范：密码必须通过环境变量配置，不允许硬编码
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "hifate_interactions")

# MongoDB连接字符串
MONGO_CONNECTION_STRING = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DATABASE}?authSource=admin"

# 导出配置字典（方便使用）
MYSQL_CONFIG = {
    'host': MYSQL_HOST,
    'port': MYSQL_PORT,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DATABASE,
    'charset': 'utf8mb4',
    'use_unicode': True
}

MONGO_CONFIG = {
    'host': MONGO_HOST,
    'port': MONGO_PORT,
    'user': MONGO_USER,
    'password': MONGO_PASSWORD,
    'database': MONGO_DATABASE,
    'connection_string': MONGO_CONNECTION_STRING
}


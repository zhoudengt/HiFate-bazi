# -*- coding: utf-8 -*-
"""
Intent Service 日志管理
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from services.intent_service.config import LOG_FILE, LOG_LEVEL

def setup_logger(name="intent_service"):
    """设置日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 确保日志目录存在
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 文件处理器（带自动滚动）
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 全局日志器
logger = setup_logger()


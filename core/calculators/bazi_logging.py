#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算模块共享日志工具

提供安全的日志输出函数，捕获 Broken pipe 等异常。
供 bazi_calculator.py 及其 mixin 模块共用。
"""

import logging


class SafeStreamHandler(logging.StreamHandler):
    """安全的 StreamHandler，捕获 Broken pipe 异常"""
    def emit(self, record):
        try:
            super().emit(record)
        except (BrokenPipeError, OSError):
            pass


logger = logging.getLogger("core.calculators.bazi_calculator")
if not logger.handlers:
    handler = SafeStreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def safe_log(level, message):
    """
    安全的日志输出函数，捕获 Broken pipe 等异常
    在 Web 服务环境中，客户端断开连接时可能触发 Broken pipe 错误
    """
    try:
        if level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)
        elif level == 'debug':
            logger.debug(message)
        else:
            logger.info(message)
    except (BrokenPipeError, OSError):
        pass

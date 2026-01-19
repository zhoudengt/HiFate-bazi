#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步执行器工具 - 统一管理线程池执行器

提供统一的线程池管理，避免每个API文件重复创建执行器
"""

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)

# 全局线程池执行器（单例）
_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = None


def get_executor() -> ThreadPoolExecutor:
    """
    获取全局线程池执行器（单例模式）
    
    根据CPU核心数动态调整线程池大小：
    - 本地开发：CPU核心数 * 2，最大16
    - 生产环境：CPU核心数 * 2，最大100
    
    Returns:
        ThreadPoolExecutor: 线程池执行器实例
    """
    global _executor, _executor_lock
    
    if _executor_lock is None:
        import threading
        _executor_lock = threading.Lock()
    
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                cpu_count = os.cpu_count() or 4
                
                # 根据环境调整线程池大小
                try:
                    from server.config.env_config import get_env_config
                    env_config = get_env_config()
                    if env_config.is_local_dev:
                        max_workers = min(cpu_count * 2, 16)  # 本地开发：较小线程池
                    else:
                        max_workers = min(cpu_count * 2, 100)  # 生产环境：较大线程池
                except Exception:
                    # 如果环境配置不可用，使用默认值
                    max_workers = min(cpu_count * 2, 100)
                
                _executor = ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="async_executor"
                )
                logger.info(f"✓ 全局线程池执行器已创建 (max_workers={max_workers})")
    
    return _executor


async def run_in_executor(func: Callable, *args, **kwargs) -> Any:
    """
    在线程池中执行同步函数（便捷函数）
    
    Args:
        func: 要执行的同步函数
        *args: 位置参数
        **kwargs: 关键字参数
    
    Returns:
        函数执行结果
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))


def shutdown_executor():
    """
    关闭线程池执行器（用于优雅关闭）
    """
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None
        logger.info("✓ 全局线程池执行器已关闭")

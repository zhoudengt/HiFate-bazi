#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存版本管理器

功能：
- 为缓存 key 添加版本前缀
- 支持按模式失效缓存
- 支持全局版本控制

使用方式：
    from server.utils.cache_version_manager import CacheVersionManager
    
    # 获取带版本的缓存 key
    cache_key = CacheVersionManager.get_versioned_key("bazi:user:123")
    
    # 失效缓存
    CacheVersionManager.invalidate_by_pattern("bazi:rule:*")
    
    # 全局版本更新
    CacheVersionManager.bump_version()
"""

import os
import logging
from typing import Optional, List, Pattern
import re

logger = logging.getLogger(__name__)


class CacheVersionManager:
    """
    缓存版本管理器（可选启用）
    
    默认不启用，启用后可以为缓存 key 添加版本前缀，实现缓存版本控制。
    """
    
    _instance: Optional['CacheVersionManager'] = None
    _lock = None
    
    def __init__(self):
        """初始化缓存版本管理器"""
        import threading
        self._lock = threading.Lock()
        
        # 检查是否启用（默认关闭）
        self._enabled = os.getenv("ENABLE_CACHE_VERSION", "false").lower() == "true"
        
        # 当前版本号
        self._version = os.getenv("CACHE_VERSION", "v1")
        
        # Redis 客户端（如果需要失效缓存）
        self._redis_client = None
        
        if self._enabled:
            try:
                # 尝试获取 Redis 客户端
                from server.config.redis_config import get_redis_client
                self._redis_client = get_redis_client()
                logger.info(f"缓存版本管理器已启用，当前版本: {self._version}")
            except Exception as e:
                logger.warning(f"无法获取 Redis 客户端: {e}，缓存失效功能可能不可用")
        else:
            logger.debug("缓存版本管理器已禁用")
    
    @classmethod
    def get_instance(cls) -> 'CacheVersionManager':
        """获取单例实例"""
        if cls._instance is None:
            import threading
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @staticmethod
    def get_versioned_key(key: str) -> str:
        """
        获取带版本的缓存 key
        
        Args:
            key: 原始缓存 key
            
        Returns:
            带版本的缓存 key（如果启用版本控制），否则返回原始 key
        """
        manager = CacheVersionManager.get_instance()
        
        if not manager._enabled:
            return key
        
        # 如果 key 已经包含版本，直接返回
        if key.startswith(f"{manager._version}:"):
            return key
        
        # 添加版本前缀
        return f"{manager._version}:{key}"
    
    @staticmethod
    def get_version() -> str:
        """获取当前缓存版本"""
        manager = CacheVersionManager.get_instance()
        return manager._version if manager._enabled else "none"
    
    @staticmethod
    def invalidate_by_pattern(pattern: str) -> int:
        """
        按模式失效缓存
        
        Args:
            pattern: 缓存 key 模式（支持通配符 * 和 ?）
            
        Returns:
            失效的缓存 key 数量
        """
        manager = CacheVersionManager.get_instance()
        
        if not manager._enabled:
            logger.warning("缓存版本控制未启用，无法失效缓存")
            return 0
        
        if not manager._redis_client:
            logger.warning("Redis 客户端不可用，无法失效缓存")
            return 0
        
        try:
            # 将模式转换为 Redis 模式
            # 如果模式不包含版本前缀，添加当前版本
            if not pattern.startswith(manager._version + ":"):
                pattern = f"{manager._version}:{pattern}"
            
            # 转换为 Redis 模式（* -> *, ? -> ?）
            redis_pattern = pattern.replace("*", "*").replace("?", "?")
            
            # 查找匹配的 key
            keys = []
            cursor = 0
            while True:
                cursor, batch_keys = manager._redis_client.scan(
                    cursor=cursor,
                    match=redis_pattern,
                    count=1000
                )
                keys.extend(batch_keys)
                if cursor == 0:
                    break
            
            # 删除匹配的 key
            if keys:
                deleted = manager._redis_client.delete(*keys)
                logger.info(f"缓存失效: {len(keys)} 个 key 匹配 {pattern}，已删除 {deleted} 个")
                return deleted
            else:
                logger.debug(f"缓存失效: 没有 key 匹配 {pattern}")
                return 0
                
        except Exception as e:
            logger.error(f"失效缓存失败: {e}")
            return 0
    
    @staticmethod
    def invalidate_by_key(key: str) -> bool:
        """
        失效指定的缓存 key
        
        Args:
            key: 缓存 key（会自动添加版本前缀）
            
        Returns:
            是否成功删除
        """
        manager = CacheVersionManager.get_instance()
        
        if not manager._enabled:
            return False
        
        if not manager._redis_client:
            return False
        
        try:
            versioned_key = CacheVersionManager.get_versioned_key(key)
            deleted = manager._redis_client.delete(versioned_key)
            return deleted > 0
        except Exception as e:
            logger.error(f"失效缓存 key 失败: {e}")
            return False
    
    @staticmethod
    def bump_version() -> str:
        """
        增加版本号（全局失效）
        
        注意：这会使得所有旧版本的缓存失效
        
        Returns:
            新版本号
        """
        manager = CacheVersionManager.get_instance()
        
        if not manager._enabled:
            logger.warning("缓存版本控制未启用，无法更新版本")
            return manager._version
        
        # 计算新版本号
        if manager._version.startswith("v"):
            try:
                version_num = int(manager._version[1:])
                new_version = f"v{version_num + 1}"
            except ValueError:
                new_version = "v2"
        else:
            new_version = "v2"
        
        with manager._lock:
            old_version = manager._version
            manager._version = new_version
        
        logger.warning(f"缓存版本更新: {old_version} -> {new_version}，所有旧版本缓存将失效")
        
        # 更新环境变量（如果可能）
        os.environ["CACHE_VERSION"] = new_version
        
        return new_version
    
    @staticmethod
    def set_version(version: str):
        """
        设置版本号
        
        Args:
            version: 版本号（如 "v1", "v2"）
        """
        manager = CacheVersionManager.get_instance()
        
        with manager._lock:
            old_version = manager._version
            manager._version = version
        
        logger.info(f"缓存版本设置: {old_version} -> {version}")
        os.environ["CACHE_VERSION"] = version
    
    @staticmethod
    def is_enabled() -> bool:
        """检查是否启用缓存版本控制"""
        manager = CacheVersionManager.get_instance()
        return manager._enabled


# 便捷函数
def get_versioned_key(key: str) -> str:
    """获取带版本的缓存 key"""
    return CacheVersionManager.get_versioned_key(key)


def invalidate_cache(pattern: str) -> int:
    """按模式失效缓存"""
    return CacheVersionManager.invalidate_by_pattern(pattern)


def invalidate_cache_key(key: str) -> bool:
    """失效指定的缓存 key"""
    return CacheVersionManager.invalidate_by_key(key)


def bump_cache_version() -> str:
    """增加缓存版本号"""
    return CacheVersionManager.bump_version()

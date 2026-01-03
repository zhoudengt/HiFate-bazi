#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字缓存服务 - 统一管理八字数据的缓存读写
支持分层缓存（Level 0/1/2）和分布式锁
"""

import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaziCacheService:
    """八字缓存服务 - 统一管理缓存读写"""
    
    # 缓存 TTL（秒）
    TTL_BASE = 2592000  # 30天 - 基础八字
    TTL_DAYUN = 2592000  # 30天 - 单个大运
    TTL_FULL = 2592000  # 30天 - 完整数据
    TTL_READY = 2592000  # 30天 - 就绪标志
    
    # 分布式锁超时时间（秒）
    LOCK_TIMEOUT = 300  # 5分钟
    
    @staticmethod
    def _generate_hash(solar_date: str, solar_time: str, gender: str) -> str:
        """
        生成缓存键的哈希值
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
        
        Returns:
            MD5 哈希值（32位）
        """
        key_str = f"{solar_date}:{solar_time}:{gender}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    @staticmethod
    def get_base_key(solar_date: str, solar_time: str, gender: str) -> str:
        """获取基础八字缓存键"""
        hash_val = BaziCacheService._generate_hash(solar_date, solar_time, gender)
        return f"bazi:base:{hash_val}"
    
    @staticmethod
    def get_dayun_key(solar_date: str, solar_time: str, gender: str, dayun_index: int) -> str:
        """获取单个大运缓存键"""
        hash_val = BaziCacheService._generate_hash(solar_date, solar_time, gender)
        return f"bazi:dayun:{hash_val}:{dayun_index}"
    
    @staticmethod
    def get_full_key(solar_date: str, solar_time: str, gender: str) -> str:
        """获取完整数据缓存键"""
        hash_val = BaziCacheService._generate_hash(solar_date, solar_time, gender)
        return f"bazi:full:{hash_val}"
    
    @staticmethod
    def get_ready_key(solar_date: str, solar_time: str, gender: str) -> str:
        """获取数据就绪标志键"""
        hash_val = BaziCacheService._generate_hash(solar_date, solar_time, gender)
        return f"bazi:ready:{hash_val}"
    
    @staticmethod
    def get_lock_key(solar_date: str, solar_time: str, gender: str, lock_type: str = "warmup") -> str:
        """获取分布式锁键"""
        hash_val = BaziCacheService._generate_hash(solar_date, solar_time, gender)
        return f"bazi:lock:{hash_val}:{lock_type}"
    
    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端"""
        try:
            from server.config.redis_config import get_redis_pool
            redis_pool = get_redis_pool()
            if redis_pool:
                return redis_pool.get_connection()
        except Exception as e:
            logger.warning(f"⚠️ 获取 Redis 客户端失败: {e}")
        return None
    
    @staticmethod
    def get_base(solar_date: str, solar_time: str, gender: str) -> Optional[Dict[str, Any]]:
        """
        获取基础八字数据（Level 0）
        
        Returns:
            基础八字数据，如果不存在则返回 None
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache_key = BaziCacheService.get_base_key(solar_date, solar_time, gender)
            result = cache.get(cache_key)
            if result:
                logger.debug(f"✅ [缓存命中] Level 0 基础八字: {cache_key[:50]}...")
            return result
        except Exception as e:
            logger.warning(f"⚠️ 读取基础八字缓存失败: {e}")
            return None
    
    @staticmethod
    def set_base(solar_date: str, solar_time: str, gender: str, data: Dict[str, Any]) -> bool:
        """
        设置基础八字数据（Level 0）
        
        Returns:
            是否成功
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache.l2.ttl = BaziCacheService.TTL_BASE
            cache_key = BaziCacheService.get_base_key(solar_date, solar_time, gender)
            cache.set(cache_key, data)
            logger.info(f"✅ [缓存写入] Level 0 基础八字: {cache_key[:50]}...")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 写入基础八字缓存失败: {e}")
            return False
    
    @staticmethod
    def get_dayun(solar_date: str, solar_time: str, gender: str, dayun_index: int) -> Optional[Dict[str, Any]]:
        """
        获取单个大运数据（Level 1）
        
        Returns:
            大运数据，如果不存在则返回 None
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache_key = BaziCacheService.get_dayun_key(solar_date, solar_time, gender, dayun_index)
            result = cache.get(cache_key)
            if result:
                logger.debug(f"✅ [缓存命中] Level 1 大运 {dayun_index}: {cache_key[:50]}...")
            return result
        except Exception as e:
            logger.warning(f"⚠️ 读取大运缓存失败: {e}")
            return None
    
    @staticmethod
    def set_dayun(solar_date: str, solar_time: str, gender: str, dayun_index: int, data: Dict[str, Any]) -> bool:
        """
        设置单个大运数据（Level 1）
        
        Returns:
            是否成功
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache.l2.ttl = BaziCacheService.TTL_DAYUN
            cache_key = BaziCacheService.get_dayun_key(solar_date, solar_time, gender, dayun_index)
            cache.set(cache_key, data)
            logger.debug(f"✅ [缓存写入] Level 1 大运 {dayun_index}: {cache_key[:50]}...")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 写入大运缓存失败: {e}")
            return False
    
    @staticmethod
    def get_full(solar_date: str, solar_time: str, gender: str) -> Optional[Dict[str, Any]]:
        """
        获取完整数据（Level 2）
        
        Returns:
            完整数据，如果不存在则返回 None
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache_key = BaziCacheService.get_full_key(solar_date, solar_time, gender)
            result = cache.get(cache_key)
            if result:
                logger.debug(f"✅ [缓存命中] Level 2 完整数据: {cache_key[:50]}...")
            return result
        except Exception as e:
            logger.warning(f"⚠️ 读取完整数据缓存失败: {e}")
            return None
    
    @staticmethod
    def set_full(solar_date: str, solar_time: str, gender: str, data: Dict[str, Any]) -> bool:
        """
        设置完整数据（Level 2）
        
        Returns:
            是否成功
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache.l2.ttl = BaziCacheService.TTL_FULL
            cache_key = BaziCacheService.get_full_key(solar_date, solar_time, gender)
            cache.set(cache_key, data)
            logger.info(f"✅ [缓存写入] Level 2 完整数据: {cache_key[:50]}...")
            
            # 同时设置就绪标志
            ready_key = BaziCacheService.get_ready_key(solar_date, solar_time, gender)
            cache.l2.ttl = BaziCacheService.TTL_READY
            cache.set(ready_key, {"ready": True, "timestamp": time.time()})
            return True
        except Exception as e:
            logger.warning(f"⚠️ 写入完整数据缓存失败: {e}")
            return False
    
    @staticmethod
    def is_ready(solar_date: str, solar_time: str, gender: str) -> bool:
        """
        检查完整数据是否已就绪
        
        Returns:
            是否就绪
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            ready_key = BaziCacheService.get_ready_key(solar_date, solar_time, gender)
            result = cache.get(ready_key)
            return result is not None and result.get("ready", False)
        except Exception:
            return False
    
    @staticmethod
    def acquire_lock(solar_date: str, solar_time: str, gender: str, lock_type: str = "warmup") -> bool:
        """
        获取分布式锁（防止重复计算）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            lock_type: 锁类型（warmup/compute）
        
        Returns:
            是否成功获取锁
        """
        redis_client = BaziCacheService.get_redis_client()
        if not redis_client:
            return False
        
        try:
            lock_key = BaziCacheService.get_lock_key(solar_date, solar_time, gender, lock_type)
            # 使用 SET NX EX 实现分布式锁
            result = redis_client.set(lock_key, "locked", nx=True, ex=BaziCacheService.LOCK_TIMEOUT)
            if result:
                logger.debug(f"✅ [获取锁] {lock_type}: {lock_key[:50]}...")
            return result is True
        except Exception as e:
            logger.warning(f"⚠️ 获取分布式锁失败: {e}")
            return False
    
    @staticmethod
    def release_lock(solar_date: str, solar_time: str, gender: str, lock_type: str = "warmup") -> bool:
        """
        释放分布式锁
        
        Returns:
            是否成功释放
        """
        redis_client = BaziCacheService.get_redis_client()
        if not redis_client:
            return False
        
        try:
            lock_key = BaziCacheService.get_lock_key(solar_date, solar_time, gender, lock_type)
            redis_client.delete(lock_key)
            logger.debug(f"✅ [释放锁] {lock_type}: {lock_key[:50]}...")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 释放分布式锁失败: {e}")
            return False


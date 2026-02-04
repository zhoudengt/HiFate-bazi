#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字数据缓存管理器 - 多级缓存管理
"""

import sys
import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.utils.cache_multi_level import get_multi_cache

# 配置日志
logger = logging.getLogger(__name__)


class BaziDataCache:
    """八字数据缓存管理器"""
    
    @staticmethod
    def _generate_cache_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        modules: Dict[str, Any]
    ) -> str:
        """
        生成缓存键
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置
        
        Returns:
            str: 缓存键
        """
        # 标准化模块配置（排序，确保相同配置生成相同键）
        modules_str = json.dumps(modules, sort_keys=True, ensure_ascii=False)
        
        # 生成键（使用完整字符串，不使用MD5哈希，便于调试和清理）
        key_parts = [
            'bazi_data',
            solar_date,
            solar_time,
            gender,
            modules_str
        ]
        key = ':'.join(key_parts)
        
        return key
    
    @staticmethod
    def get(
        solar_date: str,
        solar_time: str,
        gender: str,
        modules: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        从缓存获取数据
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置
        
        Returns:
            dict: 缓存的数据，如果不存在则返回 None
        """
        try:
            cache = get_multi_cache()
            cache_key = BaziDataCache._generate_cache_key(solar_date, solar_time, gender, modules)
            
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug(f"缓存命中: {cache_key[:100]}...")
                return cached_data
            
            logger.debug(f"缓存未命中: {cache_key[:100]}...")
            return None
        except Exception as e:
            logger.warning(f"获取缓存失败（不影响业务）: {e}")
            return None
    
    @staticmethod
    def set(
        solar_date: str,
        solar_time: str,
        gender: str,
        modules: Dict[str, Any],
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        设置缓存
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置
            data: 要缓存的数据
            ttl: 缓存过期时间（秒），如果为 None 则使用默认值
        """
        try:
            cache = get_multi_cache()
            cache_key = BaziDataCache._generate_cache_key(solar_date, solar_time, gender, modules)
            
            # 如果指定了 TTL，临时设置
            if ttl is not None:
                original_ttl = cache.l2.ttl
                cache.l2.ttl = ttl
            
            cache.set(cache_key, data)
            
            # 恢复原始 TTL
            if ttl is not None:
                cache.l2.ttl = original_ttl
            
            logger.debug(f"缓存已设置: {cache_key[:100]}...")
        except Exception as e:
            logger.warning(f"设置缓存失败（不影响业务）: {e}")
    
    @staticmethod
    def invalidate(
        solar_date: str,
        solar_time: str,
        gender: str,
        modules: Optional[Dict[str, Any]] = None
    ):
        """
        使缓存失效
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置（如果为 None，则清除所有相关缓存）
        """
        try:
            cache = get_multi_cache()
            
            if modules is None:
                # 清除所有相关缓存（使用 pattern 匹配）
                from shared.config.redis import get_redis_client
                redis_client = get_redis_client()
                
                if redis_client:
                    pattern = f"bazi_data:{solar_date}:{solar_time}:{gender}:*"
                    # 使用 SCAN 迭代删除（避免阻塞）
                    cursor = 0
                    while True:
                        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            redis_client.delete(*keys)
                        if cursor == 0:
                            break
                
                # 清除 L1 缓存
                cache.l1.clear()
            else:
                # 清除指定缓存
                cache_key = BaziDataCache._generate_cache_key(solar_date, solar_time, gender, modules)
                cache.delete(cache_key)
            
            logger.debug(f"缓存已失效: {solar_date} {solar_time} {gender}")
        except Exception as e:
            logger.warning(f"清除缓存失败（不影响业务）: {e}")


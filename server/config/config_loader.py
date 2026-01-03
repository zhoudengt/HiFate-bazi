#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 从数据库加载服务配置（需求3：services.env配置化）
支持缓存和热更新
"""

import os
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path

# 添加项目根目录到路径
import sys
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from server.utils.unified_logger import get_unified_logger

logger = get_unified_logger()


class ConfigLoader:
    """服务配置加载器（从数据库加载，支持缓存和热更新）"""
    
    _instance: Optional['ConfigLoader'] = None
    _cache: Dict[str, tuple] = {}  # {key: (value, timestamp)}
    _cache_ttl: int = 300  # 5分钟缓存
    _lock = None
    
    def __init__(self):
        """初始化配置加载器"""
        import threading
        if ConfigLoader._lock is None:
            ConfigLoader._lock = threading.Lock()
        self._load_fallback_config()
    
    @classmethod
    def get_instance(cls) -> 'ConfigLoader':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_fallback_config(self):
        """加载文件配置作为降级方案"""
        self._fallback_config = {}
        services_env_path = project_root / 'config' / 'services.env'
        
        if services_env_path.exists():
            try:
                with open(services_env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        # 解析 export KEY="VALUE" 格式
                        if line.startswith('export '):
                            line = line[7:].strip()
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                self._fallback_config[key] = value
                
                logger.info(f"✓ 已加载降级配置（文件）：{len(self._fallback_config)}项")
            except Exception as e:
                logger.warning(f"⚠️ 加载降级配置失败: {e}")
    
    def get_config(self, key: str, default: Optional[str] = None, use_cache: bool = True) -> Optional[str]:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            use_cache: 是否使用缓存
        
        Returns:
            配置值，如果不存在则返回default
        """
        # 1. 先查缓存
        if use_cache and key in self._cache:
            cached_value, cached_time = self._cache[key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_value
        
        # 2. 查数据库
        try:
            value = self._load_from_db(key)
            if value is not None:
                self._cache[key] = (value, time.time())
                return value
        except Exception as e:
            logger.warning(f"⚠️ 从数据库加载配置失败: {key}, 错误: {e}")
        
        # 3. 使用降级配置（文件）
        if key in self._fallback_config:
            value = self._fallback_config[key]
            logger.info(f"✓ 使用降级配置: {key}")
            return value
        
        # 4. 使用环境变量
        env_value = os.getenv(key)
        if env_value:
            return env_value
        
        # 5. 使用默认值
        return default
    
    def _load_from_db(self, key: str) -> Optional[str]:
        """从数据库加载配置"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT config_value, config_type 
                    FROM service_configs 
                    WHERE config_key = %s AND is_active = 1
                    ORDER BY version DESC, id DESC
                    LIMIT 1
                """
                cursor.execute(sql, (key,))
                result = cursor.fetchone()
                
                if result:
                    value = result.get('config_value')
                    config_type = result.get('config_type', 'string')
                    
                    # 根据类型转换
                    if config_type == 'bool':
                        return '1' if str(value).lower() in ('true', '1', 'yes') else '0'
                    elif config_type == 'int':
                        return str(value)
                    else:
                        return value
                
                return None
        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {key}, 错误: {e}")
            raise
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def reload_config(self, key: Optional[str] = None):
        """
        重新加载配置（热更新）
        
        Args:
            key: 要重新加载的配置键，如果为None则清空所有缓存
        """
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                logger.info(f"✓ 已清除配置缓存: {key}")
            else:
                self._cache.clear()
                logger.info("✓ 已清除所有配置缓存")
    
    def get_all_configs(self, category: Optional[str] = None) -> Dict[str, str]:
        """
        获取所有配置
        
        Args:
            category: 配置分类（可选）
        
        Returns:
            配置字典 {key: value}
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                if category:
                    sql = """
                        SELECT config_key, config_value, config_type 
                        FROM service_configs 
                        WHERE category = %s AND is_active = 1
                        ORDER BY config_key
                    """
                    cursor.execute(sql, (category,))
                else:
                    sql = """
                        SELECT config_key, config_value, config_type 
                        FROM service_configs 
                        WHERE is_active = 1
                        ORDER BY config_key
                    """
                    cursor.execute(sql)
                
                results = cursor.fetchall()
                configs = {}
                
                for result in results:
                    key = result.get('config_key')
                    value = result.get('config_value')
                    config_type = result.get('config_type', 'string')
                    
                    # 根据类型转换
                    if config_type == 'bool':
                        configs[key] = '1' if str(value).lower() in ('true', '1', 'yes') else '0'
                    elif config_type == 'int':
                        configs[key] = str(value)
                    else:
                        configs[key] = value
                
                return configs
        except Exception as e:
            logger.error(f"❌ 获取所有配置失败: {e}")
            return {}
        finally:
            if conn:
                return_mysql_connection(conn)


# 全局配置加载器实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取配置加载器实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader.get_instance()
    return _config_loader


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    获取配置值（便捷函数）
    
    Args:
        key: 配置键
        default: 默认值
    
    Returns:
        配置值
    """
    return get_config_loader().get_config(key, default)


def reload_config(key: Optional[str] = None):
    """
    重新加载配置（热更新，便捷函数）
    
    Args:
        key: 要重新加载的配置键，如果为None则清空所有缓存
    """
    get_config_loader().reload_config(key)


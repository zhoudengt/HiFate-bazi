#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付配置加载器
从 payment_configs 表读取支付相关配置
支持缓存和热更新
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class PaymentConfigLoader:
    """支付配置加载器（从 payment_configs 表加载，支持缓存和热更新）"""
    
    _instance: Optional['PaymentConfigLoader'] = None
    _cache: Dict[str, tuple] = {}  # {cache_key: (value, timestamp)}
    _cache_ttl: int = 300  # 5分钟缓存
    _lock = None
    
    def __init__(self):
        """初始化配置加载器"""
        import threading
        if PaymentConfigLoader._lock is None:
            PaymentConfigLoader._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'PaymentConfigLoader':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _get_cache_key(self, provider: str, config_key: str, environment: str = 'production', merchant_id: Optional[str] = None) -> str:
        """生成缓存键"""
        merchant_part = f":{merchant_id}" if merchant_id else ""
        return f"{provider}:{config_key}:{environment}{merchant_part}"
    
    def get_config(
        self,
        provider: str,
        config_key: str,
        environment: Optional[str] = None,
        merchant_id: Optional[str] = None,
        default: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        获取支付配置值
        
        Args:
            provider: 支付渠道（stripe/paypal/alipay/wechat/linepay/newebpay/shared）
            config_key: 配置键（如：secret_key, client_id等）
            environment: 环境（production/sandbox/test），如果为None则自动查找is_active=1的记录
            merchant_id: 商户ID（可选）
            default: 默认值
            use_cache: 是否使用缓存
        
        Returns:
            配置值，如果不存在则返回default
        """
        # 如果未指定environment，使用特殊标记表示查找is_active=1的记录
        effective_env = environment if environment is not None else '__active__'
        cache_key = self._get_cache_key(provider, config_key, effective_env, merchant_id)
        
        # 1. 先查缓存
        if use_cache and cache_key in self._cache:
            cached_value, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_value
        
        # 2. 查数据库
        try:
            value = self._load_from_db(provider, config_key, environment, merchant_id)
            if value is not None:
                self._cache[cache_key] = (value, time.time())
                return value
        except Exception as e:
            logger.warning(f"⚠️ 从数据库加载支付配置失败: {provider}.{config_key}, 错误: {e}")
        
        # 3. 使用环境变量（降级方案，保持向后兼容）
        env_key = self._get_env_key(provider, config_key)
        env_value = os.getenv(env_key)
        if env_value:
            logger.info(f"✓ 使用环境变量降级配置: {env_key}")
            return env_value
        
        # 4. 使用默认值
        return default
    
    def _get_env_key(self, provider: str, config_key: str) -> str:
        """根据 provider 和 config_key 生成环境变量键名（向后兼容）"""
        # 映射规则
        mapping = {
            ('stripe', 'secret_key'): 'STRIPE_SECRET_KEY',
            ('paypal', 'client_id'): 'PAYPAL_CLIENT_ID',
            ('paypal', 'client_secret'): 'PAYPAL_CLIENT_SECRET',
            ('paypal', 'mode'): 'PAYPAL_MODE',
            ('alipay', 'app_id'): 'ALIPAY_APP_ID',
            ('alipay', 'private_key_path'): 'ALIPAY_PRIVATE_KEY_PATH',
            ('alipay', 'public_key_path'): 'ALIPAY_PUBLIC_KEY_PATH',
            ('alipay', 'gateway'): 'ALIPAY_GATEWAY',
            ('wechat', 'app_id'): 'WECHAT_APP_ID',
            ('wechat', 'mch_id'): 'WECHAT_MCH_ID',
            ('wechat', 'api_key'): 'WECHAT_API_KEY',
            ('wechat', 'cert_path'): 'WECHAT_CERT_PATH',
            ('wechat', 'key_path'): 'WECHAT_KEY_PATH',
            ('linepay', 'channel_id'): 'LINEPAY_CHANNEL_ID',
            ('linepay', 'channel_secret'): 'LINEPAY_CHANNEL_SECRET',
            ('linepay', 'mode'): 'LINEPAY_MODE',
            ('linepay', 'sandbox_url'): 'LINEPAY_SANDBOX_URL',
            ('linepay', 'production_url'): 'LINEPAY_PRODUCTION_URL',
            ('payssion', 'api_key'): 'PAYSSION_API_KEY',
            ('payssion', 'secret'): 'PAYSSION_SECRET',
            ('payssion', 'merchant_id'): 'PAYSSION_MERCHANT_ID',
            ('payermax', 'app_id'): 'PAYERMAX_APP_ID',
            ('payermax', 'merchant_no'): 'PAYERMAX_MERCHANT_NO',
            ('payermax', 'private_key_path'): 'PAYERMAX_PRIVATE_KEY_PATH',
            ('payermax', 'public_key_path'): 'PAYERMAX_PUBLIC_KEY_PATH',
            ('newebpay', 'merchant_id'): 'NEWEBPAY_MERCHANT_ID',
            ('newebpay', 'hash_key'): 'NEWEBPAY_HASH_KEY',
            ('newebpay', 'hash_iv'): 'NEWEBPAY_HASH_IV',
            ('newebpay', 'mode'): 'NEWEBPAY_MODE',
            ('newebpay', 'test_url'): 'NEWEBPAY_TEST_URL',
            ('newebpay', 'production_url'): 'NEWEBPAY_PRODUCTION_URL',
            ('shared', 'frontend_base_url'): 'FRONTEND_BASE_URL',
            ('shared', 'api_base_url'): 'API_BASE_URL',
        }
        
        return mapping.get((provider, config_key), f"{provider.upper()}_{config_key.upper()}")
    
    def _load_from_db(
        self,
        provider: str,
        config_key: str,
        environment: Optional[str] = None,
        merchant_id: Optional[str] = None
    ) -> Optional[str]:
        """
        从数据库加载配置
        
        Args:
            provider: 支付渠道
            config_key: 配置键
            environment: 环境，如果为None则自动查找is_active=1的记录
            merchant_id: 商户ID（可选）
        
        Returns:
            配置值
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                if merchant_id:
                    if environment:
                        # 指定环境：匹配environment且is_active=1
                        sql = """
                            SELECT config_value, config_type, environment
                            FROM payment_configs 
                            WHERE provider = %s 
                              AND config_key = %s 
                              AND environment = %s 
                              AND (merchant_id = %s OR merchant_id IS NULL)
                              AND is_active = 1
                            ORDER BY merchant_id DESC, version DESC, id DESC
                            LIMIT 1
                        """
                        cursor.execute(sql, (provider, config_key, environment, merchant_id))
                    else:
                        # 未指定环境：查找is_active=1的记录
                        sql = """
                            SELECT config_value, config_type, environment
                            FROM payment_configs 
                            WHERE provider = %s 
                              AND config_key = %s 
                              AND (merchant_id = %s OR merchant_id IS NULL)
                              AND is_active = 1
                            ORDER BY merchant_id DESC, version DESC, id DESC
                            LIMIT 1
                        """
                        cursor.execute(sql, (provider, config_key, merchant_id))
                else:
                    if environment:
                        # 指定环境：匹配environment且is_active=1
                        sql = """
                            SELECT config_value, config_type, environment
                            FROM payment_configs 
                            WHERE provider = %s 
                              AND config_key = %s 
                              AND environment = %s 
                              AND merchant_id IS NULL
                              AND is_active = 1
                            ORDER BY version DESC, id DESC
                            LIMIT 1
                        """
                        cursor.execute(sql, (provider, config_key, environment))
                    else:
                        # 未指定环境：查找is_active=1的记录
                        sql = """
                            SELECT config_value, config_type, environment
                            FROM payment_configs 
                            WHERE provider = %s 
                              AND config_key = %s 
                              AND merchant_id IS NULL
                              AND is_active = 1
                            ORDER BY version DESC, id DESC
                            LIMIT 1
                        """
                        cursor.execute(sql, (provider, config_key))
                
                result = cursor.fetchone()
                
                if result:
                    value = result.get('config_value')
                    config_type = result.get('config_type', 'string')
                    found_env = result.get('environment')
                    
                    if found_env:
                        logger.debug(f"✓ 找到配置: {provider}.{config_key} (环境: {found_env})")
                    
                    # 根据类型转换
                    if config_type == 'bool':
                        return '1' if str(value).lower() in ('true', '1', 'yes') else '0'
                    elif config_type == 'int':
                        return str(value)
                    else:
                        return value
                
                return None
        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {provider}.{config_key}, 错误: {e}")
            raise
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def reload_config(
        self,
        provider: Optional[str] = None,
        config_key: Optional[str] = None,
        environment: Optional[str] = None
    ):
        """
        重新加载配置（热更新）
        
        Args:
            provider: 支付渠道，如果为None则清除所有缓存
            config_key: 配置键，如果为None则清除该渠道的所有缓存
            environment: 环境，如果为None则清除所有环境的缓存
        """
        with self._lock:
            if provider and config_key and environment:
                # 清除特定配置的缓存
                cache_key = self._get_cache_key(provider, config_key, environment)
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.info(f"✓ 已清除支付配置缓存: {cache_key}")
            elif provider:
                # 清除该渠道的所有缓存
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{provider}:")]
                for key in keys_to_remove:
                    del self._cache[key]
                logger.info(f"✓ 已清除支付配置缓存: {provider} (共{len(keys_to_remove)}项)")
            else:
                # 清除所有缓存
                self._cache.clear()
                logger.info("✓ 已清除所有支付配置缓存")
    
    def get_all_configs(
        self,
        provider: Optional[str] = None,
        environment: str = 'production'
    ) -> Dict[str, str]:
        """
        获取所有配置
        
        Args:
            provider: 支付渠道（可选）
            environment: 环境
        
        Returns:
            配置字典 {config_key: value}
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                if provider:
                    sql = """
                        SELECT config_key, config_value, config_type 
                        FROM payment_configs 
                        WHERE provider = %s 
                          AND environment = %s 
                          AND is_active = 1
                        ORDER BY config_key
                    """
                    cursor.execute(sql, (provider, environment))
                else:
                    sql = """
                        SELECT provider, config_key, config_value, config_type 
                        FROM payment_configs 
                        WHERE environment = %s 
                          AND is_active = 1
                        ORDER BY provider, config_key
                    """
                    cursor.execute(sql, (environment,))
                
                results = cursor.fetchall()
                configs = {}
                
                for result in results:
                    key = result.get('config_key')
                    value = result.get('config_value')
                    config_type = result.get('config_type', 'string')
                    
                    # 根据类型转换
                    if config_type == 'bool':
                        value = '1' if str(value).lower() in ('true', '1', 'yes') else '0'
                    elif config_type == 'int':
                        value = str(value)
                    
                    if provider:
                        configs[key] = value
                    else:
                        provider_name = result.get('provider')
                        configs[f"{provider_name}.{key}"] = value
                
                return configs
        except Exception as e:
            logger.error(f"❌ 获取所有支付配置失败: {e}")
            return {}
        finally:
            if conn:
                return_mysql_connection(conn)


# 全局配置加载器实例
_payment_config_loader: Optional[PaymentConfigLoader] = None


def get_payment_config_loader() -> PaymentConfigLoader:
    """获取支付配置加载器实例"""
    global _payment_config_loader
    if _payment_config_loader is None:
        _payment_config_loader = PaymentConfigLoader.get_instance()
    return _payment_config_loader


def get_payment_config(
    provider: str,
    config_key: str,
    environment: Optional[str] = None,
    merchant_id: Optional[str] = None,
    default: Optional[str] = None
) -> Optional[str]:
    """
    获取支付配置值（便捷函数）
    
    Args:
        provider: 支付渠道
        config_key: 配置键
        environment: 环境，如果为None则自动查找is_active=1的记录
        merchant_id: 商户ID（可选）
        default: 默认值
    
    Returns:
        配置值
    """
    return get_payment_config_loader().get_config(
        provider, config_key, environment, merchant_id, default
    )


def reload_payment_config(
    provider: Optional[str] = None,
    config_key: Optional[str] = None,
    environment: Optional[str] = None
):
    """
    重新加载支付配置（热更新，便捷函数）
    
    Args:
        provider: 支付渠道
        config_key: 配置键
        environment: 环境
    """
    get_payment_config_loader().reload_config(provider, config_key, environment)


def get_payment_environment(provider: str = 'linepay', default: str = 'production') -> str:
    """
    获取支付环境配置（便捷函数）
    
    通过查询指定支付方式的激活配置来推断当前环境。
    默认查询 linepay 的配置，因为 linepay 通常同时配置了 sandbox 和 production。
    
    Args:
        provider: 支付渠道（用于推断环境），默认 'linepay'
        default: 默认环境值（如果无法推断，默认使用 production）
    
    Returns:
        支付环境：production / sandbox / test
    """
    # 尝试从指定支付方式的配置中推断环境
    # 查询任意一个配置键的激活记录，获取其 environment
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT DISTINCT environment
                FROM payment_configs 
                WHERE provider = %s 
                  AND merchant_id IS NULL
                  AND is_active = 1
                LIMIT 1
            """
            cursor.execute(sql, (provider,))
            result = cursor.fetchone()
            
            if result:
                env = result.get('environment')
                if env:
                    valid_environments = ['production', 'sandbox', 'test']
                    if env.lower() in valid_environments:
                        return env.lower()
            
            return_mysql_connection(conn)
    except Exception as e:
        logger.warning(f"⚠️ 无法推断支付环境: {e}，使用默认值: {default}")
        if conn:
            return_mysql_connection(conn)
    
    # 如果无法推断，返回默认值
    return default

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敏感信息管理系统 - 统一管理所有密钥、Token、密码等敏感信息
要求：不允许硬编码，所有敏感信息从环境变量或密钥管理服务读取
"""

import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 延迟导入，避免循环导入
def _get_logger():
    from server.utils.unified_logger import get_unified_logger
    return get_unified_logger()


class SecretManager:
    """
    敏感信息管理器
    统一管理所有密钥、Token、密码等敏感信息
    
    特性：
    1. 从环境变量读取敏感信息
    2. 支持从 .env 文件读取（开发环境）
    3. 自动验证敏感信息是否存在
    4. 记录敏感信息访问日志（脱敏）
    5. 支持密钥轮换
    """
    
    _instance: Optional['SecretManager'] = None
    _secrets: Dict[str, Optional[str]] = {}
    
    def __init__(self):
        """初始化敏感信息管理器"""
        self._load_secrets()
    
    @classmethod
    def get_instance(cls) -> 'SecretManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_secrets(self):
        """加载敏感信息"""
        logger = _get_logger()
        # 优先加载 .env 文件（开发环境）
        try:
            from dotenv import load_dotenv
            from server.utils.unified_logger import LogLevel
            env_path = Path(project_root) / '.env'
            if env_path.exists():
                load_dotenv(env_path, override=True)
                logger.log_function(
                    'SecretManager',
                    '_load_secrets',
                    f'已加载 .env 文件: {env_path}',
                    level=LogLevel.INFO
                )
        except ImportError:
            from server.utils.unified_logger import LogLevel
            logger.log_function(
                'SecretManager',
                '_load_secrets',
                'python-dotenv 未安装，将使用系统环境变量',
                level=LogLevel.WARNING
            )
        except Exception as e:
            logger.log_error(
                'SecretManager',
                '_load_secrets',
                e
            )
        
        # 加载所有敏感信息（不设置默认值，强制从环境变量读取）
        self._secrets = {}
    
    def get_secret(self, key: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
        """
        获取敏感信息
        
        Args:
            key: 敏感信息键名
            default: 默认值（不推荐使用）
            required: 是否必须存在
            
        Returns:
            敏感信息值
            
        Raises:
            ValueError: 如果 required=True 但敏感信息不存在
        """
        # 检查缓存
        if key in self._secrets:
            value = self._secrets[key]
        else:
            # 从环境变量读取
            value = os.getenv(key, default)
            self._secrets[key] = value
        
        # 验证是否必须存在
        if required and not value:
            error_msg = f"敏感信息 '{key}' 未设置，请检查环境变量"
            logger.log_error(
                'SecretManager',
                'get_secret',
                ValueError(error_msg),
                extra={'key': key, 'required': required}
            )
            raise ValueError(error_msg)
        
        # 记录访问日志（脱敏）
        if value:
            logger = _get_logger()
            from server.utils.unified_logger import LogLevel
            masked_value = value[:4] + '***' + value[-4:] if len(value) > 8 else '***'
            logger.log_function(
                'SecretManager',
                'get_secret',
                f'访问敏感信息: {key}',
                extra={'key': key, 'masked_value': masked_value, 'exists': True},
                level=LogLevel.DEBUG
            )
        
        return value
    
    def get_coze_token(self) -> str:
        """获取 Coze Access Token"""
        return self.get_secret('COZE_ACCESS_TOKEN', required=True)
    
    def get_coze_bot_id(self) -> str:
        """获取 Coze Bot ID"""
        return self.get_secret('COZE_BOT_ID', required=True)
    
    def get_intent_bot_id(self) -> str:
        """获取 Intent Service Bot ID"""
        return self.get_secret('INTENT_BOT_ID', required=True)
    
    def get_fortune_analysis_bot_id(self) -> str:
        """获取 Fortune Analysis Bot ID"""
        return self.get_secret('FORTUNE_ANALYSIS_BOT_ID', required=True)
    
    def get_mysql_password(self) -> str:
        """获取 MySQL 密码"""
        # 支持多个环境变量名
        password = (
            self.get_secret('MYSQL_PASSWORD', required=False) or
            self.get_secret('MYSQL_ROOT_PASSWORD', required=False)
        )
        if not password:
            raise ValueError("MySQL 密码未设置，请设置 MYSQL_PASSWORD 或 MYSQL_ROOT_PASSWORD 环境变量")
        return password
    
    def get_mysql_config(self) -> Dict[str, Any]:
        """获取 MySQL 配置（不包含敏感信息）"""
        return {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USER', 'root'),
            'database': os.getenv('MYSQL_DATABASE', 'hifate_bazi'),
            'charset': 'utf8mb4',
        }
    
    def get_redis_password(self) -> Optional[str]:
        """获取 Redis 密码"""
        return self.get_secret('REDIS_PASSWORD', required=False)
    
    def get_stripe_secret_key(self) -> Optional[str]:
        """获取 Stripe Secret Key"""
        return self.get_secret('STRIPE_SECRET_KEY', required=False)
    
    def get_jwt_secret(self) -> str:
        """获取 JWT Secret"""
        secret = self.get_secret('JWT_SECRET', required=False)
        if not secret:
            # 如果没有设置，使用一个默认值（仅开发环境）
            if os.getenv('APP_ENV', 'development') == 'development':
                logger = _get_logger()
                from server.utils.unified_logger import LogLevel
                logger.log_function(
                    'SecretManager',
                    'get_jwt_secret',
                    'JWT_SECRET 未设置，使用默认值（仅开发环境）',
                    level=LogLevel.WARNING
                )
                return 'dev-secret-key-change-in-production'
            else:
                raise ValueError("JWT_SECRET 未设置，生产环境必须设置")
        return secret
    
    def get_third_party_api_keys(self) -> Dict[str, Optional[str]]:
        """获取第三方 API Keys"""
        return {
            'JISUAPI_KEY': self.get_secret('JISUAPI_KEY', required=False),
            'TIANAPI_KEY': self.get_secret('TIANAPI_KEY', required=False),
            'API6API_KEY': self.get_secret('API6API_KEY', required=False),
        }
    
    def validate_secrets(self) -> Dict[str, bool]:
        """
        验证所有必需的敏感信息是否存在
        
        Returns:
            验证结果字典，key 为敏感信息名称，value 为是否存在
        """
        required_secrets = {
            'COZE_ACCESS_TOKEN': True,
            'COZE_BOT_ID': True,
            'MYSQL_PASSWORD': True,  # 可以是 MYSQL_ROOT_PASSWORD
            'JWT_SECRET': False,  # 开发环境可以不设置
        }
        
        results = {}
        for secret_name, required in required_secrets.items():
            try:
                if secret_name == 'MYSQL_PASSWORD':
                    # 特殊处理 MySQL 密码
                    value = (
                        self.get_secret('MYSQL_PASSWORD', required=False) or
                        self.get_secret('MYSQL_ROOT_PASSWORD', required=False)
                    )
                    results[secret_name] = bool(value)
                else:
                    value = self.get_secret(secret_name, required=False)
                    results[secret_name] = bool(value)
            except Exception:
                results[secret_name] = False
        
        # 记录验证结果
        logger = _get_logger()
        from server.utils.unified_logger import LogLevel
        logger.log_function(
            'SecretManager',
            'validate_secrets',
            '验证敏感信息',
            output_data=results,
            level=LogLevel.INFO
        )
        
        return results


# 全局单例实例
_secret_manager_instance: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """获取敏感信息管理器实例"""
    global _secret_manager_instance
    if _secret_manager_instance is None:
        _secret_manager_instance = SecretManager()
    return _secret_manager_instance


# 便捷函数
def get_coze_token() -> str:
    """获取 Coze Access Token"""
    return get_secret_manager().get_coze_token()


def get_coze_bot_id() -> str:
    """获取 Coze Bot ID"""
    return get_secret_manager().get_coze_bot_id()


def get_mysql_password() -> str:
    """获取 MySQL 密码"""
    return get_secret_manager().get_mysql_password()


def get_jwt_secret() -> str:
    """获取 JWT Secret"""
    return get_secret_manager().get_jwt_secret()


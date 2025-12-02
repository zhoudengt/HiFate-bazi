#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能开关（Feature Flag）
支持灰度发布、A/B 测试、紧急开关
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class FlagType(Enum):
    """功能开关类型"""
    BOOLEAN = "boolean"        # 布尔开关
    PERCENTAGE = "percentage"  # 百分比开关
    WHITELIST = "whitelist"    # 白名单
    BLACKLIST = "blacklist"    # 黑名单


@dataclass
class FeatureFlag:
    """功能开关配置"""
    name: str                  # 开关名称
    description: str           # 描述
    enabled: bool              # 是否启用
    flag_type: FlagType       # 开关类型
    value: Any = None          # 开关值（百分比、白名单等）
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FeatureFlagManager:
    """功能开关管理器"""
    
    def __init__(self, storage_backend=None):
        """
        初始化功能开关管理器
        
        Args:
            storage_backend: 存储后端（Redis/数据库），默认使用内存
        """
        self._storage = storage_backend or InMemoryFlagStorage()
        self._flags: Dict[str, FeatureFlag] = {}
    
    def create_flag(self, flag: FeatureFlag) -> bool:
        """创建功能开关"""
        try:
            now = datetime.now().isoformat()
            if not flag.created_at:
                flag.created_at = now
            flag.updated_at = now
            
            self._flags[flag.name] = flag
            self._storage.save_flag(flag.name, {
                'name': flag.name,
                'description': flag.description,
                'enabled': flag.enabled,
                'flag_type': flag.flag_type.value,
                'value': flag.value,
                'created_at': flag.created_at,
                'updated_at': flag.updated_at
            })
            
            logger.info(f"创建功能开关: {flag.name}")
            return True
        except Exception as e:
            logger.error(f"创建功能开关失败: {e}")
            return False
    
    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """获取功能开关"""
        if name in self._flags:
            return self._flags[name]
        
        data = self._storage.load_flag(name)
        if data:
            flag = FeatureFlag(
                name=data['name'],
                description=data['description'],
                enabled=data['enabled'],
                flag_type=FlagType(data['flag_type']),
                value=data.get('value'),
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at')
            )
            self._flags[name] = flag
            return flag
        
        return None
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """
        检查功能开关是否启用
        
        Args:
            flag_name: 开关名称
            user_id: 用户ID（用于百分比/白名单/黑名单）
        
        Returns:
            bool: 是否启用
        """
        flag = self.get_flag(flag_name)
        if not flag:
            return False
        
        if not flag.enabled:
            return False
        
        # 根据类型判断
        if flag.flag_type == FlagType.BOOLEAN:
            return True
        elif flag.flag_type == FlagType.PERCENTAGE:
            if user_id:
                return self._is_in_percentage(user_id, flag.value)
            return False
        elif flag.flag_type == FlagType.WHITELIST:
            if user_id:
                return user_id in (flag.value or [])
            return False
        elif flag.flag_type == FlagType.BLACKLIST:
            if user_id:
                return user_id not in (flag.value or [])
            return True
        
        return False
    
    def _is_in_percentage(self, user_id: str, percentage: float) -> bool:
        """检查用户是否在百分比范围内"""
        import hashlib
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        percent = (hash_value % 10000) / 100.0
        return percent < percentage
    
    def toggle_flag(self, flag_name: str, enabled: bool):
        """切换开关状态"""
        flag = self.get_flag(flag_name)
        if flag:
            flag.enabled = enabled
            flag.updated_at = datetime.now().isoformat()
            self._storage.save_flag(flag_name, {
                'name': flag.name,
                'description': flag.description,
                'enabled': flag.enabled,
                'flag_type': flag.flag_type.value,
                'value': flag.value,
                'created_at': flag.created_at,
                'updated_at': flag.updated_at
            })
            logger.info(f"切换功能开关: {flag_name} -> {enabled}")


class InMemoryFlagStorage:
    """内存存储后端"""
    
    def __init__(self):
        self._flags = {}
    
    def save_flag(self, name: str, data: dict):
        self._flags[name] = data
    
    def load_flag(self, name: str) -> Optional[dict]:
        return self._flags.get(name)


# 全局实例
_feature_flag_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """获取全局功能开关管理器"""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager


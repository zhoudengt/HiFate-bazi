#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功能开关单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.utils.feature_flag import (
    FeatureFlagManager,
    FeatureFlag,
    FlagType
)


class TestFeatureFlagManager:
    """功能开关管理器测试类"""
    
    def test_create_boolean_flag(self):
        """测试创建布尔开关"""
        manager = FeatureFlagManager()
        
        flag = FeatureFlag(
            name="新功能",
            description="新功能开关",
            enabled=True,
            flag_type=FlagType.BOOLEAN
        )
        
        success = manager.create_flag(flag)
        assert success is True
        
        # 验证开关已创建
        retrieved = manager.get_flag("新功能")
        assert retrieved is not None
        assert retrieved.enabled is True
    
    def test_boolean_flag_check(self):
        """测试布尔开关检查"""
        manager = FeatureFlagManager()
        
        flag = FeatureFlag(
            name="新功能",
            description="新功能开关",
            enabled=True,
            flag_type=FlagType.BOOLEAN
        )
        manager.create_flag(flag)
        
        # 检查开关
        assert manager.is_enabled("新功能") is True
        
        # 禁用开关
        manager.toggle_flag("新功能", False)
        assert manager.is_enabled("新功能") is False
    
    def test_percentage_flag(self):
        """测试百分比开关"""
        manager = FeatureFlagManager()
        
        flag = FeatureFlag(
            name="新功能灰度",
            description="新功能灰度发布",
            enabled=True,
            flag_type=FlagType.PERCENTAGE,
            value=50.0  # 50%
        )
        manager.create_flag(flag)
        
        # 测试多个用户
        enabled_count = 0
        total_users = 100
        
        for i in range(total_users):
            if manager.is_enabled("新功能灰度", f"user{i}"):
                enabled_count += 1
        
        # 应该大约 50% 的用户启用（允许误差）
        assert 40 <= enabled_count <= 60
    
    def test_whitelist_flag(self):
        """测试白名单开关"""
        manager = FeatureFlagManager()
        
        flag = FeatureFlag(
            name="新功能白名单",
            description="新功能白名单",
            enabled=True,
            flag_type=FlagType.WHITELIST,
            value=["user1", "user2", "user3"]
        )
        manager.create_flag(flag)
        
        # 白名单用户应该启用
        assert manager.is_enabled("新功能白名单", "user1") is True
        assert manager.is_enabled("新功能白名单", "user2") is True
        
        # 非白名单用户不应该启用
        assert manager.is_enabled("新功能白名单", "user4") is False
    
    def test_blacklist_flag(self):
        """测试黑名单开关"""
        manager = FeatureFlagManager()
        
        flag = FeatureFlag(
            name="新功能黑名单",
            description="新功能黑名单",
            enabled=True,
            flag_type=FlagType.BLACKLIST,
            value=["user1", "user2"]
        )
        manager.create_flag(flag)
        
        # 黑名单用户不应该启用
        assert manager.is_enabled("新功能黑名单", "user1") is False
        
        # 非黑名单用户应该启用
        assert manager.is_enabled("新功能黑名单", "user3") is True


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A/B 测试框架单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.utils.ab_test import (
    ABTestManager,
    Experiment,
    ExperimentStatus,
    InMemoryStorage
)


class TestABTestManager:
    """A/B 测试管理器测试类"""
    
    def test_create_experiment(self):
        """测试创建实验"""
        manager = ABTestManager()
        
        experiment = Experiment(
            name="测试实验",
            description="测试描述",
            status=ExperimentStatus.RUNNING,
            traffic_percent=100.0,
            variants={"A": 50, "B": 50}
        )
        
        success = manager.create_experiment(experiment)
        assert success is True
        
        # 验证实验已创建
        retrieved = manager.get_experiment("测试实验")
        assert retrieved is not None
        assert retrieved.name == "测试实验"
        assert retrieved.status == ExperimentStatus.RUNNING
    
    def test_assign_variant(self):
        """测试分配变体"""
        manager = ABTestManager()
        
        experiment = Experiment(
            name="测试实验",
            description="测试描述",
            status=ExperimentStatus.RUNNING,
            traffic_percent=100.0,
            variants={"A": 50, "B": 50}
        )
        manager.create_experiment(experiment)
        
        # 分配变体
        variant = manager.assign_variant("测试实验", "user1")
        assert variant in ["A", "B"]
        
        # 同一用户应该分配到相同变体
        variant2 = manager.assign_variant("测试实验", "user1")
        assert variant == variant2
    
    def test_traffic_percentage(self):
        """测试流量百分比"""
        manager = ABTestManager()
        
        experiment = Experiment(
            name="测试实验",
            description="测试描述",
            status=ExperimentStatus.RUNNING,
            traffic_percent=50.0,  # 50% 流量
            variants={"A": 100}
        )
        manager.create_experiment(experiment)
        
        # 测试多个用户，应该只有部分用户分配到变体
        assigned_count = 0
        total_users = 100
        
        for i in range(total_users):
            variant = manager.assign_variant("测试实验", f"user{i}")
            if variant:
                assigned_count += 1
        
        # 应该大约 50% 的用户分配到变体（允许误差）
        assert 40 <= assigned_count <= 60
    
    def test_record_event(self):
        """测试记录事件"""
        manager = ABTestManager()
        
        experiment = Experiment(
            name="测试实验",
            description="测试描述",
            status=ExperimentStatus.RUNNING,
            traffic_percent=100.0,
            variants={"A": 50, "B": 50}
        )
        manager.create_experiment(experiment)
        
        # 分配变体
        variant = manager.assign_variant("测试实验", "user1")
        
        # 记录事件
        manager.record_event("测试实验", "user1", "click", {"button": "submit"})
        
        # 获取统计
        stats = manager.get_experiment_stats("测试实验")
        assert stats['total_events'] > 0
    
    def test_experiment_status(self):
        """测试实验状态"""
        manager = ABTestManager()
        
        experiment = Experiment(
            name="测试实验",
            description="测试描述",
            status=ExperimentStatus.PAUSED,  # 暂停状态
            traffic_percent=100.0,
            variants={"A": 50, "B": 50}
        )
        manager.create_experiment(experiment)
        
        # 暂停的实验不应该分配变体
        variant = manager.assign_variant("测试实验", "user1")
        assert variant is None
        
        # 更新为运行状态
        manager.update_experiment_status("测试实验", ExperimentStatus.RUNNING)
        variant = manager.assign_variant("测试实验", "user1")
        assert variant in ["A", "B"]


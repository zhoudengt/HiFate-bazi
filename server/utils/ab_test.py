#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A/B 测试框架
支持功能开关、流量分配、数据收集
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """实验状态"""
    DRAFT = "draft"          # 草稿
    RUNNING = "running"      # 运行中
    PAUSED = "paused"        # 暂停
    COMPLETED = "completed"  # 完成
    ARCHIVED = "archived"    # 归档


@dataclass
class Experiment:
    """实验配置"""
    name: str                    # 实验名称
    description: str             # 实验描述
    status: ExperimentStatus    # 状态
    traffic_percent: float      # 流量百分比 (0-100)
    variants: Dict[str, float]   # 变体分配 {"A": 50, "B": 50}
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ABTestManager:
    """A/B 测试管理器"""
    
    def __init__(self, storage_backend=None):
        """
        初始化 A/B 测试管理器
        
        Args:
            storage_backend: 存储后端（Redis/数据库），默认使用内存
        """
        self._storage = storage_backend or InMemoryStorage()
        self._experiments: Dict[str, Experiment] = {}
    
    def create_experiment(self, experiment: Experiment) -> bool:
        """
        创建实验
        
        Args:
            experiment: 实验配置
        
        Returns:
            bool: 是否创建成功
        """
        try:
            # 验证流量分配
            total = sum(experiment.variants.values())
            if abs(total - 100.0) > 0.01:
                raise ValueError(f"变体流量分配总和必须为 100%，当前为 {total}%")
            
            # 设置时间戳
            now = datetime.now().isoformat()
            if not experiment.created_at:
                experiment.created_at = now
            experiment.updated_at = now
            
            # 存储实验
            self._experiments[experiment.name] = experiment
            self._storage.save_experiment(experiment.name, asdict(experiment))
            
            logger.info(f"创建实验: {experiment.name}")
            return True
        except Exception as e:
            logger.error(f"创建实验失败: {e}")
            return False
    
    def get_experiment(self, name: str) -> Optional[Experiment]:
        """获取实验配置"""
        if name in self._experiments:
            return self._experiments[name]
        
        # 从存储加载
        data = self._storage.load_experiment(name)
        if data:
            experiment = Experiment(**data)
            experiment.status = ExperimentStatus(experiment.status)
            self._experiments[name] = experiment
            return experiment
        
        return None
    
    def assign_variant(self, experiment_name: str, user_id: str) -> Optional[str]:
        """
        为用户分配变体
        
        Args:
            experiment_name: 实验名称
            user_id: 用户ID
        
        Returns:
            str: 变体名称（A/B/C等），如果未分配到实验则返回 None
        """
        experiment = self.get_experiment(experiment_name)
        if not experiment:
            return None
        
        # 检查实验状态
        if experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # 检查流量百分比
        if not self._is_in_traffic(user_id, experiment.traffic_percent):
            return None
        
        # 分配变体（基于用户ID的哈希）
        variant = self._hash_to_variant(user_id, experiment.variants)
        
        # 记录分配
        self._storage.record_assignment(experiment_name, user_id, variant)
        
        return variant
    
    def _is_in_traffic(self, user_id: str, traffic_percent: float) -> bool:
        """检查用户是否在流量范围内"""
        # 使用用户ID的哈希值决定是否在流量范围内
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        percent = (hash_value % 10000) / 100.0
        return percent < traffic_percent
    
    def _hash_to_variant(self, user_id: str, variants: Dict[str, float]) -> str:
        """根据用户ID哈希分配变体"""
        # 使用实验名称+用户ID的哈希值
        hash_input = f"{user_id}_experiment"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        percent = (hash_value % 10000) / 100.0
        
        # 根据百分比分配变体
        cumulative = 0.0
        for variant, weight in sorted(variants.items()):
            cumulative += weight
            if percent < cumulative:
                return variant
        
        # 默认返回第一个变体
        return list(variants.keys())[0]
    
    def record_event(self, experiment_name: str, user_id: str, 
                    event_name: str, event_data: Optional[Dict[str, Any]] = None):
        """
        记录事件（用于分析）
        
        Args:
            experiment_name: 实验名称
            user_id: 用户ID
            event_name: 事件名称（如 "click", "purchase"）
            event_data: 事件数据
        """
        variant = self._storage.get_assignment(experiment_name, user_id)
        if variant:
            self._storage.record_event(experiment_name, user_id, variant, event_name, event_data)
    
    def get_experiment_stats(self, experiment_name: str) -> Dict[str, Any]:
        """获取实验统计"""
        return self._storage.get_experiment_stats(experiment_name)
    
    def update_experiment_status(self, experiment_name: str, status: ExperimentStatus):
        """更新实验状态"""
        experiment = self.get_experiment(experiment_name)
        if experiment:
            experiment.status = status
            experiment.updated_at = datetime.now().isoformat()
            self._storage.save_experiment(experiment_name, asdict(experiment))
            logger.info(f"更新实验状态: {experiment_name} -> {status.value}")


class InMemoryStorage:
    """内存存储后端（用于测试）"""
    
    def __init__(self):
        self._experiments = {}
        self._assignments = {}  # {experiment_name: {user_id: variant}}
        self._events = []       # [{experiment, user_id, variant, event_name, event_data, timestamp}]
    
    def save_experiment(self, name: str, data: dict):
        self._experiments[name] = data
    
    def load_experiment(self, name: str) -> Optional[dict]:
        return self._experiments.get(name)
    
    def record_assignment(self, experiment_name: str, user_id: str, variant: str):
        if experiment_name not in self._assignments:
            self._assignments[experiment_name] = {}
        self._assignments[experiment_name][user_id] = variant
    
    def get_assignment(self, experiment_name: str, user_id: str) -> Optional[str]:
        return self._assignments.get(experiment_name, {}).get(user_id)
    
    def record_event(self, experiment_name: str, user_id: str, variant: str,
                    event_name: str, event_data: Optional[Dict[str, Any]]):
        self._events.append({
            'experiment': experiment_name,
            'user_id': user_id,
            'variant': variant,
            'event_name': event_name,
            'event_data': event_data or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def get_experiment_stats(self, experiment_name: str) -> Dict[str, Any]:
        """获取实验统计"""
        assignments = self._assignments.get(experiment_name, {})
        events = [e for e in self._events if e['experiment'] == experiment_name]
        
        # 统计各变体分配数量
        variant_counts = {}
        for variant in assignments.values():
            variant_counts[variant] = variant_counts.get(variant, 0) + 1
        
        # 统计各变体事件数量
        variant_events = {}
        for event in events:
            variant = event['variant']
            if variant not in variant_events:
                variant_events[variant] = {}
            event_name = event['event_name']
            variant_events[variant][event_name] = variant_events[variant].get(event_name, 0) + 1
        
        return {
            'experiment': experiment_name,
            'total_users': len(assignments),
            'variant_counts': variant_counts,
            'variant_events': variant_events,
            'total_events': len(events)
        }


# 全局实例
_ab_test_manager: Optional[ABTestManager] = None


def get_ab_test_manager() -> ABTestManager:
    """获取全局 A/B 测试管理器"""
    global _ab_test_manager
    if _ab_test_manager is None:
        _ab_test_manager = ABTestManager()
    return _ab_test_manager


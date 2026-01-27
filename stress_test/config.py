#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力测试配置管理模块
支持多环境配置（本地、测试、生产）
"""

import os
from typing import Dict, Any


class TestConfig:
    """压力测试配置类"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "host": "http://localhost:8001",      # 默认目标地址
        "users": 30,                          # 并发用户数
        "spawn_rate": 5,                      # 每秒启动用户数（避免瞬间冲击）
        "run_time": "5m",                     # 测试持续时间（5分钟）
        "wait_time_min": 1,                   # 最小请求间隔(秒)
        "wait_time_max": 3,                   # 最大请求间隔(秒)
    }
    
    # 本地开发环境配置
    LOCAL_CONFIG = {
        "host": "http://localhost:8001",
        "users": 15,                          # 本地环境降低并发数
        "spawn_rate": 3,
        "run_time": "3m",
        "wait_time_min": 1,
        "wait_time_max": 2,
    }
    
    # 测试/预发布环境配置
    STAGING_CONFIG = {
        "host": os.getenv("STAGING_HOST", "http://staging-server:8001"),
        "users": 30,
        "spawn_rate": 5,
        "run_time": "5m",
        "wait_time_min": 1,
        "wait_time_max": 3,
    }
    
    # 生产环境配置（谨慎使用）
    PRODUCTION_CONFIG = {
        "host": os.getenv("PRODUCTION_HOST", "http://production-server:8001"),
        "users": 30,
        "spawn_rate": 5,
        "run_time": "5m",
        "wait_time_min": 1,
        "wait_time_max": 3,
    }
    
    # 高并发测试配置
    HIGH_LOAD_CONFIG = {
        "host": os.getenv("TEST_HOST", "http://localhost:8001"),
        "users": 50,                          # 更高并发
        "spawn_rate": 10,
        "run_time": "10m",
        "wait_time_min": 0.5,
        "wait_time_max": 2,
    }
    
    @classmethod
    def get_config(cls, env: str = "default") -> Dict[str, Any]:
        """
        获取指定环境的配置
        
        Args:
            env: 环境名称 (default/local/staging/production/high_load)
            
        Returns:
            配置字典
        """
        config_map = {
            "default": cls.DEFAULT_CONFIG,
            "local": cls.LOCAL_CONFIG,
            "staging": cls.STAGING_CONFIG,
            "production": cls.PRODUCTION_CONFIG,
            "high_load": cls.HIGH_LOAD_CONFIG,
        }
        
        config = config_map.get(env.lower(), cls.DEFAULT_CONFIG).copy()
        
        # 允许通过环境变量覆盖配置
        if os.getenv("STRESS_TEST_HOST"):
            config["host"] = os.getenv("STRESS_TEST_HOST")
        if os.getenv("STRESS_TEST_USERS"):
            config["users"] = int(os.getenv("STRESS_TEST_USERS"))
        if os.getenv("STRESS_TEST_SPAWN_RATE"):
            config["spawn_rate"] = int(os.getenv("STRESS_TEST_SPAWN_RATE"))
        if os.getenv("STRESS_TEST_RUN_TIME"):
            config["run_time"] = os.getenv("STRESS_TEST_RUN_TIME")
        
        return config
    
    @classmethod
    def print_config(cls, config: Dict[str, Any]):
        """打印配置信息"""
        print("=" * 60)
        print("压力测试配置")
        print("=" * 60)
        for key, value in config.items():
            print(f"  {key}: {value}")
        print("=" * 60)


# 测试任务权重配置
TASK_WEIGHTS = {
    "bazi_calculate": 40,      # 八字计算 - 40%
    "bazi_interface": 30,      # 八字界面数据 - 30%
    "daily_fortune": 20,       # 每日运势 - 20%
    "health_check": 10,       # 健康检查 - 10%
}

# 性能指标阈值
PERFORMANCE_THRESHOLDS = {
    "max_response_time_p50": 1000,   # P50 响应时间 < 1秒
    "max_response_time_p95": 2000,   # P95 响应时间 < 2秒
    "max_response_time_p99": 5000,   # P99 响应时间 < 5秒
    "max_error_rate": 0.01,          # 错误率 < 1%
    "min_rps": 10,                    # 最小 QPS > 10
}

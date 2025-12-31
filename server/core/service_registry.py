#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务注册中心

功能：
- 服务注册与发现
- 服务配置管理
- 服务状态监控
"""

import os
import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str                                   # 服务名称
    host: str                                   # 服务地址
    port: int                                   # 服务端口
    protocol: str = "grpc"                      # 协议类型：grpc, http
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_heartbeat: float = 0                   # 最后心跳时间
    metadata: Dict[str, str] = field(default_factory=dict)
    version: str = "1.0.0"
    weight: int = 100                           # 负载均衡权重
    
    @property
    def address(self) -> str:
        """获取服务地址"""
        return f"{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """判断服务是否健康"""
        return self.status == ServiceStatus.HEALTHY


# 服务配置：定义所有微服务的默认配置
SERVICE_CONFIGS = {
    "bazi-core": {
        "name": "bazi-core",
        "port": 9001,
        "description": "八字核心计算服务",
        "env_key": "BAZI_CORE_SERVICE_URL",
    },
    "bazi-fortune": {
        "name": "bazi-fortune",
        "port": 9002,
        "description": "运势计算服务",
        "env_key": "BAZI_FORTUNE_SERVICE_URL",
    },
    "bazi-analyzer": {
        "name": "bazi-analyzer",
        "port": 9003,
        "description": "八字分析服务",
        "env_key": "BAZI_ANALYZER_SERVICE_URL",
    },
    "bazi-rule": {
        "name": "bazi-rule",
        "port": 9004,
        "description": "规则匹配服务",
        "env_key": "BAZI_RULE_SERVICE_URL",
    },
    "fortune-analysis": {
        "name": "fortune-analysis",
        "port": 9005,
        "description": "运势分析服务",
        "env_key": "FORTUNE_ANALYSIS_SERVICE_URL",
    },
    "payment": {
        "name": "payment",
        "port": 9006,
        "description": "支付服务",
        "env_key": "PAYMENT_SERVICE_URL",
    },
    "fortune-rule": {
        "name": "fortune-rule",
        "port": 9007,
        "description": "运势规则服务",
        "env_key": "FORTUNE_RULE_SERVICE_URL",
    },
    "intent": {
        "name": "intent",
        "port": 9008,
        "description": "意图识别服务",
        "env_key": "INTENT_SERVICE_URL",
    },
    "prompt-optimizer": {
        "name": "prompt-optimizer",
        "port": 9009,
        "description": "提示优化服务",
        "env_key": "PROMPT_OPTIMIZER_SERVICE_URL",
    },
    "desk-fengshui": {
        "name": "desk-fengshui",
        "port": 9010,
        "description": "办公桌风水服务",
        "env_key": "DESK_FENGSHUI_SERVICE_URL",
    },
}


class ServiceRegistry:
    """
    服务注册中心
    
    使用示例：
        registry = ServiceRegistry.get_instance()
        
        # 注册服务
        registry.register("bazi-core", "localhost", 9001)
        
        # 发现服务
        service = registry.discover("bazi-core")
        if service:
            print(f"Service address: {service.address}")
        
        # 获取服务地址
        address = registry.get_service_address("bazi-core")
    """
    
    _instance: Optional['ServiceRegistry'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._services: Dict[str, List[ServiceInfo]] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._heartbeat_interval = 30  # 心跳间隔（秒）
        self._unhealthy_threshold = 90  # 不健康阈值（秒）
        self._initialized = False
        
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def initialize(self):
        """初始化注册中心，从环境变量加载服务配置"""
        if self._initialized:
            return
            
        logger.info("初始化服务注册中心...")
        
        # 从环境变量加载服务配置（支持Docker容器环境）
        for service_name, config in SERVICE_CONFIGS.items():
            env_key = config["env_key"]
            # 在Docker环境中，使用服务名或环境变量，避免硬编码localhost
            default_host = os.getenv("SERVICE_HOST", os.getenv("HOSTNAME", "localhost"))
            default_url = f"{default_host}:{config['port']}"
            
            service_url = os.getenv(env_key, default_url)
            
            # 解析地址
            if ":" in service_url:
                # 移除可能的协议前缀
                if "://" in service_url:
                    service_url = service_url.split("://")[1]
                host, port = service_url.rsplit(":", 1)
                port = int(port)
            else:
                host = service_url
                port = config["port"]
            
            # 注册服务
            self.register(
                name=service_name,
                host=host,
                port=port,
                metadata={"description": config["description"]}
            )
        
        self._initialized = True
        logger.info(f"服务注册中心初始化完成，已注册 {len(self._services)} 个服务")
    
    def register(
        self,
        name: str,
        host: str,
        port: int,
        protocol: str = "grpc",
        metadata: Optional[Dict[str, str]] = None,
        version: str = "1.0.0",
        weight: int = 100
    ) -> ServiceInfo:
        """
        注册服务
        
        Args:
            name: 服务名称
            host: 服务地址
            port: 服务端口
            protocol: 协议类型
            metadata: 元数据
            version: 服务版本
            weight: 负载均衡权重
            
        Returns:
            ServiceInfo: 服务信息
        """
        service = ServiceInfo(
            name=name,
            host=host,
            port=port,
            protocol=protocol,
            status=ServiceStatus.UNKNOWN,
            last_heartbeat=time.time(),
            metadata=metadata or {},
            version=version,
            weight=weight
        )
        
        if name not in self._services:
            self._services[name] = []
        
        # 检查是否已存在相同地址的服务
        existing = next(
            (s for s in self._services[name] if s.address == service.address),
            None
        )
        
        if existing:
            # 更新现有服务
            existing.status = service.status
            existing.last_heartbeat = service.last_heartbeat
            existing.metadata = service.metadata
            existing.version = service.version
            existing.weight = service.weight
            logger.debug(f"更新服务: {name} @ {service.address}")
            return existing
        else:
            # 添加新服务
            self._services[name].append(service)
            logger.info(f"注册服务: {name} @ {service.address}")
            
            # 触发回调
            self._notify_callbacks(name, "register", service)
            
            return service
    
    def unregister(self, name: str, host: str, port: int):
        """
        注销服务
        
        Args:
            name: 服务名称
            host: 服务地址
            port: 服务端口
        """
        if name not in self._services:
            return
        
        address = f"{host}:{port}"
        services = self._services[name]
        
        for i, service in enumerate(services):
            if service.address == address:
                removed = services.pop(i)
                logger.info(f"注销服务: {name} @ {address}")
                self._notify_callbacks(name, "unregister", removed)
                break
    
    def discover(self, name: str) -> Optional[ServiceInfo]:
        """
        发现服务（返回一个健康的服务实例）
        
        Args:
            name: 服务名称
            
        Returns:
            ServiceInfo: 服务信息，如果没有可用服务返回 None
        """
        if name not in self._services:
            return None
        
        services = self._services[name]
        
        # 优先返回健康的服务
        healthy_services = [s for s in services if s.is_healthy]
        if healthy_services:
            # 简单的轮询负载均衡（可以扩展为加权轮询）
            return healthy_services[0]
        
        # 如果没有健康的服务，返回状态未知的服务
        unknown_services = [s for s in services if s.status == ServiceStatus.UNKNOWN]
        if unknown_services:
            return unknown_services[0]
        
        # 最后返回任意服务
        return services[0] if services else None
    
    def discover_all(self, name: str) -> List[ServiceInfo]:
        """
        发现所有服务实例
        
        Args:
            name: 服务名称
            
        Returns:
            List[ServiceInfo]: 服务信息列表
        """
        return self._services.get(name, [])
    
    def get_service_address(self, name: str) -> Optional[str]:
        """
        获取服务地址
        
        Args:
            name: 服务名称
            
        Returns:
            str: 服务地址（host:port），如果没有可用服务返回 None
        """
        service = self.discover(name)
        return service.address if service else None
    
    def heartbeat(self, name: str, host: str, port: int, healthy: bool = True):
        """
        服务心跳
        
        Args:
            name: 服务名称
            host: 服务地址
            port: 服务端口
            healthy: 是否健康
        """
        if name not in self._services:
            return
        
        address = f"{host}:{port}"
        for service in self._services[name]:
            if service.address == address:
                service.last_heartbeat = time.time()
                service.status = ServiceStatus.HEALTHY if healthy else ServiceStatus.UNHEALTHY
                break
    
    def update_status(self, name: str, host: str, port: int, status: ServiceStatus):
        """
        更新服务状态
        
        Args:
            name: 服务名称
            host: 服务地址
            port: 服务端口
            status: 服务状态
        """
        if name not in self._services:
            return
        
        address = f"{host}:{port}"
        for service in self._services[name]:
            if service.address == address:
                old_status = service.status
                service.status = status
                if old_status != status:
                    logger.info(f"服务状态变更: {name} @ {address}: {old_status.value} -> {status.value}")
                    self._notify_callbacks(name, "status_change", service)
                break
    
    def check_health(self):
        """检查所有服务的健康状态"""
        current_time = time.time()
        
        for name, services in self._services.items():
            for service in services:
                if service.status == ServiceStatus.HEALTHY:
                    # 检查心跳超时
                    if current_time - service.last_heartbeat > self._unhealthy_threshold:
                        service.status = ServiceStatus.UNHEALTHY
                        logger.warning(f"服务心跳超时: {name} @ {service.address}")
                        self._notify_callbacks(name, "unhealthy", service)
    
    def on_change(self, name: str, callback: Callable):
        """
        注册服务变更回调
        
        Args:
            name: 服务名称
            callback: 回调函数 callback(event_type, service_info)
        """
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(callback)
    
    def _notify_callbacks(self, name: str, event_type: str, service: ServiceInfo):
        """通知回调"""
        if name in self._callbacks:
            for callback in self._callbacks[name]:
                try:
                    callback(event_type, service)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    def list_services(self) -> Dict[str, List[ServiceInfo]]:
        """列出所有服务"""
        return self._services.copy()
    
    def get_stats(self) -> Dict[str, any]:
        """获取统计信息"""
        stats = {
            "total_services": sum(len(s) for s in self._services.values()),
            "healthy_services": 0,
            "unhealthy_services": 0,
            "services": {}
        }
        
        for name, services in self._services.items():
            healthy = sum(1 for s in services if s.is_healthy)
            stats["healthy_services"] += healthy
            stats["unhealthy_services"] += len(services) - healthy
            stats["services"][name] = {
                "total": len(services),
                "healthy": healthy,
                "instances": [
                    {
                        "address": s.address,
                        "status": s.status.value,
                        "version": s.version
                    }
                    for s in services
                ]
            }
        
        return stats


# 便捷函数
def get_registry() -> ServiceRegistry:
    """获取服务注册中心实例"""
    return ServiceRegistry.get_instance()


def get_service_address(name: str) -> Optional[str]:
    """获取服务地址"""
    registry = get_registry()
    registry.initialize()
    return registry.get_service_address(name)

# -*- coding: utf-8 -*-
"""
热更新模块 - 支持所有模块的热更新，无需重启服务

功能：
1. 主服务热更新 (FastAPI + 源代码)
2. 微服务热更新 (gRPC 服务)
3. 规则/配置热更新 (数据库 + Redis)
4. 双机同步 (Redis 发布/订阅)
5. 回滚机制 (版本历史 + 一键回滚)
6. 单例重置 (自动清理缓存)
"""

from .hot_reload_manager import HotReloadManager
from .version_manager import VersionManager
from .reloaders import (
    RuleReloader,
    ContentReloader,
    ConfigReloaderEnhanced,
    CacheReloader,
    SourceCodeReloader,
    MicroserviceReloaderProxy,
    SingletonReloader,
    get_reloader,
    reload_all_modules,
    RELOAD_ORDER,
)
from .microservice_reloader import (
    MicroserviceReloader,
    DynamicServicer,
    create_hot_reload_server,
    register_microservice_reloader,
    get_microservice_reloader,
    get_all_microservice_reloaders,
    reload_all_microservices,
    get_all_microservice_status,
    get_dependent_services,
    trigger_dependent_services,
)
from .cluster_synchronizer import (
    ClusterSynchronizer,
    get_cluster_synchronizer,
    start_cluster_sync,
    stop_cluster_sync,
)

__all__ = [
    # 核心管理器
    'HotReloadManager',
    'VersionManager',
    
    # 重载器
    'RuleReloader',
    'ContentReloader',
    'ConfigReloaderEnhanced',
    'CacheReloader',
    'SourceCodeReloader',
    'MicroserviceReloaderProxy',
    'SingletonReloader',
    'get_reloader',
    'reload_all_modules',
    'RELOAD_ORDER',
    
    # 微服务热更新
    'MicroserviceReloader',
    'DynamicServicer',
    'create_hot_reload_server',
    'register_microservice_reloader',
    'get_microservice_reloader',
    'get_all_microservice_reloaders',
    'reload_all_microservices',
    'get_all_microservice_status',
    'get_dependent_services',
    'trigger_dependent_services',
    
    # 集群同步
    'ClusterSynchronizer',
    'get_cluster_synchronizer',
    'start_cluster_sync',
    'stop_cluster_sync',
]









































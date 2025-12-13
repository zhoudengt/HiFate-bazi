#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新API接口

提供的端点：
- GET  /hot-reload/status        获取热更新状态
- POST /hot-reload/check         手动触发热更新检查
- GET  /hot-reload/versions      获取所有模块版本号
- POST /hot-reload/reload/{module} 手动重载指定模块
- POST /hot-reload/reload-all    重载所有模块（按顺序）
- POST /hot-reload/rollback      回滚到上一版本
- POST /hot-reload/sync          触发双机同步
- GET  /hot-reload/health        健康检查
- GET  /hot-reload/microservices 获取微服务热更新状态
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from .hot_reload_manager import HotReloadManager
from .version_manager import VersionManager

router = APIRouter()


class ReloadResponse(BaseModel):
    """重载响应模型"""
    success: bool
    message: str
    reloaded_modules: Optional[List[str]] = None
    failed_modules: Optional[List[str]] = None


class ClusterSyncResponse(BaseModel):
    """集群同步响应模型"""
    success: bool
    message: str
    event_id: Optional[str] = None
    cluster_nodes: Optional[Dict] = None


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    success: bool
    status: str
    details: Dict


@router.get("/hot-reload/status", summary="获取热更新状态")
async def get_hot_reload_status():
    """
    获取热更新管理器状态
    """
    try:
        manager = HotReloadManager.get_instance()
        status = manager.get_status()
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/hot-reload/reload-endpoints", summary="强制重新注册 gRPC 端点")
async def reload_endpoints():
    """
    强制重新注册所有 gRPC 端点
    
    用于修复热更新后端点丢失的问题
    """
    try:
        from server.api.grpc_gateway import _reload_endpoints, SUPPORTED_ENDPOINTS
        
        old_count = len(SUPPORTED_ENDPOINTS)
        success = _reload_endpoints()
        new_count = len(SUPPORTED_ENDPOINTS)
        
        return {
            "success": success,
            "message": f"端点重新注册完成（旧: {old_count}, 新: {new_count}）",
            "old_count": old_count,
            "new_count": new_count,
            "endpoints": list(SUPPORTED_ENDPOINTS.keys())
        }
    except Exception as e:
        logger.error(f"重新注册端点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新注册端点失败: {str(e)}")


@router.post("/hot-reload/check", summary="手动触发热更新检查")
async def trigger_hot_reload(module_name: Optional[str] = None):
    """
    手动触发热更新检查
    
    - **module_name**: 模块名称（可选），不指定则检查所有模块
    """
    try:
        manager = HotReloadManager.get_instance()
        reloaded = manager.check_and_reload(module_name)
        
        return ReloadResponse(
            success=True,
            message=f"热更新检查完成",
            reloaded_modules=[module_name] if module_name and reloaded else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"热更新检查失败: {str(e)}")


@router.get("/hot-reload/versions", summary="获取所有模块版本号")
async def get_all_versions():
    """
    获取所有模块的版本号信息
    """
    try:
        versions = {}
        for module_name in VersionManager._version_checkers.keys():
            versions[module_name] = {
                'current': VersionManager.get_version(module_name),
                'cached': VersionManager.get_cached_version(module_name),
                'changed': VersionManager.check_version_changed(module_name)
            }
        
        return {
            "success": True,
            "versions": versions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本号失败: {str(e)}")


@router.post("/hot-reload/reload/{module_name}", summary="手动重载指定模块")
async def reload_module(module_name: str):
    """
    手动重载指定模块
    
    - **module_name**: 模块名称（rules/content/config/cache/source）
    """
    try:
        from .reloaders import get_reloader
        
        reloader_class = get_reloader(module_name)
        if not reloader_class:
            raise HTTPException(status_code=400, detail=f"未知的模块: {module_name}")
        
        success = reloader_class.reload()
        
        if success:
            # 更新版本号缓存
            VersionManager.update_cached_version(
                module_name,
                VersionManager.get_version(module_name)
            )
        
        return ReloadResponse(
            success=success,
            message=f"模块 {module_name} {'重载成功' if success else '重载失败'}",
            reloaded_modules=[module_name] if success else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重载失败: {str(e)}")


@router.post("/hot-reload/reload-all", summary="重载所有模块")
async def reload_all():
    """
    按顺序重载所有模块
    
    重载顺序：
    1. config - 配置
    2. singleton - 单例重置
    3. rules - 规则
    4. content - 内容
    5. source - 源代码
    6. microservice - 微服务
    7. cache - 缓存
    """
    try:
        from .reloaders import reload_all_modules, RELOAD_ORDER
        
        results = reload_all_modules()
        
        success_modules = [m for m, s in results.items() if s]
        failed_modules = [m for m, s in results.items() if not s]
        
        return ReloadResponse(
            success=len(failed_modules) == 0,
            message=f"重载完成: {len(success_modules)} 成功, {len(failed_modules)} 失败",
            reloaded_modules=success_modules,
            failed_modules=failed_modules if failed_modules else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"全量重载失败: {str(e)}")


@router.post("/hot-reload/rollback", summary="回滚到上一版本")
async def rollback_module(module_name: Optional[str] = None, version: Optional[int] = None):
    """
    回滚模块到上一版本
    
    - **module_name**: 模块名称（可选），不指定则回滚所有模块
    - **version**: 要回滚到的版本号（可选），不指定则回滚到上一版本
    """
    try:
        # 触发集群回滚
        try:
            from .cluster_synchronizer import get_cluster_synchronizer
            synchronizer = get_cluster_synchronizer()
            event_id = synchronizer.trigger_cluster_rollback(version)
        
        return ReloadResponse(
            success=True,
                message=f"回滚事件已发送 (事件ID: {event_id})",
            reloaded_modules=[module_name] if module_name else None
        )
        except Exception as e:
            # 如果集群同步不可用，执行本地回滚
            print(f"⚠ 集群同步不可用，执行本地回滚: {e}")
            
            # 执行本地回滚（重新加载所有模块）
            from .reloaders import reload_all_modules
            results = reload_all_modules()
            
            return ReloadResponse(
                success=all(results.values()),
                message=f"本地回滚完成",
                reloaded_modules=list(results.keys())
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@router.post("/hot-reload/sync", summary="触发双机同步")
async def trigger_cluster_sync(modules: Optional[List[str]] = None):
    """
    触发集群热更新同步
    
    - **modules**: 要同步的模块列表（可选），不指定则同步所有模块
    """
    try:
        from .cluster_synchronizer import get_cluster_synchronizer
        
        synchronizer = get_cluster_synchronizer()
        event_id = synchronizer.trigger_cluster_update(modules)
        cluster_nodes = synchronizer.check_cluster_health()
        
        return ClusterSyncResponse(
            success=True,
            message=f"同步事件已发送到 {len(cluster_nodes)} 个节点",
            event_id=event_id,
            cluster_nodes=cluster_nodes
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/hot-reload/health", summary="热更新系统健康检查")
async def health_check():
    """
    检查热更新系统的健康状态
    
    返回：
    - 热更新管理器状态
    - 文件监控器状态
    - 微服务热更新器状态
    - 集群同步器状态
    """
    try:
        details = {}
        all_healthy = True
        
        # 1. 热更新管理器
        try:
            manager = HotReloadManager.get_instance()
            details['hot_reload_manager'] = {
                'running': manager._running,
                'interval': manager._interval,
                'status': 'healthy' if manager._running else 'stopped'
            }
        except Exception as e:
            details['hot_reload_manager'] = {'status': 'error', 'error': str(e)}
            all_healthy = False
        
        # 2. 文件监控器
        try:
            from .file_monitor import get_file_monitor
            file_monitor = get_file_monitor()
            details['file_monitor'] = {
                'running': file_monitor._running,
                'watched_files': len(file_monitor._file_states),
                'status': 'healthy' if file_monitor._running else 'stopped'
            }
        except Exception as e:
            details['file_monitor'] = {'status': 'error', 'error': str(e)}
            all_healthy = False
        
        # 3. 微服务热更新器
        try:
            from .microservice_reloader import get_all_microservice_status
            microservices = get_all_microservice_status()
            details['microservices'] = {
                'count': len(microservices),
                'services': microservices,
                'status': 'healthy' if microservices else 'no_services'
            }
        except Exception as e:
            details['microservices'] = {'status': 'error', 'error': str(e)}
        
        # 4. 集群同步器
        try:
            from .cluster_synchronizer import get_cluster_synchronizer
            synchronizer = get_cluster_synchronizer()
            cluster_health = synchronizer.check_cluster_health()
            details['cluster_sync'] = {
                'running': synchronizer._running,
                'node_id': synchronizer.node_id,
                'cluster_nodes': len(cluster_health),
                'status': 'healthy' if synchronizer._running else 'stopped'
            }
        except Exception as e:
            details['cluster_sync'] = {'status': 'not_configured', 'error': str(e)}
        
        return HealthResponse(
            success=True,
            status='healthy' if all_healthy else 'degraded',
            details=details
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.get("/hot-reload/microservices", summary="获取微服务热更新状态")
async def get_microservices_status():
    """
    获取所有微服务的热更新状态
    """
    try:
        from .microservice_reloader import get_all_microservice_status
        
        status = get_all_microservice_status()
        
        return {
            "success": True,
            "count": len(status),
            "services": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取微服务状态失败: {str(e)}")























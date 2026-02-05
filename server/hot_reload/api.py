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
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

# 添加项目根目录到路径
# api.py 位于 server/hot_reload/，往上 3 层到达项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from .hot_reload_manager import HotReloadManager
from .version_manager import VersionManager
from .worker_sync import trigger_all_workers, get_worker_sync_status

logger = logging.getLogger(__name__)

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


@router.post("/hot-reload/reload-routers", summary="强制重新注册 FastAPI 路由")
async def reload_routers():
    """
    强制重新注册所有 FastAPI 路由
    
    用于修复热更新后路由丢失的问题
    """
    try:
        from server.main import router_manager
        import sys
        import importlib
        
        old_count = len(router_manager.get_registered_routers())
        
        # ⭐ 重要：先重新加载相关路由模块，确保获取最新的路由对象
        # 重新加载可能包含新路由的模块
        modules_to_reload = [
            'server.api.v2.face_analysis',
            'server.api.v2.face_analysis_stream',
            'server.api.v2.desk_fengshui_api',
            'server.api.v2.desk_fengshui_stream',
            'server.main'
        ]
        
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                try:
                    importlib.reload(sys.modules[module_name])
                    logger.info(f"✅ 已重新加载模块: {module_name}")
                except Exception as e:
                    logger.warning(f"⚠️  重新加载模块 {module_name} 失败: {e}")
        
        # ⭐ 重要：如果 server.main 模块已加载，重新执行 _register_all_routers_to_manager
        # 确保新添加的路由信息被注册到 RouterManager
        if 'server.main' in sys.modules:
            main_module = sys.modules['server.main']
            if hasattr(main_module, '_register_all_routers_to_manager'):
                try:
                    main_module._register_all_routers_to_manager()
                    logger.info("✅ 路由信息已重新注册到管理器")
                except Exception as e:
                    logger.warning(f"⚠️  重新注册路由信息到管理器失败: {e}")
        
        # 清除注册状态，强制重新注册所有路由到 FastAPI 应用
        router_manager.clear_registered_state()
        
        # 强制重新注册所有路由
        results = router_manager.register_all_routers(force=True)
        
        new_count = len(router_manager.get_registered_routers())
        
        success_count = sum(1 for success in results.values() if success)
        failed_count = len(results) - success_count
        
        return {
            "success": failed_count == 0,
            "message": f"路由重新注册完成（旧: {old_count}, 新: {new_count}, 成功: {success_count}, 失败: {failed_count}）",
            "old_count": old_count,
            "new_count": new_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
            "registered_routers": router_manager.get_registered_routers()
        }
    except Exception as e:
        logger.error(f"重新注册路由失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新注册路由失败: {str(e)}")


@router.post("/hot-reload/reload-endpoints", summary="强制重新注册 gRPC 端点")
async def reload_endpoints():
    """
    强制重新注册所有 gRPC 端点
    
    用于修复热更新后端点丢失的问题
    """
    try:
        from server.api.grpc_gateway import _reload_endpoints, SUPPORTED_ENDPOINTS, _register
        
        old_count = len(SUPPORTED_ENDPOINTS)
        
        # 先尝试重新加载模块
        success = _reload_endpoints()
        new_count = len(SUPPORTED_ENDPOINTS)
        
        # 如果重新加载后端点数量为0或缺少关键端点，手动注册关键端点
        key_endpoints = ['/bazi/interface', '/bazi/shengong-minggong', '/bazi/rizhu-liujiazi', '/daily-fortune-calendar/query']
        missing_endpoints = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
        
        if new_count == 0 or missing_endpoints:
            logger.warning(f"端点重新加载后数量为0或缺少关键端点（总数: {new_count}, 缺失: {missing_endpoints}），尝试手动注册端点...")
            try:
                # 手动注册每日运势端点
                if "/daily-fortune-calendar/query" in missing_endpoints:
                    from server.api.v1.daily_fortune_calendar import (
                        DailyFortuneCalendarRequest,
                        query_daily_fortune_calendar,
                    )
                    async def _handle_daily_fortune_calendar_query(payload: Dict[str, Any]):
                        """处理每日运势日历查询请求"""
                        request_model = DailyFortuneCalendarRequest(**payload)
                        return await query_daily_fortune_calendar(request_model)
                    SUPPORTED_ENDPOINTS["/daily-fortune-calendar/query"] = _handle_daily_fortune_calendar_query
                    logger.info("✅ 手动注册端点: /daily-fortune-calendar/query")
                
                new_count = len(SUPPORTED_ENDPOINTS)
            except Exception as e:
                logger.error(f"手动注册端点失败: {e}", exc_info=True)
        
        return {
            "success": success or new_count > 0,
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


@router.post("/hot-reload/reload-all", summary="重载所有模块（所有 Worker）")
async def reload_all():
    """
    按顺序重载所有模块（通知所有 Worker）
    
    🔴 重要改进：
    - 之前：只重载处理此请求的单个 worker
    - 现在：通过信号机制通知所有 worker 执行热更新
    
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
        
        # 1. 先在当前 worker 执行重载
        results = reload_all_modules()
        
        success_modules = [m for m, s in results.items() if s]
        failed_modules = [m for m, s in results.items() if not s]
        
        # 2. 🔴 触发所有其他 worker 执行热更新
        sync_result = trigger_all_workers(success_modules)
        
        message = f"重载完成: {len(success_modules)} 成功, {len(failed_modules)} 失败"
        if sync_result.get('success'):
            message += f" | 已通知所有 Worker (version: {sync_result.get('version')})"
        
        return ReloadResponse(
            success=len(failed_modules) == 0,
            message=message,
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
            logger.warning(f"⚠ 集群同步不可用，执行本地回滚: {e}")
            
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


@router.get("/hot-reload/worker-sync", summary="获取多 Worker 同步状态")
async def get_worker_sync():
    """
    获取多 Worker 热更新同步状态
    
    返回：
    - worker_id: 当前处理请求的 worker 进程 ID
    - running: 同步监控是否在运行
    - last_signal_version: 最后处理的信号版本号
    - signal_file: 信号文件路径
    """
    try:
        status = get_worker_sync_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")


@router.post("/hot-reload/trigger-all-workers", summary="触发所有 Worker 热更新")
async def trigger_all_workers_api():
    """
    触发所有 Worker 执行热更新
    
    通过写入信号文件，通知所有 worker 进程执行热更新。
    每个 worker 的后台监控线程会检测到信号并自动执行重载。
    """
    try:
        result = trigger_all_workers()
        return {
            "success": result.get('success', False),
            "message": result.get('message', ''),
            "version": result.get('version'),
            "error": result.get('error')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")























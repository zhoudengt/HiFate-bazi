#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路由注册管理器 - 支持热更新的路由注册

功能：
- 统一管理所有路由的注册
- 支持热更新时重新注册路由
- 避免路由重复注册
- 记录路由注册信息
"""

import sys
import os
import logging
from typing import Optional, Callable, List, Dict, Any, Tuple
from fastapi import FastAPI, APIRouter

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class RouterInfo:
    """路由信息"""
    def __init__(
        self,
        name: str,
        router_getter: Callable[[], Optional[APIRouter]],
        prefix: str = "",
        tags: Optional[List[str]] = None,
        enabled_getter: Optional[Callable[[], bool]] = None
    ):
        self.name = name
        self.router_getter = router_getter
        self.prefix = prefix
        self.tags = tags or []
        self.enabled_getter = enabled_getter
        self._registered = False
    
    def is_enabled(self) -> bool:
        """检查路由是否启用"""
        if self.enabled_getter:
            try:
                return self.enabled_getter()
            except Exception as e:
                logger.warning(f"检查路由 {self.name} 是否启用时出错: {e}")
                return False
        return True
    
    def get_router(self) -> Optional[APIRouter]:
        """获取路由对象"""
        try:
            return self.router_getter()
        except Exception as e:
            logger.warning(f"获取路由 {self.name} 时出错: {e}")
            return None


class RouterManager:
    """路由管理器 - 支持热更新的路由注册"""
    
    _instance: Optional['RouterManager'] = None
    _app: Optional[FastAPI] = None
    
    def __init__(self, app: FastAPI):
        """初始化路由管理器"""
        RouterManager._instance = self
        RouterManager._app = app
        self.app = app
        self.registered_routers: Dict[str, RouterInfo] = {}
        self._route_signatures: Dict[str, Tuple[str, str]] = {}  # 路由签名：{name: (prefix, path)}
        self._registered_route_paths: Dict[str, List[str]] = {}  # 记录每个路由名称对应的路径列表
    
    @classmethod
    def get_instance(cls) -> Optional['RouterManager']:
        """获取单例实例"""
        return cls._instance
    
    def register_router(
        self,
        name: str,
        router_getter: Callable[[], Optional[APIRouter]],
        prefix: str = "",
        tags: Optional[List[str]] = None,
        enabled_getter: Optional[Callable[[], bool]] = None
    ):
        """
        注册路由信息（延迟注册）
        
        Args:
            name: 路由名称（唯一标识）
            router_getter: 获取路由对象的函数
            prefix: 路由前缀
            tags: 路由标签
            enabled_getter: 检查路由是否启用的函数（可选）
        """
        router_info = RouterInfo(name, router_getter, prefix, tags, enabled_getter)
        self.registered_routers[name] = router_info
    
    def _get_route_signature(self, router: APIRouter, prefix: str) -> str:
        """获取路由签名（用于检测重复注册）"""
        # 构建路由的唯一标识
        routes = getattr(router, 'routes', [])
        paths = [getattr(route, 'path', '') for route in routes if hasattr(route, 'path')]
        return f"{prefix}:{':'.join(sorted(set(paths)))}"
    
    def _is_route_registered(self, router: APIRouter, prefix: str) -> bool:
        """检查路由是否已注册"""
        signature = self._get_route_signature(router, prefix)
        
        # 检查 app.routes 中是否已存在相同的路由
        for route in self.app.routes:
            route_path = getattr(route, 'path', '')
            route_methods = getattr(route, 'methods', set())
            
            # 检查是否有相同的路径和方法
            router_routes = getattr(router, 'routes', [])
            for router_route in router_routes:
                router_path = getattr(router_route, 'path', '')
                router_methods = getattr(router_route, 'methods', set())
                
                full_router_path = prefix.rstrip('/') + '/' + router_path.lstrip('/')
                if full_router_path == route_path and router_methods & route_methods:
                    return True
        
        return False
    
    def _remove_router_routes(self, router_name: str, router: APIRouter, prefix: str):
        """
        移除已注册的路由（用于热更新）
        
        注意：FastAPI 的 app.routes 是列表，可以通过修改列表来移除路由
        """
        if router_name not in self._registered_route_paths:
            return
        
        # 获取要移除的路径列表
        paths_to_remove = self._registered_route_paths[router_name]
        
        # 从 app.routes 中移除匹配的路由
        routes_to_keep = []
        for route in self.app.routes:
            route_path = getattr(route, 'path', '')
            # 检查是否是我们要移除的路由
            should_remove = False
            for path_to_remove in paths_to_remove:
                full_path = (prefix.rstrip('/') + '/' + path_to_remove.lstrip('/')).replace('//', '/')
                if route_path == full_path or route_path.startswith(full_path + '/'):
                    should_remove = True
                    break
            
            if not should_remove:
                routes_to_keep.append(route)
        
        # 替换 app.routes（FastAPI 内部使用列表存储路由）
        if hasattr(self.app, 'router'):
            # FastAPI 使用 app.router.routes
            self.app.router.routes[:] = routes_to_keep
        else:
            # 如果直接使用 app.routes
            self.app.routes[:] = routes_to_keep
        
        # 清除记录的路径
        del self._registered_route_paths[router_name]
        logger.info(f"✓ 已移除路由: {router_name} (路径数: {len(paths_to_remove)})")
    
    def _register_single_router(self, router_info: RouterInfo, force: bool = False) -> bool:
        """
        注册单个路由
        
        Args:
            router_info: 路由信息
            force: 是否强制重新注册
        
        Returns:
            bool: 是否成功注册
        """
        try:
            # 检查路由是否启用
            if not router_info.is_enabled():
                logger.debug(f"路由 {router_info.name} 未启用，跳过注册")
                return False
            
            # 获取路由对象（如果是force模式，确保获取的是最新的）
            router = router_info.get_router()
            if router is None:
                logger.warning(f"路由 {router_info.name} 获取失败，跳过注册")
                return False
            
            # 在force模式下，先移除旧路由，再注册新路由
            if force and router_info._registered:
                # 移除旧路由
                self._remove_router_routes(router_info.name, router, router_info.prefix)
                router_info._registered = False
            
            # 记录要注册的路径（用于后续移除）
            router_paths = []
            for route in router.routes:
                if hasattr(route, 'path'):
                    router_paths.append(route.path)
            self._registered_route_paths[router_info.name] = router_paths
            
            # 注册路由
            self.app.include_router(
                router,
                prefix=router_info.prefix,
                tags=router_info.tags
            )
            
            router_info._registered = True
            logger.info(f"✓ 路由已注册: {router_info.name} (prefix: {router_info.prefix}, tags: {router_info.tags}, 路径数: {len(router_paths)})")
            return True
            
        except Exception as e:
            logger.error(f"注册路由 {router_info.name} 失败: {e}", exc_info=True)
            return False
    
    def register_all_routers(self, force: bool = False) -> Dict[str, bool]:
        """
        注册所有路由
        
        Args:
            force: 是否强制重新注册（即使已注册）
        
        Returns:
            Dict[str, bool]: 路由注册结果 {name: success}
        """
        results = {}
        registered_count = 0
        failed_count = 0
        
        logger.info("🔄 开始注册所有路由...")
        
        for name, router_info in self.registered_routers.items():
            # 如果已注册且不是强制模式，跳过
            if router_info._registered and not force:
                results[name] = True
                continue
            
            # 重置注册状态（强制模式下）
            if force:
                router_info._registered = False
            
            # 注册路由（传递force参数）
            success = self._register_single_router(router_info, force=force)
            results[name] = success
            
            if success:
                registered_count += 1
            else:
                failed_count += 1
        
        logger.info(f"✅ 路由注册完成: {registered_count} 成功, {failed_count} 失败")
        
        return results
    
    def get_registered_routers(self) -> List[str]:
        """获取已注册的路由名称列表"""
        return [name for name, info in self.registered_routers.items() if info._registered]
    
    def clear_registered_state(self):
        """清除所有路由的注册状态（用于热更新重新注册）"""
        for router_info in self.registered_routers.values():
            router_info._registered = False


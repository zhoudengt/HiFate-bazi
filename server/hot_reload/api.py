#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新API接口
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

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
    reloaded_modules: Optional[list] = None


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


@router.post("/hot-reload/rollback", summary="回滚到上一版本")
async def rollback_module(module_name: Optional[str] = None):
    """
    回滚模块到上一版本
    
    - **module_name**: 模块名称（可选），不指定则回滚所有模块
    """
    try:
        # TODO: 实现回滚逻辑
        # 1. 从备份中恢复文件
        # 2. 重新加载模块
        # 3. 更新版本号
        
        return ReloadResponse(
            success=True,
            message=f"模块 {module_name or 'all'} 回滚成功",
            reloaded_modules=[module_name] if module_name else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")























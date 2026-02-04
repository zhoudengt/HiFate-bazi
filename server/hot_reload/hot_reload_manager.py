#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新管理器 - 统一管理所有模块的热更新
"""

import sys
import os
import threading
import time
import logging
from typing import Dict, Optional, Callable, Any

# 添加项目根目录到路径
# hot_reload_manager.py 位于 server/hot_reload/，往上 3 层到达项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from .version_manager import VersionManager
from .reloaders import get_reloader
from .file_monitor import get_file_monitor

logger = logging.getLogger(__name__)


class HotReloadManager:
    """热更新管理器 - 统一管理所有模块的热更新"""
    
    _instance: Optional['HotReloadManager'] = None
    _thread: Optional[threading.Thread] = None
    _running: bool = False
    _interval: int = 300  # 默认5分钟检查一次
    _callbacks: Dict[str, Callable] = {}
    
    def __init__(self, interval: int = 300):
        """
        初始化热更新管理器
        
        Args:
            interval: 检查间隔（秒），默认5分钟
        """
        self._interval = interval
        self._running = False
        self._thread = None
    
    @classmethod
    def get_instance(cls, interval: int = 300) -> 'HotReloadManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(interval)
        return cls._instance
    
    def start(self):
        """启动热更新管理器"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        
        # 初始化版本号
        VersionManager.init_versions()
        
        # 启动文件监控器
        try:
            file_monitor = get_file_monitor()
            file_monitor.start(check_interval=5)  # 5秒检查一次
            # 注册文件变化回调
            file_monitor.register_callback(self._on_file_changed)
            logger.info("✓ 文件监控器已启动")
        except Exception as e:
            logger.warning(f"⚠ 文件监控器启动失败: {e}")
        
        logger.info(f"✓ 热更新管理器已启动（检查间隔: {self._interval}秒）")
    
    def stop(self):
        """停止热更新管理器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        
        # 停止文件监控器
        try:
            file_monitor = get_file_monitor()
            file_monitor.stop()
        except Exception:
            pass
        
        logger.info("✓ 热更新管理器已停止")
    
    def _check_loop(self):
        """检查循环"""
        # 启动后立即执行一次检查，然后按间隔循环
        while self._running:
            try:
                self._check_and_reload()
            except Exception as e:
                logger.warning(f"⚠ 热更新检查失败: {e}")
            
            # 等待指定间隔后再次检查
            time.sleep(self._interval)
    
    def _check_and_reload(self):
        """检查并重新加载变化的模块"""
        from datetime import datetime
        
        changes = VersionManager.check_all_modules()
        
        reloaded_modules = []
        changed_modules = [name for name, changed in changes.items() if changed]
        
        # 打印检查日志
        if changed_modules:
            logger.info(f"\n🔍 检测到模块变化: {', '.join(changed_modules)} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        # 注意：即使没有变化，也会在5分钟后再次检查，确保修改代码后5分钟内能检测到
        
        for module_name, changed in changes.items():
            if changed:
                # 获取重载器
                reloader_class = get_reloader(module_name)
                if reloader_class:
                    # 打印模块信息
                    module_descriptions = {
                        'rules': '规则配置',
                        'content': '规则内容',
                        'config': '系统配置',
                        'cache': '缓存数据',
                        'source': 'Python源代码'
                    }
                    description = module_descriptions.get(module_name, '未知模块')
                    logger.info(f"\n📦 开始重载模块: {module_name} ({description})")
                    
                    if reloader_class.reload():
                        reloaded_modules.append(module_name)
                else:
                    logger.warning(f"⚠ 未找到模块 {module_name} 的重载器")
                
                # 执行自定义回调
                if module_name in self._callbacks:
                    try:
                        self._callbacks[module_name]()
                    except Exception as e:
                        logger.warning(f"⚠ 执行 {module_name} 回调失败: {e}")
        
        if reloaded_modules:
            logger.info(f"\n✅ 自动热更新完成: {', '.join(reloaded_modules)} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        elif changed_modules:
            logger.warning(f"⚠ 检测到变化但重载失败: {', '.join(changed_modules)}")
    
    def check_and_reload(self, module_name: Optional[str] = None) -> bool:
        """
        立即检查并重新加载（手动触发）
        
        Args:
            module_name: 模块名称，None表示检查所有模块
            
        Returns:
            bool: 是否有模块被重新加载
        """
        if module_name:
            # 检查指定模块
            if VersionManager.check_version_changed(module_name):
                reloader_class = get_reloader(module_name)
                if reloader_class:
                    return reloader_class.reload()
                return False
        else:
            # 检查所有模块
            self._check_and_reload()
            return True
    
    def register_callback(self, module_name: str, callback: Callable):
        """
        注册模块更新回调
        
        Args:
            module_name: 模块名称
            callback: 回调函数
        """
        self._callbacks[module_name] = callback
    
    def set_interval(self, interval: int):
        """设置检查间隔"""
        self._interval = interval
    
    def get_status(self) -> Dict:
        """获取热更新管理器状态"""
        versions = {}
        for module_name in VersionManager._version_checkers.keys():
            versions[module_name] = {
                'current': VersionManager.get_version(module_name),
                'cached': VersionManager.get_cached_version(module_name),
                'changed': VersionManager.check_version_changed(module_name)
            }
        
        # 获取文件监控状态
        file_status = {}
        try:
            file_monitor = get_file_monitor()
            file_status = {
                'monitored_files': len(file_monitor.get_all_files()),
                'changed_files': len(file_monitor.get_changed_files())
            }
        except Exception:
            pass
        
        return {
            'running': self._running,
            'interval': self._interval,
            'versions': versions,
            'file_monitor': file_status
        }
    
    def _on_file_changed(self, file_path: str, change_type: str, state: Optional[Dict]):
        """
        文件变化回调
        
        Args:
            file_path: 文件路径
            change_type: 变化类型（created/modified/deleted/syntax_error）
            state: 文件状态
        """
        from datetime import datetime
        
        if change_type == 'syntax_error':
            logger.error(f"❌ 检测到语法错误: {file_path} (不会自动更新)")
        elif change_type == 'modified':
            logger.info(f"📝 文件已修改: {file_path}")
            # 如果语法正确，触发源代码版本更新
            if state and state.get('syntax_valid', False):
                # 更新源代码版本号（基于文件修改时间）
                VersionManager.update_cached_version(
                    'source',
                    int(state.get('mtime', 0))
                )
        elif change_type == 'created':
            logger.info(f"➕ 新文件: {file_path}")
        elif change_type == 'deleted':
            logger.info(f"🗑️  文件已删除: {file_path}")




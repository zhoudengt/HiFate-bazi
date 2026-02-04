#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件监控模块 - 监控所有代码文件的变化
支持实时监控、代码完整性检查、语法验证
"""

import os
import logging

logger = logging.getLogger(__name__)
import sys
import time
import hashlib
import ast
import threading
from typing import Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
# file_monitor.py 位于 server/hot_reload/，往上 3 层到达项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class FileMonitor:
    """文件监控器 - 监控所有代码文件的变化"""
    
    def __init__(self, watch_directories: List[str] = None, exclude_patterns: List[str] = None):
        """
        初始化文件监控器
        
        Args:
            watch_directories: 监控的目录列表，默认监控 core、server、services
            exclude_patterns: 排除的文件模式
        """
        self.watch_directories = watch_directories or ['core', 'server', 'services']
        self.exclude_patterns = exclude_patterns or [
            '__pycache__', '.pyc', '.pyo', '.pyd',
            '.mypy_cache', '.pytest_cache', '.git',
            'node_modules', '.venv', 'venv'
        ]
        
        # 文件状态：file_path -> {'mtime': float, 'hash': str, 'syntax_valid': bool}
        self._file_states: Dict[str, Dict] = {}
        self._callbacks: List[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 5  # 默认5秒检查一次
        
    def start(self, check_interval: int = 5):
        """
        启动文件监控
        
        Args:
            check_interval: 检查间隔（秒）
        """
        if self._running:
            return
        
        self._check_interval = check_interval
        self._running = True
        
        # 初始化文件状态
        self._scan_files()
        
        # 启动监控线程
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"✓ 文件监控器已启动（检查间隔: {self._check_interval}秒）")
    
    def stop(self):
        """停止文件监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("✓ 文件监控器已停止")
    
    def register_callback(self, callback: Callable):
        """
        注册文件变化回调
        
        Args:
            callback: 回调函数，接收 (file_path, change_type) 参数
        """
        self._callbacks.append(callback)
    
    def _scan_files(self):
        """扫描所有文件，初始化状态"""
        for directory in self.watch_directories:
            dir_path = os.path.join(project_root, directory)
            if not os.path.exists(dir_path):
                continue
            
            for root, dirs, files in os.walk(dir_path):
                # 排除不需要的目录
                dirs[:] = [d for d in dirs if not any(
                    pattern in d for pattern in self.exclude_patterns
                )]
                
                for filename in files:
                    if not filename.endswith('.py'):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, project_root)
                    
                    # 检查是否应该排除
                    if any(pattern in rel_path for pattern in self.exclude_patterns):
                        continue
                    
                    self._update_file_state(file_path)
    
    def _update_file_state(self, file_path: str) -> Optional[Dict]:
        """
        更新文件状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件状态字典，如果文件不存在或无法读取则返回 None
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            # 获取文件修改时间
            mtime = os.path.getmtime(file_path)
            
            # 计算文件哈希
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            # 检查语法
            syntax_valid = self._check_syntax(file_path)
            
            state = {
                'mtime': mtime,
                'hash': file_hash,
                'syntax_valid': syntax_valid,
                'last_check': time.time()
            }
            
            self._file_states[file_path] = state
            return state
            
        except Exception as e:
            logger.info(f"⚠ 无法读取文件 {file_path}: {e}")
            return None
    
    def _check_syntax(self, file_path: str) -> bool:
        """
        检查Python文件语法
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 语法是否有效
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # 使用AST解析检查语法
            ast.parse(source, filename=file_path)
            return True
        except SyntaxError as e:
            logger.info(f"❌ 语法错误 {file_path}: {e}")
            return False
        except Exception as e:
            logger.info(f"⚠ 检查语法失败 {file_path}: {e}")
            return False
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._check_files()
            except Exception as e:
                logger.info(f"⚠ 文件监控检查失败: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_files(self):
        """检查所有文件的变化"""
        changed_files = []
        
        # 重新扫描文件（处理新增文件）
        for directory in self.watch_directories:
            dir_path = os.path.join(project_root, directory)
            if not os.path.exists(dir_path):
                continue
            
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if not any(
                    pattern in d for pattern in self.exclude_patterns
                )]
                
                for filename in files:
                    if not filename.endswith('.py'):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, project_root)
                    
                    if any(pattern in rel_path for pattern in self.exclude_patterns):
                        continue
                    
                    # 检查文件是否变化
                    old_state = self._file_states.get(file_path)
                    new_state = self._update_file_state(file_path)
                    
                    if new_state is None:
                        continue
                    
                    # 检测变化
                    if old_state is None:
                        # 新文件
                        changed_files.append(('created', file_path, new_state))
                    elif old_state['hash'] != new_state['hash']:
                        # 文件内容变化
                        change_type = 'modified'
                        if not new_state['syntax_valid']:
                            change_type = 'syntax_error'
                        changed_files.append((change_type, file_path, new_state))
        
        # 检查删除的文件
        current_files = set()
        for directory in self.watch_directories:
            dir_path = os.path.join(project_root, directory)
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if not any(
                    pattern in d for pattern in self.exclude_patterns
                )]
                for filename in files:
                    if filename.endswith('.py'):
                        file_path = os.path.join(root, filename)
                        current_files.add(file_path)
        
        for file_path in list(self._file_states.keys()):
            if file_path not in current_files:
                changed_files.append(('deleted', file_path, None))
                del self._file_states[file_path]
        
        # 触发回调
        if changed_files:
            for change_type, file_path, state in changed_files:
                for callback in self._callbacks:
                    try:
                        callback(file_path, change_type, state)
                    except Exception as e:
                        logger.info(f"⚠ 回调执行失败: {e}")
    
    def get_file_status(self, file_path: str) -> Optional[Dict]:
        """获取文件状态"""
        return self._file_states.get(file_path)
    
    def get_all_files(self) -> Dict[str, Dict]:
        """获取所有监控的文件状态"""
        return self._file_states.copy()
    
    def get_changed_files(self) -> List[str]:
        """获取变化的文件列表（需要重新加载的）"""
        changed = []
        for file_path, state in self._file_states.items():
            if not state.get('syntax_valid', True):
                continue  # 跳过语法错误的文件
            
            # 检查是否需要重新加载（基于修改时间）
            mtime = state.get('mtime', 0)
            last_check = state.get('last_check', 0)
            if mtime > last_check:
                changed.append(file_path)
        
        return changed


# 全局文件监控器实例
_file_monitor: Optional[FileMonitor] = None


def get_file_monitor() -> FileMonitor:
    """获取文件监控器单例"""
    global _file_monitor
    if _file_monitor is None:
        _file_monitor = FileMonitor()
    return _file_monitor


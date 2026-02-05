#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多 Worker 热更新同步模块

解决问题：
- uvicorn 多 worker 模式下，热更新只影响单个 worker
- 其他 worker 仍运行旧代码

方案：
- 使用信号文件作为跨进程通信机制
- 热更新 API 被调用时，写入信号文件（包含时间戳和版本号）
- 每个 worker 的后台线程监控信号文件
- 检测到新信号时，该 worker 自动执行热更新

使用方法：
1. 在 main.py 启动时调用 WorkerSyncManager.start()
2. 在 hot-reload API 中调用 WorkerSyncManager.trigger_all_workers()
"""

import os
import sys
import json
import time
import threading
import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class WorkerSyncManager:
    """多 Worker 热更新同步管理器"""
    
    # 信号文件路径（使用 /tmp 确保所有进程可访问）
    SIGNAL_FILE = "/tmp/hifate_hot_reload_signal.json"
    
    # 单例实例
    _instance: Optional['WorkerSyncManager'] = None
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_signal_version = 0
        self._last_signal_time = 0
        self._check_interval = 2  # 每 2 秒检查一次信号文件
        self._reload_callback: Optional[Callable] = None
        self._worker_id = f"{os.getpid()}"
        
    @classmethod
    def get_instance(cls) -> 'WorkerSyncManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def start(self, reload_callback: Callable = None):
        """
        启动 Worker 同步监控
        
        Args:
            reload_callback: 检测到信号时执行的回调函数
        """
        if self._running:
            logger.info(f"[Worker-{self._worker_id}] 同步监控已在运行")
            return
        
        self._reload_callback = reload_callback
        self._running = True
        
        # 初始化：读取当前信号状态
        self._read_current_signal()
        
        # 启动监控线程
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"✓ [Worker-{self._worker_id}] 热更新同步监控已启动")
    
    def stop(self):
        """停止同步监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info(f"✓ [Worker-{self._worker_id}] 热更新同步监控已停止")
    
    def _read_current_signal(self):
        """读取当前信号状态"""
        try:
            if os.path.exists(self.SIGNAL_FILE):
                with open(self.SIGNAL_FILE, 'r') as f:
                    data = json.load(f)
                    self._last_signal_version = data.get('version', 0)
                    self._last_signal_time = data.get('timestamp', 0)
        except Exception as e:
            logger.warning(f"[Worker-{self._worker_id}] 读取信号文件失败: {e}")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._check_signal()
            except Exception as e:
                logger.warning(f"[Worker-{self._worker_id}] 检查信号失败: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_signal(self):
        """检查信号文件"""
        if not os.path.exists(self.SIGNAL_FILE):
            return
        
        try:
            with open(self.SIGNAL_FILE, 'r') as f:
                data = json.load(f)
            
            signal_version = data.get('version', 0)
            signal_time = data.get('timestamp', 0)
            
            # 检查是否有新信号（版本号更大 或 时间戳更新）
            if signal_version > self._last_signal_version or signal_time > self._last_signal_time:
                logger.info(
                    f"🔔 [Worker-{self._worker_id}] 检测到热更新信号 "
                    f"(version: {self._last_signal_version} -> {signal_version})"
                )
                
                # 更新本地状态
                self._last_signal_version = signal_version
                self._last_signal_time = signal_time
                
                # 执行热更新回调
                if self._reload_callback:
                    try:
                        logger.info(f"🔄 [Worker-{self._worker_id}] 开始执行热更新...")
                        self._reload_callback()
                        logger.info(f"✅ [Worker-{self._worker_id}] 热更新完成")
                    except Exception as e:
                        logger.error(f"❌ [Worker-{self._worker_id}] 热更新执行失败: {e}")
                else:
                    logger.warning(f"[Worker-{self._worker_id}] 未设置热更新回调")
                    
        except json.JSONDecodeError as e:
            logger.warning(f"[Worker-{self._worker_id}] 信号文件格式错误: {e}")
        except Exception as e:
            logger.warning(f"[Worker-{self._worker_id}] 读取信号文件失败: {e}")
    
    @classmethod
    def trigger_all_workers(cls, modules: list = None) -> Dict[str, Any]:
        """
        触发所有 worker 执行热更新
        
        通过写入信号文件，通知所有 worker 进程执行热更新
        
        Args:
            modules: 要更新的模块列表（可选，用于记录）
            
        Returns:
            dict: 触发结果
        """
        try:
            # 读取当前版本号
            current_version = 0
            if os.path.exists(cls.SIGNAL_FILE):
                try:
                    with open(cls.SIGNAL_FILE, 'r') as f:
                        data = json.load(f)
                        current_version = data.get('version', 0)
                except:
                    pass
            
            # 写入新信号
            new_version = current_version + 1
            signal_data = {
                'version': new_version,
                'timestamp': time.time(),
                'modules': modules or ['all'],
                'trigger_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'trigger_pid': os.getpid()
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(cls.SIGNAL_FILE) or '/tmp', exist_ok=True)
            
            # 写入信号文件
            with open(cls.SIGNAL_FILE, 'w') as f:
                json.dump(signal_data, f, indent=2)
            
            logger.info(f"📢 热更新信号已广播 (version: {new_version})")
            
            return {
                'success': True,
                'version': new_version,
                'message': f'热更新信号已广播到所有 worker (version: {new_version})'
            }
            
        except Exception as e:
            logger.error(f"❌ 广播热更新信号失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'广播热更新信号失败: {e}'
            }
    
    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'worker_id': self._worker_id,
            'running': self._running,
            'check_interval': self._check_interval,
            'last_signal_version': self._last_signal_version,
            'last_signal_time': self._last_signal_time,
            'signal_file': self.SIGNAL_FILE
        }


# 便捷函数
def start_worker_sync(reload_callback: Callable = None):
    """启动 Worker 同步监控"""
    manager = WorkerSyncManager.get_instance()
    manager.start(reload_callback)
    return manager


def trigger_all_workers(modules: list = None) -> Dict[str, Any]:
    """触发所有 worker 热更新"""
    return WorkerSyncManager.trigger_all_workers(modules)


def get_worker_sync_status() -> Dict[str, Any]:
    """获取同步状态"""
    manager = WorkerSyncManager.get_instance()
    return manager.get_status()

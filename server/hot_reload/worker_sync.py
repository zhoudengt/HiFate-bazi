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
    ACK_DIR = "/tmp/hifate_hot_reload_ack"  # ACK 确认目录
    
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
        self._last_reload_success = None  # 上次重载是否成功
        self._last_reload_time = 0  # 上次重载时间
        
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
                reload_success = False
                if self._reload_callback:
                    try:
                        logger.info(f"🔄 [Worker-{self._worker_id}] 开始执行热更新...")
                        self._reload_callback()
                        reload_success = True
                        self._last_reload_success = True
                        self._last_reload_time = time.time()
                        logger.info(f"✅ [Worker-{self._worker_id}] 热更新完成")
                    except Exception as e:
                        self._last_reload_success = False
                        self._last_reload_time = time.time()
                        logger.error(f"❌ [Worker-{self._worker_id}] 热更新执行失败: {e}")
                else:
                    logger.warning(f"[Worker-{self._worker_id}] 未设置热更新回调")
                
                # 🔴 写入 ACK 确认文件
                self._write_ack(signal_version, reload_success)
                    
        except json.JSONDecodeError as e:
            logger.warning(f"[Worker-{self._worker_id}] 信号文件格式错误: {e}")
        except Exception as e:
            logger.warning(f"[Worker-{self._worker_id}] 读取信号文件失败: {e}")
    
    def _write_ack(self, version: int, success: bool):
        """写入 ACK 确认文件"""
        try:
            os.makedirs(self.ACK_DIR, exist_ok=True)
            ack_file = os.path.join(self.ACK_DIR, f"worker_{self._worker_id}.json")
            ack_data = {
                "worker_id": self._worker_id,
                "version": version,
                "success": success,
                "timestamp": time.time(),
                "ack_time": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(ack_file, 'w') as f:
                json.dump(ack_data, f, indent=2)
        except Exception as e:
            logger.warning(f"[Worker-{self._worker_id}] 写入 ACK 失败: {e}")
    
    @classmethod
    def trigger_all_workers(cls, modules: list = None, wait_ack: bool = True, ack_timeout: float = 10.0) -> Dict[str, Any]:
        """
        触发所有 worker 执行热更新
        
        通过写入信号文件，通知所有 worker 进程执行热更新。
        可选等待 ACK 确认。
        
        Args:
            modules: 要更新的模块列表（可选，用于记录）
            wait_ack: 是否等待 worker 确认（默认 True）
            ack_timeout: ACK 等待超时（秒，默认 10）
            
        Returns:
            dict: 触发结果（含 ACK 统计）
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
            
            # 🔴 清理旧 ACK 文件
            if os.path.exists(cls.ACK_DIR):
                for f in os.listdir(cls.ACK_DIR):
                    try:
                        os.remove(os.path.join(cls.ACK_DIR, f))
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
            
            # 🔴 等待 ACK 确认
            ack_results = {}
            if wait_ack:
                ack_results = cls._wait_for_acks(new_version, ack_timeout)
                ack_count = len(ack_results)
                ack_success = sum(1 for v in ack_results.values() if v.get('success'))
                logger.info(f"📋 Worker ACK: {ack_success}/{ack_count} 成功确认")
            
            return {
                'success': True,
                'version': new_version,
                'message': f'热更新信号已广播到所有 worker (version: {new_version})',
                'ack': ack_results
            }
            
        except Exception as e:
            logger.error(f"❌ 广播热更新信号失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'广播热更新信号失败: {e}'
            }
    
    @classmethod
    def _wait_for_acks(cls, version: int, timeout: float) -> Dict[str, Any]:
        """
        等待 worker ACK 确认
        
        Args:
            version: 信号版本号
            timeout: 超时时间（秒）
            
        Returns:
            各 worker 的 ACK 状态
        """
        start = time.time()
        acks = {}
        
        while time.time() - start < timeout:
            if os.path.exists(cls.ACK_DIR):
                for fname in os.listdir(cls.ACK_DIR):
                    if not fname.endswith('.json'):
                        continue
                    fpath = os.path.join(cls.ACK_DIR, fname)
                    try:
                        with open(fpath, 'r') as f:
                            data = json.load(f)
                        worker_id = data.get('worker_id', fname)
                        if data.get('version') == version and worker_id not in acks:
                            acks[worker_id] = data
                    except:
                        pass
            
            # 如果已经收到至少 1 个 ACK 且等了至少 3 秒，可以提前结束
            if acks and (time.time() - start) >= 3:
                # 再等 1 秒看有没有新的
                time.sleep(1)
                # 再检查一次
                if os.path.exists(cls.ACK_DIR):
                    for fname in os.listdir(cls.ACK_DIR):
                        if not fname.endswith('.json'):
                            continue
                        fpath = os.path.join(cls.ACK_DIR, fname)
                        try:
                            with open(fpath, 'r') as f:
                                data = json.load(f)
                            worker_id = data.get('worker_id', fname)
                            if data.get('version') == version and worker_id not in acks:
                                acks[worker_id] = data
                        except:
                            pass
                break
            
            time.sleep(0.5)
        
        return acks
    
    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'worker_id': self._worker_id,
            'running': self._running,
            'check_interval': self._check_interval,
            'last_signal_version': self._last_signal_version,
            'last_signal_time': self._last_signal_time,
            'last_reload_success': self._last_reload_success,
            'last_reload_time': self._last_reload_time,
            'signal_file': self.SIGNAL_FILE,
            'ack_dir': self.ACK_DIR
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

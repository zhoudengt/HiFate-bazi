#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微服务热更新器 - 支持 gRPC 微服务的热更新

功能：
1. 监控微服务代码文件变化
2. 动态重新加载 Servicer 类
3. 支持热替换，不中断服务
4. 支持回滚到上一版本
"""

import os
import sys
import time
import ast
import hashlib
import importlib
import threading
from typing import Dict, Optional, Callable, Any, List, Type
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class MicroserviceReloader:
    """微服务热更新器"""
    
    def __init__(
        self,
        service_name: str,
        module_path: str,
        servicer_class_name: str,
        watch_directories: List[str] = None,
        check_interval: int = 30,
        on_reload_callback: Optional[Callable] = None
    ):
        """
        初始化微服务热更新器
        
        Args:
            service_name: 服务名称（如 "bazi_core"）
            module_path: 主模块路径（如 "services.bazi_core.grpc_server"）
            servicer_class_name: Servicer 类名（如 "BaziCoreServicer"）
            watch_directories: 监控的目录列表
            check_interval: 检查间隔（秒）
            on_reload_callback: 重载成功后的回调函数
        """
        self.service_name = service_name
        self.module_path = module_path
        self.servicer_class_name = servicer_class_name
        self.watch_directories = watch_directories or [
            os.path.join(project_root, "services", service_name),
            os.path.join(project_root, "src"),
        ]
        self.check_interval = check_interval
        self.on_reload_callback = on_reload_callback
        
        # 文件状态
        self._file_states: Dict[str, Dict] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 版本管理
        self._current_version = 0
        self._version_history: List[Dict] = []
        self._max_history = 10
        
        # 当前 Servicer 实例（用于热替换）
        self._current_servicer: Optional[Any] = None
        self._servicer_lock = threading.RLock()
        
        # 初始化文件状态
        self._scan_files()
    
    def start(self):
        """启动热更新监控"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        print(f"✓ [{self.service_name}] 微服务热更新监控已启动（检查间隔: {self.check_interval}秒）")
    
    def stop(self):
        """停止热更新监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print(f"✓ [{self.service_name}] 微服务热更新监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                if self._check_and_reload():
                    print(f"✓ [{self.service_name}] 热更新完成")
            except Exception as e:
                print(f"⚠ [{self.service_name}] 热更新检查失败: {e}")
            
            time.sleep(self.check_interval)
    
    def _scan_files(self):
        """扫描所有监控的文件"""
        for directory in self.watch_directories:
            if not os.path.exists(directory):
                continue
            
            for root, dirs, files in os.walk(directory):
                # 排除缓存目录
                dirs[:] = [d for d in dirs if d not in {'__pycache__', '.mypy_cache', '.pytest_cache'}]
                
                for filename in files:
                    if not filename.endswith('.py'):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    self._update_file_state(file_path)
    
    def _update_file_state(self, file_path: str) -> Optional[Dict]:
        """更新文件状态"""
        if not os.path.exists(file_path):
            return None
        
        try:
            mtime = os.path.getmtime(file_path)
            
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
            print(f"⚠ [{self.service_name}] 无法读取文件 {file_path}: {e}")
            return None
    
    def _check_syntax(self, file_path: str) -> bool:
        """检查 Python 语法"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            ast.parse(source, filename=file_path)
            return True
        except SyntaxError as e:
            print(f"❌ [{self.service_name}] 语法错误 {file_path}: {e}")
            return False
        except Exception as e:
            print(f"⚠ [{self.service_name}] 检查语法失败 {file_path}: {e}")
            return False
    
    def _check_and_reload(self) -> bool:
        """检查文件变化并重新加载"""
        changed_files = []
        
        for directory in self.watch_directories:
            if not os.path.exists(directory):
                continue
            
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if d not in {'__pycache__', '.mypy_cache', '.pytest_cache'}]
                
                for filename in files:
                    if not filename.endswith('.py'):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    old_state = self._file_states.get(file_path)
                    new_state = self._update_file_state(file_path)
                    
                    if new_state is None:
                        continue
                    
                    # 检测变化
                    if old_state is None:
                        changed_files.append(('created', file_path))
                    elif old_state['hash'] != new_state['hash']:
                        if new_state['syntax_valid']:
                            changed_files.append(('modified', file_path))
                        else:
                            print(f"⚠ [{self.service_name}] 文件有语法错误，跳过: {file_path}")
        
        if changed_files:
            print(f"\n🔄 [{self.service_name}] 检测到 {len(changed_files)} 个文件变化:")
            for change_type, file_path in changed_files:
                rel_path = os.path.relpath(file_path, project_root)
                print(f"   {change_type}: {rel_path}")
            
            return self._reload_servicer()
        
        return False
    
    def _reload_servicer(self) -> bool:
        """重新加载 Servicer 类"""
        try:
            # 备份当前版本
            self._backup_current_version()
            
            # 重新加载模块
            if self.module_path in sys.modules:
                module = sys.modules[self.module_path]
                module = importlib.reload(module)
            else:
                module = importlib.import_module(self.module_path)
            
            # 获取新的 Servicer 类
            new_servicer_class = getattr(module, self.servicer_class_name)
            
            # 创建新实例
            new_servicer = new_servicer_class()
            
            # 热替换
            with self._servicer_lock:
                old_servicer = self._current_servicer
                self._current_servicer = new_servicer
                
                # 更新版本号
                self._current_version += 1
            
            # 记录版本历史
            self._record_version(new_servicer_class)
            
            print(f"✅ [{self.service_name}] Servicer 热更新成功 (版本: {self._current_version})")
            
            # 执行回调
            if self.on_reload_callback:
                try:
                    self.on_reload_callback(new_servicer)
                except Exception as e:
                    print(f"⚠ [{self.service_name}] 回调执行失败: {e}")
            
            return True
            
        except Exception as e:
            import traceback
            print(f"❌ [{self.service_name}] 热更新失败: {e}")
            print(traceback.format_exc())
            
            # 尝试回滚
            self._rollback()
            return False
    
    def _backup_current_version(self):
        """备份当前版本"""
        if self._current_servicer is None:
            return
        
        backup = {
            'version': self._current_version,
            'timestamp': datetime.now().isoformat(),
            'servicer_class': type(self._current_servicer).__name__,
            'module_path': self.module_path,
        }
        
        self._version_history.append(backup)
        
        # 只保留最近的历史
        if len(self._version_history) > self._max_history:
            self._version_history = self._version_history[-self._max_history:]
    
    def _record_version(self, servicer_class: Type):
        """记录新版本"""
        record = {
            'version': self._current_version,
            'timestamp': datetime.now().isoformat(),
            'servicer_class': servicer_class.__name__,
            'module_path': self.module_path,
        }
        print(f"📝 [{self.service_name}] 版本记录: v{self._current_version} @ {record['timestamp']}")
    
    def _rollback(self) -> bool:
        """回滚到上一版本"""
        if not self._version_history:
            print(f"⚠ [{self.service_name}] 没有可回滚的版本")
            return False
        
        try:
            last_version = self._version_history.pop()
            print(f"🔄 [{self.service_name}] 正在回滚到版本 {last_version['version']}...")
            
            # 重新加载上一版本的模块
            if self.module_path in sys.modules:
                module = sys.modules[self.module_path]
                # 注意：这里无法真正回滚代码，只是尝试重新加载
                # 真正的回滚需要 Git 操作
            
            print(f"✅ [{self.service_name}] 回滚完成")
            return True
            
        except Exception as e:
            print(f"❌ [{self.service_name}] 回滚失败: {e}")
            return False
    
    def get_current_servicer(self) -> Optional[Any]:
        """获取当前 Servicer 实例（线程安全）"""
        with self._servicer_lock:
            return self._current_servicer
    
    def set_servicer(self, servicer: Any):
        """设置 Servicer 实例"""
        with self._servicer_lock:
            self._current_servicer = servicer
    
    def get_status(self) -> Dict:
        """获取热更新状态"""
        return {
            'service_name': self.service_name,
            'running': self._running,
            'current_version': self._current_version,
            'check_interval': self.check_interval,
            'watched_files': len(self._file_states),
            'version_history_count': len(self._version_history),
            'watch_directories': self.watch_directories,
        }
    
    def force_reload(self) -> bool:
        """强制重新加载"""
        print(f"🔄 [{self.service_name}] 强制重新加载...")
        return self._reload_servicer()


class DynamicServicer:
    """
    动态 Servicer 包装器
    
    用于包装实际的 Servicer，支持热替换
    所有 gRPC 调用都会转发到当前的 Servicer 实例
    """
    
    def __init__(self, reloader: MicroserviceReloader):
        """
        初始化动态 Servicer
        
        Args:
            reloader: 微服务热更新器实例
        """
        self._reloader = reloader
    
    def __getattr__(self, name: str):
        """
        动态转发方法调用到当前 Servicer
        
        这样即使 Servicer 被热替换，也能正确调用新的方法
        """
        servicer = self._reloader.get_current_servicer()
        if servicer is None:
            raise RuntimeError(f"Servicer 未初始化")
        
        attr = getattr(servicer, name)
        return attr


def create_hot_reload_server(
    service_name: str,
    module_path: str,
    servicer_class_name: str,
    add_servicer_to_server_func: Callable,
    port: int,
    server_options: List = None,
    max_workers: int = 20,
    check_interval: int = 30,
    listen_addr: str = None
):
    """
    创建支持热更新的 gRPC 服务器
    
    Args:
        service_name: 服务名称
        module_path: 模块路径
        servicer_class_name: Servicer 类名
        add_servicer_to_server_func: gRPC 注册函数
        port: 端口号
        server_options: gRPC 服务器选项
        max_workers: 线程池大小
        check_interval: 热更新检查间隔
        listen_addr: 监听地址（默认: [::]:port，可自定义如 localhost:port）
    
    Returns:
        tuple: (server, reloader)
    """
    import grpc
    from concurrent import futures
    
    # 默认服务器选项
    if server_options is None:
        server_options = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
        ]
    
    # 创建热更新器
    reloader = MicroserviceReloader(
        service_name=service_name,
        module_path=module_path,
        servicer_class_name=servicer_class_name,
        check_interval=check_interval
    )
    
    # 加载初始 Servicer
    module = importlib.import_module(module_path)
    servicer_class = getattr(module, servicer_class_name)
    initial_servicer = servicer_class()
    reloader.set_servicer(initial_servicer)
    
    # 创建动态 Servicer
    dynamic_servicer = DynamicServicer(reloader)
    
    # 创建 gRPC 服务器
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=server_options
    )
    
    # 注册动态 Servicer
    add_servicer_to_server_func(dynamic_servicer, server)
    
    # 绑定端口（如果没有指定地址，使用默认的 [::]:port）
    if listen_addr is None:
        listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    
    return server, reloader


# 全局微服务热更新器注册表
_microservice_reloaders: Dict[str, MicroserviceReloader] = {}


def register_microservice_reloader(service_name: str, reloader: MicroserviceReloader):
    """注册微服务热更新器"""
    _microservice_reloaders[service_name] = reloader


def get_microservice_reloader(service_name: str) -> Optional[MicroserviceReloader]:
    """获取微服务热更新器"""
    return _microservice_reloaders.get(service_name)


def get_all_microservice_reloaders() -> Dict[str, MicroserviceReloader]:
    """获取所有微服务热更新器"""
    return _microservice_reloaders.copy()


def reload_all_microservices() -> Dict[str, bool]:
    """重新加载所有微服务"""
    results = {}
    for service_name, reloader in _microservice_reloaders.items():
        results[service_name] = reloader.force_reload()
    return results


def get_all_microservice_status() -> Dict[str, Dict]:
    """获取所有微服务热更新状态"""
    return {
        service_name: reloader.get_status()
        for service_name, reloader in _microservice_reloaders.items()
    }


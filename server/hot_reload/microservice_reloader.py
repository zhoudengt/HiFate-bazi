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
        
        # 代码备份目录
        self._backup_dir = os.path.join(project_root, ".hot_reload_backups", service_name)
        os.makedirs(self._backup_dir, exist_ok=True)
        
        # 错误日志目录
        self._error_log_dir = os.path.join(project_root, "logs", "hot_reload_errors")
        os.makedirs(self._error_log_dir, exist_ok=True)
        
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
    
    def _update_file_state(self, file_path: str, force_hash: bool = False) -> Optional[Dict]:
        """
        更新文件状态（优化版本：优先使用修改时间）
        
        Args:
            file_path: 文件路径
            force_hash: 是否强制计算哈希（用于确认变化）
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            mtime = os.path.getmtime(file_path)
            old_state = self._file_states.get(file_path)
            
            # 优化：如果修改时间没变，直接返回旧状态（避免重复计算）
            if old_state and not force_hash:
                if old_state['mtime'] == mtime:
                    # 更新检查时间
                    old_state['last_check'] = time.time()
                    return old_state
            
            # 只有在修改时间变化时才计算哈希（性能优化）
            file_hash = None
            if force_hash or (old_state and old_state['mtime'] != mtime):
                # 只读取文件一次，同时计算哈希和检查语法
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    file_hash = hashlib.md5(file_content).hexdigest()
                
                # 检查语法（使用已读取的内容）
                syntax_valid = self._check_syntax_content(file_content, file_path)
            else:
                # 如果修改时间没变，使用旧的语法检查结果
                syntax_valid = old_state.get('syntax_valid', True) if old_state else True
                file_hash = old_state.get('hash') if old_state else None
            
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
    
    def _check_syntax_content(self, content: bytes, file_path: str) -> bool:
        """检查文件内容语法（使用已读取的内容）"""
        try:
            source = content.decode('utf-8')
            ast.parse(source, filename=file_path)
            return True
        except SyntaxError as e:
            print(f"❌ [{self.service_name}] 语法错误 {file_path}: {e}")
            return False
        except Exception as e:
            print(f"⚠ [{self.service_name}] 检查语法失败 {file_path}: {e}")
            return False
    
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
                    
                    # 先快速检查修改时间（不计算哈希）
                    new_state = self._update_file_state(file_path, force_hash=False)
                    
                    if new_state is None:
                        continue
                    
                    # 检测变化（优先使用修改时间，性能更好）
                    if old_state is None:
                        # 新文件，需要计算哈希确认
                        new_state = self._update_file_state(file_path, force_hash=True)
                        if new_state and new_state['syntax_valid']:
                            changed_files.append(('created', file_path))
                    elif old_state['mtime'] != new_state['mtime']:
                        # 修改时间变化，计算哈希确认
                        new_state = self._update_file_state(file_path, force_hash=True)
                        if new_state and new_state['hash'] != old_state.get('hash'):
                            if new_state['syntax_valid']:
                                changed_files.append(('modified', file_path))
                            else:
                                print(f"⚠ [{self.service_name}] 文件有语法错误，跳过: {file_path}")
        
        if changed_files:
            print(f"\n🔄 [{self.service_name}] 检测到 {len(changed_files)} 个文件变化:")
            for change_type, file_path in changed_files:
                rel_path = os.path.relpath(file_path, project_root)
                print(f"   {change_type}: {rel_path}")
            
            # 检查是否是共享文件变化，如果是，触发所有依赖服务
            for change_type, file_path in changed_files:
                rel_path = os.path.relpath(file_path, project_root)
                # 如果变化的是共享文件（src/ 或 server/），触发依赖服务
                if rel_path.startswith('src/') or rel_path.startswith('server/'):
                    trigger_dependent_services(rel_path)
            
            return self._reload_servicer()
        
        return False
    
    def _reload_servicer(self) -> bool:
        """重新加载 Servicer 类"""
        try:
            # 备份当前版本（包括代码文件）
            backup_info = self._backup_current_version()
            
            # 重新加载模块
            if self.module_path in sys.modules:
                module = sys.modules[self.module_path]
                module = importlib.reload(module)
            else:
                module = importlib.import_module(self.module_path)
            
            # 获取新的 Servicer 类
            new_servicer_class = getattr(module, self.servicer_class_name)
            
            # 检查并重置依赖对象的全局状态
            self._reset_dependency_states(old_servicer)
            
            # 重置单例（使用 SingletonReloader）
            try:
                from server.hot_reload.reloaders import SingletonReloader
                SingletonReloader.reload()
            except Exception as e:
                print(f"⚠ [{self.service_name}] 单例重置失败: {e}")
            
            # 创建新实例（在锁外创建，避免长时间持锁）
            new_servicer = new_servicer_class()
            
            # 验证新实例是否可用
            if not self._validate_servicer(new_servicer):
                raise RuntimeError("新 Servicer 实例验证失败")
            
            # 原子替换（使用双重检查锁定模式）
            with self._servicer_lock:
                # 再次检查是否有其他线程已经更新
                if self._current_version != backup_info.get('version', self._current_version):
                    print(f"⚠ [{self.service_name}] 检测到并发更新，跳过本次更新")
                    return False
                
                # 原子替换：先更新版本号，再替换实例（确保一致性）
                old_servicer = self._current_servicer
                self._current_version += 1
                self._current_servicer = new_servicer
            
            # 清除 DynamicServicer 的方法缓存（如果有）
            # 注意：这里无法直接访问 DynamicServicer，但可以通过回调通知
            
            # 记录版本历史（包含备份信息）
            self._record_version(new_servicer_class, backup_info)
            
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
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            
            # 记录详细错误日志
            error_log = {
                'service_name': self.service_name,
                'error': error_msg,
                'traceback': error_traceback,
                'timestamp': datetime.now().isoformat(),
                'version': self._current_version,
                'module_path': self.module_path,
            }
            
            # 打印错误信息
            print(f"❌ [{self.service_name}] 热更新失败: {error_msg}")
            print(error_traceback)
            
            # 保存错误日志到文件
            self._save_error_log(error_log)
            
            # 发送告警（如果有配置）
            self._send_alert(error_log)
            
            # 尝试回滚
            rollback_success = self._rollback()
            if not rollback_success:
                critical_error = {
                    **error_log,
                    'rollback_failed': True,
                    'status': 'CRITICAL'
                }
                print(f"⚠ [{self.service_name}] 回滚失败，服务可能处于不稳定状态")
                self._save_error_log(critical_error, is_critical=True)
                self._send_alert(critical_error, is_critical=True)
            
            return False
    
    def _backup_current_version(self) -> Dict:
        """备份当前版本（包括代码文件）"""
        backup_info = {
            'version': self._current_version,
            'timestamp': datetime.now().isoformat(),
            'servicer_class': type(self._current_servicer).__name__ if self._current_servicer else None,
            'module_path': self.module_path,
            'backup_files': []
        }
        
        # 备份所有监控的文件
        version_backup_dir = os.path.join(self._backup_dir, f"v{self._current_version}")
        os.makedirs(version_backup_dir, exist_ok=True)
        
        for file_path in self._file_states.keys():
            if not os.path.exists(file_path):
                continue
            
            try:
                # 计算相对路径
                rel_path = os.path.relpath(file_path, project_root)
                backup_file_path = os.path.join(version_backup_dir, rel_path.replace(os.sep, '_'))
                
                # 创建备份目录
                os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                
                # 复制文件
                import shutil
                shutil.copy2(file_path, backup_file_path)
                
                backup_info['backup_files'].append({
                    'original': file_path,
                    'backup': backup_file_path,
                    'rel_path': rel_path
                })
            except Exception as e:
                print(f"⚠ [{self.service_name}] 备份文件失败 {file_path}: {e}")
        
        # 保存备份信息
        backup_info_file = os.path.join(version_backup_dir, 'backup_info.json')
        try:
            import json
            with open(backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠ [{self.service_name}] 保存备份信息失败: {e}")
        
        # 添加到历史记录
        self._version_history.append(backup_info)
        
        # 只保留最近的历史
        if len(self._version_history) > self._max_history:
            # 删除最旧的备份
            oldest = self._version_history.pop(0)
            self._cleanup_backup(oldest)
            self._version_history = self._version_history[-self._max_history:]
        
        return backup_info
    
    def _cleanup_backup(self, backup_info: Dict):
        """清理备份文件"""
        try:
            version = backup_info.get('version', 0)
            version_backup_dir = os.path.join(self._backup_dir, f"v{version}")
            if os.path.exists(version_backup_dir):
                import shutil
                shutil.rmtree(version_backup_dir)
        except Exception as e:
            print(f"⚠ [{self.service_name}] 清理备份失败: {e}")
    
    def _reset_dependency_states(self, old_servicer: Optional[Any]):
        """重置依赖对象的全局状态"""
        if old_servicer is None:
            return
        
        try:
            # 检查 Servicer 实例的属性，查找可能的依赖对象
            servicer_attrs = dir(old_servicer)
            reset_count = 0
            
            for attr_name in servicer_attrs:
                if attr_name.startswith('_'):
                    continue
                
                try:
                    attr_value = getattr(old_servicer, attr_name, None)
                    if attr_value is None:
                        continue
                    
                    # 检查是否是单例对象
                    if self._is_singleton(attr_value):
                        reset_count += self._reset_singleton(attr_value, attr_name)
                    
                    # 检查是否有 reset() 方法
                    if hasattr(attr_value, 'reset') and callable(getattr(attr_value, 'reset')):
                        try:
                            attr_value.reset()
                            print(f"   ✓ 重置依赖对象: {attr_name}.reset()")
                            reset_count += 1
                        except Exception as e:
                            print(f"   ⚠ 重置依赖对象失败 {attr_name}.reset(): {e}")
                    
                    # 检查是否有 clear_cache() 方法
                    if hasattr(attr_value, 'clear_cache') and callable(getattr(attr_value, 'clear_cache')):
                        try:
                            attr_value.clear_cache()
                            print(f"   ✓ 清理依赖对象缓存: {attr_name}.clear_cache()")
                            reset_count += 1
                        except Exception as e:
                            print(f"   ⚠ 清理依赖对象缓存失败 {attr_name}.clear_cache(): {e}")
                            
                except Exception as e:
                    # 忽略无法访问的属性
                    continue
            
            if reset_count > 0:
                print(f"   📊 重置了 {reset_count} 个依赖对象")
                
        except Exception as e:
            print(f"⚠ [{self.service_name}] 重置依赖对象状态失败: {e}")
    
    def _is_singleton(self, obj: Any) -> bool:
        """检查对象是否是单例模式"""
        try:
            # 检查是否有 _instance 类属性
            obj_class = type(obj)
            if hasattr(obj_class, '_instance'):
                return True
            
            # 检查是否有 get_instance 类方法
            if hasattr(obj_class, 'get_instance'):
                return True
            
            return False
        except:
            return False
    
    def _reset_singleton(self, singleton_obj: Any, attr_name: str) -> int:
        """重置单例对象"""
        reset_count = 0
        try:
            obj_class = type(singleton_obj)
            
            # 尝试重置 _instance
            if hasattr(obj_class, '_instance'):
                obj_class._instance = None
                print(f"   ✓ 重置单例: {attr_name}._instance = None")
                reset_count += 1
            
            # 尝试调用 reset() 方法
            if hasattr(singleton_obj, 'reset') and callable(getattr(singleton_obj, 'reset')):
                try:
                    singleton_obj.reset()
                    print(f"   ✓ 调用单例重置方法: {attr_name}.reset()")
                    reset_count += 1
                except Exception as e:
                    print(f"   ⚠ 调用单例重置方法失败 {attr_name}.reset(): {e}")
            
        except Exception as e:
            print(f"   ⚠ 重置单例失败 {attr_name}: {e}")
        
        return reset_count
    
    def _save_error_log(self, error_log: Dict, is_critical: bool = False):
        """保存错误日志到文件"""
        try:
            import json
            log_file = os.path.join(
                self._error_log_dir,
                f"{self.service_name}_{'CRITICAL' if is_critical else 'ERROR'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(error_log, f, ensure_ascii=False, indent=2)
            
            # 只保留最近 50 个错误日志
            self._cleanup_error_logs()
        except Exception as e:
            print(f"⚠ [{self.service_name}] 保存错误日志失败: {e}")
    
    def _cleanup_error_logs(self):
        """清理旧的错误日志"""
        try:
            import glob
            log_files = glob.glob(os.path.join(self._error_log_dir, f"{self.service_name}_*.json"))
            log_files.sort(key=os.path.getmtime, reverse=True)
            
            # 只保留最近 50 个
            if len(log_files) > 50:
                for old_log in log_files[50:]:
                    try:
                        os.remove(old_log)
                    except:
                        pass
        except Exception as e:
            print(f"⚠ [{self.service_name}] 清理错误日志失败: {e}")
    
    def _send_alert(self, error_log: Dict, is_critical: bool = False):
        """发送告警（可扩展：邮件、钉钉、企业微信等）"""
        try:
            # 检查是否配置了告警
            alert_enabled = os.getenv("HOT_RELOAD_ALERT_ENABLED", "false").lower() == "true"
            if not alert_enabled:
                return
            
            # 这里可以扩展为发送邮件、钉钉、企业微信等
            # 目前只打印告警信息
            alert_level = "🚨 CRITICAL" if is_critical else "⚠️ WARNING"
            print(f"{alert_level} [{self.service_name}] 热更新告警:")
            print(f"   错误: {error_log.get('error', 'Unknown')}")
            print(f"   时间: {error_log.get('timestamp', 'Unknown')}")
            
            # TODO: 实现实际的告警发送逻辑
            # if alert_webhook:
            #     send_webhook_alert(alert_webhook, error_log)
            
        except Exception as e:
            print(f"⚠ [{self.service_name}] 发送告警失败: {e}")
    
    def _validate_servicer(self, servicer: Any) -> bool:
        """验证 Servicer 实例是否可用"""
        try:
            # 检查是否有必需的属性或方法
            if not hasattr(servicer, '__class__'):
                return False
            
            # 检查是否有 HealthCheck 方法（大多数 gRPC Servicer 都有）
            if hasattr(servicer, 'HealthCheck'):
                # 尝试调用（不传参数，只检查是否可调用）
                if not callable(getattr(servicer, 'HealthCheck')):
                    return False
            
            return True
        except Exception as e:
            print(f"⚠ [{self.service_name}] Servicer 验证失败: {e}")
            return False
    
    def _record_version(self, servicer_class: Type, backup_info: Dict = None):
        """记录新版本"""
        record = {
            'version': self._current_version,
            'timestamp': datetime.now().isoformat(),
            'servicer_class': servicer_class.__name__,
            'module_path': self.module_path,
            'backup_info': backup_info
        }
        print(f"📝 [{self.service_name}] 版本记录: v{self._current_version} @ {record['timestamp']}")
    
    def _rollback(self) -> bool:
        """回滚到上一版本"""
        if not self._version_history:
            print(f"⚠ [{self.service_name}] 没有可回滚的版本，尝试使用 Git 回滚...")
            return self._rollback_via_git()
        
        try:
            last_version = self._version_history[-1]  # 不删除，保留在历史中
            print(f"🔄 [{self.service_name}] 正在回滚到版本 {last_version['version']}...")
            
            # 恢复备份的文件
            backup_files = last_version.get('backup_files', [])
            if backup_files:
                restored_count = 0
                for file_info in backup_files:
                    try:
                        backup_path = file_info['backup']
                        original_path = file_info['original']
                        
                        if os.path.exists(backup_path):
                            import shutil
                            shutil.copy2(backup_path, original_path)
                            restored_count += 1
                            print(f"   ✓ 恢复: {file_info['rel_path']}")
                        else:
                            print(f"   ⚠ 备份文件不存在: {backup_path}")
                    except Exception as e:
                        print(f"   ❌ 恢复文件失败 {file_info['rel_path']}: {e}")
                
                print(f"   📊 恢复了 {restored_count}/{len(backup_files)} 个文件")
            
            # 重新加载模块
            if self.module_path in sys.modules:
                module = sys.modules[self.module_path]
                module = importlib.reload(module)
            else:
                module = importlib.import_module(self.module_path)
            
            # 获取 Servicer 类并创建实例
            servicer_class = getattr(module, self.servicer_class_name)
            new_servicer = servicer_class()
            
            # 替换 Servicer
            with self._servicer_lock:
                self._current_servicer = new_servicer
                # 不减少版本号，因为这是回滚操作
            
            # 更新文件状态
            self._scan_files()
            
            print(f"✅ [{self.service_name}] 回滚完成")
            return True
            
        except Exception as e:
            import traceback
            print(f"❌ [{self.service_name}] 回滚失败: {e}")
            print(traceback.format_exc())
            
            # 如果文件回滚失败，尝试 Git 回滚
            print(f"🔄 [{self.service_name}] 尝试使用 Git 回滚...")
            return self._rollback_via_git()
    
    def _rollback_via_git(self) -> bool:
        """使用 Git 回滚代码"""
        try:
            import subprocess
            
            # 检查是否在 Git 仓库中
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠ [{self.service_name}] 不在 Git 仓库中，无法使用 Git 回滚")
                return False
            
            # 获取主模块文件路径
            module_file = self.module_path.replace('.', os.sep) + '.py'
            module_file_path = os.path.join(project_root, module_file)
            
            if not os.path.exists(module_file_path):
                print(f"⚠ [{self.service_name}] 模块文件不存在: {module_file_path}")
                return False
            
            # 使用 Git checkout 恢复文件
            print(f"🔄 [{self.service_name}] 使用 Git 恢复文件: {module_file}")
            result = subprocess.run(
                ['git', 'checkout', 'HEAD', '--', module_file],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 重新加载模块
                if self.module_path in sys.modules:
                    module = sys.modules[self.module_path]
                    module = importlib.reload(module)
                else:
                    module = importlib.import_module(self.module_path)
                
                servicer_class = getattr(module, self.servicer_class_name)
                new_servicer = servicer_class()
                
                with self._servicer_lock:
                    self._current_servicer = new_servicer
                
                self._scan_files()
                
                print(f"✅ [{self.service_name}] Git 回滚完成")
                return True
            else:
                print(f"❌ [{self.service_name}] Git 回滚失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ [{self.service_name}] Git 回滚异常: {e}")
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
        # 缓存方法引用（可选优化）
        self._method_cache: Dict[str, Any] = {}
        self._cache_lock = threading.RLock()
    
    def __getattribute__(self, name: str):
        """
        动态转发方法调用到当前 Servicer
        
        使用 __getattribute__ 确保所有属性访问都经过这里
        但需要小心处理内部属性，避免无限递归
        """
        # 处理内部属性（避免无限递归）
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        
        # 获取 reloader（使用 object.__getattribute__ 避免递归）
        reloader = object.__getattribute__(self, '_reloader')
        method_cache = object.__getattribute__(self, '_method_cache')
        cache_lock = object.__getattribute__(self, '_cache_lock')
        
        # 获取当前 Servicer
        servicer = reloader.get_current_servicer()
        if servicer is None:
            raise RuntimeError(f"Servicer 未初始化")
        
        # 尝试从缓存获取
        with cache_lock:
            if name in method_cache:
                cached_method = method_cache[name]
                # 验证缓存的方法是否仍然有效（检查 Servicer 是否改变）
                if hasattr(cached_method, '__self__') and cached_method.__self__ is servicer:
                    return cached_method
        
        # 从 Servicer 获取属性/方法
        try:
            attr = getattr(servicer, name)
            
            # 如果是可调用对象（方法），缓存它
            if callable(attr):
                # 使用 types.MethodType 创建绑定方法，确保每次调用都使用最新的 Servicer
                import types
                if isinstance(attr, types.MethodType):
                    # 重新绑定到当前 Servicer
                    bound_method = types.MethodType(attr.__func__, servicer)
                    with cache_lock:
                        method_cache[name] = bound_method
                    return bound_method
                else:
                    # 其他可调用对象（如函数）
                    with cache_lock:
                        method_cache[name] = attr
                    return attr
            else:
                # 非可调用属性
                return attr
                
        except AttributeError:
            # 如果 Servicer 没有该属性，抛出 AttributeError
            raise AttributeError(f"'{type(servicer).__name__}' object has no attribute '{name}'")
    
    def __getattr__(self, name: str):
        """
        备用方法（当 __getattribute__ 没有找到时调用）
        
        这通常不应该被调用，因为 __getattribute__ 应该处理所有情况
        但保留它作为安全网
        """
        reloader = object.__getattribute__(self, '_reloader')
        servicer = reloader.get_current_servicer()
        if servicer is None:
            raise RuntimeError(f"Servicer 未初始化")
        return getattr(servicer, name)
    
    def clear_cache(self):
        """清除方法缓存（在热更新后调用）"""
        with self._cache_lock:
            self._method_cache.clear()


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

# 依赖关系映射（共享模块 -> 依赖它的微服务列表）
DEPENDENCY_MAP: Dict[str, List[str]] = {
    'src': ['bazi_core', 'bazi_fortune', 'bazi_analyzer', 'bazi_rule', 'fortune_analysis', 'fortune_rule'],
    'server': ['bazi_core', 'bazi_fortune', 'bazi_analyzer', 'bazi_rule', 'fortune_analysis', 'fortune_rule', 'intent_service'],
    'services.fortune_analysis': ['fortune_analysis'],
    'services.fortune_rule': ['fortune_rule'],
    'services.intent_service': ['intent_service'],
    'services.prompt_optimizer': ['prompt_optimizer'],
    'services.desk_fengshui': ['desk_fengshui'],
    'services.payment_service': ['payment_service'],
}


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


def get_dependent_services(changed_file: str) -> List[str]:
    """
    获取依赖指定文件的微服务列表
    
    Args:
        changed_file: 变化的文件路径（相对于项目根目录）
    
    Returns:
        依赖该文件的微服务名称列表
    """
    dependent_services = set()
    
    # 检查文件路径，确定依赖关系
    for module_pattern, services in DEPENDENCY_MAP.items():
        if module_pattern in changed_file or changed_file.startswith(module_pattern):
            dependent_services.update(services)
    
    # 如果文件在 src/ 目录下，所有微服务都可能依赖
    if changed_file.startswith('src/'):
        dependent_services.update(['bazi_core', 'bazi_fortune', 'bazi_analyzer', 'bazi_rule', 
                                   'fortune_analysis', 'fortune_rule', 'intent_service'])
    
    return list(dependent_services)


def trigger_dependent_services(changed_file: str) -> bool:
    """
    触发依赖指定文件的微服务热更新
    
    Args:
        changed_file: 变化的文件路径
    
    Returns:
        是否成功触发
    """
    dependent_services = get_dependent_services(changed_file)
    
    if not dependent_services:
        return False
    
    print(f"🔄 检测到共享文件变化: {changed_file}")
    print(f"   → 触发依赖服务热更新: {', '.join(dependent_services)}")
    
    success_count = 0
    for service_name in dependent_services:
        if service_name in _microservice_reloaders:
            reloader = _microservice_reloaders[service_name]
            try:
                # 强制检查并重新加载
                if reloader._check_and_reload():
                    success_count += 1
                    print(f"   ✓ {service_name} 热更新成功")
                else:
                    print(f"   ⚠ {service_name} 无需更新")
            except Exception as e:
                print(f"   ❌ {service_name} 热更新失败: {e}")
        else:
            print(f"   ⚠ {service_name} 未注册")
    
    print(f"📊 依赖服务热更新完成: {success_count}/{len(dependent_services)} 成功")
    return success_count > 0


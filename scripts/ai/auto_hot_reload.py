#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化热更新系统
功能：
1. 监听代码文件变更（使用 watchdog）
2. 自动触发热更新 API
3. 自动验证热更新成功
4. 失败自动回滚

使用方法：
    python3 scripts/ai/auto_hot_reload.py --watch          # 启动文件监控
    python3 scripts/ai/auto_hot_reload.py --trigger        # 手动触发一次
    python3 scripts/ai/auto_hot_reload.py --verify         # 验证热更新状态
"""

import os
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
HOT_RELOAD_API = f"{API_BASE_URL}/api/v1/hot-reload"
HOT_RELOAD_RELOAD_ALL_API = f"{HOT_RELOAD_API}/reload-all"  # 全量重载（通知所有 Worker）
HOT_RELOAD_VERIFY_API = f"{HOT_RELOAD_API}/verify"  # 功能验证
HOT_RELOAD_STATUS_API = f"{HOT_RELOAD_API}/status"
HOT_RELOAD_ROLLBACK_API = f"{HOT_RELOAD_API}/rollback"

# 监控的目录和文件类型
WATCH_DIRS = [
    "core",
    "server",
    "services",
]

WATCH_PATTERNS = [
    "*.py",
]

IGNORE_PATTERNS = [
    "*/__pycache__/*",
    "*/.*",
    "*/logs/*",
    "*/node_modules/*",
    "*/venv/*",
    "*/env/*",
    "*/.git/*",
]


class AutoHotReload:
    """自动化热更新系统"""
    
    def __init__(self, api_base_url: str = API_BASE_URL):
        self.api_base_url = api_base_url
        # 🔴 重要：使用 reload-all 而非 check，确保通知所有 Worker
        self.hot_reload_api = f"{api_base_url}/api/v1/hot-reload/reload-all"
        self.hot_reload_verify_api = f"{api_base_url}/api/v1/hot-reload/verify"
        self.hot_reload_status_api = f"{api_base_url}/api/v1/hot-reload/status"
        self.hot_reload_rollback_api = f"{api_base_url}/api/v1/hot-reload/rollback"
        self.last_trigger_time = 0
        self.trigger_cooldown = 5  # 5秒冷却时间，避免频繁触发
        self.watcher = None
        
    def trigger_hot_reload(self, module_name: Optional[str] = None) -> Dict:
        """
        触发热更新（使用 reload-all，确保通知所有 Worker）
        
        Args:
            module_name: 模块名称（可选）
            
        Returns:
            热更新结果
        """
        # 冷却时间检查
        current_time = time.time()
        if current_time - self.last_trigger_time < self.trigger_cooldown:
            return {
                "success": False,
                "message": f"冷却时间未到，请等待 {self.trigger_cooldown - (current_time - self.last_trigger_time):.1f} 秒",
                "skipped": True
            }
        
        try:
            print(f"{BLUE}🔄 触发全量热更新（reload-all，通知所有 Worker）...{NC}")
            
            # 🔴 调用 reload-all（而非 check），确保所有 Worker 都执行重载
            response = requests.post(
                self.hot_reload_api,
                json={},
                timeout=60  # reload-all 需要更长超时
            )
            
            if response.status_code == 200:
                result = response.json()
                self.last_trigger_time = current_time
                
                failed = result.get("failed_modules", [])
                if failed:
                    print(f"{YELLOW}⚠️  热更新部分失败: {failed}{NC}")
                else:
                    print(f"{GREEN}✅ 热更新触发成功（所有 Worker 已通知）{NC}")
                
                return {
                    "success": result.get("success", True),
                    "message": result.get("message", "热更新完成"),
                    "reloaded_modules": result.get("reloaded_modules", []),
                    "failed_modules": failed
                }
            else:
                error_msg = f"热更新API返回错误: {response.status_code}"
                print(f"{RED}❌ {error_msg}{NC}")
                return {
                    "success": False,
                    "message": error_msg,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"热更新API调用失败: {str(e)}"
            print(f"{RED}❌ {error_msg}{NC}")
            return {
                "success": False,
                "message": error_msg,
                "error": str(e)
            }
    
    def verify_hot_reload_status(self) -> Dict:
        """
        验证热更新状态（包含功能验证）
        
        优先调用 /hot-reload/verify（功能验证），如果端点不存在则回退到 /hot-reload/status
        
        Returns:
            热更新状态信息
        """
        # 1. 优先调用功能验证端点
        try:
            print(f"{BLUE}🔍 执行热更新功能验证...{NC}")
            
            response = requests.post(self.hot_reload_verify_api, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"{GREEN}✅ 热更新功能验证通过{NC}")
                    checks = result.get("checks", {})
                    for name, check in checks.items():
                        status_icon = "✅" if check.get("ok") else "❌"
                        print(f"   {status_icon} {name}: {check.get('detail', '')}")
                    return {
                        "success": True,
                        "status": result,
                        "message": "热更新功能验证通过"
                    }
                else:
                    failed_checks = {k: v for k, v in result.get("checks", {}).items() if not v.get("ok")}
                    error_msg = f"热更新功能验证失败: {list(failed_checks.keys())}"
                    print(f"{RED}❌ {error_msg}{NC}")
                    for name, check in failed_checks.items():
                        print(f"   ❌ {name}: {check.get('detail', '')}")
                    return {
                        "success": False,
                        "status": result,
                        "message": error_msg
                    }
            elif response.status_code == 404:
                # verify 端点不存在，回退到 status
                print(f"{YELLOW}⚠️  /verify 端点不存在，回退到 /status{NC}")
            else:
                print(f"{YELLOW}⚠️  /verify 返回 {response.status_code}，回退到 /status{NC}")
                
        except requests.exceptions.RequestException as e:
            print(f"{YELLOW}⚠️  /verify 调用失败: {e}，回退到 /status{NC}")
        
        # 2. 回退：调用状态检查端点
        try:
            print(f"{BLUE}🔍 验证热更新状态...{NC}")
            
            response = requests.get(self.hot_reload_status_api, timeout=10)
            
            if response.status_code == 200:
                status = response.json()
                print(f"{GREEN}✅ 热更新系统运行正常{NC}")
                return {
                    "success": True,
                    "status": status,
                    "message": "热更新系统运行正常"
                }
            else:
                error_msg = f"获取热更新状态失败: {response.status_code}"
                print(f"{RED}❌ {error_msg}{NC}")
                return {
                    "success": False,
                    "message": error_msg,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"验证热更新状态失败: {str(e)}"
            print(f"{RED}❌ {error_msg}{NC}")
            return {
                "success": False,
                "message": error_msg,
                "error": str(e)
            }
    
    def rollback(self) -> Dict:
        """
        回滚热更新
        
        Returns:
            回滚结果
        """
        try:
            print(f"{YELLOW}⏪ 回滚热更新...{NC}")
            
            response = requests.post(self.hot_reload_rollback_api, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"{GREEN}✅ 回滚成功{NC}")
                return {
                    "success": True,
                    "message": result.get("message", "回滚完成")
                }
            else:
                error_msg = f"回滚失败: {response.status_code}"
                print(f"{RED}❌ {error_msg}{NC}")
                return {
                    "success": False,
                    "message": error_msg,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"回滚API调用失败: {str(e)}"
            print(f"{RED}❌ {error_msg}{NC}")
            return {
                "success": False,
                "message": error_msg,
                "error": str(e)
            }
    
    def trigger_and_verify(self, module_name: Optional[str] = None, max_retries: int = 3) -> Dict:
        """
        触发热更新并验证
        
        Args:
            module_name: 模块名称（可选）
            max_retries: 最大重试次数
            
        Returns:
            完整的热更新结果（包含验证）
        """
        # 1. 触发热更新
        trigger_result = self.trigger_hot_reload(module_name)
        
        if not trigger_result.get("success") and not trigger_result.get("skipped"):
            # 触发失败，尝试回滚
            print(f"{YELLOW}⚠️  热更新触发失败，尝试回滚...{NC}")
            rollback_result = self.rollback()
            return {
                "success": False,
                "trigger": trigger_result,
                "rollback": rollback_result,
                "message": "热更新触发失败，已回滚"
            }
        
        if trigger_result.get("skipped"):
            return trigger_result
        
        # 2. 等待热更新完成
        print(f"{BLUE}⏳ 等待热更新完成（3秒）...{NC}")
        time.sleep(3)
        
        # 3. 验证热更新状态
        verify_result = self.verify_hot_reload_status()
        
        if not verify_result.get("success"):
            # 验证失败，尝试回滚
            print(f"{YELLOW}⚠️  热更新验证失败，尝试回滚...{NC}")
            rollback_result = self.rollback()
            return {
                "success": False,
                "trigger": trigger_result,
                "verify": verify_result,
                "rollback": rollback_result,
                "message": "热更新验证失败，已回滚"
            }
        
        return {
            "success": True,
            "trigger": trigger_result,
            "verify": verify_result,
            "message": "热更新成功并已验证"
        }
    
    def start_watch(self, watch_dirs: Optional[List[str]] = None):
        """
        启动文件监控（需要 watchdog 库）
        
        Args:
            watch_dirs: 监控目录列表（默认使用 WATCH_DIRS）
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileModifiedEvent
        except ImportError:
            print(f"{RED}❌ 需要安装 watchdog 库: pip install watchdog{NC}")
            return
        
        if watch_dirs is None:
            watch_dirs = WATCH_DIRS
        
        class HotReloadHandler(FileSystemEventHandler):
            """文件变更处理器"""
            
            def __init__(self, auto_reload: 'AutoHotReload'):
                self.auto_reload = auto_reload
                self.last_modified = {}
            
            def on_modified(self, event):
                """文件修改事件"""
                if event.is_directory:
                    return
                
                # 检查文件类型
                file_path = Path(event.src_path)
                if not any(file_path.match(pattern) for pattern in WATCH_PATTERNS):
                    return
                
                # 检查忽略模式
                if any(str(file_path).find(pattern.replace("*", "")) >= 0 for pattern in IGNORE_PATTERNS):
                    return
                
                # 防抖：同一文件1秒内只触发一次
                current_time = time.time()
                if event.src_path in self.last_modified:
                    if current_time - self.last_modified[event.src_path] < 1.0:
                        return
                
                self.last_modified[event.src_path] = current_time
                
                print(f"\n{BLUE}📝 检测到文件变更: {event.src_path}{NC}")
                print(f"{BLUE}🔄 自动触发热更新...{NC}")
                
                # 自动触发热更新
                result = self.auto_reload.trigger_and_verify()
                
                if result.get("success"):
                    print(f"{GREEN}✅ 热更新成功{NC}\n")
                else:
                    print(f"{RED}❌ 热更新失败: {result.get('message')}{NC}\n")
        
        # 创建观察者
        observer = Observer()
        handler = HotReloadHandler(self)
        
        # 添加监控目录
        for watch_dir in watch_dirs:
            watch_path = PROJECT_ROOT / watch_dir
            if watch_path.exists():
                observer.schedule(handler, str(watch_path), recursive=True)
                print(f"{GREEN}✅ 监控目录: {watch_path}{NC}")
            else:
                print(f"{YELLOW}⚠️  目录不存在: {watch_path}{NC}")
        
        # 启动监控
        observer.start()
        self.watcher = observer
        
        print(f"\n{GREEN}✅ 文件监控已启动，按 Ctrl+C 停止{NC}\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}⏹️  停止文件监控...{NC}")
            observer.stop()
        
        observer.join()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化热更新系统")
    parser.add_argument("--watch", action="store_true", help="启动文件监控")
    parser.add_argument("--trigger", action="store_true", help="手动触发一次热更新")
    parser.add_argument("--verify", action="store_true", help="验证热更新状态")
    parser.add_argument("--rollback", action="store_true", help="回滚热更新")
    parser.add_argument("--module", type=str, help="指定模块名称")
    parser.add_argument("--api-url", type=str, default=API_BASE_URL, help="API基础URL")
    
    args = parser.parse_args()
    
    auto_reload = AutoHotReload(api_base_url=args.api_url)
    
    if args.watch:
        # 启动文件监控
        auto_reload.start_watch()
    elif args.trigger:
        # 手动触发
        result = auto_reload.trigger_and_verify(module_name=args.module)
        print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    elif args.verify:
        # 验证状态
        result = auto_reload.verify_hot_reload_status()
        print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    elif args.rollback:
        # 回滚
        result = auto_reload.rollback()
        print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    else:
        # 默认：触发并验证
        result = auto_reload.trigger_and_verify(module_name=args.module)
        print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    main()


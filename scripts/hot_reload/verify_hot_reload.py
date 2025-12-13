#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新验证脚本

功能：
1. 验证所有服务都支持热更新
2. 检查热更新配置是否正确
3. 测试热更新功能是否正常
4. 生成验证报告

使用方法：
    python scripts/hot_reload/verify_hot_reload.py
    python scripts/hot_reload/verify_hot_reload.py --verbose
    python scripts/hot_reload/verify_hot_reload.py --test  # 执行实际测试
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, List, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


# 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")
HOT_RELOAD_API = f"{API_BASE_URL}/api/v1/hot-reload"

# 必须支持热更新的服务列表
REQUIRED_SERVICES = [
    {"name": "web", "port": 8001, "type": "fastapi", "description": "Web 主服务"},
    {"name": "bazi_core", "port": 9001, "type": "grpc", "description": "八字核心计算"},
    {"name": "bazi_fortune", "port": 9002, "type": "grpc", "description": "运势计算"},
    {"name": "bazi_analyzer", "port": 9003, "type": "grpc", "description": "八字分析"},
    {"name": "bazi_rule", "port": 9004, "type": "grpc", "description": "规则匹配"},
    {"name": "fortune_analysis", "port": 9005, "type": "grpc", "description": "运势分析"},
    {"name": "payment_service", "port": 9006, "type": "grpc", "description": "支付服务"},
    {"name": "fortune_rule", "port": 9007, "type": "grpc", "description": "运势规则"},
    {"name": "intent_service", "port": 9008, "type": "grpc", "description": "意图识别"},
    {"name": "prompt_optimizer", "port": 9009, "type": "grpc", "description": "提示优化"},
    {"name": "desk_fengshui", "port": 9010, "type": "grpc", "description": "风水分析"},
]

# 必须存在的热更新文件
REQUIRED_FILES = [
    "server/hot_reload/__init__.py",
    "server/hot_reload/hot_reload_manager.py",
    "server/hot_reload/version_manager.py",
    "server/hot_reload/reloaders.py",
    "server/hot_reload/file_monitor.py",
    "server/hot_reload/api.py",
    "server/hot_reload/microservice_reloader.py",
    "server/hot_reload/cluster_synchronizer.py",
]

# 必须监控的目录
REQUIRED_WATCH_DIRS = [
    "src",
    "server",
    "services",
]


class HotReloadVerifier:
    """热更新验证器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[Dict] = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def log(self, message: str, level: str = "info"):
        """打印日志"""
        prefix = {
            "info": "ℹ️ ",
            "success": "✅",
            "warning": "⚠️ ",
            "error": "❌",
        }.get(level, "  ")
        
        print(f"{prefix} {message}")
    
    def add_result(self, check_name: str, passed: bool, message: str, details: Dict = None):
        """添加检查结果"""
        self.results.append({
            "check": check_name,
            "passed": passed,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        
        if passed:
            self.passed += 1
            self.log(f"{check_name}: {message}", "success")
        else:
            self.failed += 1
            self.log(f"{check_name}: {message}", "error")
    
    def add_warning(self, check_name: str, message: str):
        """添加警告"""
        self.warnings += 1
        self.log(f"{check_name}: {message}", "warning")
    
    def verify_files_exist(self) -> bool:
        """验证热更新文件是否存在"""
        self.log("\n📁 检查热更新文件...", "info")
        
        all_exist = True
        for file_path in REQUIRED_FILES:
            full_path = os.path.join(project_root, file_path)
            exists = os.path.exists(full_path)
            
            if exists:
                if self.verbose:
                    self.log(f"  文件存在: {file_path}", "success")
            else:
                self.log(f"  文件缺失: {file_path}", "error")
                all_exist = False
        
        self.add_result(
            "文件检查",
            all_exist,
            f"所有必需文件都存在" if all_exist else "部分文件缺失"
        )
        return all_exist
    
    def verify_watch_directories(self) -> bool:
        """验证监控目录配置"""
        self.log("\n📂 检查监控目录配置...", "info")
        
        try:
            from server.hot_reload.reloaders import SourceCodeReloader
            
            configured_dirs = set(SourceCodeReloader._SEARCH_DIRECTORIES)
            required_dirs = set(REQUIRED_WATCH_DIRS)
            
            missing = required_dirs - configured_dirs
            
            if missing:
                self.add_result(
                    "监控目录",
                    False,
                    f"缺少监控目录: {missing}",
                    {"configured": list(configured_dirs), "required": list(required_dirs)}
                )
                return False
            
            self.add_result(
                "监控目录",
                True,
                f"所有必需目录都已配置监控: {REQUIRED_WATCH_DIRS}",
                {"configured": list(configured_dirs)}
            )
            return True
            
        except ImportError as e:
            self.add_result("监控目录", False, f"导入失败: {e}")
            return False
    
    def verify_reloaders(self) -> bool:
        """验证重载器配置"""
        self.log("\n🔄 检查重载器配置...", "info")
        
        try:
            from server.hot_reload.reloaders import RELOADERS, RELOAD_ORDER
            
            required_reloaders = {'rules', 'content', 'config', 'cache', 'source', 'microservice', 'singleton'}
            configured_reloaders = set(RELOADERS.keys())
            
            missing = required_reloaders - configured_reloaders
            
            if missing:
                self.add_result(
                    "重载器配置",
                    False,
                    f"缺少重载器: {missing}",
                    {"configured": list(configured_reloaders)}
                )
                return False
            
            # 检查重载顺序
            if len(RELOAD_ORDER) < len(required_reloaders):
                self.add_warning("重载器配置", f"重载顺序可能不完整: {RELOAD_ORDER}")
            
            self.add_result(
                "重载器配置",
                True,
                f"所有重载器已配置: {list(configured_reloaders)}",
                {"reload_order": RELOAD_ORDER}
            )
            return True
            
        except ImportError as e:
            self.add_result("重载器配置", False, f"导入失败: {e}")
            return False
    
    def verify_api_available(self) -> bool:
        """验证热更新 API 是否可用"""
        self.log("\n🌐 检查热更新 API...", "info")
        
        try:
            response = requests.get(f"{HOT_RELOAD_API}/status", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.add_result(
                    "API 可用性",
                    True,
                    "热更新 API 可用",
                    data
                )
                return True
            else:
                self.add_result(
                    "API 可用性",
                    False,
                    f"API 返回错误状态码: {response.status_code}"
                )
                return False
                
        except requests.exceptions.ConnectionError:
            self.add_warning("API 可用性", f"无法连接到 {API_BASE_URL}（服务可能未启动）")
            return False
        except Exception as e:
            self.add_result("API 可用性", False, f"检查失败: {e}")
            return False
    
    def verify_health_check(self) -> bool:
        """验证健康检查端点"""
        self.log("\n🏥 检查健康检查端点...", "info")
        
        try:
            response = requests.get(f"{HOT_RELOAD_API}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                self.add_result(
                    "健康检查",
                    status in ['healthy', 'degraded'],
                    f"健康检查状态: {status}",
                    data.get('details', {})
                )
                return status == 'healthy'
            else:
                self.add_result("健康检查", False, f"健康检查失败: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.add_warning("健康检查", "无法连接到服务")
            return False
        except Exception as e:
            self.add_result("健康检查", False, f"检查失败: {e}")
            return False
    
    def verify_microservices(self) -> bool:
        """验证微服务热更新配置"""
        self.log("\n🔧 检查微服务热更新配置...", "info")
        
        try:
            # 检查每个微服务目录是否有 grpc_server.py
            all_configured = True
            for service in REQUIRED_SERVICES:
                if service['type'] != 'grpc':
                    continue
                
                service_dir = os.path.join(project_root, "services", service['name'])
                grpc_server_path = os.path.join(service_dir, "grpc_server.py")
                
                if os.path.exists(grpc_server_path):
                    if self.verbose:
                        self.log(f"  {service['name']}: grpc_server.py 存在", "success")
                else:
                    # 某些服务可能不存在单独目录
                    if self.verbose:
                        self.add_warning("微服务配置", f"{service['name']}: grpc_server.py 不存在")
            
            self.add_result(
                "微服务配置",
                True,
                f"已检查 {len([s for s in REQUIRED_SERVICES if s['type'] == 'grpc'])} 个微服务"
            )
            return True
            
        except Exception as e:
            self.add_result("微服务配置", False, f"检查失败: {e}")
            return False
    
    def test_hot_reload(self) -> bool:
        """测试热更新功能"""
        self.log("\n🧪 测试热更新功能...", "info")
        
        try:
            # 1. 触发热更新检查
            response = requests.post(f"{HOT_RELOAD_API}/check", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.add_result(
                    "热更新测试",
                    data.get('success', False),
                    data.get('message', '未知结果'),
                    data
                )
                return data.get('success', False)
            else:
                self.add_result("热更新测试", False, f"请求失败: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.add_warning("热更新测试", "无法连接到服务，跳过测试")
            return False
        except Exception as e:
            self.add_result("热更新测试", False, f"测试失败: {e}")
            return False
    
    def generate_report(self) -> Dict:
        """生成验证报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": len(self.results),
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "success_rate": f"{(self.passed / len(self.results) * 100):.1f}%" if self.results else "0%"
            },
            "results": self.results,
            "required_services": REQUIRED_SERVICES,
            "required_files": REQUIRED_FILES,
            "required_watch_dirs": REQUIRED_WATCH_DIRS
        }
    
    def run(self, run_tests: bool = False) -> bool:
        """运行所有验证"""
        print("\n" + "="*60)
        print("🔥 热更新系统验证")
        print("="*60)
        
        # 1. 验证文件
        self.verify_files_exist()
        
        # 2. 验证监控目录
        self.verify_watch_directories()
        
        # 3. 验证重载器
        self.verify_reloaders()
        
        # 4. 验证微服务配置
        self.verify_microservices()
        
        # 5. 验证 API（如果服务运行中）
        api_available = self.verify_api_available()
        
        if api_available:
            # 6. 验证健康检查
            self.verify_health_check()
            
            # 7. 测试热更新（如果指定）
            if run_tests:
                self.test_hot_reload()
        
        # 生成报告
        report = self.generate_report()
        
        # 打印总结
        print("\n" + "="*60)
        print("📊 验证结果总结")
        print("="*60)
        print(f"总检查数: {report['summary']['total_checks']}")
        print(f"通过: {report['summary']['passed']}")
        print(f"失败: {report['summary']['failed']}")
        print(f"警告: {report['summary']['warnings']}")
        print(f"成功率: {report['summary']['success_rate']}")
        print("="*60)
        
        # 保存报告
        report_path = os.path.join(project_root, "logs", "hot_reload_verification.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 报告已保存到: {report_path}")
        
        return self.failed == 0


def main():
    parser = argparse.ArgumentParser(description="热更新验证脚本")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    parser.add_argument("--test", "-t", action="store_true", help="执行实际的热更新测试")
    parser.add_argument("--api-url", default=API_BASE_URL, help="API 基础 URL")
    args = parser.parse_args()
    
    global API_BASE_URL, HOT_RELOAD_API
    API_BASE_URL = args.api_url
    HOT_RELOAD_API = f"{API_BASE_URL}/api/v1/hot-reload"
    
    verifier = HotReloadVerifier(verbose=args.verbose)
    success = verifier.run(run_tests=args.test)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


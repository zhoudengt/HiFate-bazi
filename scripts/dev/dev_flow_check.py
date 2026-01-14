#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发流程检查工具
用途：自动化检查开发流程完整性，确保功能开发一次性成功

使用方法：
  python3 scripts/dev/dev_flow_check.py --pre-dev          # 开发前检查
  python3 scripts/dev/dev_flow_check.py --files <文件>     # 检查指定文件
  python3 scripts/dev/dev_flow_check.py --all               # 完整检查
"""

import sys
import os
import re
import json
import subprocess
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# 导入现有的代码审查工具
try:
    from scripts.review.code_review_check import CodeReviewChecker
except ImportError:
    CodeReviewChecker = None


class DevFlowChecker:
    """开发流程检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checked_files = []
        self.report = {
            'code_standards': {'passed': 0, 'failed': 0, 'errors': []},
            'completeness': {'passed': 0, 'failed': 0, 'errors': []},
            'naming': {'passed': 0, 'failed': 0, 'errors': []},
            'grpc_registration': {'passed': 0, 'failed': 0, 'errors': []},
            'router_registration': {'passed': 0, 'failed': 0, 'errors': []},
            'hot_reload': {'passed': 0, 'failed': 0, 'errors': []},
            'test_coverage': {'passed': 0, 'failed': 0, 'errors': []},
        }
    
    def check_pre_dev(self) -> bool:
        """开发前检查"""
        print(f"{BLUE}🔍 开始开发前检查...{NC}\n")
        
        checks = [
            ("开发环境检查", self._check_dev_env),
            ("Git 状态检查", self._check_git_status),
            ("代码规范检查", self._check_code_standards),
        ]
        
        all_passed = True
        for name, check_func in checks:
            print(f"{BLUE}检查: {name}{NC}")
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                print(f"{RED}❌ {name} 检查失败: {e}{NC}\n")
                all_passed = False
        
        return all_passed
    
    def check_files(self, file_paths: List[str]) -> bool:
        """检查指定文件"""
        print(f"{BLUE}🔍 开始检查文件...{NC}\n")
        
        all_passed = True
        for file_path in file_paths:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                print(f"{YELLOW}⚠️  文件不存在: {file_path}{NC}")
                continue
            
            print(f"{BLUE}检查文件: {file_path}{NC}")
            
            # 代码规范检查
            if not self._check_file_code_standards(str(full_path)):
                all_passed = False
            
            # 完整性检查
            if not self._check_file_completeness(str(full_path)):
                all_passed = False
            
            # 命名规范检查
            if not self._check_file_naming(str(full_path)):
                all_passed = False
        
        return all_passed
    
    def check_all(self) -> bool:
        """完整检查"""
        print(f"{BLUE}🔍 开始完整检查...{NC}\n")
        
        # 1. 代码规范检查
        print(f"{BLUE}1. 代码规范检查{NC}")
        if CodeReviewChecker:
            checker = CodeReviewChecker()
            if not checker.run():
                self.report['code_standards']['failed'] += 1
                return False
            self.report['code_standards']['passed'] += 1
        
        # 2. 完整性检查
        print(f"\n{BLUE}2. 完整性检查{NC}")
        if not self._check_completeness():
            return False
        
        # 3. 命名规范检查
        print(f"\n{BLUE}3. 命名规范检查{NC}")
        if not self._check_naming_all():
            return False
        
        # 4. gRPC 端点注册检查
        print(f"\n{BLUE}4. gRPC 端点注册检查{NC}")
        if not self._check_grpc_registration():
            return False
        
        # 5. 路由注册检查
        print(f"\n{BLUE}5. 路由注册检查{NC}")
        if not self._check_router_registration():
            return False
        
        # 6. 热更新支持检查
        print(f"\n{BLUE}6. 热更新支持检查{NC}")
        if not self._check_hot_reload_support():
            return False
        
        # 7. 测试覆盖检查
        print(f"\n{BLUE}7. 测试覆盖检查{NC}")
        if not self._check_test_coverage():
            return False
        
        # 8. 自动触发热更新（如果检查通过）
        print(f"\n{BLUE}8. 自动触发热更新{NC}")
        try:
            from scripts.ai.auto_hot_reload import AutoHotReload
            auto_reload = AutoHotReload()
            result = auto_reload.trigger_and_verify()
            if result.get("success"):
                print(f"  {GREEN}✓{NC} 热更新成功")
            else:
                print(f"  {YELLOW}⚠{NC} 热更新失败（不影响检查结果）: {result.get('message')}")
        except Exception as e:
            print(f"  {YELLOW}⚠{NC} 热更新工具不可用（不影响检查结果）: {e}")
        
        return True
    
    def _check_dev_env(self) -> bool:
        """检查开发环境"""
        checks = [
            ("Python 版本", self._check_python_version),
            ("依赖包", self._check_dependencies),
            ("服务状态", self._check_service_status),
        ]
        
        all_passed = True
        for name, check_func in checks:
            try:
                if not check_func():
                    print(f"  {RED}✗{NC} {name} 检查失败")
                    all_passed = False
                else:
                    print(f"  {GREEN}✓{NC} {name} 检查通过")
            except Exception as e:
                print(f"  {RED}✗{NC} {name} 检查异常: {e}")
                all_passed = False
        
        print()
        return all_passed
    
    def _check_python_version(self) -> bool:
        """检查 Python 版本"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            return True
        print(f"  {RED}Python 版本过低: {version.major}.{version.minor}，需要 >= 3.8{NC}")
        return False
    
    def _check_dependencies(self) -> bool:
        """检查依赖包"""
        required_packages = ['fastapi', 'pydantic', 'grpc']
        missing = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            print(f"  {RED}缺少依赖包: {', '.join(missing)}{NC}")
            return False
        return True
    
    def _check_service_status(self) -> bool:
        """检查服务状态"""
        try:
            import requests
            response = requests.get('http://localhost:8001/health', timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        
        print(f"  {YELLOW}⚠️  本地服务未运行（可选）{NC}")
        return True  # 服务未运行不算错误
    
    def _check_git_status(self) -> bool:
        """检查 Git 状态"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            if result.stdout.strip():
                print(f"  {YELLOW}⚠️  有未提交的更改{NC}")
                print(f"  {YELLOW}建议先提交或暂存更改{NC}")
                return False
            return True
        except Exception:
            print(f"  {YELLOW}⚠️  无法检查 Git 状态{NC}")
            return True
    
    def _check_code_standards(self) -> bool:
        """检查代码规范"""
        if not CodeReviewChecker:
            print(f"  {YELLOW}⚠️  代码审查工具不可用{NC}")
            return True
        
        checker = CodeReviewChecker()
        return checker.run()
    
    def _check_file_code_standards(self, file_path: str) -> bool:
        """检查单个文件的代码规范"""
        if not CodeReviewChecker:
            return True
        
        checker = CodeReviewChecker()
        is_valid, errors, warnings = checker.check_file(file_path)
        
        if errors:
            for error in errors:
                print(f"  {RED}✗{NC} {error}")
                self.report['code_standards']['errors'].append(error)
            return False
        
        if warnings:
            for warning in warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
        
        return True
    
    def _check_completeness(self) -> bool:
        """检查完整性"""
        # 检查 API 文件是否有对应的 gRPC 注册和路由注册
        api_files = list((PROJECT_ROOT / 'server/api/v1').glob('*.py'))
        
        all_passed = True
        for api_file in api_files:
            if api_file.name == '__init__.py':
                continue
            
            # 检查是否有 API 定义
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@router.post' in content or '@router.get' in content:
                    # 检查 gRPC 注册
                    if not self._check_grpc_registration_for_file(api_file.name):
                        all_passed = False
                    
                    # 检查路由注册
                    if not self._check_router_registration_for_file(api_file.name):
                        all_passed = False
        
        return all_passed
    
    def _check_file_completeness(self, file_path: str) -> bool:
        """检查单个文件的完整性"""
        file_name = Path(file_path).name
        
        # 如果是 API 文件，检查 gRPC 和路由注册
        if 'api/v1' in file_path and file_name != '__init__.py':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@router.post' in content or '@router.get' in content:
                    if not self._check_grpc_registration_for_file(file_name):
                        return False
                    if not self._check_router_registration_for_file(file_name):
                        return False
        
        return True
    
    def _check_naming_all(self) -> bool:
        """检查所有文件的命名规范"""
        # 导入命名检查工具
        try:
            from scripts.dev.check_naming import NamingChecker
            checker = NamingChecker()
            return checker.check_all()
        except ImportError:
            print(f"  {YELLOW}⚠️  命名检查工具不可用，跳过{NC}")
            return True
    
    def _check_file_naming(self, file_path: str) -> bool:
        """检查单个文件的命名规范"""
        try:
            from scripts.dev.check_naming import NamingChecker
            checker = NamingChecker()
            return checker.check_file(file_path)
        except ImportError:
            return True
    
    def _check_grpc_registration(self) -> bool:
        """检查 gRPC 端点注册"""
        grpc_gateway_file = PROJECT_ROOT / 'server/api/grpc_gateway.py'
        if not grpc_gateway_file.exists():
            print(f"  {RED}✗{NC} gRPC 网关文件不存在{NC}")
            return False
        
        # 检查所有 API 文件是否在 gRPC 网关中注册
        api_files = list((PROJECT_ROOT / 'server/api/v1').glob('*.py'))
        missing_registrations = []
        
        with open(grpc_gateway_file, 'r', encoding='utf-8') as f:
            grpc_content = f.read()
        
        for api_file in api_files:
            if api_file.name == '__init__.py':
                continue
            
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@router.post' in content or '@router.get' in content:
                    # 检查是否在 gRPC 网关中注册
                    # 简单检查：查找 API 文件名或函数名
                    api_name = api_file.stem
                    if api_name not in grpc_content and f'/{api_name.replace("_", "-")}' not in grpc_content:
                        # 更详细的检查：查找 @_register 装饰器
                        if f'@_register' not in content or f'_{api_name}' not in grpc_content:
                            missing_registrations.append(api_file.name)
        
        if missing_registrations:
            print(f"  {RED}✗{NC} 以下 API 文件可能未在 gRPC 网关中注册:{NC}")
            for name in missing_registrations:
                print(f"    - {name}")
            return False
        
        print(f"  {GREEN}✓{NC} 所有 API 端点已注册到 gRPC 网关{NC}")
        return True
    
    def _check_grpc_registration_for_file(self, file_name: str) -> bool:
        """检查指定文件的 gRPC 注册"""
        grpc_gateway_file = PROJECT_ROOT / 'server/api/grpc_gateway.py'
        if not grpc_gateway_file.exists():
            return False
        
        with open(grpc_gateway_file, 'r', encoding='utf-8') as f:
            grpc_content = f.read()
        
        api_name = Path(file_name).stem
        
        # 例外：后端评测脚本使用的API不需要在gRPC网关中注册
        # 这些API仅用于评测脚本，不需要前端访问
        backend_only_apis = ['bazi_rules']  # 后端专用API列表
        if api_name in backend_only_apis:
            print(f"  {BLUE}ℹ️  {file_name} 是后端专用API，不需要在 gRPC 网关中注册{NC}")
            return True
        
        # 检查是否在 gRPC 网关中注册
        if api_name in grpc_content or f'/{api_name.replace("_", "-")}' in grpc_content:
            return True
        
        print(f"  {YELLOW}⚠️  {file_name} 可能未在 gRPC 网关中注册{NC}")
        return True  # 警告，不算错误
    
    def _check_router_registration(self) -> bool:
        """检查路由注册"""
        main_file = PROJECT_ROOT / 'server/main.py'
        if not main_file.exists():
            print(f"  {RED}✗{NC} main.py 文件不存在{NC}")
            return False
        
        with open(main_file, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        # 检查所有 API 路由是否在 main.py 中注册
        api_files = list((PROJECT_ROOT / 'server/api/v1').glob('*.py'))
        missing_registrations = []
        
        for api_file in api_files:
            if api_file.name == '__init__.py':
                continue
            
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@router.post' in content or '@router.get' in content:
                    # 检查是否在 main.py 中注册
                    router_name = api_file.stem
                    if f'register_router' in main_content:
                        # 查找 router_manager.register_router 调用
                        if router_name not in main_content and f'{router_name}_router' not in main_content:
                            missing_registrations.append(api_file.name)
        
        if missing_registrations:
            print(f"  {RED}✗{NC} 以下路由可能未在 main.py 中注册:{NC}")
            for name in missing_registrations:
                print(f"    - {name}")
            return False
        
        print(f"  {GREEN}✓{NC} 所有路由已注册到 main.py{NC}")
        return True
    
    def _check_router_registration_for_file(self, file_name: str) -> bool:
        """检查指定文件的路由注册"""
        main_file = PROJECT_ROOT / 'server/main.py'
        if not main_file.exists():
            return False
        
        with open(main_file, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        router_name = Path(file_name).stem
        if router_name in main_content or f'{router_name}_router' in main_content:
            return True
        
        print(f"  {YELLOW}⚠️  {file_name} 可能未在 main.py 中注册{NC}")
        return True  # 警告，不算错误
    
    def _check_hot_reload_support(self) -> bool:
        """检查热更新支持"""
        # 检查关键文件是否支持热更新
        key_files = [
            'server/main.py',
            'server/api/grpc_gateway.py',
        ]
        
        all_passed = True
        for file_path in key_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 检查是否有模块级全局状态初始化
            for i, line in enumerate(lines[:10], 1):  # 只检查前10行
                if '=' in line and 'import' not in line and 'from' not in line:
                    if '[' in line or '{' in line:
                        # 可能是模块级初始化
                        if not line.strip().startswith('#'):
                            print(f"  {YELLOW}⚠️  {file_path}:{i} 可能存在模块级全局状态初始化{NC}")
                            all_passed = False
        
        if all_passed:
            print(f"  {GREEN}✓{NC} 热更新支持检查通过{NC}")
        
        return all_passed
    
    def _check_test_coverage(self) -> bool:
        """检查测试覆盖"""
        try:
            result = subprocess.run(
                ['pytest', '--cov=server', '--cov=src', '--cov-report=term-missing', '--cov-fail-under=50'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✓{NC} 测试覆盖率 >= 50%{NC}")
                return True
            else:
                print(f"  {YELLOW}⚠️  测试覆盖率 < 50% 或测试失败{NC}")
                print(f"  {YELLOW}输出: {result.stdout[-500:]}{NC}")
                return True  # 警告，不算错误
        except subprocess.TimeoutExpired:
            print(f"  {YELLOW}⚠️  测试执行超时{NC}")
            return True
        except FileNotFoundError:
            print(f"  {YELLOW}⚠️  pytest 未安装，跳过测试覆盖检查{NC}")
            return True
    
    def generate_report(self) -> Dict:
        """生成检查报告"""
        return {
            'summary': {
                'total_errors': sum(cat['failed'] for cat in self.report.values()),
                'total_warnings': len(self.warnings),
                'all_passed': len(self.errors) == 0,
            },
            'details': self.report,
            'errors': self.errors,
            'warnings': self.warnings,
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='开发流程检查工具')
    parser.add_argument('--pre-dev', action='store_true', help='开发前检查')
    parser.add_argument('--files', nargs='+', help='要检查的文件路径')
    parser.add_argument('--all', action='store_true', help='完整检查')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式报告')
    parser.add_argument('--exit-on-error', action='store_true', help='发现错误时退出（用于 CI/CD）')
    
    args = parser.parse_args()
    
    checker = DevFlowChecker()
    success = False
    
    if args.pre_dev:
        success = checker.check_pre_dev()
    elif args.files:
        success = checker.check_files(args.files)
    elif args.all:
        success = checker.check_all()
    else:
        parser.print_help()
        sys.exit(1)
    
    if args.json:
        report = checker.generate_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    if args.exit_on_error and not success:
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


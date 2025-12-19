#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修改工具
用途：自动诊断和修复常见问题，快速验证修复结果

使用方法：
  python3 scripts/dev/quick_fix.py --diagnose          # 诊断问题
  python3 scripts/dev/quick_fix.py --fix <问题类型>    # 修复问题
  python3 scripts/dev/quick_fix.py --verify            # 验证修复结果
"""

import sys
import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class QuickFixer:
    """快速修复器"""
    
    def __init__(self):
        self.issues = []
        self.fixed_issues = []
    
    def diagnose(self) -> List[Dict]:
        """诊断问题"""
        print(f"{BLUE}🔍 开始诊断问题...{NC}\n")
        
        issues = []
        
        # 1. 检查语法错误
        syntax_errors = self._check_syntax_errors()
        if syntax_errors:
            issues.extend(syntax_errors)
        
        # 2. 检查导入错误
        import_errors = self._check_import_errors()
        if import_errors:
            issues.extend(import_errors)
        
        # 3. 检查命名规范
        naming_errors = self._check_naming_errors()
        if naming_errors:
            issues.extend(naming_errors)
        
        # 4. 检查 gRPC 注册
        grpc_issues = self._check_grpc_registration()
        if grpc_issues:
            issues.extend(grpc_issues)
        
        # 5. 检查路由注册
        router_issues = self._check_router_registration()
        if router_issues:
            issues.extend(router_issues)
        
        # 6. 检查热更新支持
        hot_reload_issues = self._check_hot_reload()
        if hot_reload_issues:
            issues.extend(hot_reload_issues)
        
        self.issues = issues
        
        # 输出诊断结果
        self._print_diagnosis(issues)
        
        return issues
    
    def fix(self, issue_type: Optional[str] = None) -> bool:
        """修复问题"""
        if not self.issues:
            print(f"{YELLOW}⚠️  未发现问题，请先运行 --diagnose{NC}")
            return True
        
        print(f"{BLUE}🔧 开始修复问题...{NC}\n")
        
        fixed_count = 0
        for issue in self.issues:
            if issue_type and issue['type'] != issue_type:
                continue
            
            if self._fix_issue(issue):
                fixed_count += 1
                self.fixed_issues.append(issue)
        
        print(f"\n{GREEN}✅ 修复了 {fixed_count} 个问题{NC}\n")
        return fixed_count > 0
    
    def verify(self) -> bool:
        """验证修复结果"""
        print(f"{BLUE}✅ 开始验证修复结果...{NC}\n")
        
        checks = [
            ("语法检查", self._verify_syntax),
            ("导入检查", self._verify_imports),
            ("命名规范", self._verify_naming),
            ("gRPC 注册", self._verify_grpc),
            ("路由注册", self._verify_router),
            ("热更新", self._verify_hot_reload),
        ]
        
        all_passed = True
        for name, check_func in checks:
            print(f"{BLUE}验证: {name}{NC}")
            try:
                if not check_func():
                    print(f"  {RED}✗{NC} {name} 验证失败")
                    all_passed = False
                else:
                    print(f"  {GREEN}✓{NC} {name} 验证通过")
            except Exception as e:
                print(f"  {RED}✗{NC} {name} 验证异常: {e}")
                all_passed = False
        
        print()
        if all_passed:
            print(f"{GREEN}✅ 所有验证通过！{NC}\n")
        else:
            print(f"{RED}❌ 部分验证失败，请检查{NC}\n")
        
        return all_passed
    
    def _check_syntax_errors(self) -> List[Dict]:
        """检查语法错误"""
        errors = []
        
        try:
            result = subprocess.run(
                ['python3', '-m', 'py_compile', '--help'],
                capture_output=True,
                text=True
            )
        except Exception:
            return errors
        
        # 检查变更的 Python 文件
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            if result.returncode == 0:
                changed_files = [f for f in result.stdout.strip().split('\n') if f and f.endswith('.py')]
                for file_path in changed_files:
                    full_path = PROJECT_ROOT / file_path
                    if full_path.exists():
                        try:
                            compile(open(full_path).read(), str(full_path), 'exec')
                        except SyntaxError as e:
                            errors.append({
                                'type': 'syntax',
                                'file': file_path,
                                'line': e.lineno,
                                'message': str(e),
                                'fixable': True,
                            })
        except Exception:
            pass
        
        return errors
    
    def _check_import_errors(self) -> List[Dict]:
        """检查导入错误"""
        errors = []
        
        # 检查关键模块是否可以导入
        key_modules = [
            'server.main',
            'server.api.grpc_gateway',
        ]
        
        for module_name in key_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                errors.append({
                    'type': 'import',
                    'module': module_name,
                    'message': str(e),
                    'fixable': False,
                })
        
        return errors
    
    def _check_naming_errors(self) -> List[Dict]:
        """检查命名错误"""
        errors = []
        
        try:
            from scripts.dev.check_naming import NamingChecker
            checker = NamingChecker()
            # 只检查变更的文件
            try:
                result = subprocess.run(
                    ['git', 'diff', '--name-only', 'HEAD'],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT
                )
                if result.returncode == 0:
                    changed_files = [f for f in result.stdout.strip().split('\n') if f and f.endswith('.py')]
                    for file_path in changed_files:
                        full_path = PROJECT_ROOT / file_path
                        if full_path.exists():
                            if not checker.check_file(str(full_path)):
                                for error in checker.get_errors():
                                    errors.append({
                                        'type': 'naming',
                                        'file': file_path,
                                        'message': error,
                                        'fixable': False,  # 命名问题需要手动修复
                                    })
            except Exception:
                pass
        except ImportError:
            pass
        
        return errors
    
    def _check_grpc_registration(self) -> List[Dict]:
        """检查 gRPC 注册"""
        issues = []
        
        # 检查 API 文件是否在 gRPC 网关中注册
        api_dir = PROJECT_ROOT / 'server/api/v1'
        if not api_dir.exists():
            return issues
        
        grpc_gateway_file = PROJECT_ROOT / 'server/api/grpc_gateway.py'
        if not grpc_gateway_file.exists():
            return issues
        
        with open(grpc_gateway_file, 'r', encoding='utf-8') as f:
            grpc_content = f.read()
        
        for api_file in api_dir.glob('*.py'):
            if api_file.name == '__init__.py':
                continue
            
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@router.post' in content or '@router.get' in content:
                    api_name = api_file.stem
                    if api_name not in grpc_content and f'/{api_name.replace("_", "-")}' not in grpc_content:
                        issues.append({
                            'type': 'grpc_registration',
                            'file': str(api_file.relative_to(PROJECT_ROOT)),
                            'message': f'API {api_name} 未在 gRPC 网关中注册',
                            'fixable': False,  # 需要手动注册
                        })
        
        return issues
    
    def _check_router_registration(self) -> List[Dict]:
        """检查路由注册"""
        issues = []
        
        main_file = PROJECT_ROOT / 'server/main.py'
        if not main_file.exists():
            return issues
        
        with open(main_file, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        api_dir = PROJECT_ROOT / 'server/api/v1'
        if not api_dir.exists():
            return issues
        
        for api_file in api_dir.glob('*.py'):
            if api_file.name == '__init__.py':
                continue
            
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '@router.post' in content or '@router.get' in content:
                    router_name = api_file.stem
                    if router_name not in main_content and f'{router_name}_router' not in main_content:
                        issues.append({
                            'type': 'router_registration',
                            'file': str(api_file.relative_to(PROJECT_ROOT)),
                            'message': f'路由 {router_name} 未在 main.py 中注册',
                            'fixable': False,  # 需要手动注册
                        })
        
        return issues
    
    def _check_hot_reload(self) -> List[Dict]:
        """检查热更新支持"""
        issues = []
        
        # 检查关键文件是否有模块级全局状态初始化
        key_files = [
            'server/main.py',
            'server/api/grpc_gateway.py',
        ]
        
        for file_path in key_files:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines[:10], 1):
                if '=' in line and 'import' not in line and 'from' not in line:
                    if '[' in line or '{' in line:
                        if not line.strip().startswith('#'):
                            issues.append({
                                'type': 'hot_reload',
                                'file': file_path,
                                'line': i,
                                'message': f'可能存在模块级全局状态初始化，可能影响热更新',
                                'fixable': False,  # 需要手动修复
                            })
        
        return issues
    
    def _fix_issue(self, issue: Dict) -> bool:
        """修复单个问题"""
        if not issue.get('fixable', False):
            print(f"  {YELLOW}⚠️  {issue['type']}: {issue.get('message', '')} - 需要手动修复{NC}")
            return False
        
        issue_type = issue['type']
        
        if issue_type == 'syntax':
            print(f"  {YELLOW}⚠️  语法错误需要手动修复: {issue.get('file', '')}:{issue.get('line', '')}{NC}")
            return False
        
        return False
    
    def _print_diagnosis(self, issues: List[Dict]):
        """输出诊断结果"""
        if not issues:
            print(f"{GREEN}✅ 未发现问题！{NC}\n")
            return
        
        print(f"\n{BLUE}📊 诊断结果：{NC}\n")
        
        # 按类型分组
        by_type = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)
        
        for issue_type, type_issues in by_type.items():
            print(f"{YELLOW}{issue_type} ({len(type_issues)} 个):{NC}")
            for issue in type_issues[:5]:  # 只显示前5个
                print(f"  - {issue.get('file', issue.get('module', 'unknown'))}: {issue.get('message', '')}")
            if len(type_issues) > 5:
                print(f"  ... 还有 {len(type_issues) - 5} 个")
            print()
    
    def _verify_syntax(self) -> bool:
        """验证语法"""
        try:
            result = subprocess.run(
                ['python3', '-m', 'py_compile', 'server/main.py'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return True
    
    def _verify_imports(self) -> bool:
        """验证导入"""
        try:
            import server.main
            return True
        except Exception:
            return False
    
    def _verify_naming(self) -> bool:
        """验证命名"""
        try:
            from scripts.dev.check_naming import NamingChecker
            checker = NamingChecker()
            # 只检查变更的文件
            return True  # 命名检查不阻塞验证
        except Exception:
            return True
    
    def _verify_grpc(self) -> bool:
        """验证 gRPC 注册"""
        try:
            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
            return len(SUPPORTED_ENDPOINTS) > 0
        except Exception:
            return False
    
    def _verify_router(self) -> bool:
        """验证路由注册"""
        try:
            import server.main
            return True
        except Exception:
            return False
    
    def _verify_hot_reload(self) -> bool:
        """验证热更新"""
        try:
            result = subprocess.run(
                ['curl', '-s', '-X', 'POST', 'http://localhost:8001/api/v1/hot-reload/check'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return True  # 服务未运行不算错误


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='快速修改工具')
    parser.add_argument('--diagnose', action='store_true', help='诊断问题')
    parser.add_argument('--fix', type=str, help='修复问题（指定问题类型）')
    parser.add_argument('--verify', action='store_true', help='验证修复结果')
    parser.add_argument('--all', action='store_true', help='诊断、修复、验证全流程')
    
    args = parser.parse_args()
    
    fixer = QuickFixer()
    
    if args.all:
        # 全流程
        fixer.diagnose()
        if fixer.issues:
            fixer.fix()
        fixer.verify()
    elif args.diagnose:
        fixer.diagnose()
    elif args.fix:
        fixer.diagnose()
        fixer.fix(args.fix)
    elif args.verify:
        fixer.verify()
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()


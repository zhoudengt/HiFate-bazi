#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions CI/CD 诊断脚本
用途：检查所有可能导致 CI/CD 失败的问题

使用方法：
  python3 scripts/ci/diagnose_github_actions.py
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

class GitHubActionsDiagnostic:
    """GitHub Actions CI/CD 诊断器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        
    def print_header(self, title: str):
        """打印标题"""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}{title:^60}{NC}")
        print(f"{BLUE}{'='*60}{NC}\n")
    
    def print_success(self, message: str):
        """打印成功消息"""
        print(f"{GREEN}✅ {message}{NC}")
        self.info.append(message)
    
    def print_warning(self, message: str):
        """打印警告消息"""
        print(f"{YELLOW}⚠️  {message}{NC}")
        self.warnings.append(message)
    
    def print_error(self, message: str):
        """打印错误消息"""
        print(f"{RED}❌ {message}{NC}")
        self.errors.append(message)
    
    def check_file_exists(self, file_path: Path, description: str) -> bool:
        """检查文件是否存在"""
        if file_path.exists():
            self.print_success(f"{description}: {file_path}")
            return True
        else:
            self.print_error(f"{description} 不存在: {file_path}")
            return False
    
    def check_file_executable(self, file_path: Path, description: str) -> bool:
        """检查文件是否可执行"""
        if not file_path.exists():
            return False
        
        if os.access(file_path, os.X_OK):
            self.print_success(f"{description} 可执行: {file_path}")
            return True
        else:
            self.print_warning(f"{description} 不可执行: {file_path}")
            return False
    
    def check_python_script(self, script_path: Path, description: str) -> bool:
        """检查 Python 脚本是否可以执行"""
        if not self.check_file_exists(script_path, description):
            return False
        
        # 检查是否有 shebang
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line.startswith('#!'):
                    self.print_warning(f"{description} 缺少 shebang: {script_path}")
        except Exception as e:
            self.print_error(f"无法读取 {description}: {e}")
            return False
        
        # 尝试导入脚本（检查语法）
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', str(script_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.print_success(f"{description} 语法正确: {script_path}")
                return True
            else:
                self.print_error(f"{description} 语法错误: {script_path}\n{result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.print_warning(f"{description} 编译超时: {script_path}")
            return True  # 超时不算错误
        except Exception as e:
            self.print_error(f"无法编译 {description}: {e}")
            return False
    
    def check_bash_script(self, script_path: Path, description: str) -> bool:
        """检查 Bash 脚本"""
        if not self.check_file_exists(script_path, description):
            return False
        
        # 检查是否有 shebang
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line.startswith('#!'):
                    self.print_warning(f"{description} 缺少 shebang: {script_path}")
        except Exception as e:
            self.print_error(f"无法读取 {description}: {e}")
            return False
        
        # 检查语法（使用 bash -n）
        try:
            result = subprocess.run(
                ['bash', '-n', str(script_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.print_success(f"{description} 语法正确: {script_path}")
                return True
            else:
                self.print_error(f"{description} 语法错误: {script_path}\n{result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.print_warning(f"{description} 语法检查超时: {script_path}")
            return True
        except Exception as e:
            self.print_error(f"无法检查 {description} 语法: {e}")
            return False
    
    def check_python_dependencies(self) -> bool:
        """检查 Python 依赖"""
        self.print_header("检查 Python 依赖")
        
        requirements_file = PROJECT_ROOT / 'requirements.txt'
        if not requirements_file.exists():
            self.print_error("requirements.txt 不存在")
            return False
        
        self.print_success(f"requirements.txt 存在: {requirements_file}")
        
        # 检查关键依赖
        key_dependencies = [
            'fastapi',
            'grpcio',
            'grpcio-tools',
            'pytest',
            'black',
            'isort',
            'pylint',
            'mypy'
        ]
        
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            missing_deps = []
            for dep in key_dependencies:
                if dep.lower() not in content.lower():
                    missing_deps.append(dep)
            
            if missing_deps:
                self.print_warning(f"可能缺少依赖: {', '.join(missing_deps)}")
            else:
                self.print_success("关键依赖都在 requirements.txt 中")
            
            return True
        except Exception as e:
            self.print_error(f"无法读取 requirements.txt: {e}")
            return False
    
    def check_review_scripts(self) -> bool:
        """检查代码审查脚本"""
        self.print_header("检查代码审查脚本")
        
        review_scripts = [
            ('check_cursorrules.py', '开发规范符合性检查'),
            ('check_security.py', '安全漏洞检查'),
            ('check_hot_reload.py', '热更新支持检查'),
            ('check_encoding.py', '编码方式检查'),
            ('check_grpc.py', 'gRPC 端点注册检查'),
            ('check_tests.py', '测试覆盖检查'),
            ('code_review_check.py', '综合代码审查检查'),
        ]
        
        all_ok = True
        for script_name, description in review_scripts:
            script_path = PROJECT_ROOT / 'scripts' / 'review' / script_name
            if not self.check_python_script(script_path, description):
                all_ok = False
        
        return all_ok
    
    def check_grpc_scripts(self) -> bool:
        """检查 gRPC 脚本"""
        self.print_header("检查 gRPC 脚本")
        
        grpc_scripts = [
            ('generate_grpc_code.sh', 'gRPC 代码生成脚本', self.check_bash_script),
            ('fix_version_check.py', 'gRPC 版本检查修复脚本', self.check_python_script),
        ]
        
        all_ok = True
        for script_name, description, check_func in grpc_scripts:
            script_path = PROJECT_ROOT / 'scripts' / 'grpc' / script_name
            if not check_func(script_path, description):
                all_ok = False
        
        # 检查 proto 目录
        proto_dir = PROJECT_ROOT / 'proto'
        if proto_dir.exists():
            proto_files = list(proto_dir.glob('*.proto'))
            if proto_files:
                self.print_success(f"找到 {len(proto_files)} 个 .proto 文件")
            else:
                self.print_warning("proto 目录中没有 .proto 文件")
        else:
            self.print_error("proto 目录不存在")
            all_ok = False
        
        # 检查 generated 目录
        generated_dir = PROJECT_ROOT / 'proto' / 'generated'
        if generated_dir.exists():
            grpc_files = list(generated_dir.glob('*_pb2_grpc.py'))
            if grpc_files:
                self.print_success(f"找到 {len(grpc_files)} 个生成的 gRPC 文件")
            else:
                self.print_warning("proto/generated 目录中没有生成的 gRPC 文件")
        else:
            self.print_warning("proto/generated 目录不存在（可能需要生成）")
        
        return all_ok
    
    def check_workflow_file(self) -> bool:
        """检查 workflow 文件"""
        self.print_header("检查 GitHub Actions Workflow 文件")
        
        workflow_file = PROJECT_ROOT / '.github' / 'workflows' / 'ci.yml'
        if not self.check_file_exists(workflow_file, 'CI workflow 文件'):
            return False
        
        # 检查 workflow 文件内容
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查关键步骤
            key_steps = [
                '代码质量检查',
                '代码审查检查',
                '单元测试',
                '安装依赖',
            ]
            
            for step in key_steps:
                if step in content:
                    self.print_success(f"Workflow 包含步骤: {step}")
                else:
                    self.print_warning(f"Workflow 可能缺少步骤: {step}")
            
            return True
        except Exception as e:
            self.print_error(f"无法读取 workflow 文件: {e}")
            return False
    
    def check_test_files(self) -> bool:
        """检查测试文件"""
        self.print_header("检查测试文件")
        
        test_dirs = [
            PROJECT_ROOT / 'tests' / 'unit',
            PROJECT_ROOT / 'tests' / 'api',
            PROJECT_ROOT / 'tests' / 'integration',
        ]
        
        all_ok = True
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files = list(test_dir.glob('test_*.py'))
                if test_files:
                    self.print_success(f"{test_dir.name} 目录有 {len(test_files)} 个测试文件")
                else:
                    self.print_warning(f"{test_dir.name} 目录中没有测试文件")
            else:
                self.print_warning(f"{test_dir.name} 目录不存在")
        
        return all_ok
    
    def check_grpc_import(self) -> bool:
        """检查 gRPC 代码是否可以导入"""
        self.print_header("检查 gRPC 代码导入")
        
        generated_dir = PROJECT_ROOT / 'proto' / 'generated'
        if not generated_dir.exists():
            self.print_warning("proto/generated 目录不存在，跳过导入检查")
            return True
        
        # 检查关键 gRPC 文件
        key_grpc_files = [
            'bazi_core_pb2_grpc.py',
            'bazi_rule_pb2_grpc.py',
        ]
        
        all_ok = True
        for grpc_file in key_grpc_files:
            grpc_path = generated_dir / grpc_file
            if not grpc_path.exists():
                self.print_warning(f"gRPC 文件不存在: {grpc_file}")
                continue
            
            # 尝试导入
            try:
                import sys
                sys.path.insert(0, str(generated_dir))
                
                module_name = grpc_file.replace('.py', '')
                result = subprocess.run(
                    [sys.executable, '-c', f'import sys; sys.path.insert(0, "{generated_dir}"); import {module_name}'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(PROJECT_ROOT)
                )
                
                if result.returncode == 0:
                    self.print_success(f"可以导入: {grpc_file}")
                else:
                    self.print_error(f"无法导入: {grpc_file}\n{result.stderr}")
                    all_ok = False
            except Exception as e:
                self.print_error(f"导入检查失败 {grpc_file}: {e}")
                all_ok = False
        
        return all_ok
    
    def run_all_checks(self) -> Tuple[bool, int, int]:
        """运行所有检查"""
        print(f"\n{GREEN}{'='*60}{NC}")
        print(f"{GREEN}GitHub Actions CI/CD 诊断工具{NC}")
        print(f"{GREEN}{'='*60}{NC}")
        
        checks = [
            ('Python 依赖', self.check_python_dependencies),
            ('代码审查脚本', self.check_review_scripts),
            ('gRPC 脚本', self.check_grpc_scripts),
            ('Workflow 文件', self.check_workflow_file),
            ('测试文件', self.check_test_files),
            ('gRPC 导入', self.check_grpc_import),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                if not check_func():
                    all_passed = False
            except Exception as e:
                self.print_error(f"{check_name} 检查异常: {e}")
                all_passed = False
        
        return all_passed, len(self.errors), len(self.warnings)
    
    def print_summary(self):
        """打印总结"""
        self.print_header("诊断总结")
        
        print(f"{GREEN}✅ 信息: {len(self.info)} 条{NC}")
        print(f"{YELLOW}⚠️  警告: {len(self.warnings)} 条{NC}")
        print(f"{RED}❌ 错误: {len(self.errors)} 条{NC}")
        
        if self.errors:
            print(f"\n{RED}错误列表:{NC}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n{YELLOW}警告列表:{NC}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print(f"\n{GREEN}🎉 所有检查通过！CI/CD 配置看起来正常。{NC}")
        elif not self.errors:
            print(f"\n{YELLOW}⚠️  有一些警告，但可能不影响 CI/CD 运行。{NC}")
        else:
            print(f"\n{RED}❌ 发现错误，请修复后再运行 CI/CD。{NC}")


def main():
    """主函数"""
    diagnostic = GitHubActionsDiagnostic()
    
    try:
        all_passed, error_count, warning_count = diagnostic.run_all_checks()
        diagnostic.print_summary()
        
        # 返回适当的退出码
        if error_count > 0:
            sys.exit(1)
        elif warning_count > 0:
            sys.exit(0)  # 警告不算失败
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}诊断被用户中断{NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}诊断过程发生异常: {e}{NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

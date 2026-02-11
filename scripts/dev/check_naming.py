#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命名规范检查工具
用途：检查代码命名是否符合规范

使用方法：
  python3 scripts/dev/check_naming.py [文件路径...]
  python3 scripts/dev/check_naming.py --all  # 检查所有文件
"""

import sys
import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# 命名规范正则表达式
NAMING_PATTERNS = {
    'variable': re.compile(r'^[a-z][a-z0-9_]*$'),  # snake_case
    'function': re.compile(r'^[a-z][a-z0-9_]*$'),  # snake_case
    'class': re.compile(r'^[A-Z][a-zA-Z0-9]*$'),  # PascalCase
    'constant': re.compile(r'^_?[A-Z][A-Z0-9_]*$'),  # _?UPPER_SNAKE_CASE（允许私有常量）
    'file': re.compile(r'^[a-z][a-z0-9_]*\.py$'),  # snake_case.py
}


class NamingChecker:
    """命名规范检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checked_files = []
    
    def check_file(self, file_path: str) -> bool:
        """检查单个文件的命名规范"""
        if not os.path.exists(file_path):
            return True
        
        if not file_path.endswith('.py'):
            return True
        
        # 检查文件名
        file_name = Path(file_path).name
        if not NAMING_PATTERNS['file'].match(file_name):
            self.errors.append(f"{file_path} - 文件名不符合规范: {file_name}，应为 snake_case.py")
        
        # 解析 Python 文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            self.errors.append(f"{file_path} - 语法错误: {e}")
            return False
        except Exception as e:
            self.warnings.append(f"{file_path} - 无法解析: {e}")
            return True
        
        # 检查 AST 节点
        self._check_ast_node(tree, file_path)
        
        return len(self.errors) == 0
    
    def _check_ast_node(self, node: ast.AST, file_path: str):
        """递归检查 AST 节点"""
        if isinstance(node, ast.FunctionDef):
            # 检查函数名
            if not NAMING_PATTERNS['function'].match(node.name):
                # 私有方法允许下划线开头
                if not node.name.startswith('_'):
                    self.errors.append(f"{file_path}:{node.lineno} - 函数名不符合规范: {node.name}，应为 snake_case")
                elif node.name.startswith('__') and not node.name.endswith('__'):
                    # 魔法方法允许双下划线
                    pass
                elif not NAMING_PATTERNS['function'].match(node.name.lstrip('_')):
                    self.warnings.append(f"{file_path}:{node.lineno} - 函数名建议使用 snake_case: {node.name}")
        
        elif isinstance(node, ast.ClassDef):
            # 检查类名
            if not NAMING_PATTERNS['class'].match(node.name):
                self.errors.append(f"{file_path}:{node.lineno} - 类名不符合规范: {node.name}，应为 PascalCase")
        
        elif isinstance(node, ast.Assign):
            # 检查变量名和常量名
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    
                    # 例外：PascalCase 变量名允许用于类引用，包括：
                    # 1. 类占位符：Limiter = None / RateLimitExceeded = None
                    # 2. 动态导入的类引用：ClassName = mod.ClassName
                    if NAMING_PATTERNS['class'].match(name):
                        if isinstance(node.value, ast.Constant) and node.value.value is None:
                            continue  # 类占位符
                        if isinstance(node.value, ast.Attribute):
                            continue  # 模块属性访问（动态导入类引用）
                    
                    # 判断是常量还是变量
                    if name.isupper() or '_' in name and name.isupper():
                        # 常量
                        if not NAMING_PATTERNS['constant'].match(name):
                            self.errors.append(f"{file_path}:{node.lineno} - 常量名不符合规范: {name}，应为 UPPER_SNAKE_CASE")
                    else:
                        # 变量
                        if not NAMING_PATTERNS['variable'].match(name):
                            # 私有变量允许下划线开头
                            if not name.startswith('_'):
                                self.errors.append(f"{file_path}:{node.lineno} - 变量名不符合规范: {name}，应为 snake_case")
                            elif not NAMING_PATTERNS['variable'].match(name.lstrip('_')):
                                self.warnings.append(f"{file_path}:{node.lineno} - 变量名建议使用 snake_case: {name}")
        
        # 递归检查子节点
        for child in ast.iter_child_nodes(node):
            self._check_ast_node(child, file_path)
    
    def check_all(self) -> bool:
        """检查所有 Python 文件"""
        print(f"{BLUE}🔍 开始检查所有文件的命名规范...{NC}\n")
        
        # 查找所有 Python 文件
        python_files = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # 跳过一些目录
            if any(skip in root for skip in ['.git', '__pycache__', '.venv', 'venv', 'node_modules']):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        print(f"{BLUE}找到 {len(python_files)} 个 Python 文件{NC}\n")
        
        all_passed = True
        for file_path in python_files:
            if not self.check_file(file_path):
                all_passed = False
        
        # 输出结果
        self._print_results()
        
        return all_passed
    
    def _print_results(self):
        """输出检查结果"""
        print(f"\n{BLUE}📊 检查结果：{NC}\n")
        
        if self.errors:
            print(f"{RED}❌ 发现 {len(self.errors)} 个错误：{NC}")
            for error in self.errors[:20]:  # 只显示前20个
                print(f"  {RED}✗{NC} {error}")
            if len(self.errors) > 20:
                print(f"  {RED}... 还有 {len(self.errors) - 20} 个错误{NC}")
            print()
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个警告：{NC}")
            for warning in self.warnings[:10]:  # 只显示前10个
                print(f"  {YELLOW}⚠{NC} {warning}")
            if len(self.warnings) > 10:
                print(f"  {YELLOW}... 还有 {len(self.warnings) - 10} 个警告{NC}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ 所有命名规范检查通过！{NC}\n")
        elif not self.errors:
            print(f"{GREEN}✅ 命名规范检查完成（有警告）{NC}\n")
        else:
            print(f"{RED}❌ 命名规范检查失败，请修复错误后重试{NC}\n")
    
    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """获取警告列表"""
        return self.warnings


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='命名规范检查工具')
    parser.add_argument('files', nargs='*', help='要检查的文件路径（如果不提供，检查所有变更的文件）')
    parser.add_argument('--all', action='store_true', help='检查所有文件')
    parser.add_argument('--exit-on-error', action='store_true', help='发现错误时退出（用于 CI/CD）')
    
    args = parser.parse_args()
    
    checker = NamingChecker()
    success = False
    
    if args.all:
        success = checker.check_all()
    elif args.files:
        print(f"{BLUE}🔍 开始检查指定文件...{NC}\n")
        for file_path in args.files:
            if not checker.check_file(file_path):
                success = False
        checker._print_results()
        success = len(checker.errors) == 0
    else:
        # 检查变更的文件
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            if result.returncode == 0:
                changed_files = [f for f in result.stdout.strip().split('\n') if f and f.endswith('.py')]
                if changed_files:
                    print(f"{BLUE}🔍 检查变更的文件...{NC}\n")
                    for file_path in changed_files:
                        full_path = PROJECT_ROOT / file_path
                        if full_path.exists():
                            if not checker.check_file(str(full_path)):
                                success = False
                    checker._print_results()
                    success = len(checker.errors) == 0
                else:
                    print(f"{YELLOW}⚠️  未找到需要检查的文件{NC}")
                    success = True
            else:
                print(f"{YELLOW}⚠️  无法获取变更文件列表{NC}")
                success = True
        except Exception as e:
            print(f"{YELLOW}⚠️  检查变更文件失败: {e}{NC}")
            success = True
    
    if args.exit_on_error and not success:
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


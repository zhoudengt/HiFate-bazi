#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新支持检查脚本
用途：检查代码是否支持热更新

使用方法：
  python3 scripts/review/check_hot_reload.py [文件路径...]
"""

import sys
import os
import ast
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

class HotReloadChecker:
    """热更新支持检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def check_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """检查文件是否支持热更新"""
        errors = []
        warnings = []
        
        if not os.path.exists(file_path):
            return True, [], []
        
        if not file_path.endswith('.py'):
            return True, [], []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # 语法错误，跳过检查
            return True, [], []
        
        # 1. 检查模块级全局状态初始化
        errors.extend(self._check_module_level_state(file_path, tree))
        
        # 2. 检查单例类是否有 reset 方法
        warnings.extend(self._check_singleton_reset(file_path, tree))
        
        return len(errors) == 0, errors, warnings
    
    def _check_module_level_state(self, file_path: str, tree: ast.AST) -> List[str]:
        """检查模块级全局状态初始化"""
        errors = []
        
        # 查找模块级的赋值语句（非函数/类内部）
        # 使用 ast.NodeVisitor 遍历 AST
        class ModuleLevelStateVisitor(ast.NodeVisitor):
            def __init__(self, file_path):
                self.file_path = file_path
                self.errors = []
                self.in_function = False
                self.in_class = False
            
            def visit_FunctionDef(self, node):
                old_in_function = self.in_function
                self.in_function = True
                self.generic_visit(node)
                self.in_function = old_in_function
            
            def visit_ClassDef(self, node):
                old_in_class = self.in_class
                self.in_class = True
                self.generic_visit(node)
                self.in_class = old_in_class
            
            def visit_Assign(self, node):
                # 检查是否在模块级别（不在函数/类内部）
                if not self.in_function and not self.in_class:
                    # 检查是否初始化了复杂对象（列表、字典、对象实例）
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            
                            # 检查是否初始化了全局状态
                            if isinstance(node.value, (ast.List, ast.Dict, ast.Call)):
                                # 排除导入语句和常量定义
                                if isinstance(node.value, ast.Call):
                                    if isinstance(node.value.func, ast.Name):
                                        # 排除 os.getenv 等函数调用
                                        if node.value.func.id not in ['getenv', 'environ', 'get']:
                                            self.errors.append(f"{self.file_path} - 模块级全局状态初始化 '{var_name}' 可能影响热更新，应使用函数/类方法")
                                else:
                                    self.errors.append(f"{self.file_path} - 模块级全局状态初始化 '{var_name}' 可能影响热更新，应使用函数/类方法")
                self.generic_visit(node)
        
        visitor = ModuleLevelStateVisitor(file_path)
        visitor.visit(tree)
        errors.extend(visitor.errors)
        
        return errors
    
    def _check_singleton_reset(self, file_path: str, tree: ast.AST) -> List[str]:
        """检查单例类是否有 reset 方法"""
        warnings = []
        
        # 查找单例模式
        class SingletonVisitor(ast.NodeVisitor):
            def __init__(self, file_path):
                self.file_path = file_path
                self.warnings = []
            
            def visit_ClassDef(self, node):
                class_name = node.name
                
                # 检查是否有 _instance 属性（单例模式特征）
                has_instance = False
                has_reset = False
                
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == '_instance':
                                has_instance = True
                    
                    if isinstance(item, ast.FunctionDef) and item.name == 'reset':
                        has_reset = True
                
                if has_instance and not has_reset:
                    self.warnings.append(f"{self.file_path} - 单例类 '{class_name}' 应提供 reset() 方法以支持热更新")
                
                self.generic_visit(node)
        
        visitor = SingletonVisitor(file_path)
        visitor.visit(tree)
        warnings.extend(visitor.warnings)
        
        return warnings
    
    def run(self, file_paths: List[str]) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 检查热更新支持...{NC}\n")
        
        all_valid = True
        for file_path in file_paths:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue
            
            is_valid, errors, warnings = self.check_file(str(full_path))
            
            if errors:
                all_valid = False
                self.errors.extend([(file_path, e) for e in errors])
            
            if warnings:
                self.warnings.extend([(file_path, w) for w in warnings])
        
        # 输出结果
        if self.errors:
            print(f"{RED}❌ 发现 {len(self.errors)} 个热更新问题：{NC}")
            for file_path, error in self.errors:
                print(f"  {RED}✗{NC} {error}")
            print()
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个警告：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ 热更新支持检查通过！{NC}\n")
            return True
        
        return all_valid


def main():
    """主函数"""
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description='热更新支持检查')
    parser.add_argument('files', nargs='*', help='要检查的文件路径')
    
    args = parser.parse_args()
    
    if not args.files:
        # 检查变更的文件
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        if result.returncode == 0:
            files = [f for f in result.stdout.strip().split('\n') if f and f.endswith('.py')]
        else:
            files = []
    else:
        files = args.files
    
    if not files:
        print(f"{YELLOW}⚠️  未找到需要检查的文件{NC}")
        return
    
    checker = HotReloadChecker()
    success = checker.run(files)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


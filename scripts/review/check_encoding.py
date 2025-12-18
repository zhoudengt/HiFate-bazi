#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码方式检查脚本
用途：检查数据库操作是否使用正确的编码方式（UNHEX、BINARY）

使用方法：
  python3 scripts/review/check_encoding.py [文件路径...]
"""

import sys
import os
import re
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

class EncodingChecker:
    """编码方式检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def check_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """检查文件的编码方式"""
        errors = []
        warnings = []
        
        if not os.path.exists(file_path):
            return True, [], []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 检查数据库操作文件
        if 'db' in file_path or 'service' in file_path or 'migration' in file_path:
            # 1. 检查 INSERT 语句是否使用 UNHEX
            errors.extend(self._check_insert_unhex(file_path, lines))
            
            # 2. 检查 SELECT 语句是否使用 BINARY 比较
            errors.extend(self._check_select_binary(file_path, lines))
        
        return len(errors) == 0, errors, warnings
    
    def _check_insert_unhex(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 INSERT 语句是否使用 UNHEX"""
        errors = []
        
        # 中文字符列表（建除相关）
        chinese_chars = ['收', '建', '除', '满', '平', '定', '执', '破', '危', '成', '开', '闭']
        
        for i, line in enumerate(lines, 1):
            if 'INSERT' in line.upper():
                # 检查是否包含中文字符
                has_chinese = any(char in line for char in chinese_chars)
                
                if has_chinese:
                    # 检查是否使用 UNHEX
                    if 'UNHEX' not in line.upper():
                        # 检查是否是 SQL 文件（可能直接写 SQL）
                        if file_path.endswith('.sql'):
                            errors.append(f"{file_path}:{i} - INSERT 语句包含中文字符，应使用 UNHEX 确保编码正确")
                        # 检查是否是 Python 文件（可能生成 SQL）
                        elif file_path.endswith('.py'):
                            # 检查是否在生成 SQL
                            if 'INSERT' in line.upper() and ('f"' in line or "f'" in line):
                                if 'UNHEX' not in line.upper() and 'generate_unhex_sql' not in line:
                                    errors.append(f"{file_path}:{i} - 生成包含中文字符的 INSERT SQL 应使用 UNHEX 或 generate_unhex_sql()")
        
        return errors
    
    def _check_select_binary(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 SELECT 语句是否使用 BINARY 比较"""
        errors = []
        
        # 中文字段列表
        chinese_fields = ['jianchu', 'direction', 'shishen', 'content']
        
        for i, line in enumerate(lines, 1):
            if 'SELECT' in line.upper() and 'WHERE' in line.upper():
                # 检查是否包含中文字段
                has_chinese_field = any(field in line.lower() for field in chinese_fields)
                
                if has_chinese_field:
                    # 检查是否使用 BINARY 比较
                    if 'BINARY' not in line.upper():
                        # 检查是否是 Python 文件中的 SQL 查询
                        if file_path.endswith('.py'):
                            # 检查是否是 cursor.execute 调用
                            if 'cursor.execute' in line or 'execute(' in line:
                                errors.append(f"{file_path}:{i} - 中文字段查询应使用 BINARY 比较，例如：WHERE BINARY jianchu = %s")
        
        return errors
    
    def run(self, file_paths: List[str]) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 检查编码方式...{NC}\n")
        
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
            print(f"{RED}❌ 发现 {len(self.errors)} 个编码问题：{NC}")
            for file_path, error in self.errors:
                print(f"  {RED}✗{NC} {error}")
            print()
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个警告：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ 编码方式检查通过！{NC}\n")
            return True
        
        return all_valid


def main():
    """主函数"""
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description='编码方式检查')
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
            files = [f for f in result.stdout.strip().split('\n') if f]
        else:
            files = []
    else:
        files = args.files
    
    if not files:
        print(f"{YELLOW}⚠️  未找到需要检查的文件{NC}")
        return
    
    checker = EncodingChecker()
    success = checker.run(files)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


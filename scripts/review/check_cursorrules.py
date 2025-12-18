#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发规范符合性检查脚本
用途：检查代码是否符合 .cursorrules 中的规范要求

使用方法：
  python3 scripts/review/check_cursorrules.py [文件路径...]
"""

import sys
import os
import re
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
NC = '\033[0m'

class CursorRulesChecker:
    """开发规范检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.cursorrules_path = PROJECT_ROOT / '.cursorrules'
        
    def check_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """检查文件是否符合开发规范"""
        errors = []
        warnings = []
        
        if not os.path.exists(file_path):
            return True, [], []
        
        if not file_path.endswith('.py'):
            return True, [], []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return True, [], []
        
        # 1. 检查硬编码路径（规范要求）
        errors.extend(self._check_hardcoded_paths(file_path, lines))
        
        # 2. 检查文件操作异常处理（规范要求）
        errors.extend(self._check_file_operations(file_path, lines))
        
        # 3. 检查 JSON 序列化（规范要求 ensure_ascii=False）
        errors.extend(self._check_json_serialization(file_path, lines))
        
        # 4. 检查 Pydantic 模型（规范要求）
        if 'api' in file_path:
            errors.extend(self._check_pydantic_models(file_path, lines))
        
        # 5. 检查规则存储（规范要求：禁止从文件读取）
        if 'rule' in file_path.lower():
            errors.extend(self._check_rule_storage(file_path, lines))
        
        return len(errors) == 0, errors, warnings
    
    def _check_hardcoded_paths(self, file_path: str, lines: List[str]) -> List[str]:
        """检查硬编码路径"""
        errors = []
        patterns = [
            r'/Users/[^/]+/',
            r'C:\\Users\\[^\\]+\\',
            r'/home/[^/]+/',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    # 排除注释和文档字符串
                    stripped = line.strip()
                    if stripped.startswith('#') or '"""' in line or "'''" in line:
                        continue
                    if 'PROJECT_ROOT' not in line and 'os.path' not in line and 'Path(__file__)' not in line:
                        errors.append(f"{file_path}:{i} - 硬编码路径，应使用动态路径（基于 PROJECT_ROOT）")
        
        return errors
    
    def _check_file_operations(self, file_path: str, lines: List[str]) -> List[str]:
        """检查文件操作是否有异常处理"""
        errors = []
        
        file_operations = ['open(', 'write(', 'read(']
        for i, line in enumerate(lines, 1):
            for op in file_operations:
                if op in line:
                    # 检查上下几行是否有 try-except
                    context_start = max(0, i - 5)
                    context_end = min(len(lines), i + 5)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    if 'try:' not in context and 'with open' not in line:
                        errors.append(f"{file_path}:{i} - 文件操作应有异常处理")
        
        return errors
    
    def _check_json_serialization(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 JSON 序列化是否使用 ensure_ascii=False"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            if 'json.dumps' in line:
                # 排除注释和测试文件
                if line.strip().startswith('#') or 'test' in file_path:
                    continue
                if 'ensure_ascii=False' not in line:
                    # 检查是否包含中文字符（可能不需要 ensure_ascii=False）
                    if '中文' not in line and '[\u4e00-\u9fff]' not in line:
                        continue
                    errors.append(f"{file_path}:{i} - JSON 序列化应使用 ensure_ascii=False 支持中文")
        
        return errors
    
    def _check_pydantic_models(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 Pydantic 模型是否使用 Field"""
        warnings = []
        
        has_model = False
        has_field = False
        
        for line in lines:
            if 'BaseModel' in line:
                has_model = True
            if 'Field(' in line:
                has_field = True
        
        if has_model and not has_field:
            warnings.append(f"{file_path} - Pydantic 模型应使用 Field 提供描述和示例")
        
        return warnings
    
    def _check_rule_storage(self, file_path: str, lines: List[str]) -> List[str]:
        """检查规则是否从文件读取（规范禁止）"""
        errors = []
        
        forbidden_patterns = [
            r'open\([^)]*\.json',
            r'open\([^)]*\.xlsx',
            r'open\([^)]*\.xls',
            r'pd\.read_excel',
            r'json\.load\([^)]*open',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in forbidden_patterns:
                if re.search(pattern, line):
                    if 'RuleService' not in line and 'get_mysql_connection' not in line:
                        errors.append(f"{file_path}:{i} - 规则应从数据库读取，禁止从文件读取")
        
        return errors
    
    def run(self, file_paths: List[str]) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 检查开发规范符合性...{NC}\n")
        
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
            print(f"{RED}❌ 发现 {len(self.errors)} 个规范违反：{NC}")
            for file_path, error in self.errors:
                print(f"  {RED}✗{NC} {error}")
            print()
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个警告：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ 开发规范检查通过！{NC}\n")
            return True
        
        return all_valid


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='开发规范符合性检查')
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
    
    checker = CursorRulesChecker()
    success = checker.run(files)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


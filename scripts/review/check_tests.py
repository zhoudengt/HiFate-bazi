#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试覆盖检查脚本
用途：检查代码是否有测试覆盖

使用方法：
  python3 scripts/review/check_tests.py [文件路径...]
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple, Set

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

class TestCoverageChecker:
    """测试覆盖检查器"""
    
    def __init__(self):
        self.warnings = []
        self.tests_dir = PROJECT_ROOT / 'tests'
        
    def find_test_file(self, source_file: str) -> bool:
        """查找对应的测试文件"""
        # 转换源文件路径为测试文件路径
        # server/api/v1/bazi.py -> tests/api/test_bazi.py 或 tests/unit/test_bazi.py
        
        source_path = Path(source_file)
        
        # 跳过测试文件本身
        if 'test_' in source_path.name or 'tests' in str(source_path):
            return True
        
        # 跳过非 Python 文件
        if not source_file.endswith('.py'):
            return True
        
        # 跳过配置文件和工具文件
        if 'config' in source_file or 'utils' in source_file:
            return True
        
        # 提取模块名
        module_name = source_path.stem
        
        # 查找可能的测试文件
        possible_test_files = [
            self.tests_dir / 'unit' / f'test_{module_name}.py',
            self.tests_dir / 'api' / f'test_{module_name}.py',
            self.tests_dir / 'integration' / f'test_{module_name}.py',
        ]
        
        # 检查是否存在
        for test_file in possible_test_files:
            if test_file.exists():
                return True
        
        return False
    
    def check_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """检查文件是否有测试覆盖"""
        warnings = []
        
        # 跳过测试文件
        if 'test_' in file_path or 'tests' in file_path:
            return True, []
        
        # 跳过非 Python 文件
        if not file_path.endswith('.py'):
            return True, []
        
        # 跳过配置文件和工具文件
        if 'config' in file_path or 'utils' in file_path or '__init__' in file_path:
            return True, []
        
        # 检查是否有对应的测试文件
        has_test = self.find_test_file(file_path)
        
        if not has_test:
            # 判断文件重要性
            is_important = any(keyword in file_path for keyword in [
                'api', 'service', 'engine', 'rule'
            ])
            
            if is_important:
                warnings.append(f"{file_path} - 重要模块缺少测试文件，建议添加测试覆盖")
        
        return len(warnings) == 0, warnings
    
    def run(self, file_paths: List[str]) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 检查测试覆盖...{NC}\n")
        
        all_valid = True
        for file_path in file_paths:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue
            
            is_valid, warnings = self.check_file(str(full_path))
            
            if warnings:
                self.warnings.extend([(file_path, w) for w in warnings])
        
        # 输出结果
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个缺少测试的文件：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
            print(f"{YELLOW}提示：建议为新功能添加测试，确保测试覆盖率 ≥ 50%{NC}\n")
        else:
            print(f"{GREEN}✅ 测试覆盖检查通过！{NC}\n")
            all_valid = True
        
        return all_valid


def main():
    """主函数"""
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description='测试覆盖检查')
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
    
    checker = TestCoverageChecker()
    success = checker.run(files)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


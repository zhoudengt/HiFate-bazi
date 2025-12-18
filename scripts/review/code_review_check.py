#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码审查检查脚本
用途：自动检查代码是否符合开发规范要求

使用方法：
  python3 scripts/review/code_review_check.py [文件路径...]
  
如果不提供文件路径，将检查所有变更的文件（通过 git diff）
"""

import sys
import os
import re
import subprocess
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

class CodeReviewChecker:
    """代码审查检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checked_files = []
        
    def check_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        检查单个文件
        
        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        if not os.path.exists(file_path):
            return True, [], []
        
        # 只检查 Python 文件
        if not file_path.endswith('.py'):
            return True, [], []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 1. 检查硬编码路径
        errors.extend(self._check_hardcoded_paths(file_path, lines))
        
        # 2. 检查 SQL 注入风险
        errors.extend(self._check_sql_injection(file_path, lines))
        
        # 3. 检查 XSS 风险（前端文件）
        if 'frontend' in file_path or file_path.endswith('.html') or file_path.endswith('.js'):
            errors.extend(self._check_xss(file_path, lines))
        
        # 4. 检查敏感信息泄露
        errors.extend(self._check_sensitive_info(file_path, lines))
        
        # 5. 检查编码方式（数据库操作）
        if 'db' in file_path or 'service' in file_path:
            errors.extend(self._check_encoding(file_path, lines))
        
        # 6. 检查 gRPC 端点注册
        if 'api' in file_path:
            warnings.extend(self._check_grpc_registration(file_path, lines))
        
        # 7. 检查热更新支持
        errors.extend(self._check_hot_reload(file_path, lines))
        
        return len(errors) == 0, errors, warnings
    
    def _check_hardcoded_paths(self, file_path: str, lines: List[str]) -> List[str]:
        """检查硬编码路径"""
        errors = []
        patterns = [
            r'/Users/',
            r'C:\\Users\\',
            r'/home/[^/]+/',
            r'/opt/[^/]+/',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line) and 'PROJECT_ROOT' not in line:
                    errors.append(f"{file_path}:{i} - 发现硬编码路径，应使用动态路径（基于 PROJECT_ROOT）")
        
        return errors
    
    def _check_sql_injection(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 SQL 注入风险"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            # 检查字符串拼接的 SQL
            if re.search(r'f["\'].*SELECT|f["\'].*INSERT|f["\'].*UPDATE|f["\'].*DELETE', line):
                if '%s' not in line and '?' not in line:
                    errors.append(f"{file_path}:{i} - 发现 SQL 字符串拼接，应使用参数化查询")
            
            # 检查 % 格式化的 SQL
            if re.search(r'["\'].*%s.*SELECT|["\'].*%s.*INSERT', line):
                if 'cursor.execute' not in line or '%s' not in line:
                    errors.append(f"{file_path}:{i} - 发现 SQL 字符串格式化，应使用参数化查询")
        
        return errors
    
    def _check_xss(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 XSS 风险"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            # 检查直接使用 innerHTML
            if 'innerHTML' in line and 'DOMPurify' not in line and 'textContent' not in line:
                if 'user' in line.lower() or 'input' in line.lower():
                    errors.append(f"{file_path}:{i} - 发现直接使用 innerHTML，应使用 textContent 或 DOMPurify")
        
        return errors
    
    def _check_sensitive_info(self, file_path: str, lines: List[str]) -> List[str]:
        """检查敏感信息泄露"""
        errors = []
        
        sensitive_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        
        for i, line in enumerate(lines, 1):
            # 跳过注释和文档字符串
            if line.strip().startswith('#') or '"""' in line or "'''" in line:
                continue
            
            for pattern in sensitive_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if 'os.getenv' not in line and 'os.environ' not in line:
                        errors.append(f"{file_path}:{i} - 发现硬编码敏感信息，应使用环境变量")
        
        return errors
    
    def _check_encoding(self, file_path: str, lines: List[str]) -> List[str]:
        """检查编码方式"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            # 检查 INSERT 语句是否使用 UNHEX（中文字符）
            if 'INSERT' in line.upper() and ('收' in line or '建' in line or '除' in line):
                if 'UNHEX' not in line:
                    errors.append(f"{file_path}:{i} - 包含中文字符的 INSERT 应使用 UNHEX")
            
            # 检查 SELECT 语句是否使用 BINARY 比较（中文字段）
            if 'SELECT' in line.upper() and ('jianchu' in line or 'direction' in line or 'shishen' in line):
                if 'WHERE' in line.upper() and 'BINARY' not in line.upper():
                    errors.append(f"{file_path}:{i} - 中文字段查询应使用 BINARY 比较")
        
        return errors
    
    def _check_grpc_registration(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 gRPC 端点注册"""
        warnings = []
        
        # 检查是否定义了新的 API 端点
        has_api_definition = False
        for line in lines:
            if '@router.post' in line or '@router.get' in line:
                has_api_definition = True
                break
        
        if has_api_definition:
            # 检查是否在 grpc_gateway.py 中注册
            if 'grpc_gateway' not in file_path:
                warnings.append(f"{file_path} - 定义了新的 API 端点，请确认已在 grpc_gateway.py 中注册")
        
        return warnings
    
    def _check_hot_reload(self, file_path: str, lines: List[str]) -> List[str]:
        """检查热更新支持"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            # 检查模块级全局状态初始化
            if i == 1 and '=' in line and not line.strip().startswith('#'):
                if 'import' not in line and 'from' not in line:
                    # 可能是模块级初始化
                    if '[' in line or '{' in line or '=' in line:
                        errors.append(f"{file_path}:{i} - 模块级全局状态初始化可能影响热更新，应使用函数/类方法")
        
        return errors
    
    def check_changed_files(self) -> List[str]:
        """检查变更的文件"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f]
        except Exception:
            pass
        
        return []
    
    def run(self, file_paths: Optional[List[str]] = None) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 开始代码审查检查...{NC}\n")
        
        if file_paths is None:
            file_paths = self.check_changed_files()
        
        if not file_paths:
            print(f"{YELLOW}⚠️  未找到需要检查的文件{NC}")
            return True
        
        print(f"{BLUE}检查文件列表：{NC}")
        for f in file_paths:
            print(f"  - {f}")
        print()
        
        all_valid = True
        for file_path in file_paths:
            full_path = PROJECT_ROOT / file_path
            if not full_path.exists():
                continue
            
            is_valid, errors, warnings = self.check_file(str(full_path))
            self.checked_files.append(file_path)
            
            if errors:
                all_valid = False
                self.errors.extend([(file_path, e) for e in errors])
            
            if warnings:
                self.warnings.extend([(file_path, w) for w in warnings])
        
        # 输出结果
        print(f"\n{BLUE}📊 检查结果：{NC}\n")
        
        if self.errors:
            print(f"{RED}❌ 发现 {len(self.errors)} 个错误：{NC}")
            for file_path, error in self.errors:
                print(f"  {RED}✗{NC} {error}")
            print()
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个警告：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ 所有检查通过！{NC}\n")
            return True
        
        if self.errors:
            print(f"{RED}❌ 检查失败，请修复错误后重试{NC}\n")
            return False
        
        print(f"{YELLOW}⚠️  检查完成，但有警告，请确认{NC}\n")
        return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='代码审查检查脚本')
    parser.add_argument('files', nargs='*', help='要检查的文件路径（如果不提供，检查所有变更的文件）')
    parser.add_argument('--exit-on-error', action='store_true', help='发现错误时退出（用于 CI/CD）')
    
    args = parser.parse_args()
    
    checker = CodeReviewChecker()
    success = checker.run(args.files if args.files else None)
    
    if args.exit_on_error and not success:
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


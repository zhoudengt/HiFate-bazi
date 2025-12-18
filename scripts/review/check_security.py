#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全漏洞检查脚本
用途：检查代码中的安全漏洞（SQL 注入、XSS、敏感信息泄露等）

使用方法：
  python3 scripts/review/check_security.py [文件路径...]
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

class SecurityChecker:
    """安全检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def check_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """检查文件的安全漏洞"""
        errors = []
        warnings = []
        
        if not os.path.exists(file_path):
            return True, [], []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 1. 检查 SQL 注入
        errors.extend(self._check_sql_injection(file_path, lines))
        
        # 2. 检查 XSS（前端文件）
        if file_path.endswith('.html') or file_path.endswith('.js'):
            errors.extend(self._check_xss(file_path, lines))
        
        # 3. 检查敏感信息泄露
        errors.extend(self._check_sensitive_info(file_path, lines))
        
        # 4. 检查文件上传安全
        errors.extend(self._check_file_upload(file_path, lines))
        
        return len(errors) == 0, errors, warnings
    
    def _check_sql_injection(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 SQL 注入风险"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            # 检查 f-string SQL 拼接
            if re.search(r'f["\'].*SELECT|f["\'].*INSERT|f["\'].*UPDATE|f["\'].*DELETE', line):
                if '%s' not in line and '?' not in line and 'cursor.execute' in line:
                    errors.append(f"{file_path}:{i} - SQL 注入风险：使用 f-string 拼接 SQL，应使用参数化查询")
            
            # 检查 % 格式化 SQL
            if re.search(r'["\'].*%[sd].*SELECT|["\'].*%[sd].*INSERT', line):
                if 'cursor.execute' in line and '%s' not in line:
                    errors.append(f"{file_path}:{i} - SQL 注入风险：使用 % 格式化 SQL，应使用参数化查询")
            
            # 检查字符串拼接 SQL
            if 'SELECT' in line or 'INSERT' in line or 'UPDATE' in line:
                if '+' in line and 'cursor.execute' in line:
                    if '%s' not in line:
                        errors.append(f"{file_path}:{i} - SQL 注入风险：字符串拼接 SQL，应使用参数化查询")
        
        return errors
    
    def _check_xss(self, file_path: str, lines: List[str]) -> List[str]:
        """检查 XSS 风险"""
        errors = []
        
        for i, line in enumerate(lines, 1):
            # 检查直接使用 innerHTML
            if 'innerHTML' in line:
                if 'DOMPurify' not in line and 'textContent' not in line:
                    # 检查是否包含用户输入
                    if any(keyword in line.lower() for keyword in ['user', 'input', 'data', 'value']):
                        errors.append(f"{file_path}:{i} - XSS 风险：直接使用 innerHTML，应使用 textContent 或 DOMPurify.sanitize()")
            
            # 检查 eval 使用
            if 'eval(' in line:
                errors.append(f"{file_path}:{i} - XSS 风险：使用 eval()，应避免使用")
        
        return errors
    
    def _check_sensitive_info(self, file_path: str, lines: List[str]) -> List[str]:
        """检查敏感信息泄露"""
        errors = []
        
        sensitive_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', '密码'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'API Key'),
            (r'secret\s*=\s*["\'][^"\']+["\']', '密钥'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'Token'),
            (r'access_key\s*=\s*["\'][^"\']+["\']', 'Access Key'),
        ]
        
        for i, line in enumerate(lines, 1):
            # 跳过注释和文档字符串
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            for pattern, info_type in sensitive_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if 'os.getenv' not in line and 'os.environ' not in line and 'load_dotenv' not in line:
                        errors.append(f"{file_path}:{i} - 敏感信息泄露：硬编码 {info_type}，应使用环境变量")
        
        return errors
    
    def _check_file_upload(self, file_path: str, lines: List[str]) -> List[str]:
        """检查文件上传安全"""
        errors = []
        warnings = []
        
        has_upload = False
        has_validation = False
        
        for i, line in enumerate(lines, 1):
            if 'UploadFile' in line or 'file' in line.lower():
                has_upload = True
            
            if 'mime_type' in line or 'file_type' in line or 'allowed' in line.lower():
                has_validation = True
        
        if has_upload and not has_validation:
            warnings.append(f"{file_path} - 文件上传功能应验证文件类型和大小")
        
        return errors + warnings
    
    def run(self, file_paths: List[str]) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 检查安全漏洞...{NC}\n")
        
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
            print(f"{RED}❌ 发现 {len(self.errors)} 个安全漏洞：{NC}")
            for file_path, error in self.errors:
                print(f"  {RED}✗{NC} {error}")
            print()
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个安全警告：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ 安全检查通过！{NC}\n")
            return True
        
        return all_valid


def main():
    """主函数"""
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description='安全漏洞检查')
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
    
    checker = SecurityChecker()
    success = checker.run(files)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


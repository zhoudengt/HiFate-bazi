#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 端点注册检查脚本
用途：检查新增的 API 端点是否已在 grpc_gateway.py 中注册

使用方法：
  python3 scripts/review/check_grpc.py [文件路径...]
"""

import sys
import os
import re
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

class GrpcChecker:
    """gRPC 端点注册检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.grpc_gateway_path = PROJECT_ROOT / 'server' / 'api' / 'grpc_gateway.py'
        self.registered_endpoints = set()
        
    def load_registered_endpoints(self) -> Set[str]:
        """加载已注册的 gRPC 端点"""
        if not self.grpc_gateway_path.exists():
            return set()
        
        with open(self.grpc_gateway_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有注册的端点
        # 查找 @_register("/path") 模式
        pattern = r'@_register\(["\']([^"\']+)["\']'
        matches = re.findall(pattern, content)
        
        return set(matches)
    
    def extract_api_endpoints(self, file_path: str) -> List[str]:
        """提取文件中的 API 端点定义"""
        endpoints = []
        
        if not os.path.exists(file_path):
            return endpoints
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 查找 @router.post、@router.get 等装饰器
        for i, line in enumerate(lines, 1):
            # 匹配 @router.post("/path") 或 @router.get("/path")
            match = re.search(r'@router\.(post|get|put|delete)\(["\']([^"\']+)["\']', line)
            if match:
                method, path = match.groups()
                # 提取完整路径（可能需要组合 prefix）
                endpoints.append(path)
        
        return endpoints
    
    def check_file(self, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """检查文件的 gRPC 端点注册"""
        errors = []
        warnings = []
        
        # 只检查 API 文件
        if 'api' not in file_path or file_path.endswith('grpc_gateway.py'):
            return True, [], []
        
        if not file_path.endswith('.py'):
            return True, [], []
        
        # 提取 API 端点
        endpoints = self.extract_api_endpoints(file_path)
        
        if not endpoints:
            return True, [], []
        
        # 检查是否已注册
        registered = self.load_registered_endpoints()
        
        for endpoint in endpoints:
            # 标准化路径（移除前缀）
            normalized = endpoint.replace('/api/v1/', '').replace('/api/', '')
            
            # 检查是否已注册
            if normalized not in registered and endpoint not in registered:
                # 检查是否是内部端点（不需要注册）
                if '/internal/' in endpoint or '/admin/' in endpoint:
                    continue
                
                errors.append(f"{file_path} - API 端点 '{endpoint}' 未在 grpc_gateway.py 中注册")
        
        return len(errors) == 0, errors, warnings
    
    def run(self, file_paths: List[str]) -> bool:
        """运行检查"""
        print(f"{BLUE}🔍 检查 gRPC 端点注册...{NC}\n")
        
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
            print(f"{RED}❌ 发现 {len(self.errors)} 个未注册的端点：{NC}")
            for file_path, error in self.errors:
                print(f"  {RED}✗{NC} {error}")
            print()
            print(f"{YELLOW}提示：请在 server/api/grpc_gateway.py 中使用 @_register 装饰器注册端点{NC}\n")
        
        if self.warnings:
            print(f"{YELLOW}⚠️  发现 {len(self.warnings)} 个警告：{NC}")
            for file_path, warning in self.warnings:
                print(f"  {YELLOW}⚠{NC} {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print(f"{GREEN}✅ gRPC 端点注册检查通过！{NC}\n")
            return True
        
        return all_valid


def main():
    """主函数"""
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description='gRPC 端点注册检查')
    parser.add_argument('files', nargs='*', help='要检查的文件路径')
    parser.add_argument('--exit-on-error', action='store_true', help='发现错误时退出（用于 CI/CD）')
    
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
            files = [f for f in result.stdout.strip().split('\n') if f and 'api' in f]
        else:
            files = []
    else:
        files = args.files
    
    if not files:
        print(f"{YELLOW}⚠️  未找到需要检查的文件{NC}")
        return
    
    checker = GrpcChecker()
    success = checker.run(files)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


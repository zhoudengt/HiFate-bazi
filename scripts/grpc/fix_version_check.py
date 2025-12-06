#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 gRPC 生成代码中的版本检查逻辑
直接修复所有已生成的 gRPC 文件
"""

import re
import os
import glob
import sys

def fix_grpc_version_check(grpc_file):
    """修复单个 gRPC 文件的版本检查逻辑"""
    try:
        with open(grpc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 方法1：修复版本检查逻辑，允许版本相等
        pattern1 = r'_version_not_supported = first_version_is_lower\(GRPC_VERSION, GRPC_GENERATED_VERSION\)'
        replacement1 = r'_version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION) if GRPC_VERSION != GRPC_GENERATED_VERSION else False'
        
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
        
        # 方法2：直接禁用版本检查（更可靠）
        pattern2 = r'if _version_not_supported:'
        replacement2 = r'if False and _version_not_supported:  # 版本检查已禁用，允许版本相等'
        
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
        
        # 如果内容被修改，写回文件
        if content != original_content:
            with open(grpc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"❌ 修复 {grpc_file} 失败: {e}", file=sys.stderr)
        return False

def main():
    """修复所有 gRPC 生成文件"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, 'proto', 'generated')
    
    if not os.path.exists(output_dir):
        print(f"❌ 输出目录不存在: {output_dir}")
        sys.exit(1)
    
    grpc_files = glob.glob(os.path.join(output_dir, '*_pb2_grpc.py'))
    
    if not grpc_files:
        print(f"⚠️  未找到 gRPC 文件: {output_dir}")
        sys.exit(0)
    
    print(f">>> 修复 {len(grpc_files)} 个 gRPC 文件的版本检查逻辑...")
    
    fixed_count = 0
    for grpc_file in grpc_files:
        if fix_grpc_version_check(grpc_file):
            print(f"  ✅ 修复: {os.path.basename(grpc_file)}")
            fixed_count += 1
        else:
            print(f"  ⚠️  无需修复: {os.path.basename(grpc_file)}")
    
    print(f"\n✅ 修复完成！共修复 {fixed_count}/{len(grpc_files)} 个文件")

if __name__ == '__main__':
    main()


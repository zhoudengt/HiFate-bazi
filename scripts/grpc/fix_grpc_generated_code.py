#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 gRPC 生成代码，删除不兼容的方法调用
确保所有环境代码一致
"""

import os
import glob
import re
import sys

def fix_grpc_generated_code():
    """修复所有 gRPC 生成文件，删除 add_registered_method_handlers 调用"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proto_dir = os.path.join(project_root, 'proto', 'generated')
    
    if not os.path.exists(proto_dir):
        print(f"❌ 目录不存在: {proto_dir}")
        return False
    
    grpc_files = glob.glob(os.path.join(proto_dir, '*_pb2_grpc.py'))
    
    if not grpc_files:
        print(f"⚠️  未找到 gRPC 文件: {proto_dir}")
        return False
    
    print(f">>> 修复 {len(grpc_files)} 个 gRPC 生成文件...")
    print("    删除 add_registered_method_handlers 方法调用（兼容性修复）\n")
    
    fixed_count = 0
    for file_path in grpc_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 删除 add_registered_method_handlers 行
            # 匹配模式：包含 server.add_registered_method_handlers 的整行
            pattern = r'\s*server\.add_registered_method_handlers\([^)]+\)\s*\n'
            new_content = re.sub(pattern, '', content)
            
            # 如果内容被修改，写回文件
            if content != new_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  ✅ 修复: {os.path.basename(file_path)}")
                fixed_count += 1
            else:
                print(f"  ⚠️  无需修复: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"  ❌ 修复失败 {os.path.basename(file_path)}: {e}", file=sys.stderr)
            return False
    
    print(f"\n✅ 修复完成！共修复 {fixed_count}/{len(grpc_files)} 个文件")
    return True

if __name__ == '__main__':
    success = fix_grpc_generated_code()
    sys.exit(0 if success else 1)


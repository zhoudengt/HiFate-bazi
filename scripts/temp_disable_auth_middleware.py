#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时禁用认证中间件（紧急修复）
用于在无法重启服务器时临时解决401问题
"""

import sys
import os
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

MAIN_PY = os.path.join(project_root, "server", "main.py")
BACKUP_PY = os.path.join(project_root, "server", "main.py.backup")

def disable_auth_middleware():
    """临时禁用认证中间件"""
    print("🔧 临时禁用认证中间件...")
    
    # 1. 备份原文件
    if not os.path.exists(BACKUP_PY):
        print("  📋 备份 server/main.py...")
        with open(MAIN_PY, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(BACKUP_PY, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ 备份完成")
    else:
        print("  ℹ️  备份文件已存在，跳过备份")
    
    # 2. 读取文件
    with open(MAIN_PY, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 3. 注释掉中间件
    pattern = r'(app\.add_middleware\(AuthMiddleware\))'
    replacement = r'# ⚠️ 临时禁用: \1'
    
    if '# ⚠️ 临时禁用:' in content:
        print("  ℹ️  中间件已被禁用")
        return True
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content == content:
        print("  ⚠️  未找到中间件代码，可能已经禁用")
        return False
    
    # 4. 添加日志说明
    logger_pattern = r'(logger\.info\("✓ OAuth 2\.0 认证中间件已启用"\))'
    logger_replacement = r'logger.warning("⚠ 认证中间件已临时禁用（紧急修复）")\n    # \1'
    new_content = re.sub(logger_pattern, logger_replacement, new_content)
    
    # 5. 写入文件
    with open(MAIN_PY, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("  ✅ 中间件已临时禁用")
    print("  ⏳ 等待热更新生效（约1分钟）...")
    print("  📋 或手动触发热更新: touch server/main.py")
    
    return True

def restore_auth_middleware():
    """恢复认证中间件"""
    print("🔧 恢复认证中间件...")
    
    if not os.path.exists(BACKUP_PY):
        print("  ❌ 备份文件不存在，无法恢复")
        return False
    
    # 恢复文件
    with open(BACKUP_PY, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(MAIN_PY, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("  ✅ 中间件已恢复")
    print("  ⏳ 等待热更新生效（约1分钟）...")
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_auth_middleware()
    else:
        disable_auth_middleware()
        print("\n⚠️  这是临时方案！修复后必须恢复中间件：")
        print("   python3 scripts/temp_disable_auth_middleware.py restore")


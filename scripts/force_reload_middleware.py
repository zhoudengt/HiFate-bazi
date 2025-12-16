#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制重新加载中间件模块
用于确保中间件代码修改生效
"""

import sys
import os
import importlib

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def force_reload_middleware():
    """强制重新加载认证中间件模块"""
    print("🔄 强制重新加载认证中间件...")
    
    # 需要重新加载的模块
    modules_to_reload = [
        'server.middleware.auth_middleware',
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            print(f"  📦 重新加载: {module_name}")
            try:
                module = sys.modules[module_name]
                importlib.reload(module)
                
                # 验证重新加载是否成功
                if hasattr(module, 'WHITELIST_PREFIXES'):
                    prefixes = module.WHITELIST_PREFIXES
                    print(f"    ✅ 白名单前缀: {list(prefixes)}")
                    if '/frontend' in prefixes:
                        print(f"    ✅ 包含 /frontend 前缀")
                    else:
                        print(f"    ❌ 缺少 /frontend 前缀！")
                
                print(f"    ✅ 重新加载成功")
            except Exception as e:
                print(f"    ❌ 重新加载失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  ⚠️  模块未加载: {module_name}")
    
    print("\n✅ 中间件重新加载完成")
    print("⚠️  注意：由于FastAPI中间件在应用初始化时创建，")
    print("   可能需要重启服务才能真正生效。")

if __name__ == "__main__":
    force_reload_middleware()


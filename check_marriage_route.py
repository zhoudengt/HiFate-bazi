#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查婚姻分析路由是否正确注册"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # 检查路由导入
    from server.api.v1.marriage_analysis import router
    print("✓ 路由导入成功")
    print(f"  路由对象: {router}")
    print(f"  路由路径: {[r.path for r in router.routes if hasattr(r, 'path')]}")
    
    # 检查路由注册
    from server.main import app
    print("\n✓ FastAPI 应用加载成功")
    
    # 查找所有包含 marriage 的路由
    marriage_routes = [r for r in app.routes if hasattr(r, 'path') and 'marriage' in r.path.lower()]
    print(f"\n已注册的婚姻相关路由:")
    for route in marriage_routes:
        print(f"  - {route.path} ({route.methods if hasattr(route, 'methods') else 'N/A'})")
    
    if not marriage_routes:
        print("  ✗ 未找到婚姻相关路由！")
        print("\n所有路由:")
        all_routes = [r for r in app.routes if hasattr(r, 'path')]
        for route in all_routes[:20]:  # 只显示前20个
            print(f"  - {route.path}")
    
except Exception as e:
    print(f"✗ 检查失败: {e}")
    import traceback
    traceback.print_exc()


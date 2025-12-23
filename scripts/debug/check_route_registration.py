#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查路由注册状态
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # 检查路由导入
    from server.api.v1.xishen_jishen import router as xishen_jishen_router
    print(f"✅ 路由导入成功: {xishen_jishen_router}")
    print(f"   路由路径: {[r.path for r in xishen_jishen_router.routes if hasattr(r, 'path')]}")
    
    # 检查main模块中的变量
    import importlib
    import server.main as main_module
    
    print(f"\n✅ XISHEN_JISHEN_ROUTER_AVAILABLE: {getattr(main_module, 'XISHEN_JISHEN_ROUTER_AVAILABLE', 'NOT_FOUND')}")
    print(f"✅ xishen_jishen_router in main: {getattr(main_module, 'xishen_jishen_router', 'NOT_FOUND')}")
    
    # 检查RouterManager
    router_manager = getattr(main_module, 'router_manager', None)
    if router_manager:
        print(f"\n✅ RouterManager存在")
        registered = router_manager.get_registered_routers()
        print(f"   已注册路由: {registered}")
        print(f"   xishen_jishen是否在已注册列表中: {'xishen_jishen' in registered}")
        
        # 检查路由信息
        if 'xishen_jishen' in router_manager.registered_routers:
            router_info = router_manager.registered_routers['xishen_jishen']
            print(f"\n✅ 路由信息存在:")
            print(f"   名称: {router_info.name}")
            print(f"   前缀: {router_info.prefix}")
            print(f"   标签: {router_info.tags}")
            print(f"   是否启用: {router_info.is_enabled()}")
            print(f"   是否已注册: {router_info._registered}")
            
            # 尝试获取路由对象
            router = router_info.get_router()
            print(f"   路由对象: {router}")
        else:
            print(f"\n❌ 路由信息不在registered_routers中")
    else:
        print(f"\n❌ RouterManager不存在")
        
except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()


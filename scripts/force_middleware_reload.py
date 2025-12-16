#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制重新加载认证中间件
通过热更新API触发中间件模块重新加载
"""

import requests
import sys
import time

BASE_URL = "http://localhost:8001"

def force_reload_middleware():
    """强制重新加载中间件"""
    print("🔄 尝试通过热更新重新加载中间件...")
    
    # 1. 检查热更新接口是否可用
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/hot-reload/check",
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ 热更新检查完成")
            result = response.json()
            print(f"   结果: {result.get('message', '未知')}")
        elif response.status_code == 401:
            print("❌ 热更新接口被认证中间件拦截（401）")
            print("   这说明中间件确实在拦截请求")
            return False
        else:
            print(f"⚠️  热更新接口返回: {response.status_code}")
    except Exception as e:
        print(f"❌ 热更新接口调用失败: {e}")
        return False
    
    # 2. 等待一下让热更新生效
    print("\n⏳ 等待热更新生效（3秒）...")
    time.sleep(3)
    
    # 3. 测试静态文件访问
    print("\n🧪 测试静态文件访问...")
    try:
        response = requests.get(f"{BASE_URL}/frontend/login.html", timeout=5)
        
        if response.status_code == 200:
            content = response.text[:100]
            if "<!DOCTYPE html>" in content:
                print("✅ 静态文件可以访问！中间件修复成功！")
                return True
            else:
                print(f"⚠️  返回内容异常: {content}")
                return False
        elif response.status_code == 401:
            print("❌ 静态文件仍被拦截（401）")
            print("   中间件代码可能未重新加载")
            print("\n📋 解决方案：")
            print("   中间件在应用启动时实例化，热更新无法替换已实例化的中间件")
            print("   必须重启服务器才能生效：")
            print("   1. 停止服务器（Ctrl+C）")
            print("   2. 重新启动: python3 server/start.py")
            return False
        else:
            print(f"⚠️  未知状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = force_reload_middleware()
    sys.exit(0 if success else 1)


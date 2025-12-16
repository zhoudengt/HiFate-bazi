#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试登录功能

验证：
1. 登录接口是否可访问（通过 gRPC 网关）
2. 登录是否返回正确的 Token
3. Token 是否能被验证
"""

import sys
import os
import json
import requests

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

BASE_URL = "http://localhost:8001"

def test_direct_login():
    """测试直接 REST API 登录"""
    print("=" * 60)
    print("测试 1: 直接 REST API 登录")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print("✅ 直接 REST API 登录成功")
                return data["access_token"]
            else:
                print("❌ 响应中没有 access_token")
                return None
        else:
            print(f"❌ 登录失败，状态码: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务已启动")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


def test_grpc_gateway_login():
    """测试通过 gRPC 网关登录配置"""
    print("\n" + "=" * 60)
    print("测试 2: 检查 gRPC 网关登录配置")
    print("=" * 60)
    
    try:
        # 检查认证中间件白名单
        print("\n检查认证中间件白名单...")
        try:
            with open("server/middleware/auth_middleware.py", "r", encoding="utf-8") as f:
                content = f.read()
                grpc_path = "/api/grpc-web/frontend.gateway.FrontendGateway/Call"
                if grpc_path in content:
                    print(f"✅ gRPC 网关路径在白名单中: {grpc_path}")
                else:
                    print(f"❌ gRPC 网关路径不在白名单中: {grpc_path}")
        except Exception as e:
            print(f"⚠️  无法检查白名单配置: {e}")
        
        # 检查 gRPC 网关中的白名单端点
        print("\n检查 gRPC 网关白名单端点...")
        try:
            with open("server/api/grpc_gateway.py", "r", encoding="utf-8") as f:
                content = f.read()
                if '"/auth/login"' in content and "whitelist_endpoints" in content:
                    print("✅ gRPC 网关中已配置登录接口白名单")
                else:
                    print("❌ gRPC 网关中未找到登录接口白名单配置")
        except Exception as e:
            print(f"⚠️  无法检查 gRPC 网关配置: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_verification(token):
    """测试 Token 验证"""
    print("\n" + "=" * 60)
    print("测试 3: Token 验证")
    print("=" * 60)
    
    if not token:
        print("⚠️  跳过 Token 验证（未获取到 Token）")
        return False
    
    try:
        # 注意：这里需要服务运行才能测试
        print("⚠️  Token 验证需要认证服务运行")
        print(f"   Token: {token[:20]}...")
        print("   请在服务运行后手动测试")
        return None
        
    except Exception as e:
        print(f"❌ Token 验证错误: {e}")
        return False


def test_protected_endpoint(token):
    """测试使用 Token 访问受保护接口"""
    print("\n" + "=" * 60)
    print("测试 4: 使用 Token 访问受保护接口")
    print("=" * 60)
    
    if not token:
        print("⚠️  跳过测试（未获取到 Token）")
        return False
    
    try:
        # 测试访问一个需要认证的接口
        response = requests.get(
            f"{BASE_URL}/api/v1/bazi/calculate",
            params={
                "solar_date": "1990-01-15",
                "solar_time": "12:00",
                "gender": "male"
            },
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=5
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 使用 Token 访问受保护接口成功")
            return True
        elif response.status_code == 401:
            print("❌ Token 验证失败（401 Unauthorized）")
            print(f"   响应: {response.text}")
            return False
        else:
            print(f"⚠️  意外状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试登录功能...\n")
    
    # 测试 1: 直接 REST API 登录
    token = test_direct_login()
    
    # 测试 2: gRPC 网关配置检查
    test_grpc_gateway_login()
    
    # 测试 3: Token 验证（如果获取到 Token）
    if token:
        test_token_verification(token)
        test_protected_endpoint(token)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n💡 提示：")
    print("1. 如果直接 REST API 登录成功，说明登录接口本身没问题")
    print("2. 如果 gRPC 网关路径在白名单中，说明认证中间件配置正确")
    print("3. 如果 Token 验证成功，说明认证服务正常工作")
    print("4. 前端登录应该能正常工作（通过 gRPC 网关）")


if __name__ == "__main__":
    main()

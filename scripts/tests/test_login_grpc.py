#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试登录功能（通过 gRPC 网关）
"""

import sys
import os
import requests
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_login_grpc(base_url="http://127.0.0.1:8001"):
    """
    测试通过 gRPC 网关登录
    """
    grpc_url = f"{base_url}/api/grpc-web/frontend.gateway.FrontendGateway/Call"
    
    # 构建 gRPC-Web 请求体（简化版，实际应该使用 protobuf 编码）
    # 这里我们直接测试 REST API 作为对比
    rest_url = f"{base_url}/api/v1/auth/login"
    
    print("=" * 80)
    print("登录功能测试")
    print("=" * 80)
    
    # 测试1: REST API（直接调用）
    print("\n1. 测试 REST API（直接调用）")
    print(f"   URL: {rest_url}")
    try:
        response = requests.post(
            rest_url,
            json={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 登录成功")
            print(f"   Token: {data.get('access_token', 'N/A')[:50]}...")
        else:
            print(f"   ❌ 登录失败: {response.text}")
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
    
    # 测试2: gRPC 网关（需要手动构建 gRPC-Web 请求）
    print("\n2. 测试 gRPC 网关")
    print(f"   URL: {grpc_url}")
    print("   ⚠️  注意：gRPC-Web 请求需要特殊的编码格式")
    print("   建议：使用浏览器测试前端登录页面")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    print("\n建议：")
    print("1. 打开浏览器访问: http://localhost:8001/frontend/login.html")
    print("2. 输入用户名: admin, 密码: admin123")
    print("3. 打开浏览器控制台（F12）查看详细日志")
    print("4. 检查 Network 标签中的 gRPC-Web 请求")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试登录功能")
    parser.add_argument("--url", default="http://127.0.0.1:8001", help="API基础URL")
    args = parser.parse_args()
    
    test_login_grpc(args.url)


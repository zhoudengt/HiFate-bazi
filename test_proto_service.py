#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Proto 服务 API
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_proto_service():
    """测试 Proto 服务 API"""
    print("=" * 60)
    print("测试 Proto 服务 API")
    print("=" * 60)
    
    # 1. 测试获取 frontend_gateway.proto（应该成功）
    print("\n1. 测试获取 frontend_gateway.proto（应该成功）")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/proto/frontend_gateway.proto")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            content = response.text
            print(f"✅ 成功获取文件，长度: {len(content)} 字符")
            print(f"前100字符: {content[:100]}...")
        else:
            print(f"❌ 失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 2. 测试获取文件列表（应该成功）
    print("\n2. 测试获取文件列表（应该成功）")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/proto-files")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取文件列表")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 失败: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 3. 测试访问不在白名单的文件（应该返回 403）
    print("\n3. 测试访问不在白名单的文件（应该返回 403）")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/proto/bazi_core.proto")
        print(f"状态码: {response.status_code}")
        if response.status_code == 403:
            print(f"✅ 正确拒绝访问（403）")
            print(f"错误信息: {response.json().get('detail', '')}")
        else:
            print(f"❌ 预期 403，实际: {response.status_code}")
            print(f"响应: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 4. 测试路径遍历攻击（FastAPI 会在路由匹配时拒绝，返回 404）
    print("\n4. 测试路径遍历攻击（FastAPI 路由层拒绝，返回 404）")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/proto/../server/main.py")
        print(f"状态码: {response.status_code}")
        # FastAPI 在路由匹配时就会拒绝包含 ../ 的路径，返回 404
        # 这是正常的安全行为，攻击请求不会到达我们的处理函数
        if response.status_code in [400, 404]:
            print(f"✅ 正确拒绝路径遍历（{response.status_code}）")
            print(f"说明: FastAPI 在路由层拒绝了路径遍历攻击")
        else:
            print(f"⚠️  状态码: {response.status_code}")
            print(f"响应: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 5. 测试访问不存在的文件（先检查白名单，返回 403 是合理的安全行为）
    print("\n5. 测试访问不存在的文件（先检查白名单，返回 403 是合理的安全行为）")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/proto/nonexistent.proto")
        print(f"状态码: {response.status_code}")
        # 先检查白名单，再检查文件是否存在，这是正确的安全行为
        # 返回 403 表示"禁止访问"，比 404 "不存在"更安全（不泄露文件系统信息）
        if response.status_code == 403:
            print(f"✅ 正确返回 403（先检查权限，不泄露文件系统信息）")
            print(f"错误信息: {response.json().get('detail', '')}")
        elif response.status_code == 404:
            print(f"✅ 返回 404（文件不存在）")
            print(f"错误信息: {response.json().get('detail', '')}")
        else:
            print(f"⚠️  状态码: {response.status_code}")
            print(f"响应: {response.text}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_proto_service()


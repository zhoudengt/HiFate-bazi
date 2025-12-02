#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试精选接口和限流功能（不依赖 jq）
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"  # 注意：服务器运行在 8001 端口

def test_login():
    """测试登录获取 token"""
    print("=" * 60)
    print("1. 测试登录接口")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/v1/auth/login"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(url, json=data, timeout=5)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            print(f"✓ 登录成功！")
            print(f"Token: {token[:50]}...")
            return token
        else:
            print(f"✗ 登录失败: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"✗ 无法连接到服务器 {BASE_URL}")
        print("请确保服务器已启动（运行 python server/start.py）")
        return None
    except Exception as e:
        print(f"✗ 登录异常: {e}")
        return None


def test_curated_api(token, request_num=1):
    """测试精选接口"""
    print(f"\n{'=' * 60}")
    print(f"2. 测试精选接口（请求 #{request_num}）")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/v1/bazi/rules/curated"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male",
        "k": 6,
        "use_nlg": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, json=data, headers=headers, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.2f}秒")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 请求成功！")
            print(f"精选规则数量: {result.get('rule_count', 0)}")
            curated_rules = result.get('curated_rules', [])
            if curated_rules:
                print(f"第一条规则: {curated_rules[0].get('rule_code', 'N/A')}")
            return True
        elif response.status_code == 429:
            print(f"⚠ 触发限流: {response.json().get('detail', '请求过于频繁')}")
            return "rate_limited"
        else:
            print(f"✗ 请求失败: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 请求异常: {e}")
        return False


def test_rate_limit(token):
    """测试限流功能（快速发送31次请求）"""
    print(f"\n{'=' * 60}")
    print("3. 测试限流功能（快速发送31次请求）")
    print("=" * 60)
    
    success_count = 0
    rate_limited_count = 0
    error_count = 0
    
    print("开始发送请求...")
    for i in range(1, 32):
        result = test_curated_api(token, request_num=i)
        if result is True:
            success_count += 1
        elif result == "rate_limited":
            rate_limited_count += 1
            print(f"⚠ 第 {i} 次请求被限流")
        else:
            error_count += 1
        
        # 稍微延迟，避免太快
        time.sleep(0.1)
    
    print(f"\n{'=' * 60}")
    print("限流测试结果:")
    print(f"  成功: {success_count} 次")
    print(f"  被限流: {rate_limited_count} 次")
    print(f"  错误: {error_count} 次")
    print("=" * 60)
    
    if rate_limited_count > 0:
        print("✓ 限流功能正常工作！")
    else:
        print("⚠ 未触发限流（可能 slowapi 未安装或配置问题）")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("精选接口和限流功能测试")
    print("=" * 60)
    
    # 1. 登录
    token = test_login()
    if not token:
        print("\n✗ 无法继续测试（登录失败）")
        return
    
    # 2. 测试正常请求
    test_curated_api(token)
    
    # 3. 测试限流（可选，取消注释以测试）
    test_rate_limit(token)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示：")
    print("- 如果要测试限流，取消注释 test_rate_limit(token) 行")
    print("- 服务器运行在端口 8001（不是 8000）")
    print("- 如果连接失败，请确保服务器已启动：python server/start.py")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付功能测试脚本
"""

import sys
import os
import requests
import json
from pathlib import Path

# 添加项目根目录到路径（向上两级：tests/features -> 项目根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

def test_payment_api():
    """测试支付API"""
    base_url = "http://127.0.0.1:8001/api/v1"
    
    print("=" * 60)
    print("支付功能测试")
    print("=" * 60)
    
    # 1. 检查主服务是否运行
    print("\n1. 检查主服务状态...")
    try:
        response = requests.get(f"{base_url.replace('/api/v1', '')}/healthz", timeout=5)
        if response.status_code == 200:
            print("   ✓ 主服务运行正常")
        else:
            print(f"   ✗ 主服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ✗ 主服务未运行，请先启动服务: python server/start.py")
        return False
    except Exception as e:
        print(f"   ✗ 检查失败: {e}")
        return False
    
    # 2. 检查支付路由是否注册
    print("\n2. 检查支付路由...")
    try:
        response = requests.get(f"{base_url.replace('/api/v1', '')}/docs", timeout=5)
        if response.status_code == 200:
            print("   ✓ API文档页面可访问")
            # 检查支付路由
            if "/payment/create-session" in response.text:
                print("   ✓ 支付路由已注册")
            else:
                print("   ⚠ 支付路由可能未注册，但继续测试...")
        else:
            print(f"   ⚠ API文档页面不可访问: {response.status_code}")
    except Exception as e:
        print(f"   ⚠ 无法检查API文档: {e}")
    
    # 3. 检查Stripe库
    print("\n3. 检查Stripe库...")
    try:
        import stripe
        print(f"   ✓ Stripe库已安装 (版本: {stripe.__version__})")
    except ImportError:
        print("   ✗ Stripe库未安装")
        print("   请运行: pip install stripe>=7.0.0")
        return False
    
    # 4. 检查Stripe密钥配置
    print("\n4. 检查Stripe密钥配置...")
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if stripe_key:
        masked_key = stripe_key[:20] + "..." if len(stripe_key) > 20 else stripe_key
        print(f"   ✓ STRIPE_SECRET_KEY已配置: {masked_key}")
        if stripe_key.startswith("sk_test_"):
            print("   ℹ 使用测试密钥 (sk_test_...)")
        elif stripe_key.startswith("sk_live_"):
            print("   ⚠ 使用生产密钥 (sk_live_...)")
        else:
            print("   ✗ 密钥格式不正确")
            return False
    else:
        print("   ✗ STRIPE_SECRET_KEY未配置")
        print("   请在.env文件中设置: STRIPE_SECRET_KEY=sk_test_...")
        print("   或在环境变量中设置")
        return False
    
    # 5. 测试创建支付会话
    print("\n5. 测试创建支付会话...")
    test_data = {
        "amount": "19.90",
        "currency": "USD",
        "product_name": "测试产品-月订阅会员",
        "customer_email": "test@example.com",
        "metadata": {
            "source": "test_script",
            "test": "true"
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/payment/create-session",
            json=test_data,
            timeout=10
        )
        
        print(f"   请求URL: {base_url}/payment/create-session")
        print(f"   请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
        print(f"   响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("   ✓ 支付会话创建成功!")
            print(f"   Session ID: {result.get('session_id', 'N/A')}")
            print(f"   Checkout URL: {result.get('checkout_url', 'N/A')[:80]}...")
            print(f"   状态: {result.get('status', 'N/A')}")
            return True
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"   ✗ 创建失败: {error_data}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ✗ 无法连接到服务器，请检查服务是否运行")
        return False
    except Exception as e:
        print(f"   ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

def test_payment_verify():
    """测试支付验证（需要提供session_id）"""
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        base_url = "http://127.0.0.1:8001/api/v1"
        
        print(f"\n验证支付会话: {session_id}")
        try:
            response = requests.post(
                f"{base_url}/payment/verify",
                json={"session_id": session_id},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 验证成功:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"✗ 验证失败: {response.text}")
        except Exception as e:
            print(f"✗ 验证失败: {e}")

if __name__ == "__main__":
    success = test_payment_api()
    
    if len(sys.argv) > 1:
        test_payment_verify()
    
    sys.exit(0 if success else 1)


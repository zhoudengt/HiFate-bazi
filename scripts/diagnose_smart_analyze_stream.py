#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 smart-analyze-stream 接口问题
"""
import sys
import os
import urllib.parse
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_endpoint_registration():
    """检查端点是否在 gRPC 网关中注册"""
    print("=" * 80)
    print("1. 检查 gRPC-Web 端点注册情况")
    print("=" * 80)
    
    try:
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        
        endpoint = "/smart-fortune/smart-analyze-stream"
        if endpoint in SUPPORTED_ENDPOINTS:
            print(f"✅ 端点已注册: {endpoint}")
            print(f"   处理器: {SUPPORTED_ENDPOINTS[endpoint]}")
        else:
            print(f"❌ 端点未注册: {endpoint}")
            print(f"   已注册的端点数量: {len(SUPPORTED_ENDPOINTS)}")
            print(f"   已注册的端点列表（前20个）:")
            for ep in list(SUPPORTED_ENDPOINTS.keys())[:20]:
                print(f"     - {ep}")
            
            # 检查是否有类似的端点
            similar = [ep for ep in SUPPORTED_ENDPOINTS.keys() if 'smart' in ep.lower() or 'fortune' in ep.lower()]
            if similar:
                print(f"\n   类似的端点:")
                for ep in similar:
                    print(f"     - {ep}")
    except Exception as e:
        print(f"❌ 检查端点注册失败: {e}")
        import traceback
        traceback.print_exc()

def check_router_registration():
    """检查 FastAPI 路由注册情况"""
    print("\n" + "=" * 80)
    print("2. 检查 FastAPI 路由注册情况")
    print("=" * 80)
    
    try:
        from server.main import app
        
        # 获取所有路由
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append({
                    'path': route.path,
                    'methods': list(route.methods) if route.methods else []
                })
        
        target_path = "/api/v1/smart-fortune/smart-analyze-stream"
        found = False
        
        for route in routes:
            if target_path in route['path'] or route['path'].endswith('smart-analyze-stream'):
                found = True
                print(f"✅ 找到路由: {route['path']}")
                print(f"   方法: {route['methods']}")
                break
        
        if not found:
            print(f"❌ 未找到路由: {target_path}")
            print(f"   相关的路由:")
            smart_routes = [r for r in routes if 'smart' in r['path'].lower() or 'fortune' in r['path'].lower()]
            for route in smart_routes[:10]:
                print(f"     - {route['path']} ({route['methods']})")
                
    except Exception as e:
        print(f"❌ 检查路由注册失败: {e}")
        import traceback
        traceback.print_exc()

def generate_curl_commands():
    """生成正确的 curl 命令"""
    print("\n" + "=" * 80)
    print("3. 生成正确的 curl 命令")
    print("=" * 80)
    
    # 场景1：点击选择项
    params_scenario1 = {
        'category': '事业财富',
        'year': 1990,
        'month': 5,
        'day': 15,
        'hour': 14,
        'gender': 'male',
        'user_id': 'test_user_001'
    }
    
    # 场景2：点击预设问题
    params_scenario2 = {
        'category': '事业财富',
        'question': '我今年的事业运势如何？',
        'user_id': 'test_user_001'
    }
    
    # 默认场景
    params_default = {
        'question': '我今年的事业运势如何？',
        'year': 1990,
        'month': 5,
        'day': 15,
        'hour': 14,
        'gender': 'male',
        'user_id': 'test_user_001'
    }
    
    base_urls = {
        '生产环境': 'http://8.210.52.217:8001',
        '本地环境': 'http://localhost:8001'
    }
    
    print("\n【场景1：点击选择项】")
    for env_name, base_url in base_urls.items():
        print(f"\n{env_name}:")
        query_string = urllib.parse.urlencode(params_scenario1, doseq=True, encoding='utf-8')
        url = f"{base_url}/api/v1/smart-fortune/smart-analyze-stream?{query_string}"
        print(f"curl -N -v '{url}'")
    
    print("\n【场景2：点击预设问题】")
    for env_name, base_url in base_urls.items():
        print(f"\n{env_name}:")
        query_string = urllib.parse.urlencode(params_scenario2, doseq=True, encoding='utf-8')
        url = f"{base_url}/api/v1/smart-fortune/smart-analyze-stream?{query_string}"
        print(f"curl -N -v '{url}'")
    
    print("\n【默认场景】")
    for env_name, base_url in base_urls.items():
        print(f"\n{env_name}:")
        query_string = urllib.parse.urlencode(params_default, doseq=True, encoding='utf-8')
        url = f"{base_url}/api/v1/smart-fortune/smart-analyze-stream?{query_string}"
        print(f"curl -N -v '{url}'")
    
    print("\n【gRPC-Web 网关调用（场景1）】")
    for env_name, base_url in base_urls.items():
        print(f"\n{env_name}:")
        payload = {
            "endpoint": "/smart-fortune/smart-analyze-stream",
            "payload": params_scenario1
        }
        print(f"curl -X POST '{base_url}/api/v1/grpc-web/frontend.gateway.FrontendGateway/Call' \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{json.dumps(payload, ensure_ascii=False)}'")

def check_server_health():
    """检查服务器健康状态"""
    print("\n" + "=" * 80)
    print("4. 检查服务器健康状态")
    print("=" * 80)
    
    import requests
    
    servers = {
        '生产环境': 'http://8.210.52.217:8001',
        '本地环境': 'http://localhost:8001'
    }
    
    for env_name, base_url in servers.items():
        print(f"\n{env_name} ({base_url}):")
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ 服务器运行正常 (HTTP {response.status_code})")
                try:
                    data = response.json()
                    print(f"     响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
                except:
                    print(f"     响应: {response.text[:200]}")
            else:
                print(f"  ⚠️  服务器响应异常 (HTTP {response.status_code})")
                print(f"     响应: {response.text[:200]}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ 无法连接到服务器（服务器可能未运行）")
        except requests.exceptions.Timeout:
            print(f"  ❌ 连接超时")
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")

if __name__ == "__main__":
    print("智能运势流式接口诊断工具")
    print("=" * 80)
    
    # 检查服务器健康状态
    check_server_health()
    
    # 检查端点注册
    check_endpoint_registration()
    
    # 检查路由注册
    check_router_registration()
    
    # 生成 curl 命令
    generate_curl_commands()
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

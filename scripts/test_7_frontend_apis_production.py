#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试7个前端接口在生产环境是否可用（验证7个标准参数）

测试接口：
- /bazi/interface (基本信息)
- /bazi/pan/display (基本排盘)
- /bazi/fortune/display (专业排盘-大运流年流月)
- /daily-fortune-calendar/query (八字命理-每日运势)
- /bazi/wuxing-proportion (八字命理-五行占比)
- /bazi/rizhu-liujiazi (八字命理-日元-六十甲子)
- /bazi/xishen-jishen (八字命理-喜神忌神)
"""

import sys
import os
import json
import requests
from typing import Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 导入测试工具函数
from scripts.test_frontend_gateway import (
    test_gateway_endpoint,
    API_BASE_URL
)

# 生产环境配置
NODE1_URL = "http://8.210.52.217:8001"
NODE2_URL = "http://47.243.160.43:8001"

# 标准测试参数（7个标准参数）
STANDARD_PARAMS = {
    "solar_date": "1990-01-15",
    "solar_time": "12:00",
    "gender": "male",
    "calendar_type": "solar",
    "location": "北京",
    "latitude": 39.90,
    "longitude": 116.40
}

# 7个前端接口列表
FRONTEND_APIS = [
    ("/bazi/interface", "基本信息"),
    ("/bazi/pan/display", "基本排盘"),
    ("/bazi/fortune/display", "专业排盘-大运流年流月"),
    ("/daily-fortune-calendar/query", "八字命理-每日运势"),
    ("/bazi/wuxing-proportion", "八字命理-五行占比"),
    ("/bazi/rizhu-liujiazi", "八字命理-日元-六十甲子"),
    ("/bazi/xishen-jishen", "八字命理-喜神忌神"),
]


def test_api_direct(node_url: str, endpoint: str, api_name: str) -> Dict[str, Any]:
    """
    直接测试 REST API（不通过 gRPC 网关）
    
    Args:
        node_url: 节点 URL
        endpoint: 端点路径
        api_name: API 名称
        
    Returns:
        Dict: 测试结果
    """
    url = f"{node_url}/api/v1{endpoint}"
    
    try:
        response = requests.post(
            url,
            json=STANDARD_PARAMS,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "error": None,
            "data": None
        }
        
        if response.status_code == 200:
            try:
                result["data"] = response.json()
            except json.JSONDecodeError:
                result["data"] = response.text[:200]
        else:
            result["error"] = response.text[:200]
        
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status_code": 0,
            "error": str(e),
            "data": None
        }


def test_api_via_gateway(node_url: str, endpoint: str, api_name: str) -> Dict[str, Any]:
    """
    通过 gRPC 网关测试 API
    
    Args:
        node_url: 节点 URL
        endpoint: 端点路径
        api_name: API 名称
        
    Returns:
        Dict: 测试结果
    """
    # 临时修改 API_BASE_URL
    import scripts.test_frontend_gateway as test_module
    original_url = test_module.API_BASE_URL
    test_module.API_BASE_URL = node_url
    
    try:
        result = test_gateway_endpoint(endpoint, STANDARD_PARAMS)
        return {
            "success": result.get('success', False),
            "status_code": result.get('status_code', 0),
            "error": result.get('error'),
            "data": result.get('data')
        }
    finally:
        test_module.API_BASE_URL = original_url


def test_single_api(endpoint: str, api_name: str) -> Dict[str, Any]:
    """
    测试单个接口（Node1 和 Node2）
    
    Args:
        endpoint: 端点路径
        api_name: API 名称
        
    Returns:
        Dict: 测试结果
    """
    print(f"\n{'='*60}")
    print(f"测试: {api_name} ({endpoint})")
    print(f"{'='*60}")
    
    results = {
        "api_name": api_name,
        "endpoint": endpoint,
        "node1": {},
        "node2": {}
    }
    
    # 测试 Node1（直接 REST API）
    print(f"\n📡 Node1 (8.210.52.217) - 直接 REST API:")
    node1_direct = test_api_direct(NODE1_URL, endpoint, api_name)
    results["node1"]["direct"] = node1_direct
    
    if node1_direct["success"]:
        print(f"   ✅ 成功 (HTTP {node1_direct['status_code']})")
        if node1_direct.get("data"):
            data = node1_direct["data"]
            if isinstance(data, dict):
                print(f"   📊 数据键: {list(data.keys())[:5]}...")
    else:
        print(f"   ❌ 失败: {node1_direct.get('error', '未知错误')}")
    
    # 测试 Node1（通过 gRPC 网关）
    print(f"\n📡 Node1 (8.210.52.217) - gRPC 网关:")
    node1_gateway = test_api_via_gateway(NODE1_URL, endpoint, api_name)
    results["node1"]["gateway"] = node1_gateway
    
    if node1_gateway["success"]:
        print(f"   ✅ 成功 (HTTP {node1_gateway['status_code']})")
    else:
        print(f"   ❌ 失败: {node1_gateway.get('error', '未知错误')}")
    
    # 测试 Node2（直接 REST API）
    print(f"\n📡 Node2 (47.243.160.43) - 直接 REST API:")
    node2_direct = test_api_direct(NODE2_URL, endpoint, api_name)
    results["node2"]["direct"] = node2_direct
    
    if node2_direct["success"]:
        print(f"   ✅ 成功 (HTTP {node2_direct['status_code']})")
        if node2_direct.get("data"):
            data = node2_direct["data"]
            if isinstance(data, dict):
                print(f"   📊 数据键: {list(data.keys())[:5]}...")
    else:
        print(f"   ❌ 失败: {node2_direct.get('error', '未知错误')}")
    
    # 测试 Node2（通过 gRPC 网关）
    print(f"\n📡 Node2 (47.243.160.43) - gRPC 网关:")
    node2_gateway = test_api_via_gateway(NODE2_URL, endpoint, api_name)
    results["node2"]["gateway"] = node2_gateway
    
    if node2_gateway["success"]:
        print(f"   ✅ 成功 (HTTP {node2_gateway['status_code']})")
    else:
        print(f"   ❌ 失败: {node2_gateway.get('error', '未知错误')}")
    
    # 判断整体是否成功
    all_success = (
        node1_direct["success"] and
        node1_gateway["success"] and
        node2_direct["success"] and
        node2_gateway["success"]
    )
    
    results["overall_success"] = all_success
    return results


def verify_frontend_gateway_proto_sync() -> bool:
    """
    验证 frontend_gateway.proto 在双机是否同步
    
    Returns:
        bool: 是否同步
    """
    print(f"\n{'='*60}")
    print("验证 frontend_gateway.proto 双机同步")
    print(f"{'='*60}")
    
    try:
        # 检查 Node1
        import subprocess
        project_dir = "/opt/HiFate-bazi"
        proto_file_path = os.path.join(project_dir, "proto", "frontend_gateway.proto")
        
        node1_hash = subprocess.check_output(
            f'sshpass -p "{os.getenv("SSH_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))}" '
            f'ssh -o StrictHostKeyChecking=no root@8.210.52.217 '
            f'"md5sum {proto_file_path} | cut -d\\" \\" -f1"',
            shell=True,
            text=True
        ).strip()
        
        # 检查 Node2
        node2_hash = subprocess.check_output(
            f'sshpass -p "{os.getenv("SSH_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))}" '
            f'ssh -o StrictHostKeyChecking=no root@47.243.160.43 '
            f'"md5sum {proto_file_path} | cut -d\\" \\" -f1"',
            shell=True,
            text=True
        ).strip()
        
        # 检查本地（使用动态路径）
        local_proto_path = os.path.join(PROJECT_ROOT, "proto", "frontend_gateway.proto")
        local_hash = subprocess.check_output(
            f'md5 -q "{local_proto_path}"',
            shell=True,
            text=True
        ).strip()
        
        print(f"本地 MD5: {local_hash}")
        print(f"Node1 MD5: {node1_hash}")
        print(f"Node2 MD5: {node2_hash}")
        
        if node1_hash == node2_hash == local_hash:
            print("✅ frontend_gateway.proto 三处完全一致")
            return True
        else:
            print("❌ frontend_gateway.proto 不一致")
            if node1_hash != local_hash:
                print("   ⚠️  Node1 与本地不一致")
            if node2_hash != local_hash:
                print("   ⚠️  Node2 与本地不一致")
            if node1_hash != node2_hash:
                print("   ⚠️  Node1 与 Node2 不一致")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("7个前端接口生产环境可用性测试")
    print("="*60)
    print(f"Node1: {NODE1_URL}")
    print(f"Node2: {NODE2_URL}")
    
    # 检查服务是否运行
    for node_name, node_url in [("Node1", NODE1_URL), ("Node2", NODE2_URL)]:
        try:
            response = requests.get(f"{node_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {node_name} 服务正在运行")
            else:
                print(f"⚠️  {node_name} 服务响应异常: HTTP {response.status_code}")
                return 1
        except requests.exceptions.RequestException as e:
            print(f"❌ {node_name} 服务未运行或无法连接: {e}")
            return 1
    
    # 验证 frontend_gateway.proto 同步
    proto_sync = verify_frontend_gateway_proto_sync()
    
    # 测试7个前端接口
    results = []
    for endpoint, api_name in FRONTEND_APIS:
        result = test_single_api(endpoint, api_name)
        results.append(result)
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for result in results:
        api_name = result["api_name"]
        overall_success = result.get("overall_success", False)
        
        status = "✅ 通过" if overall_success else "❌ 失败"
        print(f"\n{api_name}: {status}")
        
        # 详细状态
        node1_direct = result["node1"]["direct"]["success"]
        node1_gateway = result["node1"]["gateway"]["success"]
        node2_direct = result["node2"]["direct"]["success"]
        node2_gateway = result["node2"]["gateway"]["success"]
        
        print(f"  Node1 REST: {'✅' if node1_direct else '❌'}")
        print(f"  Node1 gRPC: {'✅' if node1_gateway else '❌'}")
        print(f"  Node2 REST: {'✅' if node2_direct else '❌'}")
        print(f"  Node2 gRPC: {'✅' if node2_gateway else '❌'}")
        
        if overall_success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"总计: {passed} 个通过, {failed} 个失败")
    print(f"frontend_gateway.proto 同步: {'✅ 是' if proto_sync else '❌ 否'}")
    print(f"{'='*60}")
    
    if failed == 0 and proto_sync:
        print("\n🎉 所有测试通过！7个前端接口在生产环境可用，frontend_gateway.proto 已同步。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败或 proto 未同步，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())


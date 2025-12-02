#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端功能测试脚本 - Python 版本（支持 gRPC-Web 格式）
"""

import json
import sys
import requests
from typing import Dict, Any, Tuple

BASE_URL = "http://localhost:8001"
GRPC_WEB_URL = f"{BASE_URL}/api/grpc-web/frontend.gateway.FrontendGateway/Call"

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# 测试计数器
passed = 0
failed = 0
skipped = 0
test_results = []


def encode_varint(value: int) -> bytes:
    """编码 varint"""
    chunks = []
    current = value & 0xFFFFFFFF
    while current >= 0x80:
        chunks.append((current & 0x7F) | 0x80)
        current >>= 7
    chunks.append(current)
    return bytes(chunks)


def encode_string_field(field_number: int, value: str) -> bytes:
    """编码字符串字段"""
    header = (field_number << 3) | 2  # wire_type = 2 (length-delimited)
    value_bytes = value.encode('utf-8')
    length_bytes = encode_varint(len(value_bytes))
    return bytes([header]) + length_bytes + value_bytes


def build_grpc_web_body(endpoint: str, payload: Dict[str, Any], token: str = "") -> bytes:
    """构建 gRPC-Web 请求体"""
    payload_json = json.dumps(payload, ensure_ascii=False)
    
    # 编码 protobuf 消息
    message = b""
    if endpoint:
        message += encode_string_field(1, endpoint)
    if payload_json:
        message += encode_string_field(2, payload_json)
    if token:
        message += encode_string_field(3, token)
    
    # 包装 gRPC-Web 帧
    flag = 0x00
    length = len(message)
    frame = bytes([flag]) + length.to_bytes(4, byteorder='big') + message
    
    return frame


def test_endpoint(name: str, endpoint: str, payload: Dict[str, Any], method: str = "POST") -> bool:
    """测试 REST API 端点"""
    global passed, failed, test_results
    
    print(f"测试: {name} ... ", end="", flush=True)
    
    try:
        if method == "POST":
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        else:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                timeout=10
            )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "error" in data:
                    print(f"{Colors.RED}失败{Colors.NC} (返回错误)")
                    print(f"  响应: {str(data)[:200]}")
                    failed += 1
                    test_results.append(f"❌ {name}")
                    return False
                else:
                    print(f"{Colors.GREEN}通过{Colors.NC}")
                    passed += 1
                    test_results.append(f"✅ {name}")
                    return True
            except:
                print(f"{Colors.GREEN}通过{Colors.NC}")
                passed += 1
                test_results.append(f"✅ {name}")
                return True
        else:
            print(f"{Colors.RED}失败{Colors.NC} (HTTP {response.status_code})")
            print(f"  响应: {response.text[:200]}")
            failed += 1
            test_results.append(f"❌ {name} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"{Colors.RED}失败{Colors.NC} (异常: {str(e)[:100]})")
        failed += 1
        test_results.append(f"❌ {name} (异常)")
        return False


def test_grpc_web(name: str, endpoint: str, payload: Dict[str, Any], token: str = "") -> bool:
    """测试 gRPC-Web 端点"""
    global passed, failed, test_results
    
    print(f"测试: {name} (gRPC-Web) ... ", end="", flush=True)
    
    try:
        body = build_grpc_web_body(endpoint, payload, token)
        
        headers = {
            "Content-Type": "application/grpc-web+proto",
            "X-Grpc-Web": "1",
            "X-User-Agent": "grpc-web-js/0.1"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.post(
            GRPC_WEB_URL,
            data=body,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            # 检查 gRPC 状态
            grpc_status = response.headers.get("grpc-status", "0")
            if grpc_status != "0":
                print(f"{Colors.RED}失败{Colors.NC} (gRPC status: {grpc_status})")
                failed += 1
                test_results.append(f"❌ {name} (gRPC {grpc_status})")
                return False
            
            # 尝试解析响应
            try:
                # gRPC-Web 响应是二进制格式，需要解析
                # 检查响应内容：如果包含 "success=False" 或明确的错误信息，才认为是失败
                content_lower = response.content.lower()
                # 检查是否有明确的错误标记
                if b"success=false" in content_lower or (b'"error"' in content_lower and b"success=true" not in content_lower):
                    print(f"{Colors.RED}失败{Colors.NC} (返回错误)")
                    print(f"  响应: {response.content[:200]}")
                    failed += 1
                    test_results.append(f"❌ {name}")
                    return False
                else:
                    # 如果包含 success=True 或没有明确的错误，认为成功
                    print(f"{Colors.GREEN}通过{Colors.NC}")
                    passed += 1
                    test_results.append(f"✅ {name}")
                    return True
            except:
                print(f"{Colors.GREEN}通过{Colors.NC}")
                passed += 1
                test_results.append(f"✅ {name}")
                return True
        else:
            print(f"{Colors.RED}失败{Colors.NC} (HTTP {response.status_code})")
            print(f"  响应: {response.text[:200]}")
            failed += 1
            test_results.append(f"❌ {name} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"{Colors.RED}失败{Colors.NC} (异常: {str(e)[:100]})")
        failed += 1
        test_results.append(f"❌ {name} (异常)")
        return False


def main():
    global passed, failed, skipped, test_results
    
    print("=" * 50)
    print("HiFate-bazi 端到端功能测试")
    print("=" * 50)
    print()
    
    # 检查服务状态
    print(f"{Colors.BLUE}检查服务状态...{Colors.NC}")
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"{Colors.GREEN}服务运行正常{Colors.NC}")
    except:
        print(f"{Colors.RED}错误: 服务未运行在 {BASE_URL}{Colors.NC}")
        print("请先启动服务: python server/start.py")
        sys.exit(1)
    print()
    
    # 1. 测试登录功能
    print(f"{Colors.BLUE}1. 测试登录功能{Colors.NC}")
    print("-" * 50)
    test_endpoint(
        "REST API 登录",
        "/api/v1/auth/login",
        {"username": "admin", "password": "admin123"}
    )
    
    # 获取 token
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token", "")
            if token:
                print(f"{Colors.GREEN}Token 获取成功{Colors.NC}")
                print()
                
                # 2. 测试 gRPC-Web 登录
                print(f"{Colors.BLUE}2. 测试 gRPC-Web 登录{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "gRPC-Web 登录",
                    "/auth/login",
                    {"username": "admin", "password": "admin123"}
                )
                
                print()
                # 3. 测试八字计算
                print(f"{Colors.BLUE}3. 测试八字计算{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "八字盘显示",
                    "/bazi/pan/display",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                test_grpc_web(
                    "旺衰分析",
                    "/bazi/wangshuai",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                
                print()
                # 4. 测试公式分析
                print(f"{Colors.BLUE}4. 测试公式分析{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "公式分析（全部类型）",
                    "/bazi/formula-analysis",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                test_grpc_web(
                    "公式分析（财富）",
                    "/bazi/formula-analysis",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male", "rule_types": ["wealth"]},
                    token
                )
                
                print()
                # 5. 测试运势功能
                print(f"{Colors.BLUE}5. 测试运势功能{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "今日运势",
                    "/bazi/daily-fortune",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                test_grpc_web(
                    "当月运势",
                    "/bazi/monthly-fortune",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                test_grpc_web(
                    "大运流年",
                    "/bazi/fortune/display",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                test_grpc_web(
                    "大运显示",
                    "/bazi/dayun/display",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                test_grpc_web(
                    "流年显示",
                    "/bazi/liunian/display",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
                
                print()
                # 6. 测试易卦功能
                print(f"{Colors.BLUE}6. 测试易卦功能{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "易卦占卜",
                    "/bazi/yigua/divinate",
                    {"question": "测试问题"},
                    token
                )
                
                print()
                # 7. 测试支付功能（仅测试接口可用性）
                print(f"{Colors.BLUE}7. 测试支付接口（可用性）{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "支付提供商列表",
                    "/payment/providers",
                    {},
                    token
                )
                
                print()
                # 8. 测试智能分析
                print(f"{Colors.BLUE}8. 测试智能分析{Colors.NC}")
                print("-" * 50)
                test_grpc_web(
                    "智能运势分析",
                    "/smart-analyze",
                    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
                    token
                )
            else:
                print(f"{Colors.RED}无法获取 token，跳过需要认证的测试{Colors.NC}")
                skipped += 5
        else:
            print(f"{Colors.RED}登录失败，跳过需要认证的测试{Colors.NC}")
            skipped += 5
    except Exception as e:
        print(f"{Colors.RED}无法获取 token: {e}，跳过需要认证的测试{Colors.NC}")
        skipped += 5
    
    print()
    print("=" * 50)
    print(f"{Colors.BLUE}测试结果汇总{Colors.NC}")
    print("=" * 50)
    for result in test_results:
        print(result)
    print()
    print("统计:")
    print(f"  {Colors.GREEN}通过: {passed}{Colors.NC}")
    print(f"  {Colors.RED}失败: {failed}{Colors.NC}")
    if skipped > 0:
        print(f"  {Colors.YELLOW}跳过: {skipped}{Colors.NC}")
    print("=" * 50)
    
    if failed == 0:
        print(f"{Colors.GREEN}所有测试通过！{Colors.NC}")
        sys.exit(0)
    else:
        print(f"{Colors.RED}有 {failed} 个测试失败{Colors.NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()


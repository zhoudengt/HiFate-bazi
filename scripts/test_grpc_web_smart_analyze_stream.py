#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 smart-analyze-stream 接口（通过 gRPC-Web 网关）
完整版本，可直接在生产环境执行
"""
import json
import struct
import sys
import requests
from typing import Dict, Any

def encode_varint(value: int) -> bytes:
    """编码 varint"""
    result = bytearray()
    while value >= 0x80:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)

def encode_string_field(field_number: int, value: str) -> bytes:
    """编码字符串字段"""
    value_bytes = value.encode('utf-8')
    header = (field_number << 3) | 2
    result = bytearray()
    result.extend(encode_varint(header))
    result.extend(encode_varint(len(value_bytes)))
    result.extend(value_bytes)
    return bytes(result)

def encode_frontend_request(endpoint: str, payload: Dict[str, Any]) -> bytes:
    """编码 FrontendJsonRequest"""
    payload_json = json.dumps(payload, ensure_ascii=False)
    parts = []
    if endpoint:
        parts.append(encode_string_field(1, endpoint))
    if payload_json:
        parts.append(encode_string_field(2, payload_json))
    result = bytearray()
    for part in parts:
        result.extend(part)
    return bytes(result)

def wrap_grpc_web_frame(flag: int, message: bytes) -> bytes:
    """包装 gRPC-Web 帧"""
    length = len(message)
    frame = bytearray()
    frame.append(flag)
    frame.extend(struct.pack('>I', length))
    frame.extend(message)
    return bytes(frame)

def build_grpc_web_request(endpoint: str, payload: Dict[str, Any]) -> bytes:
    """构建完整的 gRPC-Web 请求体"""
    message = encode_frontend_request(endpoint, payload)
    return wrap_grpc_web_frame(0x00, message)

def test_scenario_1(base_url: str):
    """场景1：点击选择项"""
    print("=" * 80)
    print("场景1：点击选择项（需要生辰信息）")
    print("=" * 80)
    endpoint = "/smart-fortune/smart-analyze-stream"
    payload = {
        "category": "事业财富",
        "year": 1990,
        "month": 5,
        "day": 15,
        "hour": 14,
        "gender": "male",
        "user_id": "test_user_001"
    }
    print(f"端点: {endpoint}")
    print(f"载荷: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    request_body = build_grpc_web_request(endpoint, payload)
    url = f"{base_url}/api/grpc-web/frontend.gateway.FrontendGateway/Call"
    headers = {
        "Content-Type": "application/grpc-web+proto",
        "X-Grpc-Web": "1",
        "X-User-Agent": "grpc-web-python/0.1"
    }
    print(f"请求 URL: {url}")
    print(f"请求体长度: {len(request_body)} 字节")
    print("发送请求中...（可能需要较长时间，流式接口会收集所有数据后返回）")
    print()
    try:
        response = requests.post(url, data=request_body, headers=headers, timeout=300)
        print(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            body = response.content
            print(f"响应体长度: {len(body)} 字节")
            try:
                result = response.json()
                print("响应内容（JSON）:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except:
                body_str = body.decode('utf-8', errors='ignore')
                print("响应内容（文本，前1000字符）:")
                print(body_str[:1000])
        else:
            print(f"请求失败: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
    except requests.exceptions.Timeout:
        print("❌ 请求超时（300秒），流式接口可能需要更长时间")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")

def test_scenario_2(base_url: str):
    """场景2：点击预设问题"""
    print("\n" + "=" * 80)
    print("场景2：点击预设问题（从会话缓存获取生辰信息）")
    print("=" * 80)
    endpoint = "/smart-fortune/smart-analyze-stream"
    payload = {
        "category": "事业财富",
        "question": "我今年的事业运势如何？",
        "user_id": "test_user_001"
    }
    print(f"端点: {endpoint}")
    print(f"载荷: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    request_body = build_grpc_web_request(endpoint, payload)
    url = f"{base_url}/api/grpc-web/frontend.gateway.FrontendGateway/Call"
    headers = {
        "Content-Type": "application/grpc-web+proto",
        "X-Grpc-Web": "1",
        "X-User-Agent": "grpc-web-python/0.1"
    }
    print(f"请求 URL: {url}")
    print(f"请求体长度: {len(request_body)} 字节")
    print("发送请求中...（可能需要较长时间，流式接口会收集所有数据后返回）")
    print()
    try:
        response = requests.post(url, data=request_body, headers=headers, timeout=300)
        print(f"响应状态码: {response.status_code}")
        if response.status_code == 200:
            body = response.content
            print(f"响应体长度: {len(body)} 字节")
            try:
                result = response.json()
                print("响应内容（JSON）:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except:
                body_str = body.decode('utf-8', errors='ignore')
                print("响应内容（文本，前1000字符）:")
                print(body_str[:1000])
        else:
            print(f"请求失败: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
    except requests.exceptions.Timeout:
        print("❌ 请求超时（300秒），流式接口可能需要更长时间")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://8.210.52.217:8001"
    print("智能运势流式接口测试（gRPC-Web 网关方式）")
    print("=" * 80)
    print(f"服务器: {base_url}")
    print()
    test_scenario_1(base_url)
    test_scenario_2(base_url)
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

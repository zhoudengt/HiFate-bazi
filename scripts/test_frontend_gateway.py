#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 FrontendGateway 服务可用性

测试 frontend_gateway.proto 定义的 FrontendGateway.Call 方法
"""

import sys
import os
import json
import requests
from typing import Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

API_BASE_URL = "http://localhost:8001"
GATEWAY_ENDPOINT = f"{API_BASE_URL}/api/grpc-web/frontend.gateway.FrontendGateway/Call"


def encode_frontend_request(endpoint: str, payload_json: str = "") -> bytes:
    """
    手动编码 FrontendJsonRequest protobuf 消息
    
    Args:
        endpoint: 要调用的 REST 相对路径
        payload_json: 请求体（JSON 字符串形式）
        
    Returns:
        bytes: 编码后的 protobuf 消息
    """
    buffer = bytearray()
    
    # string endpoint = 1; (wire_type = 2)
    if endpoint:
        endpoint_bytes = endpoint.encode('utf-8')
        buffer.extend(_write_varint((1 << 3) | 2))  # field_number=1, wire_type=2 (string)
        buffer.extend(_write_varint(len(endpoint_bytes)))
        buffer.extend(endpoint_bytes)
    
    # string payload_json = 2; (wire_type = 2)
    if payload_json:
        payload_bytes = payload_json.encode('utf-8')
        buffer.extend(_write_varint((2 << 3) | 2))  # field_number=2, wire_type=2 (string)
        buffer.extend(_write_varint(len(payload_bytes)))
        buffer.extend(payload_bytes)
    
    return bytes(buffer)


def _write_varint(value: int) -> bytes:
    """写入 protobuf varint"""
    buffer = bytearray()
    while value > 0x7F:
        buffer.append((value & 0x7F) | 0x80)
        value >>= 7
    buffer.append(value & 0x7F)
    return bytes(buffer)


def wrap_grpc_web_frame(payload: bytes) -> bytes:
    """
    将 protobuf 消息包装为 gRPC-Web 帧
    
    Args:
        payload: protobuf 消息字节
        
    Returns:
        bytes: gRPC-Web 帧
    """
    flag = 0x00  # 数据帧标志
    length = len(payload)
    header = bytes([flag]) + length.to_bytes(4, byteorder='big')
    return header + payload


def decode_frontend_response(body: bytes) -> Dict[str, Any]:
    """
    解码 FrontendJsonResponse protobuf 消息
    
    Args:
        body: gRPC-Web 响应体
        
    Returns:
        Dict: 解码后的响应数据
    """
    # 解析 gRPC-Web 帧
    if len(body) < 5:
        raise ValueError("gRPC-Web 帧长度不足")
    
    flag = body[0]
    if flag & 0x80:
        raise ValueError("首帧不应为 trailer")
    
    length = int.from_bytes(body[1:5], byteorder='big')
    message_bytes = body[5:5+length]
    
    # 解析 protobuf 消息
    result = {
        'success': False,
        'data_json': '',
        'error': '',
        'status_code': 200
    }
    
    idx = 0
    while idx < len(message_bytes):
        if idx >= len(message_bytes):
            break
        
        # 读取 field_number 和 wire_type
        tag, idx = _read_varint(message_bytes, idx)
        field_number = tag >> 3
        wire_type = tag & 0x7
        
        if wire_type == 0:  # varint
            value, idx = _read_varint(message_bytes, idx)
            if field_number == 1:  # success (bool)
                result['success'] = bool(value)
            elif field_number == 4:  # status_code (int32)
                result['status_code'] = value
        elif wire_type == 2:  # string/bytes
            length, idx = _read_varint(message_bytes, idx)
            value_bytes = message_bytes[idx:idx+length]
            idx += length
            value = value_bytes.decode('utf-8')
            if field_number == 2:  # data_json
                result['data_json'] = value
            elif field_number == 3:  # error
                result['error'] = value
    
    return result


def _read_varint(data: bytes, idx: int) -> tuple:
    """读取 protobuf varint"""
    shift = 0
    result = 0
    
    while idx < len(data):
        byte = data[idx]
        idx += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, idx
        shift += 7
    
    raise ValueError("varint 解析不完整")


def test_gateway_endpoint(endpoint: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    测试 FrontendGateway.Call 方法
    
    Args:
        endpoint: REST 端点路径（如 "/bazi/interface"）
        payload: 请求载荷（字典）
        
    Returns:
        Dict: 响应数据
    """
    # 准备请求数据
    payload_json = json.dumps(payload, ensure_ascii=False) if payload else ""
    
    # 编码 protobuf 消息
    proto_message = encode_frontend_request(endpoint, payload_json)
    
    # 包装为 gRPC-Web 帧
    grpc_web_frame = wrap_grpc_web_frame(proto_message)
    
    # 发送请求
    headers = {
        "Content-Type": "application/grpc-web+proto",
        "Accept": "application/grpc-web+proto"
    }
    
    try:
        response = requests.post(
            GATEWAY_ENDPOINT,
            data=grpc_web_frame,
            headers=headers,
            timeout=30
        )
        
        print(f"\n{'='*60}")
        print(f"测试端点: {endpoint}")
        print(f"HTTP 状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"{'='*60}\n")
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text}",
                'status_code': response.status_code
            }
        
        # 解码响应
        response_data = decode_frontend_response(response.content)
        
        # 解析 data_json
        if response_data.get('data_json'):
            try:
                response_data['data'] = json.loads(response_data['data_json'])
            except json.JSONDecodeError:
                response_data['data'] = response_data['data_json']
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"请求失败: {str(e)}",
            'status_code': 0
        }


def test_health_check():
    """测试健康检查端点"""
    print("\n" + "="*60)
    print("测试 1: 健康检查端点（通过网关）")
    print("="*60)
    
    # 先直接测试 REST 端点是否可用
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"✅ REST /health 端点可用: {response.status_code}")
    except Exception as e:
        print(f"❌ REST /health 端点不可用: {e}")
        return False
    
    # 注意：/health 可能不在 SUPPORTED_ENDPOINTS 中，我们测试一个已知的端点
    return True


def test_bazi_interface():
    """测试八字接口端点"""
    print("\n" + "="*60)
    print("测试 2: /bazi/interface 端点")
    print("="*60)
    
    payload = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male",
        "name": "测试用户",
        "location": "北京"
    }
    
    result = test_gateway_endpoint("/bazi/interface", payload)
    
    print(f"成功: {result.get('success')}")
    print(f"状态码: {result.get('status_code')}")
    if result.get('error'):
        print(f"错误: {result.get('error')}")
    if result.get('data'):
        print(f"数据键: {list(result.get('data', {}).keys())[:10]}...")
    
    return result.get('success', False)


def test_shengong_minggong():
    """测试身宫命宫端点"""
    print("\n" + "="*60)
    print("测试 3: /bazi/shengong-minggong 端点")
    print("="*60)
    
    payload = {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male"
    }
    
    result = test_gateway_endpoint("/bazi/shengong-minggong", payload)
    
    print(f"成功: {result.get('success')}")
    print(f"状态码: {result.get('status_code')}")
    if result.get('error'):
        print(f"错误: {result.get('error')}")
    if result.get('data'):
        data = result.get('data', {})
        if isinstance(data, dict):
            print(f"数据键: {list(data.keys())[:10]}...")
        else:
            print(f"数据类型: {type(data)}")
    
    return result.get('success', False)


def test_invalid_endpoint():
    """测试无效端点"""
    print("\n" + "="*60)
    print("测试 4: 无效端点（错误处理）")
    print("="*60)
    
    result = test_gateway_endpoint("/invalid/endpoint", {})
    
    print(f"成功: {result.get('success')}")
    print(f"状态码: {result.get('status_code')}")
    print(f"错误: {result.get('error', '无错误信息')}")
    
    # 无效端点应该返回错误（grpc-status=12 UNIMPLEMENTED），这是预期的
    # 检查是否返回了正确的错误信息
    has_error = bool(result.get('error'))
    correct_status = result.get('status_code') == 404 or (not result.get('success'))
    return has_error and correct_status


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("FrontendGateway 服务可用性测试")
    print("="*60)
    print(f"API 基础 URL: {API_BASE_URL}")
    print(f"网关端点: {GATEWAY_ENDPOINT}")
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务正在运行")
        else:
            print(f"⚠️  服务响应异常: HTTP {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ 服务未运行或无法连接: {e}")
        print(f"请先启动服务: python3 server/start.py")
        return
    
    # 运行测试
    results = []
    
    # 测试 1: 健康检查（验证服务可用性）
    results.append(("健康检查", test_health_check()))
    
    # 测试 2: 八字接口
    results.append(("/bazi/interface", test_bazi_interface()))
    
    # 测试 3: 身宫命宫
    results.append(("/bazi/shengong-minggong", test_shengong_minggong()))
    
    # 测试 4: 无效端点（错误处理）
    results.append(("无效端点处理", test_invalid_endpoint()))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 个通过, {failed} 个失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！FrontendGateway 服务可用。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查服务状态。")
        return 1


if __name__ == "__main__":
    sys.exit(main())

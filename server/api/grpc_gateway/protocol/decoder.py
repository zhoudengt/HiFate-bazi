#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 解码模块

提供 gRPC-Web 帧解析和 Protobuf 消息解码功能。
"""

from typing import Dict, Tuple


def read_varint(data: bytes, idx: int) -> Tuple[int, int]:
    """
    读取 protobuf varint 编码
    
    Args:
        data: 字节数据
        idx: 起始索引
        
    Returns:
        Tuple[int, int]: (解码的值, 新的索引位置)
        
    Raises:
        ValueError: varint 解析失败
    """
    shift = 0
    result = 0

    while idx < len(data):
        byte = data[idx]
        idx += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, idx
        shift += 7

    raise ValueError("varint 解析失败")


def extract_grpc_web_message(body: bytes) -> bytes:
    """
    解析 gRPC-Web 帧，返回第一帧的 payload
    
    Args:
        body: gRPC-Web 请求体
        
    Returns:
        bytes: 帧的 payload 内容
        
    Raises:
        ValueError: 帧格式错误
    """
    if len(body) < 5:
        raise ValueError("gRPC-Web 帧长度不足")

    flag = body[0]
    if flag & 0x80:
        raise ValueError("首帧不应为 trailer")

    length = int.from_bytes(body[1:5], byteorder="big")
    payload = body[5 : 5 + length]
    if len(payload) != length:
        raise ValueError("gRPC-Web payload 长度不匹配")

    return payload


def decode_frontend_request(message: bytes) -> Dict[str, str]:
    """
    手动解析 FrontendJsonRequest protobuf 消息
    
    Args:
        message: protobuf 编码的消息
        
    Returns:
        Dict[str, str]: 包含 endpoint 和 payload_json 的字典
        
    Raises:
        ValueError: 不支持的 wire_type
    """
    endpoint = ""
    payload_json = ""

    idx = 0
    length = len(message)

    while idx < length:
        key = message[idx]
        idx += 1
        field_number = key >> 3
        wire_type = key & 0x07

        if wire_type == 2:  # length-delimited
            str_len, idx = read_varint(message, idx)
            value_bytes = message[idx : idx + str_len]
            idx += str_len
            value = value_bytes.decode("utf-8")

            if field_number == 1:
                endpoint = value
            elif field_number == 2:
                payload_json = value
            # field_number == 3 (auth_token) 已移除，不再解析
        else:
            raise ValueError(f"不支持的 wire_type: {wire_type}")

    return {"endpoint": endpoint, "payload_json": payload_json}

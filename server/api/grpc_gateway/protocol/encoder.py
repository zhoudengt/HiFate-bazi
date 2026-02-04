#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC-Web 编码模块

提供 Protobuf 消息编码和 gRPC-Web 帧封装功能。
"""

from typing import Dict, Any


def write_varint(value: int) -> bytes:
    """
    写入 protobuf varint 编码
    
    Args:
        value: 要编码的整数值
        
    Returns:
        bytes: varint 编码的字节
    """
    buffer = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            buffer.append(to_write | 0x80)
        else:
            buffer.append(to_write)
            break
    return bytes(buffer)


def wrap_frame(flag: int, payload: bytes) -> bytes:
    """
    封装 gRPC-Web 帧
    
    Args:
        flag: 帧标志位（0x00 = 数据帧，0x80 = trailer 帧）
        payload: 帧内容
        
    Returns:
        bytes: 封装后的帧
    """
    header = bytes([flag]) + len(payload).to_bytes(4, byteorder="big")
    return header + payload


def encode_frontend_response(
    *, success: bool, data_json: str, error: str, status_code: int
) -> bytes:
    """
    手动编码 FrontendJsonResponse protobuf 消息
    
    Args:
        success: 是否成功
        data_json: 数据 JSON 字符串
        error: 错误信息
        status_code: HTTP 状态码
        
    Returns:
        bytes: 编码后的 protobuf 消息
    """
    buffer = bytearray()

    # bool success = 1;
    buffer.extend(write_varint((1 << 3) | 0))
    buffer.extend(write_varint(1 if success else 0))

    # string data_json = 2;
    if data_json:
        data_bytes = data_json.encode("utf-8")
        buffer.extend(write_varint((2 << 3) | 2))
        buffer.extend(write_varint(len(data_bytes)))
        buffer.extend(data_bytes)

    # string error = 3;
    if error:
        error_bytes = error.encode("utf-8")
        buffer.extend(write_varint((3 << 3) | 2))
        buffer.extend(write_varint(len(error_bytes)))
        buffer.extend(error_bytes)

    # int32 status_code = 4;
    buffer.extend(write_varint((4 << 3) | 0))
    buffer.extend(write_varint(status_code))

    return bytes(buffer)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 gRPC-Web 调用日元-六十甲子接口。

用法:
  python3 scripts/grpc/grpc_web_call_rizhu_liujiazi.py
  python3 scripts/grpc/grpc_web_call_rizhu_liujiazi.py --endpoint /bazi/rizhu-liujiazi

网关要求: Content-Type: application/grpc-web 或 application/grpc-web+proto
"""

import sys
import struct
import json
import subprocess
import argparse
import tempfile
import os


def encode_varint(n: int) -> bytes:
    n = n & 0xFFFFFFFF
    buf = []
    while n > 0x7F:
        buf.append((n & 0x7F) | 0x80)
        n >>= 7
    buf.append(n & 0x7F)
    return bytes(buf)


def encode_string_field(field_number: int, value: str) -> bytes:
    value_bytes = value.encode("utf-8")
    tag = (field_number << 3) | 2  # length-delimited
    return bytes([tag]) + encode_varint(len(value_bytes)) + value_bytes


def encode_frontend_json_request(endpoint: str, payload_json: str, auth_token: str = "") -> bytes:
    """FrontendJsonRequest: endpoint=1, payload_json=2, auth_token=3"""
    parts = []
    if endpoint:
        parts.append(encode_string_field(1, endpoint))
    if payload_json:
        parts.append(encode_string_field(2, payload_json))
    if auth_token:
        parts.append(encode_string_field(3, auth_token))
    return b"".join(parts)


def wrap_grpc_web_frame(message: bytes, flag: int = 0x00) -> bytes:
    """gRPC-Web 帧: 1 字节 flag + 4 字节大端长度 + body"""
    return bytes([flag]) + struct.pack(">I", len(message)) + message


def main():
    parser = argparse.ArgumentParser(description="gRPC-Web 调用日元-六十甲子接口")
    parser.add_argument(
        "--url",
        default="https://www.yuanqistation.com/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call",
        help="网关 URL",
    )
    parser.add_argument(
        "--endpoint",
        default="/destiny/frontend/api/v1/bazi/rizhu-liujiazi",
        help="内部端点路径（与前端一致）",
    )
    parser.add_argument(
        "--solar-date",
        default="1990-01-15",
        help="阳历日期 YYYY-MM-DD",
    )
    parser.add_argument(
        "--solar-time",
        default="12:00",
        help="出生时间 HH:MM",
    )
    parser.add_argument(
        "--gender",
        default="male",
        choices=("male", "female"),
        help="性别",
    )
    parser.add_argument(
        "--no-curl",
        action="store_true",
        help="只输出二进制到文件，不执行 curl（用于调试）",
    )
    parser.add_argument(
        "--content-type",
        default="application/grpc-web",
        help="Content-Type（网关要求 application/grpc-web 或 application/grpc-web+proto）",
    )
    args = parser.parse_args()

    payload = {
        "solar_date": args.solar_date,
        "solar_time": args.solar_time,
        "gender": args.gender,
        "calendar_type": "solar",
        "location": "北京",
        "latitude": 39.9,
        "longitude": 116.4,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)

    message = encode_frontend_json_request(args.endpoint, payload_json)
    body = wrap_grpc_web_frame(message)

    if args.no_curl:
        out_path = tempfile.mktemp(suffix=".grpcweb")
        with open(out_path, "wb") as f:
            f.write(body)
        print(f"Body 已写入: {out_path} ({len(body)} bytes)", file=sys.stderr)
        print(f"curl 命令:", file=sys.stderr)
        print(
            f"curl -s -X POST '{args.url}' -H 'Content-Type: {args.content_type}' --data-binary @{out_path}",
            file=sys.stderr,
        )
        return 0

    with tempfile.NamedTemporaryFile(delete=False, suffix=".grpcweb") as f:
        f.write(body)
        tmp = f.name

    try:
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            args.url,
            "-H",
            f"Content-Type: {args.content_type}",
            "--data-binary",
            f"@{tmp}",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        os.unlink(tmp)
        sys.stdout.buffer.write(result.stdout)
        if result.stderr:
            sys.stderr.buffer.write(result.stderr)
        return result.returncode
    except Exception as e:
        if os.path.exists(tmp):
            os.unlink(tmp)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本：测试 /api/v2/face/analyze/stream 和 /api/v2/desk-fengshui/analyze/stream
在上传大文件（如 >10MB）时为何没有返回值。

用法：
  # 测试 1MB（基线）
  python3 scripts/diagnose_stream_upload_large_file.py --base-url http://localhost:8001 --size-mb 1

  # 测试 10MB、15MB（复现问题）
  python3 scripts/diagnose_stream_upload_large_file.py --base-url http://localhost:8001 --size-mb 10
  python3 scripts/diagnose_stream_upload_large_file.py --base-url http://localhost:8001 --size-mb 15

  # 指定生产环境地址
  python3 scripts/diagnose_stream_upload_large_file.py --base-url https://api.yourdomain.com --size-mb 15 --timeout 120

  # 只测某一个接口
  python3 scripts/diagnose_stream_upload_large_file.py --base-url http://localhost:8001 --size-mb 15 --endpoint face
"""

import argparse
import os
import sys
import time
import tempfile

# 最小 JPEG 文件头 + 填充，使文件被识别为 image/jpeg
JPEG_HEADER = bytes(
    [0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01]
    + [0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00]
    + [0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14]
    + [0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12, 0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A]
    + [0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C]
    + [0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32]
)
JPEG_FOOTER = bytes([0xFF, 0xD9])


def make_dummy_jpeg(size_bytes: int) -> bytes:
    """生成指定大小的伪 JPEG 内容（可被识别为 image/jpeg）。"""
    if size_bytes <= len(JPEG_HEADER) + len(JPEG_FOOTER):
        return JPEG_HEADER + JPEG_FOOTER
    middle = size_bytes - len(JPEG_HEADER) - len(JPEG_FOOTER)
    return JPEG_HEADER + (b"\x00" * middle) + JPEG_FOOTER


def test_stream_upload(
    base_url: str,
    endpoint_path: str,
    name: str,
    image_path: str,
    timeout: int,
) -> dict:
    """
    对单个流式接口发起 POST，记录：状态码、响应头、首包时间、读取到的首段内容、异常。
    """
    try:
        import requests
    except ImportError:
        return {
            "ok": False,
            "error": "需要安装 requests: pip install requests",
            "status_code": None,
            "time_to_first_byte_s": None,
            "time_total_s": None,
            "response_preview": None,
            "headers": {},
        }

    url = (base_url.rstrip("/") + endpoint_path).strip()
    result = {
        "ok": False,
        "error": None,
        "status_code": None,
        "time_to_first_byte_s": None,
        "time_total_s": None,
        "response_preview": None,
        "headers": {},
        "bytes_read": 0,
    }

    start = time.perf_counter()
    first_byte_time = None
    preview_chunks = []
    total_bytes = 0
    max_preview = 2000

    try:
        with open(image_path, "rb") as f:
            files = {"image": ("test_large.jpg", f, "image/jpeg")}
            # 流式接收，便于测量首包时间
            with requests.post(
                url,
                files=files,
                timeout=timeout,
                stream=True,
            ) as resp:
                result["status_code"] = resp.status_code
                result["headers"] = dict(resp.headers)

                for chunk in resp.iter_content(chunk_size=4096):
                    if first_byte_time is None:
                        first_byte_time = time.perf_counter() - start
                    total_bytes += len(chunk)
                    if len(b"".join(preview_chunks)) < max_preview:
                        preview_chunks.append(chunk)

        result["time_total_s"] = round(time.perf_counter() - start, 2)
        result["time_to_first_byte_s"] = round(first_byte_time, 2) if first_byte_time is not None else None
        result["bytes_read"] = total_bytes
        raw_preview = b"".join(preview_chunks)
        result["response_preview"] = raw_preview.decode("utf-8", errors="replace")[:max_preview]
        result["ok"] = True
    except requests.exceptions.Timeout as e:
        result["time_total_s"] = round(time.perf_counter() - start, 2)
        result["time_to_first_byte_s"] = round(first_byte_time, 2) if first_byte_time is not None else None
        result["error"] = f"请求超时 (timeout={timeout}s): {e}"
        result["bytes_read"] = total_bytes
        if preview_chunks:
            result["response_preview"] = b"".join(preview_chunks).decode("utf-8", errors="replace")[:max_preview]
    except requests.exceptions.RequestException as e:
        result["time_total_s"] = round(time.perf_counter() - start, 2)
        result["error"] = f"请求异常: {type(e).__name__}: {e}"
        if preview_chunks:
            result["response_preview"] = b"".join(preview_chunks).decode("utf-8", errors="replace")[:max_preview]
    except Exception as e:
        result["time_total_s"] = round(time.perf_counter() - start, 2)
        result["error"] = f"未预期错误: {type(e).__name__}: {e}"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="测试流式接口在大文件上传时的行为，用于诊断 >10MB 无返回值问题。"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8001",
        help="API 根地址，例如 http://localhost:8001 或 https://api.yourdomain.com",
    )
    parser.add_argument(
        "--size-mb",
        type=float,
        default=12,
        help="测试图片大小（MB），例如 1, 5, 10, 12, 15",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="请求超时时间（秒）",
    )
    parser.add_argument(
        "--endpoint",
        choices=["face", "desk", "both"],
        default="both",
        help="要测试的接口：face=面相流式, desk=办公桌风水流式, both=两个都测",
    )
    parser.add_argument(
        "--keep-file",
        action="store_true",
        help="保留生成的测试图片，不删除",
    )
    args = parser.parse_args()

    size_bytes = int(args.size_mb * 1024 * 1024)
    base_url = args.base_url.rstrip("/")

    print("=" * 60)
    print("流式接口大文件上传诊断")
    print("=" * 60)
    print(f"  base_url: {base_url}")
    print(f"  测试文件大小: {args.size_mb} MB ({size_bytes} bytes)")
    print(f"  超时: {args.timeout} s")
    print(f"  接口: {args.endpoint}")
    print("=" * 60)

    content = make_dummy_jpeg(size_bytes)
    fd, path = tempfile.mkstemp(suffix=".jpg")
    try:
        os.write(fd, content)
        os.close(fd)
        fd = None
        print(f"\n已生成测试图片: {path} ({len(content)} bytes)\n")

        endpoints = []
        if args.endpoint in ("face", "both"):
            endpoints.append(("/api/v2/face/analyze/stream", "面相分析流式"))
        if args.endpoint in ("desk", "both"):
            endpoints.append(("/api/v2/desk-fengshui/analyze/stream", "办公桌风水流式"))

        for path_suffix, name in endpoints:
            print(f"--- {name} {path_suffix} ---")
            res = test_stream_upload(base_url, path_suffix, name, path, args.timeout)
            print(f"  状态码: {res['status_code']}")
            print(f"  首包时间: {res.get('time_to_first_byte_s')} s")
            print(f"  总耗时: {res.get('time_total_s')} s")
            print(f"  读取字节数: {res.get('bytes_read', 0)}")
            if res.get("error"):
                print(f"  错误: {res['error']}")
            if res.get("response_preview"):
                preview = res["response_preview"].strip()
                if len(preview) > 400:
                    preview = preview[:400] + "\n  ... (已截断)"
                print(f"  响应预览:\n  {preview}")
            print()
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if not args.keep_file and os.path.exists(path):
            os.unlink(path)
        else:
            print(f"保留测试文件: {path}")

    print("=" * 60)
    print("根据上面输出判断：")
    print("  - 状态码 413: 请求体过大被拒绝（可能是网关或服务端限制）")
    print("  - 首包时间为 None 且超时: 服务端在读完 body 前就超时或未返回")
    print("  - 连接被重置/ConnectionError: 中间层或服务端断开")
    print("  - 有首包且有 data: 内容: 服务端已开始流式返回，可再检查后续是否中断")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

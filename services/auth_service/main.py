#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证服务启动脚本
"""

import sys
import os

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

from services.auth_service.grpc_server import serve
from services.auth_service.config import AUTH_SERVICE_PORT

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="启动认证服务 gRPC 服务")
    parser.add_argument("--port", type=int, default=AUTH_SERVICE_PORT, help=f"服务端口（默认: {AUTH_SERVICE_PORT}）")
    args = parser.parse_args()
    serve(args.port)

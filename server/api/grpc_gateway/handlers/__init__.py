# -*- coding: utf-8 -*-
"""
gRPC-Web 端点处理器模块

各 handler 在 import 时通过 @_register 自动注册到 SUPPORTED_ENDPOINTS。
主 grpc_gateway.py 在加载时 import 本包下的子模块以触发注册。
"""

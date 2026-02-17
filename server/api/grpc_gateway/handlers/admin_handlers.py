# -*- coding: utf-8 -*-
"""
安全监控与 Proto 列表 gRPC-Web 端点处理器（可选功能）
"""

import logging
from typing import Any, Dict

from server.api.grpc_gateway.endpoints import _register

logger = logging.getLogger(__name__)

# 注册安全监控端点（可选）
try:
    from server.api.v1.security_monitor import (
        get_security_stats,
        get_blocked_ips,
        unblock_ip,
    )

    @_register("/security/stats")
    async def _handle_security_stats(payload: Dict[str, Any]):
        """获取安全统计信息"""
        return await get_security_stats()

    @_register("/security/blocked-ips")
    async def _handle_security_blocked_ips(payload: Dict[str, Any]):
        """获取封禁 IP 列表"""
        return await get_blocked_ips()

    @_register("/security/unblock-ip")
    async def _handle_security_unblock_ip(payload: Dict[str, Any]):
        """解封 IP"""
        from server.api.v1.security_monitor import UnblockIPRequest
        request_model = UnblockIPRequest(**payload)
        return await unblock_ip(request_model)

    logger.info("✓ 安全监控端点已注册")
except ImportError as e:
    logger.warning(f"⚠ 安全监控端点未注册（可选功能）: {e}")

# 注册 Proto 文件服务端点（可选）
try:
    from server.api.v1.proto_service import list_proto_files

    @_register("/proto/list")
    async def _handle_proto_list(payload: Dict[str, Any]):
        """获取可用的 proto 文件列表"""
        return await list_proto_files()

    logger.info("✓ Proto 文件服务端点已注册（/proto/list）")
except ImportError as e:
    logger.warning(f"⚠ Proto 文件服务端点未注册（可选功能）: {e}")

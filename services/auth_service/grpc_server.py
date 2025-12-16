#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC server for auth-service.
OAuth 2.0 认证服务
"""

from __future__ import annotations

import json
import os
import sys
import time
import secrets
from concurrent import futures
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(PROJECT_ROOT, "proto", "generated"))
import auth_pb2
import auth_pb2_grpc

# 导入配置
from .config import (
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD,
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET,
    OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
    OAUTH_REFRESH_TOKEN_EXPIRE_DAYS,
    REDIS_KEY_PREFIX_ACCESS_TOKEN,
    REDIS_KEY_PREFIX_REFRESH_TOKEN,
    REDIS_KEY_PREFIX_AUTH_CODE,
    REDIS_KEY_PREFIX_TOKEN_INFO,
)

# 尝试导入 Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  Redis 未安装，将使用内存存储（仅用于开发）", flush=True)


class AuthServicer(auth_pb2_grpc.AuthServiceServicer):
    """实现 AuthService 的 gRPC 服务"""

    def __init__(self):
        """初始化认证服务"""
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # 测试连接
                self.redis_client.ping()
                print(f"✓ Redis 连接成功: {REDIS_HOST}:{REDIS_PORT}", flush=True)
            except Exception as e:
                print(f"⚠️  Redis 连接失败: {e}，将使用内存存储", flush=True)
                self.redis_client = None
        
        # 内存存储（Redis 不可用时的降级方案）
        self._memory_storage = {}
        self._memory_storage_ttl = {}

    def _get_redis_key(self, key_type: str, token: str) -> str:
        """获取 Redis 键"""
        prefixes = {
            "access_token": REDIS_KEY_PREFIX_ACCESS_TOKEN,
            "refresh_token": REDIS_KEY_PREFIX_REFRESH_TOKEN,
            "auth_code": REDIS_KEY_PREFIX_AUTH_CODE,
            "token_info": REDIS_KEY_PREFIX_TOKEN_INFO,
        }
        return f"{prefixes.get(key_type, 'auth:')}{token}"

    def _get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """从存储中获取 Token 信息"""
        token_prefix = token[:20] + "..." if len(token) > 20 else token
        
        if self.redis_client:
            try:
                key = self._get_redis_key("token_info", token)
                data = self.redis_client.get(key)
                if data:
                    info = json.loads(data)
                    print(f"    ✓ Token 信息从 Redis 获取: {token_prefix}", flush=True)
                    return info
                else:
                    print(f"    ✗ Token 信息在 Redis 中不存在: {token_prefix} (key: {key})", flush=True)
            except Exception as e:
                print(f"    ⚠️  Redis 读取失败: {e}", flush=True)
        
        # 降级到内存存储
        if token in self._memory_storage:
            # 检查是否过期
            if token in self._memory_storage_ttl:
                if time.time() > self._memory_storage_ttl[token]:
                    print(f"    ✗ Token 信息在内存中已过期: {token_prefix}", flush=True)
                    del self._memory_storage[token]
                    del self._memory_storage_ttl[token]
                    return None
            print(f"    ✓ Token 信息从内存获取: {token_prefix}", flush=True)
            return self._memory_storage[token]
        
        print(f"    ✗ Token 信息不存在: {token_prefix}", flush=True)
        return None

    def _save_token_info(self, token: str, info: Dict[str, Any], ttl_seconds: int):
        """保存 Token 信息到存储"""
        if self.redis_client:
            try:
                key = self._get_redis_key("token_info", token)
                self.redis_client.setex(key, ttl_seconds, json.dumps(info, ensure_ascii=False))
            except Exception as e:
                print(f"⚠️  Redis 写入失败: {e}", flush=True)
        
        # 降级到内存存储
        self._memory_storage[token] = info
        self._memory_storage_ttl[token] = time.time() + ttl_seconds

    def _check_token_exists(self, token: str, token_type: str = "access_token") -> bool:
        """检查 Token 是否存在且有效"""
        token_prefix = token[:20] + "..." if len(token) > 20 else token
        
        if self.redis_client:
            try:
                key = self._get_redis_key(token_type, token)
                exists = self.redis_client.exists(key) > 0
                if exists:
                    print(f"    ✓ Token 在 Redis 中找到: {token_prefix} (key: {key})", flush=True)
                else:
                    print(f"    ✗ Token 在 Redis 中不存在: {token_prefix} (key: {key})", flush=True)
                return exists
            except Exception as e:
                print(f"    ⚠️  Redis 查询失败: {e}", flush=True)
        
        # 降级到内存存储
        if token in self._memory_storage:
            if token in self._memory_storage_ttl:
                if time.time() > self._memory_storage_ttl[token]:
                    print(f"    ✗ Token 在内存中已过期: {token_prefix}", flush=True)
                    del self._memory_storage[token]
                    del self._memory_storage_ttl[token]
                    return False
            print(f"    ✓ Token 在内存中找到: {token_prefix}", flush=True)
            return True
        
        print(f"    ✗ Token 在内存中不存在: {token_prefix}", flush=True)
        return False

    def _verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT Token（向后兼容）"""
        try:
            import jwt
            import os
            from datetime import datetime, timezone
            
            # 获取 JWT Secret
            secret = os.getenv("JWT_SECRET") or "dev-secret-change-me"
            
            # 解码 JWT Token
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            
            # 检查是否过期
            exp = payload.get("exp")
            if exp:
                current_timestamp = datetime.now(timezone.utc).timestamp()
                if current_timestamp > exp:
                    print(f"    ✗ JWT Token 已过期 (exp: {exp}, current: {current_timestamp})", flush=True)
                    return None  # Token 已过期
            
            # 返回用户信息
            user_id = payload.get("sub", "")
            print(f"    ✓ JWT Token 验证成功 (user_id: {user_id}, exp: {exp})", flush=True)
            return {
                "user_id": user_id,
                "client_id": "jwt_client",
                "expires_at": exp if exp else 0,
                "issued_at": payload.get("iat", 0),
                "scope": []
            }
        except jwt.ExpiredSignatureError as e:
            print(f"    ✗ JWT Token 已过期: {e}", flush=True)
            return None
        except jwt.InvalidTokenError as e:
            print(f"    ✗ JWT Token 无效: {e}", flush=True)
            return None
        except ImportError as e:
            print(f"    ⚠️  PyJWT 未安装，无法验证 JWT Token: {e}", flush=True)
            return None
        except Exception as e:
            print(f"    ✗ JWT Token 验证异常: {e}", flush=True)
            return None
    
    def VerifyToken(self, request: auth_pb2.VerifyTokenRequest, context: grpc.ServicerContext) -> auth_pb2.VerifyTokenResponse:
        """验证 Token 是否有效（支持 JWT 和 OAuth Token）"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            token = request.token
            if not token:
                print(f"[{request_time}] ❌ auth-service: Token 为空", flush=True)
                return auth_pb2.VerifyTokenResponse(
                    valid=False,
                    error="Token 为空"
                )
            
            # 记录 Token 前缀（用于调试，不完整显示）
            token_prefix = token[:20] + "..." if len(token) > 20 else token
            print(f"[{request_time}] 📥 auth-service: 验证 Token ({token_prefix})", flush=True)
            
            # 首先尝试作为 OAuth Token 验证
            print(f"    尝试作为 OAuth Token 验证...", flush=True)
            redis_status = "可用" if self.redis_client else "不可用（使用内存存储）"
            print(f"    Redis 状态: {redis_status}", flush=True)
            
            # 检查 Access Token 是否存在
            if self._check_token_exists(token, "access_token"):
                # 获取 Token 信息
                print(f"    获取 OAuth Token 信息...", flush=True)
                token_info = self._get_token_info(token)
                if token_info:
                    # 检查是否过期
                    expires_at = token_info.get("expires_at", 0)
                    current_time = time.time()
                    if expires_at > 0:
                        if current_time > expires_at:
                            remaining = expires_at - current_time
                            print(f"[{request_time}] ❌ auth-service: OAuth Token 已过期 ({token_prefix}, 过期时间: {expires_at}, 当前时间: {current_time}, 剩余: {remaining}秒)", flush=True)
                            return auth_pb2.VerifyTokenResponse(
                                valid=False,
                                error="Token 已过期"
                            )
                        else:
                            remaining = expires_at - current_time
                            print(f"    OAuth Token 有效期剩余: {remaining:.0f} 秒", flush=True)
                    
                    print(f"[{request_time}] ✅ auth-service: OAuth Token 验证成功 ({token_prefix}, user_id: {token_info.get('user_id', 'N/A')})", flush=True)
                    return auth_pb2.VerifyTokenResponse(
                        valid=True,
                        user_id=token_info.get("user_id", ""),
                        client_id=token_info.get("client_id", ""),
                        expires_at=int(expires_at)
                    )
            
            # 如果 OAuth Token 验证失败，尝试作为 JWT Token 验证（向后兼容）
            print(f"    OAuth Token 验证失败，尝试作为 JWT Token 验证...", flush=True)
            jwt_info = self._verify_jwt_token(token)
            if jwt_info:
                expires_at = jwt_info.get("expires_at", 0)
                print(f"[{request_time}] ✅ auth-service: JWT Token 验证成功 ({token_prefix}, user_id: {jwt_info.get('user_id', 'N/A')})", flush=True)
                return auth_pb2.VerifyTokenResponse(
                    valid=True,
                    user_id=jwt_info.get("user_id", ""),
                    client_id=jwt_info.get("client_id", ""),
                    expires_at=int(expires_at)
                )
            
            # 两种验证都失败
            print(f"[{request_time}] ❌ auth-service: Token 不存在或已过期 ({token_prefix})", flush=True)
            return auth_pb2.VerifyTokenResponse(
                valid=False,
                error="Token 不存在或已过期"
            )
            
        except Exception as e:
            import traceback
            error_msg = f"验证失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ auth-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"验证失败: {str(e)}")
            return auth_pb2.VerifyTokenResponse(
                valid=False,
                error=f"验证失败: {str(e)}"
            )

    def RefreshToken(self, request: auth_pb2.RefreshTokenRequest, context: grpc.ServicerContext) -> auth_pb2.RefreshTokenResponse:
        """刷新 Token"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] 📥 auth-service: 刷新 Token", flush=True)
        
        try:
            refresh_token = request.refresh_token
            client_id = request.client_id
            client_secret = request.client_secret
            
            # 验证客户端凭证
            if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error="客户端凭证无效"
                )
            
            # 检查 Refresh Token 是否存在
            if not self._check_token_exists(refresh_token, "refresh_token"):
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error="Refresh Token 不存在或已过期"
                )
            
            # 获取 Refresh Token 信息
            refresh_info = self._get_token_info(refresh_token)
            if not refresh_info:
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error="Refresh Token 信息不存在"
                )
            
            # 检查是否过期
            expires_at = refresh_info.get("expires_at", 0)
            if expires_at > 0 and time.time() > expires_at:
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error="Refresh Token 已过期"
                )
            
            # 生成新的 Access Token
            user_id = refresh_info.get("user_id", "")
            new_access_token = secrets.token_urlsafe(32)
            access_token_expires_at = time.time() + (OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            
            # 保存新的 Access Token
            access_token_info = {
                "user_id": user_id,
                "client_id": client_id,
                "expires_at": access_token_expires_at,
                "issued_at": time.time()
            }
            self._save_token_info(new_access_token, access_token_info, OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            
            # 保存 Access Token 到 Redis（用于快速验证）
            if self.redis_client:
                try:
                    key = self._get_redis_key("access_token", new_access_token)
                    self.redis_client.setex(key, OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
                except Exception:
                    pass
            
            print(f"[{request_time}] ✅ auth-service: Token 刷新成功", flush=True)
            return auth_pb2.RefreshTokenResponse(
                success=True,
                access_token=new_access_token,
                expires_in=OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                token_type="bearer"
            )
            
        except Exception as e:
            import traceback
            error_msg = f"刷新失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ auth-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"刷新失败: {str(e)}")
            return auth_pb2.RefreshTokenResponse(
                success=False,
                error=f"刷新失败: {str(e)}"
            )

    def GetTokenInfo(self, request: auth_pb2.GetTokenInfoRequest, context: grpc.ServicerContext) -> auth_pb2.GetTokenInfoResponse:
        """获取 Token 信息"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            token = request.token
            if not token:
                print(f"[{request_time}] ❌ auth-service: Token 为空", flush=True)
                return auth_pb2.GetTokenInfoResponse(
                    valid=False,
                    error="Token 为空"
                )
            
            token_prefix = token[:20] + "..." if len(token) > 20 else token
            print(f"[{request_time}] 📥 auth-service: 获取 Token 信息 ({token_prefix})", flush=True)
            
            # 检查 Redis 连接状态
            redis_status = "可用" if self.redis_client else "不可用（使用内存存储）"
            print(f"    Redis 状态: {redis_status}", flush=True)
            
            # 检查 Token 是否存在
            print(f"    检查 Token 是否存在...", flush=True)
            if not self._check_token_exists(token, "access_token"):
                print(f"[{request_time}] ❌ auth-service: Token 不存在或已过期 ({token_prefix})", flush=True)
                return auth_pb2.GetTokenInfoResponse(
                    valid=False,
                    error="Token 不存在或已过期"
                )
            
            # 获取 Token 信息
            print(f"    获取 Token 信息...", flush=True)
            token_info = self._get_token_info(token)
            if not token_info:
                print(f"[{request_time}] ❌ auth-service: Token 信息不存在 ({token_prefix})", flush=True)
                return auth_pb2.GetTokenInfoResponse(
                    valid=False,
                    error="Token 信息不存在"
                )
            
            # 检查是否过期
            expires_at = token_info.get("expires_at", 0)
            current_time = time.time()
            if expires_at > 0:
                if current_time > expires_at:
                    remaining = expires_at - current_time
                    print(f"[{request_time}] ❌ auth-service: Token 已过期 ({token_prefix}, 过期时间: {expires_at}, 当前时间: {current_time}, 剩余: {remaining}秒)", flush=True)
                    return auth_pb2.GetTokenInfoResponse(
                        valid=False,
                        error="Token 已过期"
                    )
                else:
                    remaining = expires_at - current_time
                    print(f"    Token 有效期剩余: {remaining:.0f} 秒", flush=True)
            
            print(f"[{request_time}] ✅ auth-service: Token 信息获取成功 ({token_prefix}, user_id: {token_info.get('user_id', 'N/A')})", flush=True)
            response = auth_pb2.GetTokenInfoResponse(
                valid=True,
                user_id=token_info.get("user_id", ""),
                client_id=token_info.get("client_id", ""),
                issued_at=int(token_info.get("issued_at", 0)),
                expires_at=int(expires_at)
            )
            # 添加 scope（如果有）
            if "scope" in token_info:
                response.scope.extend(token_info["scope"])
            
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"获取失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ auth-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"获取失败: {str(e)}")
            return auth_pb2.GetTokenInfoResponse(
                valid=False,
                error=f"获取失败: {str(e)}"
            )

    def CreateToken(self, request: auth_pb2.CreateTokenRequest, context: grpc.ServicerContext) -> auth_pb2.CreateTokenResponse:
        """创建 Token"""
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{request_time}] 📥 auth-service: 创建 Token", flush=True)
        
        try:
            user_id = request.user_id
            client_id = request.client_id
            scope = list(request.scope) if request.scope else []
            
            # 确定过期时间（使用请求值或默认值）
            access_token_expires_in = request.access_token_expires_in
            if access_token_expires_in <= 0:
                access_token_expires_in = OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            
            refresh_token_expires_in = request.refresh_token_expires_in
            if refresh_token_expires_in <= 0:
                refresh_token_expires_in = OAUTH_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            
            # 生成 Access Token 和 Refresh Token
            access_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            
            # 计算过期时间戳
            current_time = time.time()
            access_token_expires_at = current_time + access_token_expires_in
            refresh_token_expires_at = current_time + refresh_token_expires_in
            
            # 保存 Access Token 信息
            access_token_info = {
                "user_id": user_id,
                "client_id": client_id,
                "scope": scope,
                "expires_at": access_token_expires_at,
                "issued_at": current_time
            }
            self._save_token_info(access_token, access_token_info, access_token_expires_in)
            
            # 保存 Access Token 到 Redis（用于快速验证）
            if self.redis_client:
                try:
                    key = self._get_redis_key("access_token", access_token)
                    self.redis_client.setex(key, access_token_expires_in, "1")
                except Exception as e:
                    print(f"⚠️  Redis 保存 Access Token 失败: {e}", flush=True)
            
            # 保存 Refresh Token 信息
            refresh_token_info = {
                "user_id": user_id,
                "client_id": client_id,
                "scope": scope,
                "expires_at": refresh_token_expires_at,
                "issued_at": current_time
            }
            self._save_token_info(refresh_token, refresh_token_info, refresh_token_expires_in)
            
            # 保存 Refresh Token 到 Redis（用于快速验证）
            if self.redis_client:
                try:
                    key = self._get_redis_key("refresh_token", refresh_token)
                    self.redis_client.setex(key, refresh_token_expires_in, "1")
                except Exception as e:
                    print(f"⚠️  Redis 保存 Refresh Token 失败: {e}", flush=True)
            
            print(f"[{request_time}] ✅ auth-service: Token 创建成功", flush=True)
            return auth_pb2.CreateTokenResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=access_token_expires_in,
                token_type="bearer"
            )
            
        except Exception as e:
            import traceback
            error_msg = f"创建失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[{request_time}] ❌ auth-service: 错误 - {error_msg}", flush=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"创建失败: {str(e)}")
            return auth_pb2.CreateTokenResponse(
                success=False,
                error=f"创建失败: {str(e)}"
            )

    def HealthCheck(self, request: auth_pb2.HealthCheckRequest, context: grpc.ServicerContext) -> auth_pb2.HealthCheckResponse:
        """健康检查"""
        return auth_pb2.HealthCheckResponse(status="ok")


def serve(port: int = 9011):
    """启动 gRPC 服务器（支持热更新）"""
    try:
        # 尝试使用热更新模式
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server,
            register_microservice_reloader
        )
        
        # 服务器选项
        server_options = [
            ('grpc.keepalive_time_ms', 300000),  # 5分钟
            ('grpc.keepalive_timeout_ms', 20000),  # 20秒
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),  # 60秒
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),  # 5分钟
        ]
        
        # 创建支持热更新的服务器
        # ⚠️ 重要：使用 [::] 监听所有接口，确保 Docker 容器间可以通信
        # 如果使用 localhost，其他容器无法连接
        listen_addr = f"[::]:{port}"  # 支持 IPv4 和 IPv6
        server, reloader = create_hot_reload_server(
            service_name="auth_service",
            module_path="services.auth_service.grpc_server",
            servicer_class_name="AuthServicer",
            add_servicer_to_server_func=auth_pb2_grpc.add_AuthServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=20,
            check_interval=30,  # 30秒检查一次
            listen_addr=listen_addr
        )
        
        # 注册热更新器
        register_microservice_reloader("auth_service", reloader)
        
        # 启动热更新监控
        reloader.start()
        
        server.start()
        print(f"🚀 auth-service 启动成功（热更新模式）: {listen_addr}", flush=True)
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            print("\n>>> 正在停止服务...", flush=True)
            reloader.stop()
            server.stop(grace=5)
            print("✅ 服务已停止", flush=True)
        
    except ImportError:
        # 降级到普通模式
        print("⚠️  热更新模块不可用，使用普通模式", flush=True)
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)
        
        # ⚠️ 重要：使用 [::] 监听所有接口，确保 Docker 容器间可以通信
        listen_addr = f"[::]:{port}"  # 支持 IPv4 和 IPv6
        server.add_insecure_port(listen_addr)
        server.start()
        print(f"🚀 auth-service 启动成功（普通模式）: {listen_addr}", flush=True)
        server.wait_for_termination()
    except Exception as e:
        print(f"❌ auth-service 启动失败: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    from .config import AUTH_SERVICE_PORT
    serve(port=AUTH_SERVICE_PORT)

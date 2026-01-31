#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全中间件
用途：在请求处理过程中进行安全检查

功能：
1. IP 封禁检查
2. SQL 注入检测
3. XSS 攻击检测
4. 频率限制检查
5. 可疑访问检测
"""

import fnmatch
import time
import json
import logging
from typing import Callable, Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.datastructures import UploadFile
from io import BytesIO

from server.observability.security_monitor import get_security_monitor, SecurityEventType
from server.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# 全局限流策略：按路径模式配置 rate（请求/秒）与 capacity（令牌桶容量）
RATE_LIMIT_CONFIG: Dict[str, Dict[str, Any]] = {
    "/api/v1/bazi/*": {"rate": 100, "capacity": 200},
    "/api/v1/fortune/*": {"rate": 50, "capacity": 100},
    "/api/v1/stream/*": {"rate": 10, "capacity": 20},
}
# 未匹配到模式时使用的默认限流
DEFAULT_RATE_LIMIT = {"rate": 60, "capacity": 120}


def _match_path_config(path: str) -> Dict[str, Any]:
    """根据请求路径匹配限流配置"""
    for pattern, config in RATE_LIMIT_CONFIG.items():
        if fnmatch.fnmatch(path, pattern):
            return config
    return DEFAULT_RATE_LIMIT


class PathBasedRateLimiter:
    """按路径应用 RATE_LIMIT_CONFIG 的限流器，供 SecurityMiddleware 使用"""

    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = __import__("threading").Lock()

    def _get_limiter(self, path: str) -> RateLimiter:
        config = _match_path_config(path)
        pattern = next(
            (p for p in RATE_LIMIT_CONFIG if fnmatch.fnmatch(path, p)),
            "default",
        )
        name = f"security:{pattern}"
        with self._lock:
            if name not in self._limiters:
                self._limiters[name] = RateLimiter.get(
                    name,
                    rate=config["rate"],
                    capacity=config["capacity"],
                )
            return self._limiters[name]

    async def check_rate_limit(self, client_ip: str, path: str) -> bool:
        """检查是否允许请求；返回 True 表示允许，False 表示超限"""
        limiter = self._get_limiter(path)
        key = f"{client_ip}:{path}"
        return limiter.allow(key)


class ModifiedRequest(StarletteRequest):
    """包装的 Request 对象，用于修改请求体"""
    def __init__(self, scope, receive, modified_body: bytes):
        super().__init__(scope, receive)
        self._modified_body = modified_body
        self._body_consumed = False
    
    async def body(self):
        if not self._body_consumed:
            self._body_consumed = True
            return self._modified_body
        return b''


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.security_monitor = get_security_monitor()
        self.rate_limiter = rate_limiter
        
        # 白名单（不需要安全检查的端点）
        self.whitelist = [
            '/health',
            '/api/v1/health',
            '/docs',
            '/openapi.json',
            '/favicon.ico',
            # 注意：'/bazi/fortune/display' 不在白名单中，需要安全检查
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """处理请求"""
        # 获取客户端 IP
        client_ip = self._get_client_ip(request)
        
        # 1. 检查 IP 是否被封禁
        if self.security_monitor.is_ip_blocked(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "访问被拒绝"}
            )
        
        # 2. 白名单检查
        if request.url.path in self.whitelist:
            return await call_next(request)
        
        # 3. 频率限制检查
        if self.rate_limiter:
            if not await self.rate_limiter.check_rate_limit(client_ip, request.url.path):
                # 记录频率限制事件
                self.security_monitor.detect_rate_limit_exceeded(
                    source_ip=client_ip,
                    endpoint=request.url.path,
                    count=0
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "请求过于频繁，请稍后再试"}
                )
        
        # 4. 可疑访问检测
        self.security_monitor.detect_suspicious_access(
            source_ip=client_ip,
            endpoint=request.url.path
        )
        
        # 5. SQL 注入检测（请求参数）
        try:
            # 获取请求体（如果是 POST/PUT）
            if request.method in ['POST', 'PUT', 'PATCH']:
                body = await request.body()
                
                # 解析 body
                body_json = None
                if body:
                    try:
                        body_json = json.loads(body.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body_json = None
                
                # ✅ 特殊处理：针对 fortune/display 接口，在 SecurityMiddleware 中处理 "今" 参数
                if body_json and '/bazi/fortune/display' in str(request.url.path):
                    if isinstance(body_json, dict) and body_json.get('current_time') == "今":
                        from datetime import datetime
                        body_json['current_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        request.state.use_jin_mode = True
                        # ✅ 重要：更新 body，确保后续 FastAPI 使用修改后的值
                        body = json.dumps(body_json, ensure_ascii=False).encode('utf-8')
                
                # ✅ 保存 body 到 request.state，供后续路由使用（Request.body() 只能读取一次）
                # 注意：保存的是可能已经修改过的 body
                request.state.body = body
                request.state.body_json = body_json  # 保存解析后的 JSON（可能已经修改过）
                
                if body_json:
                    body_str = json.dumps(body_json, ensure_ascii=False)
                    
                    # 检测 SQL 注入
                    event = self.security_monitor.detect_sql_injection(
                        payload=body_str,
                        source_ip=client_ip,
                        endpoint=request.url.path
                    )
                    
                    if event:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"error": "请求参数无效"}
                        )
                    
                    # 检测 XSS
                    event = self.security_monitor.detect_xss_attack(
                        payload=body_str,
                        source_ip=client_ip,
                        endpoint=request.url.path
                    )
                    
                    if event:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"error": "请求参数无效"}
                        )
            
            # 检测 URL 参数中的 SQL 注入和 XSS
            query_string = str(request.url.query)
            if query_string:
                event = self.security_monitor.detect_sql_injection(
                    payload=query_string,
                    source_ip=client_ip,
                    endpoint=request.url.path
                )
                if event:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": "请求参数无效"}
                    )
        
        except Exception as e:
            # 安全检查失败不应影响正常请求
            pass
        
        # ✅ 6. 特殊处理：如果修改了 body，需要替换 Request 对象以确保 FastAPI 使用修改后的 body
        # 注意：这需要修改 request 的内部状态，但 FastAPI 可能已经在路由绑定阶段解析了 body
        # 所以我们只能通过 request.state 传递修改后的值，依赖函数中需要使用它
        
        # 6. 处理请求
        try:
            response = await call_next(request)
            
            # 7. 检查响应中的数据库错误
            if response.status_code >= 500:
                # 记录数据库错误（可能是攻击）
                # 注意：这里需要从响应中提取错误信息，实际实现可能需要调整
                pass
            
            return response
        
        except Exception as e:
            # 记录异常
            error_message = str(e)
            if 'database' in error_message.lower() or 'sql' in error_message.lower():
                self.security_monitor.detect_database_error(
                    error_message=error_message,
                    source_ip=client_ip,
                    endpoint=request.url.path
                )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 检查 X-Forwarded-For 头（代理/负载均衡）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个 IP（原始客户端 IP）
            return forwarded_for.split(",")[0].strip()
        
        # 检查 X-Real-IP 头
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 使用直接连接的 IP
        if request.client:
            return request.client.host
        
        return "unknown"


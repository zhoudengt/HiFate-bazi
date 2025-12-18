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

import time
import json
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from server.observability.security_monitor import get_security_monitor, SecurityEventType
from server.core.rate_limiter import RateLimiter


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
                if body:
                    try:
                        body_json = json.loads(body.decode('utf-8'))
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
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            
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


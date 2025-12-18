#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全监控模块
用途：监控系统安全事件，检测异常行为，触发告警

功能：
1. SQL 注入攻击检测
2. XSS 攻击检测
3. 暴力破解检测
4. 异常访问模式检测
5. 敏感操作监控
6. 安全事件告警
"""

import time
import re
import json
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from server.observability.structured_logger import StructuredLogger
from server.observability.alert_manager import AlertManager


class SecurityEventType(Enum):
    """安全事件类型"""
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    BRUTE_FORCE = "brute_force"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACCESS = "suspicious_access"
    SENSITIVE_OPERATION = "sensitive_operation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    FILE_UPLOAD_ABUSE = "file_upload_abuse"
    API_ABUSE = "api_abuse"
    DATABASE_ERROR = "database_error"


@dataclass
class SecurityEvent:
    """安全事件"""
    event_type: SecurityEventType
    severity: str  # critical, high, medium, low
    source_ip: str
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityMonitor:
    """安全监控器"""
    
    def __init__(self):
        self.logger = StructuredLogger("security_monitor")
        self.alert_manager = AlertManager()
        
        # 攻击模式检测
        self.sql_injection_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bOR\b.*=.*)",
            r"(\bAND\b.*=.*)",
            r"('.*--.*)",
            r"('.*;.*DROP.*)",
            r"('.*;.*DELETE.*)",
            r"('.*;.*UPDATE.*)",
            r"(\bEXEC\b.*\()",
            r"(\bEXECUTE\b.*\()",
            r"(\bxp_cmdshell\b)",
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*</script>",
            r"javascript:",
            r"onerror\s*=",
            r"onload\s*=",
            r"onclick\s*=",
            r"<iframe[^>]*>",
            r"<img[^>]*onerror",
        ]
        
        # 访问频率限制（按 IP）
        self.access_frequency: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.failed_login_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        
        # 异常访问模式检测
        self.suspicious_endpoints = [
            '/admin',
            '/api/v1/admin',
            '/api/v1/internal',
            '/.env',
            '/config',
            '/debug',
        ]
        
        # 敏感操作监控
        self.sensitive_operations = [
            'DELETE',
            'UPDATE',
            'DROP',
            'ALTER',
            'CREATE',
        ]
        
        # 统计信息
        self.stats = {
            'total_events': 0,
            'events_by_type': defaultdict(int),
            'events_by_severity': defaultdict(int),
            'blocked_ips': set(),
        }
    
    def detect_sql_injection(self, payload: str, source_ip: str, endpoint: str) -> Optional[SecurityEvent]:
        """检测 SQL 注入攻击"""
        if not payload:
            return None
        
        payload_upper = payload.upper()
        
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, payload_upper, re.IGNORECASE):
                event = SecurityEvent(
                    event_type=SecurityEventType.SQL_INJECTION,
                    severity="critical",
                    source_ip=source_ip,
                    endpoint=endpoint,
                    payload={"pattern": pattern, "payload": payload[:200]},  # 限制长度
                    description=f"检测到 SQL 注入攻击模式: {pattern}"
                )
                self._record_event(event)
                return event
        
        return None
    
    def detect_xss_attack(self, payload: str, source_ip: str, endpoint: str) -> Optional[SecurityEvent]:
        """检测 XSS 攻击"""
        if not payload:
            return None
        
        for pattern in self.xss_patterns:
            if re.search(pattern, payload, re.IGNORECASE):
                event = SecurityEvent(
                    event_type=SecurityEventType.XSS_ATTACK,
                    severity="high",
                    source_ip=source_ip,
                    endpoint=endpoint,
                    payload={"pattern": pattern, "payload": payload[:200]},
                    description=f"检测到 XSS 攻击模式: {pattern}"
                )
                self._record_event(event)
                return event
        
        return None
    
    def detect_brute_force(self, source_ip: str, endpoint: str, success: bool = False) -> Optional[SecurityEvent]:
        """检测暴力破解攻击"""
        now = time.time()
        
        if not success:
            # 记录失败尝试
            self.failed_login_attempts[source_ip].append(now)
            
            # 检查失败次数
            recent_failures = [
                t for t in self.failed_login_attempts[source_ip]
                if now - t < 300  # 5分钟内
            ]
            
            if len(recent_failures) >= 5:
                event = SecurityEvent(
                    event_type=SecurityEventType.BRUTE_FORCE,
                    severity="high",
                    source_ip=source_ip,
                    endpoint=endpoint,
                    description=f"检测到暴力破解攻击：5分钟内 {len(recent_failures)} 次失败尝试"
                )
                self._record_event(event)
                return event
        else:
            # 登录成功，清除失败记录
            self.failed_login_attempts[source_ip].clear()
        
        return None
    
    def detect_rate_limit_exceeded(self, source_ip: str, endpoint: str, count: int) -> Optional[SecurityEvent]:
        """检测频率限制超出"""
        now = time.time()
        
        # 记录访问
        self.access_frequency[source_ip].append(now)
        
        # 检查最近1分钟的访问次数
        recent_accesses = [
            t for t in self.access_frequency[source_ip]
            if now - t < 60  # 1分钟内
        ]
        
        # 阈值：1分钟内超过100次请求
        if len(recent_accesses) > 100:
            event = SecurityEvent(
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                severity="medium",
                source_ip=source_ip,
                endpoint=endpoint,
                description=f"频率限制超出：1分钟内 {len(recent_accesses)} 次请求"
            )
            self._record_event(event)
            return event
        
        return None
    
    def detect_suspicious_access(self, source_ip: str, endpoint: str) -> Optional[SecurityEvent]:
        """检测可疑访问"""
        # 检查是否访问敏感端点
        for suspicious in self.suspicious_endpoints:
            if suspicious in endpoint:
                event = SecurityEvent(
                    event_type=SecurityEventType.SUSPICIOUS_ACCESS,
                    severity="medium",
                    source_ip=source_ip,
                    endpoint=endpoint,
                    description=f"访问可疑端点: {endpoint}"
                )
                self._record_event(event)
                return event
        
        return None
    
    def detect_sensitive_operation(self, operation: str, source_ip: str, user_id: Optional[str] = None) -> Optional[SecurityEvent]:
        """检测敏感操作"""
        operation_upper = operation.upper()
        
        for sensitive in self.sensitive_operations:
            if sensitive in operation_upper:
                event = SecurityEvent(
                    event_type=SecurityEventType.SENSITIVE_OPERATION,
                    severity="high",
                    source_ip=source_ip,
                    user_id=user_id,
                    description=f"执行敏感操作: {operation}"
                )
                self._record_event(event)
                return event
        
        return None
    
    def detect_database_error(self, error_message: str, source_ip: str, endpoint: str) -> Optional[SecurityEvent]:
        """检测数据库错误（可能是攻击）"""
        # 检查是否是 SQL 语法错误（可能是注入攻击）
        sql_error_patterns = [
            r"SQL syntax.*MySQL",
            r"You have an error in your SQL syntax",
            r"Unknown column",
            r"Table.*doesn't exist",
        ]
        
        for pattern in sql_error_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                event = SecurityEvent(
                    event_type=SecurityEventType.DATABASE_ERROR,
                    severity="medium",
                    source_ip=source_ip,
                    endpoint=endpoint,
                    description=f"数据库错误（可能是攻击）: {error_message[:200]}"
                )
                self._record_event(event)
                return event
        
        return None
    
    def _record_event(self, event: SecurityEvent):
        """记录安全事件"""
        self.stats['total_events'] += 1
        self.stats['events_by_type'][event.event_type.value] += 1
        self.stats['events_by_severity'][event.severity] += 1
        
        # 记录日志
        self.logger.log_security_event(
            event_type=event.event_type.value,
            severity=event.severity,
            source_ip=event.source_ip,
            endpoint=event.endpoint,
            description=event.description,
            metadata=event.metadata
        )
        
        # 触发告警（严重事件）
        if event.severity in ['critical', 'high']:
            self.alert_manager.send_alert(
                level=event.severity,
                title=f"安全事件：{event.event_type.value}",
                message=event.description,
                metadata={
                    'source_ip': event.source_ip,
                    'endpoint': event.endpoint,
                    'timestamp': datetime.fromtimestamp(event.timestamp).isoformat(),
                }
            )
        
        # 严重事件自动封禁 IP（可选）
        if event.severity == 'critical' and event.event_type == SecurityEventType.SQL_INJECTION:
            self.stats['blocked_ips'].add(event.source_ip)
            self.logger.warning(f"自动封禁 IP: {event.source_ip} (SQL 注入攻击)")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_events': self.stats['total_events'],
            'events_by_type': dict(self.stats['events_by_type']),
            'events_by_severity': dict(self.stats['events_by_severity']),
            'blocked_ips_count': len(self.stats['blocked_ips']),
            'blocked_ips': list(self.stats['blocked_ips']),
        }
    
    def is_ip_blocked(self, ip: str) -> bool:
        """检查 IP 是否被封禁"""
        return ip in self.stats['blocked_ips']
    
    def unblock_ip(self, ip: str):
        """解封 IP"""
        self.stats['blocked_ips'].discard(ip)
        self.logger.info(f"解封 IP: {ip}")


# 全局单例
_security_monitor_instance: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """获取安全监控器实例"""
    global _security_monitor_instance
    if _security_monitor_instance is None:
        _security_monitor_instance = SecurityMonitor()
    return _security_monitor_instance


def reset_security_monitor():
    """重置安全监控器（用于热更新）"""
    global _security_monitor_instance
    _security_monitor_instance = None


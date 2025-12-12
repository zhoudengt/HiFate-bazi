#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控告警模块

功能：
- 告警规则管理
- 告警触发
- 告警通知
"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    FIRING = "firing"       # 触发中
    RESOLVED = "resolved"   # 已恢复
    SILENCED = "silenced"   # 已静默


@dataclass
class Alert:
    """告警"""
    name: str
    severity: AlertSeverity
    message: str
    source: str = "system"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    status: AlertStatus = AlertStatus.FIRING
    fired_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "labels": self.labels,
            "annotations": self.annotations,
            "status": self.status.value,
            "fired_at": datetime.fromtimestamp(self.fired_at).isoformat(),
            "resolved_at": datetime.fromtimestamp(self.resolved_at).isoformat() if self.resolved_at else None,
            "duration_seconds": (self.resolved_at or time.time()) - self.fired_at
        }


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: Callable[[], bool]       # 条件函数
    severity: AlertSeverity
    message: str
    labels: Dict[str, str] = field(default_factory=dict)
    for_duration: float = 0             # 持续多久才触发（秒）
    repeat_interval: float = 300        # 重复告警间隔（秒）
    enabled: bool = True
    
    _triggered_at: Optional[float] = field(default=None, init=False)
    _last_alert_at: Optional[float] = field(default=None, init=False)


class AlertManager:
    """
    告警管理器
    
    使用示例：
        alert_manager = AlertManager.get_instance()
        
        # 添加告警规则
        alert_manager.add_rule(AlertRule(
            name="high_error_rate",
            condition=lambda: error_rate > 0.1,
            severity=AlertSeverity.ERROR,
            message="错误率超过 10%"
        ))
        
        # 手动触发告警
        alert_manager.fire(Alert(
            name="service_down",
            severity=AlertSeverity.CRITICAL,
            message="bazi-core 服务不可用"
        ))
        
        # 添加通知渠道
        alert_manager.add_notifier(webhook_notifier)
        
        # 启动检查
        alert_manager.start()
    """
    
    _instance: Optional['AlertManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._history: List[Alert] = []
        self._notifiers: List[Callable[[Alert], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 30  # 检查间隔（秒）
        self._max_history = 1000
    
    @classmethod
    def get_instance(cls) -> 'AlertManager':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._rules[rule.name] = rule
        logger.info(f"添加告警规则: {rule.name} ({rule.severity.value})")
    
    def remove_rule(self, name: str):
        """移除告警规则"""
        if name in self._rules:
            del self._rules[name]
            logger.info(f"移除告警规则: {name}")
    
    def add_notifier(self, notifier: Callable[[Alert], None]):
        """添加通知器"""
        self._notifiers.append(notifier)
    
    def fire(self, alert: Alert):
        """触发告警"""
        key = f"{alert.name}:{json.dumps(alert.labels, sort_keys=True)}"
        
        # 检查是否已存在相同告警
        if key in self._alerts:
            existing = self._alerts[key]
            if existing.status == AlertStatus.FIRING:
                return  # 已经在触发中，不重复
        
        self._alerts[key] = alert
        self._history.append(alert)
        
        # 限制历史记录数量
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        logger.warning(f"告警触发: [{alert.severity.value}] {alert.name} - {alert.message}")
        
        # 发送通知
        self._notify(alert)
    
    def resolve(self, name: str, labels: Optional[Dict[str, str]] = None):
        """解除告警"""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        
        if key in self._alerts:
            alert = self._alerts[key]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            logger.info(f"告警解除: {name}")
            
            # 发送恢复通知
            self._notify(alert)
    
    def silence(self, name: str, duration: float = 3600):
        """静默告警"""
        for key, alert in self._alerts.items():
            if alert.name == name:
                alert.status = AlertStatus.SILENCED
                logger.info(f"告警静默: {name} ({duration}秒)")
    
    def _notify(self, alert: Alert):
        """发送通知"""
        for notifier in self._notifiers:
            try:
                notifier(alert)
            except Exception as e:
                logger.error(f"发送告警通知失败: {e}")
    
    def start(self, check_interval: float = 30):
        """启动告警检查"""
        if self._running:
            return
        
        self._check_interval = check_interval
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        logger.info(f"告警管理器已启动 (检查间隔: {check_interval}秒)")
    
    def stop(self):
        """停止告警检查"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("告警管理器已停止")
    
    def _check_loop(self):
        """检查循环"""
        while self._running:
            try:
                self._check_rules()
            except Exception as e:
                logger.error(f"告警检查失败: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_rules(self):
        """检查所有规则"""
        current_time = time.time()
        
        for name, rule in self._rules.items():
            if not rule.enabled:
                continue
            
            try:
                condition_met = rule.condition()
            except Exception as e:
                logger.error(f"检查规则 {name} 失败: {e}")
                continue
            
            key = f"{name}:{json.dumps(rule.labels, sort_keys=True)}"
            
            if condition_met:
                # 条件满足
                if rule._triggered_at is None:
                    rule._triggered_at = current_time
                
                # 检查是否达到持续时间
                if current_time - rule._triggered_at >= rule.for_duration:
                    # 检查是否需要重复告警
                    if rule._last_alert_at is None or \
                       current_time - rule._last_alert_at >= rule.repeat_interval:
                        
                        alert = Alert(
                            name=rule.name,
                            severity=rule.severity,
                            message=rule.message,
                            labels=rule.labels
                        )
                        self.fire(alert)
                        rule._last_alert_at = current_time
            else:
                # 条件不满足，重置
                if rule._triggered_at is not None:
                    rule._triggered_at = None
                    self.resolve(name, rule.labels)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [a for a in self._alerts.values() if a.status == AlertStatus.FIRING]
    
    def get_all_alerts(self) -> List[Alert]:
        """获取所有告警"""
        return list(self._alerts.values())
    
    def get_history(self, limit: int = 100) -> List[Alert]:
        """获取历史告警"""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        alerts = list(self._alerts.values())
        
        return {
            "total_rules": len(self._rules),
            "active_alerts": sum(1 for a in alerts if a.status == AlertStatus.FIRING),
            "resolved_alerts": sum(1 for a in alerts if a.status == AlertStatus.RESOLVED),
            "silenced_alerts": sum(1 for a in alerts if a.status == AlertStatus.SILENCED),
            "by_severity": {
                "info": sum(1 for a in alerts if a.severity == AlertSeverity.INFO and a.status == AlertStatus.FIRING),
                "warning": sum(1 for a in alerts if a.severity == AlertSeverity.WARNING and a.status == AlertStatus.FIRING),
                "error": sum(1 for a in alerts if a.severity == AlertSeverity.ERROR and a.status == AlertStatus.FIRING),
                "critical": sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL and a.status == AlertStatus.FIRING),
            },
            "history_count": len(self._history)
        }


# 便捷函数
def get_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    return AlertManager.get_instance()


# 内置通知器
def console_notifier(alert: Alert):
    """控制台通知器"""
    status = "🔴 触发" if alert.status == AlertStatus.FIRING else "🟢 恢复"
    print(f"[告警] {status} [{alert.severity.value}] {alert.name}: {alert.message}")


def log_notifier(alert: Alert):
    """日志通知器"""
    if alert.status == AlertStatus.FIRING:
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR]:
            logger.error(f"[告警触发] {alert.name}: {alert.message}")
        else:
            logger.warning(f"[告警触发] {alert.name}: {alert.message}")
    else:
        logger.info(f"[告警恢复] {alert.name}")

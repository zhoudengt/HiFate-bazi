#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇率风控监控系统
监控汇率变化、费率异常，及时告警
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class FXRiskMonitor:
    """汇率风控监控类"""
    
    # 告警阈值配置
    ALERT_THRESHOLDS = {
        "fee_rate_increase_critical": 0.20,  # 费率增加超过20% → critical
        "fee_rate_increase_high": 0.10,      # 费率增加超过10% → high
        "exchange_rate_fluctuation": 0.05,    # 汇率波动超过5% → medium
    }
    
    # 历史数据统计周期（天）
    HISTORY_PERIOD_DAYS = 7
    
    def __init__(self):
        """初始化汇率风控监控器"""
        try:
            from server.observability.alert_manager import AlertManager, AlertSeverity
            self.alert_manager = AlertManager.get_instance()
            self.AlertSeverity = AlertSeverity
        except ImportError:
            logger.warning("AlertManager未找到，告警功能将不可用")
            self.alert_manager = None
            self.AlertSeverity = None
    
    def record_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        exchange_rate: float,
        provider: str,
        transaction_id: Optional[int] = None,
        source: str = "transaction"
    ) -> bool:
        """
        记录汇率到历史表
        
        Args:
            from_currency: 源货币代码
            to_currency: 目标货币代码
            exchange_rate: 汇率
            provider: 支付渠道
            transaction_id: 关联的交易ID
            source: 数据来源
        
        Returns:
            bool: 如果记录成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO fx_rate_history 
                    (from_currency, to_currency, exchange_rate, provider, source, transaction_id, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    from_currency, to_currency, exchange_rate, provider,
                    source, transaction_id, datetime.now()
                ))
                conn.commit()
                
                # 检查汇率异常
                self._check_exchange_rate_anomaly(from_currency, to_currency, exchange_rate, provider)
                
                return True
        except Exception as e:
            logger.error(f"记录汇率失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def record_conversion_fee(
        self,
        provider: str,
        from_currency: str,
        to_currency: str,
        fee_rate: float,
        fixed_fee: float = 0.0,
        transaction_id: Optional[int] = None
    ) -> bool:
        """
        记录转换费率到历史表
        
        Args:
            provider: 支付渠道
            from_currency: 源货币代码
            to_currency: 目标货币代码
            fee_rate: 费率
            fixed_fee: 固定费用
            transaction_id: 关联的交易ID
        
        Returns:
            bool: 如果记录成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO conversion_fee_history 
                    (provider, from_currency, to_currency, fee_rate, fixed_fee, transaction_id, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    provider, from_currency, to_currency, fee_rate, fixed_fee,
                    transaction_id, datetime.now()
                ))
                conn.commit()
                
                # 检查费率异常
                self._check_fee_rate_anomaly(provider, from_currency, to_currency, fee_rate)
                
                return True
        except Exception as e:
            logger.error(f"记录转换费率失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _check_exchange_rate_anomaly(
        self,
        from_currency: str,
        to_currency: str,
        current_rate: float,
        provider: str
    ):
        """
        检查汇率异常
        
        Args:
            from_currency: 源货币代码
            to_currency: 目标货币代码
            current_rate: 当前汇率
            provider: 支付渠道
        """
        try:
            # 获取历史平均汇率
            avg_rate = self._get_average_exchange_rate(
                from_currency, to_currency, provider
            )
            
            if avg_rate is None:
                # 没有历史数据，不检查
                return
            
            # 计算汇率变化率
            rate_change = abs(current_rate - avg_rate) / avg_rate
            
            # 检查是否超过阈值
            threshold = self.ALERT_THRESHOLDS["exchange_rate_fluctuation"]
            if rate_change > threshold:
                # 触发告警
                self._fire_alert(
                    name="exchange_rate_fluctuation",
                    severity="medium",
                    message=f"汇率异常波动: {from_currency}->{to_currency} 变化率 {rate_change:.2%}",
                    labels={
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "provider": provider,
                        "current_rate": str(current_rate),
                        "avg_rate": str(avg_rate),
                        "change_rate": f"{rate_change:.2%}"
                    }
                )
        except Exception as e:
            logger.error(f"检查汇率异常失败: {e}", exc_info=True)
    
    def _check_fee_rate_anomaly(
        self,
        provider: str,
        from_currency: str,
        to_currency: str,
        current_fee_rate: float
    ):
        """
        检查费率异常
        
        Args:
            provider: 支付渠道
            from_currency: 源货币代码
            to_currency: 目标货币代码
            current_fee_rate: 当前费率
        """
        try:
            # 获取历史平均费率
            avg_fee_rate = self._get_average_fee_rate(
                provider, from_currency, to_currency
            )
            
            if avg_fee_rate is None:
                # 没有历史数据，不检查
                return
            
            # 计算费率变化率
            if avg_fee_rate > 0:
                fee_change = (current_fee_rate - avg_fee_rate) / avg_fee_rate
            else:
                fee_change = 0
            
            # 检查是否超过阈值
            critical_threshold = self.ALERT_THRESHOLDS["fee_rate_increase_critical"]
            high_threshold = self.ALERT_THRESHOLDS["fee_rate_increase_high"]
            
            if fee_change > critical_threshold:
                # 费率突然增加超过20% → critical
                self._fire_alert(
                    name="fee_rate_critical_increase",
                    severity="critical",
                    message=f"费率突然增加: {provider} {from_currency}->{to_currency} 增加 {fee_change:.2%}",
                    labels={
                        "provider": provider,
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "current_fee_rate": str(current_fee_rate),
                        "avg_fee_rate": str(avg_fee_rate),
                        "increase_rate": f"{fee_change:.2%}"
                    }
                )
            elif fee_change > high_threshold:
                # 费率增加10-20% → high
                self._fire_alert(
                    name="fee_rate_high_increase",
                    severity="high",
                    message=f"费率异常增加: {provider} {from_currency}->{to_currency} 增加 {fee_change:.2%}",
                    labels={
                        "provider": provider,
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "current_fee_rate": str(current_fee_rate),
                        "avg_fee_rate": str(avg_fee_rate),
                        "increase_rate": f"{fee_change:.2%}"
                    }
                )
        except Exception as e:
            logger.error(f"检查费率异常失败: {e}", exc_info=True)
    
    def _get_average_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        provider: str
    ) -> Optional[float]:
        """
        获取历史平均汇率（最近N天）
        
        Args:
            from_currency: 源货币代码
            to_currency: 目标货币代码
            provider: 支付渠道
        
        Returns:
            平均汇率，如果没有历史数据返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                start_date = datetime.now() - timedelta(days=self.HISTORY_PERIOD_DAYS)
                sql = """
                    SELECT AVG(exchange_rate) as avg_rate
                    FROM fx_rate_history
                    WHERE from_currency = %s
                      AND to_currency = %s
                      AND provider = %s
                      AND recorded_at >= %s
                """
                cursor.execute(sql, (from_currency, to_currency, provider, start_date))
                result = cursor.fetchone()
                if result and result.get('avg_rate'):
                    return float(result['avg_rate'])
                return None
        except Exception as e:
            logger.error(f"获取平均汇率失败: {e}", exc_info=True)
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _get_average_fee_rate(
        self,
        provider: str,
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """
        获取历史平均费率（最近N天）
        
        Args:
            provider: 支付渠道
            from_currency: 源货币代码
            to_currency: 目标货币代码
        
        Returns:
            平均费率，如果没有历史数据返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                start_date = datetime.now() - timedelta(days=self.HISTORY_PERIOD_DAYS)
                sql = """
                    SELECT AVG(fee_rate) as avg_fee_rate
                    FROM conversion_fee_history
                    WHERE provider = %s
                      AND from_currency = %s
                      AND to_currency = %s
                      AND recorded_at >= %s
                """
                cursor.execute(sql, (provider, from_currency, to_currency, start_date))
                result = cursor.fetchone()
                if result and result.get('avg_fee_rate'):
                    return float(result['avg_fee_rate'])
                return None
        except Exception as e:
            logger.error(f"获取平均费率失败: {e}", exc_info=True)
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _fire_alert(
        self,
        name: str,
        severity: str,
        message: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        触发告警
        
        Args:
            name: 告警名称
            severity: 告警级别（critical/high/medium/low）
            message: 告警消息
            labels: 告警标签
        """
        if not self.alert_manager:
            logger.warning(f"告警管理器未初始化，无法发送告警: {message}")
            return
        
        try:
            from server.observability.alert_manager import Alert, AlertSeverity
            
            severity_map = {
                "critical": AlertSeverity.CRITICAL,
                "high": AlertSeverity.ERROR,
                "medium": AlertSeverity.WARNING,
                "low": AlertSeverity.INFO,
            }
            
            alert_severity = severity_map.get(severity, AlertSeverity.WARNING)
            
            alert = Alert(
                name=name,
                severity=alert_severity,
                message=message,
                labels=labels or {}
            )
            
            self.alert_manager.fire(alert)
            logger.warning(f"告警已触发: [{severity}] {name} - {message}")
        except Exception as e:
            logger.error(f"触发告警失败: {e}", exc_info=True)


# 单例实例
_fx_risk_monitor: Optional[FXRiskMonitor] = None


def get_fx_risk_monitor() -> FXRiskMonitor:
    """获取汇率风控监控器单例"""
    global _fx_risk_monitor
    if _fx_risk_monitor is None:
        _fx_risk_monitor = FXRiskMonitor()
    return _fx_risk_monitor

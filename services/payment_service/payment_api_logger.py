#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付接口调用日志记录器
使用装饰器模式记录所有支付接口调用
"""

import os
import sys
import time
import json
import logging
import functools
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class PaymentAPILogger:
    """支付接口调用日志记录器"""
    
    @staticmethod
    def log_api_call(
        api_name: str,
        log_request: bool = True,
        log_response: bool = True,
        log_billing: bool = True
    ):
        """
        接口调用日志记录装饰器
        
        Args:
            api_name: 接口名称（如：stripe.create_checkout_session）
            log_request: 是否记录请求参数
            log_response: 是否记录响应结果
            log_billing: 是否记录账单信息
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_timestamp = datetime.now()
                success = False
                error_code = None
                error_message = None
                http_status_code = None
                response_data = None
                request_params = None
                
                # 提取请求参数（脱敏处理）
                if log_request:
                    request_params = PaymentAPILogger._sanitize_params(kwargs)
                
                try:
                    # 调用原函数
                    result = func(*args, **kwargs)
                    success = True
                    response_data = result
                    
                    # 记录响应数据（脱敏处理）
                    if log_response and result:
                        response_data = PaymentAPILogger._sanitize_response(result)
                    
                    return result
                except Exception as e:
                    success = False
                    error_message = str(e)
                    error_code = getattr(e, 'code', None)
                    http_status_code = getattr(e, 'status_code', None)
                    raise
                finally:
                    # 计算响应时间
                    end_time = time.time()
                    duration_ms = int((end_time - start_time) * 1000)
                    
                    # 提取账单信息
                    billing_info = None
                    if log_billing:
                        billing_info = PaymentAPILogger._extract_billing_info(
                            request_params, response_data
                        )
                    
                    # 记录到数据库
                    PaymentAPILogger._save_api_call_log(
                        api_name=api_name,
                        provider=PaymentAPILogger._extract_provider(api_name),
                        start_time=start_timestamp,
                        end_time=datetime.now(),
                        duration_ms=duration_ms,
                        success=success,
                        error_code=error_code,
                        error_message=error_message,
                        http_status_code=http_status_code,
                        request_params=request_params,
                        response_data=response_data,
                        billing_info=billing_info
                    )
            
            return wrapper
        return decorator
    
    @staticmethod
    def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        脱敏处理请求参数
        
        Args:
            params: 原始参数
        
        Returns:
            脱敏后的参数
        """
        sanitized = {}
        sensitive_keys = ['secret', 'key', 'password', 'token', 'api_key', 'client_secret']
        
        for key, value in params.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "***"
            elif isinstance(value, dict):
                sanitized[key] = PaymentAPILogger._sanitize_params(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def _sanitize_response(response: Any) -> Dict[str, Any]:
        """
        脱敏处理响应结果
        
        Args:
            response: 原始响应
        
        Returns:
            脱敏后的响应
        """
        if isinstance(response, dict):
            return PaymentAPILogger._sanitize_params(response)
        elif isinstance(response, str):
            try:
                data = json.loads(response)
                return PaymentAPILogger._sanitize_params(data)
            except:
                return {"raw_response": response[:200]}  # 限制长度
        else:
            return {"response_type": type(response).__name__}
    
    @staticmethod
    def _extract_billing_info(
        request_params: Optional[Dict[str, Any]],
        response_data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        提取账单信息
        
        Args:
            request_params: 请求参数
            response_data: 响应数据
        
        Returns:
            账单信息字典
        """
        billing_info = {}
        
        # 从请求参数提取
        if request_params:
            if 'amount' in request_params:
                billing_info['billing_amount'] = request_params.get('amount')
            if 'currency' in request_params:
                billing_info['billing_currency'] = request_params.get('currency')
        
        # 从响应数据提取
        if response_data:
            if isinstance(response_data, dict):
                # 提取金额和货币
                for key in ['amount', 'total_amount', 'value']:
                    if key in response_data:
                        billing_info['billing_amount'] = response_data[key]
                
                for key in ['currency', 'currency_code']:
                    if key in response_data:
                        billing_info['billing_currency'] = response_data[key]
                
                # 提取费用信息
                if 'conversion_fee' in response_data:
                    billing_info['billing_conversion_fee'] = response_data['conversion_fee']
                if 'fixed_fee' in response_data:
                    billing_info['billing_fixed_fee'] = response_data['fixed_fee']
                if 'exchange_rate' in response_data:
                    billing_info['billing_exchange_rate'] = response_data['exchange_rate']
        
        return billing_info if billing_info else None
    
    @staticmethod
    def _extract_provider(api_name: str) -> str:
        """
        从接口名称提取支付渠道
        
        Args:
            api_name: 接口名称
        
        Returns:
            支付渠道（stripe/paypal/alipay/wechat/linepay）
        """
        api_name_lower = api_name.lower()
        if 'stripe' in api_name_lower:
            return 'stripe'
        elif 'paypal' in api_name_lower:
            return 'paypal'
        elif 'alipay' in api_name_lower:
            return 'alipay'
        elif 'wechat' in api_name_lower or 'weixin' in api_name_lower:
            return 'wechat'
        elif 'linepay' in api_name_lower or 'line' in api_name_lower:
            return 'linepay'
        else:
            return 'unknown'
    
    @staticmethod
    def _save_api_call_log(
        api_name: str,
        provider: str,
        start_time: datetime,
        end_time: datetime,
        duration_ms: int,
        success: bool,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        http_status_code: Optional[int] = None,
        request_params: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        billing_info: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[int] = None,
        order_id: Optional[str] = None
    ):
        """
        保存接口调用日志到数据库
        
        Args:
            api_name: 接口名称
            provider: 支付渠道
            start_time: 开始时间
            end_time: 结束时间
            duration_ms: 响应时间（毫秒）
            success: 是否成功
            error_code: 错误码
            error_message: 错误信息
            http_status_code: HTTP状态码
            request_params: 请求参数
            response_data: 响应数据
            billing_info: 账单信息
            transaction_id: 关联的交易ID
            order_id: 关联的订单号
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO payment_api_call_logs 
                    (api_name, provider, transaction_id, order_id,
                     start_time, end_time, duration_ms, success,
                     error_code, error_message, http_status_code,
                     request_params, response_data,
                     billing_amount, billing_currency, billing_conversion_fee,
                     billing_fixed_fee, billing_exchange_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                request_params_json = json.dumps(request_params, ensure_ascii=False) if request_params else None
                response_data_json = json.dumps(response_data, ensure_ascii=False) if response_data else None
                
                billing_amount = billing_info.get('billing_amount') if billing_info else None
                billing_currency = billing_info.get('billing_currency') if billing_info else None
                billing_conversion_fee = billing_info.get('billing_conversion_fee') if billing_info else None
                billing_fixed_fee = billing_info.get('billing_fixed_fee') if billing_info else None
                billing_exchange_rate = billing_info.get('billing_exchange_rate') if billing_info else None
                
                cursor.execute(sql, (
                    api_name, provider, transaction_id, order_id,
                    start_time, end_time, duration_ms, 1 if success else 0,
                    error_code, error_message, http_status_code,
                    request_params_json, response_data_json,
                    billing_amount, billing_currency, billing_conversion_fee,
                    billing_fixed_fee, billing_exchange_rate
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存接口调用日志失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
        finally:
            if conn:
                return_mysql_connection(conn)


# 单例实例
_api_logger: Optional[PaymentAPILogger] = None


def get_payment_api_logger() -> PaymentAPILogger:
    """获取支付接口调用日志记录器单例"""
    global _api_logger
    if _api_logger is None:
        _api_logger = PaymentAPILogger()
    return _api_logger

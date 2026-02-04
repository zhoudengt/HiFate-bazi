#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付交易 DAO
实现交易记录的创建、更新、查询方法
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from decimal import Decimal

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config.database import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class PaymentTransactionDAO:
    """支付交易 DAO"""
    
    @staticmethod
    def create_transaction(
        order_id: str,
        provider: str,
        original_amount: str,
        original_currency: str,
        converted_amount: Optional[str] = None,
        converted_currency: str = "HKD",
        needs_conversion: bool = False,
        conversion_fee: Optional[float] = None,
        conversion_fee_rate: Optional[float] = None,
        fixed_fee: Optional[float] = None,
        exchange_rate: Optional[float] = None,
        user_region: Optional[str] = None,
        region_open: bool = True,
        is_whitelisted: bool = False,
        customer_email: Optional[str] = None,
        customer_id: Optional[str] = None,
        product_name: Optional[str] = None,
        product_description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[str] = None
    ) -> Optional[int]:
        """
        创建交易记录
        
        Args:
            order_id: 订单号
            provider: 支付渠道
            original_amount: 原始金额
            original_currency: 原始货币
            converted_amount: 转换后金额
            converted_currency: 转换后货币
            needs_conversion: 是否需要转换
            conversion_fee: 转换费用
            conversion_fee_rate: 转换费率
            fixed_fee: 固定费用
            exchange_rate: 汇率
            user_region: 用户所在区域
            region_open: 区域是否开放
            is_whitelisted: 是否为白名单用户
            customer_email: 客户邮箱
            customer_id: 客户ID
            product_name: 产品名称
            product_description: 产品描述
            metadata: 元数据
        
        Returns:
            int: 交易ID，如果创建失败返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                # 计算总费用
                total_fee = Decimal("0.00")
                if conversion_fee:
                    total_fee += Decimal(str(conversion_fee))
                if fixed_fee:
                    total_fee += Decimal(str(fixed_fee))
                
                sql = """
                    INSERT INTO payment_transactions 
                    (order_id, provider, original_amount, original_currency,
                     converted_amount, converted_currency, needs_conversion,
                     conversion_fee, conversion_fee_rate, fixed_fee, total_fee,
                     exchange_rate, user_region, region_open, is_whitelisted,
                     customer_email, customer_id, product_name, product_description,
                     metadata, status, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                """
                
                import json
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
                
                cursor.execute(sql, (
                    order_id, provider, original_amount, original_currency,
                    converted_amount, converted_currency, 1 if needs_conversion else 0,
                    conversion_fee, conversion_fee_rate, fixed_fee, float(total_fee),
                    exchange_rate, user_region, 1 if region_open else 0, 1 if is_whitelisted else 0,
                    customer_email, customer_id, product_name, product_description,
                    metadata_json, expires_at
                ))
                
                transaction_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"交易记录已创建: transaction_id={transaction_id}, order_id={order_id}")
                return transaction_id
        except Exception as e:
            logger.error(f"创建交易记录失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def update_transaction(
        transaction_id: int,
        provider_payment_id: Optional[str] = None,
        status: Optional[str] = None,
        actual_exchange_rate: Optional[float] = None,
        paid_at: Optional[str] = None
    ) -> bool:
        """
        更新交易记录
        
        Args:
            transaction_id: 交易ID
            provider_payment_id: 支付渠道返回的支付ID
            status: 支付状态
            actual_exchange_rate: 实际汇率
            paid_at: 支付成功时间（ISO格式字符串）
        
        Returns:
            bool: 如果更新成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                updates = []
                params = []
                
                if provider_payment_id is not None:
                    updates.append("provider_payment_id = %s")
                    params.append(provider_payment_id)
                
                if status is not None:
                    updates.append("status = %s")
                    params.append(status)
                
                if actual_exchange_rate is not None:
                    updates.append("actual_exchange_rate = %s")
                    params.append(actual_exchange_rate)
                
                if paid_at is not None:
                    updates.append("paid_at = %s")
                    params.append(paid_at)
                
                if not updates:
                    return True
                
                params.append(transaction_id)
                sql = f"UPDATE payment_transactions SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(sql, tuple(params))
                conn.commit()
                
                logger.info(f"交易记录已更新: transaction_id={transaction_id}")
                return True
        except Exception as e:
            logger.error(f"更新交易记录失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_transaction(transaction_id: int) -> Optional[Dict[str, Any]]:
        """
        查询交易记录
        
        Args:
            transaction_id: 交易ID
        
        Returns:
            交易记录字典，如果不存在返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT * FROM payment_transactions 
                    WHERE id = %s
                """
                cursor.execute(sql, (transaction_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"查询交易记录失败: {e}", exc_info=True)
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_transaction_by_order_id(order_id: str) -> Optional[Dict[str, Any]]:
        """
        根据订单号查询交易记录
        
        Args:
            order_id: 订单号
        
        Returns:
            交易记录字典，如果不存在返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT * FROM payment_transactions 
                    WHERE order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(sql, (order_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"查询交易记录失败: {e}", exc_info=True)
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_transaction_by_provider_payment_id(provider_payment_id: str, provider: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        根据支付渠道返回的支付ID查询交易记录（用于 Webhook）
        
        Args:
            provider_payment_id: 支付渠道返回的支付ID（如：session_id, payment_id, transaction_id）
            provider: 支付渠道（可选，用于精确匹配）
        
        Returns:
            交易记录字典，如果不存在返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                if provider:
                    sql = """
                        SELECT * FROM payment_transactions 
                        WHERE provider_payment_id = %s AND provider = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    cursor.execute(sql, (provider_payment_id, provider))
                else:
                    sql = """
                        SELECT * FROM payment_transactions 
                        WHERE provider_payment_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    cursor.execute(sql, (provider_payment_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"查询交易记录失败: {e}", exc_info=True)
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def check_expired(order_id: str) -> bool:
        """
        检查订单是否过期
        
        Args:
            order_id: 订单号
        
        Returns:
            bool: 如果订单已过期返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT expires_at, status 
                    FROM payment_transactions 
                    WHERE order_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(sql, (order_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                expires_at = result.get('expires_at')
                status = result.get('status')
                
                # 如果订单已成功或已失败，不算过期
                if status in ['success', 'failed', 'canceled']:
                    return False
                
                # 如果没有设置过期时间，不算过期
                if not expires_at:
                    return False
                
                # 检查是否过期
                from datetime import datetime
                now = datetime.now()
                if isinstance(expires_at, str):
                    from dateutil.parser import parse
                    expires_at = parse(expires_at)
                
                return expires_at < now
        except Exception as e:
            logger.error(f"检查订单过期状态失败: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def update_status_by_provider_payment_id(
        provider_payment_id: str,
        provider: str,
        status: str,
        paid_at: Optional[str] = None
    ) -> bool:
        """
        根据支付渠道返回的支付ID更新订单状态（用于 Webhook）
        
        Args:
            provider_payment_id: 支付渠道返回的支付ID
            provider: 支付渠道
            status: 支付状态
            paid_at: 支付成功时间（ISO格式字符串）
        
        Returns:
            bool: 如果更新成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                updates = ["status = %s"]
                params = [status]
                
                if paid_at:
                    updates.append("paid_at = %s")
                    params.append(paid_at)
                
                params.extend([provider_payment_id, provider])
                
                sql = f"""
                    UPDATE payment_transactions 
                    SET {', '.join(updates)}, updated_at = NOW()
                    WHERE provider_payment_id = %s AND provider = %s
                """
                cursor.execute(sql, tuple(params))
                conn.commit()
                
                affected_rows = cursor.rowcount
                logger.info(f"通过支付ID更新交易记录: provider_payment_id={provider_payment_id}, status={status}, affected_rows={affected_rows}")
                return affected_rows > 0
        except Exception as e:
            logger.error(f"更新交易记录失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_conversion_fees(
        provider: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询转换费用统计
        
        Args:
            provider: 支付渠道（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        
        Returns:
            统计信息字典
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                conditions = ["needs_conversion = 1"]
                params = []
                
                if provider:
                    conditions.append("provider = %s")
                    params.append(provider)
                
                if start_date:
                    conditions.append("created_at >= %s")
                    params.append(start_date)
                
                if end_date:
                    conditions.append("created_at <= %s")
                    params.append(end_date)
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                sql = f"""
                    SELECT 
                        COUNT(*) as total_transactions,
                        SUM(conversion_fee) as total_conversion_fee,
                        SUM(fixed_fee) as total_fixed_fee,
                        SUM(total_fee) as total_fee,
                        AVG(conversion_fee_rate) as avg_fee_rate
                    FROM payment_transactions
                    {where_clause}
                """
                cursor.execute(sql, tuple(params))
                result = cursor.fetchone()
                return dict(result) if result else {}
        except Exception as e:
            logger.error(f"查询转换费用统计失败: {e}", exc_info=True)
            return {}
        finally:
            if conn:
                return_mysql_connection(conn)

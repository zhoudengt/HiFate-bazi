#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付白名单管理模块
实现白名单的添加、删除、查询、启用/禁用功能
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class PaymentWhitelistManager:
    """支付白名单管理类"""
    
    def __init__(self):
        """初始化白名单管理器"""
        self._cache: Dict[str, bool] = {}  # 缓存白名单状态
        self._cache_ttl = 300  # 5分钟缓存
    
    def is_whitelisted(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        identifier: Optional[str] = None
    ) -> bool:
        """
        检查用户是否在白名单中
        
        优先级：user_id > email > phone > identifier
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            phone: 用户手机号
            identifier: 其他标识符（如IP地址等）
        
        Returns:
            bool: 如果用户在白名单中返回True，否则返回False
        """
        # 1. 按用户ID匹配（优先级最高）
        if user_id:
            if self._check_whitelist_by_user_id(user_id):
                return True
        
        # 2. 按邮箱匹配
        if email:
            if self._check_whitelist_by_email(email):
                return True
        
        # 3. 按手机号匹配
        if phone:
            if self._check_whitelist_by_phone(phone):
                return True
        
        # 4. 按其他标识符匹配
        if identifier:
            if self._check_whitelist_by_identifier(identifier):
                return True
        
        return False
    
    def _check_whitelist_by_user_id(self, user_id: str) -> bool:
        """检查用户ID是否在白名单中"""
        cache_key = f"whitelist:user_id:{user_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT 1 
                    FROM payment_whitelist 
                    WHERE user_id = %s 
                      AND whitelist_type = 'user_id'
                      AND status = 'active'
                    LIMIT 1
                """
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                is_whitelisted = bool(result)
                self._cache[cache_key] = is_whitelisted
                return is_whitelisted
        except Exception as e:
            logger.error(f"查询白名单失败（user_id）: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _check_whitelist_by_email(self, email: str) -> bool:
        """检查邮箱是否在白名单中"""
        cache_key = f"whitelist:email:{email}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT 1 
                    FROM payment_whitelist 
                    WHERE email = %s 
                      AND whitelist_type = 'email'
                      AND status = 'active'
                    LIMIT 1
                """
                cursor.execute(sql, (email,))
                result = cursor.fetchone()
                is_whitelisted = bool(result)
                self._cache[cache_key] = is_whitelisted
                return is_whitelisted
        except Exception as e:
            logger.error(f"查询白名单失败（email）: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _check_whitelist_by_phone(self, phone: str) -> bool:
        """检查手机号是否在白名单中"""
        cache_key = f"whitelist:phone:{phone}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT 1 
                    FROM payment_whitelist 
                    WHERE phone = %s 
                      AND whitelist_type = 'phone'
                      AND status = 'active'
                    LIMIT 1
                """
                cursor.execute(sql, (phone,))
                result = cursor.fetchone()
                is_whitelisted = bool(result)
                self._cache[cache_key] = is_whitelisted
                return is_whitelisted
        except Exception as e:
            logger.error(f"查询白名单失败（phone）: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _check_whitelist_by_identifier(self, identifier: str) -> bool:
        """检查其他标识符是否在白名单中"""
        cache_key = f"whitelist:identifier:{identifier}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT 1 
                    FROM payment_whitelist 
                    WHERE identifier = %s 
                      AND whitelist_type = 'identifier'
                      AND status = 'active'
                    LIMIT 1
                """
                cursor.execute(sql, (identifier,))
                result = cursor.fetchone()
                is_whitelisted = bool(result)
                self._cache[cache_key] = is_whitelisted
                return is_whitelisted
        except Exception as e:
            logger.error(f"查询白名单失败（identifier）: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def add_to_whitelist(
        self,
        whitelist_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        identifier: Optional[str] = None,
        blocked_region: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> bool:
        """
        添加用户到白名单
        
        Args:
            whitelist_type: 白名单类型（user_id/email/phone/identifier）
            user_id: 用户ID
            email: 用户邮箱
            phone: 用户手机号
            identifier: 其他标识符
            blocked_region: 被限制的区域（如：CN）
            notes: 备注说明
            created_by: 创建人
        
        Returns:
            bool: 如果添加成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO payment_whitelist 
                    (user_id, email, phone, identifier, whitelist_type, 
                     blocked_region, status, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s)
                """
                cursor.execute(sql, (
                    user_id, email, phone, identifier, whitelist_type,
                    blocked_region, notes, created_by
                ))
                conn.commit()
                
                # 清除相关缓存（在提交后清除，确保数据已写入）
                self._clear_cache(whitelist_type, user_id, email, phone, identifier)
                
                # 如果添加成功，立即更新缓存为True（避免后续查询时缓存未命中）
                if email:
                    cache_key = f"whitelist:email:{email}"
                    self._cache[cache_key] = True
                if user_id:
                    cache_key = f"whitelist:user_id:{user_id}"
                    self._cache[cache_key] = True
                if phone:
                    cache_key = f"whitelist:phone:{phone}"
                    self._cache[cache_key] = True
                if identifier:
                    cache_key = f"whitelist:identifier:{identifier}"
                    self._cache[cache_key] = True
                
                logger.info(f"用户已添加到白名单: type={whitelist_type}")
                return True
        except Exception as e:
            logger.error(f"添加白名单失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def remove_from_whitelist(
        self,
        whitelist_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        identifier: Optional[str] = None
    ) -> bool:
        """
        从白名单移除用户
        
        Args:
            whitelist_type: 白名单类型
            user_id: 用户ID
            email: 用户邮箱
            phone: 用户手机号
            identifier: 其他标识符
        
        Returns:
            bool: 如果移除成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                # 构建WHERE条件
                conditions = ["whitelist_type = %s"]
                params = [whitelist_type]
                
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                if email:
                    conditions.append("email = %s")
                    params.append(email)
                if phone:
                    conditions.append("phone = %s")
                    params.append(phone)
                if identifier:
                    conditions.append("identifier = %s")
                    params.append(identifier)
                
                sql = f"DELETE FROM payment_whitelist WHERE {' AND '.join(conditions)}"
                cursor.execute(sql, tuple(params))
                conn.commit()
                
                # 清除相关缓存
                self._clear_cache(whitelist_type, user_id, email, phone, identifier)
                
                logger.info(f"用户已从白名单移除: type={whitelist_type}")
                return True
        except Exception as e:
            logger.error(f"移除白名单失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def get_whitelist(
        self,
        status: Optional[str] = None,
        blocked_region: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询白名单列表
        
        Args:
            status: 状态过滤（active/inactive），如果为None则查询所有
            blocked_region: 区域过滤
            limit: 限制数量
            offset: 偏移量
        
        Returns:
            白名单列表
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                conditions = []
                params = []
                
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                
                if blocked_region:
                    conditions.append("blocked_region = %s")
                    params.append(blocked_region)
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                sql = f"""
                    SELECT id, user_id, email, phone, identifier, whitelist_type,
                           blocked_region, status, notes, created_by, created_at, updated_at
                    FROM payment_whitelist
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"查询白名单列表失败: {e}", exc_info=True)
            return []
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def enable_whitelist(self, whitelist_id: int) -> bool:
        """启用白名单"""
        return self._update_whitelist_status(whitelist_id, "active")
    
    def disable_whitelist(self, whitelist_id: int) -> bool:
        """禁用白名单"""
        return self._update_whitelist_status(whitelist_id, "inactive")
    
    def _update_whitelist_status(self, whitelist_id: int, status: str) -> bool:
        """更新白名单状态"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    UPDATE payment_whitelist 
                    SET status = %s 
                    WHERE id = %s
                """
                cursor.execute(sql, (status, whitelist_id))
                conn.commit()
                
                # 清除所有缓存（因为不知道具体是哪个用户）
                self._cache.clear()
                
                logger.info(f"白名单状态已更新: id={whitelist_id}, status={status}")
                return True
        except Exception as e:
            logger.error(f"更新白名单状态失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def _clear_cache(
        self,
        whitelist_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        identifier: Optional[str] = None
    ):
        """清除相关缓存"""
        keys_to_remove = []
        
        if user_id:
            keys_to_remove.append(f"whitelist:user_id:{user_id}")
        if email:
            keys_to_remove.append(f"whitelist:email:{email}")
        if phone:
            keys_to_remove.append(f"whitelist:phone:{phone}")
        if identifier:
            keys_to_remove.append(f"whitelist:identifier:{identifier}")
        
        for key in keys_to_remove:
            if key in self._cache:
                del self._cache[key]


# 单例实例
_whitelist_manager: Optional[PaymentWhitelistManager] = None


def get_whitelist_manager() -> PaymentWhitelistManager:
    """获取白名单管理器单例"""
    global _whitelist_manager
    if _whitelist_manager is None:
        _whitelist_manager = PaymentWhitelistManager()
    return _whitelist_manager

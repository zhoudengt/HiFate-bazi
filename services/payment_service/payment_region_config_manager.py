#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付区域配置管理模块
实现区域检测、区域开放状态检查等功能
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


class PaymentRegionConfigManager:
    """支付区域配置管理类"""
    
    # 区域代码映射（手机号前缀 -> 区域代码）
    PHONE_REGION_MAP = {
        "+86": "CN",   # 大陆
        "+852": "HK",  # 香港
        "+853": "MO",  # 澳门
        "+886": "TW",  # 台湾
        "+81": "JP",   # 日本
        "+82": "KR",   # 韩国
        "+65": "SG",   # 新加坡
        "+66": "TH",   # 泰国
        "+60": "MY",   # 马来西亚
        "+63": "PH",   # 菲律宾
        "+62": "ID",   # 印尼
        "+1": "US",    # 美国/加拿大
        "+44": "GB",   # 英国
        "+49": "DE",   # 德国
        "+33": "FR",   # 法国
        "+61": "AU",   # 澳大利亚
        "+64": "NZ",   # 新西兰
    }
    
    def __init__(self):
        """初始化区域配置管理器"""
        self._cache: Dict[str, bool] = {}  # 缓存区域开放状态
        self._cache_ttl = 300  # 5分钟缓存
    
    def detect_user_region(
        self,
        ip: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        检测用户所在区域
        
        优先级：IP地址 > 手机号 > 邮箱域名 > 用户注册信息
        
        Args:
            ip: 用户IP地址
            phone: 用户手机号
            email: 用户邮箱
            user_id: 用户ID（可选，用于查询用户注册信息）
        
        Returns:
            str: 区域代码（如：HK, TW, CN, US等），如果无法检测返回 "UNKNOWN"
        """
        # 1. 按手机号检测（优先级最高，最准确）
        if phone:
            region = self._detect_region_by_phone(phone)
            if region:
                logger.debug(f"通过手机号检测到区域: {phone} -> {region}")
                return region
        
        # 2. 按IP地址检测
        if ip:
            region = self._detect_region_by_ip(ip)
            if region:
                logger.debug(f"通过IP地址检测到区域: {ip} -> {region}")
                return region
        
        # 3. 按邮箱域名检测（可选，准确度较低）
        if email:
            region = self._detect_region_by_email(email)
            if region:
                logger.debug(f"通过邮箱域名检测到区域: {email} -> {region}")
                return region
        
        # 4. 按用户注册信息检测（需要查询数据库，可选）
        if user_id:
            region = self._detect_region_by_user_id(user_id)
            if region:
                logger.debug(f"通过用户ID检测到区域: {user_id} -> {region}")
                return region
        
        logger.warning(f"无法检测用户区域: ip={ip}, phone={phone}, email={email}")
        return "UNKNOWN"
    
    def _detect_region_by_phone(self, phone: str) -> Optional[str]:
        """
        根据手机号检测区域
        
        Args:
            phone: 手机号（可能包含国家代码，如：+86 13800138000）
        
        Returns:
            区域代码，如果无法检测返回None
        """
        if not phone:
            return None
        
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        # 检查手机号前缀
        for prefix, region in self.PHONE_REGION_MAP.items():
            if phone.startswith(prefix):
                return region
        
        # 如果没有国家代码，尝试根据长度和格式判断（大陆手机号11位）
        if len(phone) == 11 and phone.startswith("1"):
            # 可能是大陆手机号（没有+86前缀）
            return "CN"
        
        return None
    
    def _detect_region_by_ip(self, ip: str) -> Optional[str]:
        """
        根据IP地址检测区域
        
        Args:
            ip: IP地址
        
        Returns:
            区域代码，如果无法检测返回None
        """
        if not ip:
            return None
        
        # TODO: 集成IP地理位置库（如：geoip2, ip2location等）
        # 目前返回None，需要后续实现
        
        # 简单判断：如果是本地IP，返回UNKNOWN
        if ip in ["127.0.0.1", "localhost", "::1"]:
            return None
        
        # 可以集成第三方IP地理位置服务
        # 例如：使用 geoip2 库或调用 IP 地理位置 API
        
        return None
    
    def _detect_region_by_email(self, email: str) -> Optional[str]:
        """
        根据邮箱域名检测区域（准确度较低，仅作参考）
        
        Args:
            email: 用户邮箱
        
        Returns:
            区域代码，如果无法检测返回None
        """
        if not email or "@" not in email:
            return None
        
        domain = email.split("@")[1].lower()
        
        # 常见邮箱域名映射（可选，准确度较低）
        domain_region_map = {
            "qq.com": "CN",
            "163.com": "CN",
            "126.com": "CN",
            "gmail.com": "US",  # 不准确，仅作参考
            "yahoo.com": "US",  # 不准确，仅作参考
        }
        
        return domain_region_map.get(domain)
    
    def _detect_region_by_user_id(self, user_id: str) -> Optional[str]:
        """
        根据用户ID查询用户注册信息中的区域
        
        Args:
            user_id: 用户ID
        
        Returns:
            区域代码，如果无法检测返回None
        """
        # TODO: 查询用户表，获取用户注册时的区域信息
        # 目前返回None，需要后续实现
        
        return None
    
    def is_region_open(self, region_code: str) -> bool:
        """
        检查区域是否开放支付
        
        Args:
            region_code: 区域代码（如：HK, TW, CN等）
        
        Returns:
            bool: 如果区域开放返回True，否则返回False
        """
        if not region_code or region_code == "UNKNOWN":
            # 未知区域默认关闭
            return False
        
        # 检查缓存
        cache_key = f"region_open:{region_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 查询数据库
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT is_open 
                    FROM payment_region_config 
                    WHERE region_code = %s
                """
                cursor.execute(sql, (region_code,))
                result = cursor.fetchone()
                
                if result:
                    is_open = bool(result.get('is_open', 0))
                    # 更新缓存
                    self._cache[cache_key] = is_open
                    return is_open
                else:
                    # 如果区域不在配置表中，默认关闭
                    logger.warning(f"区域 {region_code} 不在配置表中，默认关闭")
                    self._cache[cache_key] = False
                    return False
        except Exception as e:
            logger.error(f"查询区域配置失败: {e}", exc_info=True)
            # 出错时默认关闭
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def get_open_regions(self) -> List[Dict[str, Any]]:
        """
        获取所有开放的区域列表
        
        Returns:
            区域列表，每个区域包含 region_code, region_name, description
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT region_code, region_name, description 
                    FROM payment_region_config 
                    WHERE is_open = 1
                    ORDER BY region_code
                """
                cursor.execute(sql)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"查询开放区域失败: {e}", exc_info=True)
            return []
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def get_closed_regions(self) -> List[Dict[str, Any]]:
        """
        获取所有关闭的区域列表
        
        Returns:
            区域列表
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT region_code, region_name, description 
                    FROM payment_region_config 
                    WHERE is_open = 0
                    ORDER BY region_code
                """
                cursor.execute(sql)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"查询关闭区域失败: {e}", exc_info=True)
            return []
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def set_region_status(self, region_code: str, is_open: bool) -> bool:
        """
        设置区域开放/关闭状态
        
        Args:
            region_code: 区域代码
            is_open: 是否开放
        
        Returns:
            bool: 如果设置成功返回True，否则返回False
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    UPDATE payment_region_config 
                    SET is_open = %s 
                    WHERE region_code = %s
                """
                cursor.execute(sql, (1 if is_open else 0, region_code))
                conn.commit()
                
                # 清除缓存
                cache_key = f"region_open:{region_code}"
                if cache_key in self._cache:
                    del self._cache[cache_key]
                
                logger.info(f"区域 {region_code} 状态已更新: is_open={is_open}")
                return True
        except Exception as e:
            logger.error(f"设置区域状态失败: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)


# 单例实例
_region_config_manager: Optional[PaymentRegionConfigManager] = None


def get_region_config_manager() -> PaymentRegionConfigManager:
    """获取区域配置管理器单例"""
    global _region_config_manager
    if _region_config_manager is None:
        _region_config_manager = PaymentRegionConfigManager()
    return _region_config_manager

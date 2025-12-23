#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置表查询服务
用于查询五行属性配置表和十神命格配置表的ID映射
"""

import logging
import os
import sys
from typing import Dict, Optional, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class ConfigService:
    """配置表查询服务"""
    
    # 缓存配置映射（避免重复查询数据库）
    _element_cache: Optional[Dict[str, int]] = None
    _mingge_cache: Optional[Dict[str, int]] = None
    
    @classmethod
    def _get_element_mapping(cls) -> Dict[str, int]:
        """获取五行属性映射（带缓存）"""
        if cls._element_cache is not None:
            return cls._element_cache
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, name FROM wuxing_attributes")
                    rows = cursor.fetchall()
                    
                    # 兼容字典和元组格式
                    if rows and isinstance(rows[0], dict):
                        cls._element_cache = {row['name']: row['id'] for row in rows}
                    else:
                        cls._element_cache = {row[1]: row[0] for row in rows}
                    logger.info(f"✅ 加载五行属性配置: {len(cls._element_cache)} 条")
                    return cls._element_cache
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"❌ 查询五行属性配置失败: {e}", exc_info=True)
            # 返回默认映射（防止数据库查询失败）
            cls._element_cache = {
                '木': 1,
                '火': 2,
                '土': 3,
                '金': 4,
                '水': 5
            }
            return cls._element_cache
    
    @classmethod
    def _get_mingge_mapping(cls) -> Dict[str, int]:
        """获取十神命格映射（带缓存）"""
        if cls._mingge_cache is not None:
            return cls._mingge_cache
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, name FROM shishen_patterns")
                    rows = cursor.fetchall()
                    
                    # 兼容字典和元组格式
                    if rows and isinstance(rows[0], dict):
                        cls._mingge_cache = {row['name']: row['id'] for row in rows}
                    else:
                        cls._mingge_cache = {row[1]: row[0] for row in rows}
                    logger.info(f"✅ 加载十神命格配置: {len(cls._mingge_cache)} 条")
                    return cls._mingge_cache
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"❌ 查询十神命格配置失败: {e}", exc_info=True)
            # 返回空映射（数据库查询失败时）
            cls._mingge_cache = {}
            return cls._mingge_cache
    
    @classmethod
    def get_element_id(cls, element_name: str) -> Optional[int]:
        """
        根据五行名称获取ID
        
        Args:
            element_name: 五行名称，如 '木', '火', '土', '金', '水'
            
        Returns:
            int: 五行ID，如果未找到返回None
        """
        mapping = cls._get_element_mapping()
        return mapping.get(element_name)
    
    @classmethod
    def get_mingge_id(cls, mingge_name: str) -> Optional[int]:
        """
        根据十神命格名称获取ID
        
        Args:
            mingge_name: 十神命格名称，如 '正官格', '七杀格' 等
            
        Returns:
            int: 十神命格ID，如果未找到返回None
        """
        mapping = cls._get_mingge_mapping()
        return mapping.get(mingge_name)
    
    @classmethod
    def get_all_elements(cls) -> Dict[str, int]:
        """
        获取所有五行映射
        
        Returns:
            Dict[str, int]: 五行名称到ID的映射字典
        """
        return cls._get_element_mapping()
    
    @classmethod
    def get_all_mingge(cls) -> Dict[str, int]:
        """
        获取所有十神命格映射
        
        Returns:
            Dict[str, int]: 十神命格名称到ID的映射字典
        """
        return cls._get_mingge_mapping()
    
    @classmethod
    def map_elements_to_ids(cls, element_names: List[str]) -> List[Dict[str, any]]:
        """
        批量映射五行名称到ID
        
        Args:
            element_names: 五行名称列表，如 ['金', '土']
            
        Returns:
            List[Dict]: 包含名称和ID的字典列表，如 [{'name': '金', 'id': 4}, {'name': '土', 'id': 3}]
        """
        result = []
        mapping = cls._get_element_mapping()
        
        for name in element_names:
            element_id = mapping.get(name)
            if element_id is not None:
                result.append({
                    'name': name,
                    'id': element_id
                })
            else:
                logger.warning(f"⚠️  未找到五行 '{name}' 的ID映射")
        
        return result
    
    @classmethod
    def map_mingge_to_ids(cls, mingge_names: List[str]) -> List[Dict[str, any]]:
        """
        批量映射十神命格名称到ID
        
        Args:
            mingge_names: 十神命格名称列表，如 ['正官格', '七杀格']
            
        Returns:
            List[Dict]: 包含名称和ID的字典列表，如 [{'name': '正官格', 'id': 2001}, {'name': '七杀格', 'id': 2002}]
        """
        result = []
        mapping = cls._get_mingge_mapping()
        
        for name in mingge_names:
            mingge_id = mapping.get(name)
            if mingge_id is not None:
                result.append({
                    'name': name,
                    'id': mingge_id
                })
            else:
                logger.warning(f"⚠️  未找到十神命格 '{name}' 的ID映射")
        
        return result
    
    @classmethod
    def clear_cache(cls):
        """清除缓存（用于热更新）"""
        cls._element_cache = None
        cls._mingge_cache = None
        logger.info("✅ 配置服务缓存已清除")


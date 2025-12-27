#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业服务类 - 从数据库查询五行行业映射
支持连接池、缓存机制、热更新
"""

import logging
import os
import sys
from typing import Dict, List, Optional, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class IndustryService:
    """行业服务类 - 从数据库查询五行行业映射"""
    
    # 类级别缓存（避免频繁查询数据库）
    _industry_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
    
    @classmethod
    def _load_industries_from_db(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        从数据库加载所有行业数据（带缓存）
        
        Returns:
            Dict[str, List[Dict]]: {element: [行业数据列表]}
        """
        # 如果缓存存在，直接返回
        if cls._industry_cache is not None:
            return cls._industry_cache
        
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    # 查询所有启用的行业，按五行、优先级排序
                    cursor.execute("""
                        SELECT element, category, industry_name, description, priority
                        FROM wuxing_industries
                        WHERE enabled = 1
                        ORDER BY element, priority ASC, category, industry_name
                    """)
                    rows = cursor.fetchall()
                    
                    # 按五行分组
                    result = {}
                    for row in rows:
                        element = row['element']
                        if element not in result:
                            result[element] = []
                        
                        result[element].append({
                            'category': row['category'],
                            'industry_name': row['industry_name'],
                            'description': row.get('description', ''),
                            'priority': row.get('priority', 100)
                        })
                    
                    # 缓存结果
                    cls._industry_cache = result
                    logger.info(f"✅ 加载行业配置: {sum(len(v) for v in result.values())} 条（{len(result)} 个五行）")
                    return result
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"❌ 查询行业配置失败: {e}", exc_info=True)
            # 返回空字典（防止数据库查询失败影响业务）
            cls._industry_cache = {}
            return {}
    
    @classmethod
    def get_industries_by_elements(
        cls, 
        xi_elements: List[str], 
        ji_elements: List[str]
    ) -> Dict[str, Any]:
        """
        根据喜忌五行获取行业建议（兼容原有接口格式）
        
        Args:
            xi_elements: 喜神五行列表，如 ['金', '土']
            ji_elements: 忌神五行列表，如 ['木', '火']
        
        Returns:
            dict: {
                'best_industries': [...],      # 适合的行业列表
                'secondary_industries': [],    # 次要行业（预留）
                'avoid_industries': [...],     # 需要避免的行业列表
                'analysis': ''                 # 分析说明（预留）
            }
        """
        # 从数据库加载行业数据
        all_industries = cls._load_industries_from_db()
        
        result = {
            'best_industries': [],
            'secondary_industries': [],
            'avoid_industries': [],
            'analysis': ''
        }
        
        # 收集适合的行业（基于喜神五行）
        best_industry_set = set()
        for element in xi_elements:
            if element in all_industries:
                for industry_data in all_industries[element]:
                    industry_name = industry_data['industry_name']
                    if industry_name not in best_industry_set:
                        best_industry_set.add(industry_name)
                        result['best_industries'].append(industry_name)
        
        # 收集需要避免的行业（基于忌神五行）
        avoid_industry_set = set()
        for element in ji_elements:
            if element in all_industries:
                for industry_data in all_industries[element]:
                    industry_name = industry_data['industry_name']
                    if industry_name not in avoid_industry_set:
                        avoid_industry_set.add(industry_name)
                        result['avoid_industries'].append(industry_name)
        
        logger.debug(f"行业匹配: 喜神={xi_elements} → {len(result['best_industries'])}个行业, "
                    f"忌神={ji_elements} → {len(result['avoid_industries'])}个行业")
        
        return result
    
    @classmethod
    def get_all_industries_by_element(cls, element: str) -> List[Dict[str, Any]]:
        """
        获取指定五行的所有行业
        
        Args:
            element: 五行名称，如 '金', '木', '水', '火', '土'
        
        Returns:
            List[Dict]: 行业数据列表，每个元素包含 category, industry_name, description, priority
        """
        all_industries = cls._load_industries_from_db()
        return all_industries.get(element, [])
    
    @classmethod
    def clear_cache(cls):
        """
        清理缓存（支持热更新）
        热更新时调用此方法，强制重新从数据库加载
        """
        cls._industry_cache = None
        logger.info("✅ 行业服务缓存已清理")
    
    @classmethod
    def get_industry_mapping(cls) -> Dict[str, List[str]]:
        """
        获取五行到行业名称列表的映射（兼容旧格式）
        
        Returns:
            Dict[str, List[str]]: {element: [行业名称列表]}
        """
        all_industries = cls._load_industries_from_db()
        
        result = {}
        for element, industry_list in all_industries.items():
            result[element] = [item['industry_name'] for item in industry_list]
        
        return result


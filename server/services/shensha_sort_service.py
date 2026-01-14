#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神煞排序服务 - 提供神煞排序功能

功能：
1. 从数据库加载神煞排序配置并缓存到内存
2. 提供排序方法，按配置的排序顺序对神煞列表排序
3. 支持热更新（通过 refresh_cache 方法刷新缓存）

性能优化：
- 使用内存缓存，避免每次查询数据库
- 首次调用时延迟加载
- 使用字典实现 O(1) 查找
"""

import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ShenshaSortService:
    """神煞排序服务"""
    
    # 单例模式
    _instance = None
    _lock = threading.Lock()
    
    # 缓存：{神煞名称: 排序顺序}
    _sort_config: Dict[str, int] = {}
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def _load_config(cls) -> None:
        """从数据库加载神煞排序配置"""
        if cls._loaded:
            return
        
        with cls._lock:
            if cls._loaded:
                return
            
            try:
                from server.db.mysql_connector import get_db_connection
                
                db = get_db_connection()
                rows = db.execute_query("""
                    SELECT name, sort_order 
                    FROM shensha_sort_config 
                    WHERE enabled = TRUE 
                    ORDER BY sort_order ASC
                """)
                
                # 构建缓存字典
                cls._sort_config = {row['name']: row['sort_order'] for row in rows}
                cls._loaded = True
                
                logger.info(f"神煞排序配置加载成功，共 {len(cls._sort_config)} 条记录")
                
            except Exception as e:
                logger.warning(f"加载神煞排序配置失败: {e}，将使用默认排序")
                cls._sort_config = {}
                cls._loaded = True  # 标记为已加载，避免重复尝试
    
    @classmethod
    def refresh_cache(cls) -> None:
        """刷新缓存（用于热更新）"""
        cls._loaded = False
        cls._sort_config = {}
        cls._load_config()
        logger.info("神煞排序配置缓存已刷新")
    
    @classmethod
    def get_sort_order(cls, name: str) -> int:
        """
        获取神煞的排序顺序
        
        Args:
            name: 神煞名称
            
        Returns:
            int: 排序顺序，未找到则返回 float('inf') 表示排在最后
        """
        if not cls._loaded:
            cls._load_config()
        
        return cls._sort_config.get(name, float('inf'))
    
    @classmethod
    def sort_shensha(cls, deities: List[str]) -> List[str]:
        """
        对神煞列表进行排序
        
        Args:
            deities: 神煞名称列表
            
        Returns:
            List[str]: 排序后的神煞列表
            
        排序规则：
        1. 有排序配置的按 sort_order 从小到大排序
        2. 无配置的排在最后
        3. 同排序值按名称字母序（保证稳定性）
        """
        if not deities:
            return deities
        
        if not cls._loaded:
            cls._load_config()
        
        # 如果没有配置数据，直接返回原列表
        if not cls._sort_config:
            return deities
        
        return sorted(deities, key=lambda x: (
            cls._sort_config.get(x, float('inf')),  # 无配置的排最后
            x  # 同排序值按名称字母序
        ))
    
    @classmethod
    def get_config_count(cls) -> int:
        """获取配置数量"""
        if not cls._loaded:
            cls._load_config()
        return len(cls._sort_config)
    
    @classmethod
    def is_loaded(cls) -> bool:
        """检查配置是否已加载"""
        return cls._loaded


# 便捷函数，避免每次都要写类名
def sort_shensha(deities: List[str]) -> List[str]:
    """
    对神煞列表进行排序（便捷函数）
    
    Args:
        deities: 神煞名称列表
        
    Returns:
        List[str]: 排序后的神煞列表
    """
    return ShenshaSortService.sort_shensha(deities)


def refresh_shensha_sort_cache() -> None:
    """刷新神煞排序缓存（便捷函数）"""
    ShenshaSortService.refresh_cache()

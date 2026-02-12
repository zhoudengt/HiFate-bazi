#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 缓存工具函数
用于前端接口的多级缓存（L1 内存 + L2 Redis）
"""

import hashlib
import json
import logging
import threading
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# TTL 配置
L1_TTL = 600      # L1 内存缓存：10 分钟
L2_TTL = 86400    # L2 Redis 缓存：24 小时

# 缓存命中率统计（线程安全）
_cache_stats_lock = threading.Lock()
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "errors": 0,
    "by_endpoint": {}  # 按接口统计
}


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    生成缓存 key
    
    Args:
        prefix: 接口标识（如 'pan', 'dayun', 'rizhu' 等）
        *args: 位置参数（如 date, time, gender）
        **kwargs: 关键字参数（如 target_year, year_range 等）
    
    Returns:
        缓存 key 字符串
    """
    parts = [prefix]
    
    # 添加位置参数
    for arg in args:
        if arg is not None:
            parts.append(str(arg))
        else:
            parts.append("")
    
    # 添加关键字参数的哈希（如果有）
    if kwargs:
        # 过滤掉 None 值
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if filtered_kwargs:
            kwargs_str = json.dumps(filtered_kwargs, sort_keys=True, default=str)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:16]
            parts.append(kwargs_hash)
    
    return ":".join(parts)


def get_cached_result(cache_key: str, endpoint: str = "") -> Optional[Any]:
    """
    从多级缓存获取结果
    
    Args:
        cache_key: 缓存 key
        endpoint: 接口名称（用于统计）
    
    Returns:
        缓存的结果，如果不存在返回 None
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        result = cache.get(cache_key)
        
        if result is not None:
            record_cache_hit(endpoint)
            logger.debug(f"✅ 缓存命中: {cache_key[:50]}...")
            return result
        else:
            record_cache_miss(endpoint)
            logger.debug(f"❌ 缓存未命中: {cache_key[:50]}...")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ 缓存读取失败: {cache_key[:50]}..., 错误: {e}")
        record_cache_error(endpoint)
        return None


def set_cached_result(cache_key: str, result: Any, ttl: int = L2_TTL) -> bool:
    """
    设置多级缓存结果
    
    Args:
        cache_key: 缓存 key
        result: 要缓存的结果
        ttl: L2 缓存过期时间（秒），默认 24 小时
    
    Returns:
        是否设置成功
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        
        # 使用 per-operation TTL 参数，避免修改全局实例导致竞态
        cache.set(cache_key, result, ttl=ttl)
        
        logger.debug(f"✅ 缓存已设置: {cache_key[:50]}... (TTL: {ttl}秒)")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ 缓存设置失败: {cache_key[:50]}..., 错误: {e}")
        return False


def record_cache_hit(endpoint: str = ""):
    """记录缓存命中"""
    with _cache_stats_lock:
        _cache_stats["hits"] += 1
        if endpoint:
            if endpoint not in _cache_stats["by_endpoint"]:
                _cache_stats["by_endpoint"][endpoint] = {"hits": 0, "misses": 0, "errors": 0}
            _cache_stats["by_endpoint"][endpoint]["hits"] += 1


def record_cache_miss(endpoint: str = ""):
    """记录缓存未命中"""
    with _cache_stats_lock:
        _cache_stats["misses"] += 1
        if endpoint:
            if endpoint not in _cache_stats["by_endpoint"]:
                _cache_stats["by_endpoint"][endpoint] = {"hits": 0, "misses": 0, "errors": 0}
            _cache_stats["by_endpoint"][endpoint]["misses"] += 1


def record_cache_error(endpoint: str = ""):
    """记录缓存错误"""
    with _cache_stats_lock:
        _cache_stats["errors"] += 1
        if endpoint:
            if endpoint not in _cache_stats["by_endpoint"]:
                _cache_stats["by_endpoint"][endpoint] = {"hits": 0, "misses": 0, "errors": 0}
            _cache_stats["by_endpoint"][endpoint]["errors"] += 1


def get_cache_hit_rate() -> float:
    """
    获取总体缓存命中率
    
    Returns:
        命中率百分比（0-100）
    """
    with _cache_stats_lock:
        total = _cache_stats["hits"] + _cache_stats["misses"]
        if total == 0:
            return 0.0
        return _cache_stats["hits"] / total * 100


def get_endpoint_hit_rate(endpoint: str) -> float:
    """
    获取指定接口的缓存命中率
    
    Args:
        endpoint: 接口名称
    
    Returns:
        命中率百分比（0-100）
    """
    with _cache_stats_lock:
        if endpoint not in _cache_stats["by_endpoint"]:
            return 0.0
        stats = _cache_stats["by_endpoint"][endpoint]
        total = stats["hits"] + stats["misses"]
        if total == 0:
            return 0.0
        return stats["hits"] / total * 100


def get_cache_stats() -> dict:
    """
    获取缓存统计信息
    
    Returns:
        包含命中率统计的字典
    """
    with _cache_stats_lock:
        total = _cache_stats["hits"] + _cache_stats["misses"]
        hit_rate = _cache_stats["hits"] / total * 100 if total > 0 else 0.0
        
        # 计算各接口的命中率
        endpoint_stats = {}
        for endpoint, stats in _cache_stats["by_endpoint"].items():
            ep_total = stats["hits"] + stats["misses"]
            ep_hit_rate = stats["hits"] / ep_total * 100 if ep_total > 0 else 0.0
            endpoint_stats[endpoint] = {
                "hits": stats["hits"],
                "misses": stats["misses"],
                "errors": stats["errors"],
                "total": ep_total,
                "hit_rate": f"{ep_hit_rate:.2f}%"
            }
        
        return {
            "total_hits": _cache_stats["hits"],
            "total_misses": _cache_stats["misses"],
            "total_errors": _cache_stats["errors"],
            "total_requests": total,
            "overall_hit_rate": f"{hit_rate:.2f}%",
            "by_endpoint": endpoint_stats,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "l1_ttl": L1_TTL,
                "l2_ttl": L2_TTL
            }
        }


def reset_cache_stats():
    """重置缓存统计（用于测试）"""
    with _cache_stats_lock:
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0
        _cache_stats["errors"] = 0
        _cache_stats["by_endpoint"] = {}


# 便捷函数：获取当前日期（用于按天缓存的场景）
def get_current_date_str() -> str:
    """获取当前日期字符串（YYYY-MM-DD），用于按天缓存"""
    return datetime.now().strftime("%Y-%m-%d")


# 便捷函数：获取当前年份
def get_current_year() -> int:
    """获取当前年份"""
    return datetime.now().year


# 便捷函数：获取当前月份
def get_current_month_str() -> str:
    """获取当前月份字符串（YYYY-MM）"""
    return datetime.now().strftime("%Y-%m")

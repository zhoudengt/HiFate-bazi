#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口统一缓存工具
用于优化所有流式接口的响应速度（数据缓存 + LLM缓存）
"""

import hashlib
import json
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

# TTL 配置
DATA_CACHE_TTL = 86400    # 数据缓存：24 小时
LLM_CACHE_TTL = 3600      # LLM 缓存：1 小时


def generate_stream_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    生成流式接口缓存 key
    
    Args:
        prefix: 接口标识（如 'marriage', 'health', 'career_wealth' 等）
        *args: 位置参数（如 solar_date, solar_time, gender）
        **kwargs: 关键字参数
    
    Returns:
        缓存 key 字符串
    """
    parts = [f"stream_{prefix}"]
    
    # 添加位置参数
    for arg in args:
        if arg is not None:
            parts.append(str(arg))
        else:
            parts.append("")
    
    # 添加关键字参数的哈希（如果有）
    if kwargs:
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if filtered_kwargs:
            kwargs_str = json.dumps(filtered_kwargs, sort_keys=True, default=str)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
            parts.append(kwargs_hash)
    
    return ":".join(parts)


def get_stream_data_cache(
    prefix: str,
    solar_date: str,
    solar_time: str,
    gender: str,
    endpoint: str = "",
    **extra_params
) -> Optional[Dict[str, Any]]:
    """
    获取流式接口数据部分的缓存
    
    Args:
        prefix: 缓存前缀（如 'marriage', 'health'）
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        endpoint: 接口名称（用于统计）
        **extra_params: 额外参数
    
    Returns:
        缓存的数据，如果不存在返回 None
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        
        cache_key = generate_stream_cache_key(
            prefix, solar_date, solar_time, gender, **extra_params
        )
        
        cache = get_multi_cache()
        result = cache.get(cache_key)
        
        if result is not None:
            logger.debug(f"✅ 流式数据缓存命中: {endpoint or prefix}")
            return result
        else:
            logger.debug(f"❌ 流式数据缓存未命中: {endpoint or prefix}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ 流式数据缓存读取失败: {e}")
        return None


def set_stream_data_cache(
    prefix: str,
    solar_date: str,
    solar_time: str,
    gender: str,
    data: Dict[str, Any],
    ttl: int = DATA_CACHE_TTL,
    **extra_params
) -> bool:
    """
    设置流式接口数据部分的缓存
    
    Args:
        prefix: 缓存前缀
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        data: 要缓存的数据
        ttl: 缓存过期时间（秒）
        **extra_params: 额外参数
    
    Returns:
        是否设置成功
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        
        cache_key = generate_stream_cache_key(
            prefix, solar_date, solar_time, gender, **extra_params
        )
        
        cache = get_multi_cache()
        original_ttl = cache.l2.ttl
        cache.l2.ttl = ttl
        cache.set(cache_key, data)
        cache.l2.ttl = original_ttl
        
        logger.debug(f"✅ 流式数据缓存已设置: {prefix} (TTL: {ttl}秒)")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ 流式数据缓存设置失败: {e}")
        return False


def compute_input_data_hash(input_data: Dict[str, Any]) -> str:
    """
    计算 input_data 的哈希值（用于 LLM 缓存）
    
    Args:
        input_data: 输入数据
    
    Returns:
        哈希值字符串
    """
    try:
        data_str = json.dumps(input_data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()[:16]
    except Exception:
        # 如果序列化失败，使用 repr
        return hashlib.md5(repr(input_data).encode()).hexdigest()[:16]


def get_llm_cache(prefix: str, input_data_hash: str) -> Optional[str]:
    """
    获取 LLM 生成结果的缓存
    
    Args:
        prefix: 缓存前缀
        input_data_hash: input_data 的哈希值
    
    Returns:
        缓存的 LLM 生成结果
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        
        cache_key = f"llm_{prefix}:{input_data_hash}"
        cache = get_multi_cache()
        result = cache.get(cache_key)
        
        if result is not None:
            logger.debug(f"✅ LLM缓存命中: {prefix}")
            return result
        else:
            logger.debug(f"❌ LLM缓存未命中: {prefix}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ LLM缓存读取失败: {e}")
        return None


def set_llm_cache(
    prefix: str,
    input_data_hash: str,
    content: str,
    ttl: int = LLM_CACHE_TTL
) -> bool:
    """
    设置 LLM 生成结果的缓存
    
    Args:
        prefix: 缓存前缀
        input_data_hash: input_data 的哈希值
        content: LLM 生成的内容
        ttl: 缓存过期时间（秒）
    
    Returns:
        是否设置成功
    """
    try:
        from server.utils.cache_multi_level import get_multi_cache
        
        cache_key = f"llm_{prefix}:{input_data_hash}"
        cache = get_multi_cache()
        original_ttl = cache.l2.ttl
        cache.l2.ttl = ttl
        cache.set(cache_key, content)
        cache.l2.ttl = original_ttl
        
        logger.debug(f"✅ LLM缓存已设置: {prefix} (TTL: {ttl}秒)")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ LLM缓存设置失败: {e}")
        return False


def clear_stream_cache(prefix: str, solar_date: str = None) -> int:
    """
    清除流式接口缓存
    
    Args:
        prefix: 缓存前缀
        solar_date: 可选，指定日期的缓存
    
    Returns:
        清除的缓存数量
    """
    try:
        from server.config.redis_config import get_redis_client
        
        redis_client = get_redis_client()
        if not redis_client:
            return 0
        
        if solar_date:
            pattern = f"stream_{prefix}:{solar_date}:*"
        else:
            pattern = f"stream_{prefix}:*"
        
        cursor = 0
        deleted_count = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted_count += redis_client.delete(*keys)
            if cursor == 0:
                break
        
        logger.info(f"✅ 已清除流式缓存: {deleted_count} 条 (prefix: {prefix})")
        return deleted_count
        
    except Exception as e:
        logger.warning(f"⚠️ 清除流式缓存失败: {e}")
        return 0

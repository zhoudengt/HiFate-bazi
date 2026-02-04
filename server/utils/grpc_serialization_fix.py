#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 序列化修复工具

历史背景：
2025-11-20 发现 gRPC 序列化问题，某些字典字段（如 ten_gods_stats、element_counts 等）
在通过 gRPC 传输后可能变成字符串格式，导致下游服务解析失败。

本模块提供统一的修复函数，避免在各个服务中重复编写相同的修复逻辑。
"""

import logging
import json
import ast
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def fix_dict_field(
    value: Any,
    field_name: str = "unknown",
    default: Optional[Dict] = None,
    log_errors: bool = True
) -> Dict:
    """
    修复可能被序列化为字符串的字典字段
    
    gRPC 传输过程中，某些字典字段可能被序列化为字符串。
    此函数尝试将字符串解析回字典，如果失败则返回默认值。
    
    Args:
        value: 原始值（可能是字典或字符串）
        field_name: 字段名称（用于日志）
        default: 解析失败时的默认值，默认为空字典
        log_errors: 是否记录错误日志
    
    Returns:
        解析后的字典
    
    使用示例：
    ```python
    from server.utils.grpc_serialization_fix import fix_dict_field
    
    ten_gods_stats = fix_dict_field(
        bazi_data.get('ten_gods_stats'),
        field_name='ten_gods_stats'
    )
    ```
    """
    if default is None:
        default = {}
    
    # 如果已经是字典，直接返回
    if isinstance(value, dict):
        return value
    
    # 如果是 None 或空值，返回默认值
    if value is None or value == '':
        return default
    
    # 如果是字符串，尝试解析
    if isinstance(value, str):
        # 方法1：尝试使用 ast.literal_eval（更安全，支持 Python 字面量格式）
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, dict):
                logger.debug(f"[{field_name}] 使用 ast.literal_eval 解析成功")
                return parsed
        except (ValueError, SyntaxError):
            pass
        
        # 方法2：尝试使用 JSON 解析
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                logger.debug(f"[{field_name}] 使用 json.loads 解析成功")
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 解析失败
        if log_errors:
            # 截取前 100 个字符用于日志
            preview = value[:100] + "..." if len(value) > 100 else value
            logger.error(f"[{field_name}] 字符串解析为字典失败: {preview}")
        return default
    
    # 其他类型，记录警告并返回默认值
    if log_errors:
        logger.warning(f"[{field_name}] 类型异常: {type(value).__name__}，期望 dict 或 str")
    return default


def fix_ten_gods_stats(
    bazi_data: Dict,
    extract_totals: bool = False
) -> Dict:
    """
    修复并提取 ten_gods_stats 字段
    
    这是针对 ten_gods_stats 字段的专用修复函数，
    因为这个字段在多个服务中使用，且有时需要提取其中的 totals 子字段。
    
    Args:
        bazi_data: 八字数据字典
        extract_totals: 是否提取 totals 子字段（用于运势计算）
    
    Returns:
        修复后的 ten_gods_stats 字典
    """
    ten_gods_stats_raw = bazi_data.get('ten_gods_stats', {})
    ten_gods_stats = fix_dict_field(ten_gods_stats_raw, 'ten_gods_stats')
    
    if extract_totals:
        # 提取 totals 子字段
        totals = ten_gods_stats.get('totals', {})
        totals = fix_dict_field(totals, 'ten_gods_stats.totals')
        return totals
    
    return ten_gods_stats


def fix_element_counts(bazi_data: Dict) -> Dict:
    """
    修复 element_counts 字段
    
    Args:
        bazi_data: 八字数据字典
    
    Returns:
        修复后的 element_counts 字典
    """
    element_counts_raw = bazi_data.get('element_counts', {})
    return fix_dict_field(element_counts_raw, 'element_counts')


def fix_elements(bazi_data: Dict) -> Dict:
    """
    修复 elements 字段
    
    Args:
        bazi_data: 八字数据字典
    
    Returns:
        修复后的 elements 字典
    """
    elements_raw = bazi_data.get('elements', {})
    return fix_dict_field(elements_raw, 'elements')


def fix_relationships(bazi_data: Dict) -> Dict:
    """
    修复 relationships 字段
    
    Args:
        bazi_data: 八字数据字典
    
    Returns:
        修复后的 relationships 字典
    """
    relationships_raw = bazi_data.get('relationships', {})
    return fix_dict_field(relationships_raw, 'relationships')


def fix_all_grpc_fields(bazi_data: Dict) -> Dict:
    """
    修复所有可能被 gRPC 序列化影响的字段
    
    这是一个便捷函数，一次性修复所有已知的问题字段。
    
    Args:
        bazi_data: 八字数据字典（会被原地修改）
    
    Returns:
        修复后的八字数据字典
    """
    if not isinstance(bazi_data, dict):
        return bazi_data
    
    # 修复各个字段
    fields_to_fix = ['ten_gods_stats', 'element_counts', 'elements', 'relationships']
    
    for field in fields_to_fix:
        if field in bazi_data:
            bazi_data[field] = fix_dict_field(bazi_data.get(field), field)
    
    return bazi_data


# ==================== 向后兼容的别名 ====================

# 为了向后兼容，提供一些简短的别名
fix_grpc_dict = fix_dict_field

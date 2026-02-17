# -*- coding: utf-8 -*-
"""
序列化工具：深度清理对象确保可 JSON 序列化
"""

from typing import Any


def deep_clean_for_serialization(obj: Any, visited: set = None) -> Any:
    """深度清理对象，确保可以 JSON 序列化

    递归清理字典、列表和对象，将无法序列化的类型转换为字符串。
    用于修复面相分析V2和办公桌风水的 Maximum call stack exceeded 错误。

    Args:
        obj: 要清理的对象
        visited: 已访问对象的ID集合，用于检测循环引用
    """
    if visited is None:
        visited = set()

    if obj is None:
        return None

    obj_id = id(obj)
    if obj_id in visited:
        return "[循环引用]"
    visited.add(obj_id)

    try:
        if isinstance(obj, dict):
            return {k: deep_clean_for_serialization(v, visited) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [deep_clean_for_serialization(item, visited) for item in obj]
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif hasattr(obj, '__dict__'):
            return deep_clean_for_serialization(obj.__dict__, visited)
        else:
            return str(obj)
    finally:
        visited.discard(obj_id)

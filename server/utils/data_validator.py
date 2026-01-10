"""
数据验证和类型转换工具

用途：防止gRPC序列化导致的类型问题
- 确保字典类型的字段不会变成字符串
- 统一的类型检查和转换逻辑
- 避免 "'str' object has no attribute 'get'" 错误
"""

import json
from typing import Any, Dict, List, Union


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def ensure_dict(data: Any, default: Dict = None) -> Dict:
        """
        确保数据是字典类型
        
        Args:
            data: 要检查的数据
            default: 如果不是字典，返回的默认值
            
        Returns:
            字典类型的数据
        """
        if default is None:
            default = {}
        
        # 如果已经是字典，直接返回
        if isinstance(data, dict):
            return data
        
        # 如果是字符串，尝试JSON解析
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
        
        # 其他情况返回默认值
        return default
    
    @staticmethod
    def ensure_list(data: Any, default: List = None) -> List:
        """
        确保数据是列表类型
        
        Args:
            data: 要检查的数据
            default: 如果不是列表，返回的默认值
            
        Returns:
            列表类型的数据
        """
        if default is None:
            default = []
        
        # 如果已经是列表，直接返回
        if isinstance(data, list):
            return data
        
        # 如果是字符串，尝试JSON解析
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
        
        # 其他情况返回默认值
        return default
    
    @staticmethod
    def safe_get_nested(data: Dict, *keys: str, default: Any = None) -> Any:
        """
        安全地获取嵌套字典中的值
        
        Args:
            data: 字典数据
            *keys: 键路径（如 'a', 'b', 'c' 表示 data['a']['b']['c']）
            default: 默认值
            
        Returns:
            获取到的值或默认值
            
        Example:
            safe_get_nested(data, 'bazi', 'pillars', 'day', 'stem', default='')
        """
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current
    
    @staticmethod
    def validate_bazi_data(bazi_data: Dict) -> Dict:
        """
        验证并修复八字数据中的类型问题
        
        这是一个中心化的验证函数，用于处理所有可能的类型问题
        
        Args:
            bazi_data: 八字数据
            
        Returns:
            验证并修复后的八字数据
        """
        if not isinstance(bazi_data, dict):
            return {}
        
        # 需要确保是字典类型的字段列表
        dict_fields = [
            'bazi_pillars',
            'details',
            'elements',
            'relationships',
            'element_counts',
            'ten_gods_stats',
            'basic_info'
        ]
        
        # 需要确保是列表类型的字段
        list_fields = [
            'dayun_list',
            'liunian_list'
        ]
        
        # 验证和修复字典类型字段
        for field in dict_fields:
            if field in bazi_data:
                bazi_data[field] = DataValidator.ensure_dict(bazi_data[field])
        
        # 验证和修复列表类型字段
        for field in list_fields:
            if field in bazi_data:
                bazi_data[field] = DataValidator.ensure_list(bazi_data[field])
        
        # ⚠️ 关键修复：递归验证 bazi_pillars 的嵌套结构
        # bazi_pillars 应该是 {'year': {'stem': 'X', 'branch': 'X'}, ...} 格式
        # 但有时可能是 {'year': 'XX', ...} 字符串格式，需要转换
        if 'bazi_pillars' in bazi_data:
            bazi_pillars = bazi_data['bazi_pillars']
            if isinstance(bazi_pillars, dict):
                # 检查每个柱是否是字典格式，如果不是，尝试转换
                for pillar_name in ['year', 'month', 'day', 'hour']:
                    pillar_value = bazi_pillars.get(pillar_name)
                    if isinstance(pillar_value, str) and len(pillar_value) == 2:
                        # 字符串格式（如 "乙酉"），转换为字典格式
                        bazi_pillars[pillar_name] = {
                            'stem': pillar_value[0],
                            'branch': pillar_value[1]
                        }
                    elif not isinstance(pillar_value, dict):
                        # 其他格式或为空，确保是字典格式
                        bazi_pillars[pillar_name] = DataValidator.ensure_dict(pillar_value, default={})
                    elif isinstance(pillar_value, dict):
                        # 已经是字典格式，但确保包含 stem 和 branch
                        if 'stem' not in pillar_value or 'branch' not in pillar_value:
                            # 如果缺少字段，保持原样（可能是其他格式的字典）
                            pass
        
        # 递归验证嵌套结构
        if 'relationships' in bazi_data:
            relationships = bazi_data['relationships']
            if isinstance(relationships, dict):
                if 'branch_relations' in relationships:
                    relationships['branch_relations'] = DataValidator.ensure_dict(
                        relationships['branch_relations']
                    )
        
        if 'details' in bazi_data:
            details = bazi_data['details']
            if isinstance(details, dict):
                for pillar in ['year', 'month', 'day', 'hour']:
                    if pillar in details:
                        details[pillar] = DataValidator.ensure_dict(details[pillar])
        
        return bazi_data
    
    @staticmethod
    def safe_dict_get(data: Any, key: str, default: Any = None) -> Any:
        """
        安全地从数据中获取值（自动处理字符串类型）
        
        Args:
            data: 数据（可能是dict或str）
            key: 键名
            default: 默认值
            
        Returns:
            获取到的值或默认值
        """
        # 确保数据是字典类型
        if not isinstance(data, dict):
            data = DataValidator.ensure_dict(data)
        
        return data.get(key, default)


class TypeGuard:
    """类型守卫 - 用于装饰器"""
    
    @staticmethod
    def ensure_dict_field(*field_names):
        """
        装饰器：确保函数参数中指定的字段是字典类型
        
        Example:
            @TypeGuard.ensure_dict_field('bazi_data', 'ten_gods')
            def my_function(bazi_data, ten_gods):
                # bazi_data 和 ten_gods 会自动转换为字典类型
                pass
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 处理位置参数
                new_args = list(args)
                func_code = func.__code__
                arg_names = func_code.co_varnames[:func_code.co_argcount]
                
                for i, arg_name in enumerate(arg_names):
                    if arg_name in field_names and i < len(new_args):
                        new_args[i] = DataValidator.ensure_dict(new_args[i])
                
                # 处理关键字参数
                for field_name in field_names:
                    if field_name in kwargs:
                        kwargs[field_name] = DataValidator.ensure_dict(kwargs[field_name])
                
                return func(*new_args, **kwargs)
            return wrapper
        return decorator


# 导出常用函数
ensure_dict = DataValidator.ensure_dict
ensure_list = DataValidator.ensure_list
safe_get_nested = DataValidator.safe_get_nested
validate_bazi_data = DataValidator.validate_bazi_data
safe_dict_get = DataValidator.safe_dict_get

__all__ = [
    'DataValidator',
    'TypeGuard',
    'ensure_dict',
    'ensure_list',
    'safe_get_nested',
    'validate_bazi_data',
    'safe_dict_get'
]


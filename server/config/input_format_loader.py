#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input Data格式定义加载器（需求2：input_data格式配置化）
从数据库加载格式定义，根据格式定义从Redis获取数据组装input_data
"""

import json
import time
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

# 添加项目根目录到路径
import sys
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from server.utils.unified_logger import get_unified_logger

logger = get_unified_logger()


class InputDataFormatLoader:
    """Input Data格式定义加载器"""
    
    _instance: Optional['InputDataFormatLoader'] = None
    _format_cache: Dict[str, tuple] = {}  # {format_name: (format_def, timestamp)}
    _cache_ttl: int = 300  # 5分钟缓存
    _lock = None
    
    def __init__(self):
        """初始化格式定义加载器"""
        import threading
        if InputDataFormatLoader._lock is None:
            InputDataFormatLoader._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'InputDataFormatLoader':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_format(self, format_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        加载格式定义
        
        Args:
            format_name: 格式名称
            use_cache: 是否使用缓存
        
        Returns:
            格式定义字典，如果不存在则返回None
        """
        # 1. 查缓存
        if use_cache and format_name in self._format_cache:
            cached_format, cached_time = self._format_cache[format_name]
            if time.time() - cached_time < self._cache_ttl:
                return cached_format
        
        # 2. 查数据库
        try:
            format_def = self._load_from_db(format_name)
            if format_def:
                self._format_cache[format_name] = (format_def, time.time())
                return format_def
        except Exception as e:
            logger.error(f"❌ 加载格式定义失败: {format_name}, 错误: {e}")
        
        return None
    
    def _load_from_db(self, format_name: str) -> Optional[Dict[str, Any]]:
        """从数据库加载格式定义"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT structure, intent, format_type, description, version
                    FROM llm_input_formats 
                    WHERE format_name = %s AND is_active = 1
                    ORDER BY version DESC, id DESC
                    LIMIT 1
                """
                cursor.execute(sql, (format_name,))
                result = cursor.fetchone()
                
                if result:
                    structure = result.get('structure')
                    if isinstance(structure, str):
                        structure = json.loads(structure)
                    
                    return {
                        'format_name': format_name,
                        'intent': result.get('intent'),
                        'format_type': result.get('format_type', 'full'),
                        'structure': structure,
                        'description': result.get('description'),
                        'version': result.get('version', 'v1.0')
                    }
                
                return None
        except Exception as e:
            logger.error(f"❌ 数据库查询失败: {format_name}, 错误: {e}")
            raise
        finally:
            if conn:
                return_mysql_connection(conn)
    
    def build_input_data(
        self,
        format_name: str,
        request_params: Dict[str, Any],
        redis_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        根据格式定义构建input_data
        
        Args:
            format_name: 格式名称
            request_params: 请求参数（包含solar_date, solar_time, gender, intent, question等）
            redis_client: Redis客户端（可选，如果为None则尝试自动获取）
        
        Returns:
            组装好的input_data字典
        """
        # 1. 加载格式定义
        format_def = self.load_format(format_name)
        if not format_def:
            raise ValueError(f"格式定义不存在: {format_name}")
        
        structure = format_def.get('structure', {})
        fields = structure.get('fields', {})
        
        # 2. 获取Redis客户端
        if redis_client is None:
            redis_client = self._get_redis_client()
        
        # 3. 根据格式定义组装input_data
        input_data = {}
        
        for field_name, field_config in fields.items():
            source = field_config.get('source')
            
            if source == 'request_param':
                # 从请求参数获取
                param_field = field_config.get('field')
                value = request_params.get(param_field)
                if value is not None or not field_config.get('optional', False):
                    input_data[field_name] = value
            
            elif source == 'redis':
                # 从Redis获取
                key_template = field_config.get('key_template')
                if key_template:
                    # 替换模板变量
                    redis_key = self._replace_template_vars(key_template, request_params)
                    
                    # 从Redis获取数据
                    redis_data = self._get_from_redis(redis_client, redis_key)
                    
                    if redis_data:
                        # 提取指定字段
                        target_fields = field_config.get('fields', [])
                        if target_fields:
                            # 提取多个字段
                            field_data = {}
                            for target_field in target_fields:
                                if target_field in redis_data:
                                    value = redis_data[target_field]
                                    
                                    # 应用转换
                                    transform = field_config.get('transform', {})
                                    if target_field in transform:
                                        value = self._apply_transform(value, transform[target_field])
                                    
                                    field_data[target_field] = value
                            
                            input_data[field_name] = field_data
                        else:
                            # 直接使用整个数据
                            input_data[field_name] = redis_data
                    else:
                        # Redis中没有数据，使用默认值或跳过
                        if not field_config.get('optional', False):
                            input_data[field_name] = field_config.get('default', {})
            
            elif source == 'static':
                # 静态值
                input_data[field_name] = field_config.get('value')
            
            elif source == 'calculated':
                # 计算值（调用计算函数）
                func_name = field_config.get('function')
                func_params = field_config.get('params', [])
                params = [request_params.get(p) for p in func_params]
                input_data[field_name] = self._call_calculator(func_name, params)
        
        return input_data
    
    def build_input_data_from_result(
        self,
        format_def: Dict[str, Any],
        bazi_data: Dict[str, Any],
        detail_result: Dict[str, Any],
        wangshuai_result: Optional[Dict[str, Any]] = None,
        rule_result: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        根据格式定义从计算结果直接组装 input_data（不依赖 Redis）
        
        Args:
            format_def: 格式定义字典（从 load_format 获取）
            bazi_data: 基础八字数据
            detail_result: 详细计算结果（包含大运流年等）
            wangshuai_result: 旺衰计算结果（可选）
            rule_result: 规则匹配结果（可选）
            **kwargs: 其他数据源
        
        Returns:
            组装好的 input_data 字典
        """
        if not format_def:
            raise ValueError("格式定义不能为空")
        
        structure = format_def.get('structure', {})
        fields = structure.get('fields', {})
        
        # 构建数据源映射
        data_sources = {
            'bazi_data': bazi_data,
            'detail_result': detail_result,
            'wangshuai_result': wangshuai_result or {},
            'rule_result': rule_result or {},
            **kwargs
        }
        
        input_data = {}
        
        for field_name, field_config in fields.items():
            source = field_config.get('source')
            
            if source == 'result':
                # 从计算结果提取
                data_source = field_config.get('data_source', 'detail_result')  # 默认从 detail_result
                source_data = data_sources.get(data_source, {})
                
                # 提取指定字段
                target_fields = field_config.get('fields', [])
                if target_fields:
                    # 提取多个字段
                    field_data = {}
                    for target_field in target_fields:
                        value = self._extract_nested_field(source_data, target_field)
                        if value is not None:
                            # 应用转换
                            transform = field_config.get('transform', {})
                            if target_field in transform:
                                value = self._apply_transform(value, transform[target_field])
                            field_data[target_field] = value
                    input_data[field_name] = field_data
                else:
                    # 提取单个字段或整个数据源
                    field_path = field_config.get('field')
                    if field_path:
                        value = self._extract_nested_field(source_data, field_path)
                        if value is not None:
                            input_data[field_name] = value
                    else:
                        # 使用整个数据源
                        input_data[field_name] = source_data
            
            elif source == 'calculated':
                # 计算值（调用计算函数）
                func_name = field_config.get('function')
                func_params = field_config.get('params', [])
                params = [data_sources.get(p, {}) for p in func_params]
                input_data[field_name] = self._call_calculator(func_name, params)
            
            elif source == 'static':
                # 静态值
                input_data[field_name] = field_config.get('value')
            
            elif source == 'composite':
                # 复合字段：从多个数据源组合
                composite_config = field_config.get('composite', {})
                composite_data = {}
                for comp_field, comp_config in composite_config.items():
                    comp_source = comp_config.get('data_source', 'detail_result')
                    comp_path = comp_config.get('field')
                    if comp_source in data_sources and comp_path:
                        value = self._extract_nested_field(data_sources[comp_source], comp_path)
                        if value is not None:
                            composite_data[comp_field] = value
                input_data[field_name] = composite_data
        
        return input_data
    
    def _extract_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        从嵌套字典中提取字段（支持点号分隔的路径）
        
        Args:
            data: 数据字典
            field_path: 字段路径，如 "dayun_sequence.0.year_start"
        
        Returns:
            字段值，如果不存在则返回 None
        """
        if not field_path:
            return None
        
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                except ValueError:
                    return None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _replace_template_vars(self, template: str, params: Dict[str, Any]) -> str:
        """替换模板变量"""
        result = template
        for key, value in params.items():
            result = result.replace(f'{{{key}}}', str(value))
        return result
    
    def _get_redis_client(self) -> Optional[Any]:
        """获取Redis客户端"""
        try:
            from server.config.redis_config import get_redis_pool
            redis_pool = get_redis_pool()
            if redis_pool:
                return redis_pool.get_connection()
        except Exception as e:
            logger.warning(f"⚠️ 获取Redis客户端失败: {e}")
        return None
    
    def _get_from_redis(self, redis_client: Optional[Any], key: str) -> Optional[Dict[str, Any]]:
        """从Redis获取数据"""
        if not redis_client:
            return None
        
        try:
            value = redis_client.get(key)
            if value:
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                if isinstance(value, str):
                    return json.loads(value)
                return value
        except Exception as e:
            logger.warning(f"⚠️ 从Redis获取数据失败: {key}, 错误: {e}")
        
        return None
    
    def _apply_transform(self, value: Any, transform: str) -> Any:
        """应用数据转换"""
        if transform.startswith('slice:'):
            # slice:0:5
            parts = transform.split(':')
            if len(parts) == 3:
                start = int(parts[1])
                end = int(parts[2])
                if isinstance(value, (list, str)):
                    return value[start:end]
        return value
    
    def _call_calculator(self, func_name: str, params: List[Any]) -> Any:
        """调用计算函数"""
        # 这里可以根据需要实现各种计算函数
        # 例如：提取年份、计算摘要等
        return None
    
    def reload_format(self, format_name: Optional[str] = None):
        """
        重新加载格式定义（热更新）
        
        Args:
            format_name: 要重新加载的格式名称，如果为None则清空所有缓存
        """
        with self._lock:
            if format_name:
                if format_name in self._format_cache:
                    del self._format_cache[format_name]
                logger.info(f"✓ 已清除格式定义缓存: {format_name}")
            else:
                self._format_cache.clear()
                logger.info("✓ 已清除所有格式定义缓存")
    
    def get_format_by_intent(self, intent: str, format_type: str = 'full') -> Optional[Dict[str, Any]]:
        """
        根据意图获取格式定义
        
        Args:
            intent: 意图类型
            format_type: 格式类型（full/minimal/custom）
        
        Returns:
            格式定义字典
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    SELECT format_name, structure, format_type, description, version
                    FROM llm_input_formats 
                    WHERE intent = %s AND format_type = %s AND is_active = 1
                    ORDER BY version DESC, id DESC
                    LIMIT 1
                """
                cursor.execute(sql, (intent, format_type))
                result = cursor.fetchone()
                
                if result:
                    format_name = result.get('format_name')
                    return self.load_format(format_name)
                
                return None
        except Exception as e:
            logger.error(f"❌ 根据意图获取格式定义失败: {intent}, {format_type}, 错误: {e}")
            return None
        finally:
            if conn:
                return_mysql_connection(conn)


# 全局格式定义加载器实例
_format_loader: Optional[InputDataFormatLoader] = None


def get_format_loader() -> InputDataFormatLoader:
    """获取格式定义加载器实例"""
    global _format_loader
    if _format_loader is None:
        _format_loader = InputDataFormatLoader.get_instance()
    return _format_loader


def build_input_data(
    format_name: str,
    request_params: Dict[str, Any],
    redis_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    根据格式定义构建input_data（便捷函数）
    
    Args:
        format_name: 格式名称
        request_params: 请求参数
        redis_client: Redis客户端（可选）
    
    Returns:
        组装好的input_data字典
    """
    return get_format_loader().build_input_data(format_name, request_params, redis_client)


def build_input_data_from_result(
    format_name: str,
    bazi_data: Dict[str, Any],
    detail_result: Dict[str, Any],
    wangshuai_result: Optional[Dict[str, Any]] = None,
    rule_result: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    根据格式定义从计算结果直接组装 input_data（便捷函数）
    
    Args:
        format_name: 格式名称
        bazi_data: 基础八字数据
        detail_result: 详细计算结果
        wangshuai_result: 旺衰计算结果（可选）
        rule_result: 规则匹配结果（可选）
        **kwargs: 其他数据源
    
    Returns:
        组装好的 input_data 字典
    """
    format_loader = get_format_loader()
    format_def = format_loader.load_format(format_name)
    if not format_def:
        raise ValueError(f"格式定义不存在: {format_name}")
    
    return format_loader.build_input_data_from_result(
        format_def=format_def,
        bazi_data=bazi_data,
        detail_result=detail_result,
        wangshuai_result=wangshuai_result,
        rule_result=rule_result,
        **kwargs
    )


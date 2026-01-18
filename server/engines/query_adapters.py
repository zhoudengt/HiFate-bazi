#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询适配器模块 - 支持动态查询规则内容
"""

import sys
import os
from typing import Dict, Any, Optional, Callable

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


class QueryAdapterRegistry:
    """查询适配器注册表"""
    
    _adapters = {}
    _cached_version = 0
    _check_counter = 0
    _content_cache = {}  # 内容缓存
    
    @classmethod
    def register(cls, adapter_name: str, adapter_class: type, query_method: str = None):
        """
        注册查询适配器
        
        Args:
            adapter_name: 适配器名称
            adapter_class: 适配器类
            query_method: 查询方法名（默认使用 analyze_* 方法）
        """
        cls._adapters[adapter_name] = {
            'class': adapter_class,
            'query_method': query_method
        }
    
    @classmethod
    def get_adapter(cls, adapter_name: str) -> Optional[Dict]:
        """获取适配器"""
        return cls._adapters.get(adapter_name)
    
    @classmethod
    def query(cls, adapter_name: str, bazi_data: Dict, **kwargs) -> Any:
        """
        调用适配器查询
        
        Args:
            adapter_name: 适配器名称
            bazi_data: 八字数据
            **kwargs: 额外参数
            
        Returns:
            查询结果
        """
        # 每100次请求检查一次版本号（减少数据库压力）
        cls._check_counter += 1
        if cls._check_counter % 100 == 0:
            cls._check_version()
        
        adapter_info = cls.get_adapter(adapter_name)
        if not adapter_info:
            return None
        
        adapter_class = adapter_info['class']
        query_method = adapter_info.get('query_method')
        
        try:
            # 创建适配器实例
            if adapter_name == 'RizhuGenderAnalyzer':
                # RizhuGenderAnalyzer 需要 bazi_pillars 和 gender
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                gender = bazi_data.get('basic_info', {}).get('gender', 'male')
                
                # 优先从数据库查询
                result = cls._query_from_database(bazi_pillars, gender)
                if result:
                    return result
                
                # 数据库没有，使用配置文件（原有逻辑）
                adapter = adapter_class(bazi_pillars, gender)
            elif adapter_name == 'DeitiesAnalyzer':
                # DeitiesAnalyzer 需要 bazi_pillars, details, gender
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                details = bazi_data.get('details', {})
                gender = bazi_data.get('basic_info', {}).get('gender', 'male')
                adapter = adapter_class(bazi_pillars, details, gender)
            else:
                # 其他适配器，尝试通用初始化
                adapter = adapter_class(bazi_data, **kwargs)
            
            # 调用查询方法
            if query_method:
                method = getattr(adapter, query_method, None)
                if method:
                    return method()
            else:
                # 尝试自动查找方法
                if hasattr(adapter, 'analyze_rizhu_gender'):
                    return adapter.analyze_rizhu_gender()
                elif hasattr(adapter, 'analyze_all_deities_rules'):
                    return adapter.analyze_all_deities_rules()
                elif hasattr(adapter, 'get_formatted_output'):
                    return adapter.get_formatted_output()
            
            return None
            
        except Exception as e:
            print(f"查询适配器 {adapter_name} 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @classmethod
    def _query_from_database(cls, bazi_pillars: Dict, gender: str) -> Optional[Dict]:
        """
        从数据库查询日柱性别内容
        
        Args:
            bazi_pillars: 八字四柱数据
            gender: 性别
            
        Returns:
            Dict: 查询结果，如果数据库没有则返回None
        """
        try:
            day_stem = bazi_pillars.get('day', {}).get('stem', '')
            day_branch = bazi_pillars.get('day', {}).get('branch', '')
            rizhu = f"{day_stem}{day_branch}"
            
            # 检查缓存
            cache_key = f"{rizhu}_{gender}"
            if cache_key in cls._content_cache:
                return cls._content_cache[cache_key]
            
            # 从数据库查询
            from server.db.rule_content_dao import RuleContentDAO
            descriptions = RuleContentDAO.get_rizhu_gender_content(rizhu, gender)
            
            if descriptions:
                result = {
                    'rizhu': rizhu,
                    'gender': gender,
                    'descriptions': descriptions,
                    'has_data': True,
                    'source': 'database'
                }
                # 缓存结果
                cls._content_cache[cache_key] = result
                return result
            
            return None
        except Exception as e:
            # 数据库查询失败，不抛出异常，回退到配置文件
            print(f"⚠ 数据库查询失败，使用配置文件: {e}")
            return None
    
    @classmethod
    def _check_version(cls):
        """检查版本号并重新加载（使用统一的热更新管理器）"""
        try:
            # 使用统一的热更新管理器
            from server.hot_reload.hot_reload_manager import HotReloadManager
            manager = HotReloadManager.get_instance()
            manager.check_and_reload('content')
        except Exception:
            # 降级到原来的逻辑
            try:
                from server.db.rule_content_dao import RuleContentDAO
                current_version = RuleContentDAO.get_content_version()
                
                if current_version > cls._cached_version:
                    # 清空缓存
                    cls._content_cache.clear()
                    cls._cached_version = current_version
                    print(f"✓ 检测到版本号变化，已清空缓存: {current_version}")
            except Exception as e:
                print(f"⚠ 检查版本号失败: {e}")


# 注册现有的分析器作为查询适配器
def register_default_adapters():
    """注册默认的查询适配器"""
    try:
        from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
        QueryAdapterRegistry.register(
            'RizhuGenderAnalyzer',
            RizhuGenderAnalyzer,
            'analyze_rizhu_gender'
        )
        print("✓ 注册查询适配器: RizhuGenderAnalyzer")
    except Exception as e:
        print(f"⚠ 注册 RizhuGenderAnalyzer 失败: {e}")
    
    try:
        from core.analyzers.deities_analyzer import DeitiesAnalyzer
        QueryAdapterRegistry.register(
            'DeitiesAnalyzer',
            DeitiesAnalyzer,
            'analyze_all_deities_rules'
        )
        print("✓ 注册查询适配器: DeitiesAnalyzer")
    except Exception as e:
        print(f"⚠ 注册 DeitiesAnalyzer 失败: {e}")


# 自动注册默认适配器
register_default_adapters()


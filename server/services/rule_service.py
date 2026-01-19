#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则服务层 - 提供规则匹配服务
"""

import sys
import os
import threading
import time
import logging
from typing import Dict, List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.engines.rule_engine import EnhancedRuleEngine
from server.engines.query_adapters import QueryAdapterRegistry
from server.utils.cache_multi_level import get_multi_cache
from server.config.mysql_config import mysql_config

logger = logging.getLogger(__name__)


class RuleReloader:
    """规则自动刷新器"""
    
    def __init__(self, interval: int = 300):  # 默认5分钟
        self.interval = interval
        self.running = False
        self.thread = None
    
    def start(self):
        """启动自动刷新"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._reload_loop, daemon=True)
        self.thread.start()
        logger.info(f"✓ 规则自动刷新器已启动（间隔: {self.interval}秒）")
    
    def stop(self):
        """停止自动刷新"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _reload_loop(self):
        """自动刷新循环"""
        while self.running:
            time.sleep(self.interval)
            try:
                # 检查版本号
                from server.db.rule_content_dao import RuleContentDAO
                current_version = RuleContentDAO.get_content_version()
                
                if current_version > RuleService._cached_content_version:
                    # 清空查询适配器缓存
                    QueryAdapterRegistry._content_cache.clear()
                    QueryAdapterRegistry._cached_version = current_version
                    RuleService._cached_content_version = current_version
                    logger.info(f"✓ 规则内容自动刷新: {time.strftime('%Y-%m-%d %H:%M:%S')} (版本: {current_version})")
                
                # 检查规则版本号
                current_rule_version = RuleContentDAO.get_rule_version()
                if current_rule_version > RuleService._cached_rule_version:
                    RuleService.reload_rules()
                    RuleService._cached_rule_version = current_rule_version
                    logger.info(f"✓ 规则自动刷新: {time.strftime('%Y-%m-%d %H:%M:%S')} (版本: {current_rule_version})")
                    
            except Exception as e:
                logger.warning(f"⚠ 规则刷新失败: {e}")


class RuleService:
    """规则服务类"""
    
    _engine: Optional[EnhancedRuleEngine] = None
    _cache = None
    _reloader: Optional[RuleReloader] = None
    _cached_content_version = 0
    _cached_rule_version = 0
    
    @classmethod
    def get_engine(cls) -> EnhancedRuleEngine:
        """获取规则引擎实例（单例模式）"""
        if cls._engine is None:
            cls._engine = EnhancedRuleEngine(use_index=True)
            
            # 优先从数据库加载规则
            db_rules_loaded = False
            try:
                from server.db.mysql_connector import get_db_connection
                db = get_db_connection()
                # 从数据库加载规则
                rules = db.execute_query("SELECT * FROM bazi_rules WHERE enabled = 1 ORDER BY priority DESC")
                
                if rules and len(rules) > 0:
                    health_rule_count = 0
                    
                    def fix_encoding_in_dict(obj):
                        """递归修复字典中的编码问题"""
                        if isinstance(obj, dict):
                            return {k: fix_encoding_in_dict(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [fix_encoding_in_dict(item) for item in obj]
                        elif isinstance(obj, str):
                            try:
                                return obj.encode('latin1').decode('utf-8')
                            except (UnicodeDecodeError, UnicodeEncodeError):
                                return obj
                        else:
                            return obj
                    
                    for rule in rules:
                        # 处理 JSON 字段
                        conditions = rule['conditions']
                        if isinstance(conditions, str):
                            import json
                            # 修复字符编码问题（pymysql以latin1读取UTF-8数据）
                            try:
                                conditions = conditions.encode('latin1').decode('utf-8')
                            except (UnicodeDecodeError, UnicodeEncodeError):
                                pass  # 如果编码转换失败，使用原始字符串
                            conditions = json.loads(conditions)
                        elif isinstance(conditions, dict):
                            # 如果已经是字典，递归修复编码
                            conditions = fix_encoding_in_dict(conditions)
                        
                        content = rule['content']
                        if isinstance(content, str):
                            import json
                            content = json.loads(content)
                        
                        rule_dict = {
                            'rule_id': rule['rule_code'],
                            'rule_name': rule['rule_name'],
                            'rule_type': rule['rule_type'],
                            'rule_category': rule.get('rule_category'),  # 添加 rule_category
                            'priority': rule['priority'],
                            'conditions': conditions,
                            'content': content,
                            'enabled': rule['enabled'],
                            'description': rule.get('description', ''),
                            # 置信度和权重字段
                            'confidence_prior': float(rule.get('confidence_prior', 0.6)) if rule.get('confidence_prior') is not None else 0.6,
                            'mutually_exclusive_group': rule.get('mutually_exclusive_group'),
                            'contradicts': rule.get('contradicts', []),
                            'tags': rule.get('tags', []),
                            'segment_weights': rule.get('segment_weights', {}),
                            'biz_impact_weight': float(rule.get('biz_impact_weight', 1.0)) if rule.get('biz_impact_weight') is not None else 1.0,
                            'history_score': float(rule.get('history_score', 0.5)) if rule.get('history_score') is not None else 0.5,
                        }
                        cls._engine.add_rule(rule_dict)
                    
                        # 调试：统计health类型规则
                        if rule['rule_type'] == 'health' and rule['rule_code'].startswith('FORMULA_70'):
                            health_rule_count += 1
                    
                    logger.info(f"✓ 从数据库加载规则: {len(rules)} 条 (health类型FORMULA_70xxx: {health_rule_count}条)")
                    db_rules_loaded = True
            except Exception as e:
                logger.error(f"⚠ 从数据库加载规则失败: {e}", exc_info=True)
                if not db_rules_loaded:
                    raise RuntimeError(
                        "规则必须从数据库加载，数据库连接失败。"
                        "请检查数据库连接和规则数据。"
                    )
        
        return cls._engine
    
    @classmethod
    def get_cache(cls):
        """获取缓存实例"""
        if cls._cache is None:
            cls._cache = get_multi_cache()
        return cls._cache
    
    @classmethod
    def match_rules(cls, bazi_data: Dict, rule_types: List[str] = None, use_cache: bool = True) -> List[Dict]:
        """
        匹配规则
        
        Args:
            bazi_data: 八字数据（完整的八字计算结果）
            rule_types: 要匹配的规则类型列表
            use_cache: 是否使用缓存
            
        Returns:
            List[Dict]: 匹配的规则列表
        """
        # 生成缓存键
        cache_key = cls._generate_cache_key(bazi_data, rule_types)
        
        # 检查缓存
        if use_cache:
            cache = cls.get_cache()
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        # 匹配规则
        engine = cls.get_engine()
        matched_rules = engine.match_rules(bazi_data, rule_types)
        
        # 格式化规则结果（支持动态查询）
        formatted_rules = []
        for rule in matched_rules:
            rule_content = rule.get('content', {})
            
            # 检查是否是动态查询规则
            if rule_content.get('type') == 'dynamic':
                # 动态查询规则：调用查询适配器获取内容
                adapter_name = rule_content.get('query_adapter')
                if adapter_name:
                    query_result = QueryAdapterRegistry.query(adapter_name, bazi_data)
                    if query_result:
                        # 根据适配器返回的结果格式化内容
                        if adapter_name == 'RizhuGenderAnalyzer':
                            # RizhuGenderAnalyzer 返回的是字典格式
                            if isinstance(query_result, dict):
                                descriptions = query_result.get('descriptions', [])
                                formatted_content = {
                                    "type": "description",
                                    "items": [
                                        {"type": "description", "text": desc}
                                        for desc in descriptions
                                    ]
                                }
                            else:
                                formatted_content = {
                                    "type": "description",
                                    "text": str(query_result)
                                }
                        else:
                            # 其他适配器，尝试格式化
                            formatted_content = {
                                "type": "description",
                                "text": str(query_result)
                            }
                        rule_content = formatted_content
                    else:
                        # 查询失败，使用默认内容
                        rule_content = rule_content.get('default_content', {})
            
            formatted_rule = {
                "rule_id": rule.get('rule_id', ''),
                "rule_code": rule.get('rule_id', ''),
                "rule_name": rule.get('rule_name', ''),
                "rule_type": rule.get('rule_type', ''),
                "priority": rule.get('priority', 100),
                "content": rule_content,
                "description": rule.get('description', '')
            }
            
            # 添加置信度和权重信息
            if rule.get('confidence_prior') is not None:
                formatted_rule['confidence'] = float(rule.get('confidence_prior', 0.6))
            if rule.get('history_score') is not None:
                formatted_rule['history_score'] = float(rule.get('history_score', 0.5))
            if rule.get('tags'):
                formatted_rule['tags'] = rule.get('tags')
            
            formatted_rules.append(formatted_rule)
        
        # 缓存结果
        if use_cache and formatted_rules:
            cache = cls.get_cache()
            cache.set(cache_key, formatted_rules)
        
        return formatted_rules
    
    @classmethod
    def _generate_cache_key(cls, bazi_data: Dict, rule_types: List[str] = None) -> str:
        """生成缓存键"""
        import hashlib
        import json
        
        # 提取关键信息
        key_parts = [
            bazi_data.get('basic_info', {}).get('solar_date', ''),
            bazi_data.get('basic_info', {}).get('solar_time', ''),
            bazi_data.get('basic_info', {}).get('gender', ''),
        ]
        
        # 添加四柱信息
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_data.get('bazi_pillars', {}).get(pillar_type, {})
            key_parts.append(f"{pillar.get('stem', '')}{pillar.get('branch', '')}")
        
        # 添加规则类型
        if rule_types:
            key_parts.append(str(sorted(rule_types)))
        
        key_str = ':'.join(key_parts)
        return f"bazi:rules:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    @classmethod
    def reload_rules(cls):
        """重新加载规则"""
        cls._engine = None
        return cls.get_engine()
    
    @classmethod
    def start_auto_reload(cls, interval: int = 300):
        """启动自动刷新（热加载）"""
        if cls._reloader is None:
            cls._reloader = RuleReloader(interval)
            cls._reloader.start()
            
            # 初始化版本号
            try:
                from server.db.rule_content_dao import RuleContentDAO
                cls._cached_content_version = RuleContentDAO.get_content_version()
                cls._cached_rule_version = RuleContentDAO.get_rule_version()
                QueryAdapterRegistry._cached_version = cls._cached_content_version
            except Exception as e:
                logger.warning(f"⚠ 初始化版本号失败: {e}")
    
    @classmethod
    def check_and_reload(cls) -> bool:
        """
        检查并重新加载（如果版本号变化）
        非阻塞，快速检查
        
        注意：此方法已被热更新管理器替代，保留用于兼容
        """
        try:
            # 使用统一的热更新管理器
            from server.hot_reload.hot_reload_manager import HotReloadManager
            manager = HotReloadManager.get_instance()
            return manager.check_and_reload()
        except Exception:
            # 降级到原来的逻辑
            try:
                from server.db.rule_content_dao import RuleContentDAO
                current_content_version = RuleContentDAO.get_content_version()
                current_rule_version = RuleContentDAO.get_rule_version()
                
                reloaded = False
                
                # 检查内容版本号
                if current_content_version > cls._cached_content_version:
                    QueryAdapterRegistry._content_cache.clear()
                    QueryAdapterRegistry._cached_version = current_content_version
                    cls._cached_content_version = current_content_version
                    reloaded = True
                
                # 检查规则版本号
                if current_rule_version > cls._cached_rule_version:
                    cls.reload_rules()
                    cls._cached_rule_version = current_rule_version
                    reloaded = True
                
                return reloaded
            except Exception as e:
                # 忽略错误，不影响主流程
                return False


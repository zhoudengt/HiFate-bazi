# -*- coding: utf-8 -*-
"""
规则查询客户端

查询指定类目下的所有规则（用于计算未匹配规则）
"""

import sys
import os
import json
from typing import List, Dict, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from server.db.mysql_connector import get_db_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    get_db_connection = None


class RuleQueryClient:
    """规则查询客户端"""
    
    @classmethod
    def get_rules_by_type(cls, rule_types: List[str]) -> List[Dict]:
        """
        获取指定 rule_type 下的所有规则
        
        Args:
            rule_types: rule_type 列表，如 ["wealth", "career"]
            
        Returns:
            规则列表，每个规则包含 rule_code, rule_name, rule_type, content 等字段
        """
        if not DB_AVAILABLE:
            return []
        
        if not rule_types:
            return []
        
        try:
            db = get_db_connection()
            
            # 构建 SQL 查询（使用 IN 子句）
            placeholders = ','.join(['%s'] * len(rule_types))
            sql = f"""
                SELECT rule_code, rule_name, rule_type, content, description
                FROM bazi_rules
                WHERE rule_type IN ({placeholders}) AND enabled = 1
                ORDER BY rule_type, priority DESC
            """
            
            rules = db.execute_query(sql, tuple(rule_types))
            
            # 处理 JSON 字段
            result = []
            for rule in rules:
                content = rule.get('content', {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except:
                        content = {}
                
                result.append({
                    'rule_code': rule.get('rule_code', ''),
                    'rule_name': rule.get('rule_name', ''),
                    'rule_type': rule.get('rule_type', ''),
                    'content': content,
                    'description': rule.get('description', ''),
                })
            
            return result
            
        except Exception as e:
            print(f"⚠ 查询规则失败: {e}")
            return []
    
    @classmethod
    def extract_rule_text(cls, rule: Dict) -> str:
        """
        从规则中提取文本内容
        
        Args:
            rule: 规则字典
            
        Returns:
            规则文本内容
        """
        content = rule.get('content', {})
        
        if isinstance(content, dict):
            # 尝试提取 text 字段
            if 'text' in content:
                return content['text']
            # 尝试提取 items
            if 'items' in content and isinstance(content['items'], list):
                texts = []
                for item in content['items']:
                    if isinstance(item, dict) and 'text' in item:
                        texts.append(item['text'])
                if texts:
                    return '\n'.join(texts)
        
        # 如果没有文本，返回 description
        description = rule.get('description', '')
        if description:
            return description
        
        return ''

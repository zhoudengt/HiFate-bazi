#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则内容数据访问对象
负责规则内容的数据库操作
"""

import json
import logging

logger = logging.getLogger(__name__)
import sys
import os
from typing import List, Optional, Dict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.db.mysql_connector import get_db_connection


class RuleContentDAO:
    """规则内容数据访问对象"""
    
    @staticmethod
    def get_rizhu_gender_content(rizhu: str, gender: str) -> List[str]:
        """
        从数据库查询日柱性别内容
        
        Args:
            rizhu: 日柱，如 '甲子'
            gender: 性别，'male' 或 'female'
            
        Returns:
            List[str]: 描述列表，如果找不到返回空列表
        """
        try:
            db = get_db_connection()
            sql = """
                SELECT descriptions 
                FROM rizhu_gender_contents 
                WHERE rizhu = %s AND gender = %s AND enabled = 1
            """
            result = db.execute_query(sql, (rizhu, gender))
            if result and result[0].get('descriptions'):
                # MySQL 返回的 JSON 可能是字符串或已解析的字典
                descriptions = result[0]['descriptions']
                if isinstance(descriptions, str):
                    return json.loads(descriptions)
                elif isinstance(descriptions, list):
                    return descriptions
            return []
        except Exception as e:
            logger.info(f"⚠ 查询日柱性别内容失败: {e}")
            return []
    
    @staticmethod
    def get_content_version() -> int:
        """
        获取内容版本号
        
        Returns:
            int: 内容版本号
        """
        try:
            db = get_db_connection()
            result = db.execute_query("SELECT content_version FROM rule_version LIMIT 1")
            if result and result[0].get('content_version'):
                return int(result[0]['content_version'])
            return 1
        except Exception as e:
            logger.info(f"⚠ 获取版本号失败: {e}")
            return 1
    
    @staticmethod
    def get_rule_version() -> int:
        """
        获取规则版本号
        
        Returns:
            int: 规则版本号
        """
        try:
            db = get_db_connection()
            result = db.execute_query("SELECT rule_version FROM rule_version LIMIT 1")
            if result and result[0].get('rule_version'):
                return int(result[0]['rule_version'])
            return 1
        except Exception as e:
            logger.info(f"⚠ 获取规则版本号失败: {e}")
            return 1
    
    @staticmethod
    def update_content_version():
        """更新内容版本号（更新内容时调用）"""
        try:
            db = get_db_connection()
            db.execute_update(
                "UPDATE rule_version SET content_version = content_version + 1"
            )
            logger.info("✓ 内容版本号已更新")
            return True
        except Exception as e:
            logger.info(f"⚠ 更新内容版本号失败: {e}")
            return False
    
    @staticmethod
    def update_rule_version():
        """更新规则版本号（更新规则时调用）"""
        try:
            db = get_db_connection()
            db.execute_update(
                "UPDATE rule_version SET rule_version = rule_version + 1"
            )
            logger.info("✓ 规则版本号已更新")
            return True
        except Exception as e:
            logger.info(f"⚠ 更新规则版本号失败: {e}")
            return False
    
    @staticmethod
    def save_rizhu_gender_content(rizhu: str, gender: str, descriptions: List[str]) -> bool:
        """
        保存日柱性别内容
        
        Args:
            rizhu: 日柱
            gender: 性别
            descriptions: 描述列表
            
        Returns:
            bool: 是否成功
        """
        try:
            db = get_db_connection()
            sql = """
                INSERT INTO rizhu_gender_contents (rizhu, gender, descriptions)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    descriptions = VALUES(descriptions),
                    version = version + 1,
                    updated_at = NOW()
            """
            db.execute_update(sql, (
                rizhu, 
                gender, 
                json.dumps(descriptions, ensure_ascii=False)
            ))
            # 更新版本号
            RuleContentDAO.update_content_version()
            return True
        except Exception as e:
            logger.info(f"⚠ 保存日柱性别内容失败: {e}")
            return False
    
    @staticmethod
    def batch_save_rizhu_gender_contents(contents: List[Dict]) -> int:
        """
        批量保存日柱性别内容（单次批量 INSERT，避免 N+1 查询）。
        
        Args:
            contents: 内容列表，格式：[{'rizhu': '甲子', 'gender': 'male', 'descriptions': [...]}, ...]
            
        Returns:
            int: 成功保存的数量
        """
        if not contents:
            return 0
        try:
            db = get_db_connection()
            placeholders = ", ".join(["(%s, %s, %s)"] * len(contents))
            sql = (
                "INSERT INTO rizhu_gender_contents (rizhu, gender, descriptions) "
                "VALUES " + placeholders + """
                ON DUPLICATE KEY UPDATE
                    descriptions = VALUES(descriptions),
                    version = version + 1,
                    updated_at = NOW()
            """
            )
            params = []
            for c in contents:
                params.extend([
                    c['rizhu'],
                    c['gender'],
                    json.dumps(c['descriptions'], ensure_ascii=False),
                ])
            db.execute_update(sql, tuple(params))
            RuleContentDAO.update_content_version()
            return len(contents)
        except Exception as e:
            logger.warning("批量保存日柱性别内容失败: %s", e)
            return 0
    
    @staticmethod
    def get_all_rizhu_gender_contents() -> List[Dict]:
        """
        获取所有日柱性别内容
        
        Returns:
            List[Dict]: 内容列表
        """
        try:
            db = get_db_connection()
            sql = """
                SELECT rizhu, gender, descriptions, enabled, version
                FROM rizhu_gender_contents
                ORDER BY rizhu, gender
            """
            result = db.execute_query(sql)
            contents = []
            for row in result:
                descriptions = row['descriptions']
                if isinstance(descriptions, str):
                    descriptions = json.loads(descriptions)
                contents.append({
                    'rizhu': row['rizhu'],
                    'gender': row['gender'],
                    'descriptions': descriptions,
                    'enabled': bool(row['enabled']),
                    'version': row['version']
                })
            return contents
        except Exception as e:
            logger.info(f"⚠ 获取所有内容失败: {e}")
            return []
    
    @staticmethod
    def disable_rizhu_gender_content(rizhu: str, gender: str) -> bool:
        """
        禁用日柱性别内容
        
        Args:
            rizhu: 日柱
            gender: 性别
            
        Returns:
            bool: 是否成功
        """
        try:
            db = get_db_connection()
            sql = """
                UPDATE rizhu_gender_contents 
                SET enabled = 0, version = version + 1
                WHERE rizhu = %s AND gender = %s
            """
            db.execute_update(sql, (rizhu, gender))
            RuleContentDAO.update_content_version()
            return True
        except Exception as e:
            logger.info(f"⚠ 禁用内容失败: {e}")
            return False
    
    @staticmethod
    def enable_rizhu_gender_content(rizhu: str, gender: str) -> bool:
        """
        启用日柱性别内容
        
        Args:
            rizhu: 日柱
            gender: 性别
            
        Returns:
            bool: 是否成功
        """
        try:
            db = get_db_connection()
            sql = """
                UPDATE rizhu_gender_contents 
                SET enabled = 1, version = version + 1
                WHERE rizhu = %s AND gender = %s
            """
            db.execute_update(sql, (rizhu, gender))
            RuleContentDAO.update_content_version()
            return True
        except Exception as e:
            logger.info(f"⚠ 启用内容失败: {e}")
            return False









































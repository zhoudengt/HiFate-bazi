#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日元-六十甲子服务 - 根据日柱查询解析内容
"""

import sys
import os
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection


class RizhuLiujiaziService:
    """日元-六十甲子服务"""
    
    @staticmethod
    def get_rizhu_analysis(rizhu: str) -> Optional[Dict[str, Any]]:
        """
        根据日柱查询解析内容
        
        Args:
            rizhu: 日柱（如：乙丑）
            
        Returns:
            dict: 包含 id, rizhu, analysis 的字典，如果未找到返回 None
        """
        if not rizhu:
            return None
        
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None
            
            with conn.cursor() as cursor:
                # 使用 BINARY 比较确保精确匹配（遵循数据库编码规范）
                cursor.execute("""
                    SELECT id, rizhu, analysis, enabled
                    FROM rizhu_liujiazi
                    WHERE BINARY rizhu = %s AND enabled = TRUE
                    LIMIT 1
                """, (rizhu,))
                
                result = cursor.fetchone()
                
                if result:
                    # DictCursor 返回字典，使用键访问
                    return {
                        'id': result.get('id'),
                        'rizhu': result.get('rizhu'),
                        'analysis': result.get('analysis'),
                        'enabled': bool(result.get('enabled', True))
                    }
                else:
                    return None
                    
        except Exception as e:
            print(f"⚠️  查询日柱解析失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None
        finally:
            if conn:
                return_mysql_connection(conn)
    
    @staticmethod
    def get_all_rizhu_list() -> List[Dict[str, Any]]:
        """
        获取所有日柱列表（用于调试或管理）
        
        Returns:
            list: 包含所有日柱的列表
        """
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return []
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, rizhu, enabled
                    FROM rizhu_liujiazi
                    WHERE enabled = TRUE
                    ORDER BY id
                """)
                
                results = cursor.fetchall()
                
                return [
                    {
                        'id': row.get('id'),
                        'rizhu': row.get('rizhu'),
                        'enabled': bool(row.get('enabled', True))
                    }
                    for row in results
                ]
                    
        except Exception as e:
            print(f"⚠️  查询日柱列表失败: {e}", flush=True)
            return []
        finally:
            if conn:
                return_mysql_connection(conn)


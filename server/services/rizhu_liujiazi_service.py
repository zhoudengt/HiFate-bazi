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
            
            # 确保使用新的连接，避免事务冲突
            # 如果连接在事务中，先提交或回滚
            try:
                if conn.in_transaction:
                    conn.rollback()
            except:
                pass
            
            with conn.cursor() as cursor:
                # 使用多种方式尝试查询，确保兼容性
                # 方式1: BINARY精确匹配，enabled = 1（兼容布尔值）
                cursor.execute("""
                    SELECT id, rizhu, analysis, enabled
                    FROM rizhu_liujiazi
                    WHERE BINARY rizhu = %s AND enabled = 1
                    LIMIT 1
                """, (rizhu,))
                
                result = cursor.fetchone()
                
                # 方式2: 如果失败，尝试普通匹配，enabled = 1
                if not result:
                    cursor.execute("""
                        SELECT id, rizhu, analysis, enabled
                        FROM rizhu_liujiazi
                        WHERE rizhu = %s AND enabled = 1
                        LIMIT 1
                    """, (rizhu,))
                    result = cursor.fetchone()
                
                # 方式3: 如果还是失败，尝试不检查enabled（容错）
                if not result:
                    cursor.execute("""
                        SELECT id, rizhu, analysis, enabled
                        FROM rizhu_liujiazi
                        WHERE BINARY rizhu = %s
                        LIMIT 1
                    """, (rizhu,))
                    result = cursor.fetchone()
                
                # 方式4: 最后尝试普通匹配，不检查enabled
                if not result:
                    cursor.execute("""
                        SELECT id, rizhu, analysis, enabled
                        FROM rizhu_liujiazi
                        WHERE rizhu = %s
                        LIMIT 1
                    """, (rizhu,))
                    result = cursor.fetchone()
                
                if result:
                    # DictCursor 返回字典，使用键访问
                    # 确保正确处理字典格式
                    if isinstance(result, dict):
                        return {
                            'id': result.get('id'),
                            'rizhu': result.get('rizhu'),
                            'analysis': result.get('analysis'),
                            'enabled': bool(result.get('enabled', True))
                        }
                    else:
                        # 如果不是字典，尝试按顺序访问（兼容性处理）
                        return {
                            'id': result[0] if len(result) > 0 else None,
                            'rizhu': result[1] if len(result) > 1 else None,
                            'analysis': result[2] if len(result) > 2 else None,
                            'enabled': bool(result[3] if len(result) > 3 else True)
                        }
                else:
                    # 添加详细日志，便于排查问题
                    print(f"⚠️  未找到日柱 {rizhu} 的解析内容（所有查询方式都失败）", flush=True)
                    
                    # 检查表中是否有数据（各种方式）
                    debug_queries = [
                        ("总数", "SELECT COUNT(*) as count FROM rizhu_liujiazi", None),
                        ("启用数(enabled=1)", "SELECT COUNT(*) as count FROM rizhu_liujiazi WHERE enabled = 1", None),
                        ("启用数(enabled=TRUE)", "SELECT COUNT(*) as count FROM rizhu_liujiazi WHERE enabled = TRUE", None),
                        ("包含该日柱的", "SELECT COUNT(*) as count FROM rizhu_liujiazi WHERE rizhu = %s", (rizhu,)),
                    ]
                    
                    for desc, query, params in debug_queries:
                        try:
                            if params:
                                cursor.execute(query, params)
                            else:
                                cursor.execute(query)
                            count_result = cursor.fetchone()
                            if isinstance(count_result, dict):
                                total_count = count_result.get('count', 0)
                            elif isinstance(count_result, tuple):
                                total_count = count_result[0] if count_result else 0
                            else:
                                total_count = count_result
                            print(f"⚠️  {desc}: {total_count}", flush=True)
                        except Exception as e:
                            print(f"⚠️  {desc}查询失败: {e}", flush=True)
                    
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
    def get_total_count() -> int:
        """
        获取表中总记录数（用于诊断）
        
        Returns:
            int: 总记录数
        """
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return 0
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM rizhu_liujiazi")
                result = cursor.fetchone()
                
                if isinstance(result, dict):
                    return result.get('count', 0)
                elif isinstance(result, tuple):
                    return result[0] if result else 0
                else:
                    return int(result) if result else 0
                    
        except Exception as e:
            print(f"⚠️  查询总记录数失败: {e}", flush=True)
            return 0
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


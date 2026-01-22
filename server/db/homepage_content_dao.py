#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页内容数据访问对象
负责首页内容的数据库操作
"""

import json
import sys
import os
from typing import List, Optional, Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.db.mysql_connector import get_db_connection


class HomepageContentDAO:
    """首页内容数据访问对象"""
    
    @staticmethod
    def get_all_contents(enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有首页内容
        
        Args:
            enabled_only: 是否只获取启用的内容，默认True
            
        Returns:
            List[Dict]: 内容列表，按sort_order排序
        """
        try:
            db = get_db_connection()
            if enabled_only:
                sql = """
                    SELECT id, title, tags, description, image_base64, sort_order, enabled,
                           created_at, updated_at
                    FROM homepage_contents
                    WHERE enabled = 1
                    ORDER BY sort_order ASC, id ASC
                """
            else:
                sql = """
                    SELECT id, title, tags, description, image_base64, sort_order, enabled,
                           created_at, updated_at
                    FROM homepage_contents
                    ORDER BY sort_order ASC, id ASC
                """
            
            result = db.execute_query(sql)
            
            # 处理JSON字段
            for item in result:
                if item.get('tags') and isinstance(item['tags'], str):
                    try:
                        item['tags'] = json.loads(item['tags'])
                    except json.JSONDecodeError:
                        item['tags'] = []
                elif item.get('tags') is None:
                    item['tags'] = []
            
            return result
        except Exception as e:
            print(f"⚠ 查询首页内容失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def get_content_by_id(content_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            Dict: 内容字典，如果不存在返回None
        """
        try:
            db = get_db_connection()
            sql = """
                SELECT id, title, tags, description, image_base64, sort_order, enabled,
                       created_at, updated_at
                FROM homepage_contents
                WHERE id = %s
            """
            result = db.execute_query(sql, (content_id,))
            
            if result and len(result) > 0:
                item = result[0]
                # 处理JSON字段
                if item.get('tags') and isinstance(item['tags'], str):
                    try:
                        item['tags'] = json.loads(item['tags'])
                    except json.JSONDecodeError:
                        item['tags'] = []
                elif item.get('tags') is None:
                    item['tags'] = []
                return item
            return None
        except Exception as e:
            print(f"⚠ 查询首页内容失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def create_content(
        title: str,
        tags: List[str],
        description: str,
        image_base64: str,
        sort_order: int = 0
    ) -> Optional[int]:
        """
        创建新内容
        
        Args:
            title: 标题
            tags: 标签列表
            description: 详细描述
            image_base64: 图片Base64编码
            sort_order: 排序字段
            
        Returns:
            int: 新创建的内容ID，失败返回None
        """
        try:
            db = get_db_connection()
            tags_json = json.dumps(tags, ensure_ascii=False)
            
            # 使用同一个连接执行插入和获取ID
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO homepage_contents (title, tags, description, image_base64, sort_order, enabled)
                        VALUES (%s, %s, %s, %s, %s, 1)
                    """
                    cursor.execute(sql, (title, tags_json, description, image_base64, sort_order))
                    conn.commit()
                    
                    # 获取插入的ID（必须在同一个连接中）
                    cursor.execute("SELECT LAST_INSERT_ID() as id")
                    result = cursor.fetchone()
                    if result:
                        return result['id'] if isinstance(result, dict) else result[0]
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"创建首页内容失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def update_content(
        content_id: int,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        image_base64: Optional[str] = None,
        sort_order: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """
        更新内容
        
        Args:
            content_id: 内容ID
            title: 标题（可选）
            tags: 标签列表（可选）
            description: 详细描述（可选）
            image_base64: 图片Base64编码（可选）
            sort_order: 排序字段（可选）
            enabled: 是否启用（可选）
            
        Returns:
            bool: 是否更新成功
        """
        try:
            db = get_db_connection()
            
            # 构建动态更新SQL
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = %s")
                params.append(title)
            
            if tags is not None:
                updates.append("tags = %s")
                params.append(json.dumps(tags, ensure_ascii=False))
            
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            
            if image_base64 is not None:
                updates.append("image_base64 = %s")
                params.append(image_base64)
            
            if sort_order is not None:
                updates.append("sort_order = %s")
                params.append(sort_order)
            
            if enabled is not None:
                updates.append("enabled = %s")
                params.append(1 if enabled else 0)
            
            if not updates:
                return False
            
            sql = f"UPDATE homepage_contents SET {', '.join(updates)} WHERE id = %s"
            params.append(content_id)
            
            result = db.execute_update(sql, tuple(params))
            return result > 0
        except Exception as e:
            print(f"⚠ 更新首页内容失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def delete_content(content_id: int, hard_delete: bool = False) -> bool:
        """
        删除内容（默认软删除）
        
        Args:
            content_id: 内容ID
            hard_delete: 是否硬删除（物理删除），默认False（软删除）
            
        Returns:
            bool: 是否删除成功
        """
        try:
            db = get_db_connection()
            
            if hard_delete:
                # 硬删除
                sql = "DELETE FROM homepage_contents WHERE id = %s"
            else:
                # 软删除（设置enabled=False）
                sql = "UPDATE homepage_contents SET enabled = 0 WHERE id = %s"
            
            result = db.execute_update(sql, (content_id,))
            return result > 0
        except Exception as e:
            print(f"⚠ 删除首页内容失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def update_sort_order(content_id: int, sort_order: int) -> bool:
        """
        更新排序字段
        
        Args:
            content_id: 内容ID
            sort_order: 新的排序值
            
        Returns:
            bool: 是否更新成功
        """
        try:
            db = get_db_connection()
            sql = "UPDATE homepage_contents SET sort_order = %s WHERE id = %s"
            result = db.execute_update(sql, (sort_order, content_id))
            return result > 0
        except Exception as e:
            print(f"⚠ 更新排序失败: {e}")
            import traceback
            traceback.print_exc()
            return False

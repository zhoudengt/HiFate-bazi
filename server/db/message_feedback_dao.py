#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息评价 - 数据访问层 (MySQL)
"""

import logging
from typing import Any, Dict, Optional

from shared.config.database import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class MessageFeedbackDAO:
    """消息评价 DAO"""

    @staticmethod
    def upsert(
        request_id: str,
        rating: str,
        comment: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        """
        插入或更新一条消息评价（同一 request_id 重复提交时覆盖）

        Args:
            request_id: 关联 stream_api_call_logs.request_id
            rating: 评价类型 (up / down)
            comment: 用户补充说明
            email: 用户邮箱（前端传入）
            name: 用户名称（前端传入）

        Returns:
            bool: 是否操作成功
        """
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO message_feedback (request_id, rating, comment, email, name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        rating = VALUES(rating),
                        comment = VALUES(comment),
                        email = VALUES(email),
                        name = VALUES(name)
                """
                cursor.execute(sql, (request_id, rating, comment, email, name))
                conn.commit()
                logger.debug(f"[MessageFeedbackDAO] upsert 成功: request_id={request_id}, rating={rating}")
                return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"[MessageFeedbackDAO] upsert 失败: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)

    @staticmethod
    def request_id_exists(request_id: str) -> bool:
        """检查 request_id 是否存在于 stream_api_call_logs 表"""
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = "SELECT 1 FROM stream_api_call_logs WHERE request_id = %s LIMIT 1"
                cursor.execute(sql, (request_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"[MessageFeedbackDAO] 检查 request_id 失败: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)

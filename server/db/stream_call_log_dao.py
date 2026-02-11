#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口调用记录 - 数据访问层 (MySQL)
"""

import json
import logging
from typing import Any, Dict, Optional

from shared.config.database import get_mysql_connection, return_mysql_connection

logger = logging.getLogger(__name__)


class StreamCallLogDAO:
    """流式接口调用记录 DAO"""

    @staticmethod
    def insert(
        trace_id: str,
        function_type: str,
        frontend_api: str,
        frontend_input: Dict[str, Any],
        input_data: str,
        llm_output: str,
        api_total_ms: Optional[int] = None,
        input_data_gen_ms: Optional[int] = None,
        llm_first_token_ms: Optional[int] = None,
        llm_total_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        cache_hit: bool = False,
        bot_id: Optional[str] = None,
        llm_platform: Optional[str] = None,
    ) -> bool:
        """
        插入一条流式接口调用记录

        Returns:
            bool: 是否插入成功
        """
        conn = None
        try:
            # 计算数据大小
            input_data_size = len(input_data.encode('utf-8')) if input_data else 0
            llm_output_size = len(llm_output.encode('utf-8')) if llm_output else 0

            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO stream_api_call_logs (
                        trace_id, function_type, frontend_api,
                        frontend_input, input_data, llm_output,
                        api_total_ms, input_data_gen_ms, llm_first_token_ms, llm_total_ms,
                        status, error_message, cache_hit,
                        bot_id, llm_platform,
                        input_data_size, llm_output_size
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s
                    )
                """
                frontend_input_json = json.dumps(frontend_input, ensure_ascii=False) if frontend_input else '{}'
                cursor.execute(sql, (
                    trace_id, function_type, frontend_api,
                    frontend_input_json, input_data, llm_output,
                    api_total_ms, input_data_gen_ms, llm_first_token_ms, llm_total_ms,
                    status, error_message, 1 if cache_hit else 0,
                    bot_id, llm_platform,
                    input_data_size, llm_output_size,
                ))
                conn.commit()
                logger.debug(f"[StreamCallLogDAO] 记录插入成功: trace_id={trace_id}, function_type={function_type}")
                return True
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"[StreamCallLogDAO] 插入失败: {e}", exc_info=True)
            return False
        finally:
            if conn:
                return_mysql_connection(conn)

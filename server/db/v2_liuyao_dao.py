# -*- coding: utf-8 -*-
"""V2 六爻落库（表不存在或写入失败时不影响接口）。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def insert_casting(
    question: str,
    method: str,
    category: Optional[str],
    coin_results: Optional[List[int]],
    number_input: Optional[List[int]],
    divination_time: Optional[str],
    result_json: Dict[str, Any],
) -> Optional[int]:
    """插入一条起卦记录，返回主键 id；失败返回 None。"""
    try:
        from shared.config.database import get_mysql_connection
    except Exception as e:
        logger.debug("v2_liuyao skip persist (no db): %s", e)
        return None

    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO v2_liuyao_castings
                (question, method, category, coin_results, number_input,
                 divination_time, result_json, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed')
                """,
                (
                    question,
                    method,
                    category or "general",
                    json.dumps(coin_results) if coin_results is not None else None,
                    json.dumps(number_input) if number_input is not None else None,
                    divination_time,
                    json.dumps(result_json, ensure_ascii=False),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
    except Exception as e:
        logger.warning("v2_liuyao insert failed (run migration if needed): %s", e)
        return None


def update_ai_reading(row_id: int, text: str) -> None:
    try:
        from shared.config.database import get_mysql_connection
    except Exception:
        return
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE v2_liuyao_castings
                SET ai_reading = %s, status = 'ai_analyzed'
                WHERE id = %s
                """,
                (text, row_id),
            )
        conn.commit()
    except Exception as e:
        logger.warning("v2_liuyao update ai_reading failed: %s", e)

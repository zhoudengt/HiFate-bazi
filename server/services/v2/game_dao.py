# -*- coding: utf-8 -*-
"""V2 游戏状态与等级配置 DAO。"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from server.services.v2.db_conn import v2_mysql_conn

logger = logging.getLogger(__name__)


def fetch_level_thresholds() -> List[Tuple[int, int]]:
    """返回 [(level, xp_required), ...] level 1..100，按 level 升序。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT level, xp_required FROM v2_youxi_level_config ORDER BY level ASC"
                )
                rows = cur.fetchall() or []
        return [(int(r["level"]), int(r["xp_required"])) for r in rows]
    except Exception as e:
        logger.warning("v2 level_config fetch failed: %s", e)
        return []


def get_game_state_row(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, level, xp, destiny_points, tree_level, tree_last_water_date
                    FROM v2_youxi_states
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                return cur.fetchone()
    except Exception as e:
        logger.warning("v2 game_state get failed: %s", e)
        return None


def create_game_state(user_id: int) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_youxi_states (user_id, level, xp, destiny_points, tree_level)
                    VALUES (%s, 1, 0, 0, 1)
                    """,
                    (user_id,),
                )
                conn.commit()
                return True
    except Exception as e:
        logger.warning("v2 game_state create failed: %s", e)
        return False


def update_game_state(
    user_id: int,
    *,
    level: Optional[int] = None,
    xp: Optional[int] = None,
    destiny_points: Optional[int] = None,
    tree_level: Optional[int] = None,
    tree_last_water_date: Optional[date] = None,
) -> bool:
    fields = []
    params: List[Any] = []
    if level is not None:
        fields.append("level = %s")
        params.append(level)
    if xp is not None:
        fields.append("xp = %s")
        params.append(xp)
    if destiny_points is not None:
        fields.append("destiny_points = %s")
        params.append(destiny_points)
    if tree_level is not None:
        fields.append("tree_level = %s")
        params.append(tree_level)
    if tree_last_water_date is not None:
        fields.append("tree_last_water_date = %s")
        params.append(tree_last_water_date)
    if not fields:
        return True
    params.append(user_id)
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                sql = f"UPDATE v2_youxi_states SET {', '.join(fields)} WHERE user_id = %s"
                cur.execute(sql, params)
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning("v2 game_state update failed: %s", e)
        return False


def insert_xp_log(user_id: int, amount: int, source: str, source_detail: Optional[str]) -> None:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_youxi_xp_logs (user_id, amount, source, source_detail)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, amount, source[:50], (source_detail or "")[:200] or None),
                )
                conn.commit()
    except Exception as e:
        logger.warning("v2_youxi_xp_logs insert failed: %s", e)


def insert_points_log(user_id: int, amount: int, source: str, source_detail: Optional[str]) -> None:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_youxi_points_logs (user_id, amount, source, source_detail)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, amount, source[:50], (source_detail or "")[:200] or None),
                )
                conn.commit()
    except Exception as e:
        logger.warning("v2_youxi_points_logs insert failed: %s", e)

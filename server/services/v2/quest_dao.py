# -*- coding: utf-8 -*-
"""V2 任务模块 DAO（v2_renwu_*）。"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from server.services.v2.db_conn import v2_mysql_conn

logger = logging.getLogger(__name__)


def _today_key() -> str:
    return date.today().isoformat()


def _week_key() -> str:
    d = date.today()
    return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"


# ═══════════════════════════════════════
# 主线任务配置
# ═══════════════════════════════════════

def get_current_main_quests(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    返回用户当前可见的主线任务（每条链最前面的未完成任务 + 最近已完成的几条）。
    """
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id, c.pretask_id, c.tasktype, c.taskname, c.condition_value,
                           c.award_item_id, c.award_num, c.icon, c.open_level, c.end_level,
                           COALESCE(p.completed, 0) AS completed,
                           COALESCE(p.claimed, 0) AS claimed
                    FROM v2_renwu_config c
                    LEFT JOIN v2_renwu_user_progress p ON p.quest_id = c.id AND p.user_id = %s
                    WHERE c.show_initial = 1
                       OR c.pretask_id IN (
                           SELECT quest_id FROM v2_renwu_user_progress
                           WHERE user_id = %s AND completed = 1
                       )
                    ORDER BY c.id ASC
                    LIMIT %s
                    """,
                    (user_id, user_id, limit),
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("get_current_main_quests failed: %s", e)
        return []


def get_main_quest_by_id(quest_id: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM v2_renwu_config WHERE id = %s LIMIT 1",
                    (quest_id,),
                )
                return cur.fetchone()
    except Exception as e:
        logger.warning("get_main_quest_by_id failed: %s", e)
        return None


def get_user_quest_progress(user_id: int, quest_id: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM v2_renwu_user_progress WHERE user_id = %s AND quest_id = %s LIMIT 1",
                    (user_id, quest_id),
                )
                return cur.fetchone()
    except Exception as e:
        logger.warning("get_user_quest_progress failed: %s", e)
        return None


def complete_main_quest(user_id: int, quest_id: int) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_renwu_user_progress (user_id, quest_id, completed, completed_at)
                    VALUES (%s, %s, 1, NOW())
                    ON DUPLICATE KEY UPDATE completed = 1, completed_at = COALESCE(completed_at, NOW())
                    """,
                    (user_id, quest_id),
                )
                conn.commit()
                return True
    except Exception as e:
        logger.warning("complete_main_quest failed: %s", e)
        return False


def claim_main_quest(user_id: int, quest_id: int) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE v2_renwu_user_progress
                    SET claimed = 1, claimed_at = NOW()
                    WHERE user_id = %s AND quest_id = %s AND completed = 1 AND claimed = 0
                    """,
                    (user_id, quest_id),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning("claim_main_quest failed: %s", e)
        return False


# ═══════════════════════════════════════
# 每日/每周任务
# ═══════════════════════════════════════

def get_daily_quest_configs() -> List[Dict[str, Any]]:
    """type=1 的每日任务配置。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM v2_renwu_daily_config WHERE type = 1 ORDER BY id ASC"
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("get_daily_quest_configs failed: %s", e)
        return []


def get_box_configs(tasktype: int) -> List[Dict[str, Any]]:
    """tasktype=99 每日宝箱, tasktype=100 每周宝箱。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM v2_renwu_daily_config WHERE tasktype = %s ORDER BY condition_count ASC",
                    (tasktype,),
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("get_box_configs failed: %s", e)
        return []


def get_user_daily_progress(user_id: int, period_key: str) -> List[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT quest_config_id, progress, completed, claimed
                    FROM v2_renwu_user_daily
                    WHERE user_id = %s AND period_key = %s
                    """,
                    (user_id, period_key),
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("get_user_daily_progress failed: %s", e)
        return []


def increment_daily_progress(user_id: int, quest_config_id: int, period_key: str, target: int) -> Tuple[int, bool]:
    """
    进度 +1，返回 (new_progress, newly_completed)。
    """
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_renwu_user_daily (user_id, quest_config_id, period_key, progress, completed)
                    VALUES (%s, %s, %s, 1, IF(1 >= %s, 1, 0))
                    ON DUPLICATE KEY UPDATE
                      progress = progress + 1,
                      completed = IF(progress >= %s, 1, completed)
                    """,
                    (user_id, quest_config_id, period_key, target, target),
                )
                conn.commit()
                cur.execute(
                    "SELECT progress, completed FROM v2_renwu_user_daily WHERE user_id=%s AND quest_config_id=%s AND period_key=%s",
                    (user_id, quest_config_id, period_key),
                )
                row = cur.fetchone()
                if row:
                    return int(row["progress"]), bool(row["completed"])
                return 1, False
    except Exception as e:
        logger.warning("increment_daily_progress failed: %s", e)
        return 0, False


def claim_daily_quest(user_id: int, quest_config_id: int, period_key: str) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE v2_renwu_user_daily
                    SET claimed = 1
                    WHERE user_id = %s AND quest_config_id = %s AND period_key = %s
                      AND completed = 1 AND claimed = 0
                    """,
                    (user_id, quest_config_id, period_key),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning("claim_daily_quest failed: %s", e)
        return False


# ═══════════════════════════════════════
# 活跃值
# ═══════════════════════════════════════

def get_activity_points(user_id: int, period_type: str, period_key: str) -> int:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT points FROM v2_renwu_user_activity WHERE user_id=%s AND period_type=%s AND period_key=%s",
                    (user_id, period_type, period_key),
                )
                row = cur.fetchone()
                return int(row["points"]) if row else 0
    except Exception as e:
        logger.warning("get_activity_points failed: %s", e)
        return 0


def add_activity_points(user_id: int, period_type: str, period_key: str, delta: int) -> int:
    """增加活跃值，返回新值。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_renwu_user_activity (user_id, period_type, period_key, points)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE points = points + VALUES(points)
                    """,
                    (user_id, period_type, period_key, delta),
                )
                conn.commit()
                cur.execute(
                    "SELECT points FROM v2_renwu_user_activity WHERE user_id=%s AND period_type=%s AND period_key=%s",
                    (user_id, period_type, period_key),
                )
                row = cur.fetchone()
                return int(row["points"]) if row else delta
    except Exception as e:
        logger.warning("add_activity_points failed: %s", e)
        return 0


def claim_box(user_id: int, config_id: int, period_key: str) -> bool:
    """领取宝箱（记录在 v2_renwu_user_daily 中，claimed=1）。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_renwu_user_daily (user_id, quest_config_id, period_key, progress, completed, claimed)
                    VALUES (%s, %s, %s, 0, 1, 1)
                    ON DUPLICATE KEY UPDATE claimed = 1
                    """,
                    (user_id, config_id, period_key),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning("claim_box failed: %s", e)
        return False

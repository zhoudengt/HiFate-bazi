# -*- coding: utf-8 -*-
"""V2 学堂：章节、关卡、掉落配置与用户进度 DAO。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set

from server.services.v2.db_conn import v2_mysql_conn

logger = logging.getLogger(__name__)


def _json_val(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8", errors="replace")
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v
    return v


def fetch_all_chapters() -> List[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, description, cover_scene, sort_order "
                    "FROM v2_xuetang_chapters ORDER BY sort_order ASC, id ASC"
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("v2_xuetang_chapters fetch failed: %s", e)
        return []


def fetch_levels_by_chapter(chapter_id: int) -> List[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sn, chapter_id, stage_index, unlock_sn, name, battlefield,
                           reward_coin_id, reward_coin_num, reward_xp_id, reward_xp_num,
                           drop_id, start_drama_id, end_drama_id, lesson_body, quiz_json
                    FROM v2_xuetang_levels
                    WHERE chapter_id = %s
                    ORDER BY stage_index ASC
                    """,
                    (chapter_id,),
                )
                rows = list(cur.fetchall() or [])
                for r in rows:
                    r["quiz_json"] = _json_val(r.get("quiz_json"))
                return rows
    except Exception as e:
        logger.warning("fetch_levels_by_chapter failed: %s", e)
        return []


def fetch_level_by_sn(sn: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sn, chapter_id, stage_index, unlock_sn, name, battlefield,
                           reward_coin_id, reward_coin_num, reward_xp_id, reward_xp_num,
                           drop_id, start_drama_id, end_drama_id, lesson_body, quiz_json
                    FROM v2_xuetang_levels WHERE sn = %s LIMIT 1
                    """,
                    (sn,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                row = dict(row)
                row["quiz_json"] = _json_val(row.get("quiz_json"))
                return row
    except Exception as e:
        logger.warning("fetch_level_by_sn failed: %s", e)
        return None


def fetch_drop_by_sn(sn: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sn, note, item_ids, rates, quantities FROM v2_xuetang_drops WHERE sn = %s LIMIT 1",
                    (sn,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                d["item_ids"] = _json_val(d.get("item_ids")) or []
                d["rates"] = _json_val(d.get("rates")) or []
                d["quantities"] = _json_val(d.get("quantities")) or []
                return d
    except Exception as e:
        logger.warning("fetch_drop_by_sn failed: %s", e)
        return None


def get_user_completed_level_sns(user_id: int) -> Set[int]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT level_sn FROM v2_xuetang_user_progress WHERE user_id = %s",
                    (user_id,),
                )
                return {int(r["level_sn"]) for r in (cur.fetchall() or [])}
    except Exception as e:
        logger.warning("get_user_completed_level_sns failed: %s", e)
        return set()


def is_level_completed(user_id: int, level_sn: int) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM v2_xuetang_user_progress WHERE user_id = %s AND level_sn = %s LIMIT 1",
                    (user_id, level_sn),
                )
                return cur.fetchone() is not None
    except Exception as e:
        logger.warning("is_level_completed failed: %s", e)
        return False


def insert_level_completion(user_id: int, level_sn: int, score: Optional[int]) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_xuetang_user_progress (user_id, level_sn, score)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE score = COALESCE(VALUES(score), score)
                    """,
                    (user_id, level_sn, score),
                )
                conn.commit()
                return True
    except Exception as e:
        logger.warning("insert_level_completion failed: %s", e)
        return False

# -*- coding: utf-8 -*-
"""V2 匿名用户档案 DAO。"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, Optional

from server.services.v2.db_conn import v2_mysql_conn

logger = logging.getLogger(__name__)


def _random_nickname() -> str:
    return f"元辰访客{random.randint(1000, 9999)}"


def get_profile_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, guest_token, nickname, avatar_url, created_at, updated_at
                    FROM v2_yonghu_profiles
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                return cur.fetchone()
    except Exception as e:
        logger.warning("v2 profile get by id failed: %s", e)
        return None


def get_profile_by_guest_token(guest_token: str) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, guest_token, nickname, avatar_url, created_at, updated_at
                    FROM v2_yonghu_profiles
                    WHERE guest_token = %s
                    LIMIT 1
                    """,
                    (guest_token,),
                )
                return cur.fetchone()
    except Exception as e:
        logger.warning("v2 profile get failed: %s", e)
        return None


def create_profile(guest_token: str, nickname: Optional[str] = None) -> Optional[int]:
    nick = nickname or _random_nickname()
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_yonghu_profiles (guest_token, nickname)
                    VALUES (%s, %s)
                    """,
                    (guest_token, nick),
                )
                conn.commit()
                return int(cur.lastrowid)
    except Exception as e:
        logger.warning("v2 profile create failed: %s", e)
        return None


def update_nickname(user_id: int, nickname: str) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE v2_yonghu_profiles SET nickname = %s WHERE id = %s",
                    (nickname[:50], user_id),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning("v2 profile nickname update failed: %s", e)
        return False


def update_avatar_url(user_id: int, avatar_url: str) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE v2_yonghu_profiles SET avatar_url = %s WHERE id = %s",
                    (avatar_url[:512], user_id),
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        logger.warning("v2 profile avatar update failed: %s", e)
        return False

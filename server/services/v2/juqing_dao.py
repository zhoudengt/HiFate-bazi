# -*- coding: utf-8 -*-
"""V2 剧情配置 DAO（v2_juqing_config）。"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from server.services.v2.db_conn import v2_mysql_conn

logger = logging.getLogger(__name__)


def load_all_dialogues_grouped() -> Dict[int, List[Dict[str, Any]]]:
    """
    全表读取，按 dialogue_id 分组；供 juqing_service 内存缓存使用。
    """
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    with v2_mysql_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dialogue_id, seq, speaker, avatar_id, content
                FROM v2_juqing_config
                ORDER BY dialogue_id ASC, seq ASC
                """
            )
            rows = cur.fetchall() or []
    for row in rows:
        did = int(row["dialogue_id"])
        grouped[did].append(
            {
                "seq": int(row["seq"]),
                "speaker": row["speaker"],
                "avatar_id": int(row["avatar_id"]),
                "content": row["content"],
            }
        )
    return dict(grouped)

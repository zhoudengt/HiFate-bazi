# -*- coding: utf-8 -*-
"""V2 经验值：与命运点数解耦，仅负责 XP 与等级。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from server.services.v2 import game_dao

logger = logging.getLogger(__name__)

_MAX_LEVEL = 100


def _thresholds_list() -> List[Tuple[int, int]]:
    return game_dao.fetch_level_thresholds()


def compute_level_from_xp(xp: int, thresholds: Optional[List[Tuple[int, int]]] = None) -> int:
    """xp_required[L] = 达到 L+1 级的最低累计经验。当前等级从 1 起。"""
    th = thresholds if thresholds is not None else _thresholds_list()
    if not th:
        return 1
    lvl = 1
    for level_idx, req in th:
        if xp >= req:
            lvl = level_idx + 1
        else:
            break
    return min(lvl, _MAX_LEVEL)


def xp_to_next(xp: int, current_level: int, thresholds: Optional[List[Tuple[int, int]]] = None) -> int:
    """距离下一级还需要的经验（当前段内）。"""
    th = thresholds if thresholds is not None else _thresholds_list()
    if not th or current_level >= _MAX_LEVEL:
        return 0
    # 升到 current_level+1 所需最低总经验 = 表中 level == current_level 的 xp_required
    need_map = {lv: rq for lv, rq in th}
    nxt = need_map.get(current_level)
    if nxt is None:
        return 0
    return max(0, int(nxt) - int(xp))


def add_xp(
    user_id: int,
    amount: int,
    source: str,
    source_detail: Optional[str] = None,
) -> Dict[str, Any]:
    if amount == 0:
        return {"ok": False, "error": "amount_zero"}
    if amount < 0:
        return {"ok": False, "error": "negative_xp_use_dedicated_flow"}

    row = game_dao.get_game_state_row(user_id)
    if not row:
        return {"ok": False, "error": "no_game_state"}

    th = _thresholds_list()
    old_xp = int(row["xp"])
    old_level = int(row["level"])
    new_xp = old_xp + amount
    new_level = compute_level_from_xp(new_xp, th)

    game_dao.update_game_state(user_id, level=new_level, xp=new_xp)
    game_dao.insert_xp_log(user_id, amount, source, source_detail)

    leveled_up = new_level > old_level
    xpn = xp_to_next(new_xp, new_level, th)

    return {
        "ok": True,
        "leveled_up": leveled_up,
        "old_level": old_level,
        "new_level": new_level,
        "xp": new_xp,
        "xp_to_next": xpn,
    }

# -*- coding: utf-8 -*-
"""组装 GET /game/state 的 data 字段。"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from server.services.v2 import economy_dao, game_dao, xp_service


def _default_buildings(level: int, tree_level: int) -> List[Dict[str, Any]]:
    return [
        {"code": "caishen", "name": "财神殿", "unlocked": True, "level": level},
        {"code": "ganqing", "name": "感情殿", "unlocked": True, "level": level},
        {"code": "shiye", "name": "事业殿", "unlocked": True, "level": level},
        {"code": "exchange", "name": "兑换殿", "unlocked": True, "level": level},
        {"code": "prayer", "name": "祈福", "unlocked": True, "level": level},
        {"code": "tree", "name": "生命之树", "unlocked": True, "level": tree_level},
        {"code": "quest", "name": "任务中心", "unlocked": True, "level": level},
        {"code": "academy", "name": "学堂", "unlocked": True, "level": level},
    ]


def build_game_state_payload(user_id: int) -> Optional[Dict[str, Any]]:
    row = game_dao.get_game_state_row(user_id)
    if not row:
        return None
    th = game_dao.fetch_level_thresholds()
    xp = int(row["xp"])
    level = xp_service.compute_level_from_xp(xp, th)
    stored = int(row["level"])
    if level != stored:
        game_dao.update_game_state(user_id, level=level)
    xp_next = xp_service.xp_to_next(xp, level, th)
    # 当前等级段内进度 0~1（满级为 1；无配置表时为 0）
    ratio = 1.0 if level >= 100 else 0.0
    if level < 100 and th:
        need_map = {lv: rq for lv, rq in th}
        prev_need = 0
        if level > 1:
            prev_need = int(need_map.get(level - 1, 0))
        next_need = int(need_map.get(level, xp + xp_next))
        span = max(1, next_need - prev_need)
        ratio = max(0.0, min(1.0, (xp - prev_need) / span))
    tree_level = int(row["tree_level"])
    water = row.get("tree_last_water_date")
    if water is None:
        tree_water_today = False
    else:
        wd = water.date() if hasattr(water, "date") else water
        tree_water_today = wd == date.today()

    destiny_points = int(row["destiny_points"])
    try:
        dbal = economy_dao.get_currency_balance(user_id, economy_dao.DESTINY_CURRENCY_ITEM_ID)
        if dbal is not None:
            destiny_points = int(dbal)
    except Exception:
        pass

    return {
        "level": level,
        "xp": xp,
        "xp_to_next": xp_next,
        "xp_progress_ratio": round(ratio, 4),
        "destiny_points": destiny_points,
        "tree_level": tree_level,
        "tree_water_today": tree_water_today,
        "buildings": _default_buildings(level, tree_level),
    }

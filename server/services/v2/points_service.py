# -*- coding: utf-8 -*-
"""V2 货币/命运点数：以 v2_jingji_user_currencies 为准，v2_youxi_states.destiny_points 作缓存（仅 1001）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from server.services.v2 import economy_dao, game_dao

logger = logging.getLogger(__name__)

DESTINY_CURRENCY_ITEM_ID = economy_dao.DESTINY_CURRENCY_ITEM_ID


def add_currency(
    user_id: int,
    currency_item_id: int,
    amount: int,
    source: str,
    source_detail: Optional[str] = None,
) -> Dict[str, Any]:
    if amount == 0:
        return {"ok": False, "error": "amount_zero"}

    row = game_dao.get_game_state_row(user_id)
    if not row:
        return {"ok": False, "error": "no_game_state"}

    bal = economy_dao.get_currency_balance(user_id, currency_item_id)
    if bal is None:
        if currency_item_id == DESTINY_CURRENCY_ITEM_ID:
            bal = int(row["destiny_points"])
            economy_dao.set_currency_balance(user_id, currency_item_id, bal)
        else:
            economy_dao.ensure_currency_row(user_id, currency_item_id, 0)
            bal = 0

    new = bal + amount
    if new < 0:
        return {
            "ok": False,
            "error": "insufficient_funds",
            "balance": bal,
            "currency_item_id": currency_item_id,
        }

    if not economy_dao.set_currency_balance(user_id, currency_item_id, new):
        return {"ok": False, "error": "persist_failed"}

    if currency_item_id == DESTINY_CURRENCY_ITEM_ID:
        game_dao.update_game_state(user_id, destiny_points=new)
        game_dao.insert_points_log(user_id, amount, source, source_detail)

    return {
        "ok": True,
        "balance": new,
        "delta": amount,
        "currency_item_id": currency_item_id,
        "destiny_points": new if currency_item_id == DESTINY_CURRENCY_ITEM_ID else None,
    }


def add_points(
    user_id: int,
    amount: int,
    source: str,
    source_detail: Optional[str] = None,
) -> Dict[str, Any]:
    """命运点数（货币 1001）。"""
    r = add_currency(user_id, DESTINY_CURRENCY_ITEM_ID, amount, source, source_detail)
    if not r.get("ok"):
        if r.get("error") == "insufficient_funds":
            return {
                "ok": False,
                "error": "insufficient_points",
                "destiny_points": r.get("balance"),
            }
        return r
    return {
        "ok": True,
        "destiny_points": r["balance"],
        "delta": r["delta"],
    }

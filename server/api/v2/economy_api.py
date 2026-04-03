# -*- coding: utf-8 -*-
"""V2 经济 API：商店、背包、货币余额（替代 economy_mock）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.api.v2.v2_guest_deps import get_or_create_user_id
from server.services.v2 import economy_dao, economy_service

router = APIRouter()


class PurchaseBody(BaseModel):
    listing_id: int = Field(..., ge=1)


class UseItemBody(BaseModel):
    item_id: int = Field(..., ge=1)
    quantity: int = Field(1, ge=1, le=9999)


@router.get("/balance")
def get_balance(user_id: int = Depends(get_or_create_user_id)):
    balances = economy_service.get_balances(user_id)
    destiny = economy_dao.get_currency_balance(user_id, economy_dao.DESTINY_CURRENCY_ITEM_ID)
    if destiny is None:
        from server.services.v2 import game_dao

        row = game_dao.get_game_state_row(user_id)
        destiny = int(row["destiny_points"]) if row else 0
    return {
        "code": 0,
        "message": "success",
        "data": {
            "currencies": balances,
            "destiny_points": destiny,
        },
    }


@router.get("/shop/items")
def shop_items(user_id: int = Depends(get_or_create_user_id)):
    _ = user_id
    items = economy_service.get_shop_items(1)
    return {"code": 0, "message": "success", "data": {"items": items}}


@router.post("/shop/purchase")
def shop_purchase(
    body: PurchaseBody,
    user_id: int = Depends(get_or_create_user_id),
):
    r = economy_service.purchase_listing(user_id, body.listing_id)
    if not r.get("ok"):
        code_map = {
            "listing_not_found": 1,
            "insufficient_funds": 2,
            "invalid_params": 3,
            "transaction_failed": 4,
            "no_currency_row": 5,
        }
        c = code_map.get(r.get("error"), 9)
        return {"code": c, "message": r.get("error", "purchase_failed"), "data": r}
    return {"code": 0, "message": "success", "data": r}


@router.get("/inventory")
def inventory(user_id: int = Depends(get_or_create_user_id)):
    items = economy_service.get_inventory(user_id)
    return {"code": 0, "message": "success", "data": {"items": items}}


@router.get("/transactions")
def transactions(
    page: int = 1,
    size: int = 20,
    user_id: int = Depends(get_or_create_user_id),
):
    data = economy_service.get_transactions(user_id, page=max(1, page), size=min(100, max(1, size)))
    return {"code": 0, "message": "success", "data": data}


@router.post("/items/use")
def use_item(
    _body: UseItemBody,
    _user_id: int = Depends(get_or_create_user_id),
):
    return {
        "code": 99,
        "message": "not_implemented",
        "data": None,
    }

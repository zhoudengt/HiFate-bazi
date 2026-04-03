# -*- coding: utf-8 -*-
"""V2 商店、背包、余额组装。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from server.services.v2 import economy_dao

ICON_URL_TEMPLATE = "/assets/items/{icon_id}.jpg"


def _icon_url(icon_id: int) -> str:
    return ICON_URL_TEMPLATE.format(icon_id=icon_id)


def get_shop_items(shop_id: int = 1) -> List[Dict[str, Any]]:
    rows = economy_dao.fetch_shop_listings(shop_id)
    out: List[Dict[str, Any]] = []
    for r in rows:
        icon_id = int(r.get("icon_id") or r.get("item_id") or 0)
        out.append(
            {
                "listing_id": int(r["listing_id"]),
                "shop_id": int(r["shop_id"]),
                "item_id": int(r["item_id"]),
                "name": r["item_name"],
                "description": r.get("item_description") or "",
                "quantity": int(r["quantity"]),
                "currency_item_id": int(r["currency_item_id"]),
                "cost": int(r["cost"]),
                "rarity": int(r.get("rarity") or 1),
                "icon_url": _icon_url(icon_id),
            }
        )
    return out


def purchase_listing(user_id: int, listing_id: int) -> Dict[str, Any]:
    listing = economy_dao.get_listing_by_id(listing_id)
    if not listing:
        return {"ok": False, "error": "listing_not_found"}
    ok, err, new_bal = economy_dao.purchase_listing_atomic(
        user_id=user_id,
        listing_id=listing_id,
        currency_item_id=int(listing["currency_item_id"]),
        cost=int(listing["cost"]),
        grant_item_id=int(listing["item_id"]),
        grant_quantity=int(listing["quantity"]),
    )
    if not ok:
        return {"ok": False, "error": err, "new_balance": new_bal}
    return {
        "ok": True,
        "listing_id": listing_id,
        "item_id": int(listing["item_id"]),
        "quantity_granted": int(listing["quantity"]),
        "currency_item_id": int(listing["currency_item_id"]),
        "new_balance": new_bal,
    }


def get_inventory(user_id: int) -> List[Dict[str, Any]]:
    rows = economy_dao.get_user_inventory(user_id)
    out: List[Dict[str, Any]] = []
    for r in rows:
        icon_id = int(r.get("icon_id") or r["item_id"])
        out.append(
            {
                "item_id": int(r["item_id"]),
                "name": r["name"],
                "quantity": int(r["quantity"]),
                "description": r.get("description") or "",
                "icon_url": _icon_url(icon_id),
                "item_type": int(r.get("item_type") or 1),
            }
        )
    return out


def get_balances(user_id: int) -> List[Dict[str, Any]]:
    rows = economy_dao.get_all_user_currencies(user_id)
    out: List[Dict[str, Any]] = []
    for r in rows:
        icon_id = int(r.get("icon_id") or r["currency_item_id"])
        out.append(
            {
                "currency_item_id": int(r["currency_item_id"]),
                "name": r["name"],
                "balance": int(r["balance"]),
                "icon_url": _icon_url(icon_id),
            }
        )
    return out


def get_transactions(user_id: int, page: int = 1, size: int = 20) -> Dict[str, Any]:
    rows, total = economy_dao.fetch_points_logs(user_id, page, size)
    items: List[Dict[str, Any]] = []
    for r in rows:
        amt = int(r["amount"])
        items.append(
            {
                "amount": amt,
                "type": "earn" if amt > 0 else "spend",
                "source": r.get("source") or "",
                "description": (r.get("source_detail") or "")[:200],
                "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            }
        )
    return {"items": items, "total": total, "page": page, "size": size}

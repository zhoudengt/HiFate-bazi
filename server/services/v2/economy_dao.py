# -*- coding: utf-8 -*-
"""V2 经济：物品、商店、货币、背包 DAO。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from server.services.v2.db_conn import v2_mysql_conn

logger = logging.getLogger(__name__)

DESTINY_CURRENCY_ITEM_ID = 1001


def fetch_all_items() -> List[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, item_type, category, icon_id, rarity, use_condition, description "
                    "FROM v2_jingji_items ORDER BY id ASC"
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("v2_jingji_items fetch failed: %s", e)
        return []


def fetch_shop_listings(shop_id: int = 1) -> List[Dict[str, Any]]:
    """上架行 JOIN 商品信息。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      l.id AS listing_id,
                      l.shop_id,
                      l.item_id,
                      l.quantity,
                      l.currency_item_id,
                      l.cost,
                      l.sort_order,
                      l.enabled,
                      i.name AS item_name,
                      i.item_type,
                      i.icon_id,
                      i.rarity,
                      i.description AS item_description
                    FROM v2_jingji_shop_listings l
                    INNER JOIN v2_jingji_items i ON i.id = l.item_id
                    WHERE l.shop_id = %s AND l.enabled = 1
                    ORDER BY l.sort_order ASC, l.id ASC
                    """,
                    (shop_id,),
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("v2_jingji_shop_listings fetch failed: %s", e)
        return []


def get_listing_by_id(listing_id: int) -> Optional[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT l.id AS listing_id, l.shop_id, l.item_id, l.quantity,
                           l.currency_item_id, l.cost, l.enabled,
                           i.name AS item_name, i.item_type
                    FROM v2_jingji_shop_listings l
                    INNER JOIN v2_jingji_items i ON i.id = l.item_id
                    WHERE l.id = %s AND l.enabled = 1
                    LIMIT 1
                    """,
                    (listing_id,),
                )
                return cur.fetchone()
    except Exception as e:
        logger.warning("v2_shop_listing get failed: %s", e)
        return None


def get_currency_balance(user_id: int, currency_item_id: int) -> Optional[int]:
    """返回余额；表不存在或错误返回 None。"""
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT balance FROM v2_jingji_user_currencies
                    WHERE user_id = %s AND currency_item_id = %s
                    LIMIT 1
                    """,
                    (user_id, currency_item_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return int(row["balance"])
    except Exception as e:
        logger.debug("v2_jingji_user_currencies read failed: %s", e)
        return None


def get_all_user_currencies(user_id: int) -> List[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.currency_item_id, c.balance, i.name, i.item_type, i.icon_id
                    FROM v2_jingji_user_currencies c
                    INNER JOIN v2_jingji_items i ON i.id = c.currency_item_id
                    WHERE c.user_id = %s
                    ORDER BY c.currency_item_id ASC
                    """,
                    (user_id,),
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("v2_jingji_user_currencies list failed: %s", e)
        return []


def ensure_currency_row(user_id: int, currency_item_id: int, initial_balance: int = 0) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_jingji_user_currencies (user_id, currency_item_id, balance)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE balance = balance
                    """,
                    (user_id, currency_item_id, initial_balance),
                )
                conn.commit()
                return True
    except Exception as e:
        logger.warning("ensure_currency_row failed: %s", e)
        return False


def set_currency_balance(user_id: int, currency_item_id: int, new_balance: int) -> bool:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_jingji_user_currencies (user_id, currency_item_id, balance)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE balance = VALUES(balance)
                    """,
                    (user_id, currency_item_id, new_balance),
                )
                conn.commit()
                return True
    except Exception as e:
        logger.warning("set_currency_balance failed: %s", e)
        return False


def get_user_inventory(user_id: int) -> List[Dict[str, Any]]:
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT inv.item_id, inv.quantity, i.name, i.icon_id, i.item_type, i.description
                    FROM v2_jingji_user_inventory inv
                    INNER JOIN v2_jingji_items i ON i.id = inv.item_id
                    WHERE inv.user_id = %s AND inv.quantity > 0
                    ORDER BY inv.item_id ASC
                    """,
                    (user_id,),
                )
                return list(cur.fetchall() or [])
    except Exception as e:
        logger.warning("v2_jingji_user_inventory list failed: %s", e)
        return []


def add_to_inventory(user_id: int, item_id: int, quantity: int) -> bool:
    if quantity <= 0:
        return True
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO v2_jingji_user_inventory (user_id, item_id, quantity)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
                    """,
                    (user_id, item_id, quantity),
                )
                conn.commit()
                return True
    except Exception as e:
        logger.warning("add_to_inventory failed: %s", e)
        return False


def remove_from_inventory(user_id: int, item_id: int, quantity: int) -> Tuple[bool, str]:
    if quantity <= 0:
        return True, "ok"
    try:
        with v2_mysql_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT quantity FROM v2_jingji_user_inventory WHERE user_id = %s AND item_id = %s FOR UPDATE",
                    (user_id, item_id),
                )
                row = cur.fetchone()
                if not row or int(row["quantity"]) < quantity:
                    conn.rollback()
                    return False, "insufficient_item"
                new_q = int(row["quantity"]) - quantity
                cur.execute(
                    "UPDATE v2_jingji_user_inventory SET quantity = %s WHERE user_id = %s AND item_id = %s",
                    (new_q, user_id, item_id),
                )
                conn.commit()
                return True, "ok"
    except Exception as e:
        logger.warning("remove_from_inventory failed: %s", e)
        return False, "error"


def fetch_points_logs(user_id: int, page: int = 1, size: int = 20) -> Tuple[List[Dict[str, Any]], int]:
    try:
        with v2_mysql_conn() as conn:
            offset = max(0, (page - 1) * size)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM v2_youxi_points_logs WHERE user_id = %s",
                    (user_id,),
                )
                total = int((cur.fetchone() or {}).get("c", 0))
                cur.execute(
                    """
                    SELECT amount, source, source_detail, created_at
                    FROM v2_youxi_points_logs
                    WHERE user_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, size, offset),
                )
                rows = list(cur.fetchall() or [])
            return rows, total
    except Exception as e:
        logger.warning("fetch_points_logs failed: %s", e)
        return [], 0


def purchase_listing_atomic(
    user_id: int,
    listing_id: int,
    currency_item_id: int,
    cost: int,
    grant_item_id: int,
    grant_quantity: int,
) -> Tuple[bool, str, Optional[int]]:
    """
    单事务：扣货币、加背包、若货币为 1001 则同步 v2_youxi_states.destiny_points。
    返回 (ok, error_code, new_currency_balance)。
    """
    if cost < 0 or grant_quantity <= 0:
        return False, "invalid_params", None
    try:
        with v2_mysql_conn() as conn:
            if hasattr(conn, "get_autocommit"):
                prev_autocommit = conn.get_autocommit()
            else:
                prev_autocommit = bool(getattr(conn, "autocommit", True))
            conn.autocommit(False)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT balance FROM v2_jingji_user_currencies
                        WHERE user_id = %s AND currency_item_id = %s FOR UPDATE
                        """,
                        (user_id, currency_item_id),
                    )
                    row = cur.fetchone()
                    if row is None:
                        cur.execute(
                            "SELECT destiny_points FROM v2_youxi_states WHERE user_id = %s FOR UPDATE",
                            (user_id,),
                        )
                        gs = cur.fetchone()
                        initial = int(gs["destiny_points"]) if gs else 0
                        if currency_item_id != DESTINY_CURRENCY_ITEM_ID:
                            conn.rollback()
                            return False, "no_currency_row", None
                        cur.execute(
                            """
                            INSERT INTO v2_jingji_user_currencies (user_id, currency_item_id, balance)
                            VALUES (%s, %s, %s)
                            """,
                            (user_id, currency_item_id, initial),
                        )
                        bal = initial
                    else:
                        bal = int(row["balance"])
                    if bal < cost:
                        conn.rollback()
                        return False, "insufficient_funds", None
                    new_bal = bal - cost
                    cur.execute(
                        """
                        UPDATE v2_jingji_user_currencies SET balance = %s
                        WHERE user_id = %s AND currency_item_id = %s
                        """,
                        (new_bal, user_id, currency_item_id),
                    )
                    if currency_item_id == DESTINY_CURRENCY_ITEM_ID:
                        cur.execute(
                            "UPDATE v2_youxi_states SET destiny_points = %s WHERE user_id = %s",
                            (new_bal, user_id),
                        )
                    cur.execute(
                        """
                        INSERT INTO v2_jingji_user_inventory (user_id, item_id, quantity)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
                        """,
                        (user_id, grant_item_id, grant_quantity),
                    )
                    cur.execute(
                        """
                        INSERT INTO v2_youxi_points_logs (user_id, amount, source, source_detail)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, -cost, "shop_purchase", f"listing_{listing_id}"),
                    )
                conn.commit()
                return True, "ok", new_bal
            except Exception:
                conn.rollback()
                raise
            finally:
                try:
                    conn.autocommit(prev_autocommit)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("purchase_listing_atomic failed: %s", e)
        return False, "transaction_failed", None

# -*- coding: utf-8 -*-
"""V2 游戏状态 API（持久化 MySQL），替代 game_mock。"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.api.v2.game_state_builder import build_game_state_payload
from server.api.v2.v2_guest_deps import get_or_create_user_id
from server.services.v2 import game_dao, points_service, xp_service

router = APIRouter()


class XpAddBody(BaseModel):
    amount: int = Field(..., ge=1, le=1_000_000)
    source: str = Field(..., min_length=1, max_length=50)
    source_detail: Optional[str] = Field(None, max_length=200)


class PointsAddBody(BaseModel):
    amount: int = Field(..., ge=-1_000_000, le=1_000_000)
    source: str = Field(..., min_length=1, max_length=50)
    source_detail: Optional[str] = Field(None, max_length=200)


def _state_or_error(user_id: int) -> Dict[str, Any]:
    data = build_game_state_payload(user_id)
    if not data:
        return {"code": 1, "message": "game_state_unavailable", "data": None}
    return {"code": 0, "message": "success", "data": data}


@router.get("/state")
def get_game_state(user_id: int = Depends(get_or_create_user_id)):
    return _state_or_error(user_id)


@router.post("/xp/add")
def add_xp_endpoint(body: XpAddBody, user_id: int = Depends(get_or_create_user_id)):
    r = xp_service.add_xp(user_id, body.amount, body.source, body.source_detail)
    if not r.get("ok"):
        return {"code": 2, "message": r.get("error", "xp_failed"), "data": r}
    state = build_game_state_payload(user_id)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "xp_result": r,
            "state": state,
        },
    }


@router.post("/points/add")
def add_points_endpoint(body: PointsAddBody, user_id: int = Depends(get_or_create_user_id)):
    r = points_service.add_points(user_id, body.amount, body.source, body.source_detail)
    if not r.get("ok"):
        return {"code": 3, "message": r.get("error", "points_failed"), "data": r}
    state = build_game_state_payload(user_id)
    return {
        "code": 0,
        "message": "success",
        "data": {"points_result": r, "state": state},
    }


@router.post("/tree/water")
def water_tree(user_id: int = Depends(get_or_create_user_id)):
    row = game_dao.get_game_state_row(user_id)
    if not row:
        return {"code": 1, "message": "game_state_unavailable", "data": None}
    today = date.today()
    w = row.get("tree_last_water_date")
    if w is not None:
        wd = w.date() if hasattr(w, "date") else w
        if wd == today:
            return {
                "code": 4,
                "message": "already_watered_today",
                "data": {"tree_water_today": True},
            }

    xp_service.add_xp(user_id, 5, "tree_water", None)
    points_service.add_points(user_id, 2, "tree_water", None)
    game_dao.update_game_state(user_id, tree_last_water_date=today)

    state = build_game_state_payload(user_id)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "tree_level": state["tree_level"] if state else row["tree_level"],
            "reward": {"xp": 5, "destiny_points": 2},
            "tree_water_today": True,
            "state": state,
        },
    }

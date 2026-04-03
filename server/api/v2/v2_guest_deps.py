# -*- coding: utf-8 -*-
"""V2 匿名访客：请求头 X-V2-Guest-Token。"""

from __future__ import annotations

from fastapi import Header, HTTPException

from server.services.v2 import profile_dao, game_dao

GUEST_HEADER = "X-V2-Guest-Token"


def get_or_create_user_id(x_v2_guest_token: str | None = Header(None, alias="X-V2-Guest-Token")) -> int:
    if not x_v2_guest_token or len(x_v2_guest_token.strip()) < 8:
        raise HTTPException(status_code=400, detail="missing_or_invalid_guest_token")
    token = x_v2_guest_token.strip()[:64]

    row = profile_dao.get_profile_by_guest_token(token)
    if row:
        uid = int(row["id"])
        if not game_dao.get_game_state_row(uid):
            game_dao.create_game_state(uid)
        return uid

    uid = profile_dao.create_profile(token)
    if uid is None:
        row2 = profile_dao.get_profile_by_guest_token(token)
        if not row2:
            raise HTTPException(status_code=503, detail="profile_create_failed")
        uid = int(row2["id"])
    if not game_dao.get_game_state_row(uid):
        game_dao.create_game_state(uid)
    return uid

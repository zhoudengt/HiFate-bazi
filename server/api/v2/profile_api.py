# -*- coding: utf-8 -*-
"""V2 匿名用户档案：昵称、头像（本地上传）。"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from server.api.v2.game_state_builder import build_game_state_payload
from server.api.v2.v2_guest_deps import get_or_create_user_id
from server.services.v2 import profile_dao

logger = logging.getLogger(__name__)

router = APIRouter()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_AVATAR_DIR = Path(_PROJECT_ROOT) / "uploads" / "v2" / "avatars"
_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class ProfileUpdateBody(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)


@router.get("/me")
def get_me(user_id: int = Depends(get_or_create_user_id)):
    row = profile_dao.get_profile_by_id(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="profile_not_found")
    state = build_game_state_payload(user_id)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": str(row["id"]),
            "nickname": row["nickname"],
            "avatar_url": row["avatar_url"],
            "game": state,
        },
    }


@router.put("/me")
def put_me(body: ProfileUpdateBody, user_id: int = Depends(get_or_create_user_id)):
    ok = profile_dao.update_nickname(user_id, body.nickname)
    if not ok:
        return {"code": 1, "message": "update_failed", "data": None}
    row = profile_dao.get_profile_by_id(user_id)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": str(row["id"]) if row else str(user_id),
            "nickname": row["nickname"] if row else body.nickname,
            "avatar_url": row["avatar_url"] if row else None,
        },
    }


@router.post("/avatar")
def post_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(get_or_create_user_id),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="unsupported_image_type")

    try:
        _AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        fn = f"{user_id}_{uuid.uuid4().hex}{ext}"
        path = _AVATAR_DIR / fn
        content = file.file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="file_too_large")
        path.write_bytes(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("v2 avatar save failed: %s", e)
        raise HTTPException(status_code=500, detail="save_failed") from e

    public_url = f"/uploads/v2/avatars/{fn}"
    profile_dao.update_avatar_url(user_id, public_url)
    return {"code": 0, "message": "success", "data": {"avatar_url": public_url}}

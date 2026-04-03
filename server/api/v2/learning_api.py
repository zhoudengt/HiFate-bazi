# -*- coding: utf-8 -*-
"""V2 学堂 API：章节、关卡、测验、通关奖励（替代 learning_mock）。"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.api.v2.game_state_builder import build_game_state_payload
from server.api.v2.v2_guest_deps import get_or_create_user_id
from server.services.v2 import learning_service

router = APIRouter()


class CompleteBody(BaseModel):
    answers: List[int] = Field(default_factory=list)


@router.get("/chapters")
def get_chapters(user_id: int = Depends(get_or_create_user_id)):
    return {
        "code": 0,
        "message": "success",
        "data": learning_service.get_chapters_payload(user_id),
    }


@router.get("/chapters/{chapter_id}/stages")
def get_chapter_stages(chapter_id: int, user_id: int = Depends(get_or_create_user_id)):
    d = learning_service.get_stages_payload(user_id, chapter_id)
    if d.get("error"):
        return {"code": 1, "message": d["error"], "data": None}
    return {"code": 0, "message": "success", "data": d}


@router.get("/stages/{stage_sn}/detail")
def get_stage_detail(stage_sn: int, user_id: int = Depends(get_or_create_user_id)):
    d = learning_service.get_stage_detail(user_id, stage_sn)
    if d.get("error"):
        return {"code": 2, "message": d["error"], "data": None}
    return {"code": 0, "message": "success", "data": d}


@router.get("/stages/{stage_sn}/quiz")
def get_stage_quiz(stage_sn: int, user_id: int = Depends(get_or_create_user_id)):
    d = learning_service.get_quiz_payload(user_id, stage_sn)
    if d.get("error"):
        return {"code": 3, "message": d["error"], "data": None}
    return {"code": 0, "message": "success", "data": d}


@router.post("/stages/{stage_sn}/complete")
def post_stage_complete(
    stage_sn: int,
    body: CompleteBody,
    user_id: int = Depends(get_or_create_user_id),
):
    r = learning_service.complete_stage(user_id, stage_sn, body.answers)
    if not r.get("ok"):
        code_map = {"level_not_found": 4, "level_locked": 5, "invalid_answers": 6}
        return {
            "code": code_map.get(r.get("error"), 9),
            "message": r.get("error", "complete_failed"),
            "data": r,
        }
    state = build_game_state_payload(user_id)
    out = {**r, "state": state}
    return {"code": 0, "message": "success", "data": out}

# -*- coding: utf-8 -*-
"""V2 任务 API（替换 quest_mock）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from server.api.v2.v2_guest_deps import get_or_create_user_id
from server.services.v2 import quest_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview")
async def quest_overview(user_id: int = Depends(get_or_create_user_id)):
    data = quest_service.get_quest_overview(user_id)
    return {"code": 0, "message": "success", "data": data}


class ClaimDailyRequest(BaseModel):
    quest_config_id: int


@router.post("/claim-daily")
async def claim_daily(req: ClaimDailyRequest, user_id: int = Depends(get_or_create_user_id)):
    result = quest_service.claim_daily_reward(user_id, req.quest_config_id)
    if not result.get("ok"):
        return {"code": 1, "message": result.get("error", "failed"), "data": result}
    return {"code": 0, "message": "success", "data": result}


class ClaimMainRequest(BaseModel):
    quest_id: int


@router.post("/claim-main")
async def claim_main(req: ClaimMainRequest, user_id: int = Depends(get_or_create_user_id)):
    result = quest_service.claim_main_reward(user_id, req.quest_id)
    if not result.get("ok"):
        return {"code": 1, "message": result.get("error", "failed"), "data": result}
    return {"code": 0, "message": "success", "data": result}


class ClaimBoxRequest(BaseModel):
    box_config_id: int


@router.post("/claim-box")
async def claim_box(req: ClaimBoxRequest, user_id: int = Depends(get_or_create_user_id)):
    result = quest_service.claim_box_reward(user_id, req.box_config_id)
    if not result.get("ok"):
        return {"code": 1, "message": result.get("error", "failed"), "data": result}
    return {"code": 0, "message": "success", "data": result}


class RecordActionRequest(BaseModel):
    tasktype: int


@router.post("/record-action")
async def record_action(req: RecordActionRequest, user_id: int = Depends(get_or_create_user_id)):
    result = quest_service.record_daily_action(user_id, req.tasktype)
    if result is None:
        return {"code": 1, "message": "no_matching_quest", "data": None}
    return {"code": 0, "message": "success", "data": result}

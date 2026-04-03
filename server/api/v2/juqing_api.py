# -*- coding: utf-8 -*-
"""V2 剧情 API（只读配置，数据来自 juqing_service 内存缓存）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from server.services.v2 import juqing_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dialogue/{dialogue_id}")
async def get_story_dialogue(dialogue_id: int):
    lines = juqing_service.get_dialogue(dialogue_id)
    return {"code": 0, "message": "success", "data": {"lines": lines}}

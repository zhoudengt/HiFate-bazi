"""V2 任务 Mock API"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

MOCK_QUESTS = {
    "daily": [
        {"code": "daily_prayer", "name": "每日祈福", "description": "完成一次祈福", "progress": 0, "target": 1, "completed": False, "claimed": False, "rewards": {"xp": 10, "destiny_points": 5}},
        {"code": "daily_learn", "name": "学习一课", "description": "完成一节学堂课程", "progress": 0, "target": 1, "completed": False, "claimed": False, "rewards": {"xp": 15, "destiny_points": 8}},
        {"code": "daily_cast", "name": "完成一次起卦", "description": "使用六爻起卦一次", "progress": 0, "target": 1, "completed": False, "claimed": False, "rewards": {"xp": 20, "destiny_points": 10}},
    ],
    "weekly": [
        {"code": "weekly_cast3", "name": "周常起卦", "description": "本周完成3次起卦", "progress": 1, "target": 3, "completed": False, "claimed": False, "rewards": {"xp": 50, "destiny_points": 30}},
        {"code": "weekly_learn5", "name": "周常学习", "description": "本周学习5节课程", "progress": 2, "target": 5, "completed": False, "claimed": False, "rewards": {"xp": 60, "destiny_points": 35}},
    ],
    "main": [
        {"code": "main_first_cast", "name": "初入道门", "description": "完成第一次六爻起卦", "progress": 1, "target": 1, "completed": True, "claimed": True, "rewards": {"xp": 100, "destiny_points": 50}},
    ],
    "achieve": [],
}


@router.get("/list")
async def quest_list(type: str = "daily"):
    quests = MOCK_QUESTS.get(type, [])
    return {"code": 0, "message": "success", "data": {"quests": quests}}


class ClaimRequest(BaseModel):
    quest_code: str


@router.post("/claim")
async def claim_quest(req: ClaimRequest):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "rewards": {"xp": 10, "destiny_points": 5},
            "new_balance": {"xp": 290, "points": 155},
        },
    }

"""V2 祈福 Mock API"""

from fastapi import APIRouter

router = APIRouter()

_prayed_today = False


@router.post("/pray")
async def pray():
    global _prayed_today
    _prayed_today = True
    return {
        "code": 0,
        "message": "success",
        "data": {
            "message": "上上签 — 风调雨顺，万事如意。\n\n今日宜：求财、出行、签约。\n今日忌：诉讼、动土。",
            "rewards": {"xp": 5, "destiny_points": 3},
            "special": None,
        },
    }


@router.get("/status")
async def prayer_status():
    return {
        "code": 0,
        "message": "success",
        "data": {"prayed_today": _prayed_today, "streak_days": 7},
    }

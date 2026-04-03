"""V2 游戏状态 Mock API — [DEPRECATED] 已由 server.api.v2.game_api 替代，路由不再注册。"""

from fastapi import APIRouter

router = APIRouter()

MOCK_STATE = {
    "level": 3,
    "xp": 280,
    "xp_to_next": 600,
    "destiny_points": 150,
    "tree_level": 2,
    "tree_water_today": False,
    "buildings": [
        {"code": "caishen", "name": "财神殿", "unlocked": True, "level": 1},
        {"code": "ganqing", "name": "感情殿", "unlocked": True, "level": 1},
        {"code": "shiye", "name": "事业殿", "unlocked": True, "level": 1},
        {"code": "exchange", "name": "兑换殿", "unlocked": True, "level": 1},
        {"code": "prayer", "name": "祈福", "unlocked": True, "level": 1},
        {"code": "tree", "name": "生命之树", "unlocked": True, "level": 2},
        {"code": "quest", "name": "任务中心", "unlocked": True, "level": 1},
        {"code": "academy", "name": "学堂", "unlocked": True, "level": 1},
    ],
}


@router.get("/state")
async def get_game_state():
    return {"code": 0, "message": "success", "data": MOCK_STATE}


@router.post("/tree/water")
async def water_tree():
    MOCK_STATE["tree_water_today"] = True
    return {
        "code": 0,
        "message": "success",
        "data": {
            "tree_level": MOCK_STATE["tree_level"],
            "reward": {"xp": 5, "destiny_points": 2},
            "tree_water_today": True,
        },
    }

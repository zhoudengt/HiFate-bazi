"""V2 学堂 Mock API — [DEPRECATED] 已由 server.api.v2.learning_api 替代，路由不再注册。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/chapters")
async def get_chapters():
    return {
        "code": 0,
        "message": "success",
        "data": {
            "chapters": [
                {"code": "ch1", "name": "风回忆来", "description": "认识阴阳与五行的基本概念", "cover": "", "sections_count": 5, "completed_pct": 40, "unlocked": True},
                {"code": "ch2", "name": "命悬一线", "description": "天干地支与六十甲子", "cover": "", "sections_count": 4, "completed_pct": 0, "unlocked": True},
                {"code": "ch3", "name": "熬路前建", "description": "六爻基础：卦象与爻位", "cover": "", "sections_count": 6, "completed_pct": 0, "unlocked": False},
                {"code": "ch4", "name": "苦子知甘", "description": "六爻进阶：六亲与六神", "cover": "", "sections_count": 5, "completed_pct": 0, "unlocked": False},
            ]
        },
    }


@router.get("/chapters/{code}/sections")
async def get_sections(code: str):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "sections": [
                {"code": f"{code}_s1", "name": "阴阳的起源", "cards_count": 3, "completed_pct": 100},
                {"code": f"{code}_s2", "name": "五行相生相克", "cards_count": 4, "completed_pct": 50},
                {"code": f"{code}_s3", "name": "天人合一", "cards_count": 3, "completed_pct": 0},
            ]
        },
    }


@router.get("/sections/{code}/cards")
async def get_cards(code: str):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "cards": [
                {"id": 1, "type": "text", "title": "阴与阳", "content": "阴阳是中国古代哲学的基本概念，代表着宇宙间一切事物的两种对立统一的力量。阳代表光明、积极、外向；阴代表黑暗、消极、内敛。", "read": True},
                {"id": 2, "type": "text", "title": "太极图", "content": "太极图是阴阳思想的图形化表达。黑白两条鱼形图案首尾相连，象征阴阳互根、消长转化的永恒规律。", "read": True},
                {"id": 3, "type": "text", "title": "阴阳在生活中", "content": "日与夜、寒与暑、男与女、动与静……阴阳无处不在。理解阴阳，就是理解世界运行的基本规律。", "read": False},
            ]
        },
    }


@router.get("/sections/{code}/quiz")
async def get_quiz(code: str):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "quiz_id": 1,
            "questions": [
                {"id": "q1", "text": "下列哪个属于「阳」的属性？", "options": ["黑暗", "光明", "寒冷", "内敛"], "type": "single"},
                {"id": "q2", "text": "太极图中黑色部分代表？", "options": ["阳", "阴", "五行", "八卦"], "type": "single"},
                {"id": "q3", "text": "阴阳关系的核心特征是？", "options": ["绝对对立", "互根消长", "静止不变", "无关联"], "type": "single"},
            ],
        },
    }


@router.post("/cards/{card_id}/read")
async def mark_read(card_id: int):
    return {"code": 0, "message": "success", "data": {"xp_earned": 2}}


@router.post("/quizzes/{quiz_id}/submit")
async def submit_quiz(quiz_id: int):
    return {
        "code": 0,
        "message": "success",
        "data": {"score": 100, "passed": True, "rewards": {"xp": 20, "destiny_points": 10}},
    }

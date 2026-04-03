"""V2 经济系统 Mock API — [DEPRECATED] 已由 server.api.v2.economy_api 替代，路由不再注册。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/balance")
async def get_balance():
    return {"code": 0, "message": "success", "data": {"destiny_points": 150}}


@router.get("/transactions")
async def get_transactions(page: int = 1, size: int = 20):
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {"amount": 10, "type": "earn", "source": "quest", "description": "完成每日祈福", "created_at": "2026-03-25T10:00:00"},
                {"amount": -20, "type": "spend", "source": "liuyao", "description": "AI 单次解读", "created_at": "2026-03-24T15:30:00"},
                {"amount": 50, "type": "earn", "source": "quest", "description": "完成主线任务", "created_at": "2026-03-23T09:00:00"},
            ],
            "total": 3,
        },
    }


@router.get("/shop/items")
async def shop_items():
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [
                {"code": "hint_scroll", "name": "提示卷", "description": "获得一次额外提示", "icon": "", "price_points": 10, "price_money": None, "category": "consumable"},
                {"code": "compass", "name": "抉择罗盘", "description": "帮助做出重大决策", "icon": "", "price_points": 50, "price_money": None, "category": "consumable"},
                {"code": "ai_single", "name": "AI 单次咨询", "description": "AI 大师单次解答", "icon": "", "price_points": 20, "price_money": 1.99, "category": "consumable"},
                {"code": "ai_deep", "name": "AI 深度问答", "description": "AI 大师深度分析", "icon": "", "price_points": 100, "price_money": 6.99, "category": "consumable"},
            ]
        },
    }


@router.get("/inventory")
async def inventory():
    return {
        "code": 0,
        "message": "success",
        "data": {"items": [{"code": "hint_scroll", "name": "提示卷", "icon": "", "quantity": 2}]},
    }

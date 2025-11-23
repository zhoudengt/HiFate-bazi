from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from ...services.bazi_service import BaziService

router = APIRouter()

bazi_service = BaziService()


@router.post("/", summary="输入生日信息生成八字分析")
async def analyze_bazi(
    birthday: str = Body(..., embed=True, description="生日，格式：YYYY-MM-DD 或 YYYY-MM-DD HH"),
    calendar_type: str = Body(
        default="solar",
        embed=True,
        description="历法类型：solar（阳历）或 lunar（阴历），默认阳历",
    ),
    location: str | None = Body(
        default=None, embed=True, description="出生地（可选，用于精准换算时区）"
    ),
):
    """
    - 根据生日信息调用内置八字工具，生成命盘和五行喜忌
    """
    result = bazi_service.analyze(
        birthday=birthday, calendar_type=calendar_type, location=location
    )
    return JSONResponse(content=result)






























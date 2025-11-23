from fastapi import FastAPI

from .routers import face_router, hand_router, fengshui_router, bazi_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="面相手相与风水推荐服务",
        description="提供面相分析、手相分析、八字推算与办公室摆件建议的综合服务",
        version="0.1.0",
    )

    app.include_router(face_router.router, prefix="/analysis/face", tags=["面相分析"])
    app.include_router(hand_router.router, prefix="/analysis/hand", tags=["手相分析"])
    app.include_router(bazi_router.router, prefix="/analysis/bazi", tags=["八字分析"])
    app.include_router(
        fengshui_router.router, prefix="/recommendations/fengshui", tags=["办公室摆件建议"]
    )

    return app


app = create_app()






























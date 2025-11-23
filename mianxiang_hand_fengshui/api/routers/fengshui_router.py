import json
from typing import Any

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ...services.recommendation_service import FengshuiRecommendationService

router = APIRouter()

recommendation_service = FengshuiRecommendationService()


@router.post("/", summary="基于分析结果生成办公室摆件建议")
async def recommend_decor(
    workspace_image: UploadFile | None = File(
        default=None, description="办公环境照片（可选，上传则进行图像分析）"
    ),
    face_profile: str | None = Form(
        default=None, description="面相分析结果JSON（可选，用于增强建议）"
    ),
    hand_profile: str | None = Form(
        default=None, description="手相分析结果JSON（可选，用于增强建议）"
    ),
    bazi_profile: str | None = Form(
        default=None, description="八字分析结果JSON（可选，用于增强建议）"
    ),
):
    """
    - 根据输入的面相、手相、八字特征，生成办公室摆件的类型、摆放位置和注意事项
    - 若上传办公室图片，附加图像分析结果
    - 若缺失某项，将自动采用默认规则
    """
    face_payload = _loads_optional_json(face_profile)
    hand_payload = _loads_optional_json(hand_profile)
    bazi_payload = _loads_optional_json(bazi_profile)

    response = await recommendation_service.generate_response(
        workspace_image=workspace_image,
        face_profile=face_payload,
        hand_profile=hand_payload,
        bazi_profile=bazi_payload,
    )

    return JSONResponse(content=response)


def _loads_optional_json(payload: str | None) -> dict[str, Any] | None:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


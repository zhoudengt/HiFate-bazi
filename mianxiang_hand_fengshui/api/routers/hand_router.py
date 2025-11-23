from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from ...services.hand_service import HandAnalysisService
from ...services.report_service import ReportAssembler

router = APIRouter()

hand_service = HandAnalysisService()
report_service = ReportAssembler()


@router.post("/", summary="上传手掌图像进行手相分析")
async def analyze_hand(image: UploadFile = File(..., description="手掌正面清晰照片")):
    """
    - 提取手部关键点和掌纹
    - 调用手相规则引擎，生成解析结果
    """
    analysis_result = await hand_service.analyze(image=image)
    report = report_service.render_hand_section(analysis_result)
    return JSONResponse(content=report)






























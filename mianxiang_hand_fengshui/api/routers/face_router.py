from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ...services.face_service import FaceAnalysisService
from ...services.report_service import ReportAssembler

router = APIRouter()

face_service = FaceAnalysisService()
report_service = ReportAssembler()


@router.post("/", summary="上传人脸图像进行面相分析")
async def analyze_face(
    image: UploadFile = File(..., description="包含正面人脸的清晰照片"),
    birthday: str | None = Form(
        default=None, description="八字信息（YYYY-MM-DD 或 YYYY-MM-DD HH 格式）"
    ),
):
    """
    - 读取人脸图像，调用面相特征提取逻辑
    - 可选：结合生日信息，返回面相 + 八字综合分析
    """
    analysis_result = await face_service.analyze(image=image, birthday=birthday)
    report = report_service.render_face_section(analysis_result)
    return JSONResponse(content=report)






























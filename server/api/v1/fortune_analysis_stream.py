#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面相手相分析 API 接口 - 流式版本
提供流式 HTTP 接口，使用 Server-Sent Events (SSE)
"""

import sys
import os
import json
import asyncio
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from server.api.base.stream_handler import generate_request_id
from pydantic import BaseModel
from typing import Optional
import grpc

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
# server/api/v1/fortune_analysis_stream.py -> 向上4级到项目根
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
sys.path.insert(0, project_root)

# 导入生成的 gRPC 代码
generated_path = os.path.join(project_root, "proto", "generated")
if generated_path not in sys.path:
    sys.path.insert(0, generated_path)

# 使用 importlib 直接从文件导入，避免模块路径问题
import importlib.util

pb2_path = os.path.join(generated_path, "fortune_analysis_pb2.py")
pb2_grpc_path = os.path.join(generated_path, "fortune_analysis_pb2_grpc.py")

if os.path.exists(pb2_path) and os.path.exists(pb2_grpc_path):
    # 从文件直接加载模块
    spec = importlib.util.spec_from_file_location("fortune_analysis_pb2", pb2_path)
    fortune_analysis_pb2 = importlib.util.module_from_spec(spec)
    sys.modules["fortune_analysis_pb2"] = fortune_analysis_pb2
    spec.loader.exec_module(fortune_analysis_pb2)
    
    spec = importlib.util.spec_from_file_location("fortune_analysis_pb2_grpc", pb2_grpc_path)
    fortune_analysis_pb2_grpc = importlib.util.module_from_spec(spec)
    sys.modules["fortune_analysis_pb2_grpc"] = fortune_analysis_pb2_grpc
    spec.loader.exec_module(fortune_analysis_pb2_grpc)
else:
    # 如果文件不存在，尝试普通导入
    try:
        import fortune_analysis_pb2
        import fortune_analysis_pb2_grpc
    except ImportError as e:
        raise ImportError(f"无法导入 fortune_analysis_pb2，文件路径: {pb2_path}, 错误: {e}")

router = APIRouter()

# 获取服务地址
FORTUNE_ANALYSIS_SERVICE_URL = os.getenv("FORTUNE_ANALYSIS_SERVICE_URL", "localhost:9001")

# 简单认证：API Key（必须从环境变量读取）
# 安全规范：生产环境不允许使用默认值
_app_env = os.getenv("APP_ENV", "development").lower()
if _app_env == "production":
    FORTUNE_ANALYSIS_API_KEY = os.getenv("FORTUNE_ANALYSIS_API_KEY")
    if not FORTUNE_ANALYSIS_API_KEY:
        import logging
        logging.getLogger(__name__).warning(
            "⚠️ 生产环境未配置 FORTUNE_ANALYSIS_API_KEY，fortune_analysis 接口将拒绝所有请求"
        )
else:
    # 开发环境：允许使用默认值（方便本地调试）
    FORTUNE_ANALYSIS_API_KEY = os.getenv("FORTUNE_ANALYSIS_API_KEY", "dev_fortune_analysis_key")

# 导入图像验证器和流式分析器
# 添加服务目录到路径，确保能正确导入
fortune_service_dir = os.path.join(project_root, "services", "fortune_analysis")
if fortune_service_dir not in sys.path:
    sys.path.insert(0, fortune_service_dir)

try:
    from image_validator import ImageValidator
    image_validator = ImageValidator()
    IMAGE_VALIDATOR_AVAILABLE = True
    logger.info("✅ 图像验证器导入成功")
except ImportError as e:
    logger.warning(f"⚠️  图像验证器导入失败: {e}，将跳过图像类型验证")
    image_validator = None
    IMAGE_VALIDATOR_AVAILABLE = False

# 导入流式分析器（分别导入手相和面相，互不影响）
try:
    from hand_analyzer_stream import HandAnalyzerStream
    hand_analyzer_stream = HandAnalyzerStream()
    HAND_STREAM_ANALYZER_AVAILABLE = True
    logger.info("✅ 手相流式分析器导入成功")
except ImportError as e:
    import traceback
    logger.warning(f"⚠️  手相流式分析器导入失败: {e}", exc_info=True)
    hand_analyzer_stream = None
    HAND_STREAM_ANALYZER_AVAILABLE = False

try:
    from face_analyzer_stream import FaceAnalyzerStream
    face_analyzer_stream = FaceAnalyzerStream()
    FACE_STREAM_ANALYZER_AVAILABLE = True
    logger.info("✅ 面相流式分析器导入成功")
except ImportError as e:
    import traceback
    logger.warning(f"⚠️  面相流式分析器导入失败: {e}", exc_info=True)
    face_analyzer_stream = None
    FACE_STREAM_ANALYZER_AVAILABLE = False


def get_grpc_client():
    """获取 gRPC 客户端地址"""
    address = FORTUNE_ANALYSIS_SERVICE_URL
    if address.startswith("http://"):
        address = address[7:]
    elif address.startswith("https://"):
        address = address[8:]
    
    if ":" not in address:
        address = f"{address}:9001"
    
    return address


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    验证 API Key（简单认证）
    
    Args:
        x_api_key: 从请求头获取的 API Key
        
    Returns:
        API Key 字符串
        
    Raises:
        HTTPException: 如果 API Key 无效
    """
    if not x_api_key or x_api_key != FORTUNE_ANALYSIS_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="无效的 API Key，请在请求头中提供正确的 X-API-Key"
        )
    return x_api_key


async def analyze_hand_stream_generator(image_bytes: bytes, image_format: str, 
                                        solar_date: Optional[str], solar_time: Optional[str], 
                                        gender: Optional[str], use_bazi: bool,
                                        request_id: Optional[str] = None):
    """手相分析流式生成器（真正的流式响应）"""
    try:
        request_id = request_id or generate_request_id()
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"

        # 发送开始消息（包含显示指令）
        start_msg = {
            'type': 'start',
            'statusText': '开始分析手相',
            'showGrid': True,
            'showStatus': True,
            'showPlayButton': True
        }
        yield f"data: {json.dumps(start_msg, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
        
        # 使用手相流式分析器（真正的流式响应）
        if HAND_STREAM_ANALYZER_AVAILABLE and hand_analyzer_stream:
            logger.info("✅ 使用手相流式分析器（真正的流式响应）")
            try:
                # 使用手相流式分析器
                async for result in hand_analyzer_stream.analyze_hand_stream(
                    image_bytes=image_bytes,
                    image_format=image_format,
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    use_bazi=use_bazi,
                    progress_callback=lambda text: None  # 进度在内部处理
                ):
                    logger.debug(f"📤 流式分析器返回: type={result.get('type')}, statusText={result.get('statusText', '')}")
                    
                    # 转换结果格式
                    if result.get('type') == 'progress':
                        progress_msg = {
                            'type': 'progress',
                            'statusText': result.get('statusText', '正在分析...'),
                            'showGrid': True,
                            'showStatus': True,
                            'showPlayButton': True
                        }
                        yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0)
                    elif result.get('type') == 'complete':
                        data = result.get('data', {})
                        logger.debug(f"📤 发送complete消息，data类型: {type(data)}, success: {data.get('success') if isinstance(data, dict) else 'N/A'}")
                        complete_msg = {
                            'type': 'complete',
                            'data': data,
                            'statusText': '分析完成',
                            'showGrid': False,
                            'showStatus': False,
                            'showPlayButton': False
                        }
                        yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
                        logger.debug("✅ complete消息已发送到客户端")
                    elif result.get('type') == 'error':
                        error_msg = {
                            'type': 'error',
                            'error': result.get('error', '分析失败'),
                            'statusText': '分析失败',
                            'showGrid': False,
                            'showStatus': False,
                            'showPlayButton': False
                        }
                        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                        logger.error("❌ error消息已发送到客户端")
            except Exception as stream_error:
                import traceback
                error_detail = f"流式分析器异常: {str(stream_error)}\n{traceback.format_exc()}"
                logger.error(f"❌ {error_detail}")
                error_msg = {
                    'type': 'error',
                    'error': f"流式分析失败: {str(stream_error)}",
                    'statusText': '分析失败',
                    'showGrid': False,
                    'showStatus': False,
                    'showPlayButton': False
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        else:
            logger.warning("⚠️  流式分析器不可用，使用 gRPC（非流式，较慢）")
            # 降级方案：使用 gRPC（非流式）
            # 先验证图像
            if IMAGE_VALIDATOR_AVAILABLE and image_validator:
                logger.debug("🔍 验证图像...")
                is_valid, error_msg = image_validator.validate_hand_image(image_bytes)
                logger.debug(f"验证结果: 有效={is_valid}, 错误={error_msg}")
                if not is_valid:
                    error_response = {
                        'type': 'error',
                        'error': error_msg,
                        'statusText': '图像验证失败',
                        'showGrid': False,
                        'showStatus': False,
                        'showPlayButton': False
                    }
                    yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                    return
            else:
                logger.warning("⚠️  图像验证器不可用，跳过验证")
            
            # 构建 gRPC 请求
            request = fortune_analysis_pb2.HandAnalysisRequest()
            request.image.image_bytes = image_bytes
            request.image.image_format = image_format
            request.image.filename = f"hand.{image_format}"
            
            # 八字信息
            if use_bazi and solar_date and solar_time and gender:
                request.bazi_info.solar_date = solar_date
                request.bazi_info.solar_time = solar_time
                request.bazi_info.gender = gender
                request.bazi_info.use_bazi = True
            else:
                request.bazi_info.use_bazi = False
            
            # 调用 gRPC 服务
            address = get_grpc_client()
            
            with grpc.insecure_channel(address) as channel:
                stub = fortune_analysis_pb2_grpc.FortuneAnalysisServiceStub(channel)
                response = stub.AnalyzeHand(request, timeout=60.0)
            
            if response.success:
                report = json.loads(response.report_json) if response.report_json else {}
                complete_msg = {
                    'type': 'complete',
                    'data': report,
                    'statusText': '分析完成',
                    'showGrid': False,
                    'showStatus': False,
                    'showPlayButton': False
                }
                yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            else:
                error_msg = {
                    'type': 'error',
                    'error': response.error_message,
                    'statusText': '分析失败',
                    'showGrid': False,
                    'showStatus': False,
                    'showPlayButton': False
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        import traceback
        error_msg = f"手相分析失败: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"


@router.post("/fortune/hand/analyze/stream", summary="手相分析（流式）")
async def analyze_hand_stream(
    image: UploadFile = File(..., description="手掌照片"),
    solar_date: Optional[str] = Form(None, description="阳历日期 YYYY-MM-DD"),
    solar_time: Optional[str] = Form(None, description="出生时间 HH:MM"),
    gender: Optional[str] = Form(None, description="性别 male/female"),
    use_bazi: bool = Form(True, description="是否结合八字分析"),
    api_key: str = Depends(verify_api_key)
):
    """
    手相分析接口（流式版本）
    使用 Server-Sent Events (SSE) 实时返回分析进度和结果
    
    需要认证：在请求头中提供 X-API-Key
    """
    try:
        # 读取图像数据
        image_bytes = await image.read()
        image_format = image.filename.split('.')[-1] if image.filename else "jpg"
        
        return StreamingResponse(
            analyze_hand_stream_generator(
                image_bytes, image_format, solar_date, solar_time, gender, use_bazi,
                request_id=None
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"手相分析失败: {str(e)}")


async def analyze_face_stream_generator(image_bytes: bytes, image_format: str,
                                       solar_date: Optional[str], solar_time: Optional[str],
                                       gender: Optional[str], use_bazi: bool,
                                       request_id: Optional[str] = None):
    """面相分析流式生成器（真正的流式响应）"""
    try:
        request_id = request_id or generate_request_id()
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"

        # 发送开始消息（包含显示指令）
        start_msg = {
            'type': 'start',
            'statusText': '开始分析面相',
            'showGrid': True,
            'showStatus': True,
            'showPlayButton': True
        }
        yield f"data: {json.dumps(start_msg, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
        
        # 使用面相流式分析器（真正的流式响应）
        if FACE_STREAM_ANALYZER_AVAILABLE and face_analyzer_stream:
            logger.info("✅ 使用面相流式分析器（真正的流式响应）")
            try:
                # 使用面相流式分析器
                async for result in face_analyzer_stream.analyze_face_stream(
                    image_bytes=image_bytes,
                    image_format=image_format,
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    use_bazi=use_bazi,
                    progress_callback=lambda text: None  # 进度在内部处理
                ):
                    logger.debug(f"📤 流式分析器返回: type={result.get('type')}, statusText={result.get('statusText', '')}")
                    
                    # 转换结果格式
                    if result.get('type') == 'progress':
                        progress_msg = {
                            'type': 'progress',
                            'statusText': result.get('statusText', '正在分析...'),
                            'showGrid': True,
                            'showStatus': True,
                            'showPlayButton': True
                        }
                        yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0)
                    elif result.get('type') == 'complete':
                        data = result.get('data', {})
                        logger.debug(f"📤 发送complete消息，data类型: {type(data)}, success: {data.get('success') if isinstance(data, dict) else 'N/A'}")
                        complete_msg = {
                            'type': 'complete',
                            'data': data,
                            'statusText': '分析完成',
                            'showGrid': False,
                            'showStatus': False,
                            'showPlayButton': False
                        }
                        yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
                        logger.debug("✅ complete消息已发送到客户端")
                    elif result.get('type') == 'error':
                        error_msg = {
                            'type': 'error',
                            'error': result.get('error', '分析失败'),
                            'statusText': '分析失败',
                            'showGrid': False,
                            'showStatus': False,
                            'showPlayButton': False
                        }
                        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                        logger.error("❌ error消息已发送到客户端")
            except Exception as stream_error:
                import traceback
                error_detail = f"流式分析器异常: {str(stream_error)}\n{traceback.format_exc()}"
                logger.error(f"❌ {error_detail}")
                error_msg = {
                    'type': 'error',
                    'error': f"流式分析失败: {str(stream_error)}",
                    'statusText': '分析失败',
                    'showGrid': False,
                    'showStatus': False,
                    'showPlayButton': False
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        else:
            logger.warning("⚠️  流式分析器不可用，使用 gRPC（非流式，较慢）")
            # 降级方案：使用 gRPC（非流式）
            # 先验证图像
            if IMAGE_VALIDATOR_AVAILABLE and image_validator:
                logger.debug("🔍 验证图像...")
                is_valid, error_msg = image_validator.validate_face_image(image_bytes)
                logger.debug(f"验证结果: 有效={is_valid}, 错误={error_msg}")
                if not is_valid:
                    error_response = {
                        'type': 'error',
                        'error': error_msg,
                        'statusText': '图像验证失败',
                        'showGrid': False,
                        'showStatus': False,
                        'showPlayButton': False
                    }
                    yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                    return
            else:
                logger.warning("⚠️  图像验证器不可用，跳过验证")
            
            # 构建 gRPC 请求
            request = fortune_analysis_pb2.FaceAnalysisRequest()
            request.image.image_bytes = image_bytes
            request.image.image_format = image_format
            request.image.filename = f"face.{image_format}"
            
            # 八字信息
            if use_bazi and solar_date and solar_time and gender:
                request.bazi_info.solar_date = solar_date
                request.bazi_info.solar_time = solar_time
                request.bazi_info.gender = gender
                request.bazi_info.use_bazi = True
            else:
                request.bazi_info.use_bazi = False
            
            # 调用 gRPC 服务
            address = get_grpc_client()
            
            with grpc.insecure_channel(address) as channel:
                stub = fortune_analysis_pb2_grpc.FortuneAnalysisServiceStub(channel)
                response = stub.AnalyzeFace(request, timeout=60.0)
            
            if response.success:
                report = json.loads(response.report_json) if response.report_json else {}
                complete_msg = {
                    'type': 'complete',
                    'data': report,
                    'statusText': '分析完成',
                    'showGrid': False,
                    'showStatus': False,
                    'showPlayButton': False
                }
                yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            else:
                error_msg = {
                    'type': 'error',
                    'error': response.error_message,
                    'statusText': '分析失败',
                    'showGrid': False,
                    'showStatus': False,
                    'showPlayButton': False
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        import traceback
        error_msg = f"面相分析失败: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"


@router.post("/fortune/face/analyze/stream", summary="面相分析（流式）")
async def analyze_face_stream(
    image: UploadFile = File(..., description="头部面相照片"),
    solar_date: Optional[str] = Form(None, description="阳历日期 YYYY-MM-DD"),
    solar_time: Optional[str] = Form(None, description="出生时间 HH:MM"),
    gender: Optional[str] = Form(None, description="性别 male/female"),
    use_bazi: bool = Form(True, description="是否结合八字分析"),
    api_key: str = Depends(verify_api_key)
):
    """
    面相分析接口（流式版本）
    使用 Server-Sent Events (SSE) 实时返回分析进度和结果
    
    需要认证：在请求头中提供 X-API-Key
    """
    try:
        image_bytes = await image.read()
        image_format = image.filename.split('.')[-1] if image.filename else "jpg"
        
        return StreamingResponse(
            analyze_face_stream_generator(
                image_bytes, image_format, solar_date, solar_time, gender, use_bazi,
                request_id=None
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"面相分析失败: {str(e)}")


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面相手相分析 API 接口
提供 HTTP 接口，内部调用 gRPC 服务
"""

import sys
import os
import base64
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import grpc

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

# 导入生成的 gRPC 代码
sys.path.insert(0, os.path.join(project_root, "proto", "generated"))
import fortune_analysis_pb2
import fortune_analysis_pb2_grpc

router = APIRouter()

# 获取服务地址
FORTUNE_ANALYSIS_SERVICE_URL = os.getenv("FORTUNE_ANALYSIS_SERVICE_URL", "127.0.0.1:9005")


class FortuneAnalysisResponse(BaseModel):
    """分析响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


def get_grpc_client():
    """获取 gRPC 客户端"""
    # 解析地址
    address = FORTUNE_ANALYSIS_SERVICE_URL
    if address.startswith("http://"):
        address = address[7:]
    elif address.startswith("https://"):
        address = address[8:]
    
    if ":" not in address:
        address = f"{address}:9005"
    
    return address


@router.post("/fortune/hand/analyze", response_model=FortuneAnalysisResponse, summary="手相分析")
async def analyze_hand(
    image: UploadFile = File(..., description="手掌照片"),
    solar_date: Optional[str] = Form(None, description="阳历日期 YYYY-MM-DD"),
    solar_time: Optional[str] = Form(None, description="出生时间 HH:MM"),
    gender: Optional[str] = Form(None, description="性别 male/female"),
    use_bazi: bool = Form(True, description="是否结合八字分析")
):
    """
    手相分析接口
    - 上传手掌照片
    - 可选：提供八字信息进行融合分析
    """
    try:
        # 读取图像数据
        image_bytes = await image.read()
        
        # 构建 gRPC 请求
        request = fortune_analysis_pb2.HandAnalysisRequest()
        request.image.image_bytes = image_bytes
        request.image.image_format = image.filename.split('.')[-1] if image.filename else "jpg"
        request.image.filename = image.filename or "hand.jpg"
        
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
        
        # 转换为字典
        if response.success:
            import json
            report = json.loads(response.report_json) if response.report_json else {}
            
            return FortuneAnalysisResponse(
                success=True,
                data=report
            )
        else:
            return FortuneAnalysisResponse(
                success=False,
                error=response.error_message
            )
            
    except Exception as e:
        import traceback
        error_msg = f"手相分析失败: {str(e)}"
        print(f"❌ {error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/fortune/face/analyze", response_model=FortuneAnalysisResponse, summary="面相分析")
async def analyze_face(
    image: UploadFile = File(..., description="头部面相照片"),
    solar_date: Optional[str] = Form(None, description="阳历日期 YYYY-MM-DD"),
    solar_time: Optional[str] = Form(None, description="出生时间 HH:MM"),
    gender: Optional[str] = Form(None, description="性别 male/female"),
    use_bazi: bool = Form(True, description="是否结合八字分析")
):
    """
    面相分析接口
    - 上传头部面相照片
    - 可选：提供八字信息进行融合分析
    """
    try:
        # 读取图像数据
        image_bytes = await image.read()
        
        # 构建 gRPC 请求
        request = fortune_analysis_pb2.FaceAnalysisRequest()
        request.image.image_bytes = image_bytes
        request.image.image_format = image.filename.split('.')[-1] if image.filename else "jpg"
        request.image.filename = image.filename or "face.jpg"
        
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
        
        # 转换为字典
        if response.success:
            import json
            report = json.loads(response.report_json) if response.report_json else {}
            
            return FortuneAnalysisResponse(
                success=True,
                data=report
            )
        else:
            return FortuneAnalysisResponse(
                success=False,
                error=response.error_message
            )
            
    except Exception as e:
        import traceback
        error_msg = f"面相分析失败: {str(e)}"
        print(f"❌ {error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)


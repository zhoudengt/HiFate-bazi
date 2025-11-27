# -*- coding: utf-8 -*-
"""
面相分析V2 gRPC服务器
"""

import grpc
from concurrent import futures
import time
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from proto.generated import face_analysis_v2_pb2
from proto.generated import face_analysis_v2_pb2_grpc
from services.face_analysis_v2.service import FaceAnalysisService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceAnalysisServicer(face_analysis_v2_pb2_grpc.FaceAnalysisServiceServicer):
    """gRPC服务实现"""
    
    def __init__(self):
        self.service = FaceAnalysisService()
    
    def DetectFaceLandmarks(self, request, context):
        """检测人脸关键点"""
        try:
            result = self.service.detect_landmarks(
                request.image_data,
                request.image_format
            )
            
            # 构建响应
            response = face_analysis_v2_pb2.LandmarksResponse()
            response.success = result['success']
            response.message = result['message']
            
            # 添加关键点
            for lm in result.get('landmarks', []):
                landmark = response.landmarks.add()
                landmark.index = lm['index']
                landmark.x = lm['x']
                landmark.y = lm['y']
                landmark.z = lm.get('z', 0)
                landmark.visibility = lm.get('visibility', 1.0)
            
            # 添加映射特征点
            for mf in result.get('mapped_features', []):
                feature = response.mapped_features.add()
                feature.feature_id = mf['feature_id']
                feature.feature_name = mf['feature_name']
                feature.x = mf['x']
                feature.y = mf['y']
                feature.gongwei = mf.get('gongwei', '')
                feature.position_type = mf.get('position_type', '')
            
            return response
        
        except Exception as e:
            logger.error(f"DetectFaceLandmarks error: {e}")
            response = face_analysis_v2_pb2.LandmarksResponse()
            response.success = False
            response.message = f"错误：{str(e)}"
            return response
    
    def AnalyzeGongwei(self, request, context):
        """宫位分析"""
        try:
            result = self.service.analyze_gongwei(
                request.image_data,
                request.image_format,
                list(request.analysis_types)
            )
            
            response = face_analysis_v2_pb2.GongweiResponse()
            response.success = result['success']
            response.message = result['message']
            
            return response
        
        except Exception as e:
            logger.error(f"AnalyzeGongwei error: {e}")
            response = face_analysis_v2_pb2.GongweiResponse()
            response.success = False
            response.message = f"错误：{str(e)}"
            return response
    
    def AnalyzeFaceFeatures(self, request, context):
        """综合面相分析"""
        try:
            birth_info = None
            if request.HasField('birth_info'):
                birth_info = {
                    'year': request.birth_info.year,
                    'month': request.birth_info.month,
                    'day': request.birth_info.day,
                    'hour': request.birth_info.hour,
                    'gender': request.birth_info.gender
                }
            
            result = self.service.analyze_face_features(
                request.image_data,
                request.image_format,
                birth_info
            )
            
            response = face_analysis_v2_pb2.FaceAnalysisResponse()
            response.success = result['success']
            response.message = result['message']
            response.overall_summary = result.get('overall_summary', '')
            
            return response
        
        except Exception as e:
            logger.error(f"AnalyzeFaceFeatures error: {e}")
            response = face_analysis_v2_pb2.FaceAnalysisResponse()
            response.success = False
            response.message = f"错误：{str(e)}"
            return response


def serve(port=9010):
    """启动服务"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    face_analysis_v2_pb2_grpc.add_FaceAnalysisServiceServicer_to_server(
        FaceAnalysisServicer(), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logger.info(f"✅ 面相分析V2微服务启动成功，监听端口 {port}")
    
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        logger.info("服务停止")
        server.stop(0)


if __name__ == '__main__':
    serve()


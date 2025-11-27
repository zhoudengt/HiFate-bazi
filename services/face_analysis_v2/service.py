# -*- coding: utf-8 -*-
"""
面相分析V2微服务 - 核心服务
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
import base64
import io
from PIL import Image

from .models.landmark_detector import LandmarkDetector
from .models.feature_mapper import FeatureMapper
from .analyzers.gongwei_analyzer import GongweiAnalyzer
from .utils.geometry import GeometryCalculator


class FaceAnalysisService:
    """面相分析服务"""
    
    def __init__(self):
        self.landmark_detector = LandmarkDetector()
        self.feature_mapper = FeatureMapper()
        self.gongwei_analyzer = GongweiAnalyzer()
        self.geometry_calculator = GeometryCalculator()
    
    def detect_landmarks(self, image_data: bytes, image_format: str = 'jpg') -> Dict:
        """
        检测人脸关键点
        
        Args:
            image_data: 图片二进制数据
            image_format: 图片格式
        
        Returns:
            检测结果
        """
        try:
            # 解码图片
            image = self._decode_image(image_data, image_format)
            
            # 检测关键点
            result = self.landmark_detector.detect(image)
            
            if not result:
                return {
                    'success': False,
                    'message': '未检测到人脸',
                    'landmarks': [],
                    'mapped_features': []
                }
            
            # 映射到99个特征点
            mapped_features = self.feature_mapper.map_features(
                result['landmarks'],
                result['face_bounds']
            )
            
            return {
                'success': True,
                'message': '检测成功',
                'landmarks': result['landmarks'],
                'mapped_features': mapped_features,
                'face_bounds': result['face_bounds']
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'检测失败：{str(e)}',
                'landmarks': [],
                'mapped_features': []
            }
    
    def analyze_gongwei(self, image_data: bytes, image_format: str = 'jpg', 
                        analysis_types: List[str] = None) -> Dict:
        """
        宫位分析
        
        Args:
            image_data: 图片数据
            image_format: 图片格式
            analysis_types: 分析类型列表
        
        Returns:
            宫位分析结果
        """
        if analysis_types is None:
            analysis_types = ['gongwei', 'liuqin', 'shishen']
        
        # 先检测关键点
        detect_result = self.detect_landmarks(image_data, image_format)
        
        if not detect_result['success']:
            return {
                'success': False,
                'message': detect_result['message'],
                'gongwei_list': [],
                'liuqin_list': [],
                'shishen_list': []
            }
        
        landmarks = detect_result['landmarks']
        mapped_features = detect_result['mapped_features']
        
        # 分析各类宫位
        result = {
            'success': True,
            'message': '分析成功'
        }
        
        if 'gongwei' in analysis_types:
            result['gongwei_list'] = self.gongwei_analyzer.analyze_shisan_gongwei(
                mapped_features, landmarks
            )
        
        if 'liuqin' in analysis_types:
            result['liuqin_list'] = self.gongwei_analyzer.analyze_liuqin(
                mapped_features, landmarks
            )
        
        if 'shishen' in analysis_types:
            result['shishen_list'] = self.gongwei_analyzer.analyze_shishen(
                mapped_features, landmarks
            )
        
        return result
    
    def analyze_face_features(self, image_data: bytes, image_format: str = 'jpg',
                              birth_info: Dict = None) -> Dict:
        """
        综合面相分析
        
        Args:
            image_data: 图片数据
            image_format: 图片格式
            birth_info: 生辰信息（可选）
        
        Returns:
            完整分析结果
        """
        # 检测关键点
        detect_result = self.detect_landmarks(image_data, image_format)
        
        if not detect_result['success']:
            return {
                'success': False,
                'message': detect_result['message']
            }
        
        landmarks = detect_result['landmarks']
        mapped_features = detect_result['mapped_features']
        face_bounds = detect_result['face_bounds']
        
        # 宫位分析
        gongwei_result = self.analyze_gongwei(image_data, image_format)
        
        # 三停分析
        santing = self.geometry_calculator.calculate_santing(landmarks, face_bounds)
        
        # 五眼分析
        wuyan = self.geometry_calculator.calculate_wuyan(landmarks)
        
        return {
            'success': True,
            'message': '分析成功',
            'landmarks': {
                'mediapipe_points': len(landmarks),
                'mapped_features': len(mapped_features)
            },
            'gongwei': gongwei_result,
            'santing': santing,
            'wuyan': wuyan,
            'features': mapped_features[:10],  # 返回前10个特征点示例
            'overall_summary': self._generate_summary(santing, wuyan)
        }
    
    def _decode_image(self, image_data: bytes, image_format: str) -> np.ndarray:
        """解码图片"""
        # 从字节数据解码
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("无法解码图片")
        
        return image
    
    def _generate_summary(self, santing: Dict, wuyan: Dict) -> str:
        """生成综合总结"""
        summary_parts = []
        
        summary_parts.append(f"三停分析：{santing['evaluation']}")
        summary_parts.append(f"五眼分析：{wuyan['evaluation']}")
        summary_parts.append("详细断语需结合规则引擎进行匹配")
        
        return "；".join(summary_parts)
    
    def close(self):
        """关闭服务"""
        if self.landmark_detector:
            self.landmark_detector.close()


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

# 导入规则匹配服务
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from services.face_knowledge_v2.service import FaceKnowledgeService


class FaceAnalysisService:
    """面相分析服务"""
    
    def __init__(self):
        self.landmark_detector = LandmarkDetector()
        self.feature_mapper = FeatureMapper()
        self.gongwei_analyzer = GongweiAnalyzer()
        self.geometry_calculator = GeometryCalculator()
        self.knowledge_service = FaceKnowledgeService()  # 规则匹配服务
    
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
            gongwei_list = self.gongwei_analyzer.analyze_shisan_gongwei(
                mapped_features, landmarks
            )
            # 为每个十三宫位填充interpretations
            for gongwei_item in gongwei_list:
                position = gongwei_item.get('name', '')
                features = gongwei_item.get('features', {})
                # 调用规则匹配器获取interpretations
                interpretations = self.knowledge_service.get_interpretation(
                    rule_type='gongwei',
                    position=position,
                    features=features
                )
                gongwei_item['interpretations'] = interpretations
            result['gongwei_list'] = gongwei_list
        
        if 'liuqin' in analysis_types:
            liuqin_list = self.gongwei_analyzer.analyze_liuqin(
                mapped_features, landmarks
            )
            # 为每个六亲宫位填充interpretations
            for liuqin_item in liuqin_list:
                position = liuqin_item.get('relation', '')
                features = liuqin_item.get('features', {})
                # 调用规则匹配器获取interpretations
                interpretations = self.knowledge_service.get_interpretation(
                    rule_type='liuqin',
                    position=position,
                    features=features
                )
                liuqin_item['interpretations'] = interpretations
            result['liuqin_list'] = liuqin_list
        
        if 'shishen' in analysis_types:
            shishen_list = self.gongwei_analyzer.analyze_shishen(
                mapped_features, landmarks
            )
            # 为每个十神宫位填充interpretations
            for shishen_item in shishen_list:
                shishen_name = shishen_item.get('shishen', '')
                features = shishen_item.get('features', {})
                # 构建十神位置名称（格式：宫位-十神，如"印堂-正官"）
                # 需要根据十神名称和对应的宫位来匹配规则
                # 从规则配置来看，位置格式是"宫位-十神"
                position = None
                # 尝试匹配十神规则的位置
                # 这里需要根据十神名称找到对应的位置
                # 简化处理：直接使用十神名称作为位置的一部分
                if '正官' in shishen_name:
                    position = '印堂-正官'
                elif '偏官' in shishen_name or '七杀' in shishen_name:
                    position = '司空-偏官'
                elif '正财' in shishen_name:
                    position = '准头-正财'
                elif '偏财' in shishen_name:
                    position = '鼻翼-偏财'
                elif '食神' in shishen_name:
                    position = '上唇-食神'
                elif '伤官' in shishen_name:
                    position = '下唇-伤官'
                elif '正印' in shishen_name:
                    position = '天庭-正印'
                elif '偏印' in shishen_name:
                    position = '额角-偏印'
                elif '比肩' in shishen_name:
                    position = '颧骨-比肩'
                elif '劫财' in shishen_name:
                    position = '下颌-劫财'
                
                if position:
                    # 调用规则匹配器获取interpretations
                    interpretations = self.knowledge_service.get_interpretation(
                        rule_type='shishen',
                        position=position,
                        features=features
                    )
                    shishen_item['interpretations'] = interpretations
            result['shishen_list'] = shishen_list
        
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


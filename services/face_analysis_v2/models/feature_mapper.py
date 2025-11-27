# -*- coding: utf-8 -*-
"""
面相特征点映射器
将MediaPipe 468个关键点映射到面相学的99个特征点
"""

import numpy as np
from typing import List, Dict, Optional


class FeatureMapper:
    """面相特征点映射器"""
    
    def __init__(self):
        # 定义99个面相特征点的映射规则
        self.feature_mapping = self._init_feature_mapping()
    
    def _init_feature_mapping(self) -> Dict:
        """初始化特征点映射规则"""
        return {
            # 1-15: 额头区域（天中、天庭等）
            1: {'name': '天中', 'method': 'single', 'indices': [10], 'gongwei': '天中', 'type': 'shisan_gongwei'},
            2: {'name': '天庭中', 'method': 'single', 'indices': [151], 'gongwei': '天庭', 'type': 'shisan_gongwei'},
            3: {'name': '天庭左', 'method': 'offset', 'base': [151], 'offset': (-0.05, 0), 'gongwei': '天庭', 'type': 'shisan_gongwei'},
            4: {'name': '天庭右', 'method': 'offset', 'base': [151], 'offset': (0.05, 0), 'gongwei': '天庭', 'type': 'shisan_gongwei'},
            5: {'name': '司空', 'method': 'interpolate', 'indices': [151, 9], 'ratio': 0.3, 'gongwei': '司空', 'type': 'shisan_gongwei'},
            6: {'name': '中正', 'method': 'interpolate', 'indices': [151, 9], 'ratio': 0.6, 'gongwei': '中正', 'type': 'shisan_gongwei'},
            
            # 16-20: 印堂区域
            16: {'name': '印堂', 'method': 'average', 'indices': [9], 'gongwei': '印堂', 'type': 'shisan_gongwei'},
            17: {'name': '印堂左眉心', 'method': 'single', 'indices': [107], 'gongwei': '印堂', 'type': 'shisan_gongwei'},
            18: {'name': '印堂右眉心', 'method': 'single', 'indices': [336], 'gongwei': '印堂', 'type': 'shisan_gongwei'},
            
            # 21-30: 眉毛区域（兄弟宫）
            21: {'name': '左眉头', 'method': 'single', 'indices': [70], 'gongwei': '兄弟宫', 'type': 'liuqin'},
            22: {'name': '左眉中', 'method': 'single', 'indices': [107], 'gongwei': '兄弟宫', 'type': 'liuqin'},
            23: {'name': '左眉尾', 'method': 'single', 'indices': [66], 'gongwei': '兄弟宫', 'type': 'liuqin'},
            24: {'name': '右眉头', 'method': 'single', 'indices': [300], 'gongwei': '兄弟宫', 'type': 'liuqin'},
            25: {'name': '右眉中', 'method': 'single', 'indices': [336], 'gongwei': '兄弟宫', 'type': 'liuqin'},
            26: {'name': '右眉尾', 'method': 'single', 'indices': [296], 'gongwei': '兄弟宫', 'type': 'liuqin'},
            
            # 31-45: 眼睛区域
            31: {'name': '左眼内角', 'method': 'single', 'indices': [133], 'gongwei': '子女宫', 'type': 'liuqin'},
            32: {'name': '左眼外角', 'method': 'single', 'indices': [33], 'gongwei': '夫妻宫', 'type': 'liuqin'},
            33: {'name': '左眼上眼睑中', 'method': 'single', 'indices': [159], 'gongwei': '田宅宫', 'type': 'gongwei'},
            34: {'name': '左眼下眼睑中', 'method': 'single', 'indices': [145], 'gongwei': '子女宫', 'type': 'liuqin'},
            35: {'name': '左眼瞳孔', 'method': 'average', 'indices': [468], 'gongwei': '眼', 'type': 'feature'},
            
            36: {'name': '右眼内角', 'method': 'single', 'indices': [362], 'gongwei': '子女宫', 'type': 'liuqin'},
            37: {'name': '右眼外角', 'method': 'single', 'indices': [263], 'gongwei': '夫妻宫', 'type': 'liuqin'},
            38: {'name': '右眼上眼睑中', 'method': 'single', 'indices': [386], 'gongwei': '田宅宫', 'type': 'gongwei'},
            39: {'name': '右眼下眼睑中', 'method': 'single', 'indices': [374], 'gongwei': '子女宫', 'type': 'liuqin'},
            40: {'name': '右眼瞳孔', 'method': 'average', 'indices': [473], 'gongwei': '眼', 'type': 'feature'},
            
            # 46-60: 鼻子区域（财帛宫、疾厄宫）
            46: {'name': '山根', 'method': 'single', 'indices': [6], 'gongwei': '山根', 'type': 'shisan_gongwei'},
            47: {'name': '鼻梁上段', 'method': 'single', 'indices': [197], 'gongwei': '年上', 'type': 'shisan_gongwei'},
            48: {'name': '鼻梁中段', 'method': 'single', 'indices': [195], 'gongwei': '寿上', 'type': 'shisan_gongwei'},
            49: {'name': '鼻梁下段', 'method': 'single', 'indices': [5], 'gongwei': '准头', 'type': 'shisan_gongwei'},
            50: {'name': '鼻头（准头）', 'method': 'single', 'indices': [4], 'gongwei': '准头', 'type': 'shisan_gongwei'},
            51: {'name': '左鼻翼', 'method': 'single', 'indices': [129], 'gongwei': '偏财', 'type': 'shishen'},
            52: {'name': '右鼻翼', 'method': 'single', 'indices': [358], 'gongwei': '偏财', 'type': 'shishen'},
            53: {'name': '左鼻孔', 'method': 'single', 'indices': [98], 'gongwei': '准头', 'type': 'feature'},
            54: {'name': '右鼻孔', 'method': 'single', 'indices': [327], 'gongwei': '准头', 'type': 'feature'},
            
            # 61-75: 嘴巴区域（食禄宫）
            61: {'name': '人中上', 'method': 'interpolate', 'indices': [2, 0], 'ratio': 0.3, 'gongwei': '人中', 'type': 'shisan_gongwei'},
            62: {'name': '人中中', 'method': 'interpolate', 'indices': [2, 0], 'ratio': 0.5, 'gongwei': '人中', 'type': 'shisan_gongwei'},
            63: {'name': '人中下', 'method': 'single', 'indices': [0], 'gongwei': '人中', 'type': 'shisan_gongwei'},
            
            64: {'name': '上唇中心', 'method': 'single', 'indices': [13], 'gongwei': '食神', 'type': 'shishen'},
            65: {'name': '上唇左', 'method': 'single', 'indices': [37], 'gongwei': '食神', 'type': 'shishen'},
            66: {'name': '上唇右', 'method': 'single', 'indices': [267], 'gongwei': '食神', 'type': 'shishen'},
            67: {'name': '下唇中心', 'method': 'single', 'indices': [14], 'gongwei': '伤官', 'type': 'shishen'},
            68: {'name': '下唇左', 'method': 'single', 'indices': [84], 'gongwei': '伤官', 'type': 'shishen'},
            69: {'name': '下唇右', 'method': 'single', 'indices': [314], 'gongwei': '伤官', 'type': 'shishen'},
            70: {'name': '左口角', 'method': 'single', 'indices': [61], 'gongwei': '水星', 'type': 'shisan_gongwei'},
            71: {'name': '右口角', 'method': 'single', 'indices': [291], 'gongwei': '水星', 'type': 'shisan_gongwei'},
            
            # 76-85: 下巴区域（地阁）
            76: {'name': '承浆', 'method': 'single', 'indices': [199], 'gongwei': '承浆', 'type': 'shisan_gongwei'},
            77: {'name': '下唇下方左', 'method': 'single', 'indices': [83], 'gongwei': '承浆', 'type': 'feature'},
            78: {'name': '下唇下方右', 'method': 'single', 'indices': [313], 'gongwei': '承浆', 'type': 'feature'},
            79: {'name': '下巴中心', 'method': 'single', 'indices': [152], 'gongwei': '地阁', 'type': 'shisan_gongwei'},
            80: {'name': '下巴左侧', 'method': 'single', 'indices': [176], 'gongwei': '地阁', 'type': 'shisan_gongwei'},
            81: {'name': '下巴右侧', 'method': 'single', 'indices': [400], 'gongwei': '地阁', 'type': 'shisan_gongwei'},
            
            # 86-92: 脸颊区域（颧骨）
            86: {'name': '左颧骨', 'method': 'single', 'indices': [205], 'gongwei': '比肩', 'type': 'shishen'},
            87: {'name': '右颧骨', 'method': 'single', 'indices': [425], 'gongwei': '比肩', 'type': 'shishen'},
            88: {'name': '左脸颊中', 'method': 'single', 'indices': [123], 'gongwei': '颧骨', 'type': 'feature'},
            89: {'name': '右脸颊中', 'method': 'single', 'indices': [352], 'gongwei': '颧骨', 'type': 'feature'},
            
            # 93-99: 耳朵和太阳穴区域
            90: {'name': '左太阳穴', 'method': 'offset', 'base': [127], 'offset': (-0.08, 0), 'gongwei': '迁移宫', 'type': 'gongwei'},
            91: {'name': '右太阳穴', 'method': 'offset', 'base': [356], 'offset': (0.08, 0), 'gongwei': '迁移宫', 'type': 'gongwei'},
            
            # 填充剩余特征点（根据需要扩展）
            92: {'name': '左额角', 'method': 'offset', 'base': [67], 'offset': (-0.05, -0.05), 'gongwei': '父母宫', 'type': 'liuqin'},
            93: {'name': '右额角', 'method': 'offset', 'base': [297], 'offset': (0.05, -0.05), 'gongwei': '父母宫', 'type': 'liuqin'},
            94: {'name': '左下颌', 'method': 'single', 'indices': [172], 'gongwei': '奴仆宫', 'type': 'liuqin'},
            95: {'name': '右下颌', 'method': 'single', 'indices': [397], 'gongwei': '奴仆宫', 'type': 'liuqin'},
            96: {'name': '额头左上', 'method': 'offset', 'base': [70], 'offset': (0, -0.08), 'gongwei': '父母宫', 'type': 'liuqin'},
            97: {'name': '额头右上', 'method': 'offset', 'base': [300], 'offset': (0, -0.08), 'gongwei': '父母宫', 'type': 'liuqin'},
            98: {'name': '左脸轮廓中', 'method': 'single', 'indices': [187], 'gongwei': '面部轮廓', 'type': 'feature'},
            99: {'name': '右脸轮廓中', 'method': 'single', 'indices': [411], 'gongwei': '面部轮廓', 'type': 'feature'},
        }
    
    def map_features(self, mediapipe_landmarks: List[Dict], face_bounds: Dict) -> List[Dict]:
        """
        将MediaPipe关键点映射为99个面相特征点
        
        Args:
            mediapipe_landmarks: MediaPipe检测的468个关键点
            face_bounds: 人脸边界框
        
        Returns:
            99个面相特征点列表
        """
        mapped_features = []
        
        for feature_id in sorted(self.feature_mapping.keys()):
            feature_def = self.feature_mapping[feature_id]
            
            # 根据方法计算特征点坐标
            point = self._calculate_feature_point(
                feature_def, mediapipe_landmarks, face_bounds
            )
            
            if point:
                mapped_features.append({
                    'feature_id': feature_id,
                    'feature_name': feature_def['name'],
                    'x': point['x'],
                    'y': point['y'],
                    'z': point.get('z', 0),
                    'gongwei': feature_def.get('gongwei', ''),
                    'position_type': feature_def.get('type', ''),
                    'method': feature_def['method']
                })
        
        return mapped_features
    
    def _calculate_feature_point(self, feature_def: Dict, landmarks: List[Dict], 
                                  face_bounds: Dict) -> Optional[Dict]:
        """
        根据定义计算特征点坐标
        """
        method = feature_def['method']
        
        if method == 'single':
            # 单个关键点
            index = feature_def['indices'][0]
            return self._get_landmark_by_index(landmarks, index)
        
        elif method == 'average':
            # 多个关键点的平均
            indices = feature_def['indices']
            points = [self._get_landmark_by_index(landmarks, idx) for idx in indices]
            points = [p for p in points if p is not None]
            if points:
                return {
                    'x': sum(p['x'] for p in points) / len(points),
                    'y': sum(p['y'] for p in points) / len(points),
                    'z': sum(p.get('z', 0) for p in points) / len(points)
                }
        
        elif method == 'interpolate':
            # 两点之间插值
            indices = feature_def['indices']
            ratio = feature_def.get('ratio', 0.5)
            
            p1 = self._get_landmark_by_index(landmarks, indices[0])
            p2 = self._get_landmark_by_index(landmarks, indices[1])
            
            if p1 and p2:
                return {
                    'x': p1['x'] + (p2['x'] - p1['x']) * ratio,
                    'y': p1['y'] + (p2['y'] - p1['y']) * ratio,
                    'z': p1.get('z', 0) + (p2.get('z', 0) - p1.get('z', 0)) * ratio
                }
        
        elif method == 'offset':
            # 基于某点的偏移
            base_index = feature_def['base'][0]
            offset = feature_def['offset']
            
            base_point = self._get_landmark_by_index(landmarks, base_index)
            if base_point:
                return {
                    'x': base_point['x'] + offset[0],
                    'y': base_point['y'] + offset[1],
                    'z': base_point.get('z', 0)
                }
        
        return None
    
    def _get_landmark_by_index(self, landmarks: List[Dict], index: int) -> Optional[Dict]:
        """根据索引获取关键点"""
        for lm in landmarks:
            if lm['index'] == index:
                return lm
        return None
    
    def get_features_by_gongwei(self, mapped_features: List[Dict], gongwei: str) -> List[Dict]:
        """根据宫位筛选特征点"""
        return [f for f in mapped_features if f.get('gongwei') == gongwei]
    
    def get_features_by_type(self, mapped_features: List[Dict], position_type: str) -> List[Dict]:
        """根据类型筛选特征点"""
        return [f for f in mapped_features if f.get('position_type') == position_type]


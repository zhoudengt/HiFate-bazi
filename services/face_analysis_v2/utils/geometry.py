# -*- coding: utf-8 -*-
"""
几何计算工具
计算三停、五眼、面部比例等
"""

import numpy as np
from typing import List, Dict, Tuple


class GeometryCalculator:
    """几何计算器"""
    
    @staticmethod
    def calculate_santing(landmarks: List[Dict], face_bounds: Dict) -> Dict:
        """
        计算三停（上停、中停、下停）
        
        上停：发际线到眉毛
        中停：眉毛到鼻底
        下停：鼻底到下巴
        
        Returns:
            三停比例和评价
        """
        # 获取关键点
        hairline_y = face_bounds['top'] - 0.1  # 估算发际线（额头上方）
        eyebrow_y = GeometryCalculator._get_avg_y(landmarks, [70, 300])  # 眉毛
        nose_bottom_y = GeometryCalculator._get_avg_y(landmarks, [2])  # 鼻底
        chin_y = face_bounds['bottom']  # 下巴
        
        # 计算三停长度
        upper_length = eyebrow_y - hairline_y
        middle_length = nose_bottom_y - eyebrow_y
        lower_length = chin_y - nose_bottom_y
        total_length = chin_y - hairline_y
        
        # 计算比例
        upper_ratio = upper_length / total_length if total_length > 0 else 0
        middle_ratio = middle_length / total_length if total_length > 0 else 0
        lower_ratio = lower_length / total_length if total_length > 0 else 0
        
        # 评价（理想比例约 1:1:1）
        evaluation = GeometryCalculator._evaluate_santing(
            upper_ratio, middle_ratio, lower_ratio
        )
        
        return {
            'upper_ratio': float(upper_ratio),
            'middle_ratio': float(middle_ratio),
            'lower_ratio': float(lower_ratio),
            'evaluation': evaluation,
            'measurements': {
                'upper_length': float(upper_length),
                'middle_length': float(middle_length),
                'lower_length': float(lower_length),
                'total_length': float(total_length)
            }
        }
    
    @staticmethod
    def _evaluate_santing(upper: float, middle: float, lower: float) -> str:
        """评价三停比例"""
        ideal = 1/3
        tolerance = 0.05
        
        if all(abs(r - ideal) < tolerance for r in [upper, middle, lower]):
            return "三停匀称，五官协调，运势平稳"
        elif upper > middle and upper > lower:
            return "上停长，额头饱满，智慧聪颖，早年得志"
        elif middle > upper and middle > lower:
            return "中停长，鼻梁挺拔，中年运势佳，事业有成"
        elif lower > upper and lower > middle:
            return "下停长，晚年运势好，福寿绵长"
        else:
            return "三停比例需调整，运势有起伏"
    
    @staticmethod
    def calculate_wuyan(landmarks: List[Dict]) -> Dict:
        """
        计算五眼（五眼比例）
        
        一眼 = 脸宽的1/5，理想情况：
        - 左侧面到左眼 = 1眼
        - 左眼宽 = 1眼
        - 两眼间距 = 1眼
        - 右眼宽 = 1眼
        - 右眼到右侧面 = 1眼
        """
        # 获取关键点
        left_face = GeometryCalculator._get_point(landmarks, 234)  # 左脸边界
        left_eye_outer = GeometryCalculator._get_point(landmarks, 33)  # 左眼外角
        left_eye_inner = GeometryCalculator._get_point(landmarks, 133)  # 左眼内角
        right_eye_inner = GeometryCalculator._get_point(landmarks, 362)  # 右眼内角
        right_eye_outer = GeometryCalculator._get_point(landmarks, 263)  # 右眼外角
        right_face = GeometryCalculator._get_point(landmarks, 454)  # 右脸边界
        
        # 计算距离
        face_width = abs(right_face['x'] - left_face['x'])
        left_side = abs(left_eye_outer['x'] - left_face['x'])
        left_eye_width = abs(left_eye_inner['x'] - left_eye_outer['x'])
        eye_distance = abs(right_eye_inner['x'] - left_eye_inner['x'])
        right_eye_width = abs(right_eye_outer['x'] - right_eye_inner['x'])
        right_side = abs(right_face['x'] - right_eye_outer['x'])
        
        # 转换为比例
        eye_widths = [
            left_side / face_width,
            left_eye_width / face_width,
            eye_distance / face_width,
            right_eye_width / face_width,
            right_side / face_width
        ]
        
        # 评价
        evaluation = GeometryCalculator._evaluate_wuyan(eye_widths)
        
        return {
            'eye_widths': [float(w) for w in eye_widths],
            'face_width': float(face_width),
            'evaluation': evaluation
        }
    
    @staticmethod
    def _evaluate_wuyan(widths: List[float]) -> str:
        """评价五眼比例"""
        ideal = 0.2
        tolerance = 0.03
        
        if all(abs(w - ideal) < tolerance for w in widths):
            return "五眼匀称，面部协调，美观大方"
        elif widths[2] < ideal - tolerance:
            return "两眼间距窄，专注力强但需注意心胸开阔"
        elif widths[2] > ideal + tolerance:
            return "两眼间距宽，心胸开阔，性格大度"
        else:
            return "五眼比例基本协调"
    
    @staticmethod
    def calculate_distance(p1: Dict, p2: Dict) -> float:
        """计算两点距离"""
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        return np.sqrt(dx**2 + dy**2)
    
    @staticmethod
    def calculate_angle(p1: Dict, p2: Dict, p3: Dict) -> float:
        """计算三点角度（以p2为顶点）"""
        v1 = np.array([p1['x'] - p2['x'], p1['y'] - p2['y']])
        v2 = np.array([p3['x'] - p2['x'], p3['y'] - p2['y']])
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        return np.degrees(angle)
    
    @staticmethod
    def _get_point(landmarks: List[Dict], index: int) -> Dict:
        """根据索引获取点"""
        for lm in landmarks:
            if lm['index'] == index:
                return lm
        return {'x': 0, 'y': 0, 'z': 0}
    
    @staticmethod
    def _get_avg_y(landmarks: List[Dict], indices: List[int]) -> float:
        """获取一组点的平均Y坐标"""
        points = [GeometryCalculator._get_point(landmarks, idx) for idx in indices]
        return sum(p['y'] for p in points) / len(points) if points else 0


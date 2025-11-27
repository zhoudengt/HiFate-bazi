# -*- coding: utf-8 -*-
"""
MediaPipe人脸关键点检测器 - 降级方案
如果MediaPipe无法使用，提供模拟数据
"""

import cv2
import numpy as np
from typing import List, Dict, Optional


class LandmarkDetectorFallback:
    """降级检测器 - 返回模拟数据用于测试"""
    
    def detect(self, image: np.ndarray) -> Optional[Dict]:
        """
        返回模拟的关键点数据（用于测试）
        """
        h, w = image.shape[:2]
        
        # 生成模拟的468个关键点（基于人脸中心区域）
        landmarks = []
        center_x, center_y = 0.5, 0.4  # 人脸中心位置
        
        for i in range(468):
            # 在中心区域随机分布
            x = center_x + np.random.normal(0, 0.15)
            y = center_y + np.random.normal(0, 0.15)
            x = np.clip(x, 0, 1)
            y = np.clip(y, 0, 1)
            
            landmarks.append({
                'index': i,
                'x': float(x),
                'y': float(y),
                'z': float(np.random.normal(0, 0.01)),
                'visibility': 1.0,
                'x_px': int(x * w),
                'y_px': int(y * h)
            })
        
        face_bounds = {
            'left': 0.2,
            'top': 0.1,
            'right': 0.8,
            'bottom': 0.7,
            'width': 0.6,
            'height': 0.6
        }
        
        return {
            'landmarks': landmarks,
            'face_bounds': face_bounds,
            'image_size': {'width': w, 'height': h}
        }
    
    def close(self):
        """关闭检测器"""
        pass


# -*- coding: utf-8 -*-
"""
MediaPipe人脸关键点检测器
使用MediaPipe Face Mesh检测468个3D关键点
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️  MediaPipe未安装，将使用降级模式")


class LandmarkDetector:
    """MediaPipe人脸关键点检测器"""
    
    def __init__(self):
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = None
        self._initialized = False
        self._use_fallback = False
        self.fallback = None
    
    def _ensure_initialized(self):
        """延迟初始化MediaPipe（避免启动时失败）"""
        if not self._initialized:
            if not MEDIAPIPE_AVAILABLE:
                raise RuntimeError("MediaPipe未安装。请运行: pip install mediapipe")
            try:
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    static_image_mode=True,
                    max_num_faces=1,
                    refine_landmarks=False,  # 禁用refine_landmarks避免错误
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self._initialized = True
            except Exception as e:
                # 如果初始化失败，使用降级方案
                print(f"⚠️  MediaPipe初始化失败：{e}")
                print("   将使用降级模式（模拟数据）")
                from .landmark_detector_fallback import LandmarkDetectorFallback
                self.fallback = LandmarkDetectorFallback()
                self._initialized = True
                self._use_fallback = True
        
    def detect(self, image: np.ndarray) -> Optional[Dict]:
        """
        检测人脸关键点
        
        Args:
            image: OpenCV图像（BGR格式）
        
        Returns:
            检测结果字典，包含landmarks和face_bounds
        """
        # 确保已初始化
        self._ensure_initialized()
        
        # 如果使用降级模式
        if self._use_fallback and self.fallback:
            return self.fallback.detect(image)
        
        # 转换为RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        
        # 检测
        results = self.face_mesh.process(image_rgb)
        
        if not results.multi_face_landmarks:
            return None
        
        # 获取第一张人脸的关键点
        face_landmarks = results.multi_face_landmarks[0]
        
        # 转换为像素坐标
        landmarks = []
        for idx, landmark in enumerate(face_landmarks.landmark):
            landmarks.append({
                'index': idx,
                'x': landmark.x,  # 归一化坐标 0-1
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility if hasattr(landmark, 'visibility') else 1.0,
                'x_px': int(landmark.x * w),  # 像素坐标
                'y_px': int(landmark.y * h)
            })
        
        # 计算人脸边界框
        x_coords = [lm['x'] for lm in landmarks]
        y_coords = [lm['y'] for lm in landmarks]
        
        face_bounds = {
            'left': min(x_coords),
            'top': min(y_coords),
            'right': max(x_coords),
            'bottom': max(y_coords),
            'width': max(x_coords) - min(x_coords),
            'height': max(y_coords) - min(y_coords)
        }
        
        return {
            'landmarks': landmarks,
            'face_bounds': face_bounds,
            'image_size': {'width': w, 'height': h}
        }
    
    def get_landmark_by_index(self, landmarks: List[Dict], index: int) -> Optional[Dict]:
        """根据索引获取关键点"""
        for lm in landmarks:
            if lm['index'] == index:
                return lm
        return None
    
    def get_landmark_group(self, landmarks: List[Dict], indices: List[int]) -> List[Dict]:
        """获取一组关键点"""
        return [lm for lm in landmarks if lm['index'] in indices]
    
    def calculate_center(self, landmark_group: List[Dict]) -> Dict:
        """计算一组关键点的中心"""
        if not landmark_group:
            return None
        
        avg_x = sum(lm['x'] for lm in landmark_group) / len(landmark_group)
        avg_y = sum(lm['y'] for lm in landmark_group) / len(landmark_group)
        avg_z = sum(lm['z'] for lm in landmark_group) / len(landmark_group)
        
        return {'x': avg_x, 'y': avg_y, 'z': avg_z}
    
    def close(self):
        """关闭检测器"""
        if self.face_mesh:
            self.face_mesh.close()


# MediaPipe关键点索引定义（部分重要点位）
MEDIAPIPE_LANDMARKS = {
    # 轮廓
    'face_oval': list(range(0, 17)) + list(range(397, 400)),
    
    # 眉毛
    'left_eyebrow': [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
    'right_eyebrow': [300, 293, 334, 296, 336, 285, 295, 282, 283, 276],
    
    # 眼睛
    'left_eye': [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
    'right_eye': [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466],
    
    # 鼻子
    'nose_bridge': [6, 197, 195, 5],
    'nose_tip': [4],
    'nose_bottom': [2, 98, 327],
    'left_nostril': [97, 98, 129],
    'right_nostril': [326, 327, 358],
    
    # 嘴巴
    'outer_lips': [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 146, 91, 181, 84, 17, 314, 405, 321, 375],
    'inner_lips': [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95],
    'upper_lip': [61, 185, 40, 39, 37, 0, 267, 269, 270, 409],
    'lower_lip': [146, 91, 181, 84, 17, 314, 405, 321, 375, 291],
    
    # 脸颊
    'left_cheek': [116, 123, 147, 187, 207, 187],
    'right_cheek': [345, 352, 376, 411, 427],
    
    # 下巴
    'chin': [152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162]
}


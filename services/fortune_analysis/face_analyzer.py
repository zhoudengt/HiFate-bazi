#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面相分析模块
使用 MediaPipe 提取面部特征
"""

import cv2
import logging

logger = logging.getLogger(__name__)
import numpy as np
from typing import Dict, Any, Optional, List
import json

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.info("⚠️  MediaPipe 未安装，面相分析功能将受限")

import sys
import os

# 添加服务目录到路径
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)

from image_preprocessor import ImagePreprocessor
try:
    from .mediapipe_singleton import MediaPipeSingleton
except ImportError:
    from mediapipe_singleton import MediaPipeSingleton


class FaceAnalyzer:
    """面相分析器"""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.mp_singleton = MediaPipeSingleton.get_instance()
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
        else:
            self.mp_face_mesh = None
    
    def _get_face_mesh_instance(self):
        """获取 MediaPipe FaceMesh 实例（使用单例）"""
        if not MEDIAPIPE_AVAILABLE:
            return None
        return self.mp_singleton.get_face_mesh()
    
    def analyze(self, image_bytes: bytes, image_format: str = "jpg", enable_special_features: bool = False) -> Dict[str, Any]:
        """
        分析面相（优化版：性能优化）
        
        Args:
            image_bytes: 图像字节数据
            image_format: 图像格式
            enable_special_features: 是否启用特殊特征检测（默认False，提升性能）
            
        Returns:
            分析结果
        """
        import datetime
        request_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 验证图像
        is_valid, error_msg = self.preprocessor.validate_image(image_bytes)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        # 2. 转换为 OpenCV 图像
        img = self.preprocessor.bytes_to_cv2(image_bytes)
        if img is None:
            return {
                "success": False,
                "error": "图像解码失败"
            }
        
        # 3. 图像增强
        img = self.preprocessor.enhance_image(img)
        
        # 4. 提取特征（传入特殊特征检测开关）
        features = self._extract_features(img, enable_special_features=enable_special_features)
        
        return {
            "success": True,
            "features": features
        }
    
    def _extract_features(self, img: np.ndarray, enable_special_features: bool = False) -> Dict[str, Any]:
        """提取面部特征（优化版：性能优化，减少日志）"""
        features = {
            "san_ting_ratio": {},
            "facial_attributes": {},
            "feature_measurements": {},
            "special_features": [],
            "landmarks": []
        }
        
        # 转换为 RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 获取 MediaPipe FaceMesh 实例（使用单例）
        face_mesh = self._get_face_mesh_instance()
        if not face_mesh:
            return self._extract_features_fallback(img)
        
        # 检测面部
        results = face_mesh.process(img_rgb)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            
            # 提取关键点（优化：批量处理）
            landmarks_list = []
            for landmark in landmarks.landmark:
                landmarks_list.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z
                })
            features["landmarks"] = landmarks_list
            
            # 计算三停比例
            features["san_ting_ratio"] = self._calculate_san_ting(landmarks, img.shape)
            
            # 分析五官
            features["feature_measurements"] = self._analyze_facial_features(landmarks, img.shape)
            
            # 检测特殊特征（可选，默认关闭以提升性能）
            if enable_special_features:
                features["special_features"] = self._detect_special_features(img, landmarks)
            else:
                features["special_features"] = []  # 快速跳过，提升性能
            
            # 面部属性（简化）
            features["facial_attributes"] = {
                "age": "成年",
                "gender": "未知",
                "emotion": "中性"
            }
        else:
            return self._extract_features_fallback(img)
        
        return features
    
    def _calculate_san_ting(self, landmarks, image_shape) -> Dict[str, float]:
        """计算三停比例"""
        # MediaPipe Face Mesh 关键点索引
        # 发际线：约在顶部
        # 眉毛：约在 10, 151, 337 等点
        # 鼻尖：约在 4, 5, 6 等点
        # 下巴：约在 175, 199 等点
        
        h, w = image_shape[:2]
        
        # 上停：发际线到眉毛
        # 使用关键点估算
        top_y = min([landmarks.landmark[i].y for i in range(10)]) * h
        eyebrow_y = np.mean([landmarks.landmark[i].y for i in [10, 151, 337] if i < len(landmarks.landmark)]) * h
        upper_ting = abs(eyebrow_y - top_y)
        
        # 中停：眉毛到鼻尖
        nose_y = np.mean([landmarks.landmark[i].y for i in [4, 5, 6] if i < len(landmarks.landmark)]) * h
        middle_ting = abs(nose_y - eyebrow_y)
        
        # 下停：鼻尖到下巴
        chin_y = np.mean([landmarks.landmark[i].y for i in [175, 199] if i < len(landmarks.landmark)]) * h
        lower_ting = abs(chin_y - nose_y)
        
        # 计算比例
        total = upper_ting + middle_ting + lower_ting
        if total > 0:
            return {
                "upper": float(upper_ting / total),
                "middle": float(middle_ting / total),
                "lower": float(lower_ting / total)
            }
        
        return {"upper": 0.33, "middle": 0.33, "lower": 0.34}
    
    def _analyze_facial_features(self, landmarks, image_shape) -> Dict[str, float]:
        """分析五官特征（优化版：减少计算，增加特征）"""
        measurements = {}
        h, w = image_shape[:2]
        landmark_list = landmarks.landmark
        
        # 缓存常用关键点（避免重复索引检查）
        def safe_landmark(idx, default_idx=0):
            if idx < len(landmark_list):
                return landmark_list[idx]
            return landmark_list[default_idx] if default_idx < len(landmark_list) else landmark_list[0]
        
        # 额头宽度（优化：直接计算，避免重复sqrt）
        forehead_left = safe_landmark(234)
        forehead_right = safe_landmark(454)
        dx = (forehead_right.x - forehead_left.x) * w
        dy = (forehead_right.y - forehead_left.y) * h
        measurements["forehead_width"] = float(np.sqrt(dx*dx + dy*dy))
        
        # 眼睛大小（优化：计算双眼平均宽度）
        left_eye_left = safe_landmark(33)
        left_eye_right = safe_landmark(133)
        right_eye_left = safe_landmark(362)
        right_eye_right = safe_landmark(263)
        
        # 左眼宽度
        dx1 = (left_eye_right.x - left_eye_left.x) * w
        dy1 = (left_eye_right.y - left_eye_left.y) * h
        left_eye_w = np.sqrt(dx1*dx1 + dy1*dy1)
        
        # 右眼宽度
        dx2 = (right_eye_right.x - right_eye_left.x) * w
        dy2 = (right_eye_right.y - right_eye_left.y) * h
        right_eye_w = np.sqrt(dx2*dx2 + dy2*dy2)
        
        measurements["eye_width"] = float((left_eye_w + right_eye_w) / 2)
        measurements["eye_symmetry"] = float(abs(left_eye_w - right_eye_w) / max(left_eye_w, right_eye_w, 1.0))  # 对称性
        
        # 鼻子高度（优化）
        nose_top = safe_landmark(6)
        nose_bottom = safe_landmark(4)
        dx = (nose_bottom.x - nose_top.x) * w
        dy = (nose_bottom.y - nose_top.y) * h
        measurements["nose_height"] = float(np.sqrt(dx*dx + dy*dy))
        
        # 鼻子宽度（新增）
        nose_left = safe_landmark(131)
        nose_right = safe_landmark(360)
        dx = (nose_right.x - nose_left.x) * w
        dy = (nose_right.y - nose_left.y) * h
        measurements["nose_width"] = float(np.sqrt(dx*dx + dy*dy))
        measurements["nose_ratio"] = float(measurements["nose_height"] / max(measurements["nose_width"], 1.0))  # 高宽比
        
        # 嘴巴宽度（新增）
        mouth_left = safe_landmark(61)
        mouth_right = safe_landmark(291)
        dx = (mouth_right.x - mouth_left.x) * w
        dy = (mouth_right.y - mouth_left.y) * h
        measurements["mouth_width"] = float(np.sqrt(dx*dx + dy*dy))
        
        # 面部宽度（新增：颧骨宽度）
        cheek_left = safe_landmark(234)
        cheek_right = safe_landmark(454)
        dx = (cheek_right.x - cheek_left.x) * w
        dy = (cheek_right.y - cheek_left.y) * h
        measurements["face_width"] = float(np.sqrt(dx*dx + dy*dy))
        
        # 面部高度（新增：从发际线到下巴）
        top_y = min([landmark_list[i].y for i in range(min(10, len(landmark_list)))]) * h
        chin_y = safe_landmark(175).y * h
        measurements["face_height"] = float(abs(chin_y - top_y))
        measurements["face_ratio"] = float(measurements["face_width"] / max(measurements["face_height"], 1.0))  # 面部宽高比
        
        # 额头高度（新增）
        eyebrow_y = np.mean([safe_landmark(i).y for i in [10, 151, 337]]) * h
        measurements["forehead_height"] = float(abs(eyebrow_y - top_y))
        measurements["forehead_ratio"] = float(measurements["forehead_width"] / max(measurements["forehead_height"], 1.0))  # 额头宽高比
        
        return measurements
    
    def _detect_special_features(self, img: np.ndarray, landmarks) -> List[Dict[str, Any]]:
        """检测特殊特征（痣、疤痕等）（优化版：减少计算）"""
        special_features = []
        
        # 优化：只在面部区域检测，减少计算量
        h, w = img.shape[:2]
        landmark_list = landmarks.landmark
        
        # 获取面部边界框（快速估算）
        xs = [lm.x * w for lm in landmark_list[:50]]  # 只检查前50个点
        ys = [lm.y * h for lm in landmark_list[:50]]
        if not xs or not ys:
            return special_features
        
        x_min, x_max = int(min(xs)), int(max(xs))
        y_min, y_max = int(min(ys)), int(max(ys))
        
        # 扩展边界框
        margin = 20
        x_min = max(0, x_min - margin)
        y_min = max(0, y_min - margin)
        x_max = min(w, x_max + margin)
        y_max = min(h, y_max + margin)
        
        # 只处理面部区域
        face_roi = img[y_min:y_max, x_min:x_max]
        if face_roi.size == 0:
            return special_features
        
        # 转换为灰度（只处理ROI）
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 优化：使用更快的检测方法（减少参数设置）
        # 使用简单的阈值检测异常点（比BlobDetector快）
        _, thresh = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤小区域
        valid_contours = [c for c in contours if 10 < cv2.contourArea(c) < 500]
        
        if len(valid_contours) > 0:
            for i, contour in enumerate(valid_contours[:5]):  # 最多5个
                area = cv2.contourArea(contour)
                # 估算位置（相对于面部）
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"]) + x_min
                    cy = int(M["m01"] / M["m00"]) + y_min
                    # 判断位置区域
                    if cy < y_min + (y_max - y_min) * 0.3:
                        region = "上停"
                    elif cy < y_min + (y_max - y_min) * 0.7:
                        region = "中停"
                    else:
                        region = "下停"
                    
                    special_features.append({
                        "type": "特殊标记",
                        "region": region,
                        "area": float(area),
                        "position": {"x": cx, "y": cy}
                    })
        
        return special_features
    
    def _extract_features_fallback(self, img: np.ndarray) -> Dict[str, Any]:
        """降级方案"""
        # 检测面部区域
        face_region = self.preprocessor.detect_face_region(img)
        
        features = {
            "san_ting_ratio": {
                "upper": 0.33,
                "middle": 0.33,
                "lower": 0.34
            },
            "facial_attributes": {
                "age": "成年",
                "gender": "未知",
                "emotion": "中性"
            },
            "feature_measurements": {},
            "special_features": [],
            "landmarks": []
        }
        
        if face_region:
            x, y, w, h = face_region
            # 简单的三停估算
            features["feature_measurements"] = {
                "face_width": float(w),
                "face_height": float(h),
                "face_ratio": float(w / h) if h > 0 else 0
            }
        
        return features


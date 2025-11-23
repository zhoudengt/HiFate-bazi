#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像类型验证模块
验证上传的图像是否包含手部或面部
"""

import cv2
import numpy as np
from typing import Tuple, Optional

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# 导入单例管理器（使用相对导入）
try:
    from .mediapipe_singleton import MediaPipeSingleton
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import os
    import sys
    service_dir = os.path.dirname(os.path.abspath(__file__))
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    from mediapipe_singleton import MediaPipeSingleton


class ImageValidator:
    """图像类型验证器"""
    
    def __init__(self):
        self.mp_singleton = MediaPipeSingleton.get_instance()
        if MEDIAPIPE_AVAILABLE:
            self.mp_hands = mp.solutions.hands
            self.mp_face_mesh = mp.solutions.face_mesh
        else:
            self.mp_hands = None
            self.mp_face_mesh = None
    
    def _ensure_hands_initialized(self):
        """确保 MediaPipe Hands 已初始化（使用单例）"""
        if not MEDIAPIPE_AVAILABLE:
            return False
        hands = self.mp_singleton.get_hands()
        return hands is not None
    
    def _ensure_face_initialized(self):
        """确保 MediaPipe FaceMesh 已初始化（使用单例）"""
        if not MEDIAPIPE_AVAILABLE:
            return False
        face_mesh = self.mp_singleton.get_face_mesh()
        return face_mesh is not None
    
    def validate_hand_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        验证图像是否包含手部
        
        Args:
            image_bytes: 图像字节数据
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 转换为 OpenCV 图像
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return False, "无法解码图像数据"
            
            # 转换为 RGB（MediaPipe 需要 RGB）
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 使用 MediaPipe 检测手部（使用单例）
            if MEDIAPIPE_AVAILABLE and self._ensure_hands_initialized():
                hands = self.mp_singleton.get_hands()
                results = hands.process(img_rgb)
                
                if results.multi_hand_landmarks:
                    # 验证手部关键点数量（手掌应该有21个关键点）
                    hand_landmarks = results.multi_hand_landmarks[0]
                    if len(hand_landmarks.landmark) >= 21:
                        return True, ""
                    else:
                        return False, "检测到的手部关键点不足，请确保上传的是完整清晰的手掌照片"
                else:
                    # MediaPipe 检测失败，不降级，直接拒绝
                    return False, "未检测到手部，请确保上传的是清晰的手掌照片，手掌正面朝上，光线充足，背景简洁"
            else:
                # MediaPipe 不可用时，使用严格的降级方案
                return self._validate_hand_fallback(img)
                
        except Exception as e:
            return False, f"手部验证失败: {str(e)}"
    
    def validate_face_image(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        验证图像是否包含面部
        
        Args:
            image_bytes: 图像字节数据
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 转换为 OpenCV 图像
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return False, "无法解码图像数据"
            
            # 转换为 RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # 使用 MediaPipe 检测面部（使用单例）
            if MEDIAPIPE_AVAILABLE and self._ensure_face_initialized():
                face_mesh = self.mp_singleton.get_face_mesh()
                results = face_mesh.process(img_rgb)
                
                if results.multi_face_landmarks:
                    # 验证面部关键点数量（面部应该有468个关键点）
                    face_landmarks = results.multi_face_landmarks[0]
                    if len(face_landmarks.landmark) >= 400:  # 至少400个关键点
                        return True, ""
                    else:
                        return False, "检测到的面部关键点不足，请确保上传的是完整清晰的面部照片"
                else:
                    # MediaPipe 检测失败，不降级，直接拒绝
                    return False, "未检测到面部，请确保上传的是清晰的正面面部照片，光线充足，面部清晰可见，背景简洁"
            else:
                # MediaPipe 不可用时，使用降级方案
                return self._validate_face_fallback(img)
                
        except Exception as e:
            return False, f"面部验证失败: {str(e)}"
    
    def _validate_hand_fallback(self, img: np.ndarray) -> Tuple[bool, str]:
        """降级方案：使用严格的肤色和形状检测验证手部"""
        try:
            # 转换为 HSV 色彩空间
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # 肤色范围
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            
            # 创建掩码
            mask = cv2.inRange(hsv, lower_skin, upper_skin)
            
            # 计算肤色区域占比
            skin_ratio = np.sum(mask > 0) / (img.shape[0] * img.shape[1])
            
            # 提高阈值：从 10% 提高到 35%，更严格
            if skin_ratio < 0.35:
                return False, f"未检测到手部区域（肤色占比: {skin_ratio*100:.1f}%，要求: ≥35%），请确保上传的是清晰的手掌照片，手掌正面朝上"
            
            # 额外的形状验证：检查是否有类似手掌的形状（长宽比）
            # 手掌通常宽度和高度相近，或者稍微宽一些
            h, w = img.shape[:2]
            aspect_ratio = w / h if h > 0 else 0
            
            # 手掌照片通常长宽比在 0.7-1.5 之间
            if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                return False, f"图像比例不符合手掌特征（宽高比: {aspect_ratio:.2f}），请确保上传的是完整的手掌照片"
            
            # 检查是否有足够的轮廓（手掌应该有多个手指轮廓）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 手掌应该有多个明显的轮廓区域
            if len(contours) < 3:
                return False, "未检测到足够的手部轮廓特征，请确保上传的是清晰的手掌照片"
            
            return True, ""
                
        except Exception as e:
            return False, f"手部验证失败: {str(e)}"
    
    def _validate_face_fallback(self, img: np.ndarray) -> Tuple[bool, str]:
        """降级方案：使用 OpenCV 的 Haar 级联分类器验证面部"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 使用 OpenCV 的默认人脸检测器
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                return True, ""
            else:
                return False, "未检测到面部，请确保上传的是清晰的正面面部照片"
                
        except Exception as e:
            return False, f"面部验证失败: {str(e)}"


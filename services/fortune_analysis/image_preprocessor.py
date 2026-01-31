#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像预处理模块
"""

import cv2
import logging

logger = logging.getLogger(__name__)
import numpy as np
from PIL import Image
import io
from typing import Tuple, Optional


class ImagePreprocessor:
    """图像预处理器"""
    
    @staticmethod
    def validate_image(image_bytes: bytes, min_size: Tuple[int, int] = (400, 300), strict_clarity: bool = False) -> Tuple[bool, str]:
        """
        验证图像质量
        
        Args:
            image_bytes: 图像字节数据
            min_size: 最小尺寸 (width, height)
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 转换为 numpy 数组
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return False, "无法解码图像数据"
            
            height, width = img.shape[:2]
            
            # 检查尺寸
            if width < min_size[0] or height < min_size[1]:
                return False, f"图像尺寸过小，最小要求: {min_size[0]}x{min_size[1]}"
            
            # 检查清晰度（使用 Laplacian 方差）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 降低阈值，因为手掌照片的纹理可能较平滑
            # strict_clarity=True 时使用更严格的标准（100），否则使用宽松标准（30）
            min_clarity = 100 if strict_clarity else 30
            
            if laplacian_var < min_clarity:
                # 提供更详细的错误信息，包括实际清晰度值
                return False, f"图像清晰度不足（清晰度: {laplacian_var:.1f}，要求: {min_clarity}），请上传更清晰的照片。建议：确保光线充足，避免模糊，正面拍摄"
            
            # 如果清晰度较低但可接受，记录警告但不拒绝
            if laplacian_var < 100:
                logger.info(f"⚠️  图像清晰度较低: {laplacian_var:.1f}，但继续处理")
            
            return True, ""
            
        except Exception as e:
            return False, f"图像验证失败: {str(e)}"
    
    @staticmethod
    def bytes_to_cv2(image_bytes: bytes) -> Optional[np.ndarray]:
        """将字节数据转换为 OpenCV 图像"""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.info(f"图像解码失败: {e}")
            return None
    
    @staticmethod
    def enhance_image(img: np.ndarray) -> np.ndarray:
        """
        图像增强
        
        Args:
            img: OpenCV 图像
            
        Returns:
            增强后的图像
        """
        # 转换为 LAB 色彩空间
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 应用 CLAHE（对比度受限的自适应直方图均衡化）
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # 合并通道
        lab = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # 去噪
        enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
        
        return enhanced
    
    @staticmethod
    def normalize_image(img: np.ndarray, target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        图像归一化
        
        Args:
            img: OpenCV 图像
            target_size: 目标尺寸 (width, height)，如果为 None 则保持原尺寸
            
        Returns:
            归一化后的图像
        """
        if target_size:
            img = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)
        
        return img
    
    @staticmethod
    def detect_hand_region(img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测手部区域（简单实现，实际应使用 MediaPipe）
        
        Args:
            img: OpenCV 图像
            
        Returns:
            (x, y, width, height) 或 None
        """
        # 转换为 HSV 色彩空间
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # 肤色范围（需要根据实际情况调整）
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # 创建掩码
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 形态学操作
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 找到最大的轮廓
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # 扩展边界
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2 * padding)
            h = min(img.shape[0] - y, h + 2 * padding)
            
            return (x, y, w, h)
        
        return None
    
    @staticmethod
    def detect_face_region(img: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测面部区域（简单实现，实际应使用 MediaPipe）
        
        Args:
            img: OpenCV 图像
            
        Returns:
            (x, y, width, height) 或 None
        """
        # 使用 Haar 级联分类器（需要下载模型文件）
        # 这里使用简单的实现
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 尝试使用 OpenCV 的默认人脸检测器
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                # 返回最大的面部
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                return (x, y, w, h)
        except:
            pass
        
        # 如果检测失败，返回整个图像的中心区域
        h, w = img.shape[:2]
        return (w // 4, h // 4, w // 2, h // 2)


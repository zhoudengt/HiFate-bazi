#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手相分析模块
使用 MediaPipe 提取手部特征
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, List
import json

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️  MediaPipe 未安装，手相分析功能将受限")

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


class HandAnalyzer:
    """手相分析器"""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.mp_singleton = MediaPipeSingleton.get_instance()
        if MEDIAPIPE_AVAILABLE:
            self.mp_hands = mp.solutions.hands
        else:
            self.mp_hands = None
    
    def _get_hands_instance(self):
        """获取 MediaPipe Hands 实例（使用单例）"""
        if not MEDIAPIPE_AVAILABLE:
            return None
        return self.mp_singleton.get_hands()
    
    def analyze(self, image_bytes: bytes, image_format: str = "jpg") -> Dict[str, Any]:
        """
        分析手相
        
        Args:
            image_bytes: 图像字节数据
            image_format: 图像格式
            
        Returns:
            分析结果
        """
        # 验证图像
        is_valid, error_msg = self.preprocessor.validate_image(image_bytes)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        # 转换为 OpenCV 图像
        img = self.preprocessor.bytes_to_cv2(image_bytes)
        if img is None:
            return {
                "success": False,
                "error": "图像解码失败"
            }
        
        # 图像增强
        img = self.preprocessor.enhance_image(img)
        
        # 提取特征
        features = self._extract_features(img)
        
        return {
            "success": True,
            "features": features
        }
    
    def _extract_features(self, img: np.ndarray) -> Dict[str, Any]:
        """提取手部特征（增强版：提取更多特征维度）"""
        features = {
            "hand_shape": "未知",
            "finger_lengths": {},
            "palm_lines": {},
            "measurements": {},
            "landmarks": [],
            "finger_ratios": {},  # 新增：手指比例（连续值）
            "finger_thickness": {},  # 新增：手指粗细
            "palm_texture": {},  # 新增：手掌纹理特征
            "special_marks": [],  # 新增：特殊标记
            "hand_orientation": "未知"  # 新增：手部方向（左右手）
        }
        
        # 转换为 RGB（MediaPipe 需要 RGB）
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 获取 MediaPipe Hands 实例（使用单例）
        hands = self._get_hands_instance()
        if not hands:
            # 降级方案：使用简单的图像处理
            return self._extract_features_fallback(img)
        
        # 检测手部
        results = hands.process(img_rgb)
        
        if results.multi_hand_landmarks:
            landmarks = results.multi_hand_landmarks[0]
            
            # 提取关键点
            landmarks_list = []
            for landmark in landmarks.landmark:
                landmarks_list.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z
                })
            features["landmarks"] = landmarks_list
            
            # 分析手型（增强版：返回更多信息）
            hand_shape_info = self._analyze_hand_shape_enhanced(landmarks, img.shape)
            features["hand_shape"] = hand_shape_info.get("shape", "未知")
            features["hand_shape_ratio"] = hand_shape_info.get("ratio", 0.0)
            features["hand_shape_confidence"] = hand_shape_info.get("confidence", 0.0)
            
            # 分析指长（增强版：返回连续值）
            finger_info = self._analyze_finger_lengths_enhanced(landmarks)
            features["finger_lengths"] = finger_info.get("categories", {})
            features["finger_ratios"] = finger_info.get("ratios", {})  # 连续值
            
            # 分析手指粗细
            features["finger_thickness"] = self._analyze_finger_thickness(img, landmarks)
            
            # 分析手掌尺寸
            features["measurements"] = self._measure_hand_enhanced(landmarks, img.shape)
            
            # 提取掌纹（增强版：更准确的识别）
            features["palm_lines"] = self._extract_palm_lines_enhanced(img, landmarks)
            
            # 分析手掌纹理
            features["palm_texture"] = self._analyze_palm_texture(img, landmarks)
            
            # 检测特殊标记
            features["special_marks"] = self._detect_special_marks(img, landmarks)
            
            # 判断左右手
            features["hand_orientation"] = self._detect_hand_orientation(landmarks)
        else:
            # 未检测到手部，使用降级方案
            return self._extract_features_fallback(img)
        
        return features
    
    def _analyze_hand_shape(self, landmarks, image_shape) -> str:
        """分析手型（保留兼容性）"""
        result = self._analyze_hand_shape_enhanced(landmarks, image_shape)
        return result.get("shape", "未知")
    
    def _analyze_hand_shape_enhanced(self, landmarks, image_shape) -> Dict[str, Any]:
        """分析手型（增强版：返回更多信息）"""
        # 获取关键点
        wrist = landmarks.landmark[0]
        index_mcp = landmarks.landmark[5]  # 食指根部
        ring_mcp = landmarks.landmark[13]   # 无名指根部
        pinky_mcp = landmarks.landmark[17]  # 小指根部
        middle_mcp = landmarks.landmark[9]  # 中指根部
        
        # 计算手掌宽度和长度
        palm_width = abs(ring_mcp.x - index_mcp.x) * image_shape[1]
        palm_length = abs(wrist.y - middle_mcp.y) * image_shape[0]
        
        # 计算宽高比
        ratio = palm_width / palm_length if palm_length > 0 else 0
        
        # 计算手指根部对齐度（用于判断圆形手）
        finger_alignment = abs(ring_mcp.y - index_mcp.y) * image_shape[0]
        
        # 计算手掌的对称性
        left_side = abs(pinky_mcp.x - wrist.x) * image_shape[1]
        right_side = abs(index_mcp.x - wrist.x) * image_shape[1]
        symmetry = min(left_side, right_side) / max(left_side, right_side) if max(left_side, right_side) > 0 else 0
        
        # 判断手型（更细致的分类）
        shape = "未知"
        confidence = 0.5
        
        if ratio > 0.75:
            shape = "方形手"
            confidence = 0.8
        elif ratio < 0.45:
            shape = "尖形手"
            confidence = 0.8
        elif finger_alignment < 8 and symmetry > 0.85:
            shape = "圆形手"
            confidence = 0.75
        elif 0.55 <= ratio <= 0.65:
            shape = "标准手"
            confidence = 0.7
        else:
            shape = "长方形手"
            confidence = 0.6
        
        return {
            "shape": shape,
            "ratio": float(ratio),
            "palm_width": float(palm_width),
            "palm_length": float(palm_length),
            "symmetry": float(symmetry),
            "confidence": float(confidence)
        }
    
    def _analyze_finger_lengths(self, landmarks) -> Dict[str, str]:
        """分析指长（保留兼容性）"""
        result = self._analyze_finger_lengths_enhanced(landmarks)
        return result.get("categories", {})
    
    def _analyze_finger_lengths_enhanced(self, landmarks) -> Dict[str, Any]:
        """分析指长（增强版：返回连续值和分类）"""
        finger_lengths = {}
        finger_ratios = {}
        
        # 定义手指关键点索引
        fingers = {
            "thumb": [1, 2, 3, 4],
            "index": [5, 6, 7, 8],
            "middle": [9, 10, 11, 12],
            "ring": [13, 14, 15, 16],
            "pinky": [17, 18, 19, 20]
        }
        
        # 计算各手指长度
        finger_lengths_calc = {}
        for finger_name, indices in fingers.items():
            total_length = 0
            for i in range(len(indices) - 1):
                p1 = landmarks.landmark[indices[i]]
                p2 = landmarks.landmark[indices[i + 1]]
                length = np.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
                total_length += length
            finger_lengths_calc[finger_name] = total_length
        
        # 归一化（以中指为基准）
        middle_length = finger_lengths_calc.get("middle", 1.0)
        if middle_length > 0:
            for finger_name, length in finger_lengths_calc.items():
                ratio = length / middle_length
                finger_ratios[finger_name] = float(ratio)  # 保存连续值
                
                # 更细致的分类（使用更窄的阈值）
                if ratio > 1.15:
                    finger_lengths[finger_name] = "很长"
                elif ratio > 1.05:
                    finger_lengths[finger_name] = "长"
                elif ratio < 0.85:
                    finger_lengths[finger_name] = "短"
                elif ratio < 0.95:
                    finger_lengths[finger_name] = "稍短"
                else:
                    finger_lengths[finger_name] = "中等"
        
        return {
            "categories": finger_lengths,
            "ratios": finger_ratios,
            "absolute_lengths": {k: float(v) for k, v in finger_lengths_calc.items()}
        }
    
    def _measure_hand(self, landmarks, image_shape) -> Dict[str, float]:
        """测量手部尺寸（保留兼容性）"""
        return self._measure_hand_enhanced(landmarks, image_shape)
    
    def _measure_hand_enhanced(self, landmarks, image_shape) -> Dict[str, float]:
        """测量手部尺寸（增强版：更多测量维度）"""
        measurements = {}
        
        # 手掌宽度（食指根部到小指根部）
        index_mcp = landmarks.landmark[5]
        pinky_mcp = landmarks.landmark[17]
        palm_width = np.sqrt(
            (pinky_mcp.x - index_mcp.x)**2 * image_shape[1]**2 +
            (pinky_mcp.y - index_mcp.y)**2 * image_shape[0]**2
        )
        measurements["palm_width"] = float(palm_width)
        
        # 手掌长度（手腕到中指根部）
        wrist = landmarks.landmark[0]
        middle_mcp = landmarks.landmark[9]
        palm_length = np.sqrt(
            (middle_mcp.x - wrist.x)**2 * image_shape[1]**2 +
            (middle_mcp.y - wrist.y)**2 * image_shape[0]**2
        )
        measurements["palm_length"] = float(palm_length)
        
        # 宽高比
        if palm_length > 0:
            measurements["palm_ratio"] = float(palm_width / palm_length)
        
        # 手掌面积（近似）
        measurements["palm_area"] = float(palm_width * palm_length)
        
        # 手指总长度
        finger_total = 0
        for i in [8, 12, 16, 20]:  # 各手指指尖
            tip = landmarks.landmark[i]
            mcp_idx = i - 3  # 对应的根部
            mcp = landmarks.landmark[mcp_idx]
            finger_len = np.sqrt(
                (tip.x - mcp.x)**2 * image_shape[1]**2 +
                (tip.y - mcp.y)**2 * image_shape[0]**2
            )
            finger_total += finger_len
        measurements["finger_total_length"] = float(finger_total)
        
        # 手掌与手指比例
        if palm_length > 0:
            measurements["palm_finger_ratio"] = float(palm_length / finger_total) if finger_total > 0 else 0
        
        return measurements
    
    def _extract_palm_lines(self, img: np.ndarray, landmarks) -> Dict[str, str]:
        """提取掌纹（保留兼容性）"""
        return self._extract_palm_lines_enhanced(img, landmarks)
    
    def _extract_palm_lines_enhanced(self, img: np.ndarray, landmarks) -> Dict[str, str]:
        """提取掌纹（增强版，提取更多信息）"""
        # 获取手掌区域
        wrist = landmarks.landmark[0]
        index_mcp = landmarks.landmark[5]
        pinky_mcp = landmarks.landmark[17]
        middle_tip = landmarks.landmark[12]  # 中指指尖
        
        # 转换为像素坐标
        h, w = img.shape[:2]
        wrist_pt = (int(wrist.x * w), int(wrist.y * h))
        index_pt = (int(index_mcp.x * w), int(index_mcp.y * h))
        pinky_pt = (int(pinky_mcp.x * w), int(pinky_mcp.y * h))
        middle_tip_pt = (int(middle_tip.x * w), int(middle_tip.y * h))
        
        # 提取手掌 ROI（扩大范围以包含更多掌纹信息）
        x_min = min(wrist_pt[0], index_pt[0], pinky_pt[0], middle_tip_pt[0])
        x_max = max(wrist_pt[0], index_pt[0], pinky_pt[0], middle_tip_pt[0])
        y_min = min(wrist_pt[1], index_pt[1], pinky_pt[1], middle_tip_pt[1])
        y_max = max(wrist_pt[1], index_pt[1], pinky_pt[1], middle_tip_pt[1])
        
        # 扩展边界（增加 padding 以捕获更多细节）
        padding = 50
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(w, x_max + padding)
        y_max = min(h, y_max + padding)
        
        palm_roi = img[y_min:y_max, x_min:x_max]
        
        if palm_roi.size == 0:
            return {
                "life_line": "无法检测",
                "head_line": "无法检测",
                "heart_line": "无法检测",
                "fate_line": "无法检测",
                "marriage_line": "无法检测"
            }
        
        # 转换为灰度
        gray = cv2.cvtColor(palm_roi, cv2.COLOR_BGR2GRAY)
        
        # 增强对比度（CLAHE）
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
        
        # 边缘检测（使用自适应阈值）
        edges = cv2.Canny(blurred, 30, 100)
        
        # 形态学操作，连接断开的线条
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # 线条检测（降低阈值以检测更多线条）
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30, minLineLength=20, maxLineGap=15)
        
        # 分析掌纹（更详细的分类）
        palm_lines = {
            "life_line": "中等",
            "head_line": "中等",
            "heart_line": "中等",
            "fate_line": "中等",
            "marriage_line": "中等",
            "line_count": 0,
            "line_density": "中等"
        }
        
        if lines is not None and len(lines) > 0:
            line_count = len(lines)
            palm_lines["line_count"] = line_count
            
            # 计算线条密度
            roi_area = palm_roi.shape[0] * palm_roi.shape[1]
            density = line_count / (roi_area / 1000) if roi_area > 0 else 0
            
            if density > 0.5:
                palm_lines["line_density"] = "高"
            elif density > 0.2:
                palm_lines["line_density"] = "中等"
            else:
                palm_lines["line_density"] = "低"
            
            # 根据线条数量和密度判断掌纹
            if line_count > 10:
                palm_lines["life_line"] = "深且长"
                palm_lines["head_line"] = "清晰"
                palm_lines["heart_line"] = "明显"
            elif line_count > 5:
                palm_lines["life_line"] = "中等"
                palm_lines["head_line"] = "中等"
                palm_lines["heart_line"] = "中等"
            else:
                palm_lines["life_line"] = "浅"
                palm_lines["head_line"] = "模糊"
                palm_lines["heart_line"] = "不明显"
            
            # 分析线条方向（简化版）
            horizontal_lines = 0
            vertical_lines = 0
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                if angle < 30 or angle > 150:
                    horizontal_lines += 1
                else:
                    vertical_lines += 1
            
            if horizontal_lines > vertical_lines:
                palm_lines["fate_line"] = "明显"
            else:
                palm_lines["fate_line"] = "不明显"
        
        # 改进的掌纹识别：根据线条位置和方向识别具体掌纹（覆盖之前的粗略判断）
        specific_lines = self._identify_specific_palm_lines(lines, landmarks, img.shape, palm_roi.shape)
        # 合并结果（优先使用具体识别结果）
        for key in ["life_line", "head_line", "heart_line", "fate_line", "marriage_line"]:
            if specific_lines.get(key) != "中等" and specific_lines.get(key) != "不明显":
                palm_lines[key] = specific_lines[key]
        
        return palm_lines
    
    def _identify_specific_palm_lines(self, lines, landmarks, image_shape, roi_shape) -> Dict[str, str]:
        """识别具体掌纹类型（根据位置和方向）"""
        palm_lines = {
            "life_line": "中等",
            "head_line": "中等",
            "heart_line": "中等",
            "fate_line": "中等",
            "marriage_line": "中等",
            "line_count": len(lines) if lines is not None else 0,
            "line_density": "中等"
        }
        
        if lines is None or len(lines) == 0:
            return palm_lines
        
        h, w = image_shape[:2]
        roi_h, roi_w = roi_shape[:2]
        
        # 获取关键点位置（用于定位掌纹区域）
        wrist = landmarks.landmark[0]
        index_mcp = landmarks.landmark[5]
        middle_mcp = landmarks.landmark[9]
        ring_mcp = landmarks.landmark[13]
        pinky_mcp = landmarks.landmark[17]
        
        # 转换为 ROI 内的相对坐标
        wrist_y = int(wrist.y * h)
        index_x = int(index_mcp.x * w)
        middle_y = int(middle_mcp.y * h)
        
        # 分类线条：根据位置和方向
        life_lines = []  # 生命线：从拇指根部向下弯曲
        head_lines = []  # 智慧线：从食指根部横向
        heart_lines = []  # 感情线：从手掌边缘横向
        fate_lines = []  # 事业线：从手腕向上
        marriage_lines = []  # 婚姻线：小指根部横向
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 计算线条中心点
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            # 计算角度
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # 生命线：从拇指根部向下弯曲（角度 60-120 度，位置在手掌内侧）
            if 60 < angle < 120 and center_x < index_x:
                life_lines.append((length, angle))
            # 智慧线：横向（角度 0-30 或 150-180 度，位置在手掌中部）
            elif (angle < 30 or angle > 150) and middle_y - 20 < center_y < middle_y + 20:
                head_lines.append((length, angle))
            # 感情线：横向（角度 0-30 或 150-180 度，位置在手指根部）
            elif (angle < 30 or angle > 150) and center_y < middle_y - 30:
                heart_lines.append((length, angle))
            # 事业线：纵向（角度 60-120 度，位置在手掌中央）
            elif 60 < angle < 120 and abs(center_x - w/2) < w/4:
                fate_lines.append((length, angle))
            # 婚姻线：横向（角度 0-30 或 150-180 度，位置在小指根部）
            elif (angle < 30 or angle > 150) and center_y < middle_y - 50:
                marriage_lines.append((length, angle))
        
        # 根据检测到的线条数量和长度判断掌纹特征
        if len(life_lines) > 0:
            avg_length = sum(l[0] for l in life_lines) / len(life_lines)
            if avg_length > 50:
                palm_lines["life_line"] = "深且长"
            elif avg_length > 30:
                palm_lines["life_line"] = "中等"
            else:
                palm_lines["life_line"] = "浅短"
        
        if len(head_lines) > 0:
            avg_length = sum(l[0] for l in head_lines) / len(head_lines)
            if avg_length > 40:
                palm_lines["head_line"] = "清晰深长"
            elif avg_length > 25:
                palm_lines["head_line"] = "中等"
            else:
                palm_lines["head_line"] = "浅短"
        
        if len(heart_lines) > 0:
            avg_length = sum(l[0] for l in heart_lines) / len(heart_lines)
            if avg_length > 45:
                palm_lines["heart_line"] = "明显深长"
            elif avg_length > 25:
                palm_lines["heart_line"] = "中等"
            else:
                palm_lines["heart_line"] = "不明显"
        
        if len(fate_lines) > 0:
            avg_length = sum(l[0] for l in fate_lines) / len(fate_lines)
            if avg_length > 40:
                palm_lines["fate_line"] = "明显"
            else:
                palm_lines["fate_line"] = "不明显"
        
        if len(marriage_lines) > 0:
            palm_lines["marriage_line"] = "明显" if len(marriage_lines) > 1 else "不明显"
        
        # 计算线条密度
        roi_area = roi_h * roi_w
        density = len(lines) / (roi_area / 1000) if roi_area > 0 else 0
        if density > 0.5:
            palm_lines["line_density"] = "高"
        elif density > 0.2:
            palm_lines["line_density"] = "中等"
        else:
            palm_lines["line_density"] = "低"
        
        return palm_lines
    
    def _analyze_finger_thickness(self, img: np.ndarray, landmarks) -> Dict[str, float]:
        """分析手指粗细"""
        thickness = {}
        
        # 定义手指关键点（用于测量宽度）
        finger_joints = {
            "thumb": [2, 3],  # 拇指关节
            "index": [6, 7],  # 食指关节
            "middle": [10, 11],  # 中指关节
            "ring": [14, 15],  # 无名指关节
            "pinky": [18, 19]  # 小指关节
        }
        
        h, w = img.shape[:2]
        
        for finger_name, indices in finger_joints.items():
            if len(indices) >= 2:
                p1 = landmarks.landmark[indices[0]]
                p2 = landmarks.landmark[indices[1]]
                # 计算关节间的距离（近似手指宽度）
                width = np.sqrt(
                    (p2.x - p1.x)**2 * w**2 +
                    (p2.y - p1.y)**2 * h**2
                )
                thickness[finger_name] = float(width)
        
        return thickness
    
    def _analyze_palm_texture(self, img: np.ndarray, landmarks) -> Dict[str, Any]:
        """分析手掌纹理特征"""
        texture = {
            "roughness": "中等",
            "wrinkle_density": 0.0,
            "skin_tone": "中等"
        }
        
        # 获取手掌 ROI
        wrist = landmarks.landmark[0]
        index_mcp = landmarks.landmark[5]
        pinky_mcp = landmarks.landmark[17]
        
        h, w = img.shape[:2]
        wrist_pt = (int(wrist.x * w), int(wrist.y * h))
        index_pt = (int(index_mcp.x * w), int(index_mcp.y * h))
        pinky_pt = (int(pinky_mcp.x * w), int(pinky_mcp.y * h))
        
        x_min = max(0, min(wrist_pt[0], index_pt[0], pinky_pt[0]) - 20)
        x_max = min(w, max(wrist_pt[0], index_pt[0], pinky_pt[0]) + 20)
        y_min = max(0, min(wrist_pt[1], index_pt[1], pinky_pt[1]) - 20)
        y_max = min(h, max(wrist_pt[1], index_pt[1], pinky_pt[1]) + 20)
        
        palm_roi = img[y_min:y_max, x_min:x_max]
        
        if palm_roi.size > 0:
            # 转换为灰度
            gray = cv2.cvtColor(palm_roi, cv2.COLOR_BGR2GRAY)
            
            # 计算纹理粗糙度（使用局部方差）
            kernel = np.ones((5, 5), np.float32) / 25
            local_mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
            local_var = cv2.filter2D((gray.astype(np.float32) - local_mean)**2, -1, kernel)
            avg_var = np.mean(local_var)
            
            if avg_var > 500:
                texture["roughness"] = "粗糙"
            elif avg_var < 200:
                texture["roughness"] = "细腻"
            else:
                texture["roughness"] = "中等"
            
            # 计算皱纹密度（边缘检测）
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            texture["wrinkle_density"] = float(edge_density)
            
            # 分析肤色（简化版）
            mean_color = np.mean(palm_roi, axis=(0, 1))
            if mean_color[0] > 150:  # BGR 格式
                texture["skin_tone"] = "较白"
            elif mean_color[0] < 100:
                texture["skin_tone"] = "较深"
            else:
                texture["skin_tone"] = "中等"
        
        return texture
    
    def _detect_special_marks(self, img: np.ndarray, landmarks) -> List[Dict[str, Any]]:
        """检测特殊标记（星纹、岛纹、十字纹等）"""
        marks = []
        
        # 获取手掌 ROI
        wrist = landmarks.landmark[0]
        index_mcp = landmarks.landmark[5]
        pinky_mcp = landmarks.landmark[17]
        
        h, w = img.shape[:2]
        wrist_pt = (int(wrist.x * w), int(wrist.y * h))
        index_pt = (int(index_mcp.x * w), int(index_mcp.y * h))
        pinky_pt = (int(pinky_mcp.x * w), int(pinky_mcp.y * h))
        
        x_min = max(0, min(wrist_pt[0], index_pt[0], pinky_pt[0]) - 20)
        x_max = min(w, max(wrist_pt[0], index_pt[0], pinky_pt[0]) + 20)
        y_min = max(0, min(wrist_pt[1], index_pt[1], pinky_pt[1]) - 20)
        y_max = min(h, max(wrist_pt[1], index_pt[1], pinky_pt[1]) + 20)
        
        palm_roi = img[y_min:y_max, x_min:x_max]
        
        if palm_roi.size > 0:
            gray = cv2.cvtColor(palm_roi, cv2.COLOR_BGR2GRAY)
            
            # 检测圆形标记（可能是星纹或岛纹）
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, 1, 20,
                param1=50, param2=30, minRadius=3, maxRadius=15
            )
            
            if circles is not None:
                for circle in circles[0]:
                    x, y, r = circle
                    marks.append({
                        "type": "圆形标记",
                        "position": {"x": float(x), "y": float(y)},
                        "radius": float(r)
                    })
            
            # 检测交叉点（可能是十字纹）
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 20, minLineLength=10, maxLineGap=5)
            
            if lines is not None and len(lines) > 1:
                # 检测线条交叉点
                for i, line1 in enumerate(lines):
                    for line2 in lines[i+1:]:
                        x1, y1, x2, y2 = line1[0]
                        x3, y3, x4, y4 = line2[0]
                        # 计算交叉点（简化版）
                        # 这里可以添加更复杂的交叉点检测逻辑
                        pass
        
        return marks
    
    def _detect_hand_orientation(self, landmarks) -> str:
        """判断左右手"""
        # 通过拇指位置判断
        thumb_tip = landmarks.landmark[4]
        index_mcp = landmarks.landmark[5]
        
        # 如果拇指在食指左侧，通常是左手；在右侧，通常是右手
        if thumb_tip.x < index_mcp.x:
            return "左手"
        else:
            return "右手"
    
    def _extract_features_fallback(self, img: np.ndarray) -> Dict[str, Any]:
        """降级方案：不使用 MediaPipe 的特征提取"""
        # 检测手部区域
        hand_region = self.preprocessor.detect_hand_region(img)
        
        features = {
            "hand_shape": "未知",
            "finger_lengths": {},
            "palm_lines": {
                "life_line": "无法检测",
                "head_line": "无法检测",
                "heart_line": "无法检测"
            },
            "measurements": {},
            "landmarks": []
        }
        
        if hand_region:
            x, y, w, h = hand_region
            # 简单的宽高比判断
            ratio = w / h if h > 0 else 0
            if ratio > 0.7:
                features["hand_shape"] = "方形手"
            elif ratio < 0.5:
                features["hand_shape"] = "尖形手"
            else:
                features["hand_shape"] = "长方形手"
            
            features["measurements"] = {
                "palm_width": float(w),
                "palm_length": float(h),
                "palm_ratio": float(ratio)
            }
        
        return features


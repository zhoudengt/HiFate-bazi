#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MediaPipe 单例管理器
复用 MediaPipe 对象，避免重复初始化，提高性能
"""

import threading
import logging

logger = logging.getLogger(__name__)
from typing import Optional

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class MediaPipeSingleton:
    """MediaPipe 对象单例管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        if MEDIAPIPE_AVAILABLE:
            self.mp_hands = mp.solutions.hands
            self.mp_face_mesh = mp.solutions.face_mesh
        else:
            self.mp_hands = None
            self.mp_face_mesh = None
        
        self._hands_instance = None
        self._face_mesh_instance = None
        self._hands_lock = threading.Lock()
        self._face_mesh_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_hands(self):
        """获取 Hands 实例（单例）"""
        if not MEDIAPIPE_AVAILABLE:
            return None
        
        if self._hands_instance is None:
            with self._hands_lock:
                if self._hands_instance is None:
                    try:
                        self._hands_instance = self.mp_hands.Hands(
                            static_image_mode=True,
                            max_num_hands=1,
                            min_detection_confidence=0.7,
                            min_tracking_confidence=0.5
                        )
                        logger.info("✅ MediaPipe Hands 单例已创建")
                    except Exception as e:
                        logger.info(f"⚠️  MediaPipe Hands 初始化失败: {e}")
                        return None
        
        return self._hands_instance
    
    def get_face_mesh(self):
        """获取 FaceMesh 实例（单例）"""
        if not MEDIAPIPE_AVAILABLE:
            return None
        
        if self._face_mesh_instance is None:
            with self._face_mesh_lock:
                if self._face_mesh_instance is None:
                    try:
                        self._face_mesh_instance = self.mp_face_mesh.FaceMesh(
                            static_image_mode=True,
                            max_num_faces=1,
                            refine_landmarks=True,
                            min_detection_confidence=0.6,
                            min_tracking_confidence=0.5
                        )
                        logger.info("✅ MediaPipe FaceMesh 单例已创建")
                    except Exception as e:
                        logger.info(f"⚠️  MediaPipe FaceMesh 初始化失败: {e}")
                        return None
        
        return self._face_mesh_instance
    
    def reset_hands(self):
        """重置 Hands 实例（用于错误恢复）"""
        with self._hands_lock:
            if self._hands_instance:
                try:
                    self._hands_instance.close()
                except:
                    pass
                self._hands_instance = None
    
    def reset_face_mesh(self):
        """重置 FaceMesh 实例（用于错误恢复）"""
        with self._face_mesh_lock:
            if self._face_mesh_instance:
                try:
                    self._face_mesh_instance.close()
                except:
                    pass
                self._face_mesh_instance = None


# -*- coding: utf-8 -*-
"""
办公桌物品检测器
使用 YOLOv8 进行物品识别
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DeskItemDetector:
    """办公桌物品检测器"""
    
    # 办公桌相关物品映射表（COCO数据集类别 -> 中文名称）
    ITEM_MAP = {
        'laptop': '笔记本电脑',
        'mouse': '鼠标',
        'keyboard': '键盘',
        'cup': '杯子',
        'bottle': '水瓶',
        'book': '书籍',
        'potted plant': '绿植',
        'cell phone': '手机',
        'clock': '时钟',
        'vase': '花瓶',
        'bowl': '碗',
        'scissors': '剪刀',
        'teddy bear': '玩偶',
        'tv': '显示器',
        'remote': '遥控器',
        'pen': '笔'
    }
    
    # 特殊物品（需要自定义训练或规则识别）
    SPECIAL_ITEMS = {
        'kettle': '烧水壶',
        'pen_holder': '笔筒',
        'calendar': '日历',
        'photo_frame': '相框',
        'cactus': '仙人掌',
        'bamboo': '竹子',
        'lucky_cat': '招财猫',
        'fish_tank': '鱼缸',
        'mirror': '镜子'
    }
    
    def __init__(self, model_path: str = 'yolov8n.pt', confidence_threshold: float = 0.5):
        """
        初始化检测器
        
        Args:
            model_path: YOLO模型路径
            confidence_threshold: 置信度阈值
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            logger.info(f"✅ YOLO模型加载成功: {model_path}")
        except ImportError as e:
            logger.warning(f"⚠️ ultralytics 未安装，将使用OpenCV备用方案: {e}")
            self.model = None
        except Exception as e:
            logger.error(f"❌ YOLO模型加载失败: {e}")
            self.model = None
    
    def detect(self, image_bytes: bytes) -> Dict:
        """
        检测办公桌物品
        
        Args:
            image_bytes: 图像字节数据
        
        Returns:
            检测结果字典
        """
        try:
            # 1. 解码图像
            img = self._decode_image(image_bytes)
            if img is None:
                return {'success': False, 'error': '图像解码失败'}
            
            # 2. 执行检测
            if self.model is not None:
                items = self._detect_with_yolo(img)
            else:
                logger.warning("⚠️ YOLO模型未安装，使用备用方案（准确率较低）")
                logger.warning("   建议执行: ./scripts/install_yolo.sh")
                items = self._detect_with_opencv(img)
            
            # 3. 过滤相关物品
            filtered_items = [
                item for item in items 
                if item['name'] in self.ITEM_MAP or item['name'] in self.SPECIAL_ITEMS
            ]
            
            # 4. 记录检测结果
            if len(filtered_items) == 0 and self.model is None:
                logger.warning(f"❌ 未检测到物品（使用备用方案）")
                logger.warning("   原因：YOLO模型未安装，OpenCV备用方案准确率较低")
                logger.warning("   解决：请运行 ./scripts/install_yolo.sh 安装YOLO模型")
            else:
                logger.info(f"✅ 检测到 {len(filtered_items)} 个办公桌相关物品")
            
            return {
                'success': True,
                'items': filtered_items,
                'image_shape': img.shape,
                'total_detected': len(items),
                'using_backup': self.model is None,  # 标记是否使用备用方案
                'warning': '未安装YOLO模型，使用备用检测方案（准确率较低）' if self.model is None else None
            }
            
        except Exception as e:
            logger.error(f"物品检测失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _decode_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """解码图像"""
        try:
            img_array = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"图像解码失败: {e}")
            return None
    
    def _detect_with_yolo(self, img: np.ndarray) -> List[Dict]:
        """使用YOLO检测物品"""
        items = []
        
        try:
            # 执行检测
            results = self.model(img, verbose=False)
            
            # 解析结果
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].cpu().numpy().tolist()  # [x1, y1, x2, y2]
                    
                    if confidence >= self.confidence_threshold:
                        label = self.ITEM_MAP.get(class_name, class_name)
                        
                        items.append({
                            'name': class_name,
                            'label': label,
                            'confidence': round(confidence, 2),
                            'bbox': bbox
                        })
            
            logger.debug(f"YOLO检测到 {len(items)} 个物品")
            
        except Exception as e:
            logger.error(f"YOLO检测失败: {e}", exc_info=True)
        
        return items
    
    def _detect_with_opencv(self, img: np.ndarray) -> List[Dict]:
        """
        使用OpenCV备用检测方案（简化版）
        注意：准确率较低，仅作为备用方案
        """
        logger.warning("使用OpenCV备用检测方案，准确率可能较低")
        
        items = []
        height, width = img.shape[:2]
        
        # 简单的颜色和形状检测（示例）
        # 这里可以实现一些基础的物品检测逻辑
        # 比如：检测绿色物体（可能是植物）、矩形物体（可能是书本）等
        
        # 检测绿色物体（可能是植物）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # 过滤小面积
                x, y, w, h = cv2.boundingRect(contour)
                items.append({
                    'name': 'potted plant',
                    'label': '绿植',
                    'confidence': 0.6,
                    'bbox': [x, y, x + w, y + h]
                })
        
        logger.debug(f"OpenCV检测到 {len(items)} 个物品")
        
        return items
    
    def draw_detections(self, image_bytes: bytes, items: List[Dict]) -> Optional[bytes]:
        """
        在图像上绘制检测结果
        
        Args:
            image_bytes: 原始图像
            items: 检测到的物品列表
        
        Returns:
            绘制后的图像字节数据
        """
        try:
            img = self._decode_image(image_bytes)
            if img is None:
                return None
            
            # 绘制边界框和标签
            for item in items:
                bbox = item['bbox']
                label = item['label']
                confidence = item['confidence']
                
                x1, y1, x2, y2 = map(int, bbox)
                
                # 绘制矩形
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # 绘制标签
                text = f"{label} {confidence:.2f}"
                cv2.putText(img, text, (x1, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 编码为字节
            _, encoded = cv2.imencode('.jpg', img)
            return encoded.tobytes()
            
        except Exception as e:
            logger.error(f"绘制检测结果失败: {e}")
            return None


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    detector = DeskItemDetector()
    
    # 加载测试图像
    with open("test_desk.jpg", "rb") as f:
        image_bytes = f.read()
    
    result = detector.detect(image_bytes)
    print(f"检测结果: {result}")


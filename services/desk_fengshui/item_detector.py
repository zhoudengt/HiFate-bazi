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
    
    def __init__(self, model_path: str = 'yolov8n.pt', confidence_threshold: float = 0.15):
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
            
            # 3. 过滤相关物品（大幅放宽条件，尽量保留所有检测到的物品）
            # 允许的物品类别（COCO数据集中的常见办公桌物品）
            allowed_items = set(self.ITEM_MAP.keys()) | set(self.SPECIAL_ITEMS.keys())
            # 添加更多可能的物品类别
            additional_items = ['cell phone', 'remote', 'pen', 'book', 'vase', 'bowl', 'scissors', 'clock', 
                              'calculator', 'tissue', 'container', 'box', 'bag', 'mug', 'cup', 'bottle']
            allowed_items.update(additional_items)
            
            # 先过滤允许的物品
            filtered_items = [
                item for item in items 
                if item['name'] in allowed_items
            ]
            
            # 如果过滤后物品太少，保留所有置信度>0.2的物品（不限制类别）
            if len(filtered_items) < 5:
                filtered_items = [
                    item for item in items 
                    if item.get('confidence', 0) > 0.2
                ]
                logger.info(f"放宽过滤条件，保留 {len(filtered_items)} 个物品（置信度>0.2）")
            
            # 4. 去重：相同物品且位置重叠的合并为一个（使用IOU计算重叠度）
            if len(filtered_items) > 1:
                unique_items = []
                for i, item in enumerate(filtered_items):
                    is_duplicate = False
                    bbox1 = item.get('bbox', [0, 0, 0, 0])
                    
                    if isinstance(bbox1, list) and len(bbox1) >= 4:
                        x1_1, y1_1, x2_1, y2_1 = bbox1[0], bbox1[1], bbox1[2], bbox1[3]
                        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
                        
                        # 检查是否与已有物品重叠
                        for existing_item in unique_items:
                            if existing_item['name'] != item['name']:
                                continue
                            
                            bbox2 = existing_item.get('bbox', [0, 0, 0, 0])
                            if isinstance(bbox2, list) and len(bbox2) >= 4:
                                x1_2, y1_2, x2_2, y2_2 = bbox2[0], bbox2[1], bbox2[2], bbox2[3]
                                
                                # 计算重叠区域
                                overlap_x1 = max(x1_1, x1_2)
                                overlap_y1 = max(y1_1, y1_2)
                                overlap_x2 = min(x2_1, x2_2)
                                overlap_y2 = min(y2_1, y2_2)
                                
                                if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                                    overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                                    # 如果重叠面积超过较小物品的50%，视为重复
                                    min_area = min(area1, (x2_2 - x1_2) * (y2_2 - y1_2))
                                    if overlap_area / min_area > 0.5:
                                        is_duplicate = True
                                        # 保留置信度更高的
                                        if item.get('confidence', 0) > existing_item.get('confidence', 0):
                                            unique_items.remove(existing_item)
                                            unique_items.append(item)
                                        break
                    
                    if not is_duplicate:
                        unique_items.append(item)
                
                filtered_items = unique_items
                logger.info(f"去重后保留 {len(filtered_items)} 个物品")
            
            # 4. 记录检测结果
            warning_msg = None
            if self.model is None:
                # 使用备用方案时
                if len(filtered_items) == 0:
                    logger.warning(f"❌ 未检测到物品（使用备用方案）")
                    logger.warning("   原因：YOLO模型未安装，OpenCV备用方案准确率较低")
                    logger.warning("   解决：请运行 ./scripts/install_yolo.sh 安装YOLO模型")
                    warning_msg = '未安装YOLO模型，使用备用检测方案（准确率较低）'
                else:
                    logger.info(f"✅ 检测到 {len(filtered_items)} 个办公桌相关物品（使用备用方案）")
                    # 即使检测到物品，也不显示警告，避免干扰用户体验
            else:
                logger.info(f"✅ 检测到 {len(filtered_items)} 个办公桌相关物品")
            
            return {
                'success': True,
                'items': filtered_items,
                'image_shape': img.shape,
                'total_detected': len(items),
                'using_backup': self.model is None,  # 标记是否使用备用方案
                'warning': warning_msg  # 只有真正检测失败时才返回警告
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
                        # 特殊处理：laptop需要更高的置信度（因为容易误识别显示器为laptop）
                        if class_name == 'laptop' and confidence < 0.4:
                            continue
                        
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


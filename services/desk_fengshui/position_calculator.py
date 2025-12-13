# -*- coding: utf-8 -*-
"""
方位计算器
计算物品在办公桌上的相对位置和八卦方位
"""

from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class PositionCalculator:
    """方位计算器"""
    
    # 八卦方位映射表
    BAGUA_MAP = {
        ('left', 'front'): 'east',          # 左前 -> 东
        ('center', 'front'): 'south',       # 正前 -> 南
        ('right', 'front'): 'west',         # 右前 -> 西
        ('left', 'center'): 'east',         # 左中 -> 东
        ('center', 'center'): 'center',     # 中心 -> 中
        ('right', 'center'): 'west',        # 右中 -> 西
        ('left', 'back'): 'northeast',      # 左后 -> 东北
        ('center', 'back'): 'north',        # 正后 -> 北
        ('right', 'back'): 'northwest'      # 右后 -> 西北
    }
    
    # 方位中文名称
    DIRECTION_NAMES = {
        'left': '左侧（青龙位）',
        'right': '右侧（白虎位）',
        'front': '前方（朱雀位）',
        'back': '后方（玄武位）',
        'center': '中央',
        'east': '东方',
        'west': '西方',
        'south': '南方',
        'north': '北方',
        'northeast': '东北方',
        'northwest': '西北方',
        'southeast': '东南方',
        'southwest': '西南方'
    }
    
    @classmethod
    def calculate_position(cls, bbox: List[float], img_shape: Tuple[int, int]) -> Dict:
        """
        计算物品的相对位置和八卦方位
        
        Args:
            bbox: 边界框 [x1, y1, x2, y2]
            img_shape: 图像尺寸 (height, width)
        
        Returns:
            位置信息字典
        """
        height, width = img_shape[:2]
        
        # 计算物品中心点
        x_center = (bbox[0] + bbox[2]) / 2
        y_center = (bbox[1] + bbox[3]) / 2
        
        # 计算相对位置（横向）
        if x_center < width * 0.35:
            horizontal = 'left'
        elif x_center > width * 0.65:
            horizontal = 'right'
        else:
            horizontal = 'center'
        
        # 计算相对位置（纵向）
        if y_center < height * 0.35:
            vertical = 'front'
        elif y_center > height * 0.65:
            vertical = 'back'
        else:
            vertical = 'center'
        
        # 映射到八卦方位
        bagua_direction = cls.BAGUA_MAP.get((horizontal, vertical), 'unknown')
        
        # 获取中文名称
        relative_name = cls.DIRECTION_NAMES.get(horizontal, horizontal)
        vertical_name = cls.DIRECTION_NAMES.get(vertical, vertical)
        bagua_name = cls.DIRECTION_NAMES.get(bagua_direction, bagua_direction)
        
        return {
            'relative': horizontal,
            'relative_name': relative_name,
            'vertical': vertical,
            'vertical_name': vertical_name,
            'bagua_direction': bagua_direction,
            'bagua_name': bagua_name,
            'center': [round(x_center, 2), round(y_center, 2)],
            'normalized': {
                'x': round(x_center / width, 2),
                'y': round(y_center / height, 2)
            }
        }
    
    @classmethod
    def calculate_all_positions(cls, items: List[Dict], img_shape: Tuple[int, int]) -> List[Dict]:
        """
        批量计算物品位置
        
        Args:
            items: 检测到的物品列表
            img_shape: 图像尺寸
        
        Returns:
            增强后的物品列表（包含位置信息）
        """
        enriched_items = []
        
        for item in items:
            bbox = item.get('bbox', [])
            if len(bbox) != 4:
                logger.warning(f"物品 {item.get('name')} 的bbox格式不正确: {bbox}")
                continue
            
            # 计算位置
            position = cls.calculate_position(bbox, img_shape)
            
            # 合并到物品信息中
            enriched_item = {
                **item,
                'position': position
            }
            
            enriched_items.append(enriched_item)
        
        return enriched_items
    
    @classmethod
    def get_position_summary(cls, items: List[Dict]) -> Dict:
        """
        获取物品位置分布统计
        
        Args:
            items: 物品列表（含位置信息）
        
        Returns:
            统计信息
        """
        summary = {
            'total': len(items),
            'by_relative': {},
            'by_bagua': {}
        }
        
        for item in items:
            position = item.get('position', {})
            relative = position.get('relative', 'unknown')
            bagua = position.get('bagua_direction', 'unknown')
            
            # 按相对位置统计
            if relative not in summary['by_relative']:
                summary['by_relative'][relative] = []
            summary['by_relative'][relative].append(item['label'])
            
            # 按八卦方位统计
            if bagua not in summary['by_bagua']:
                summary['by_bagua'][bagua] = []
            summary['by_bagua'][bagua].append(item['label'])
        
        return summary
    
    @classmethod
    def check_position_conflict(cls, item1: Dict, item2: Dict, threshold: float = 0.3) -> bool:
        """
        检查两个物品是否位置过于接近（可能冲突）
        
        Args:
            item1, item2: 物品信息
            threshold: 距离阈值（归一化坐标）
        
        Returns:
            是否冲突
        """
        # 🔴 防御性检查：避免链式调用导致 None 错误
        pos1_raw = item1.get('position') or {}
        pos1 = pos1_raw.get('normalized', {}) if isinstance(pos1_raw, dict) else {}
        pos2_raw = item2.get('position') or {}
        pos2 = pos2_raw.get('normalized', {}) if isinstance(pos2_raw, dict) else {}
        
        if not pos1 or not pos2:
            return False
        
        # 计算欧氏距离
        distance = ((pos1['x'] - pos2['x']) ** 2 + (pos1['y'] - pos2['y']) ** 2) ** 0.5
        
        return distance < threshold


if __name__ == "__main__":
    # 测试代码
    items = [
        {'name': 'laptop', 'label': '笔记本电脑', 'bbox': [400, 300, 600, 500]},
        {'name': 'cup', 'label': '杯子', 'bbox': [700, 200, 750, 300]},
        {'name': 'plant', 'label': '绿植', 'bbox': [100, 150, 200, 350]}
    ]
    
    img_shape = (600, 800)  # height, width
    
    enriched = PositionCalculator.calculate_all_positions(items, img_shape)
    
    for item in enriched:
        print(f"{item['label']}: {item['position']}")
    
    summary = PositionCalculator.get_position_summary(enriched)
    print(f"\n位置统计: {summary}")


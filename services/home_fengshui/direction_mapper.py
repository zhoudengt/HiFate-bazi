# -*- coding: utf-8 -*-
"""
方位换算工具
大门朝向 → 九宫格绝对方位映射
照片九宫格区域 → 相对/绝对方位转换
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 8个方向（顺时针）
EIGHT_DIRECTIONS = ['北', '东北', '东', '东南', '南', '西南', '西', '西北']

# 英文←→中文方向映射
DIR_CN_TO_EN = {
    '北': 'north', '东北': 'northeast', '东': 'east', '东南': 'southeast',
    '南': 'south', '西南': 'southwest', '西': 'west', '西北': 'northwest',
    '中': 'center',
}
DIR_EN_TO_CN = {v: k for k, v in DIR_CN_TO_EN.items()}

# 九宫格区域（照片识别用）：3x3格
# 行0=北/后方，行1=中，行2=南/前方（以进门方向为南）
# 列0=西/左，列1=中，列2=东/右
GRID_ZONE_NAMES = {
    (0, 0): '西北', (0, 1): '北',  (0, 2): '东北',
    (1, 0): '西',   (1, 1): '中',  (1, 2): '东',
    (2, 0): '西南', (2, 1): '南',  (2, 2): '东南',
}

# 大门朝向→该房间九宫格的绝对方位
# 以"大门所在墙"为南方起算（传统风水：以门定方位）
# door_direction是大门朝向的方向（门面向哪边），坐山=门朝向的对面
DOOR_DIR_TO_ZONE_MAP: Dict[str, Dict[str, str]] = {
    '南': {
        'south': '南', 'north': '北', 'east': '东', 'west': '西',
        'southeast': '东南', 'southwest': '西南', 'northeast': '东北', 'northwest': '西北',
        'center': '中',
    },
    '北': {
        'south': '北', 'north': '南', 'east': '西', 'west': '东',
        'southeast': '西北', 'southwest': '东北', 'northeast': '西南', 'northwest': '东南',
        'center': '中',
    },
    '东': {
        'south': '东', 'north': '西', 'east': '南', 'west': '北',
        'southeast': '东南', 'southwest': '东北', 'northeast': '西南', 'northwest': '西北',
        'center': '中',
    },
    '西': {
        'south': '西', 'north': '东', 'east': '北', 'west': '南',
        'southeast': '西南', 'southwest': '西北', 'northeast': '东南', 'northwest': '东北',
        'center': '中',
    },
    '东南': {
        'south': '东南', 'north': '西北', 'east': '东北', 'west': '西南',
        'southeast': '东', 'southwest': '南', 'northeast': '北', 'northwest': '西',
        'center': '中',
    },
    '西南': {
        'south': '西南', 'north': '东北', 'east': '东南', 'west': '西北',
        'southeast': '南', 'southwest': '西', 'northeast': '东', 'northwest': '北',
        'center': '中',
    },
    '东北': {
        'south': '东北', 'north': '西南', 'east': '西北', 'west': '东南',
        'southeast': '北', 'southwest': '东', 'northeast': '西', 'northwest': '南',
        'center': '中',
    },
    '西北': {
        'south': '西北', 'north': '东南', 'east': '西南', 'west': '东北',
        'southeast': '西', 'southwest': '北', 'northeast': '南', 'northwest': '东',
        'center': '中',
    },
}

# 五行方位对应
DIRECTION_ELEMENT = {
    '东': '木', '东南': '木',
    '南': '火',
    '西南': '土', '中': '土', '东北': '土',
    '西': '金', '西北': '金',
    '北': '水',
}

# 房间内相对位置描述→九宫格区域（照片分析用）
RELATIVE_ZONE_MAP = {
    'top_left':     'northwest', 'top_center':    'north', 'top_right':     'northeast',
    'center_left':  'west',      'center':        'center', 'center_right': 'east',
    'bottom_left':  'southwest', 'bottom_center': 'south', 'bottom_right':  'southeast',
}


def relative_to_absolute(relative_zone: str, door_direction: Optional[str]) -> str:
    """
    将照片中的相对区域（如 north/south）转换为绝对方位中文（如 北/南）

    Args:
        relative_zone: 照片识别的相对区域（英文）
        door_direction: 大门朝向（中文）

    Returns:
        绝对方位（中文），无大门朝向时返回相对区域的英文直译
    """
    if not door_direction or door_direction not in DOOR_DIR_TO_ZONE_MAP:
        return DIR_EN_TO_CN.get(relative_zone, relative_zone)

    zone_map = DOOR_DIR_TO_ZONE_MAP[door_direction]
    return zone_map.get(relative_zone, DIR_EN_TO_CN.get(relative_zone, relative_zone))


def get_direction_element(direction_cn: str) -> str:
    """获取方位对应的五行"""
    return DIRECTION_ELEMENT.get(direction_cn, '')


def is_auspicious_direction(direction_cn: str, auspicious_dirs: List[str]) -> bool:
    """判断某方向是否在吉方列表中"""
    return direction_cn in auspicious_dirs


def bbox_to_zone(bbox: List[float], img_width: int, img_height: int) -> str:
    """
    将边界框坐标转换为九宫格区域（英文）

    Args:
        bbox: [x1, y1, x2, y2]
        img_width: 图片宽度
        img_height: 图片高度

    Returns:
        区域英文名称（如 'north', 'southeast'）
    """
    if not bbox or len(bbox) < 4:
        return 'center'

    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2

    col = 0 if cx < img_width / 3 else (2 if cx > img_width * 2 / 3 else 1)
    row = 0 if cy < img_height / 3 else (2 if cy > img_height * 2 / 3 else 1)

    zone_cn = GRID_ZONE_NAMES.get((row, col), '中')
    return DIR_CN_TO_EN.get(zone_cn, 'center')


def parse_solar_year(solar_date: str) -> Optional[int]:
    """从出生日期字符串中提取年份"""
    if not solar_date:
        return None
    try:
        parts = solar_date.replace('/', '-').split('-')
        return int(parts[0])
    except (ValueError, IndexError):
        return None

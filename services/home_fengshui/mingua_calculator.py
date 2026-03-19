# -*- coding: utf-8 -*-
"""
八宅命卦计算器
根据出生年份和性别计算命卦，确定8个方位的吉凶属性
参考：《八宅明镜》《阳宅三要》

核心规则：
- 东四命/宅(坎1/离9/震3/巽4)：四吉星永远在东四方{北,东,东南,南}
- 西四命/宅(乾6/坤2/艮8/兑7)：四吉星永远在西四方{西,西北,西南,东北}
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 命卦数字→名称
MINGUA_NAMES = {
    1: '坎', 2: '坤', 3: '震', 4: '巽',
    6: '乾', 7: '兑', 8: '艮', 9: '离',
}

# 命卦分组
EAST_FOUR_MINGUA = {1, 3, 4, 9}   # 东四命
WEST_FOUR_MINGUA = {2, 6, 7, 8}   # 西四命

EAST_FOUR_DIRECTIONS = {'北', '东', '东南', '南'}
WEST_FOUR_DIRECTIONS = {'西', '西北', '西南', '东北'}

# 宅卦分组（大门朝向→宅卦名称、宅卦类型）
# 传统八宅：门朝X → 坐在X的对面 → 宅名按坐方
DOOR_TO_HOUSE = {
    '南':   ('坎宅', '东四宅'),   # 坐北朝南
    '北':   ('离宅', '东四宅'),   # 坐南朝北
    '西':   ('震宅', '东四宅'),   # 坐东朝西
    '东':   ('兑宅', '西四宅'),   # 坐西朝东
    '西北': ('巽宅', '东四宅'),   # 坐东南朝西北
    '东南': ('乾宅', '西四宅'),   # 坐西北朝东南
    '西南': ('艮宅', '西四宅'),   # 坐东北朝西南
    '东北': ('坤宅', '西四宅'),   # 坐西南朝东北
}

# 大门朝向 → 宅卦编号（用于直接查 MINGUA_DIRECTIONS 获取宅级方位）
DOOR_TO_HOUSE_GUA = {
    '南': 1,   # 坎宅(坐北)
    '北': 9,   # 离宅(坐南)
    '东': 7,   # 兑宅(坐西)
    '西': 3,   # 震宅(坐东)
    '东南': 6, # 乾宅(坐西北)
    '西北': 4, # 巽宅(坐东南)
    '西南': 8, # 艮宅(坐东北)
    '东北': 2, # 坤宅(坐西南)
}

# 各命卦/宅卦的8个方位吉凶对照表
# 数据来源：《八宅明镜》，已校验东四/西四方位约束
# 东四(1,3,4,9)：四吉必在{北,东,东南,南}，四凶必在{西,西北,西南,东北}
# 西四(2,6,7,8)：四吉必在{西,西北,西南,东北}，四凶必在{北,东,东南,南}
MINGUA_DIRECTIONS: Dict[int, Dict[str, str]] = {
    1: {  # 坎（东四）- 坐北朝南
        '生气': '东南', '天医': '东',  '延年': '南',  '伏位': '北',
        '祸害': '西',  '六煞': '西北', '五鬼': '东北', '绝命': '西南',
    },
    2: {  # 坤（西四）- 坐西南朝东北
        '生气': '东北', '天医': '西',  '延年': '西北', '伏位': '西南',
        '祸害': '东',  '六煞': '南',  '五鬼': '东南', '绝命': '北',
    },
    3: {  # 震（东四）- 坐东朝西
        '生气': '南',  '天医': '东南', '延年': '北',  '伏位': '东',
        '祸害': '西北', '六煞': '东北', '五鬼': '西南', '绝命': '西',
    },
    4: {  # 巽（东四）- 坐东南朝西北
        '生气': '北',  '天医': '东',  '延年': '南',  '伏位': '东南',
        '祸害': '东北', '六煞': '西南', '五鬼': '西北', '绝命': '西',
    },
    6: {  # 乾（西四）- 坐西北朝东南
        '生气': '西',  '天医': '东北', '延年': '西南', '伏位': '西北',
        '祸害': '东南', '六煞': '北',  '五鬼': '东',  '绝命': '南',
    },
    7: {  # 兑（西四）- 坐西朝东
        '生气': '西北', '天医': '西南', '延年': '东北', '伏位': '西',
        '祸害': '东',  '六煞': '北',  '五鬼': '南',  '绝命': '东南',
    },
    8: {  # 艮（西四）- 坐东北朝西南
        '生气': '西南', '天医': '西',  '延年': '西北', '伏位': '东北',
        '祸害': '南',  '六煞': '东南', '五鬼': '北',  '绝命': '东',
    },
    9: {  # 离（东四）- 坐南朝北
        '生气': '东',  '天医': '东南', '延年': '北',  '伏位': '南',
        '祸害': '西南', '六煞': '东北', '五鬼': '西',  '绝命': '西北',
    },
}

# 吉凶分级
AUSPICIOUS = {'生气', '延年', '天医', '伏位'}
INAUSPICIOUS = {'祸害', '六煞', '五鬼', '绝命'}

# 吉凶级别描述
LEVEL_DESC = {
    '生气': '大吉（旺盛、催财、促健康）',
    '延年': '大吉（婚姻、感情、长寿）',
    '天医': '次吉（健康、催贵人）',
    '伏位': '小吉（稳定、保守）',
    '祸害': '小凶（病痛、小人）',
    '六煞': '次凶（桃花劫、破财）',
    '五鬼': '大凶（火灾、盗贼）',
    '绝命': '大凶（重病、凶险）',
}


def calc_mingua(birth_year: int, gender: str) -> int:
    """
    计算八宅命卦（1-9，5男归坤2，5女归艮8）

    男命：(11 - (各位数字之和 % 9)) % 9，结果0取9
    女命：((各位数字之和 % 9) + 4) % 9，结果0取9

    Args:
        birth_year: 出生年份（公历）
        gender: 'male' 或 'female'

    Returns:
        命卦数字 1-9（无5）
    """
    digit_sum = sum(int(d) for d in str(birth_year))
    while digit_sum >= 10:
        digit_sum = sum(int(d) for d in str(digit_sum))

    if gender == 'male':
        gua = (11 - digit_sum) % 9 or 9
        return 2 if gua == 5 else gua
    else:
        gua = (digit_sum + 4) % 9 or 9
        return 8 if gua == 5 else gua


def get_mingua_info(birth_year: int, gender: str, door_direction: Optional[str] = None) -> Dict:
    """
    获取完整的命卦信息

    Args:
        birth_year: 出生年份
        gender: 'male' / 'female'
        door_direction: 大门朝向（可选，用于计算宅卦相配）

    Returns:
        命卦信息字典
    """
    mingua = calc_mingua(birth_year, gender)
    mingua_name = MINGUA_NAMES.get(mingua, str(mingua))
    mingua_type = '东四命' if mingua in EAST_FOUR_MINGUA else '西四命'
    directions = MINGUA_DIRECTIONS.get(mingua, {})

    # 构建方位→吉凶名称的映射（反向索引）
    direction_map: Dict[str, str] = {}
    for level, direction in directions.items():
        direction_map[direction] = level

    # 宅卦信息
    house_name = ''
    house_type = ''
    is_compatible = False
    compatibility_message = ''

    if door_direction and door_direction in DOOR_TO_HOUSE:
        house_name, house_type = DOOR_TO_HOUSE[door_direction]
        # 命宅相配：同属东四或同属西四
        if mingua_type == '东四命' and house_type == '东四宅':
            is_compatible = True
            compatibility_message = f'您为{mingua_type}（{mingua_name}卦），居住{house_name}（{house_type}），命宅相配，大吉！'
        elif mingua_type == '西四命' and house_type == '西四宅':
            is_compatible = True
            compatibility_message = f'您为{mingua_type}（{mingua_name}卦），居住{house_name}（{house_type}），命宅相配，大吉！'
        else:
            compatibility_message = (
                f'您为{mingua_type}（{mingua_name}卦），居住{house_name}（{house_type}），命宅不相配。'
                f'建议通过调整室内家具方向（朝向个人生气位{directions.get("生气", "")}）来弥补。'
            )

    return {
        'mingua': mingua,
        'mingua_name': mingua_name,
        'mingua_type': mingua_type,
        'house_name': house_name,
        'house_type': house_type,
        'is_compatible': is_compatible,
        'compatibility_message': compatibility_message,
        'direction_map': direction_map,
        'directions': directions,   # level → direction（用于规则匹配）
        'auspicious_directions': [directions[k] for k in AUSPICIOUS if k in directions],
        'inauspicious_directions': [directions[k] for k in INAUSPICIOUS if k in directions],
    }


def get_auspicious_direction(mingua: int, level: str) -> Optional[str]:
    """获取指定命卦的某吉凶位方向"""
    return MINGUA_DIRECTIONS.get(mingua, {}).get(level)


def classify_direction(mingua: int, direction: str) -> Tuple[str, str]:
    """
    判断某方向对该命卦的吉凶

    Returns:
        (level, desc) 如 ('生气', '大吉（旺盛、催财、促健康）')
    """
    directions = MINGUA_DIRECTIONS.get(mingua, {})
    for level, dir_ in directions.items():
        if dir_ == direction:
            return level, LEVEL_DESC.get(level, '')
    return '未知', ''


def get_house_gua(door_direction: str) -> Optional[int]:
    """根据大门朝向获取宅卦编号"""
    return DOOR_TO_HOUSE_GUA.get(door_direction)


def get_house_directions(door_direction: str) -> Optional[Dict[str, str]]:
    """
    根据大门朝向获取宅卦的8个方位吉凶

    Args:
        door_direction: 大门朝向（中文，如 '南'、'东北'）

    Returns:
        {'生气': '东南', '天医': '东', ...} 或 None
    """
    house_gua = DOOR_TO_HOUSE_GUA.get(door_direction)
    if house_gua is None:
        return None
    return MINGUA_DIRECTIONS.get(house_gua)


def get_house_star_for_direction(door_direction: str, target_direction: str) -> Tuple[str, str]:
    """
    查询某方位在该宅中对应的星（吉凶）

    Args:
        door_direction: 大门朝向
        target_direction: 要查询的方位（中文）

    Returns:
        (star_name, desc) 如 ('五鬼', '大凶（火灾、盗贼）')
    """
    dirs = get_house_directions(door_direction)
    if not dirs:
        return '未知', ''
    for star, direction in dirs.items():
        if direction == target_direction:
            return star, LEVEL_DESC.get(star, '')
    return '未知', ''

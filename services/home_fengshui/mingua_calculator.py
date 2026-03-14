# -*- coding: utf-8 -*-
"""
八宅命卦计算器
根据出生年份和性别计算命卦，确定8个方位的吉凶属性
参考：《八宅明镜》《阳宅三要》
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

# 宅卦分组（大门朝向→宅卦类型）
DOOR_TO_HOUSE = {
    '南':   ('坎宅', '东四宅'),
    '北':   ('离宅', '东四宅'),
    '西':   ('震宅', '东四宅'),
    '东':   ('兑宅', '西四宅'),
    '西北': ('巽宅', '东四宅'),
    '东南': ('乾宅', '西四宅'),
    '西南': ('艮宅', '西四宅'),
    '东北': ('坤宅', '西四宅'),
}

# 各命卦的8个方位吉凶对照表（完整）
# 数据来源：《八宅明镜》传统风水经典
MINGUA_DIRECTIONS: Dict[int, Dict[str, str]] = {
    1: {  # 坎命（东四命）
        '生气': '东南', '延年': '北',  '天医': '南',  '伏位': '东',
        '祸害': '西',  '六煞': '东北', '五鬼': '西南', '绝命': '西北',
    },
    2: {  # 坤命（西四命）
        '生气': '东北', '延年': '西',  '天医': '西北', '伏位': '西南',
        '祸害': '东',  '六煞': '东南', '五鬼': '南',  '绝命': '北',
    },
    3: {  # 震命（东四命）
        '生气': '南',  '延年': '东南', '天医': '北',  '伏位': '东',
        '祸害': '西北', '六煞': '西南', '五鬼': '西',  '绝命': '东北',
    },
    4: {  # 巽命（东四命）
        '生气': '北',  '延年': '南',  '天医': '东',  '伏位': '东南',
        '祸害': '西南', '六煞': '西',  '五鬼': '东北', '绝命': '西北',
    },
    6: {  # 乾命（西四命）
        '生气': '西',  '延年': '东北', '天医': '西南', '伏位': '西北',
        '祸害': '东南', '六煞': '南',  '五鬼': '北',  '绝命': '东',
    },
    7: {  # 兑命（西四命）
        '生气': '西北', '延年': '西南', '天医': '东北', '伏位': '西',
        '祸害': '南',  '六煞': '北',  '五鬼': '东南', '绝命': '东',
    },
    8: {  # 艮命（西四命）
        '生气': '西南', '延年': '西北', '天医': '西',  '伏位': '东北',
        '祸害': '北',  '六煞': '东',  '五鬼': '东南', '绝命': '南',
    },
    9: {  # 离命（东四命）
        '生气': '东',  '延年': '北',  '天医': '东南', '伏位': '南',
        '祸害': '西北', '六煞': '西',  '五鬼': '西南', '绝命': '东北',
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

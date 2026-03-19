# -*- coding: utf-8 -*-
"""
居家风水方位计算器
集中实现财位、文昌位、桃花位、天医位等风水方位计算
数据来源：《八宅明镜》《阳宅三要》及传统风水经典
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 天干与出生年尾数的对应
# ---------------------------------------------------------------------------
HEAVENLY_STEM_BY_LAST_DIGIT = {
    4: '甲', 5: '乙', 6: '丙', 7: '丁', 8: '戊',
    9: '己', 0: '庚', 1: '辛', 2: '壬', 3: '癸',
}

# ---------------------------------------------------------------------------
# 地支（生肖）与出生年的对应
# ---------------------------------------------------------------------------
EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
ZODIAC_NAMES = {
    '子': '鼠', '丑': '牛', '寅': '虎', '卯': '兔', '辰': '龙', '巳': '蛇',
    '午': '马', '未': '羊', '申': '猴', '酉': '鸡', '戌': '狗', '亥': '猪',
}

# ---------------------------------------------------------------------------
# 本命文昌方位对照表（天干 → 文昌方位）
# ---------------------------------------------------------------------------
WENZHANG_BY_STEM = {
    '甲': '东南', '乙': '正南', '丙': '西南', '丁': '正西',
    '戊': '西南', '己': '正西', '庚': '西北', '辛': '正北',
    '壬': '东北', '癸': '正东',
}

# ---------------------------------------------------------------------------
# 生肖桃花方位对照表（地支 → 桃花方位）
# ---------------------------------------------------------------------------
PEACH_BLOSSOM_BY_BRANCH = {
    '子': '正西', '丑': '正南', '寅': '正东', '卯': '正北',
    '辰': '正西', '巳': '正南', '午': '正东', '未': '正北',
    '申': '正西', '酉': '正南', '戌': '正东', '亥': '正北',
}

# ---------------------------------------------------------------------------
# 流年桃花位（九紫星年度方位）
# 九紫右弼星按洛书飞星轨迹逆飞，9年一循环
# ---------------------------------------------------------------------------
_NINE_PURPLE_BASE_YEAR = 2023
_NINE_PURPLE_BASE_POSITIONS = [
    '正东',   # 2023
    '东南',   # 2024
    '中宫',   # 2025
    '西北',   # 2026
    '正西',   # 2027
    '东北',   # 2028
    '正南',   # 2029
    '正北',   # 2030
    '西南',   # 2031 (cycle repeats)
]

# ---------------------------------------------------------------------------
# 明财位对照表（大门朝向 → 明财位方位）
# 明财位 = 大门对角线位置
# ---------------------------------------------------------------------------
BRIGHT_WEALTH_BY_DOOR = {
    '南':   ['东北', '西北'],
    '北':   ['东南', '西南'],
    '东':   ['西南', '西北'],
    '西':   ['东南', '东北'],
    '东南': ['西北'],
    '西北': ['东南'],
    '东北': ['西南'],
    '西南': ['东北'],
}


def get_heavenly_stem(birth_year: int) -> str:
    """根据出生年份获取天干"""
    last_digit = birth_year % 10
    return HEAVENLY_STEM_BY_LAST_DIGIT.get(last_digit, '')


def get_earthly_branch(birth_year: int) -> str:
    """根据出生年份获取地支"""
    idx = (birth_year - 4) % 12
    return EARTHLY_BRANCHES[idx]


def get_zodiac(birth_year: int) -> str:
    """根据出生年份获取生肖"""
    branch = get_earthly_branch(birth_year)
    return ZODIAC_NAMES.get(branch, '')


# ===== 财位计算 =====

def calc_bright_wealth_position(door_direction: str) -> Dict:
    """
    计算明财位（大门对角线位置）

    Args:
        door_direction: 大门朝向

    Returns:
        {'positions': ['东北', '西北'], 'description': '...'}
    """
    positions = BRIGHT_WEALTH_BY_DOOR.get(door_direction, [])
    if not positions:
        return {'positions': [], 'description': '无法确定明财位（需要大门朝向）'}

    pos_text = '和'.join(positions) if len(positions) > 1 else positions[0]
    return {
        'positions': positions,
        'description': f'明财位在{pos_text}方，为大门对角线位置',
    }


def calc_dark_wealth_position(door_direction: str) -> Dict:
    """
    计算暗财位（八宅生气位 + 天医位）

    Args:
        door_direction: 大门朝向

    Returns:
        {'shengqi': '东南', 'tianyi': '东', 'description': '...'}
    """
    try:
        from mingua_calculator import get_house_directions
    except ImportError:
        from services.home_fengshui.mingua_calculator import get_house_directions

    dirs = get_house_directions(door_direction)
    if not dirs:
        return {'shengqi': '', 'tianyi': '', 'description': '无法确定暗财位（需要大门朝向）'}

    shengqi = dirs.get('生气', '')
    tianyi = dirs.get('天医', '')
    return {
        'shengqi': shengqi,
        'tianyi': tianyi,
        'primary': shengqi,
        'description': f'暗财位主位在{shengqi}方（生气位），辅位在{tianyi}方（天医位）',
    }


def calc_wealth_position(door_direction: str) -> Dict:
    """
    综合财位分析（明财位 + 暗财位）
    """
    bright = calc_bright_wealth_position(door_direction)
    dark = calc_dark_wealth_position(door_direction)

    overlap = set(bright.get('positions', [])) & {dark.get('shengqi', ''), dark.get('tianyi', '')}
    overlap = [d for d in overlap if d]

    return {
        'bright': bright,
        'dark': dark,
        'overlap': list(overlap),
        'has_overlap': len(overlap) > 0,
        'overlap_description': f'明暗财位在{overlap[0]}方重合，为最佳财位格局' if overlap else '',
    }


# ===== 文昌位计算 =====

def calc_personal_wenzhang(birth_year: int) -> Dict:
    """
    计算本命文昌位（根据出生年天干）

    Args:
        birth_year: 出生年份

    Returns:
        {'direction': '东南', 'stem': '甲', 'description': '...'}
    """
    stem = get_heavenly_stem(birth_year)
    direction = WENZHANG_BY_STEM.get(stem, '')
    return {
        'direction': direction,
        'stem': stem,
        'description': f'本命文昌在{direction}方（天干{stem}年）' if direction else '',
    }


def calc_house_wenzhang(door_direction: str) -> Dict:
    """
    计算宅文昌位（根据住宅坐向）
    八宅中巽宫(东南)为文昌位的主要方位，但各宅有不同的文昌星落宫
    简化：以宅的天医位作为宅文昌参考（天医主文昌贵人）
    """
    try:
        from mingua_calculator import get_house_directions
    except ImportError:
        from services.home_fengshui.mingua_calculator import get_house_directions

    dirs = get_house_directions(door_direction)
    if not dirs:
        return {'direction': '', 'description': ''}

    tianyi = dirs.get('天医', '')
    return {
        'direction': tianyi,
        'description': f'宅文昌在{tianyi}方（天医位）' if tianyi else '',
    }


def calc_wenzhang_position(door_direction: str, birth_year: Optional[int] = None) -> Dict:
    """综合文昌位分析"""
    result = {
        'personal': calc_personal_wenzhang(birth_year) if birth_year else None,
        'house': calc_house_wenzhang(door_direction) if door_direction else None,
    }

    personal_dir = result.get('personal', {}).get('direction', '') if result['personal'] else ''
    house_dir = result.get('house', {}).get('direction', '') if result['house'] else ''

    if personal_dir and house_dir and personal_dir == house_dir:
        result['overlap'] = True
        result['overlap_description'] = f'本命文昌与宅文昌同在{personal_dir}方，文昌力量加倍，大利学业'
    else:
        result['overlap'] = False
        result['overlap_description'] = ''

    return result


# ===== 桃花位计算 =====

def calc_zodiac_peach_blossom(birth_year: int) -> Dict:
    """
    计算生肖桃花位

    Args:
        birth_year: 出生年份

    Returns:
        {'direction': '正西', 'zodiac': '鼠', 'branch': '子', 'description': '...'}
    """
    branch = get_earthly_branch(birth_year)
    zodiac = ZODIAC_NAMES.get(branch, '')
    direction = PEACH_BLOSSOM_BY_BRANCH.get(branch, '')
    return {
        'direction': direction,
        'zodiac': zodiac,
        'branch': branch,
        'description': f'生肖桃花在{direction}方（属{zodiac}，桃花在{branch}）' if direction else '',
    }


def calc_annual_peach_blossom(year: Optional[int] = None) -> Dict:
    """
    计算流年桃花位（九紫星年度方位）

    Args:
        year: 年份，默认当前年
    """
    if year is None:
        year = datetime.now().year

    idx = (year - _NINE_PURPLE_BASE_YEAR) % len(_NINE_PURPLE_BASE_POSITIONS)
    direction = _NINE_PURPLE_BASE_POSITIONS[idx]
    return {
        'direction': direction,
        'year': year,
        'description': f'{year}年流年桃花在{direction}方（九紫右弼星）',
    }


def calc_house_peach_blossom(door_direction: str) -> Dict:
    """
    计算住宅桃花位（八宅延年位）

    Args:
        door_direction: 大门朝向
    """
    try:
        from mingua_calculator import get_house_directions
    except ImportError:
        from services.home_fengshui.mingua_calculator import get_house_directions

    dirs = get_house_directions(door_direction)
    if not dirs:
        return {'direction': '', 'description': ''}

    yannian = dirs.get('延年', '')
    return {
        'direction': yannian,
        'description': f'住宅桃花在{yannian}方（延年位）' if yannian else '',
    }


def calc_peach_blossom_position(
    door_direction: str,
    birth_year: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict:
    """综合桃花位分析"""
    result = {
        'zodiac': calc_zodiac_peach_blossom(birth_year) if birth_year else None,
        'annual': calc_annual_peach_blossom(year),
        'house': calc_house_peach_blossom(door_direction) if door_direction else None,
    }

    all_dirs = []
    if result['zodiac']:
        all_dirs.append(result['zodiac'].get('direction', ''))
    all_dirs.append(result['annual'].get('direction', ''))
    if result['house']:
        all_dirs.append(result['house'].get('direction', ''))
    all_dirs = [d for d in all_dirs if d]

    from collections import Counter
    counter = Counter(all_dirs)
    overlaps = [d for d, c in counter.items() if c >= 2]

    result['overlap_directions'] = overlaps
    result['has_overlap'] = len(overlaps) > 0
    if overlaps:
        result['overlap_description'] = f'桃花位在{overlaps[0]}方重合（多重催旺），效果加倍'
    else:
        result['overlap_description'] = ''

    return result


# ===== 天医位计算 =====

def calc_tianyi_position(door_direction: str) -> Dict:
    """
    计算天医位（八宅天医方位）

    Args:
        door_direction: 大门朝向
    """
    try:
        from mingua_calculator import get_house_directions
    except ImportError:
        from services.home_fengshui.mingua_calculator import get_house_directions

    dirs = get_house_directions(door_direction)
    if not dirs:
        return {'direction': '', 'description': ''}

    tianyi = dirs.get('天医', '')
    return {
        'direction': tianyi,
        'description': f'天医位在{tianyi}方，主健康长寿、催贵人' if tianyi else '',
    }


# ===== 汇总接口 =====

def get_all_positions(
    door_direction: Optional[str] = None,
    birth_year: Optional[int] = None,
    gender: Optional[str] = None,
    year: Optional[int] = None,
) -> Dict:
    """
    汇总所有风水方位计算结果

    Args:
        door_direction: 大门朝向
        birth_year: 出生年份
        gender: 性别 ('male'/'female')
        year: 分析年份（默认当前年）

    Returns:
        包含所有方位分析的字典
    """
    result = {}

    if door_direction:
        result['wealth_position'] = calc_wealth_position(door_direction)
        result['tianyi_position'] = calc_tianyi_position(door_direction)

    result['wenzhang_position'] = calc_wenzhang_position(
        door_direction or '', birth_year
    )

    result['peach_blossom_position'] = calc_peach_blossom_position(
        door_direction or '', birth_year, year
    )

    if birth_year:
        result['birth_info'] = {
            'birth_year': birth_year,
            'heavenly_stem': get_heavenly_stem(birth_year),
            'earthly_branch': get_earthly_branch(birth_year),
            'zodiac': get_zodiac(birth_year),
        }

    return result

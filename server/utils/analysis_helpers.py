#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析接口公共辅助函数

从 career_wealth_analysis / children_study_analysis / general_review_analysis 等
提取的重复辅助函数，统一在此维护。
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from server.services.industry_service import IndustryService

logger = logging.getLogger(__name__)

# 五行对应方位
ELEMENT_DIRECTION = {
    "木": "东", "火": "南", "土": "中", "金": "西", "水": "北"
}

# --- 干支五行计算 ---
# 通过顶部 import 导入，确保评测脚本和流式接口使用相同的函数


def _calculate_ganzhi_elements(stem: str, branch: str) -> Dict[str, int]:
    """
    计算干支的五行分布
    
    Args:
        stem: 天干
        branch: 地支
        
    Returns:
        dict: 五行统计，如 {'木': 1, '火': 1, '土': 0, '金': 0, '水': 0}
    """
    elements = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    
    # 天干五行
    if stem and stem in STEM_ELEMENTS:
        element = STEM_ELEMENTS[stem]
        elements[element] = elements.get(element, 0) + 1
    
    # 地支五行
    if branch and branch in BRANCH_ELEMENTS:
        element = BRANCH_ELEMENTS[branch]
        elements[element] = elements.get(element, 0) + 1
    
    return elements

# --- 大运八字关系分析 ---

def analyze_dayun_bazi_relation(
    dayun: Dict[str, Any],
    bazi_elements: Dict[str, int]
) -> Optional[str]:
    """
    分析大运与原局的生克关系
    
    Args:
        dayun: 大运信息（包含 stem, branch）
        bazi_elements: 原局五行统计
        
    Returns:
        关系类型字符串，如"水土混战"、"水火交战"等，如果没有特殊关系返回None
    """
    # 1. 计算大运的五行
    dayun_stem = dayun.get('stem', '')
    dayun_branch = dayun.get('branch', '')
    dayun_elements = _calculate_ganzhi_elements(dayun_stem, dayun_branch)
    
    # 2. 判断是否存在"混战"或"交战"关系
    # 水土混战：大运土多 + 原局水多，或大运水多 + 原局土多
    if (dayun_elements.get('土', 0) >= 2 and bazi_elements.get('水', 0) >= 2) or \
       (dayun_elements.get('水', 0) >= 2 and bazi_elements.get('土', 0) >= 2):
        return '水土混战'
    
    # 水火交战：大运火多 + 原局水多，或大运水多 + 原局火多
    if (dayun_elements.get('火', 0) >= 2 and bazi_elements.get('水', 0) >= 2) or \
       (dayun_elements.get('水', 0) >= 2 and bazi_elements.get('火', 0) >= 2):
        return '水火交战'
    
    # 金木相战：大运金多 + 原局木多，或大运木多 + 原局金多
    if (dayun_elements.get('金', 0) >= 2 and bazi_elements.get('木', 0) >= 2) or \
       (dayun_elements.get('木', 0) >= 2 and bazi_elements.get('金', 0) >= 2):
        return '金木相战'
    
    # 木土相战：大运木多 + 原局土多，或大运土多 + 原局木多
    if (dayun_elements.get('木', 0) >= 2 and bazi_elements.get('土', 0) >= 2) or \
       (dayun_elements.get('土', 0) >= 2 and bazi_elements.get('木', 0) >= 2):
        return '木土相战'
    
    # 火金相战：大运火多 + 原局金多，或大运金多 + 原局火多
    if (dayun_elements.get('火', 0) >= 2 and bazi_elements.get('金', 0) >= 2) or \
       (dayun_elements.get('金', 0) >= 2 and bazi_elements.get('火', 0) >= 2):
        return '火金相战'
    
    return None

# --- 关键大运识别 ---

def identify_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    bazi_elements: Dict[str, int],
    current_age: int
) -> Dict[str, Any]:
    """
    识别现行运和关键节点大运
    
    Args:
        dayun_sequence: 大运序列
        bazi_elements: 原局五行统计
        current_age: 当前年龄
        
    Returns:
        {
            'current_dayun': {...},  # 现行运
            'key_dayuns': [...]       # 关键节点大运列表
        }
    """
    current_dayun = None
    key_dayuns = []
    
    # 1. 识别现行运（跳过"小运"）
    for dayun in dayun_sequence:
        step = dayun.get('step', '')
        if step == '小运':
            continue
        age_display = dayun.get('age_display', '')
        if age_display:
            try:
                parts = age_display.replace('岁', '').split('-')
                if len(parts) == 2:
                    start_age = int(parts[0])
                    end_age = int(parts[1])
                    if start_age <= current_age <= end_age:
                        current_dayun = dayun
                        break
            except Exception:
                pass
    
    # 如果没找到，使用第一个非"小运"的大运
    if not current_dayun and dayun_sequence:
        for dayun in dayun_sequence:
            step = dayun.get('step', '')
            if step != '小运':
                current_dayun = dayun
                break
    
    # 2. 识别关键节点大运（与原局有特殊生克关系，跳过"小运"）
    for dayun in dayun_sequence:
        step = dayun.get('step', '')
        if step == '小运':
            continue
        relation_type = analyze_dayun_bazi_relation(dayun, bazi_elements)
        if relation_type:
            key_dayuns.append({
                **dayun,
                'relation_type': relation_type
            })
    
    return {
        'current_dayun': current_dayun,
        'key_dayuns': key_dayuns
    }

# --- 事业星提取 ---

def extract_career_star(ten_gods_stats: dict) -> dict:
    """
    提取事业星信息
    事业星：正官、七杀（官杀代表事业）；正印、偏印（代表贵人、学识）
    """
    result = {
        'primary': '',
        'secondary': '',
        'positions': [],
        'strength': '',
        'description': ''
    }
    
    # 统计官杀印星数量
    zhengguan = ten_gods_stats.get('正官', 0)
    qisha = ten_gods_stats.get('七杀', 0)
    zhengyin = ten_gods_stats.get('正印', 0)
    pianyin = ten_gods_stats.get('偏印', 0)
    
    # 确定主要事业星
    if zhengguan > 0 or qisha > 0:
        if zhengguan >= qisha:
            result['primary'] = '正官'
            if qisha > 0:
                result['secondary'] = '七杀'
        else:
            result['primary'] = '七杀'
            if zhengguan > 0:
                result['secondary'] = '正官'
    elif zhengyin > 0 or pianyin > 0:
        if zhengyin >= pianyin:
            result['primary'] = '正印'
        else:
            result['primary'] = '偏印'
    
    return result

# --- 财富星提取 ---

def extract_wealth_star(ten_gods_stats: dict) -> dict:
    """
    提取财富星信息
    财富星：正财、偏财
    """
    result = {
        'primary': '',
        'positions': [],
        'strength': '',
        'description': ''
    }
    
    zhengcai = ten_gods_stats.get('正财', 0)
    piancai = ten_gods_stats.get('偏财', 0)
    
    if zhengcai > 0 or piancai > 0:
        if zhengcai >= piancai:
            result['primary'] = '正财'
        else:
            result['primary'] = '偏财'
    
    return result

# --- 食伤生财检查 ---

def check_shishang_shengcai(ten_gods_stats: dict, ten_gods_data: dict) -> dict:
    """
    检查食伤生财组合
    """
    result = {
        'has_combination': False,
        'shishen_positions': [],
        'shangguan_positions': [],
        'combination_type': '',
        'analysis': ''
    }
    
    shishen = ten_gods_stats.get('食神', 0)
    shangguan = ten_gods_stats.get('伤官', 0)
    zhengcai = ten_gods_stats.get('正财', 0)
    piancai = ten_gods_stats.get('偏财', 0)
    
    has_shishang = shishen > 0 or shangguan > 0
    has_cai = zhengcai > 0 or piancai > 0
    
    if has_shishang and has_cai:
        result['has_combination'] = True
        if shishen > 0 and shangguan > 0:
            result['combination_type'] = '食伤生财'
        elif shishen > 0:
            result['combination_type'] = '食神生财'
        else:
            result['combination_type'] = '伤官生财'
        result['analysis'] = '命局有食伤生财组合，利于才华变现、创业创收'
    
    return result

# --- 年龄计算 ---

def calculate_age(birth_date: str) -> int:
    """计算当前年龄"""
    try:
        birth = datetime.strptime(birth_date, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth.year
        if today.month < birth.month or (today.month == birth.month and today.day < birth.day):
            age -= 1
        return max(0, age)
    except Exception:
        return 0

# --- 方位推导 ---

def get_directions_from_elements(xi_elements: List[str], ji_elements: List[str]) -> dict:
    """根据喜忌五行获取方位建议"""
    result = {
        'best_directions': [],
        'avoid_directions': [],
        'analysis': ''
    }
    
    for element in xi_elements:
        direction = ELEMENT_DIRECTION.get(element)
        if direction and direction not in result['best_directions']:
            result['best_directions'].append(direction)
    
    for element in ji_elements:
        direction = ELEMENT_DIRECTION.get(element)
        if direction and direction not in result['avoid_directions']:
            result['avoid_directions'].append(direction)
    
    return result

# --- 行业推导 ---

def get_industries_from_elements(xi_elements: List[str], ji_elements: List[str]) -> dict:
    """
    根据喜忌五行获取行业建议（从数据库读取）
    
    Args:
        xi_elements: 喜神五行列表，如 ['金', '土']
        ji_elements: 忌神五行列表，如 ['木', '火']
    
    Returns:
        dict: {
            'best_industries': [...],      # 适合的行业列表
            'secondary_industries': [],    # 次要行业（预留）
            'avoid_industries': [...],     # 需要避免的行业列表
            'analysis': ''                 # 分析说明（预留）
        }
    """
    # 使用 IndustryService 从数据库查询行业数据
    return IndustryService.get_industries_by_elements(xi_elements, ji_elements)



# --- 通用输入验证 ---

def validate_analysis_input(data: dict, required_fields: Dict[str, str]) -> tuple:
    """
    通用的分析接口输入数据验证。

    Args:
        data: 待验证的输入数据字典
        required_fields: {字段路径: 描述} 字典，如 {"basic_info.gender": "性别信息"}

    Returns:
        (is_valid, error_message)
    """
    missing = []
    for field_path, desc in required_fields.items():
        parts = field_path.split(".")
        obj = data
        found = True
        for part in parts:
            if isinstance(obj, dict) and part in obj and obj[part] is not None:
                obj = obj[part]
            else:
                found = False
                break
        if not found:
            missing.append(f"{desc}({field_path})")

    if missing:
        return False, f"缺少必要数据: {', '.join(missing)}"
    return True, ""


# --- 通用数据提取辅助 ---

def extract_wangshuai_data(result: dict) -> Optional[Dict[str, Any]]:
    """从编排器结果中提取旺衰数据"""
    wangshuai_result = result.get("wangshuai_result")
    if wangshuai_result:
        return wangshuai_result if isinstance(wangshuai_result, dict) else None
    return None


def extract_ten_gods_data(detail_result: Optional[dict], bazi_data: Optional[dict]) -> Optional[Dict[str, Any]]:
    """从详情结果或八字数据中提取十神数据"""
    if detail_result and isinstance(detail_result, dict):
        ten_gods = detail_result.get("ten_gods_stats")
        if ten_gods:
            return ten_gods
    if bazi_data and isinstance(bazi_data, dict):
        ten_gods = bazi_data.get("ten_gods_stats")
        if ten_gods:
            return ten_gods
    return None


def clean_liunian_data(liunian_list: list) -> list:
    """清理流年数据，移除多余的子级数据（流月/流日/流时）"""
    if not isinstance(liunian_list, list):
        return []
    cleaned = []
    for item in liunian_list:
        if isinstance(item, dict):
            item_copy = {k: v for k, v in item.items()
                        if k not in ("liuyue", "liuri", "liushi")}
            cleaned.append(item_copy)
        else:
            cleaned.append(item)
    return cleaned

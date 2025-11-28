#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 docs/追加.json 解析追加的婚姻规则，并批量写入 MySQL。
支持 --dry-run 仅打印解析结果而不写数据库。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 导入婚姻规则的解析函数
from scripts.import_marriage_rules import (
    CONDITION_HANDLERS,
    normalize_gender,
    build_conditions,
    load_pending_rule_ids,
    resolve_json_path,
    RULE_TYPE_MAP,
    PILLAR_NAMES,
    make_pillar_in,
    make_pillar_equals,
    make_pillar_relation,
    make_branches_count,
)

DEFAULT_JSON_PATH = os.path.join(PROJECT_ROOT, "docs", "追加.json")
DEFAULT_PENDING_PATH = os.path.join(PROJECT_ROOT, "docs", "zhuijia_rule_pending_confirmation.json")

RULE_CATEGORY_MAP = {
    "婚姻": "marriage",
}

RULE_CODE_PREFIX = "MARR"


@dataclass
class ParsedRule:
    rule: Dict[str, Any]
    row: Dict[str, Any]
    source: str
    sheet: str


@dataclass
class SkippedRule:
    rule_id: int
    reason: str
    source: str
    sheet: str
    rule_type: str = ""


def load_rows(json_path: str) -> List[Dict[str, Any]]:
    """从追加.json加载数据"""
    path = resolve_json_path(json_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到规则表: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    raw_rows: List[Dict[str, Any]] = []
    sheets = data.get("sheets", {})
    
    for sheet_name, sheet_data in sheets.items():
        rows = sheet_data.get("data", [])
        for row in rows:
            if not row or not isinstance(row, dict):
                continue
            record = dict(row)
            record["_source"] = os.path.basename(path)
            record["_sheet"] = sheet_name
            raw_rows.append(record)
    
    return raw_rows


def handle_ten_god_combined_with_caixing(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：正官被其它天干、地支合，需判断对应的财星是否与其他剩余天干/地支发生合"""
    # 匹配：正官被...合，需判断对应的财星是否...
    if "正官" in cond2 and "被" in cond2 and "合" in cond2 and "财星" in cond2:
        # 这是一个复杂的条件，需要检查：
        # 1. 正官被合（天干五合或地支六合）
        # 2. 对应的财星（女命对应正官的是正财）是否也被合
        # 由于这是女命规则，正官对应正财
        return [
            {
                "ten_god_combines": {
                    "god": "正官",
                    "source": "any",
                    "pillars": ["year", "month", "day", "hour"],
                    "target_pillars": ["year", "month", "day", "hour"],
                    "target_part": "any",
                    "relation": "any",  # 天干五合或地支六合
                }
            },
            {
                "ten_god_combines": {
                    "god": "正财",
                    "source": "any",
                    "pillars": ["year", "month", "day", "hour"],
                    "target_pillars": ["year", "month", "day", "hour"],
                    "target_part": "any",
                    "relation": "any",
                }
            }
        ], None
    return None, f"未实现的十神被合条件: {cond2}"


def handle_day_branch_chong(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：需要判断日支与年/月/时支是否构成六冲"""
    if "日支" in cond2 and "六冲" in cond2:
        # 日支与年/月/时支构成六冲
        return [
            {
                "any": [
                    make_pillar_relation("day", "year", "chong", part="branch"),
                    make_pillar_relation("day", "month", "chong", part="branch"),
                    make_pillar_relation("day", "hour", "chong", part="branch"),
                ]
            }
        ], None
    return None, f"未实现的日支六冲条件: {cond2}"


def handle_ten_god_order(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：主星或副星七杀在前，正官在后 / 主星或副星偏财在前，正财在后 / 男命主星或副星偏财在前，正财在后 / 主星和副星，出现顺序满足"七杀在前，正官在后"视为命中"""
    # 匹配多种格式
    patterns = [
        r'["'"'"'\"]([^\"'"'"'\"]+)在前，([^\"'"'"'\"]+)在后["'"'"'\"]',  # 优先匹配引号内的内容
        r'出现顺序满足["'"'"'\"]([^\"'"'"'\"]+)在前，([^\"'"'"'\"]+)在后["'"'"'\"]',
        r"(?:男命)?(?:主星或副星)?([^在]+)在前，([^在]+)在后",
        r"主星和副星[^，,]*([^在]+)在前，([^在]+)在后",
        r'([^在]+)在前，([^在]+)在后',  # 通用模式，放在最后
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cond2)
        if match:
            first_god = match.group(1).strip()
            second_god = match.group(2).strip()
            
            # 移除各种前缀
            first_god = re.sub(r"^(?:主星或副星|主星和副星|出现顺序满足|，)", "", first_god).strip()
            second_god = re.sub(r"^(?:主星或副星|主星和副星|出现顺序满足|，)", "", second_god).strip()
            
            # 移除引号（包括中文引号和英文引号）
            first_god = first_god.strip('"'"'"'"').strip('"').strip("'")
            second_god = second_god.strip('"'"'"'"').strip('"').strip("'")
            
            # 移除"视为命中"等后缀
            first_god = re.sub(r'视为命中.*$', '', first_god).strip()
            second_god = re.sub(r'视为命中.*$', '', second_god).strip()
            
            # 如果还有逗号或其他字符，只取第一个词
            if '，' in first_god or ',' in first_god:
                first_god = first_god.split('，')[0].split(',')[0].strip()
            if '，' in second_god or ',' in second_god:
                second_god = second_god.split('，')[0].split(',')[0].strip()
            
            # 如果提取的内容包含"在前"或"在后"，需要进一步提取
            if '在前' in first_god:
                first_god = first_god.split('在前')[0].strip()
            if '在后' in second_god:
                second_god = second_god.split('在后')[0].strip()
            
            # 如果还有引号或其他前缀，继续清理
            first_god = re.sub(r'^["'"'"'\"].*?["'"'"'\"](.*)', r'\1', first_god).strip()
            second_god = re.sub(r'^["'"'"'\"].*?["'"'"'\"](.*)', r'\1', second_god).strip()
            
            # 最后尝试：如果包含"七杀"、"正官"等十神名称，直接提取
            ten_god_names = ["七杀", "偏官", "正官", "偏财", "正财", "比肩", "劫财", "食神", "伤官", "偏印", "正印"]
            for tg in ten_god_names:
                if tg in first_god and first_god != tg:
                    # 提取十神名称
                    first_god = tg
                    break
            for tg in ten_god_names:
                if tg in second_god and second_god != tg:
                    # 提取十神名称
                    second_god = tg
                    break
            
            # 检查是否是十神名称
            if first_god in ten_god_names and second_god in ten_god_names:
                # 需要检查顺序：第一个十神在年/月柱，第二个十神在日/时柱
                return [
                    {
                        "ten_gods_total": {
                            "names": [first_god],
                            "pillars": ["year", "month"],
                            "min": 1
                        }
                    },
                    {
                        "ten_gods_total": {
                            "names": [second_god],
                            "pillars": ["day", "hour"],
                            "min": 1
                        }
                    }
                ], None
    
    return None, f"未实现的十神顺序条件: {cond2}"


def handle_branches_count_three_or_four(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：子、午、卯、酉占三字或四字者"""
    # 提取地支列表
    branches = [b.strip() for b in re.split(r"[、,，]", cond2) if b.strip() and b.strip() in "子丑寅卯辰巳午未申酉戌亥"]
    if branches and ("三字" in cond2 or "四字" in cond2 or "3" in cond2 or "4" in cond2):
        # 占三字或四字
        if "三字" in cond2 or "3" in cond2:
            return [make_branches_count(branches, min_val=3)], None
        elif "四字" in cond2 or "4" in cond2:
            return [make_branches_count(branches, min_val=4)], None
        else:
            # 三字或四字
            return [make_branches_count(branches, min_val=3)], None
    return None, f"未实现的地支计数条件: {cond2}"


def handle_day_stem_month_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：甲、己日干的人生在辰月 / 乙、庚日干的人生在寅月 / 丙、辛日干的人生在酉月或者戌月"""
    # 匹配：XXX、YYY日干的人生在ZZZ月（或WWW月）
    pattern = r"([^日]+)日干.*?生在([^月]+)月"
    match = re.search(pattern, cond2)
    if match:
        stems_str = match.group(1).strip()
        month_branches_str = match.group(2).strip()
        
        # 提取天干
        stems = [s.strip() for s in re.split(r"[、,，]", stems_str) if s.strip() and s.strip() in "甲乙丙丁戊己庚辛壬癸"]
        
        # 提取月份地支（可能包含"或"）
        month_branches = []
        if "或" in month_branches_str:
            parts = month_branches_str.split("或")
            for part in parts:
                part = part.strip()
                if part in "子丑寅卯辰巳午未申酉戌亥":
                    month_branches.append(part)
        else:
            if month_branches_str in "子丑寅卯辰巳午未申酉戌亥":
                month_branches.append(month_branches_str)
        
        if stems and month_branches:
            conditions = []
            # 日干在指定列表中
            conditions.append({
                "pillar_in": {
                    "pillar": "day",
                    "part": "stem",
                    "values": stems
                }
            })
            # 月支在指定列表中
            conditions.append({
                "pillar_in": {
                    "pillar": "month",
                    "part": "branch",
                    "values": month_branches
                }
            })
            return conditions, None
    
    return None, f"未实现的日干月支条件: {cond2}"


def handle_year_branch_month_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：年支子、午、卯、酉，且月支是寅"""
    # 匹配：年支XXX，且月支是YYY
    pattern = r"年支([^，,]+)，且月支是([^，,]+)"
    match = re.search(pattern, cond2)
    if match:
        year_branches_str = match.group(1).strip()
        month_branch = match.group(2).strip()
        
        year_branches = [b.strip() for b in re.split(r"[、,，]", year_branches_str) if b.strip() and b.strip() in "子丑寅卯辰巳午未申酉戌亥"]
        
        if year_branches and month_branch in "子丑寅卯辰巳午未申酉戌亥":
            return [
                make_pillar_in("year", "branch", year_branches),
                make_pillar_in("month", "branch", [month_branch])
            ], None
    
    return None, f"未实现的年支月支条件: {cond2}"


def handle_zodiac_month(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：属鼠的五月生 / 属牛的六月生 / 属马的十一生 等"""
    # 匹配：属XXX的YYY月生 / 属XXX的YYY生
    pattern = r"属([^的]+)的([^月生]+)(?:月)?生"
    match = re.search(pattern, cond2)
    if match:
        zodiac = match.group(1).strip()
        month_str = match.group(2).strip()
        
        # 生肖到地支的映射
        zodiac_to_branch = {
            "鼠": "子", "牛": "丑", "虎": "寅", "兔": "卯",
            "龙": "辰", "蛇": "巳", "马": "午", "羊": "未",
            "猴": "申", "鸡": "酉", "狗": "戌", "猪": "亥"
        }
        
        # 月份中文数字到数字的映射
        month_map = {
            "正": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12
        }
        
        year_branch = zodiac_to_branch.get(zodiac)
        month_num = month_map.get(month_str)
        
        if year_branch and month_num:
            return [
                make_pillar_in("year", "branch", [year_branch]),
                {
                    "lunar_month_in": {
                        "values": [month_num]
                    }
                }
            ], None
    
    return None, f"未实现的生肖月份条件: {cond2}"


def handle_liunian_chong_day_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：流年地支相冲日支"""
    if ("流年" in cond2 or "地支相冲" in cond2) and ("相冲" in cond2 or "冲" in cond2) and "日支" in cond2:
        return [
            {
                "liunian_relation": {
                    "target": "day",
                    "part": "branch",
                    "relation": "chong"
                }
            }
        ], None
    return None, f"未实现的流年相冲条件: {cond2}"


def handle_day_pillar_combines(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日柱与年月时任何一柱天干合地支合"""
    if "日柱" in cond2 and "天干合" in cond2 and "地支合" in cond2:
        return [
            {
                "any": [
                    {
                        "pillar_relation": {
                            "pillar_a": "day",
                            "pillar_b": "year",
                            "relation": "he",
                            "part": "stem"
                        }
                    },
                    {
                        "pillar_relation": {
                            "pillar_a": "day",
                            "pillar_b": "year",
                            "relation": "liuhe",
                            "part": "branch"
                        }
                    },
                    {
                        "pillar_relation": {
                            "pillar_a": "day",
                            "pillar_b": "month",
                            "relation": "he",
                            "part": "stem"
                        }
                    },
                    {
                        "pillar_relation": {
                            "pillar_a": "day",
                            "pillar_b": "month",
                            "relation": "liuhe",
                            "part": "branch"
                        }
                    },
                    {
                        "pillar_relation": {
                            "pillar_a": "day",
                            "pillar_b": "hour",
                            "relation": "he",
                            "part": "stem"
                        }
                    },
                    {
                        "pillar_relation": {
                            "pillar_a": "day",
                            "pillar_b": "hour",
                            "relation": "liuhe",
                            "part": "branch"
                        }
                    }
                ]
            }
        ], None
    return None, f"未实现的日柱合条件: {cond2}"


def handle_nayin_tianshuihe(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：原命盘四柱任何两柱或三柱有天河水"""
    if "天河水" in cond2:
        # 天河水纳音对应：丙午、丁未
        # 需要统计四柱中纳音为天河水的柱数
        # 判断是否有2柱或3柱（用户说"两柱即可"）
        
        # 提取数量要求
        min_count = 2  # 默认至少2柱
        if "三柱" in cond2 or "3柱" in cond2:
            # 如果明确说三柱，可以设置max为3，但用户说"两柱即可"，所以min=2即可
            pass
        
        # 天河水对应的日柱：丙午、丁未
        tianshuihe_pillars = ["丙午", "丁未"]
        
        # 构建条件：检查四柱中是否有至少2柱的纳音是天河水
        # 使用pillar_element条件检查每柱的纳音
        conditions = []
        for pillar in PILLAR_NAMES:
            conditions.append({
                "pillar_element": {
                    "pillar": pillar,
                    "part": "nayin",
                    "in": ["天河水"]
                }
            })
        
        # 需要至少2柱满足条件
        # 由于规则引擎支持any/all，我们需要使用一个自定义条件
        # 但更简单的方法是：检查是否有至少2个柱的纳音是天河水
        # 我们可以使用一个组合条件：any中包含多个pillar_element，然后统计满足的数量
        
        # 由于规则引擎可能不支持直接统计，我们可以使用一个变通方法：
        # 检查任意两柱的组合是否都是天河水
        # 但这样会有很多组合，不现实
        
        # 更好的方法：使用一个自定义条件类型 "nayin_count"
        # 或者使用现有的条件组合
        
        # 暂时使用一个简化的方法：检查是否有至少2柱的纳音是天河水
        # 通过any条件，只要任意2个柱满足即可
        # 但规则引擎可能不支持这种统计
        
        # 实际上，我们可以使用一个更直接的方法：
        # 检查四柱中是否有至少2柱的纳音是天河水
        # 这需要一个新的条件类型，或者使用现有的条件
        
        # 由于规则引擎的限制，我们使用一个变通方法：
        # 使用多个any条件，每个any包含2个pillar_element条件
        # 但这样会有C(4,2)=6种组合，太复杂
        
        # 使用自定义条件 "nayin_count_in_pillars" 统计纳音出现次数
        return [{
            "nayin_count_in_pillars": {
                "nayin_name": "天河水",
                "pillars": PILLAR_NAMES,
                "min": min_count
            }
        }], None
    
    return None, f"未实现的纳音条件: {cond2}"


def handle_stems_sequence(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：年干为甲，月干为乙，日干为丙，时干为丁，天干顺序依次为甲乙丙丁"""
    # 尝试多种模式
    patterns = [
        r"年干为([^，,]+)，月干为([^，,]+)，日干为([^，,]+)，时干为([^，,]+)",
        r"四柱(?:的)?天干(?:，)?(?:年月日时|年月日)?天干顺序依次为([^，,]+)[，,]([^，,]+)[，,]([^，,]+)[，,]?([^，,]+)?",
        r"四柱天干[，,](?:年月日时|年月日)?天干顺序依次([^，,]+)[，,]([^，,]+)[，,]([^，,]+)[，,]?([^，,]+)?",
        r"顺序依次为([^，,]+)[，,]([^，,]+)[，,]([^，,]+)[，,]?([^，,]+)?",
        r"顺序依次([^，,]+)[，,]([^，,]+)[，,]([^，,]+)[，,]?([^，,]+)?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cond2)
        if match:
            try:
                stems = []
                for i in range(1, 5):
                    try:
                        if match.group(i):
                            stems.append(match.group(i).strip())
                    except IndexError:
                        break
                
                if len(stems) >= 3:
                    conditions = []
                    if len(stems) >= 1:
                        conditions.append(make_pillar_equals("year", [stems[0]]))
                    if len(stems) >= 2:
                        conditions.append(make_pillar_equals("month", [stems[1]]))
                    if len(stems) >= 3:
                        conditions.append(make_pillar_equals("day", [stems[2]]))
                    if len(stems) >= 4:
                        conditions.append(make_pillar_equals("hour", [stems[3]]))
                    
                    if conditions:
                        return conditions, None
            except (ValueError, IndexError):
                continue
    
    # 如果正则表达式都失败，尝试直接提取天干字符
    valid_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    found_stems = []
    for stem in valid_stems:
        if stem in cond2:
            found_stems.append(stem)
    
    # 如果找到4个天干，按顺序匹配
    if len(found_stems) >= 3:
        conditions = []
        if len(found_stems) >= 1:
            conditions.append(make_pillar_equals("year", [found_stems[0]]))
        if len(found_stems) >= 2:
            conditions.append(make_pillar_equals("month", [found_stems[1]]))
        if len(found_stems) >= 3:
            conditions.append(make_pillar_equals("day", [found_stems[2]]))
        if len(found_stems) >= 4:
            conditions.append(make_pillar_equals("hour", [found_stems[3]]))
        
        if conditions:
            return conditions, None
    
    return None, f"未实现的天干顺序条件: {cond2}"


def handle_branches_repeat_or_sanhui(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：地支出现了三个相同的字或四个连续相同的字或出现三会局"""
    # 这个条件需要：
    # 1. 检查是否有三个相同的地支
    # 2. 检查是否出现三会局（寅卯辰、巳午未、申酉戌、亥子丑）
    # 使用自定义条件
    return [{
        "branches_repeat_or_sanhui": {
            "min_repeat": 3,  # 至少3个相同
            "check_sanhui": True  # 检查三会局
        }
    }], None


def handle_month_branch_xing_chong_ke_hai(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：月支（月令）遭受到刑、冲、克、害"""
    if "月支" in cond2 and ("刑" in cond2 or "冲" in cond2 or "克" in cond2 or "害" in cond2):
        # 月支与年/日/时支有刑、冲、克、害关系
        relations = []
        if "刑" in cond2:
            relations.append("xing")
        if "冲" in cond2:
            relations.append("chong")
        if "克" in cond2:
            relations.append("ke")  # 注意：可能需要检查五行相克
        if "害" in cond2:
            relations.append("hai")
        
        if relations:
            conditions = []
            for pillar in ["year", "day", "hour"]:
                for relation in relations:
                    conditions.append(make_pillar_relation("month", pillar, relation, part="branch"))
            return [{"any": conditions}], None
    
    return None, f"未实现的月支刑冲克害条件: {cond2}"


def handle_branches_chenxu_chouwei(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：辰、戍、丑、未中至少见两个重复相同的字"""
    if "辰" in cond2 and ("戍" in cond2 or "戌" in cond2) and "丑" in cond2 and "未" in cond2:
        branches = ["辰", "戌", "丑", "未"]
        return [make_branches_count(branches, min_val=2)], None
    return None, f"未实现的辰戌丑未条件: {cond2}"


def handle_lunar_birthday(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：农历生日是正月廿三生"""
    # 匹配：农历生日是XXX月YYY日生（支持"不管是否闰月"等前缀）
    # 尝试多种模式
    patterns = [
        r"农历生日是([^月]+)月([^日]+)日",
        r"农历生日是([^月]+)月([^日]+)",
        r"是([^月]+)月([^日]+)生",
        r"([^月]+)月([^日]+)生",
    ]
    
    match = None
    for pattern in patterns:
        match = re.search(pattern, cond2)
        if match:
            break
    if match:
        month_str = match.group(1).strip()
        day_str = match.group(2).strip()
        
        # 清理日期字符串，去掉"生"字
        day_str = day_str.replace("生", "").strip()
        
        # 月份映射
        month_map = {
            "正": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12
        }
        
        month_num = month_map.get(month_str)
        # 提取日期数字
        day_num = None
        
        # 先尝试直接提取数字
        day_match = re.search(r"(\d+)", day_str)
        if day_match:
            day_num = int(day_match.group(1))
        else:
            # 处理中文数字，特别是"廿三"这种情况
            # 廿 = 20, 三 = 3, 廿三 = 23
            if "廿" in day_str:
                # 提取"廿"后面的数字
                remaining = day_str.replace("廿", "").replace("十", "").strip()
                day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
                          "七": 7, "八": 8, "九": 9}
                if remaining in day_map:
                    day_num = 20 + day_map[remaining]
                elif remaining == "":
                    day_num = 20
            elif "卅" in day_str:
                # 卅 = 30
                remaining = day_str.replace("卅", "").strip()
                day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
                          "七": 7, "八": 8, "九": 9}
                if remaining in day_map:
                    day_num = 30 + day_map[remaining]
                elif remaining == "":
                    day_num = 30
            else:
                # 普通中文数字
                day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
                          "七": 7, "八": 8, "九": 9, "十": 10}
                day_num = day_map.get(day_str)
        
        if month_num and day_num:
            return [
                {
                    "lunar_month_in": {
                        "values": [month_num]
                    }
                },
                {
                    "lunar_day_in": {
                        "values": [day_num]
                    }
                }
            ], None
    
    return None, f"未实现的农历生日条件: {cond2}"


def handle_year_nayin_water_count(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：年柱的纳音五行是水，并且整个八字中水的五行三个以上"""
    if "年柱" in cond2 and "纳音" in cond2 and "水" in cond2:
        # 年柱纳音是水
        # 整个八字中水的五行三个以上（包括大运流年）
        return [
            {
                "pillar_element": {
                    "pillar": "year",
                    "part": "nayin",
                    "in": ["水"]
                }
            },
            {
                "element_total": {
                    "names": ["水"],
                    "min": 3
                }
            }
        ], None
    return None, f"未实现的年柱纳音水条件: {cond2}"


def handle_deities_simple(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理简单的神煞条件：驿马、孤辰、寡宿、两个羊刃、桃花"""
    # 处理单个神煞
    if cond2 == "驿马":
        return [{"deities_in_day": "驿马"}], None
    elif cond2 == "孤辰":
        return [{"deities_in_day": "孤辰"}], None
    elif cond2 == "寡宿":
        return [{"deities_in_day": "寡宿"}], None
    elif cond2 == "两个羊刃" or cond2 == "2个羊刃":
        # 需要检查羊刃的数量
        return [{"deities_count": {"name": "羊刃", "min": 2}}], None
    elif "桃花" in cond2:
        # 检查是否有桃花神煞
        return [{"deities_in_day": "桃花"}], None
    return None, f"未实现的神煞条件: {cond2}"


def handle_day_pillar_simple(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理简单的日柱条件：乙、亥、庚、子 或 乙亥、庚子"""
    # 检查是否是"神煞有XXX"的情况（如：神煞有桃花）
    if "神煞" in cond2 and "有" in cond2:
        # 提取神煞名称
        deity_match = re.search(r"神煞有(.+)", cond2)
        if deity_match:
            deity_name = deity_match.group(1).strip()
            # 使用deities_in_day条件
            return [{"deities_in_day": deity_name}], None
    
    # 提取日柱列表
    pillars = [p.strip() for p in re.split(r"[、,，]", cond2) if p.strip()]
    if not pillars:
        return None, f"未实现的日柱条件: {cond2}"
    
    # 检查是否是分开的天干地支（如：乙、亥、庚、子）
    # 如果是4个元素且都是单个字符，尝试组合成日柱
    if len(pillars) == 4:
        stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        branches = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
        
        # 检查前两个是否是单个天干和地支
        if (pillars[0] in stems and pillars[1] in branches and 
            pillars[2] in stems and pillars[3] in branches):
            # 组合成日柱：乙亥、庚子
            combined_pillars = [f"{pillars[0]}{pillars[1]}", f"{pillars[2]}{pillars[3]}"]
            return [make_pillar_equals("day", combined_pillars)], None
    
    # 否则直接使用原始列表
    return [make_pillar_equals("day", pillars)], None


# 扩展条件处理器
EXTENDED_CONDITION_HANDLERS = CONDITION_HANDLERS.copy()
EXTENDED_CONDITION_HANDLERS.update({
    "十神": lambda cond2, qty: handle_ten_god_combined_with_caixing(cond2, qty) if "正官被" in cond2 and "财星" in cond2
    else handle_ten_god_order(cond2, qty) if "在前" in cond2 and "在后" in cond2
    else CONDITION_HANDLERS.get("十神", lambda c, q: (None, f"未处理的十神条件: {c}"))(cond2, qty),
    "地支": lambda cond2, qty: handle_branches_count_three_or_four(cond2, qty) if "占" in cond2 and ("三字" in cond2 or "四字" in cond2)
    else CONDITION_HANDLERS.get("地支", lambda c, q: (None, f"未处理的地支条件: {c}"))(cond2, qty),
    "日干": handle_day_stem_month_branch,
    "年支": handle_year_branch_month_branch,
    "生肖": handle_zodiac_month,
    "神煞": handle_deities_simple,
    "流年": handle_liunian_chong_day_branch,
    "日柱": lambda cond2, qty: handle_day_pillar_combines(cond2, qty) if "天干合" in cond2 and "地支合" in cond2
    else handle_day_pillar_simple(cond2, qty) if re.match(r"^[^，,]+(?:[、,，][^，,]+)+$", cond2)
    else CONDITION_HANDLERS.get("日柱", lambda c, q: (None, f"未处理的日柱条件: {c}"))(cond2, qty),
    "纳音": handle_nayin_tianshuihe,
    "天干": handle_stems_sequence,
    "年柱月柱日柱时柱的天干地支": lambda cond2, qty: handle_branches_repeat_or_sanhui(cond2, qty) if "三个相同的字" in cond2 or "三会局" in cond2
    else handle_branches_chenxu_chouwei(cond2, qty) if "辰" in cond2 and "未" in cond2
    else (None, f"未处理的天干地支条件: {cond2}"),
    "月支": handle_month_branch_xing_chong_ke_hai,
    "农历生日": handle_lunar_birthday,
    "年柱": handle_year_nayin_water_count,
})


def build_zhuijia_conditions(row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """构建追加规则条件"""
    rule_id = int(row["ID"])
    cond1 = str(row.get("筛选条件1") or "").strip()
    cond2 = str(row.get("筛选条件2") or "").strip()
    qty_raw = row.get("数量")
    qty = str(qty_raw).strip() if qty_raw is not None and not (isinstance(qty_raw, float) and str(qty_raw) == "nan") else ""
    gender = normalize_gender(row.get("性别"))
    rule_type = str(row.get("类型", "")).strip()

    conds: List[Dict[str, Any]] = []
    if gender:
        conds.append({"gender": gender})

    if not cond1:
        return None, "缺少筛选条件1"

    if not cond2:
        return None, "缺少筛选条件2"

    # 特殊处理：日支六冲
    if cond1 == "十神" and "日支" in cond2 and "六冲" in cond2:
        extra_conditions, reason = handle_day_branch_chong(cond2, qty)
    # 特殊处理：日柱条件中的神煞（如：神煞有桃花）
    elif cond1 == "日柱" and "神煞" in cond2 and "有" in cond2:
        extra_conditions, reason = handle_day_pillar_simple(cond2, qty)
    else:
        # 使用扩展处理器
        try:
            handler = EXTENDED_CONDITION_HANDLERS.get(cond1)
            if handler:
                extra_conditions, reason = handler(cond2, qty)
            else:
                return None, f"暂未支持的筛选条件类型:{cond1}"
        except Exception as exc:
            return None, f"解析异常: {exc}"

    if extra_conditions is None:
        return None, reason or "无法解析条件"

    conds.extend(extra_conditions)
    conds = [c for c in conds if c]
    if not conds:
        return None, reason or "未生成任何条件"

    if len(conds) == 1:
        return conds[0], None
    return {"all": conds}, None


def import_rules(
    json_path: str,
    write_db: bool = True,
    append: bool = False,
    pending_path: Optional[str] = DEFAULT_PENDING_PATH,
) -> Tuple[List[ParsedRule], List[SkippedRule], List[SkippedRule], int, int]:
    """导入规则"""
    rows = load_rows(json_path)
    pending_ids = load_pending_rule_ids(pending_path)
    parsed: List[ParsedRule] = []
    skipped: List[SkippedRule] = []
    skipped_existing: List[SkippedRule] = []
    seen_codes: Set[str] = set()

    # 去重：相同ID只保留第一条
    seen_rule_ids: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        source = row.get("_source", "")
        sheet = row.get("_sheet", "")
        rule_type = row.get("类型", "").strip()
        raw_rule_id = str(row.get("ID", "")).strip()
        
        # 处理 NaN 值
        if raw_rule_id == "nan" or raw_rule_id == "":
            continue
        
        try:
            rule_id = int(float(raw_rule_id))  # 处理可能的浮点数
        except (TypeError, ValueError):
            continue
        
        # 如果已经见过这个ID，跳过（去重）
        if rule_id not in seen_rule_ids:
            seen_rule_ids[rule_id] = row
    
    # 处理去重后的规则
    for rule_id, row in seen_rule_ids.items():
        source = row.get("_source", "")
        sheet = row.get("_sheet", "")
        rule_type = row.get("类型", "").strip()

        if pending_ids and rule_id in pending_ids:
            skipped.append(SkippedRule(
                rule_id=rule_id,
                reason="待确认规则，暂不导入",
                source=source,
                sheet=sheet,
                rule_type=rule_type
            ))
            continue

        condition, reason = build_zhuijia_conditions(row)
        if not condition:
            skipped.append(SkippedRule(
                rule_id=rule_id,
                reason=reason or "未解析",
                source=source,
                sheet=sheet,
                rule_type=rule_type
            ))
            continue

        # 生成规则代码
        rule_code = f"{RULE_CODE_PREFIX}-{rule_id}"
        
        if rule_code in seen_codes:
            skipped.append(SkippedRule(
                rule_id=rule_id,
                reason="rule_code 重复（输入文件）",
                source=source,
                sheet=sheet,
                rule_type=rule_type
            ))
            continue
        seen_codes.add(rule_code)

        cond1 = (row.get("筛选条件1") or "").strip()
        rule_type_db = RULE_TYPE_MAP.get(cond1, f"{RULE_CATEGORY_MAP.get(rule_type, 'marriage')}_general")
        rule_category = RULE_CATEGORY_MAP.get(rule_type, "marriage")
        
        rule_dict = {
            "rule_code": rule_code,
            "rule_name": f"{rule_type}规则{rule_id}",
            "rule_type": rule_type_db,
            "rule_category": rule_category,
            "priority": 85,
            "conditions": condition,
            "content": {
                "type": "description",
                "text": (row.get("结果") or "").strip(),
            },
        }
        parsed.append(ParsedRule(rule=rule_dict, row=row, source=source, sheet=sheet))

    inserted_count = 0
    updated_count = 0

    if write_db and parsed:
        from server.config.mysql_config import get_mysql_connection  # noqa: E402

        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                existing_codes: Set[str] = set()
                if append:
                    # 查询所有相关前缀的规则
                    cur.execute("SELECT rule_code FROM bazi_rules WHERE rule_code LIKE %s", (f"{RULE_CODE_PREFIX}-%",))
                    existing_codes = {item["rule_code"] for item in cur.fetchall()}
                else:
                    # 只删除当前类型的规则
                    cur.execute("DELETE FROM bazi_rules WHERE rule_code LIKE %s", (f"{RULE_CODE_PREFIX}-%",))

                sql = (
                    "INSERT INTO bazi_rules "
                    "(rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                )

                values = []
                update_values = []
                for item in parsed:
                    rule = item.rule
                    code = rule["rule_code"]
                    if append and code in existing_codes:
                        update_values.append((
                            rule["rule_name"],
                            rule["rule_type"],
                            rule["rule_category"],
                            rule["priority"],
                            json.dumps(rule["conditions"], ensure_ascii=False),
                            json.dumps(rule["content"], ensure_ascii=False),
                            rule["content"]["text"],
                            True,
                            rule["rule_code"],
                        ))
                    else:
                        values.append((
                            rule["rule_code"],
                            rule["rule_name"],
                            rule["rule_type"],
                            rule["rule_category"],
                            rule["priority"],
                            json.dumps(rule["conditions"], ensure_ascii=False),
                            json.dumps(rule["content"], ensure_ascii=False),
                            rule["content"]["text"],
                            True,
                        ))

                if values:
                    cur.executemany(sql, values)
                    inserted_count = len(values)

                if update_values:
                    update_sql = """
                        UPDATE bazi_rules
                        SET rule_name = %s, rule_type = %s, rule_category = %s, priority = %s,
                            conditions = %s, content = %s, description = %s, enabled = %s
                        WHERE rule_code = %s
                    """
                    cur.executemany(update_sql, update_values)
                    updated_count = len(update_values)

                if values or update_values:
                    cur.execute("UPDATE rule_version SET rule_version = rule_version + 1, content_version = content_version + 1")
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    return parsed, skipped, skipped_existing, inserted_count, updated_count


def save_pending_rules(skipped: List[SkippedRule], output_path: str):
    """保存待确认规则到JSON文件"""
    pending_rules = []
    for item in skipped:
        pending_rules.append({
            "id": item.rule_id,
            "rule_type": item.rule_type,
            "sheet": item.sheet,
            "source": item.source,
            "reason": item.reason,
        })
    
    output = {
        "rules_requiring_confirmation": pending_rules,
        "total_count": len(pending_rules),
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"💾 待确认规则已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="导入追加规则到数据库")
    parser.add_argument("--dry-run", action="store_true", help="仅解析并打印结果，不写入数据库")
    parser.add_argument("--append", action="store_true", help="采用追加模式，不清空现有规则")
    parser.add_argument("--json-path", dest="json_path", default=DEFAULT_JSON_PATH,
                        help=f"指定要解析的 JSON 文件（默认 {DEFAULT_JSON_PATH}）")
    parser.add_argument("--pending-json", dest="pending_json", default=DEFAULT_PENDING_PATH,
                        help=f"待确认规则列表 JSON（默认 {DEFAULT_PENDING_PATH}）")
    args = parser.parse_args()

    parsed, skipped, skipped_existing, inserted, updated = import_rules(
        json_path=args.json_path,
        write_db=not args.dry_run,
        append=args.append,
        pending_path=args.pending_json,
    )

    print(f"✓ 可解析规则: {len(parsed)} 条, 待确认/跳过: {len(skipped)} 条, 已存在跳过: {len(skipped_existing)} 条")
    print(f"使用 JSON 文件: {args.json_path}")
    
    if not args.dry_run:
        if inserted > 0:
            print(f"数据库实际新增规则: {inserted} 条")
        if updated > 0:
            print(f"数据库实际更新规则: {updated} 条")

    if skipped:
        print(f"\n⚠ 需确认的规则：{len(skipped)} 条")
        # 按原因分组统计
        reason_count = {}
        for item in skipped:
            reason = item.reason
            if reason not in reason_count:
                reason_count[reason] = []
            reason_count[reason].append(item)
        
        for reason, items in reason_count.items():
            print(f"  - {reason}: {len(items)} 条")
            for item in items[:3]:  # 只显示前3个示例
                print(f"    ID {item.rule_id} ({item.rule_type})")
        
        # 保存到文件
        save_pending_rules(skipped, args.pending_json)

    if skipped_existing:
        print(f"\n⚠ 已存在的规则：{len(skipped_existing)} 条")

    if args.dry_run and parsed:
        print("\n示例规则预览（前5条）：")
        for item in parsed[:5]:
            print(json.dumps(item.rule, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 docs/cc确认.json 解析规则，并批量写入 MySQL。
如果规则已存在则更新，不存在则新增。
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
    resolve_json_path,
    RULE_TYPE_MAP,
    PILLAR_NAMES,
    make_pillar_in,
    make_pillar_equals,
    make_pillar_relation,
    make_branches_count,
    make_stems_count,
)

# 导入追加规则的扩展处理函数
from scripts.import_zhuijia_rules import (
    handle_day_pillar_combines,
    handle_nayin_tianshuihe,
    handle_stems_sequence,
    handle_branches_repeat_or_sanhui,
    handle_month_branch_xing_chong_ke_hai,
    handle_branches_chenxu_chouwei,
    handle_day_pillar_simple,
    handle_ten_god_order,
    handle_ten_god_combined_with_caixing,
    handle_day_branch_chong,
    handle_zodiac_month,
    handle_liunian_chong_day_branch,
    handle_deities_simple,
    handle_lunar_birthday,
    handle_year_nayin_water_count,
)
from scripts.handle_deities_huagai_liuhe_sanhe import handle_deities_huagai_liuhe_sanhe

DEFAULT_JSON_PATH = os.path.join(PROJECT_ROOT, "docs", "cc确认.json")

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
    """从cc确认.json加载数据"""
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


def handle_day_pillar_ten_god_deity(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日柱的主星或福星带神煞伤官"""
    # 匹配：日柱的主星或福星带神煞XXX
    pattern = r"日柱的(?:主星或)?(?:福星|副星)?带神煞(.+)"
    match = re.search(pattern, cond2)
    if match:
        deity_name = match.group(1).strip()
        # 使用deities_in_day条件
        return [{"deities_in_day": deity_name}], None
    return None, f"未实现的日柱神煞条件: {cond2}"


def handle_stems_specific_count(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：天干出现三个"戊"一个"丁" """
    # 匹配：天干出现N个"XXX" M个"YYY"（支持中文引号）
    # 方法1: 使用正则表达式提取
    patterns = [
        r'(\d+)(?:个)?["'"'"'"]([^"'"'"'"]+)["'"'"'"]',  # 中文引号
        r'(\d+)(?:个)?[""]([^""]+)[""]',  # 英文引号
    ]
    
    matches = []
    for pattern in patterns:
        matches = re.findall(pattern, cond2)
        if len(matches) >= 2:
            break
    
    # 方法2: 如果正则失败，直接提取数字和天干
    if len(matches) < 2:
        # 提取所有数字（包括中文数字）
        counts = re.findall(r'(\d+)(?:个)?', cond2)
        # 中文数字映射
        chinese_nums = {'三': '3', '一': '1', '二': '2', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10', '两': '2'}
        for cn, val in chinese_nums.items():
            if cn in cond2:
                counts.append(val)
        
        # 提取所有天干
        valid_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        found_stems = []
        for stem in valid_stems:
            if stem in cond2:
                found_stems.append(stem)
        
        # 组合数字和天干（按出现顺序）
        if len(counts) >= 2 and len(found_stems) >= 2:
            # 找到每个天干对应的数字
            stem_counts = {}
            for i, stem in enumerate(found_stems):
                if i < len(counts):
                    stem_counts[stem] = counts[i]
            
            matches = [(stem_counts.get(found_stems[0], '0'), found_stems[0]), 
                      (stem_counts.get(found_stems[1], '0'), found_stems[1])]
    
    if len(matches) >= 2:
        try:
            count1 = int(matches[0][0])
            stem1 = matches[0][1].strip()
            count2 = int(matches[1][0])
            stem2 = matches[1][1].strip()
            
            # 验证天干
            valid_stems = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
            if stem1 in valid_stems and stem2 in valid_stems:
                return [
                    make_stems_count([stem1], eq=count1),
                    make_stems_count([stem2], eq=count2),
                ], None
        except (ValueError, IndexError):
            pass
    
    return None, f"未实现的天干特定数量条件: {cond2}"


def handle_day_pillar_changsheng(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日柱的十二长生是沐浴 / 日支自坐十二长生的沐浴"""
    # 匹配：日柱的十二长生是XXX / 日支自坐十二长生的XXX
    patterns = [
        r"日柱的十二长生是(.+)",
        r"日支自坐十二长生的(.+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cond2)
        if match:
            changsheng = match.group(1).strip()
            # 使用自定义条件
            return [{
                "day_pillar_changsheng": changsheng
            }], None
    
    return None, f"未实现的十二长生条件: {cond2}"


def handle_ten_gods_main_count(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：主星十神同时出现了两个伤官"""
    # 匹配：主星十神同时出现了N个XXX（支持中文数字）
    patterns = [
        r"主星十神同时出现了(\d+)(?:个)?(.+)",
        r"主星十神同时出现了([^个]+)(?:个)?(.+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cond2)
        if match:
            try:
                count_str = match.group(1).strip()
                ten_god = match.group(2).strip()
                
                # 转换中文数字
                chinese_nums = {'两': 2, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '一': 1}
                if count_str in chinese_nums:
                    count = chinese_nums[count_str]
                else:
                    count = int(count_str)
                
                return [{
                    "ten_gods_main": {
                        "names": [ten_god],
                        "eq": count
                    }
                }], None
            except (ValueError, IndexError):
                continue
    
    return None, f"未实现的主星十神数量条件: {cond2}"


def handle_branches_double_repeat(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：地支中出现辰辰，戌戌，丑丑，未未任何两个字"""
    # 匹配：地支中出现XXX，YYY，ZZZ任何N个字
    if "辰辰" in cond2 or "戌戌" in cond2 or "丑丑" in cond2 or "未未" in cond2:
        # 提取重复的地支对
        branches = []
        if "辰辰" in cond2:
            branches.append("辰")
        if "戌戌" in cond2 or "戍戍" in cond2:
            branches.append("戌")
        if "丑丑" in cond2:
            branches.append("丑")
        if "未未" in cond2:
            branches.append("未")
        
        # 提取数量要求
        min_count = 2  # 默认至少2个
        if "两个" in cond2 or "2个" in cond2:
            min_count = 2
        
        if branches:
            return [make_branches_count(branches, min_val=min_count)], None
    
    return None, f"未实现的地支重复条件: {cond2}"


def handle_day_month_branch_liuhe(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日支和月支形成六合中的一组"""
    if "日支" in cond2 and "月支" in cond2 and "六合" in cond2:
        return [{
            "pillar_relation": {
                "pillar_a": "day",
                "pillar_b": "month",
                "relation": "liuhe",
                "part": "branch"
            }
        }], None
    return None, f"未实现的地支六合条件: {cond2}"


def handle_year_branch_yin_day_stem_yi(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：出生年支为阴，并且日干是乙"""
    if "年支为阴" in cond2 or ("年支" in cond2 and "阴" in cond2):
        # 阴支：丑、卯、巳、未、酉、亥
        yin_branches = ["丑", "卯", "巳", "未", "酉", "亥"]
        return [
            {
                "pillar_in": {
                    "pillar": "year",
                    "part": "branch",
                    "values": yin_branches
                }
            },
            {
                "pillar_in": {
                    "pillar": "day",
                    "part": "stem",
                    "values": ["乙"]
                }
            }
        ], None
    return None, f"未实现的年支阴日干乙条件: {cond2}"


def handle_stems_chong(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：天干出现四冲关系中的任何一组"""
    if "四冲" in cond2 or "天干" in cond2 and "冲" in cond2:
        # 天干四冲：甲庚、乙辛、丙壬、丁癸、戊己（但戊己不算冲，实际是甲庚、乙辛、丙壬、丁癸）
        # 使用any条件，检查是否有任何一组天干相冲
        return [{
            "stems_chong": True
        }], None
    return None, f"未实现的天干四冲条件: {cond2}"


def handle_month_day_branch_same_ten_gods(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：月支和日支是同一个字，并且月柱和日柱副星是'比肩'或'劫财'"""
    if "月支和日支是同一个字" in cond2 or ("月支" in cond2 and "日支" in cond2 and "同一个字" in cond2):
        # 提取十神
        ten_gods = []
        if "比肩" in cond2:
            ten_gods.append("比肩")
        if "劫财" in cond2:
            ten_gods.append("劫财")
        
        conditions = [{
            "pillar_equals": {
                "pillar_a": "month",
                "pillar_b": "day",
                "part": "branch"
            }
        }]
        
        if ten_gods:
            conditions.append({
                "any": [
                    {"ten_gods_sub": {"names": ten_gods, "pillars": ["month"], "min": 1}},
                    {"ten_gods_sub": {"names": ten_gods, "pillars": ["day"], "min": 1}}
                ]
            })
        
        return conditions, None
    return None, f"未实现的月支日支相同副星条件: {cond2}"


def handle_stems_wuhe_pairs(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：天干出现甲己、乙庚、丙辛、丁壬、戊癸任何两组不分顺序"""
    if "甲己" in cond2 or "乙庚" in cond2 or "丙辛" in cond2 or "丁壬" in cond2 or "戊癸" in cond2:
        # 天干五合：甲己、乙庚、丙辛、丁壬、戊癸
        # 提取数量要求
        min_pairs = 2
        if "两组" in cond2 or "2组" in cond2:
            min_pairs = 2
        elif "一组" in cond2 or "1组" in cond2:
            min_pairs = 1
        
        return [{
            "stems_wuhe_pairs": {
                "min_pairs": min_pairs
            }
        }], None
    return None, f"未实现的天干五合组条件: {cond2}"


def handle_day_branch_simple(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日支为XXX或YYY"""
    # 匹配：日支为亥或子 / 地支为辰，戌，丑，未中的一个
    patterns = [
        r"日支为([^，,或]+)(?:或|，|,)([^，,或]+)",
        r"地支为([^，,或]+)(?:，|,)([^，,或]+)(?:，|,)([^，,或]+)(?:，|,)?([^，,或]+)?(?:中的一个)?",
        r"地支为([^，,或]+)(?:或|，|,)([^，,或]+)",
    ]
    
    branches = []
    valid_branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    for pattern in patterns:
        try:
            match = re.search(pattern, cond2)
            if match:
                for i in range(1, 10):  # 增加范围
                    try:
                        group_val = match.group(i)
                        if group_val:
                            branch = group_val.strip()
                            if branch in valid_branches and branch not in branches:
                                branches.append(branch)
                    except IndexError:
                        break
                if branches:
                    break
        except Exception:
            continue
    
    # 如果正则表达式匹配失败，尝试直接提取地支
    if not branches:
        for branch in valid_branches:
            if branch in cond2 and branch not in branches:
                branches.append(branch)
    
    if branches:
        return [make_pillar_in("day", "branch", branches)], None
    
    return None, f"未实现的日支条件: {cond2}"


def handle_day_branch_main_star_deity(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日支主星是正财，并且日柱神煞有驿马"""
    if "日支主星" in cond2 and "日柱神煞" in cond2:
        # 提取主星
        main_star_match = re.search(r"主星是(.+)", cond2)
        main_star = main_star_match.group(1).strip() if main_star_match else None
        
        # 提取神煞
        deity_match = re.search(r"神煞有(.+)", cond2)
        deity = deity_match.group(1).strip() if deity_match else None
        
        conditions = []
        if main_star:
            conditions.append({
                "main_star_in_pillar": {
                    "pillar": "day",
                    "in": [main_star]
                }
            })
        if deity:
            conditions.append({
                "deities_in_day": deity
            })
        
        if conditions:
            return conditions, None
    
    return None, f"未实现的日支主星神煞条件: {cond2}"


def handle_hour_stem_main_star(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：时干主星是偏财/正官"""
    if "时干主星" in cond2:
        # 提取主星
        main_star_match = re.search(r"主星是(.+)", cond2)
        main_star = main_star_match.group(1).strip() if main_star_match else None
        
        if main_star:
            return [{
                "main_star_in_pillar": {
                    "pillar": "hour",
                    "in": [main_star]
                }
            }], None
    
    return None, f"未实现的时干主星条件: {cond2}"


def handle_day_stem_combines_others(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日干与其他三柱天干相合"""
    if "日干" in cond2 and "其他三柱天干相合" in cond2:
        return [{
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
                        "pillar_b": "month",
                        "relation": "he",
                        "part": "stem"
                    }
                },
                {
                    "pillar_relation": {
                        "pillar_a": "day",
                        "pillar_b": "hour",
                        "relation": "he",
                        "part": "stem"
                    }
                }
            ]
        }], None
    return None, f"未实现的日干相合条件: {cond2}"


def handle_year_stem_yang(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：在阳年，天干为甲、丙、戊、庚、壬年"""
    if "阳年" in cond2 or ("年" in cond2 and "甲" in cond2 and "丙" in cond2):
        yang_stems = ["甲", "丙", "戊", "庚", "壬"]
        return [make_pillar_in("year", "stem", yang_stems)], None
    return None, f"未实现的阳年条件: {cond2}"


def handle_nayin_water_branches(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：四柱的纳音是水的五行有3个或三个以上，同时地支又出现了"戌、亥、子"其中的两个字"""
    if "纳音是水的五行" in cond2 or ("纳音" in cond2 and "水" in cond2):
        # 纳音五行是水的纳音
        water_nayin = ["涧下水", "大溪水", "长流水", "天河水", "井泉水", "大海水"]
        branches = ["戌", "亥", "子"]
        
        return [
            {
                "nayin_count_in_pillars": {
                    "nayin_names": water_nayin,
                    "pillars": PILLAR_NAMES,
                    "min": 3
                }
            },
            make_branches_count(branches, min_val=2)
        ], None
    return None, f"未实现的纳音水地支条件: {cond2}"


def handle_day_branch_chong_by_year_hour(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日支被年支和时支同时产生刑、冲、害、绝关系中的一种"""
    if "日支被年支和时支同时" in cond2 or ("日支" in cond2 and "年支" in cond2 and "时支" in cond2):
        # 需要年支和时支都对日支有刑、冲、害、绝关系
        return [{
            "all": [
                {
                    "any": [
                        {"pillar_relation": {"pillar_a": "year", "pillar_b": "day", "relation": "xing", "part": "branch"}},
                        {"pillar_relation": {"pillar_a": "year", "pillar_b": "day", "relation": "chong", "part": "branch"}},
                        {"pillar_relation": {"pillar_a": "year", "pillar_b": "day", "relation": "hai", "part": "branch"}},
                    ]
                },
                {
                    "any": [
                        {"pillar_relation": {"pillar_a": "hour", "pillar_b": "day", "relation": "xing", "part": "branch"}},
                        {"pillar_relation": {"pillar_a": "hour", "pillar_b": "day", "relation": "chong", "part": "branch"}},
                        {"pillar_relation": {"pillar_a": "hour", "pillar_b": "day", "relation": "hai", "part": "branch"}},
                    ]
                }
            ]
        }], None
    return None, f"未实现的日支被年时支刑冲害条件: {cond2}"


def handle_branches_repeat_three_four(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：八字中出现三个或者四个重复的字"""
    if "三个或者四个重复的字" in cond2 or "三个或四个重复" in cond2:
        return [{
            "branches_repeat_or_sanhui": {
                "min_repeat": 3,
                "check_sanhui": False
            }
        }], None
    return None, f"未实现的地支重复条件: {cond2}"


def handle_month_pillar_deities_kongwang(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：月柱副星神煞是空亡 / 月柱神煞出现空亡"""
    if "月柱" in cond2 and ("空亡" in cond2 or "副星神煞是空亡" in cond2):
        return [{"deities_in_month": "空亡"}], None
    return None, f"未实现的月柱空亡条件: {cond2}"


def handle_day_pillar_main_star_hour_deity(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日柱是主星正印，时柱出现神煞华盖"""
    if "日柱是主星" in cond2 and "时柱" in cond2 and "神煞" in cond2:
        # 提取主星
        main_star_match = re.search(r"主星(.+)", cond2)
        main_star = main_star_match.group(1).strip() if main_star_match else None
        
        # 提取神煞
        deity_match = re.search(r"神煞(.+)", cond2)
        deity = deity_match.group(1).strip() if deity_match else None
        
        conditions = []
        if main_star:
            conditions.append({
                "main_star_in_pillar": {
                    "pillar": "day",
                    "in": [main_star]
                }
            })
        if deity:
            conditions.append({
                "deities_in_hour": deity
            })
        
        if conditions:
            return conditions, None
    
    return None, f"未实现的日柱主星时柱神煞条件: {cond2}"


def handle_dayun_branch_equals_day_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：大运地支，与日支（配偶宫）是同一个字时"""
    if "大运地支" in cond2 and "日支" in cond2 and ("同一个字" in cond2 or "相同" in cond2):
        return [{
            "dayun_branch_equals": {
                "target_pillar": "day",
                "target_part": "branch"
            }
        }], None
    return None, f"未实现的大运地支条件: {cond2}"


def handle_liunian_combines_month(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：流年的天干地支，与月柱天干地支形成天干合同时地支合时"""
    if "流年" in cond2 and "月柱" in cond2 and "天干合" in cond2 and "地支合" in cond2:
        return [{
            "liunian_combines_pillar": {
                "target_pillar": "month",
                "stem_relation": "he",
                "branch_relation": "liuhe"
            }
        }], None
    return None, f"未实现的流年相合条件: {cond2}"


def handle_liunian_ganzhi_equals(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：日干是甲，当遇到甲寅流年"""
    # 匹配：当遇到XXX流年
    pattern = r"当遇到(.+?)流年"
    match = re.search(pattern, cond2)
    if match:
        ganzhi = match.group(1).strip()
        if len(ganzhi) == 2:
            return [{
                "liunian_ganzhi_equals": ganzhi
            }], None
    return None, f"未实现的流年干支条件: {cond2}"


def handle_liunian_branch_in_stems_present(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：天干有壬和丁，不分前后，可间隔，遇到流年出现"巳"或"酉" """
    # 提取天干
    stems = []
    if "壬" in cond2:
        stems.append("壬")
    if "丁" in cond2:
        stems.append("丁")
    
    # 提取流年地支
    branch_match = re.search(r'流年出现["'"'"'"]([^"'"'"'"]+)["'"'"'"]', cond2)
    if not branch_match:
        # 尝试其他格式
        branch_match = re.search(r'流年出现(.+)', cond2)
    
    branches = []
    if branch_match:
        branch_str = branch_match.group(1).strip()
        # 提取地支
        for branch in ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]:
            if branch in branch_str:
                branches.append(branch)
    
    conditions = []
    if stems:
        conditions.append({
            "stems_count": {
                "names": stems,
                "min": len(stems)
            }
        })
    if branches:
        conditions.append({
            "liunian_branch_in": {
                "values": branches
            }
        })
    
    if conditions:
        return conditions, None
    
    return None, f"未实现的天干流年条件: {cond2}"


def handle_suiyun_binglin_kongwang(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：遇到'岁运并临'的年份，并且这个并临的干支正好是日柱的空亡之时"""
    if "岁运并临" in cond2 and "日柱的空亡" in cond2:
        return [{
            "suiyun_binglin_kongwang": {
                "target_pillar": "day"
            }
        }], None
    return None, f"未实现的岁运并临条件: {cond2}"


def handle_dayun_liunian_ten_gods(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：月柱副星是比肩、劫财或伤官，当大运或流年主星或副星再次遇到比肩、劫财或伤官时"""
    if "月柱副星" in cond2 and ("大运" in cond2 or "流年" in cond2) and "主星或副星" in cond2:
        # 提取十神
        ten_gods = []
        if "比肩" in cond2:
            ten_gods.append("比肩")
        if "劫财" in cond2:
            ten_gods.append("劫财")
        if "伤官" in cond2:
            ten_gods.append("伤官")
        
        if ten_gods:
            return [{
                "month_ten_gods_with_dayun_liunian": {
                    "ten_gods": ten_gods,
                    "check_dayun": "大运" in cond2,
                    "check_liunian": "流年" in cond2
                }
            }], None
    
    return None, f"未实现的大运流年十神条件: {cond2}"


# 扩展条件处理器
EXTENDED_CONDITION_HANDLERS = CONDITION_HANDLERS.copy()
EXTENDED_CONDITION_HANDLERS.update({
    "十神": lambda cond2, qty: handle_ten_god_combined_with_caixing(cond2, qty) if "正官被" in cond2 and "财星" in cond2
    else handle_ten_god_order(cond2, qty) if "在前" in cond2 and "在后" in cond2
    else CONDITION_HANDLERS.get("十神", lambda c, q: (None, f"未处理的十神条件: {c}"))(cond2, qty),
    "地支": lambda cond2, qty: handle_day_month_branch_liuhe(cond2, qty) if "日支" in cond2 and "月支" in cond2 and "六合" in cond2
    else handle_branches_double_repeat(cond2, qty) if "辰辰" in cond2 or "戌戌" in cond2
    else CONDITION_HANDLERS.get("地支", lambda c, q: (None, f"未处理的地支条件: {c}"))(cond2, qty),
    "日干": lambda cond2, qty: handle_liunian_ganzhi_equals(cond2, qty) if "流年" in cond2 and "当遇到" in cond2
    else handle_day_stem_combines_others(cond2, qty) if "其他三柱天干相合" in cond2
    else CONDITION_HANDLERS.get("日干", lambda c, q: (None, f"未处理的日干条件: {c}"))(cond2, qty),
    "年支": CONDITION_HANDLERS.get("年支", lambda c, q: (None, f"未处理的年支条件: {c}")),
    "生肖": handle_zodiac_month,
    "神煞": lambda cond2, qty: handle_deities_huagai_liuhe_sanhe(cond2, qty) if "华盖" in cond2 and ("六合" in cond2 or "三合" in cond2)
    else handle_deities_simple(cond2, qty),
    "流年": lambda cond2, qty: handle_liunian_combines_month(cond2, qty) if "月柱" in cond2 and "天干合" in cond2 and "地支合" in cond2
    else handle_liunian_chong_day_branch(cond2, qty),
    "大运": handle_dayun_branch_equals_day_branch,
    "年份": handle_suiyun_binglin_kongwang,
    "日柱": lambda cond2, qty: handle_day_pillar_combines(cond2, qty) if "天干合" in cond2 and "地支合" in cond2
    else handle_day_pillar_ten_god_deity(cond2, qty) if "主星" in cond2 and "神煞" in cond2
    else handle_day_pillar_simple(cond2, qty) if re.match(r"^[^，,]+(?:[、,，][^，,]+)+$", cond2) or "神煞" in cond2
    else CONDITION_HANDLERS.get("日柱", lambda c, q: (None, f"未处理的日柱条件: {c}"))(cond2, qty),
    "纳音": handle_nayin_tianshuihe,
    "天干": lambda cond2, qty: handle_stems_sequence(cond2, qty) if "顺序" in cond2 or ("年干" in cond2 and "月干" in cond2)
    else handle_stems_specific_count(cond2, qty) if "出现" in cond2 and ("\"" in cond2 or "'" in cond2 or "“" in cond2)
    else CONDITION_HANDLERS.get("天干", lambda c, q: (None, f"未处理的天干条件: {c}"))(cond2, qty),
    "年柱月柱日柱时柱的天干地支": lambda cond2, qty: handle_branches_repeat_or_sanhui(cond2, qty) if "三个相同的字" in cond2 or "三会局" in cond2
    else handle_branches_repeat_three_four(cond2, qty) if "三个或者四个重复" in cond2
    else handle_branches_double_repeat(cond2, qty) if "辰辰" in cond2 or "戌戌" in cond2
    else handle_branches_chenxu_chouwei(cond2, qty) if "辰" in cond2 and "未" in cond2
    else handle_day_pillar_main_star_hour_deity(cond2, qty) if "日柱是主星" in cond2 and "时柱" in cond2
    else (None, f"未处理的天干地支条件: {cond2}"),
    "月支": lambda cond2, qty: handle_dayun_liunian_ten_gods(cond2, qty) if "月柱副星" in cond2 and ("大运" in cond2 or "流年" in cond2)
    else handle_month_day_branch_same_ten_gods(cond2, qty) if "月支和日支是同一个字" in cond2
    else handle_month_pillar_deities_kongwang(cond2, qty) if "月柱" in cond2 and "空亡" in cond2
    else handle_month_branch_xing_chong_ke_hai(cond2, qty),
    "农历生日": lambda cond2, qty: handle_year_branch_yin_day_stem_yi(cond2, qty) if "年支为阴" in cond2 or ("年支" in cond2 and "阴" in cond2 and "日干是乙" in cond2)
    else handle_lunar_birthday(cond2, qty),
    "年柱": lambda cond2, qty: handle_year_stem_yang(cond2, qty) if "阳年" in cond2
    else handle_year_nayin_water_count(cond2, qty),
    "纳音": lambda cond2, qty: handle_nayin_water_branches(cond2, qty) if "纳音是水的五行" in cond2 or ("纳音" in cond2 and "水" in cond2 and "3个" in cond2)
    else handle_nayin_tianshuihe(cond2, qty),
    "日支": lambda cond2, qty: handle_day_branch_simple(cond2, qty) if "日支为" in cond2 or "地支为" in cond2
    else handle_day_branch_main_star_deity(cond2, qty) if "日支主星" in cond2 and "日柱神煞" in cond2
    else handle_day_branch_chong_by_year_hour(cond2, qty) if "日支被年支和时支" in cond2
    else CONDITION_HANDLERS.get("日支", lambda c, q: (None, f"未处理的日支条件: {c}"))(cond2, qty),
    "月柱": lambda cond2, qty: handle_month_pillar_deities_kongwang(cond2, qty) if "月柱" in cond2 and "空亡" in cond2
    else CONDITION_HANDLERS.get("月柱", lambda c, q: (None, f"未处理的月柱条件: {c}"))(cond2, qty),
    "时柱": handle_hour_stem_main_star,
    "月支 地支": lambda cond2, qty: handle_month_branch_xing_chong_ke_hai(cond2, qty) if "月支和日支" in cond2 and ("刑" in cond2 or "冲" in cond2 or "害" in cond2)
    else (None, f"未处理的月支地支条件: {cond2}"),
})


def build_cc_conditions(row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """构建cc确认规则条件"""
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

    # 特殊处理
    if cond1 == "十神" and "日支" in cond2 and "六冲" in cond2:
        extra_conditions, reason = handle_day_branch_chong(cond2, qty)
    elif cond1 == "十神" and "主星和副星" in cond2 and "顺序" in cond2:
        extra_conditions, reason = handle_ten_god_order(cond2, qty)
    elif cond1 == "日柱" and "神煞" in cond2 and "有" in cond2:
        extra_conditions, reason = handle_day_pillar_simple(cond2, qty)
    elif cond1 == "日柱" and "十二长生" in cond2:
        extra_conditions, reason = handle_day_pillar_changsheng(cond2, qty)
    elif cond1 == "天干" and "主星十神" in cond2:
        extra_conditions, reason = handle_ten_gods_main_count(cond2, qty)
    elif cond1 == "天干" and "四冲" in cond2:
        extra_conditions, reason = handle_stems_chong(cond2, qty)
    elif cond1 == "天干" and "流年出现" in cond2:
        extra_conditions, reason = handle_liunian_branch_in_stems_present(cond2, qty)
    elif cond1 == "日干" and "其他三柱天干相合" in cond2 and "十二长生的沐浴" in cond2:
        # 日干与其他三柱天干相合，并且日支自坐十二长生的沐浴
        conditions1, reason1 = handle_day_stem_combines_others(cond2, qty)
        conditions2, reason2 = handle_day_pillar_changsheng(cond2, qty)
        if conditions1 and conditions2:
            extra_conditions = conditions1 if isinstance(conditions1, list) else [conditions1]
            extra_conditions.extend(conditions2 if isinstance(conditions2, list) else [conditions2])
            reason = None
        else:
            extra_conditions, reason = None, reason1 or reason2
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
) -> Tuple[List[ParsedRule], List[SkippedRule], int, int]:
    """导入规则"""
    rows = load_rows(json_path)
    parsed: List[ParsedRule] = []
    skipped: List[SkippedRule] = []
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
            rule_id = int(float(raw_rule_id))
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

        condition, reason = build_cc_conditions(row)
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
                # 查询已存在的规则代码
                rule_codes = [item.rule["rule_code"] for item in parsed]
                placeholders = ",".join(["%s"] * len(rule_codes))
                cur.execute(f"SELECT rule_code FROM bazi_rules WHERE rule_code IN ({placeholders})", tuple(rule_codes))
                existing_codes = {item["rule_code"] for item in cur.fetchall()}

                # 准备插入和更新的数据
                insert_values = []
                update_values = []
                
                for item in parsed:
                    rule = item.rule
                    code = rule["rule_code"]
                    
                    if code in existing_codes:
                        # 更新
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
                        # 插入
                        insert_values.append((
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

                # 执行插入
                if insert_values:
                    insert_sql = (
                        "INSERT INTO bazi_rules "
                        "(rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    )
                    cur.executemany(insert_sql, insert_values)
                    inserted_count = len(insert_values)

                # 执行更新
                if update_values:
                    update_sql = """
                        UPDATE bazi_rules
                        SET rule_name = %s, rule_type = %s, rule_category = %s, priority = %s,
                            conditions = %s, content = %s, description = %s, enabled = %s
                        WHERE rule_code = %s
                    """
                    cur.executemany(update_sql, update_values)
                    updated_count = len(update_values)

                # 更新版本号
                if insert_values or update_values:
                    cur.execute("UPDATE rule_version SET rule_version = rule_version + 1, content_version = content_version + 1")
                
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    return parsed, skipped, inserted_count, updated_count


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
    parser = argparse.ArgumentParser(description="导入cc确认规则到数据库")
    parser.add_argument("--dry-run", action="store_true", help="仅解析并打印结果，不写入数据库")
    parser.add_argument("--json-path", dest="json_path", default=DEFAULT_JSON_PATH,
                        help=f"指定要解析的 JSON 文件（默认 {DEFAULT_JSON_PATH}）")
    parser.add_argument("--pending-json", dest="pending_json",
                        help="待确认规则列表 JSON（可选）")
    args = parser.parse_args()

    parsed, skipped, inserted, updated = import_rules(
        json_path=args.json_path,
        write_db=not args.dry_run,
    )

    print(f"✓ 可解析规则: {len(parsed)} 条, 待确认/跳过: {len(skipped)} 条")
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
        if args.pending_json:
            save_pending_rules(skipped, args.pending_json)

    if args.dry_run and parsed:
        print("\n示例规则预览（前5条）：")
        for item in parsed[:5]:
            print(json.dumps(item.rule, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


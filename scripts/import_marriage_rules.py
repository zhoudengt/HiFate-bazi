#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 docs/婚姻算法公式00.json 解析婚姻规则，并批量写入 MySQL。
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

DEFAULT_JSON_PATH = os.path.join(PROJECT_ROOT, "docs", "婚姻算法公式00.json")
DEFAULT_PENDING_PATH = os.path.join(PROJECT_ROOT, "docs", "rule_pending_confirmation.json")

RULE_TYPE_MAP = {
    "十神": "marriage_ten_gods",
    "五行": "marriage_element",
    "日干": "marriage_day_stem",
    "日支": "marriage_day_branch",
    "日柱": "marriage_day_pillar",
    "天干": "marriage_stem_pattern",
    "地支": "marriage_branch_pattern",
    "八字": "marriage_bazi_pattern",
    "神煞": "marriage_deity",
    "月支": "marriage_month_branch",
    "年支": "marriage_year_branch",
    "年干": "marriage_year_stem",
    "年柱": "marriage_year_pillar",
    "纳音": "marriage_nayin",
    "农历生日": "marriage_lunar_birthday",
    "时柱": "marriage_hour_pillar",
    "年份": "marriage_year_event",
    "大运": "marriage_luck_cycle",
}

STEMS = list("甲乙丙丁戊己庚辛壬癸")
BRANCHES = list("子丑寅卯辰巳午未申酉戌亥")
PILLAR_NAMES = ["year", "month", "day", "hour"]


@dataclass
class ParsedRule:
    rule: Dict[str, Any]
    row: Dict[str, Any]
    source: str


@dataclass
class SkippedRule:
    rule_id: int
    reason: str
    source: str


def normalize_gender(raw: Any) -> Optional[str]:
    if not raw:
        return None
    text = str(raw).strip()
    if text in {"男", "male", "男命", "男性"}:
        return "male"
    if text in {"女", "female", "女命", "女性"}:
        return "female"
    return None


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def split_values(text: str) -> List[str]:
    if not text:
        return []
    return [item.strip() for item in re.split(r"[、,，/\s]+", text) if item.strip()]


def make_pillar_in(pillar: str, part: str, values: List[str]) -> Dict[str, Any]:
    return {
        "pillar_in": {
            "pillar": pillar,
            "part": part,
            "values": values,
        }
    }


def make_pillar_equals(pillar: str, values: List[str]) -> Dict[str, Any]:
    return {
        "pillar_equals": {
            "pillar": pillar,
            "values": values,
        }
    }


def make_stems_count(names: List[str], *, eq: Optional[int] = None, min_val: Optional[int] = None,
                     max_val: Optional[int] = None) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"names": names}
    if eq is not None:
        spec["eq"] = eq
    if min_val is not None:
        spec["min"] = min_val
    if max_val is not None:
        spec["max"] = max_val
    return {"stems_count": spec}


def make_stems_repeat(*, eq: Optional[int] = None, min_val: Optional[int] = None,
                      max_val: Optional[int] = None) -> Dict[str, Any]:
    spec: Dict[str, Any] = {}
    if eq is not None:
        spec["any_eq"] = eq
    if min_val is not None:
        spec["any_min"] = min_val
    if max_val is not None:
        spec["any_max"] = max_val
    return {"stems_count": spec}


def make_branches_count(names: List[str], *, eq: Optional[int] = None, min_val: Optional[int] = None,
                        max_val: Optional[int] = None) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"names": names}
    if eq is not None:
        spec["eq"] = eq
    if min_val is not None:
        spec["min"] = min_val
    if max_val is not None:
        spec["max"] = max_val
    return {"branches_count": spec}


def make_branches_repeat(*, eq: Optional[int] = None, min_val: Optional[int] = None,
                         max_val: Optional[int] = None) -> Dict[str, Any]:
    spec: Dict[str, Any] = {}
    if eq is not None:
        spec["any_eq"] = eq
    if min_val is not None:
        spec["any_min"] = min_val
    if max_val is not None:
        spec["any_max"] = max_val
    return {"branches_count": spec}


def make_pillar_relation(pillar_a: str, pillar_b: str, relation: str, *, part: str = "branch") -> Dict[str, Any]:
    return {
        "pillar_relation": {
            "pillar_a": pillar_a,
            "pillar_b": pillar_b,
            "relation": relation,
            "part": part,
        }
    }


def parse_quantity_spec(qty: str) -> Dict[str, int]:
    if not qty:
        return {}
    qty = qty.strip()
    converted = qty
    for han, digit in [("两", "2"), ("一", "1"), ("二", "2"), ("三", "3"), ("四", "4"),
                       ("五", "5"), ("六", "6"), ("七", "7"), ("八", "8"), ("九", "9"), ("十", "10")]:
        converted = converted.replace(han, digit)
    numbers = re.findall(r"\d+", converted)
    if not numbers:
        return {}
    values = [int(n) for n in numbers]
    spec: Dict[str, int] = {}
    primary = values[0]
    if any(token in qty for token in ("以上", "不少于", "至少", "及以上", "或更多")):
        spec["min"] = primary
    elif "只有" in qty or "仅" in qty or "只" in qty:
        spec["eq"] = primary
    elif "或" in qty and len(values) >= 2:
        spec["min"] = min(values)
    else:
        spec["eq"] = primary
    return spec


CHINESE_NUMBER_MAP = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def parse_chinese_numeral(text: str) -> Optional[int]:
    if not text:
        return None
    clean = re.sub(r"[^零〇一二三四五六七八九十两\d]", "", text)
    if not clean:
        return None

    digits = re.findall(r"\d+", clean)
    if digits:
        return int(digits[0])

    if clean in CHINESE_NUMBER_MAP:
        return CHINESE_NUMBER_MAP[clean]

    if "十" in clean:
        parts = clean.split("十")
        if parts[0] == "":
            high = 1
        else:
            high = CHINESE_NUMBER_MAP.get(parts[0], 0)
        if parts[-1] == "":
            low = 0
        else:
            low = CHINESE_NUMBER_MAP.get(parts[-1], 0)
        return high * 10 + low

    total = 0
    for ch in clean:
        total = total * 10 + CHINESE_NUMBER_MAP.get(ch, 0)
    return total if total > 0 else None


def make_any_pillar_equals(value: str) -> Dict[str, Any]:
    """生成条件：任意一柱等于指定干支"""
    return {
        "any": [
            make_pillar_equals(pillar, [value])
            for pillar in PILLAR_NAMES
        ]
    }


def resolve_json_path(path: str) -> str:
    if not path:
        return DEFAULT_JSON_PATH
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return expanded
    return os.path.join(PROJECT_ROOT, expanded)


def load_rows(json_paths: List[str]) -> List[Dict[str, Any]]:
    if not json_paths:
        json_paths = [DEFAULT_JSON_PATH]

    raw_rows: List[Dict[str, Any]] = []
    for raw_path in json_paths:
        path = resolve_json_path(raw_path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"未找到规则表: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for sheet_name, sheet_rows in data.items():
            if not isinstance(sheet_rows, list):
                continue
            for row in sheet_rows:
                if not row or not isinstance(row, dict):
                    continue
                record = dict(row)
                record["_source"] = os.path.basename(path)
                record["_sheet"] = sheet_name
                raw_rows.append(record)

    # 规则去重：以 ID 优先，其次以 rule_code（或“编号”）去重。
    # 后出现的记录会覆盖同 ID/编号的旧记录，因此在 json_paths 中后面的文件具有更高优先级。
    from collections import OrderedDict

    deduped: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    index_by_id: Dict[str, str] = {}
    index_by_code: Dict[str, str] = {}

    def get_rule_id(record: Dict[str, Any]) -> Optional[str]:
        value = record.get("ID")
        if value is None or value == "":
            return None
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value).strip() or None

    def get_rule_code(record: Dict[str, Any]) -> Optional[str]:
        for key in ("rule_code", "规则编号", "编号", "RuleCode", "ruleCode"):
            value = record.get(key)
            if value:
                return str(value).strip()
        return None

    for record in raw_rows:
        rule_id = get_rule_id(record)
        rule_code = get_rule_code(record)

        dedup_key: Optional[str] = None
        if rule_id and rule_id in index_by_id:
            dedup_key = index_by_id[rule_id]
        elif rule_code and rule_code in index_by_code:
            dedup_key = index_by_code[rule_code]
        else:
            dedup_key = f"row_{len(deduped)}"

        deduped[dedup_key] = record
        if rule_id:
            index_by_id[rule_id] = dedup_key
        if rule_code:
            index_by_code[rule_code] = dedup_key

    return list(deduped.values())


def load_pending_rule_ids(pending_path: Optional[str]) -> Set[int]:
    """
    读取待确认规则列表，返回 ID 集合
    """
    if not pending_path:
        return set()

    path = resolve_json_path(pending_path)
    if not os.path.exists(path):
        return set()  # 文件不存在时返回空集合，不抛出异常

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 支持两种格式：dict格式（rules_requiring_confirmation）和list格式（直接是规则列表）
    if isinstance(data, dict):
        rules = data.get("rules_requiring_confirmation")
    elif isinstance(data, list):
        rules = data
    else:
        return set()
    
    if not rules:
        return set()

    pending_ids: Set[int] = set()
    for item in rules:
        try:
            pending_ids.add(int(item["id"]))
        except (TypeError, ValueError, KeyError):
            continue
    return pending_ids


def build_conditions(row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    rule_id = int(row["ID"])
    cond1 = (row.get("筛选条件1") or "").strip()
    cond2 = (row.get("筛选条件2") or "").strip()
    qty = (row.get("数量") or "").strip()
    gender = normalize_gender(row.get("性别"))

    conds: List[Dict[str, Any]] = []
    if gender:
        conds.append({"gender": gender})

    if not cond1:
        return None, "缺少筛选条件1"

    try:
        handler = CONDITION_HANDLERS.get(cond1)
        if handler:
            extra_conditions, reason = handler(cond2, qty)
        else:
            return None, f"暂未支持的筛选条件类型:{cond1}"
    except Exception as exc:  # 捕获任何解析异常
        return None, f"解析异常: {exc}"

    if extra_conditions is None:
        # handler 返回 None 表示无法处理
        return None, reason or "无法解析条件"

    conds.extend(extra_conditions)
    conds = [c for c in conds if c]
    if not conds:
        return None, reason or "未生成任何条件"

    if len(conds) == 1:
        return conds[0], None
    return {"all": conds}, None


def handle_element_total(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    cond2 = cond2.strip()
    pattern = re.compile(r"(?:有)?([零〇一二三四五六七八九十两\\d]+)(?:个)?字?属([木火土金水])")
    matches = list(pattern.finditer(cond2))
    if matches:
        conds: List[Dict[str, Any]] = []
        for match in matches:
            num_text = match.group(1)
            element = match.group(2)
            count = parse_chinese_numeral(num_text)
            if count is None:
                return None, f"无法解析五行数量: {num_text}"
            conds.append({"element_total": {"names": [element], "eq": count}})
        return conds, None

    names = split_values(cond2.replace("或", "、"))
    if not names:
        return None, "缺少五行名称"
    spec = {"names": names}
    spec.update(parse_quantity_spec(qty))
    return [{"element_total": spec}], None


TEN_GOD_NAMES: List[str] = [
    "正财",
    "偏财",
    "正官",
    "偏官",
    "七杀",
    "正印",
    "偏印",
    "劫财",
    "比肩",
    "食神",
    "伤官",
]


def _extract_ten_god_names(text: str) -> List[str]:
    return [name for name in TEN_GOD_NAMES if name in text]


def _parse_ten_god_count_spec(text: str) -> Optional[Dict[str, Any]]:
    """解析带数量要求的十神描述，返回 ten_gods_total 结构。"""
    normalized = re.sub(r"[（）()]", "", text)
    for name in TEN_GOD_NAMES:
        if name not in normalized:
            continue
        tail = normalized.split(name, 1)[1]
        spec: Dict[str, Any] = {"names": [name]}
        if any(token in tail for token in ("只有一个", "只有1个", "只剩一个", "只有一個")):
            spec["eq"] = 1
            return {"ten_gods_total": spec}
        if any(token in tail for token in ("只有两个", "只有2个", "恰好两个", "恰好2个")):
            spec["eq"] = 2
            return {"ten_gods_total": spec}
        if match := re.search(r"(\d+)个以上", tail):
            spec["min"] = int(match.group(1))
            return {"ten_gods_total": spec}
        if match := re.search(r"不少于(\d+)个", tail):
            spec["min"] = int(match.group(1))
            return {"ten_gods_total": spec}
        if match := re.search(r"至少(\d+)个", tail):
            spec["min"] = int(match.group(1))
            return {"ten_gods_total": spec}
        if match := re.search(r"多于(\d+)个", tail):
            spec["min"] = int(match.group(1)) + 1
            return {"ten_gods_total": spec}
        if match := re.search(r"(\d+)个", tail):
            if any(token in tail for token in ("只有", "恰好", "正好")):
                spec["eq"] = int(match.group(1))
                return {"ten_gods_total": spec}
    return None


def handle_ten_gods(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    conds: List[Dict[str, Any]] = []
    normalized = cond2.replace(" ", "")
    for ch in "‘’“”":
        normalized = normalized.replace(ch, "")
    normalized = normalized.replace("、", "")
    normalized = normalized.replace("、", "")
    normalized = normalized.replace("、", "")
    normalized = normalized.replace("、", "")
    normalized = re.sub(r"[，,（）()]", "", normalized)
    qty_spec = parse_quantity_spec(qty)

    def apply_qty(names: List[str]) -> Dict[str, Any]:
        spec = {"names": names}
        spec.update(qty_spec)
        return spec

    def add_any_or_single(options: List[Dict[str, Any]]) -> bool:
        if not options:
            return False
        if len(options) == 1:
            conds.append(options[0])
        else:
            conds.append({"any": options})
        return True

    # “主星和副星只有一个X” / “…只有一个Y” 类型
    if "主星和副星只有" in cond2 and "一个" in cond2:
        options: List[Dict[str, Any]] = []
        for name in TEN_GOD_NAMES:
            if f"一个{name}" in cond2:
                options.append({"ten_gods_total": {"names": [name], "eq": 1}})
        if add_any_or_single(options):
            return conds, None

    # “地支副星有三个偏官” 等描述
    if "地支副星有" in cond2:
        text = cond2.split("地支副星有", 1)[1]
        names = split_values(text)
        if not names:
            names = _extract_ten_god_names(text)
        if names:
            count = 1
            if match := re.search(r"(\d+)个", text):
                count = int(match.group(1))
            conds.append({"ten_gods_sub": {"names": names, "min": count}})
            return conds, None

    # “正财3个以上（包含3个），或偏财3个以上（包含3个）” 等带“或”的数量条件
    if "或" in cond2 and any(char.isdigit() for char in cond2):
        parts = [p.strip(" ，。") for p in re.split(r"[，,]?或", cond2) if p.strip()]
        options: List[Dict[str, Any]] = []
        for part in parts:
            spec = _parse_ten_god_count_spec(part)
            if spec:
                options.append(spec)
        if add_any_or_single(options):
            return conds, None

    if qty_spec:
        names = _extract_ten_god_names(cond2)
        if names:
            for name in names:
                spec = {"names": [name]}
                spec.update(qty_spec)
                conds.append({"ten_gods_total": spec})
            if conds:
                return conds, None

    if spec := _parse_ten_god_count_spec(cond2):
        conds.append(spec)
        return conds, None

    if any(token in normalized for token in ("正财或偏财", "偏财或正财")):
        spec = apply_qty(["正财", "偏财"])
        if len(spec) == 1:
            return None, "数量条件需确认"
        conds.append({"ten_gods_total": spec})
    elif any(token in normalized for token in ("正官或偏官", "偏官或正官")):
        spec = apply_qty(["正官", "偏官"])
        if len(spec) == 1:
            return None, "数量条件需确认"
        conds.append({"ten_gods_total": spec})
    elif ("偏财" in normalized and any(token in normalized for token in ("无", "没有"))) and "正财" not in normalized:
        conds.append({"ten_gods_total": {"names": ["偏财"], "eq": 0}})
    elif ("正官" in normalized and any(token in normalized for token in ("无", "没有"))) and "偏官" not in normalized:
        conds.append({"ten_gods_total": {"names": ["正官"], "eq": 0}})
    elif cond2 == "偏财星很少（小于等于1个），而比肩、劫财很多（大于等于3个）":
        conds.append({"ten_gods_main": {"names": ["偏财"], "max": 1}})
        conds.append({"ten_gods_main": {"names": ["比肩", "劫财"], "min": 3}})
    elif cond2 == "偏财星很少（小于等于1个）":
        conds.append({"ten_gods_main": {"names": ["偏财"], "max": 1}})
    elif normalized in {"日支的主星和副星是比肩或劫财", "日支有比肩或劫财"}:
        conds.append({"ten_gods_sub": {"names": ["比肩", "劫财"], "pillars": ["day"], "min": 1}})
    elif normalized in {"日支的主星和副星是食神或伤官", "日支有食神或伤官", "日支是食神或伤官"}:
        conds.append({"ten_gods_sub": {"names": ["食神", "伤官"], "pillars": ["day"], "min": 1}})
    elif cond2 == "主星有正财和偏财":
        conds.append({"ten_gods_main": {"names": ["正财"], "min": 1}})
        conds.append({"ten_gods_main": {"names": ["偏财"], "min": 1}})
    elif cond2 == "主星有两个偏财":
        conds.append({"ten_gods_main": {"names": ["偏财"], "eq": 2}})
    elif cond2 == "主星有两个偏官":
        conds.append({"ten_gods_main": {"names": ["偏官"], "eq": 2}})
    elif cond2 == "地支藏两个偏官":
        conds.append({"ten_gods_sub": {"names": ["偏官"], "min": 2}})
    elif cond2 == "日柱有伤官":
        conds.append({"main_star_in_day": "伤官"})
    elif cond2 == "日支有比肩或劫财":
        conds.append({"ten_gods_sub": {"names": ["比肩", "劫财"], "pillars": ["day"], "min": 1}})
    elif cond2 == "日支的主星和副星是比肩或劫财":
        conds.append({"ten_gods_sub": {"names": ["比肩", "劫财"], "pillars": ["day"], "min": 1}})
    elif cond2 == "日支的主星和副星是食神或伤官":
        conds.append({"ten_gods_sub": {"names": ["食神", "伤官"], "pillars": ["day"], "min": 1}})
    elif cond2 == "偏财在年柱或月柱":
        conds.append({"ten_gods_total": {"names": ["偏财"], "pillars": ["year", "month"], "min": 1}})
    elif cond2 == "正官在年柱或月柱":
        conds.append({"ten_gods_total": {"names": ["正官"], "pillars": ["year", "month"], "min": 1}})
    elif cond2 == "正财在日柱或时柱":
        conds.append({"ten_gods_total": {"names": ["正财"], "pillars": ["day", "hour"], "min": 1}})
    elif cond2 == "正官在日柱或时柱":
        conds.append({"ten_gods_total": {"names": ["正官"], "pillars": ["day", "hour"], "min": 1}})
    elif cond2 == "比肩或劫财在年月柱":
        conds.append({"ten_gods_total": {"names": ["比肩", "劫财"], "pillars": ["year", "month"], "min": 1}})
    elif cond2 == "食神或伤官在年月柱":
        conds.append({"ten_gods_total": {"names": ["食神", "伤官"], "pillars": ["year", "month"], "min": 1}})
    elif cond2 == "月干主星是伤官且地支藏干有七杀":
        conds.append({"main_star_in_pillar": {"pillar": "month", "in": ["伤官"]}})
        conds.append({"ten_gods_sub": {"names": ["七杀"], "pillars": ["month"], "min": 1}})
    elif cond2 == "正财与日干或日支合":
        conds.append({
            "any": [
                {
                    "ten_god_combines": {
                        "god": "正财",
                        "source": "main",
                        "pillars": ["year", "month", "hour"],
                        "target_pillars": ["day"],
                        "target_part": "stem",
                        "relation": "he",
                    }
                },
                {
                    "ten_god_combines": {
                        "god": "正财",
                        "source": "any",
                        "pillars": ["year", "month", "day", "hour"],
                        "target_pillars": ["day"],
                        "target_part": "branch",
                        "relation": "liuhe",
                    }
                }
            ]
        })
    elif cond2 == "年干和月支有伤官":
        conds.append({"main_star_in_pillar": {"pillar": "year", "in": ["伤官"]}})
        conds.append({"ten_gods_sub": {"names": ["伤官"], "pillars": ["month"], "min": 1}})
    elif cond2 == "年柱和时柱主星都是伤官":
        conds.append({"main_star_in_pillar": {"pillar": "year", "eq": "伤官"}})
        conds.append({"main_star_in_pillar": {"pillar": "hour", "eq": "伤官"}})
    elif cond2 == "在年柱或月柱有七杀（偏官），而在日柱或时柱有正官":
        conds.append({"ten_gods_total": {"names": ["七杀", "偏官"], "pillars": ["year", "month"], "min": 1}})
        conds.append({"ten_gods_total": {"names": ["正官"], "pillars": ["day", "hour"], "min": 1}})
    elif normalized in {"主星只有偏财而没有正财", "主星只有偏财,而没有正财"}:
        conds.append({"ten_gods_main": {"names": ["正财"], "eq": 0}})
        conds.append({"ten_gods_main": {"names": ["偏财"], "min": 1}})
    elif normalized in {"主星只有偏财但是没有正财", "主星只有偏财无正财"}:
        conds.append({"ten_gods_main": {"names": ["正财"], "eq": 0}})
        conds.append({"ten_gods_main": {"names": ["偏财"], "min": 1}})
    elif normalized in {"主星没有正财但是有偏财"}:
        conds.append({"ten_gods_main": {"names": ["正财"], "eq": 0}})
        conds.append({"ten_gods_main": {"names": ["偏财"], "min": 1}})
    elif normalized in {"主星和副星中偏财3个以上包含3个", "主星和副星偏财3个以上包含3个", "主星和副星偏财三个以上包含3个"} or ("主星和副星中偏财" in normalized and "3个以上" in normalized):
        spec = {"names": ["偏财"], "min": 3}
        conds.append({"ten_gods_total": spec})
    elif normalized in {"主星和副星劫财这个十神出现了五个之多"}:
        conds.append({"ten_gods_total": {"names": ["劫财"], "min": 5}})
    elif normalized in {"正印这个十神出现了三个或更多"}:
        conds.append({"ten_gods_total": {"names": ["正印"], "min": 3}})
    elif normalized in {"月干为比肩月支为食神"}:
        conds.append({"main_star_in_pillar": {"pillar": "month", "eq": "比肩"}})
        conds.append({"ten_gods_sub": {"names": ["食神"], "pillars": ["month"], "min": 1}})
    elif normalized in {"年干主星是七杀偏官"}:
        conds.append({"main_star_in_pillar": {"pillar": "year", "in": ["七杀", "偏官"]}})
    elif "同一柱" in normalized and "偏财" in normalized and "将星" in normalized:
        combo_conds = []
        for pillar in PILLAR_NAMES:
            combo_conds.append({
                "all": [
                    {
                        "any": [
                            {"main_star_in_pillar": {"pillar": pillar, "eq": "偏财"}},
                            {"ten_gods_sub": {"names": ["偏财"], "pillars": [pillar], "min": 1}},
                        ]
                    },
                    {f"deities_in_{pillar}": "将星"},
                ]
            })
        conds.append({"any": combo_conds})
    elif "天干主星上出现了七杀" in normalized and "副星上出现了正官" in normalized:
        combo_conds = []
        for pillar in PILLAR_NAMES:
            combo_conds.append({
                "all": [
                    {"main_star_in_pillar": {"pillar": pillar, "eq": "七杀"}},
                    {"ten_gods_sub": {"names": ["正官"], "pillars": [pillar], "min": 1}},
                ]
            })
        conds.append({"any": combo_conds})
    elif "七杀" in normalized and "长生" in normalized:
        combo_conds = []
        for pillar in PILLAR_NAMES:
            combo_conds.append({
                "all": [
                    {"main_star_in_pillar": {"pillar": pillar, "in": ["七杀", "偏官"]}},
                    {f"star_fortune_in_{pillar}": "长生"},
                ]
            })
        conds.append({"any": combo_conds})
    elif "偏印和食神出现在同一柱" in normalized:
        combo_conds = []
        for pillar in PILLAR_NAMES:
            combo_conds.append({
                "all": [
                    {
                        "any": [
                            {"main_star_in_pillar": {"pillar": pillar, "eq": "偏印"}},
                            {"ten_gods_sub": {"names": ["偏印"], "pillars": [pillar], "min": 1}},
                        ]
                    },
                    {
                        "any": [
                            {"main_star_in_pillar": {"pillar": pillar, "eq": "食神"}},
                            {"ten_gods_sub": {"names": ["食神"], "pillars": [pillar], "min": 1}},
                        ]
                    },
                ]
            })
        conds.append({"any": combo_conds})
    elif "正官坐在了驿马" in normalized:
        combo_conds = []
        for pillar in PILLAR_NAMES:
            combo_conds.append({
                "all": [
                    {"main_star_in_pillar": {"pillar": pillar, "eq": "正官"}},
                    {f"deities_in_{pillar}": "驿马"},
                ]
            })
        conds.append({"any": combo_conds})
    elif "正财和偏财在四柱中受到刑冲的伤害" in normalized:
        conds.append({
            "ten_gods_injured": {
                "gods": ["正财", "偏财"],
                "relations": ["chong", "xing"]
            }
        })
    elif "主星有正财" in cond2 or "主星有偏财" in cond2:
        star = "正财" if "正财" in cond2 else "偏财"
        conds.append({"ten_gods_main": {"names": [star], "min": 1}})
    elif "主星有正官和七杀" in cond2:
        conds.append({"ten_gods_main": {"names": ["正官"], "min": 1}})
        conds.append({"ten_gods_main": {"names": ["七杀"], "min": 1}})
    elif cond2 == "时柱（天干或地支）有食神":
        conds.append({"main_star_in_pillar": {"pillar": "hour", "in": ["食神"]}})
        conds.append({"ten_gods_sub": {"names": ["食神"], "pillars": ["hour"], "min": 1}})
    elif cond2 == "正官没有与日柱相合，反而去合了年、月、时等其他柱":
        return None, "涉及合化逻辑，暂未实现"
    elif cond2 == "正财与日干或日支合":
        conds.append({
            "any": [
                {
                    "ten_god_combines": {
                        "god": "正财",
                        "source": "main",
                        "pillars": ["year", "month", "hour"],
                        "target_pillars": ["day"],
                        "target_part": "stem",
                        "relation": "he",
                    }
                },
                {
                    "ten_god_combines": {
                        "god": "正财",
                        "source": "any",
                        "pillars": ["year", "month", "day", "hour"],
                        "target_pillars": ["day"],
                        "target_part": "branch",
                        "relation": "liuhe",
                    }
                }
            ]
        })
    else:
        return None, f"未实现的十神条件: {cond2}"

    return conds, None


def handle_day_stem(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    conds: List[Dict[str, Any]] = []
    if cond2 in STEMS:
        conds.append(make_pillar_in("day", "stem", [cond2]))
        return conds, None
    if cond2 in {"五行属土", "对应的五行属土"}:
        conds.append({"pillar_element": {"pillar": "day", "part": "stem", "in": ["土"]}})
        return conds, None
    if cond2 in {"五行属木", "对应的五行属木"}:
        conds.append({"pillar_element": {"pillar": "day", "part": "stem", "in": ["木"]}})
        return conds, None
    if cond2 in {"五行属火", "对应的五行属火"}:
        conds.append({"pillar_element": {"pillar": "day", "part": "stem", "in": ["火"]}})
        return conds, None
    if cond2 in {"五行属金", "对应的五行属金"}:
        conds.append({"pillar_element": {"pillar": "day", "part": "stem", "in": ["金"]}})
        return conds, None
    if cond2 in {"五行属水", "对应的五行属水"}:
        conds.append({"pillar_element": {"pillar": "day", "part": "stem", "in": ["水"]}})
        return conds, None
    if cond2 == "日干是癸水，并且天干又出现了戊":
        conds.append(make_pillar_in("day", "stem", ["癸"]))
        conds.append(make_stems_count(["戊"], min_val=1))
        return conds, None
    if cond2 == "日干与其他天干相合，并且日支坐沐浴":
        return None, "涉及合化与十二长生双条件，暂未实现"
    if cond2 == "流年天干与日主天干相合":
        conds.append({
            "liunian_relation": {
                "part": "stem",
                "target": "day",
                "relation": "he",
            }
        })
        return conds, None
    if "日干是壬水或癸水" in cond2 and ("金3个以上" in cond2 or "水3个以上" in cond2):
        conds.append(make_pillar_in("day", "stem", list("壬癸")))
        conds.append({
            "any": [
                {"element_total": {"names": ["金"], "min": 3}},
                {"element_total": {"names": ["水"], "min": 3}},
            ]
        })
        return conds, None
    if cond2 == "日干是甲木，并且八字天干上有两个己土，那么当遇到蛇年（巳年）或马年（午年）的时候":
        conds.append(make_pillar_in("day", "stem", ["甲"]))
        conds.append(make_stems_count(["己"], eq=2))
        return conds, "涉及流年触发条件需人工确认"
    return None, f"未实现的日干条件: {cond2}"


def handle_day_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    conds: List[Dict[str, Any]] = []
    if cond2 in {"正财", "偏财", "伤官", "七杀", "正印", "偏印", "食神", "比肩", "劫财"}:
        conds.append({"ten_gods_sub": {"names": [cond2], "pillars": ["day"], "min": 1}})
        return conds, None
    if cond2.startswith("副星有"):
        names = split_values(cond2.replace("副星有", ""))
        if not names:
            name = cond2.replace("副星有", "").strip(" ，。")
            if name:
                names = [name]
        if names:
            conds.append({"ten_gods_sub": {"names": names, "pillars": ["day"], "min": 1}})
            return conds, None
    if cond2.startswith("副星包含"):
        names = split_values(cond2.replace("副星包含", ""))
        if names:
            conds.append({"ten_gods_sub": {"names": names, "pillars": ["day"], "min": len(names)}})
            return conds, None
    if cond2.startswith("副星出现"):
        names = split_values(cond2.replace("副星出现", ""))
        if names:
            conds.append({"ten_gods_sub": {"names": names, "pillars": ["day"], "min": 1}})
        return conds, None
    if "日支是正财" in cond2 and "日柱有驿马" in cond2:
        conds.append({"ten_gods_sub": {"names": ["正财"], "pillars": ["day"], "min": 1}})
        conds.append({"deities_in_day": "驿马"})
        return conds, None
    if cond2.startswith("五行为"):
        element = cond2.replace("五行为", "").strip()
        if element:
            conds.append({"day_branch_element_in": [element]})
            return conds, None
    if cond2.startswith("对应的五行为"):
        element = cond2.replace("对应的五行为", "").strip(" ，。")
        if element:
            conds.append({"day_branch_element_in": [element]})
            return conds, None
    if cond2 in {"日干日支五行相生", "日干与日支五行相生"}:
        conds.append({
            "element_relation": {
                "source": "day_stem",
                "target": "day_branch",
                "type": ["generate", "generated_by"],
            }
        })
        return conds, None
    if cond2 in {"日干五行生日支五行", "日干五行与日支五行相生"}:
        conds.append({"element_relation": {"source": "day_stem", "target": "day_branch", "type": "generate"}})
        return conds, None
    if cond2 in {"日支五行生日干五行", "日支五行与日干五行相生"}:
        conds.append({"element_relation": {"source": "day_branch", "target": "day_stem", "type": "generate"}})
        return conds, None
    if cond2 in {"日干日支相克", "日干与日支相克"}:
        conds.append({
            "element_relation": {
                "source": "day_stem",
                "target": "day_branch",
                "type": ["control", "controlled_by"],
            }
        })
        return conds, None
    if cond2 == "长生":
        conds.append({"star_fortune_in_day": "长生"})
        return conds, None
    if cond2 == "沐浴":
        conds.append({"star_fortune_in_day": "沐浴"})
        return conds, None
    if cond2 == "空亡":
        conds.append({"pillar_in": {"pillar": "day", "part": "kongwang", "values": ["空亡"]}})
        return conds, None
    if cond2 in {"神煞有空亡", "神煞是空亡"}:
        conds.append({"deities_in_day": "空亡"})
        return conds, None
    if cond2 in {"神煞有华盖", "神煞是华盖"}:
        conds.append({"deities_in_day": "华盖"})
        return conds, None
    if cond2 == "羊刃":
        conds.append({"deities_in_day": "羊刃"})
        return conds, None
    if cond2.startswith("自坐有"):
        stage = cond2.replace("自坐有", "").strip(" ，。")
        if stage:
            conds.append({"pillar_in": {"pillar": "day", "part": "self_sitting", "values": [stage]}})
            return conds, None
    if cond2 == "日支和时支六合":
        conds.append(make_pillar_relation("day", "hour", "liuhe"))
        return conds, None
    if cond2 == "日支和时支是辰和戌，形成相冲":
        conds.append(make_pillar_in("day", "branch", ["辰"]))
        conds.append(make_pillar_in("hour", "branch", ["戌"]))
        return conds, None
    if "日支和时支同时出现了" in cond2 and "辰" in cond2 and "戌" in cond2:
        combos = [
            {"all": [make_pillar_in("day", "branch", ["辰"]), make_pillar_in("hour", "branch", ["戌"])]},
            {"all": [make_pillar_in("day", "branch", ["戌"]), make_pillar_in("hour", "branch", ["辰"])]},
        ]
        return [{"any": combos}], None
    if cond2 == "华盖":
        conds.append({"deities_in_day": "华盖"})
        return conds, None
    if cond2 == "日支为丑，且时支为戍":
        conds.append(make_pillar_in("day", "branch", ["丑"]))
        conds.append(make_pillar_in("hour", "branch", ["戌"]))
        return conds, None
    if "其中之一" in qty:
        branches = split_values(cond2)
        if branches:
            conds.append({"day_branch_in": branches})
            return conds, None
    if "日支是子、午、卯、酉这四个字" in cond2:
        conds.append({"day_branch_in": list("子午卯酉")})
        return conds, None
    if cond2 == "日支和时支相合，但月支和日支相冲":
        conds.append(make_pillar_relation("day", "hour", "liuhe"))
        conds.append(make_pillar_relation("day", "month", "chong"))
        return conds, None
    if cond2 == "日支同时包含‘羊刃’和‘华盖’":
        conds.append({"all": [{"deities_in_day": "羊刃"}, {"deities_in_day": "华盖"}]})
        return conds, None
    if cond2 in {"日支与月支相同", "日支和月支相同"}:
        conds.append({"day_branch_equals": ["month"]})
        return conds, None
    if cond2 == "日支被其他地支冲克":
        relations = []
        for pillar in ["year", "month", "hour"]:
            relations.append(make_pillar_relation("day", pillar, "chong"))
            relations.append(make_pillar_relation("day", pillar, "ke"))
        return [{"any": relations}], None
    if cond2 == "日支被其他地支刑克":
        relations = []
        for pillar in ["year", "month", "hour"]:
            relations.append(make_pillar_relation("day", pillar, "xing"))
            relations.append(make_pillar_relation("day", pillar, "ke"))
        return [{"any": relations}], None
    if cond2 == "日支被年支和时支同时产生刑、冲、害、绝中的任意一种关系":
        relation_keys = ["xing", "chong", "hai", "po"]
        year_options = [make_pillar_relation("day", "year", rel) for rel in relation_keys]
        hour_options = [make_pillar_relation("day", "hour", rel) for rel in relation_keys]
        return [{"all": [{"any": year_options}, {"any": hour_options}]}], None
    if cond2 == "日支与其他地支形成“六合”的关系":
        relations = [make_pillar_relation("day", pillar, "liuhe") for pillar in ["year", "month", "hour"]]
        return [{"any": relations}], None
    if cond2 == "日支与月支或时支形成“六合”的关系":
        relations = [make_pillar_relation("day", pillar, "liuhe") for pillar in ["month", "hour"]]
        return [{"any": relations}], None
    if cond2 == "日支与年支、月支、时支任何一支发生“刑”或“冲”的关系":
        relations = []
        for pillar in ["year", "month", "hour"]:
            relations.append(make_pillar_relation("day", pillar, "xing"))
            relations.append(make_pillar_relation("day", pillar, "chong"))
        return [{"any": relations}], None
    if "日支是年支在十二地支顺序中的前一位" in cond2:
        conds.append({"branch_offset": {"source": "year", "target": "day", "offset": -1}})
        return conds, None
    if cond2 == "日支、时支是午亥酉辰其中一个字，且日支和时支是一样的字":
        branches = list("午亥酉辰")
        conds.append(make_pillar_relation("day", "hour", "equal"))
        conds.append(make_pillar_in("day", "branch", branches))
        return conds, None
    if cond2 == "流年地支与日主地支相合":
        conds.append({
            "liunian_relation": {
                "part": "branch",
                "target": "day",
                "relation": "liuhe",
            }
        })
        return conds, None
    if cond2 == "日支正好是其坐下对应天干五行的“墓库”":
        conds.append({"pillar_in": {"pillar": "day", "part": "self_sitting", "values": ["墓"]}})
        return conds, None
    return None, f"未实现的日支条件: {cond2}"


def handle_day_pillar(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    conds: List[Dict[str, Any]] = []
    normalized = cond2.replace(" ", "")
    for ch in "‘’“”":
        normalized = normalized.replace(ch, "")

    def extract_pillars(text: str) -> List[str]:
        result: List[str] = []
        for part in re.split(r"[、,，/]+|或", text):
            candidate = (
                part.strip()
                .replace("年", "")
                .replace("月", "")
                .replace("日", "")
                .replace("时", "")
                .replace("柱", "")
                .replace("是", "")
                .replace("为", "")
                .replace("上", "")
                .replace("天干地支", "")
                .replace("天干", "")
                .replace("地支", "")
            )
            candidate = candidate.replace("戍", "戌")
            if len(candidate) == 2 and candidate[0] in STEMS and candidate[1] in BRANCHES:
                result.append(candidate)
        return result

    segments = re.split(r"[，,]", cond2)
    segment_handled = False
    for seg in segments:
        seg = seg.strip()
        pillar_key = None
        if "年柱" in seg:
            pillar_key = "year"
        elif "月柱" in seg:
            pillar_key = "month"
        elif "日柱" in seg:
            pillar_key = "day"
        elif "时柱" in seg:
            pillar_key = "hour"

        if pillar_key:
            candidates = extract_pillars(seg)
            if "华盖" in seg:
                conds.append({f"deities_in_{pillar_key}": "华盖"})
                segment_handled = True
                continue
            if "驿马" in seg:
                conds.append({f"deities_in_{pillar_key}": "驿马"})
                segment_handled = True
                continue
            if candidates:
                conds.append(make_pillar_equals(pillar_key, candidates))
                segment_handled = True

    pillar_candidates = extract_pillars(cond2)

    if pillar_candidates:
        conds.append(make_pillar_equals("day", pillar_candidates))
        return conds, None

    if cond2 == "桃花":
        return None, "桃花日柱判定需额外表，暂未实现"
    if cond2 == "沐浴":
        conds.append({"star_fortune_in_day": "沐浴"})
        return conds, None
    if cond2 == "伤官":
        conds.append({"main_star_in_day": "伤官"})
        return conds, None
    if "日柱的天干和地支都是正财" in normalized:
        conds.append({"main_star_in_day": "正财"})
        conds.append({"ten_gods_sub": {"names": ["正财"], "pillars": ["day"], "min": 1}})
        return conds, None
    if "日柱是正印" in normalized:
        conds.append({"main_star_in_day": "正印"})
        return conds, None
    if cond2 == "偏财":
        conds.append({"main_star_in_day": "偏财"})
        return conds, None
    if cond2.startswith("副星有"):
        names = split_values(cond2.replace("副星有", ""))
        if not names:
            name = cond2.replace("副星有", "").strip(" ，。")
            if name:
                names = [name]
        if names:
            conds.append({"ten_gods_sub": {"names": names, "pillars": ["day"], "min": 1}})
            return conds, None
    if cond2 == "天合地合":
        return None, "涉及天干地支同时合，暂未实现"
    if cond2 == "日柱和时柱相合":
        conds.append(make_pillar_relation("day", "hour", "he"))
        return conds, None
    if cond2 == "日柱和时柱的纳音五行，克年柱的纳音五行":
        return None, "纳音克性判定暂未实现"
    if cond2 == "日柱是乙巳，日支有空亡":
        conds.append(make_pillar_equals("day", ["乙巳"]))
        conds.append({"pillar_in": {"pillar": "day", "part": "kongwang", "values": ["空亡"]}})
        return conds, None
    if cond2 == "日柱是甲戌，日支有空亡":
        conds.append(make_pillar_equals("day", ["甲戌"]))
        conds.append({"pillar_in": {"pillar": "day", "part": "kongwang", "values": ["空亡"]}})
        return conds, None
    if cond2 == "日柱是甲辰，且时柱是甲戍":
        conds.append(make_pillar_equals("day", ["甲辰"]))
        conds.append(make_pillar_equals("hour", ["甲戌"]))
        return conds, None
    if conds:
        return conds, None
    return None, f"未实现的日柱条件: {cond2}"


def handle_four_pillars(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    normalized = cond2.replace(" ", "")
    conds: List[Dict[str, Any]] = []

    if normalized in {"没有偏财", "主星和副星没有偏财"}:
        conds.append({"ten_gods_total": {"names": ["偏财"], "eq": 0}})
        return conds, None

    if normalized in {"没有正官", "主星和副星没有正官"}:
        conds.append({"ten_gods_total": {"names": ["正官"], "eq": 0}})
        return conds, None

    if normalized == "主星没有正财但是有偏财":
        conds.append({"ten_gods_main": {"names": ["正财"], "eq": 0}})
        conds.append({"ten_gods_main": {"names": ["偏财"], "min": 1}})
        return conds, None

    if "丙午或丁未" in normalized and "水" in normalized:
        conds.append({
            "any": [
                make_any_pillar_equals("丙午"),
                make_any_pillar_equals("丁未"),
            ]
        })
        conds.append({"element_total": {"names": ["水"], "min": 3}})
        return conds, None

    if normalized == "同时有甲申和甲寅这两柱":
        conds.append(make_any_pillar_equals("甲申"))
        conds.append(make_any_pillar_equals("甲寅"))
        return conds, None

    return None, f"未实现的四柱条件: {cond2}"


def handle_branch_pattern(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    text = cond2.strip()
    if "紧挨着出现" in text:
        return [{"branch_adjacent": {"pairs": [["丑", "寅"], ["亥", "午"]]}}], None
    targets = re.findall(r"[‘“](.+?)[’”]", text)
    if targets:
        if "两个" in cond2:
            if len(targets) == 1:
                return [make_branches_count([targets[0]], eq=2)], None
            return [make_branches_count(targets, eq=2)], None
        if "三个" in cond2:
            return [make_branches_count(targets, eq=3)], None
        if "四个" in cond2:
            return [make_branches_count(targets, eq=4)], None
        conds = [make_branches_count([t], min_val=1) for t in targets]
        return conds, None
    if "构成了三合局" in text:
        return [{"branch_group": {"type": "sanhe"}}], None
    if "三会局" in text:
        return [{"branch_group": {"type": "sanhui"}}], None
    match = re.match(r"有([一二三四五六七八九十两\d]+)个(.+)", text)
    if match:
        num_text = match.group(1)
        target = match.group(2).strip()
        spec = parse_quantity_spec(num_text)
        count = spec.get("eq") or spec.get("min") or 0
        if count:
            if len(target) == 1 and target in BRANCHES:
                return [make_branches_count([target], eq=count)], None
            if "和" in target and "或" not in target:
                branches = re.split(r"[和、]", target)
                branches = [b for b in branches if b]
                return [make_branches_count(branches, eq=count)], None
    if cond2 == "巳和亥":
        return [make_branches_count(["巳"], min_val=1), make_branches_count(["亥"], min_val=1)], None
    if cond2 == "同时出现了‘辰’和‘戌’这两个字":
        return [
            make_branches_count(["辰"], min_val=1),
            make_branches_count(["戌"], min_val=1),
        ], None
    if text.strip() in {"辰、戌、丑、未", "辰戌丑未"}:
        return [
            make_branches_count(["辰"], min_val=1),
            make_branches_count(["戌"], min_val=1),
            make_branches_count(["丑"], min_val=1),
            make_branches_count(["未"], min_val=1),
        ], None
    if "四个地支都是同样的一个字" in text:
        return [{"branches_unique": {"eq": 1}}], None

    return None, f"未实现的地支条件: {cond2}"


def handle_stem_pattern(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    normalized = cond2.replace(" ", "")
    if "同时出现了" in cond2 and "‘" in cond2:
        targets = re.findall(r"‘(.+?)’", cond2)
        if targets:
            conds = [make_stems_count([stem], min_val=1) for stem in targets]
            return conds, None
    if cond2 == "主星有偏财":
        return [{"ten_gods_main": {"names": ["偏财"], "min": 1}}], None
    if cond2 == "主星有正官":
        return [{"ten_gods_main": {"names": ["正官"], "min": 1}}], None
    if cond2 == "同时出现了两个伤官":
        return [{"ten_gods_total": {"names": ["伤官"], "min": 2}}], None
    if "两个丙" in cond2 and "一个庚" in cond2:
        return [make_stems_count(["丙"], eq=2), make_stems_count(["庚"], eq=1)], None
    if "有三个“癸”和一个“辛”" in cond2 or "有三个癸和一个辛" in cond2:
        return [make_stems_count(["癸"], eq=3), make_stems_count(["辛"], eq=1)], None
    if "有戊和癸" in cond2:
        return [make_stems_count(["戊"], min_val=1), make_stems_count(["癸"], min_val=1)], None
    if "同时出现了壬水和丙火" in cond2:
        return [make_stems_count(["壬"], min_val=1), make_stems_count(["丙"], min_val=1)], None
    if "有四个甲" in cond2:
        return [make_stems_count(["甲"], eq=4)], None
    if "有四个丁" in cond2:
        return [make_stems_count(["丁"], eq=4)], None
    if "四个天干都是同样的一个字" in cond2:
        return [{"stems_unique": {"eq": 1}}], None
    if cond2 == "三戊一丁":
        return [make_stems_count(["戊"], eq=3), make_stems_count(["丁"], eq=1)], None
    if "出现了“伤官”这个十神，而没有出现“正官”" in cond2 or "出现了伤官这个十神而没有出现正官" in cond2:
        return [
            {"ten_gods_total": {"names": ["伤官"], "min": 1}},
            {"ten_gods_total": {"names": ["正官"], "eq": 0}},
        ], None
    if cond2 == "四个天干中，有三个是相同的字":
        return [make_stems_repeat(min_val=3)], None
    if "按照甲、乙、丙、丁这样的顺序顺次排列" in cond2 or "按照甲乙丙丁顺序排列" in cond2:
        return None, "涉及序列顺序判定，暂未实现"
    if cond2 == "有两组天干是相冲的关系":
        return None, "天干冲关系暂未实现"
    if cond2 == "甲乙壬癸":
        return [make_stems_count(list("甲乙壬癸"), min_val=1)], "请确认是否要求四字全部出现"
    if "出现两个“甲”" in cond2 and "两个“庚”" in cond2:
        return [{
            "any": [
                make_stems_count(["甲"], min_val=2),
                make_stems_count(["庚"], min_val=2),
            ]
        }], None
    if "出现了三个“庚”" in cond2:
        return [make_stems_count(["庚"], eq=3)], None
    if "出现了三个“寅”" in cond2:
        return [make_branches_count(["寅"], eq=3)], None
    if cond2 == "天干主星上出现了“七杀”，且副星上出现了“正官”":
        return [
            {"ten_gods_main": {"names": ["七杀"], "min": 1}},
            {"ten_gods_sub": {"names": ["正官"], "min": 1}},
        ], None
    if "四个天干全部是阳干" in cond2:
        return [{"stems_parity": {"type": "yang"}}], None
    if "四个天干全部是阴干" in cond2:
        return [{"stems_parity": {"type": "yin"}}], None
    return None, f"未实现的天干条件: {cond2}"


def handle_bazi_pattern(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    conds: List[Dict[str, Any]] = []
    normalized = cond2.replace(" ", "")
    for ch in "‘’“”":
        normalized = normalized.replace(ch, "")
    normalized = normalized.replace("、", "")
    normalized = re.sub(r"[，,（）()]", "", normalized)

    if cond2 == "年支和日支是同一个字":
        return [make_pillar_relation("year", "day", "equal")], None
    if cond2 == "年支和日支相合":
        return [make_pillar_relation("year", "day", "liuhe")], None
    if cond2 == "年柱和日柱的字是相同的":
        return [make_pillar_relation("year", "day", "equal", part="pillar")], None
    if cond2 == "年柱和日柱相合":
        return [make_pillar_relation("year", "day", "he")], None
    if cond2 == "日柱和时柱相合":
        return [make_pillar_relation("day", "hour", "he")], None
    if normalized == "年干和日干都是甲":
        return [make_pillar_in("year", "stem", ["甲"]), make_pillar_in("day", "stem", ["甲"])], None
    if normalized == "日柱和时柱都是甲子":
        return [make_pillar_equals("day", ["甲子"]), make_pillar_equals("hour", ["甲子"])], None
    if normalized == "月柱和日柱的天干相合同时地支也相合":
        return [
            make_pillar_relation("month", "day", "he", part="stem"),
            make_pillar_relation("month", "day", "liuhe"),
        ], None
    if normalized == "年柱和日柱天干相合地支也相合":
        return [
            make_pillar_relation("year", "day", "he", part="stem"),
            make_pillar_relation("year", "day", "liuhe"),
        ], None
    if normalized == "日支和时支相冲":
        return [make_pillar_relation("day", "hour", "chong")], None
    if normalized == "日支和时支是相刑的关系":
        return [make_pillar_relation("day", "hour", "xing")], None
    if normalized == "年柱的天干和日柱的天干是相合的关系":
        return [make_pillar_relation("year", "day", "he", part="stem")], None
    if "月支和日支的关系是相克或者相合" in normalized:
        return [
            {
                "any": [
                    make_pillar_relation("month", "day", "ke"),
                    make_pillar_relation("month", "day", "liuhe"),
                ]
            }
        ], None
    if "月支日支时支的地支是同一个字" in normalized:
        return [
            make_pillar_relation("month", "day", "equal"),
            make_pillar_relation("day", "hour", "equal"),
        ], None
    if "月柱和时柱的天干地支完全一样" in normalized:
        return [make_pillar_relation("month", "hour", "equal", part="pillar")], None
    if normalized == "日柱和时柱是天合地合的关系":
        return [
            make_pillar_relation("day", "hour", "he", part="stem"),
            make_pillar_relation("day", "hour", "liuhe"),
        ], None
    if "日干是壬水或癸水" in normalized and ("金3个以上" in normalized or "水3个以上" in normalized):
        return [
            make_pillar_in("day", "stem", list("壬癸")),
            {
                "any": [
                    {"element_total": {"names": ["金"], "min": 3}},
                    {"element_total": {"names": ["水"], "min": 3}},
                ]
            },
        ], None
    if "出现了两个‘" in cond2:
        targets = re.findall(r"‘(.+?)’", cond2)
        if targets:
            return [make_branches_count(targets, eq=2)], None
    if cond2 == "辰戌丑末" and "3个" in qty:
        return [make_branches_count(list("辰戌丑未"), min_val=3)], None
    if cond2 == "地支出现了三个或四个连续的字（比如三会局，或地支一字连）":
        return None, "需要检测连续地支，暂未实现"
    if cond2 == "月柱和日柱，天干相克、地支相冲":
        return [
            make_pillar_relation("month", "day", "ke", part="stem"),
            make_pillar_relation("month", "day", "chong"),
        ], None
    if "地支“丑”和“寅”" in cond2 and "“亥”和“午”" in cond2 and "紧挨着出现" in cond2:
        return [{"branch_adjacent": {"pairs": [["丑", "寅"], ["亥", "午"]]}}], None
    if cond2 == "年柱戊寅，时柱甲子":
        return [
            make_pillar_equals("year", ["戊寅"]),
            make_pillar_equals("hour", ["甲子"]),
        ], None
    if cond2 == "日支和月支形成地支六合":
        return [make_pillar_relation("day", "month", "liuhe")], None
    if "四个天干全部是阳干" in cond2 and "全部是阴干" in cond2:
        return [{
            "any": [
                {"stems_parity": {"type": "yang"}},
                {"stems_parity": {"type": "yin"}},
            ]
        }], None
    if cond2 == "辰、戍、丑、未见相同的字":
        return None, "需要排除四墓重字，暂未实现"
    if conds:
        return conds, None
    return None, f"未实现的八字条件: {cond2}"


def handle_deity(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    text = cond2.strip()
    if "流年" in text:
        quote_pattern = r"[‘'\"“](.+?)[’'\"”]"
        names = re.findall(quote_pattern, text)
        if not names:
            candidates = []
            for keyword in ["红鸾", "天喜", "天德", "月德"]:
                if keyword in text:
                    candidates.append(keyword)
            names = candidates
        if not names:
            return None, "流年神煞条件缺少神煞名称"
        return [{"liunian_deities": {"any": names}}], None

    if "命局中“六合”与“三合”" in text:
        return None, "神煞组合判定待实现"

    quote_pattern = r"[‘'\"“](.+?)[’'\"”]"

    if "带有" in text:
        # e.g. 日柱带有‘魁罡’这个神煞
        m = re.findall(quote_pattern, text)
        deity_names = m if m else []
        if not deity_names:
            suffix = text.split("带有", 1)[-1]
            suffix = suffix.replace("这个神煞", "").strip()
            if suffix:
                deity_names = [suffix]
        if not deity_names:
            return None, "神煞名称缺失"

        targets = []
        if "日柱" in text:
            targets.append("day")
        if "月柱" in text:
            targets.append("month")
        if "年柱" in text:
            targets.append("year")
        if "时柱" in text:
            targets.append("hour")

        if not targets:
            targets = PILLAR_NAMES

        conds: List[Dict[str, Any]] = []
        for deity in deity_names:
            if len(targets) == 1:
                target = targets[0]
                key = f"deities_in_{target}"
                conds.append({key: deity})
            else:
                any_list = []
                for target in targets:
                    key = f"deities_in_{target}"
                    any_list.append({key: deity})
                container = "all" if any(token in text for token in ["都", "同时"]) else "any"
                conds.append({container: any_list})
        return conds, None

    if "同时出现了" in text or "同时出现在" in text:
        items = re.findall(quote_pattern, text)
        if len(items) >= 2:
            pair_conds = []
            for pillar in PILLAR_NAMES:
                key = f"deities_in_{pillar}"
                pair_conds.append({"all": [{key: items[0]}, {key: items[1]}]})
            return [{"any": pair_conds}], None

    if "魁罡" in text:
        # 默认日柱魁罡
        return [{"deities_in_day": "魁罡"}], None

    return None, "神煞组合判定待实现"


def handle_year_pillar(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    if cond2 == "年柱和日柱形成了天克地冲的关系":
        return [
            make_pillar_relation("year", "day", "chong"),
            make_pillar_relation("year", "day", "ke", part="stem"),
        ], None
    if cond2 == "年柱和日柱都是甲午":
        return [make_pillar_equals("year", ["甲午"]), make_pillar_equals("day", ["甲午"])], None
    if cond2 == "年柱纳音是水，并且整个八字中水的五行非常多":
        return None, "纳音与五行数量复合判断暂未实现"
    if cond2 == "夫妻两人的年柱是天克地冲的关系":
        return None, "涉及两人数据，当前排盘数据仅一方，暂未实现"
    return None, f"未实现的年柱条件: {cond2}"


def handle_year_stem(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    if cond2 == "年干和日干是同一个字":
        return [make_pillar_relation("year", "day", "equal", part="stem")], None
    if cond2 == "年干和时干形成天干五合":
        return [make_pillar_relation("year", "hour", "he", part="stem")], None
    if "主星是七杀" in cond2 and ("偏官" in cond2 or "七杀" in cond2):
        return [{"main_star_in_pillar": {"pillar": "year", "in": ["七杀", "偏官"]}}], None
    if cond2 == "年干有戊，且日干或时干有癸":
        return [make_pillar_in("year", "stem", ["戊"]),
                {"any": [make_pillar_in("day", "stem", ["癸"]), make_pillar_in("hour", "stem", ["癸"])]}], None
    if cond2 == "年干有癸，且日干或时干有戊":
        return [make_pillar_in("year", "stem", ["癸"]),
                {"any": [make_pillar_in("day", "stem", ["戊"]), make_pillar_in("hour", "stem", ["戊"])]}], None
    if cond2 == "年干和日干，既是相合的关系，又是相克的关系":
        return [
            make_pillar_relation("year", "day", "he", part="stem"),
            make_pillar_relation("year", "day", "ke", part="stem"),
        ], None
    return None, f"未实现的年干条件: {cond2}"


def handle_year_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    if cond2 == "年支和日支是同一个字":
        return [make_pillar_relation("year", "day", "equal")], None
    if cond2 == "年支是子或午，月支是卯或酉":
        return [
            make_pillar_in("year", "branch", list("子午")),
            make_pillar_in("month", "branch", list("卯酉")),
        ], None
    if cond2 == "年支是寅或申，月支是巳或亥":
        return [
            make_pillar_in("year", "branch", list("寅申")),
            make_pillar_in("month", "branch", list("巳亥")),
        ], None
    if cond2 == "年支是酉，而日支是巳或者午":
        return [
            make_pillar_in("year", "branch", ["酉"]),
            make_pillar_in("day", "branch", list("巳午")),
        ], None
    if "年支是“酉”" in cond2 and "日支的五行属“火”" in cond2:
        return [
            make_pillar_in("year", "branch", ["酉"]),
            {"pillar_element": {"pillar": "day", "part": "branch", "in": ["火"]}},
        ], None
    if cond2 == "正印":
        return [{"ten_gods_main": {"names": ["正印"], "pillars": ["year"], "min": 1}}], None
    return None, f"未实现的年支条件: {cond2}"


def handle_month_branch(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    if cond2 == "月支和日支相冲":
        return [make_pillar_relation("month", "day", "chong")], None
    if cond2 == "空亡":
        return [{"pillar_in": {"pillar": "month", "part": "kongwang", "values": ["空亡"]}}], None
    if cond2 == "月支（月令）遭受到刑、冲、克、害（绝与穿是害的另一种说法）":
        return None, "刑克害复合关系暂未实现"
    if cond2 == "月支和日支是同一个字，并且这个字是‘比肩’或‘劫财’":
        return None, "需要将月支转换为十神判定，暂未实现"
    if cond2 == "月支是辰或戌，日支是丑或未":
        return [
            make_pillar_in("month", "branch", list("辰戌")),
            make_pillar_in("day", "branch", list("丑未")),
        ], None
    if cond2 == "月支与其他地支（尤其是日支）形成“六合”的关系":
        relations = [
            make_pillar_relation("month", pillar, "liuhe")
            for pillar in ["day", "year", "hour"]
        ]
        return [{"any": relations}], None
    if "副星包含伤官、偏印、七杀" in cond2 or "副星包含伤官偏印七杀" in cond2:
        return [
            {"ten_gods_sub": {"names": ["伤官"], "pillars": ["month"], "min": 1}},
            {"ten_gods_sub": {"names": ["偏印"], "pillars": ["month"], "min": 1}},
            {"ten_gods_sub": {"names": ["七杀"], "pillars": ["month"], "min": 1}},
        ], None
    return None, f"未实现的月支条件: {cond2}"


def handle_month_pillar(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    text = cond2.replace("（", "(").replace("）", ")").strip()
    if text in {"主星有七杀（偏官）", "主星有七杀(偏官)"}:
        return [{"main_star_in_pillar": {"pillar": "month", "in": ["七杀", "偏官"]}}], None
    if text == "空亡":
        return [{"pillar_in": {"pillar": "month", "part": "kongwang", "values": ["空亡"]}}], None
    return None, f"未实现的月柱条件: {cond2}"


def handle_hour_pillar(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    if cond2 == "辛卯":
        return [make_pillar_equals("hour", ["辛卯"])], None
    if cond2 == "主星副星只有一个偏财":
        return [{"all": [
            {"ten_gods_main": {"names": ["偏财"], "pillars": ["hour"], "eq": 1}},
            {"ten_gods_sub": {"names": ["偏财"], "pillars": ["hour"], "eq": 0}},
        ]}], None
    if cond2 == "天干是偏财":
        return [{"main_star_in_pillar": {"pillar": "hour", "eq": "偏财"}}], None
    if cond2 == "天干是正官":
        return [{"main_star_in_pillar": {"pillar": "hour", "eq": "正官"}}], None
    return None, f"未实现的时柱条件: {cond2}"


def handle_nayin(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    if cond2 == "月柱和日柱的纳音相同":
        return [make_pillar_relation("month", "day", "equal", part="nayin")], None
    if cond2 == "天河水":
        return None, "需要统计纳音数量，暂未实现"
    return None, f"未实现的纳音条件: {cond2}"


def handle_lunar_birthday(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    return None, "农历生日相关条件需外部输入，暂未实现"


def handle_year_event(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    return None, "年份与岁运相关条件需动态大运数据，暂未实现"


def handle_luck_cycle(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    return None, "大运条件需大运信息，暂未实现"


CONDITION_HANDLERS = {
    "十神": handle_ten_gods,
    "五行": handle_element_total,
    "日干": handle_day_stem,
    "日支": handle_day_branch,
    "日柱": handle_day_pillar,
    "天干": handle_stem_pattern,
    "地支": handle_branch_pattern,
    "八字": handle_bazi_pattern,
    "神煞": handle_deity,
    "月支": handle_month_branch,
    "月柱": handle_month_pillar,
    "年支": handle_year_branch,
    "年干": handle_year_stem,
    "年柱": handle_year_pillar,
    "纳音": handle_nayin,
    "农历生日": handle_lunar_birthday,
    "时柱": handle_hour_pillar,
    "年份": handle_year_event,
    "大运": handle_luck_cycle,
    "四柱": handle_four_pillars,
}


def import_rules(
    json_paths: List[str],
    write_db: bool = True,
    append: bool = False,
    pending_path: Optional[str] = DEFAULT_PENDING_PATH,
) -> Tuple[List[ParsedRule], List[SkippedRule], List[SkippedRule], int, int]:
    rows = load_rows(json_paths)
    pending_ids = load_pending_rule_ids(pending_path)
    parsed: List[ParsedRule] = []
    skipped: List[SkippedRule] = []
    skipped_existing: List[SkippedRule] = []
    seen_codes: Set[str] = set()

    for row in rows:
        source = row.get("_source", "")
        raw_rule_id = str(row.get("ID", "")).strip()
        try:
            rule_id = int(raw_rule_id)
        except (TypeError, ValueError):
            skipped.append(SkippedRule(rule_id=-1, reason="ID 缺失或非法", source=source))
            continue

        if pending_ids and rule_id in pending_ids:
            skipped.append(SkippedRule(rule_id=rule_id, reason="待确认规则，暂不导入", source=source))
            continue

        condition, reason = build_conditions(row)
        if not condition:
            skipped.append(SkippedRule(rule_id=rule_id, reason=reason or "未解析", source=source))
            continue

        rule_code = f"MARR-{rule_id}"
        if rule_code in seen_codes:
            skipped.append(SkippedRule(rule_id=rule_id, reason="rule_code 重复（输入文件）", source=source))
            continue
        seen_codes.add(rule_code)

        cond1 = (row.get("筛选条件1") or "").strip()
        rule_type = RULE_TYPE_MAP.get(cond1, "marriage_general")
        rule_dict = {
            "rule_code": rule_code,
            "rule_name": f"婚姻规则{rule_id}",
            "rule_type": rule_type,
            "rule_category": "marriage",
            "priority": 85,
            "conditions": condition,
            "content": {
                "type": "description",
                "text": (row.get("结果") or "").strip(),
            },
        }
        parsed.append(ParsedRule(rule=rule_dict, row=row, source=source))

    inserted_count = 0
    updated_count = 0

    if write_db and parsed:
        from server.config.mysql_config import get_mysql_connection  # noqa: E402

        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                existing_codes: Set[str] = set()
                if append:
                    cur.execute("SELECT rule_code FROM bazi_rules")
                    existing_codes = {item["rule_code"] for item in cur.fetchall()}
                else:
                    cur.execute("DELETE FROM bazi_rules")

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
                        # 在append模式下，如果规则已存在，也更新它（使用新解析的逻辑）
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
                        continue
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
                    existing_codes.add(code)

                if values:
                    cur.executemany(sql, values)
                    inserted_count = len(values)
                
                # 更新已存在的规则
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


def main():
    parser = argparse.ArgumentParser(description="导入婚姻规则到数据库（支持干支规则）")
    parser.add_argument("--dry-run", action="store_true", help="仅解析并打印结果，不写入数据库")
    parser.add_argument("--append", action="store_true", help="采用追加模式，不清空现有规则")
    parser.add_argument("--json-path", action="append", dest="json_paths", help="指定要解析的 JSON 文件，可多次使用", default=[])
    parser.add_argument("--pending-json", dest="pending_json", default=DEFAULT_PENDING_PATH,
                        help="待确认规则列表 JSON，命中后直接跳过（默认 docs/rule_pending_confirmation.json）")
    args = parser.parse_args()

    json_paths = args.json_paths or [DEFAULT_JSON_PATH]
    parsed, skipped, skipped_existing, inserted, updated = import_rules(
        json_paths=json_paths,
        write_db=not args.dry_run,
        append=args.append,
        pending_path=args.pending_json,
    )

    print(f"✓ 可解析规则: {len(parsed)} 条, 待确认/跳过: {len(skipped)} 条, 已存在跳过: {len(skipped_existing)} 条")
    print("使用 JSON 文件:", ", ".join(json_paths))
    if not args.dry_run:
        if inserted > 0:
            print(f"数据库实际新增规则: {inserted} 条")
        if updated > 0:
            print(f"数据库实际更新规则: {updated} 条")

    if skipped:
        print("⚠ 需确认的规则：")
        for item in skipped:
            print(f" - {item.source} ID {item.rule_id}: {item.reason}")

    if skipped_existing:
        print("⚠ 已存在的规则：")
        for item in skipped_existing:
            print(f" - {item.source} ID {item.rule_id}: {item.reason}")

    if args.dry_run and parsed:
        print("\n示例规则预览（前5条）：")
        for item in parsed[:5]:
            print(json.dumps(item.rule, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


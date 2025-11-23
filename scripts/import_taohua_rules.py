#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 docs/桃花算法公式.json 解析桃花、正缘、婚姻、富贵命规则，并批量写入 MySQL。
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
    make_pillar_equals,
    make_pillar_in,
)

DEFAULT_JSON_PATH = os.path.join(PROJECT_ROOT, "docs", "桃花算法公式.json")
DEFAULT_PENDING_PATH = os.path.join(PROJECT_ROOT, "docs", "taohua_rule_pending_confirmation.json")

# 规则类型映射（基于类型字段）
RULE_CATEGORY_MAP = {
    "桃花": "taohua",
    "正缘": "zhengyuan",
    "婚姻": "marriage",
    "上上乘富贵命": "fugui",
}

# 规则代码前缀映射
RULE_CODE_PREFIX_MAP = {
    "桃花": "TAOHUA",
    "正缘": "ZHENGYUAN",
    "婚姻": "MARRIAGE",
    "上上乘富贵命": "FUGUI",
}


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
    """从桃花算法公式.json加载数据"""
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


def handle_taohua_nayin(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理桃花纳音条件，支持大运/流年"""
    # 示例：日柱的纳音五行属性为金的，年、月、日、时柱或大运、流年中，见到"巳"或"亥"地支
    # 使用更灵活的模式匹配中文引号（中文引号是 "" (U+201C) 和 "" (U+201D)）
    # 使用 Unicode 转义或字符类来匹配中文引号
    pattern = r'日柱的纳音五行属性为([木火土金水])的.*?见到[\u201C\u201D"]([^\u201C\u201D"]+)[\u201C\u201D"].*?[\u201C\u201D"]([^\u201C\u201D"]+)[\u201C\u201D"]地支'
    match = re.search(pattern, cond2)
    if match:
        element = match.group(1)
        branch1 = match.group(2)
        branch2 = match.group(3)
        
        # 检查是否包含大运/流年
        has_dayun_liunian = "大运" in cond2 or "流年" in cond2
        
        # 构建条件：日柱纳音 + 在任意柱/大运/流年中查找指定地支
        conditions = [
            {"pillar_element": {"pillar": "day", "part": "nayin", "in": [element]}}
        ]
        
        # 在四柱中查找
        pillar_conditions = [
            make_pillar_in(pillar, "branch", [branch1, branch2])
            for pillar in PILLAR_NAMES
        ]
        
        # 如果包含大运/流年，添加大运/流年条件
        if has_dayun_liunian:
            # 大运条件：在大运地支中查找
            dayun_condition = {
                "dayun_branch_in": {
                    "values": [branch1, branch2]
                }
            }
            # 流年条件：在流年地支中查找
            liunian_condition = {
                "liunian_branch_in": {
                    "values": [branch1, branch2]
                }
            }
            # 任意一个满足即可（四柱、大运、流年）
            conditions.append({
                "any": pillar_conditions + [dayun_condition, liunian_condition]
            })
        else:
            # 只在四柱中查找
            conditions.append({"any": pillar_conditions})
        
        return conditions, None
    return None, f"未实现的纳音桃花条件: {cond2}"


def handle_taohua_pillar_combination(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理桃花日柱组合条件，如：日柱为丙子，时柱辛卯"""
    # 匹配：日柱为XXX，时柱YYY
    pattern = r"日柱为([^，,]+)，时柱([^，,]+)"
    match = re.search(pattern, cond2)
    if match:
        day_pillar = match.group(1).strip()
        hour_pillar = match.group(2).strip()
        return [
            make_pillar_equals("day", [day_pillar]),
            make_pillar_equals("hour", [hour_pillar]),
        ], None
    
    # 匹配：时柱为XXX，日柱YYY
    pattern = r"时柱为([^，,]+)，日柱([^，,]+)"
    match = re.search(pattern, cond2)
    if match:
        hour_pillar = match.group(1).strip()
        day_pillar = match.group(2).strip()
        return [
            make_pillar_equals("day", [day_pillar]),
            make_pillar_equals("hour", [hour_pillar]),
        ], None
    
    return None, f"未实现的日柱组合条件: {cond2}"


def handle_taohua_day_branch_complex(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理复杂的日支条件，如：日支是申、子、辰其中之一，且时支是酉
    支持农历月份条件，如：日支是申、子、辰其中之一，农历是4、5、6月份其中之一出生，且时支是巳"""
    # 匹配：日支是XXX、YYY、ZZZ其中之一，且时支是WWW（可能中间有农历月份条件）
    # 使用更灵活的模式，允许中间有农历月份条件
    pattern = r"日支是([^，,]+?)(?:，.*?)?且时支是([^，,]+)"
    match = re.search(pattern, cond2)
    if match:
        day_branches_str = match.group(1).strip()
        hour_branch = match.group(2).strip()
        
        # 提取日支列表（可能是"申、子、辰其中之一"或直接是"申、子、辰"）
        day_branches = [b.strip() for b in re.split(r"[、,，]", day_branches_str) if b.strip()]
        # 移除"其中之一"等后缀
        day_branches = [b.replace("其中之一", "").strip() for b in day_branches if b.replace("其中之一", "").strip()]
        
        conditions = []
        if day_branches:
            conditions.append(make_pillar_in("day", "branch", day_branches))
        if hour_branch:
            conditions.append(make_pillar_in("hour", "branch", [hour_branch]))
        
        # 检查是否包含农历月份条件
        lunar_month_pattern = r"农历是([^，,]+)月份"
        lunar_match = re.search(lunar_month_pattern, cond2)
        if lunar_match:
            months_str = lunar_match.group(1).strip()
            # 提取月份数字
            months = []
            for m in re.split(r"[、,，]", months_str):
                m = m.strip()
                # 提取数字
                numbers = re.findall(r"\d+", m)
                if numbers:
                    months.extend([int(n) for n in numbers])
            
            if months:
                conditions.append({
                    "lunar_month_in": {
                        "values": months
                    }
                })
        
        if conditions:
            return conditions, None
    
    return None, f"未实现的复杂日支条件: {cond2}"


def handle_taohua_simple_branches(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理简单的地支列表，如：子、午、卯、酉"""
    branches = [b.strip() for b in re.split(r"[、,，]", cond2) if b.strip() and b.strip() in "子丑寅卯辰巳午未申酉戌亥"]
    if branches:
        return [make_pillar_in("day", "branch", branches)], None
    return None, f"无法解析地支列表: {cond2}"


# 扩展条件处理器
EXTENDED_CONDITION_HANDLERS = CONDITION_HANDLERS.copy()
EXTENDED_CONDITION_HANDLERS["纳音"] = handle_taohua_nayin


def build_taohua_conditions(row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """构建桃花规则条件"""
    rule_id = int(row["ID"])
    cond1 = (row.get("筛选条件1") or "").strip()
    cond2 = (row.get("筛选条件2") or "").strip()
    qty = (row.get("数量") or "").strip()
    gender = normalize_gender(row.get("性别"))
    rule_type = row.get("类型", "").strip()

    conds: List[Dict[str, Any]] = []
    if gender:
        conds.append({"gender": gender})

    if not cond1:
        return None, "缺少筛选条件1"

    if not cond2:
        return None, "缺少筛选条件2"

    # 特殊处理桃花相关的复杂条件
    if rule_type == "桃花" and cond1 == "纳音":
        extra_conditions, reason = handle_taohua_nayin(cond2, qty)
    elif rule_type == "桃花" and cond1 == "日柱" and ("时柱" in cond2 or "日柱为" in cond2):
        extra_conditions, reason = handle_taohua_pillar_combination(cond2, qty)
    elif cond1 == "日支" and ("且时支" in cond2 or "农历" in cond2):
        # 支持农历月份条件的复杂日支条件
        extra_conditions, reason = handle_taohua_day_branch_complex(cond2, qty)
    elif cond1 in ["日支", "时支"] and re.match(r"^[子丑寅卯辰巳午未申酉戌亥、，,]+$", cond2):
        # 简单的地支列表
        if cond1 == "日支":
            branches = [b.strip() for b in re.split(r"[、,，]", cond2) if b.strip() and b.strip() in "子丑寅卯辰巳午未申酉戌亥"]
            if branches:
                extra_conditions, reason = [make_pillar_in("day", "branch", branches)], None
            else:
                extra_conditions, reason = None, f"无法解析日支列表: {cond2}"
        elif cond1 == "时支":
            branches = [b.strip() for b in re.split(r"[、,，]", cond2) if b.strip() and b.strip() in "子丑寅卯辰巳午未申酉戌亥"]
            if branches:
                extra_conditions, reason = [make_pillar_in("hour", "branch", branches)], None
            else:
                extra_conditions, reason = None, f"无法解析时支列表: {cond2}"
        else:
            extra_conditions, reason = None, f"未处理的简单地支条件: {cond1}"
    else:
        # 使用标准处理器
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

    for row in rows:
        source = row.get("_source", "")
        sheet = row.get("_sheet", "")
        rule_type = row.get("类型", "").strip()
        raw_rule_id = str(row.get("ID", "")).strip()
        
        try:
            rule_id = int(raw_rule_id)
        except (TypeError, ValueError):
            skipped.append(SkippedRule(
                rule_id=-1,
                reason="ID 缺失或非法",
                source=source,
                sheet=sheet,
                rule_type=rule_type
            ))
            continue

        if pending_ids and rule_id in pending_ids:
            skipped.append(SkippedRule(
                rule_id=rule_id,
                reason="待确认规则，暂不导入",
                source=source,
                sheet=sheet,
                rule_type=rule_type
            ))
            continue

        condition, reason = build_taohua_conditions(row)
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
        prefix = RULE_CODE_PREFIX_MAP.get(rule_type, "TAOHUA")
        rule_code = f"{prefix}-{rule_id}"
        
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
        rule_type_db = RULE_TYPE_MAP.get(cond1, f"{RULE_CATEGORY_MAP.get(rule_type, 'taohua')}_general")
        rule_category = RULE_CATEGORY_MAP.get(rule_type, "taohua")
        
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
                    # 查询所有相关前缀的规则（MySQL语法）
                    prefixes = list(RULE_CODE_PREFIX_MAP.values())
                    if prefixes:
                        conditions = " OR ".join(["rule_code LIKE %s"] * len(prefixes))
                        patterns = [f"{prefix}-%" for prefix in prefixes]
                        cur.execute(f"SELECT rule_code FROM bazi_rules WHERE {conditions}", tuple(patterns))
                        existing_codes = {item["rule_code"] for item in cur.fetchall()}
                else:
                    # 只删除当前类型的规则
                    for prefix in RULE_CODE_PREFIX_MAP.values():
                        cur.execute("DELETE FROM bazi_rules WHERE rule_code LIKE %s", (f"{prefix}-%",))

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
    parser = argparse.ArgumentParser(description="导入桃花算法规则到数据库")
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


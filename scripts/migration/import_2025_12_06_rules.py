#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 2025.12.06算法公式--中午.xlsx 规则到数据库

支持的规则类型:
- 事业: 十神、旺衰、神煞等
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 尝试导入 pandas
try:
    import pandas as pd
except ImportError:
    print("❌ 需要安装 pandas: pip install pandas openpyxl")
    sys.exit(1)

# 导入解析器
from scripts.migration.import_2025_12_03_rules import RuleParser, RULE_TYPE_MAP, GENDER_MAP

XLSX_FILE = os.path.join(PROJECT_ROOT, "docs", "2025.12.06算法公式--中午.xlsx")


def load_excel_rules(xlsx_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """加载Excel规则"""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"文件不存在: {xlsx_path}")
    
    rules_by_sheet = {}
    xls = pd.ExcelFile(xlsx_path)
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        rows = df.to_dict("records")
        rules_by_sheet[sheet_name] = rows
    
    return rules_by_sheet


def analyze_rules(
    xlsx_path: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """分析规则，返回成功解析、失败解析和失败原因统计
    
    Returns:
        (parsed_rules, failed_rules, failure_reasons)
    """
    
    # 加载规则
    rules_by_sheet = load_excel_rules(xlsx_path)
    
    parsed_rules: List[Dict[str, Any]] = []
    failed_rules: List[Dict[str, Any]] = []
    failure_reasons: Dict[str, int] = {}
    
    for sheet_name, rows in rules_by_sheet.items():
        rule_type = RULE_TYPE_MAP.get(sheet_name, sheet_name.lower())
        
        for row in rows:
            rule_id = int(row.get("ID", 0))
            if not rule_id:
                continue
            
            # 解析规则
            result = RuleParser.parse(row, sheet_name)
            
            if not result.success:
                # 保存完整的规则信息
                failed_rule = {
                    "ID": rule_id,
                    "类型": sheet_name,
                    "性别": str(row.get("性别", "无论男女")),
                    "筛选条件1": str(row.get("筛选条件1", "")),
                    "筛选条件2": str(row.get("筛选条件2", "")),
                    "数量": str(row.get("数量", "")) if pd.notna(row.get("数量")) else "",
                    "结果": str(row.get("结果", "")),
                    "解析失败原因": result.reason or "解析失败",
                    "rule_code": f"FORMULA_{sheet_name.upper()}_{rule_id}"
                }
                failed_rules.append(failed_rule)
                
                # 统计失败原因
                reason = result.reason or "解析失败"
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            else:
                # 成功解析的规则
                parsed_rule = {
                    "ID": rule_id,
                    "类型": sheet_name,
                    "筛选条件1": str(row.get("筛选条件1", "")),
                    "筛选条件2": str(row.get("筛选条件2", "")),
                    "conditions": result.conditions,
                    "rule_code": f"FORMULA_{sheet_name.upper()}_{rule_id}"
                }
                parsed_rules.append(parsed_rule)
    
    return parsed_rules, failed_rules, failure_reasons


def main():
    parser = argparse.ArgumentParser(description="分析 2025.12.06算法公式--中午.xlsx 规则")
    parser.add_argument("--xlsx", default=XLSX_FILE, help="Excel文件路径")
    parser.add_argument("--output", default=None, help="输出JSON文件路径（默认：docs/未解析规则_2025_12_06_中午.json）")
    args = parser.parse_args()
    
    print("=" * 60)
    print("分析 2025.12.06算法公式--中午.xlsx 规则")
    print("=" * 60)
    
    try:
        parsed, failed, failure_reasons = analyze_rules(xlsx_path=args.xlsx)
        
        total = len(parsed) + len(failed)
        success_rate = (len(parsed) / total * 100) if total > 0 else 0
        
        print(f"\n✅ 解析完成:")
        print(f"  - 总规则数: {total}")
        print(f"  - 成功解析: {len(parsed)} 条 ({success_rate:.1f}%)")
        print(f"  - 无法解析: {len(failed)} 条 ({100-success_rate:.1f}%)")
        
        if failure_reasons:
            print(f"\n📊 失败原因统计:")
            for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {reason}: {count} 条")
        
        if failed:
            print(f"\n⚠️ 无法解析的规则详情:")
            for item in failed[:10]:  # 只显示前10条
                print(f"  - ID {item.get('ID', '未知')}: {item.get('解析失败原因', '未知')}")
                print(f"    条件: {item.get('筛选条件1', '')} | {item.get('筛选条件2', '')[:60]}...")
            if len(failed) > 10:
                print(f"  ... 还有 {len(failed) - 10} 条")
            
            # 保存未解析规则到JSON文件
            output_file = args.output or os.path.join(PROJECT_ROOT, "docs", "未解析规则_2025_12_06_中午.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "统计": {
                        "总规则数": total,
                        "成功解析": len(parsed),
                        "无法解析": len(failed),
                        "解析成功率": f"{success_rate:.1f}%"
                    },
                    "失败原因统计": failure_reasons,
                    "未解析规则": failed
                }, f, ensure_ascii=False, indent=2)
            print(f"\n📄 未解析规则详情已保存到: {output_file}")
        
        if parsed:
            print(f"\n✅ 成功解析的规则示例 (前3条):")
            for rule in parsed[:3]:
                print(f"\n  ID: {rule['ID']}")
                print(f"  条件: {rule['筛选条件1']} | {rule['筛选条件2'][:60]}...")
                print(f"  解析结果: {json.dumps(rule['conditions'], ensure_ascii=False, indent=4)}")
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 十神命格12.20.xlsx 规则到数据库

规则类型: shishen (十神命格)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 尝试导入 pandas
try:
    import pandas as pd
except ImportError:
    print("❌ 需要安装 pandas: pip install pandas openpyxl")
    sys.exit(1)

# 导入解析器（使用最新的RuleParser）
from scripts.migration.import_2025_12_03_rules import RuleParser, RuleRecord, ParseResult

XLSX_FILE = os.path.join(PROJECT_ROOT, "docs", "upload", "十神命格12.20.xlsx")
OUTPUT_JSON = os.path.join(PROJECT_ROOT, "docs", "未解析规则_十神命格12.20_详细说明.json")

# 规则类型映射（十神命格）
RULE_TYPE = "shishen"

# 性别映射
GENDER_MAP = {
    "无论男女": None,
    "男": "male",
    "女": "female",
}


def load_excel_rules(xlsx_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """加载Excel规则"""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"文件不存在: {xlsx_path}")
    
    rules_by_sheet = {}
    xls = pd.ExcelFile(xlsx_path)
    
    print(f"📖 读取Excel文件: {xlsx_path}")
    print(f"   工作表数量: {len(xls.sheet_names)}")
    print(f"   工作表名称: {', '.join(xls.sheet_names)}")
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        # 清理空行
        df = df.dropna(how='all')
        rows = df.to_dict("records")
        rules_by_sheet[sheet_name] = rows
        print(f"   - {sheet_name}: {len(rows)} 条记录")
    
    return rules_by_sheet


def generate_rule_code(rule_id: int, sheet_name: str = "十神命格") -> str:
    """生成规则编码"""
    # 使用 SHISHEN 作为前缀，避免中文编码问题
    return f"FORMULA_SHISHEN_{rule_id}"


def analyze_unparsed_rule(row: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """分析未解析的规则，生成详细说明"""
    rule_id = row.get("ID", 0)
    cond1 = str(row.get("筛选条件1", "")).strip()
    cond2 = str(row.get("筛选条件2", "")).strip()
    result = str(row.get("结果", "")).strip()
    gender = str(row.get("性别", "无论男女")).strip()
    qty = str(row.get("数量", "")) if pd.notna(row.get("数量")) else ""
    
    # 分析不理解的点
    unclear_points = []
    need_clarification = {}
    
    # 检查条件格式
    if not cond1 or not cond2:
        unclear_points.append("筛选条件为空或不完整")
    
    # 检查条件类型
    supported_cond1_types = ["日柱", "月柱", "年柱", "时柱", "十神", "神煞", "五行", "旺衰", "四柱", "日干", "月令", "天干", "地支", "神煞十神"]
    if cond1 and cond1 not in supported_cond1_types:
        unclear_points.append(f"筛选条件1类型未知: {cond1}")
        need_clarification[cond1] = f"需要确认'{cond1}'是什么类型的条件"
    
    # 检查条件2的格式
    if cond2:
        # 检查是否包含干支
        import re
        ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
        ganzhi_matches = re.findall(ganzhi_pattern, cond2)
        if not ganzhi_matches and cond1 in ["日柱", "月柱", "年柱", "时柱"]:
            unclear_points.append(f"条件2 '{cond2}' 不包含有效的干支组合")
        
        # 检查是否包含十神
        ten_gods = ["比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "偏官", "七杀", "正印", "偏印"]
        has_ten_god = any(tg in cond2 for tg in ten_gods)
        if not has_ten_god and cond1 == "十神":
            unclear_points.append(f"条件2 '{cond2}' 不包含有效的十神名称")
    
    # 歧义说明
    ambiguity = ""
    if unclear_points:
        ambiguity = f"条件格式不明确，无法确定如何匹配。具体问题：{'; '.join(unclear_points)}"
    else:
        ambiguity = reason or "解析器无法识别该条件格式"
    
    # 案例说明（如果有结果文本）
    case_example = {}
    if result:
        # 尝试从结果中提取可能的命格名称
        case_example["结果文本"] = result[:200] + ("..." if len(result) > 200 else "")
    
    return {
        "ID": rule_id,
        "类型": "十神命格",
        "筛选条件1": cond1,
        "筛选条件2": cond2,
        "性别": gender,
        "数量": qty,
        "结果": result[:500] + ("..." if len(result) > 500 else ""),  # 限制长度
        "rule_code": generate_rule_code(rule_id),
        "解析失败原因": reason or "解析失败",
        "不理解点说明": {
            "不理解的点": unclear_points if unclear_points else ["解析器无法识别该条件格式"],
            "需要澄清的概念": need_clarification,
            "歧义说明": ambiguity,
            "案例说明": case_example,
            "解决方案": "需要扩展解析器支持该条件格式，或确认条件的正确表达方式"
        }
    }


def import_rules(
    xlsx_path: str,
    write_db: bool = True,
    dry_run: bool = False,
) -> Tuple[List[RuleRecord], List[Dict[str, Any]], int, int, int]:
    """导入规则
    
    Returns:
        (parsed_rules, unparsed_rules_details, inserted_count, updated_count, total_rules)
    """
    
    # 加载规则
    rules_by_sheet = load_excel_rules(xlsx_path)
    
    parsed_rules: List[RuleRecord] = []
    unparsed_rules: List[Dict[str, Any]] = []
    
    # 计算总规则数
    total_rules = sum(len(rows) for rows in rules_by_sheet.values())
    
    # 处理所有工作表
    for sheet_name, rows in rules_by_sheet.items():
        print(f"\n{'='*60}")
        print(f"处理工作表: {sheet_name}")
        print(f"{'='*60}")
        
        for idx, row in enumerate(rows, 1):
            rule_id = row.get("ID")
            if not rule_id or pd.isna(rule_id):
                print(f"  [{idx}/{len(rows)}] ⚠️  跳过：缺少ID")
                continue
            
            try:
                rule_id = int(rule_id)
            except (ValueError, TypeError):
                print(f"  [{idx}/{len(rows)}] ⚠️  跳过无效ID: {rule_id}")
                continue
            
            # 解析规则
            try:
                result = RuleParser.parse(row, sheet_name)
            except Exception as e:
                print(f"  [{idx}/{len(rows)}] ❌ 规则 {rule_id}: 解析异常 - {e}")
                unparsed_detail = analyze_unparsed_rule(row, f"解析异常: {str(e)}")
                unparsed_rules.append(unparsed_detail)
                continue
            
            if not result.success:
                # 分析未解析的规则
                unparsed_detail = analyze_unparsed_rule(row, result.reason or "解析失败")
                unparsed_rules.append(unparsed_detail)
                print(f"  [{idx}/{len(rows)}] ❌ 规则 {rule_id}: {result.reason or '解析失败'}")
                continue
            
            # 构建规则记录
            rule_code = generate_rule_code(rule_id, sheet_name)
            
            # 提取规则结果
            result_text = str(row.get("结果", "")).strip()
            if pd.isna(row.get("结果")):
                result_text = ""
            
            rule_record = RuleRecord(
                rule_id=rule_id,
                rule_code=rule_code,
                rule_name=f"十神命格规则-{rule_id}",
                rule_type=RULE_TYPE,  # 使用 shishen，不是 formula_shishen
                rule_category="shishen",
                priority=100,
                conditions=result.conditions,
                content={
                    "type": "text",
                    "text": result_text
                },
                description=json.dumps({
                    "筛选条件1": str(row.get("筛选条件1", "")),
                    "筛选条件2": str(row.get("筛选条件2", "")),
                    "性别": str(row.get("性别", "无论男女")),
                    "数量": str(row.get("数量", "")) if pd.notna(row.get("数量")) else "",
                }, ensure_ascii=False),
                source=sheet_name
            )
            parsed_rules.append(rule_record)
            print(f"  [{idx}/{len(rows)}] ✅ 规则 {rule_id}: 解析成功")
    
    # 写入数据库
    inserted_count = 0
    updated_count = 0
    
    if write_db and parsed_rules and not dry_run:
        from server.config.mysql_config import get_mysql_connection, return_mysql_connection
        import time
        
        # 重试连接（最多3次）
        conn = None
        for retry in range(3):
            try:
                conn = get_mysql_connection()
                break
            except Exception as e:
                if retry < 2:
                    print(f"  ⚠️  连接失败，等待5秒后重试 ({retry+1}/3)...")
                    time.sleep(5)
                else:
                    raise
        
        if not conn:
            raise Exception("无法连接到数据库")
        
        try:
            with conn.cursor() as cur:
                # 获取已存在的规则
                existing_codes = set()
                cur.execute("SELECT rule_code FROM bazi_rules WHERE rule_code LIKE 'FORMULA_SHISHEN_%'")
                existing_codes = {item["rule_code"] for item in cur.fetchall()}
                
                insert_sql = """
                    INSERT INTO bazi_rules 
                    (rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                update_sql = """
                    UPDATE bazi_rules SET
                        rule_name = %s,
                        rule_type = %s,
                        rule_category = %s,
                        priority = %s,
                        conditions = %s,
                        content = %s,
                        description = %s,
                        updated_at = NOW()
                    WHERE rule_code = %s
                """
                
                for rule in parsed_rules:
                    if rule.rule_code in existing_codes:
                        # 更新
                        cur.execute(update_sql, (
                            rule.rule_name,
                            rule.rule_type,
                            rule.rule_category,
                            rule.priority,
                            json.dumps(rule.conditions, ensure_ascii=False),
                            json.dumps(rule.content, ensure_ascii=False),
                            rule.description,
                            rule.rule_code
                        ))
                        updated_count += 1
                    else:
                        # 插入
                        cur.execute(insert_sql, (
                            rule.rule_code,
                            rule.rule_name,
                            rule.rule_type,
                            rule.rule_category,
                            rule.priority,
                            json.dumps(rule.conditions, ensure_ascii=False),
                            json.dumps(rule.content, ensure_ascii=False),
                            rule.description,
                            1  # enabled
                        ))
                        inserted_count += 1
                
                conn.commit()
                print(f"\n✅ 数据库操作完成: 新增 {inserted_count} 条, 更新 {updated_count} 条")
        except Exception as e:
            conn.rollback()
            print(f"❌ 数据库操作失败: {e}")
            raise
        finally:
            return_mysql_connection(conn)
    elif dry_run or (not write_db):
        # 预览模式：不连接数据库，只统计
        print(f"\n⚠️  预览模式: 成功解析 {len(parsed_rules)} 条规则")
        print(f"   注意: 实际导入时会检查现有规则，可能部分规则会更新而非新增")
    
    return parsed_rules, unparsed_rules, inserted_count, updated_count, total_rules


def save_unparsed_rules(unparsed_rules: List[Dict[str, Any]], output_path: str, total_rules: int):
    """保存未解析规则到JSON文件"""
    # 统计信息
    parsed_count = total_rules - len(unparsed_rules)
    stats = {
        "总规则数": total_rules,
        "成功解析": parsed_count,
        "无法解析": len(unparsed_rules),
        "解析成功率": f"{parsed_count / total_rules * 100:.1f}%" if total_rules > 0 else "0%"
    }
    
    output_data = {
        "统计": stats,
        "未解析规则详细说明": unparsed_rules,
        "生成时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📝 未解析规则已保存到: {output_path}")
    print(f"   无法解析: {len(unparsed_rules)} 条")


def escape_sql_string(s: str) -> str:
    """转义SQL字符串"""
    if not s:
        return "''"
    # 转义单引号和反斜杠
    s = s.replace('\\', '\\\\').replace("'", "\\'")
    return f"'{s}'"


def generate_sql_file(parsed_rules: List[RuleRecord], sql_path: str):
    """生成SQL文件"""
    sql_statements = []
    sql_statements.append("-- 导入十神命格12.20.xlsx规则")
    sql_statements.append("USE hifate_bazi;")
    sql_statements.append("")
    
    for rule in parsed_rules:
        # 转义JSON字符串
        conditions_json = json.dumps(rule.conditions, ensure_ascii=False)
        content_json = json.dumps(rule.content, ensure_ascii=False)
        description_json = rule.description  # 已经是JSON字符串
        
        sql_statements.append(f"-- 规则 {rule.rule_id}: {rule.rule_name}")
        sql_statements.append("INSERT INTO bazi_rules (rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)")
        sql_statements.append(f"VALUES ({escape_sql_string(rule.rule_code)}, {escape_sql_string(rule.rule_name)}, {escape_sql_string(rule.rule_type)}, {escape_sql_string(rule.rule_category)}, {rule.priority}, {escape_sql_string(conditions_json)}, {escape_sql_string(content_json)}, {escape_sql_string(description_json)}, 1)")
        sql_statements.append("ON DUPLICATE KEY UPDATE")
        sql_statements.append(f"  rule_name = {escape_sql_string(rule.rule_name)},")
        sql_statements.append(f"  rule_type = {escape_sql_string(rule.rule_type)},")
        sql_statements.append(f"  rule_category = {escape_sql_string(rule.rule_category)},")
        sql_statements.append(f"  priority = {rule.priority},")
        sql_statements.append(f"  conditions = {escape_sql_string(conditions_json)},")
        sql_statements.append(f"  content = {escape_sql_string(content_json)},")
        sql_statements.append(f"  description = {escape_sql_string(description_json)},")
        sql_statements.append("  updated_at = NOW();")
        sql_statements.append("")
    
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))
    
    print(f"\n📝 SQL文件已生成: {sql_path}")


def main():
    parser = argparse.ArgumentParser(description='导入十神命格12.20.xlsx规则到数据库')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入数据库')
    parser.add_argument('--xlsx', type=str, default=XLSX_FILE, help='Excel文件路径')
    parser.add_argument('--output', type=str, default=OUTPUT_JSON, help='未解析规则JSON输出路径')
    parser.add_argument('--sql-only', action='store_true', help='只生成SQL文件，不导入数据库')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📥 导入十神命格12.20.xlsx规则")
    print("=" * 60)
    
    if args.dry_run:
        print("\n⚠️  预览模式（不写入数据库）")
    
    try:
        # 导入规则
        parsed_rules, unparsed_rules, inserted_count, updated_count, total_rules = import_rules(
            args.xlsx,
            write_db=not args.sql_only and not args.dry_run,  # sql-only模式不写入数据库
            dry_run=args.dry_run or args.sql_only  # sql-only模式视为dry-run
        )
        
        # 保存未解析规则
        if unparsed_rules:
            save_unparsed_rules(unparsed_rules, args.output, total_rules)
        
        # 输出统计
        total_parsed = len(parsed_rules)
        total_unparsed = len(unparsed_rules)
        
        print("\n" + "=" * 60)
        print("📊 导入统计")
        print("=" * 60)
        print(f"总规则数: {total_rules}")
        print(f"成功解析: {total_parsed} ({total_parsed/total_rules*100:.1f}%)" if total_rules > 0 else "成功解析: 0")
        print(f"无法解析: {total_unparsed} ({total_unparsed/total_rules*100:.1f}%)" if total_rules > 0 else "无法解析: 0")
        
        if not args.dry_run and not args.sql_only:
            print(f"\n数据库操作:")
            print(f"  新增: {inserted_count} 条")
            print(f"  更新: {updated_count} 条")
        
        # 如果只生成SQL文件
        if args.sql_only and parsed_rules:
            sql_path = os.path.join(PROJECT_ROOT, "docs", "import_shishen_12_20_rules.sql")
            generate_sql_file(parsed_rules, sql_path)
        
        print("\n✅ 导入完成!")
        
        # 如果有未解析的规则，提示用户
        if unparsed_rules:
            print(f"\n⚠️  发现 {len(unparsed_rules)} 条无法解析的规则")
            print(f"   详细信息已保存到: {args.output}")
            print(f"   请查看文件并告诉我如何处理这些规则")
        
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Excel 文件转换为规则内容 JSON 格式
支持从 Excel 文件读取规则，转换为 rules_content_example.json 格式

Excel 列格式要求：
- rule_code (必需): 规则编号，如 "MARR-10156"
- content_text (必需): 规则内容文本，如 "注意关注，外来女人争丈夫。"
- content_type (可选): 内容类型，默认为 "description"
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    import pandas as pd
except ImportError:
    print("❌ 错误：需要安装 pandas 库")
    print("   安装命令: pip install pandas openpyxl")
    sys.exit(1)


def excel_to_rules_content_json(
    excel_file: str,
    output_file: str,
    sheet_name: Optional[str] = None,
    rule_code_column: str = "rule_code",
    content_text_column: str = "content_text",
    content_type_column: Optional[str] = "content_type",
    default_content_type: str = "description",
    rule_code_prefix: Optional[str] = "MARR-",
    auto_add_prefix: bool = True
) -> int:
    """
    将 Excel 文件转换为规则内容 JSON 格式
    
    Args:
        excel_file: Excel 文件路径
        output_file: 输出 JSON 文件路径
        sheet_name: 工作表名称（如果为 None，读取第一个工作表）
        rule_code_column: 规则编号列名（默认 "rule_code"）
        content_text_column: 内容文本列名（默认 "content_text"）
        content_type_column: 内容类型列名（默认 "content_type"，可选）
        default_content_type: 默认内容类型（默认 "description"）
    
    Returns:
        转换的规则数量
    """
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel 文件不存在: {excel_file}")
    
    print(f"读取 Excel 文件: {excel_file}")
    
    # 读取 Excel 文件
    try:
        if sheet_name:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        else:
            df = pd.read_excel(excel_file, sheet_name=0)  # 读取第一个工作表
    except Exception as e:
        raise ValueError(f"读取 Excel 文件失败: {e}")
    
    print(f"读取到 {len(df)} 行数据")
    print(f"列名: {list(df.columns)}")
    print()
    
    # 检查必需的列
    if rule_code_column not in df.columns:
        raise ValueError(f"Excel 文件缺少必需的列: {rule_code_column}")
    
    if content_text_column not in df.columns:
        raise ValueError(f"Excel 文件缺少必需的列: {content_text_column}")
    
    # 转换为 JSON 格式
    rules_data = []
    skipped_count = 0
    
    for idx, row in df.iterrows():
        try:
            rule_code = str(row[rule_code_column]).strip()
            content_text = str(row[content_text_column]).strip()
            
            # 跳过空值
            if not rule_code or rule_code == 'nan' or rule_code == 'None':
                print(f"  ⚠️  第 {idx + 2} 行：rule_code 为空，跳过")
                skipped_count += 1
                continue
            
            if not content_text or content_text == 'nan' or content_text == 'None':
                print(f"  ⚠️  第 {idx + 2} 行：content_text 为空，跳过")
                skipped_count += 1
                continue
            
            # 自动添加前缀（如果启用且 rule_code 不包含前缀）
            if auto_add_prefix and rule_code_prefix:
                # 检查是否已经包含前缀
                if not rule_code.startswith(rule_code_prefix):
                    # 如果 rule_code 是纯数字，添加前缀
                    if rule_code.isdigit() or (rule_code.startswith('-') and rule_code[1:].isdigit()):
                        rule_code = rule_code_prefix + rule_code
                    # 如果 rule_code 不包含 "-"，可能是需要添加前缀的格式
                    elif '-' not in rule_code:
                        rule_code = rule_code_prefix + rule_code
            
            # 构建 content 对象
            content = {
                "text": content_text
            }
            
            # 添加 content_type（如果存在）
            if content_type_column and content_type_column in df.columns:
                content_type = row[content_type_column]
                if pd.notna(content_type) and str(content_type).strip():
                    content["type"] = str(content_type).strip()
                else:
                    content["type"] = default_content_type
            else:
                content["type"] = default_content_type
            
            rules_data.append({
                "rule_code": rule_code,
                "content": content
            })
        
        except Exception as e:
            print(f"  ✗ 处理第 {idx + 2} 行失败: {e}")
            skipped_count += 1
    
    # 写入 JSON 文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 转换完成")
    print(f"  成功: {len(rules_data)} 条")
    print(f"  跳过: {skipped_count} 条")
    print(f"  输出文件: {output_file}")
    
    return len(rules_data)


def create_excel_template(output_file: str):
    """
    创建 Excel 模板文件（rule_code 不带前缀，程序会自动添加 MARR-）
    """
    import pandas as pd
    
    # 创建示例数据（rule_code 不带前缀，程序会自动添加 MARR-）
    data = {
        'rule_code': ['10156', '10157', '10158'],  # 不带前缀，程序会自动添加
        'content_text': [
            '注意关注，外来女人争丈夫。',
            '其他规则内容1',
            '其他规则内容2'
        ],
        'content_type': ['description', 'description', 'description']
    }
    
    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False, engine='openpyxl')
    
    print(f"✓ 已创建 Excel 模板文件: {output_file}")
    print(f"  包含列: {list(df.columns)}")
    print(f"  示例数据: {len(df)} 行")
    print(f"  注意：rule_code 列可以不带 'MARR-' 前缀，程序会自动添加")


def main():
    parser = argparse.ArgumentParser(
        description='将 Excel 文件转换为规则内容 JSON 格式'
    )
    parser.add_argument('--mode', choices=['convert', 'template'], required=True,
                       help='操作模式：convert=转换 Excel 到 JSON, template=创建 Excel 模板')
    
    # 转换模式
    parser.add_argument('--excel', type=str, help='Excel 文件路径（convert 模式）')
    parser.add_argument('--output', type=str, help='输出 JSON 文件路径（convert 模式）')
    parser.add_argument('--sheet', type=str, help='工作表名称（可选，默认第一个工作表）')
    parser.add_argument('--rule-code-column', type=str, default='rule_code',
                       help='规则编号列名（默认: rule_code）')
    parser.add_argument('--content-text-column', type=str, default='content_text',
                       help='内容文本列名（默认: content_text）')
    parser.add_argument('--content-type-column', type=str, default='content_type',
                       help='内容类型列名（默认: content_type，可选）')
    parser.add_argument('--default-content-type', type=str, default='description',
                       help='默认内容类型（默认: description）')
    parser.add_argument('--rule-code-prefix', type=str, default='MARR-',
                       help='规则编号前缀（默认: MARR-）')
    parser.add_argument('--no-auto-prefix', action='store_true',
                       help='禁用自动添加前缀（默认会自动添加前缀）')
    
    # 模板模式
    parser.add_argument('--template-output', type=str, help='模板文件路径（template 模式）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Excel 转规则内容 JSON 工具")
    print("=" * 60)
    print()
    
    try:
        if args.mode == 'convert':
            if not args.excel or not args.output:
                print("❌ 错误：convert 模式需要指定 --excel 和 --output 参数")
                return 1
            
            count = excel_to_rules_content_json(
                excel_file=args.excel,
                output_file=args.output,
                sheet_name=args.sheet,
                rule_code_column=args.rule_code_column,
                content_text_column=args.content_text_column,
                content_type_column=args.content_type_column,
                default_content_type=args.default_content_type,
                rule_code_prefix=args.rule_code_prefix,
                auto_add_prefix=not args.no_auto_prefix
            )
            
            print("\n" + "=" * 60)
            print(f"✓ 转换完成，共 {count} 条规则")
            print(f"  使用以下命令导入更新：")
            print(f"  python scripts/batch_update_content_from_json.py --mode import --file {args.output}")
            print("=" * 60)
        
        elif args.mode == 'template':
            if not args.template_output:
                print("❌ 错误：template 模式需要指定 --template-output 参数")
                return 1
            
            create_excel_template(args.template_output)
            
            print("\n" + "=" * 60)
            print("Excel 模板列说明：")
            print("  • rule_code (必需): 规则编号，可以不带前缀（如 '10156'），程序会自动添加 'MARR-'")
            print("  • content_text (必需): 规则内容文本")
            print("  • content_type (可选): 内容类型，默认为 'description'")
            print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())


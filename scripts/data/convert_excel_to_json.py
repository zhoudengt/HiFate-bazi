#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 转 JSON 脚本
将 桃花算法公式.xlsx 转换为 JSON 格式
"""

import sys
import os
import json
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def convert_excel_to_json(excel_path: str, output_path: str = None):
    """
    将 Excel 文件转换为 JSON 格式
    
    Args:
        excel_path: Excel 文件路径
        output_path: 输出 JSON 文件路径，如果为 None 则自动生成
    """
    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在: {excel_path}")
        return False
    
    print(f"📖 读取 Excel 文件: {excel_path}")
    
    # 读取所有工作表
    excel_file = pd.ExcelFile(excel_path)
    sheet_names = excel_file.sheet_names
    print(f"📋 发现 {len(sheet_names)} 个工作表: {', '.join(sheet_names)}")
    
    result = {
        "source_file": os.path.basename(excel_path),
        "sheets": {}
    }
    
    # 遍历每个工作表
    for sheet_name in sheet_names:
        print(f"\n处理工作表: {sheet_name}")
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # 清理数据：去除空行，填充 NaN
        df = df.dropna(how='all')  # 删除完全空白的行
        df = df.fillna('')  # 将 NaN 填充为空字符串
        
        # 转换为字典列表
        records = []
        for idx, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                # 处理数值类型
                if pd.notna(value) and isinstance(value, (int, float)):
                    # 如果是整数，转换为 int
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                record[col] = value
            records.append(record)
        
        result["sheets"][sheet_name] = {
            "columns": list(df.columns),
            "row_count": len(records),
            "data": records
        }
        
        print(f"  ✓ 处理完成: {len(records)} 条记录")
    
    # 确定输出路径
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(excel_path))[0]
        output_path = os.path.join(os.path.dirname(excel_path), f"{base_name}.json")
    
    # 保存 JSON 文件
    print(f"\n💾 保存 JSON 文件: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 转换完成！")
    print(f"   输出文件: {output_path}")
    print(f"   总工作表数: {len(result['sheets'])}")
    print(f"   总记录数: {sum(sheet['row_count'] for sheet in result['sheets'].values())}")
    
    return True


def main():
    """主函数"""
    excel_path = os.path.join(project_root, 'docs', '桃花算法公式.xlsx')
    output_path = os.path.join(project_root, 'docs', '桃花算法公式.json')
    
    print("=" * 60)
    print("Excel 转 JSON 工具")
    print("=" * 60)
    
    success = convert_excel_to_json(excel_path, output_path)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 转换成功！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 转换失败！")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()


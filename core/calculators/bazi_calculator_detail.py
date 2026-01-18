#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.calculators.BaziDetailPrinter import BaziDetailPrinter
from core.calculators.BaziCalculator import BaziCalculator


def main():
    """主方法 - 可直接执行，参数可在代码中修改"""
    import argparse
    from datetime import datetime

    # ========== 可在此处直接修改默认参数 ==========
    DEFAULT_DATE = '1984-03-08'  # 出生日期 (YYYY-MM-DD)
    DEFAULT_TIME = '09:15'  # 出生时间 (HH:MM)
    DEFAULT_GENDER = 'male'  # 性别 (male/female 或 男/女)
    DEFAULT_CURRENT_TIME = None  # 当前时间，None表示使用当前系统时间
    # ============================================
    
    parser = argparse.ArgumentParser(
        description="八字详细计算器 - 包含大运流年",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认参数
  python bazi_calculator_detail.py
  
  # 使用命令行参数
  python bazi_calculator_detail.py --date 1990-05-15 --time 14:30 --gender male
  
  # 指定当前时间（用于计算大运流年）
  python bazi_calculator_detail.py --date 1990-05-15 --time 14:30 --current-time "2024-01-01 12:00"
        """
    )
    
    parser.add_argument("--date", default=DEFAULT_DATE,
                       help=f"出生日期 YYYY-MM-DD (默认: {DEFAULT_DATE})")
    parser.add_argument("--time", default=DEFAULT_TIME,
                       help=f"出生时间 HH:MM (默认: {DEFAULT_TIME})")
    parser.add_argument("--gender", default=DEFAULT_GENDER,
                       choices=["male", "female", "男", "女"],
                       help=f"性别 (默认: {DEFAULT_GENDER})")
    parser.add_argument("--current-time", default=None,
                       help="当前时间 YYYY-MM-DD HH:MM (用于计算大运流年，默认使用系统当前时间)")
    
    args = parser.parse_args()
    
    # 解析当前时间
    current_time = None
    if args.current_time:
        try:
            current_time = datetime.strptime(args.current_time, "%Y-%m-%d %H:%M")
        except ValueError:
            print(f"警告: 当前时间格式错误，使用系统当前时间")
            current_time = datetime.now()
    else:
        current_time = datetime.now()

    print("=" * 60)
    print("八字详细计算器 - 大运流年版本")
    print("=" * 60)
    print(f"出生日期: {args.date}")
    print(f"出生时间: {args.time}")
    print(f"性别: {args.gender}")
    print(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print()
    
    try:
        # 创建八字计算器
        calculator = BaziCalculator(
            solar_date=args.date,
            solar_time=args.time,
            gender=args.gender
        )

        # 创建详细打印器
        printer = BaziDetailPrinter(calculator)

        # 打印详细结果
        printer.print_detailed_result(current_time=current_time)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # 运行主方法
    main()

    # 或者运行测试案例
    # test_specific_case()
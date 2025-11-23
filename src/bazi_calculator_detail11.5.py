#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.tool.BaziDetailPrinter import BaziDetailPrinter
from src.tool.BaziCalculator import BaziCalculator


def main():
    """主方法 - 用于测试和演示"""
    from datetime import datetime

    # 获取命令行参数或使用默认值
    if len(sys.argv) >= 4:
        solar_date = sys.argv[1]
        solar_time = sys.argv[2]
        gender = sys.argv[3]
    else:
        # 默认测试数据
        solar_date = '1991-02-15'
        solar_time = '10:30'
        gender = 'male'

    print(f"计算八字信息: {solar_date} {solar_time} {gender}")

    # 创建八字计算器
    calculator = BaziCalculator(
        solar_date=solar_date,
        solar_time=solar_time,
        gender=gender
    )

    # 创建详细打印器
    printer = BaziDetailPrinter(calculator)

    # 打印详细结果（使用当前时间）
    printer.print_detailed_result(current_time=datetime.now())


if __name__ == "__main__":
    # 运行主方法
    main()

    # 或者运行测试案例
    # test_specific_case()
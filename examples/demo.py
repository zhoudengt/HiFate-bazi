#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bazi_calculator16 import WenZhenBazi

def main():
    """主函数"""
    print("HiFate排盘演示")
    print("=" * 50)

    # 测试案例1：原始案例
    print("\n案例1: 1988年1月7日 08:31:21 (男)")
    bazi1 = WenZhenBazi(
        solar_date='1988-01-07',
        solar_time='08:31:21',
        gender='male'
    )
    bazi1.print_result()

    # 测试案例2：其他日期
    print("\n" + "="*50)
    print("\n案例2: 1990年1月1日 12:00:00 (女)")
    bazi2 = WenZhenBazi(
        solar_date='1990-01-01',
        solar_time='12:00:00',
        gender='female'
    )
    bazi2.print_result()

if __name__ == "__main__":
    main()
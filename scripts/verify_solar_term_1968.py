#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 1968-07-07 06:00 的节气边界计算是否正确

小暑节气边界：若出生时间 < 小暑，月柱为戊午（午月）；若 >= 小暑，月柱为己未（未月）
正确月柱应为戊午（stream 接口显示正确），评测脚本曾显示己未（错误）
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    from lunar_python import Solar, Lunar
    from core.calculators.LunarConverter import LunarConverter

    solar_date = "1968-07-07"
    solar_time = "06:00"
    year, month, day = 1968, 7, 7
    hour, minute = 6, 0

    print(f"=== 验证 {solar_date} {solar_time} 的节气与月柱 ===\n")

    # 1. 使用 LunarConverter（与 BaziService 一致）
    result = LunarConverter.solar_to_lunar(solar_date, solar_time)
    pillars = result["bazi_pillars"]
    month_pillar = f"{pillars['month']['stem']}{pillars['month']['branch']}"
    print(f"[LunarConverter] 月柱: {month_pillar}")

    # 2. 直接使用 lunar_python 获取小暑时刻（用于参考）
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()
    jieqi_table = lunar.getJieQiTable()
    xiaoshu_solar = jieqi_table.get("小暑") if hasattr(jieqi_table, "get") else None
    if xiaoshu_solar is None and hasattr(jieqi_table, "items"):
        for name, obj in jieqi_table.items():
            if name == "小暑":
                xiaoshu_solar = obj
                break

    print()
    if xiaoshu_solar:
        xs_ymd = xiaoshu_solar.toYmd()
        print(f"[lunar_python] 1968 年小暑日期: {xs_ymd}")

    print()
    print(f"出生时间: {solar_date} {solar_time}")
    print(f"期望月柱: 戊午（stream 接口正确值）")
    print(f"实际月柱: {month_pillar}")

    if month_pillar == "戊午":
        print("\n结论: 本地 lunar_python/LunarConverter 计算正确，问题为纯缓存腐化。")
    else:
        print("\n结论: 本地计算与期望不一致，需进一步排查。")

    # 4. 四柱完整输出
    print("\n四柱:", end=" ")
    for k in ["year", "month", "day", "hour"]:
        p = pillars[k]
        print(f"{p['stem']}{p['branch']}", end=" ")
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 lunar_python 是否支持胎神方法
"""

from lunar_python import Solar

# 测试日期
solar = Solar.fromYmd(2025, 1, 15)
lunar = solar.getLunar()

# 测试可能的方法名
possible_methods = [
    'getDayPositionTaiShenDesc',
    'getPositionTaiShen',
    'getDayTaiShen',
    'getTaiShen',
    'getDayPositionTaiShen',
    'getTaiShenDesc',
]

print("=" * 60)
print("测试 lunar_python 胎神方法")
print("=" * 60)

found_method = None
for method_name in possible_methods:
    if hasattr(lunar, method_name):
        method = getattr(lunar, method_name)
        try:
            result = method()
            print(f"✅ {method_name}() = {result}")
            if result and not found_method:
                found_method = method_name
        except Exception as e:
            print(f"❌ {method_name}() 存在但调用失败: {e}")
    else:
        print(f"❌ {method_name}() 不存在")

# 查看所有包含 Position 或 Tai 的方法
print("\n" + "=" * 60)
print("所有包含 Position 或 Tai 的方法：")
print("=" * 60)
for attr in dir(lunar):
    if 'Position' in attr or 'Tai' in attr.lower() or '胎' in attr:
        print(f"  - {attr}")

# 查看所有 getDay 开头的方法
print("\n" + "=" * 60)
print("所有 getDay 开头的方法：")
print("=" * 60)
day_methods = [attr for attr in dir(lunar) if attr.startswith('getDay')]
for method in sorted(day_methods):
    print(f"  - {method}")

if found_method:
    print(f"\n✅ 找到胎神方法: {found_method}")
    print(f"示例结果: {getattr(lunar, found_method)()}")
else:
    print("\n❌ 未找到胎神方法，需要使用备用计算方案")


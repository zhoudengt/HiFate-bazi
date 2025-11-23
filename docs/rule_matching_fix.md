# 规则匹配问题修复说明

## 问题描述
执行 `bazi_calculator.py` 时，打印出的规则命中与未命中加起来不够 462 条。

## 问题原因
`bazi_calculator.py` 中的 `match_rules` 方法只匹配了指定的 `rule_types` 列表中的规则类型。数据库中有 28 条规则的规则类型不在该列表中：

1. **marriage_general**: 27 条规则
2. **taohua_general**: 1 条规则

因此这 28 条规则不会被匹配和打印，导致总数只有 434 条（462 - 28 = 434）。

## 修复方案
在 `src/bazi_calculator.py` 的 `match_rules` 方法调用中，添加缺失的规则类型：

```python
matched_rules, unmatched_rules = bazi.match_rules(
    rule_types=[
        # ... 原有规则类型 ...
        "marriage_general",  # 添加婚姻通用规则类型
        "taohua_general",    # 添加桃花通用规则类型
        "rizhu_gender_dynamic"
    ]
)
```

## 修复结果
- ✅ 所有 462 条规则都会被匹配
- ✅ 命中规则数 + 未命中规则数 = 462 条
- ✅ 所有规则类型都已包含在 `rule_types` 列表中

## 规则类型统计（修复后）
- marriage_day_pillar: 138 条
- marriage_day_branch: 83 条
- marriage_ten_gods: 52 条
- marriage_stem_pattern: 29 条
- **marriage_general: 27 条** ← 已添加
- marriage_bazi_pattern: 23 条
- marriage_day_stem: 21 条
- marriage_branch_pattern: 18 条
- marriage_deity: 15 条
- marriage_month_branch: 12 条
- marriage_nayin: 11 条
- marriage_year_branch: 9 条
- marriage_year_stem: 6 条
- marriage_element: 5 条
- marriage_hour_pillar: 4 条
- marriage_year_pillar: 4 条
- marriage_lunar_birthday: 2 条
- marriage_luck_cycle: 1 条
- marriage_year_event: 1 条
- **taohua_general: 1 条** ← 已添加
- **总计: 462 条**

## 验证方法
运行以下命令验证所有规则都会被匹配：

```python
from src.bazi_calculator import WenZhenBazi

bazi = WenZhenBazi(
    solar_date='1984-03-08',
    solar_time='09:15',
    gender='male'
)

matched, unmatched = bazi.match_rules(rule_types=[...])  # 包含所有规则类型
print(f"匹配: {len(matched)} 条")
print(f"未匹配: {len(unmatched)} 条")
print(f"总计: {len(matched) + len(unmatched)} 条")  # 应该等于 462
```


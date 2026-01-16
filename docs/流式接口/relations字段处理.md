# relations 字段处理规范

## 问题描述

底层计算的 relations（岁运并临、天克地冲、天合地合）是正确的，但在 input_data 中没有正确关联到大运。

## 数据流转

```
底层计算 (BaziCalculator)
  ↓ relations 字段正确
liunian_sequence (包含 relations)
  ↓ 筛选有 relations 的流年
special_liunians (添加 dayun_step)
  ↓ 组织到大运
build_enhanced_dayun_structure
  ↓ 添加到 input_data
formatted_data
```

## 关键修复点

### 1. add_liunian_metadata

**位置**: `server/utils/dayun_liunian_helper.py`

**修复**: 显式保留 relations、dayun_step、dayun_ganzhi 字段

```python
# ⚠️ 关键：确保保留 relations 字段
if 'relations' not in liunian_copy:
    liunian_copy['relations'] = liunian.get('relations', [])
```

### 2. clean_liunian_data

**位置**: `server/api/v1/general_review_analysis.py`

**修复**: 确保 relations 字段不被移除

```python
# ⚠️ 关键：确保 relations 和 dayun_step 字段被保留
if 'relations' not in cleaned:
    cleaned['relations'] = liunian.get('relations', [])
```

## 验证方法

检查 input_data 中的流年是否包含 relations：

```python
for dayun in input_data['dayun_liunian']['key_dayuns']:
    for liunian in dayun['liunians']:
        assert 'relations' in liunian  # 必须包含
        assert 'dayun_step' in liunian  # 必须包含
```

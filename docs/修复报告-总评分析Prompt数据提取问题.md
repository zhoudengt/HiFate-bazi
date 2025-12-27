# 修复报告：总评分析 Prompt 数据提取问题

## 修复日期
2025-01-XX

## 问题描述

### 问题1：特殊流年数据提取路径错误
- **现象**：Coze Bot 输出"无特殊天克地冲、天合地合等特殊流年"
- **原因**：代码从 `guanjian` 顶层直接获取特殊流年字段，但实际数据存储在 `dayun_liunians` 的每个大运分组中
- **影响**：特殊流年数据无法传递给 Coze Bot，导致输出不完整

### 问题2：喜忌数据可能不完整
- **现象**：输出中只提到"喜神五行水、金"，没有提到忌神五行
- **原因**：如果忌神数据为空，代码不会输出任何信息，Coze Bot 无法判断是数据缺失还是确实为空
- **影响**：喜忌信息不完整，不符合提示词要求

## 修复内容

### 修复1：特殊流年数据提取逻辑

**修复位置**：`server/api/v1/general_review_analysis.py` 第1692-1770行

**修复前**：
```python
# ❌ 错误：从顶层获取（不存在）
tiankedi_chong = guanjian.get('tiankedi_chong', [])  # 返回 []
```

**修复后**：
```python
# ✅ 正确：从 dayun_liunians 中提取并合并
dayun_liunians = guanjian.get('dayun_liunians', {})
tiankedi_chong = []
tianhedi_he = []
suiyun_binglin = []
other_liunian = []

# 遍历所有大运分组，合并特殊流年
for dayun_step, dayun_data in dayun_liunians.items():
    if isinstance(dayun_data, dict):
        tiankedi_chong.extend(dayun_data.get('tiankedi_chong', []))
        tianhedi_he.extend(dayun_data.get('tianhedi_he', []))
        suiyun_binglin.extend(dayun_data.get('suiyun_binglin', []))
        other_liunian.extend(dayun_data.get('other', []))
```

**改进点**：
1. ✅ 正确从 `dayun_liunians` 中提取数据
2. ✅ 合并所有大运的特殊流年
3. ✅ 添加格式化失败时的降级方案（至少显示年份和干支）
4. ✅ 添加日志记录，便于调试

### 修复2：喜忌数据完整性

**修复位置**：`server/api/v1/general_review_analysis.py` 第1778-1815行

**修复前**：
```python
# ❌ 如果数据为空，不输出任何信息
if xishen_shishen:
    prompt_lines.append(f"喜用神（十神）：{'、'.join(xishen_shishen)}")
# 如果为空，不输出
```

**修复后**：
```python
# ✅ 即使数据为空也明确标注
if xishen_shishen:
    prompt_lines.append(f"喜用神（十神）：{'、'.join(xishen_shishen)}")
else:
    prompt_lines.append("喜用神（十神）：无")

if jishen_wuxing:
    prompt_lines.append(f"忌神五行：{'、'.join(jishen_wuxing)}")
else:
    prompt_lines.append("忌神五行：无")
```

**改进点**：
1. ✅ 即使数据为空也明确标注"无"
2. ✅ 确保 Coze Bot 能看到完整的喜忌信息
3. ✅ 添加日志记录，便于调试

## 修复效果

### 修复前
- 特殊流年：输出"无特殊流年"（数据未传递）
- 喜忌数据：只显示有数据的部分，缺失部分不显示

### 修复后
- 特殊流年：正确提取并显示所有特殊流年（天克地冲、天合地合、岁运并临等）
- 喜忌数据：完整显示喜神和忌神信息，即使为空也明确标注

## 验证方法

### 1. 使用调试接口验证

```bash
curl -X POST http://localhost:8001/api/v1/general-review/debug \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-01-15",
    "solar_time": "12:00",
    "gender": "male"
  }'
```

检查返回的 `input_data`：
- `guanjian_dayun.dayun_liunians` - 应包含特殊流年数据
- `zhongsheng_tidian.jishen.wuxing` - 应包含忌神五行（可能为空列表）

### 2. 检查日志输出

修复后，日志中应显示：
```
[Prompt构建] 特殊流年统计: 天克地冲=X, 天合地合=X, 岁运并临=X, 其他=X
[Prompt构建] 喜忌数据: 喜神十神=X, 喜神五行=X, 忌神十神=X, 忌神五行=X
```

### 3. 验证 Prompt 内容

在 `build_general_review_prompt` 函数中添加临时日志，输出构建的 prompt 内容，检查：
- 是否包含特殊流年数据（天克地冲、天合地合、岁运并临）
- 是否包含完整的喜忌数据（喜神和忌神，即使为空也标注"无"）

## 测试建议

1. **测试特殊流年提取**：
   - 使用包含特殊流年的生辰数据测试
   - 验证 prompt 中是否包含特殊流年信息
   - 验证 Coze Bot 输出是否包含特殊流年分析

2. **测试喜忌数据**：
   - 使用不同生辰测试
   - 验证 prompt 中是否包含完整的喜忌信息
   - 验证即使数据为空也明确标注"无"

3. **端到端测试**：
   - 调用总评分析接口
   - 验证 Coze Bot 输出是否符合提示词要求
   - 验证特殊流年和喜忌数据是否完整

## 相关文件

- `server/api/v1/general_review_analysis.py` - 修复文件
- `docs/问题分析-总评分析Prompt与输出不匹配.md` - 问题分析报告

## 注意事项

1. **数据格式**：确保 `dayun_liunians` 的数据格式符合预期（字典，每个大运分组包含 `tiankedi_chong`、`tianhedi_he` 等字段）
2. **降级方案**：如果 `format_special_liunians_for_prompt` 格式化失败，至少显示年份和干支
3. **日志记录**：添加了详细的日志，便于排查问题


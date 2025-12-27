# 问题分析：总评分析 Prompt 与输出不匹配

## 问题描述

用户提供的 Coze Bot 提示词要求：
1. **特殊流年必须列出**：必须列出所有特殊流年，优先展示天克地冲、天合地合、岁运并临
2. **喜忌数据必须分离**：喜神和忌神必须分开分析，喜神五行和忌神五行必须分开列出

但实际输出：
1. **特殊流年显示"无"**：输出显示"无特殊天克地冲、天合地合等特殊流年"
2. **喜忌数据不完整**：只提到了"喜神五行水、金"，没有提到忌神五行

## 问题根因分析

### 问题1：特殊流年数据提取错误

#### 数据存储位置

在 `build_general_review_input_data` 函数中（第893行），特殊流年数据被组织为按大运分组的字典：

```python
'guanjian_dayun': {
    'dayun_liunians': organize_special_liunians_by_dayun(special_liunians, dayun_sequence),  # 按大运分组
    ...
}
```

`organize_special_liunians_by_dayun` 返回的数据结构：
```python
{
    dayun_step: {
        'dayun_info': {...},
        'tiankedi_chong': [...],  # 天克地冲
        'tianhedi_he': [...],     # 天合地合
        'suiyun_binglin': [...],  # 岁运并临
        'other': [...]            # 其他
    }
}
```

#### Prompt 构建错误

在 `build_general_review_prompt` 函数中（第1697-1728行），代码尝试从 `guanjian` 字典的顶层直接获取特殊流年：

```python
# ❌ 错误：从 guanjian 顶层获取（这些字段不存在）
tiankedi_chong = guanjian.get('tiankedi_chong', [])  # 返回空列表 []
tianhedi_he = guanjian.get('tianhedi_he', [])        # 返回空列表 []
suiyun_binglin = guanjian.get('suiyun_binglin', [])  # 返回空列表 []
other_liunian = guanjian.get('other_liunian', [])    # 返回空列表 []
```

**实际数据位置**：特殊流年数据存储在 `guanjian['dayun_liunians']` 中，需要从每个大运分组中提取。

#### 正确的提取方式

应该从 `dayun_liunians` 中提取并合并所有大运的特殊流年：

```python
# ✅ 正确：从 dayun_liunians 中提取
dayun_liunians = guanjian.get('dayun_liunians', {})
tiankedi_chong = []
tianhedi_he = []
suiyun_binglin = []
other_liunian = []

for dayun_step, dayun_data in dayun_liunians.items():
    tiankedi_chong.extend(dayun_data.get('tiankedi_chong', []))
    tianhedi_he.extend(dayun_data.get('tianhedi_he', []))
    suiyun_binglin.extend(dayun_data.get('suiyun_binglin', []))
    other_liunian.extend(dayun_data.get('other', []))
```

### 问题2：喜忌数据可能为空或不完整

#### 数据提取逻辑

在 `build_general_review_prompt` 函数中（第1736-1759行），喜忌数据的提取逻辑看起来是正确的：

```python
# 喜神（独立）
xishen = zhongsheng.get('xishen', {})
if xishen:
    xishen_shishen = xishen.get('shishen', [])
    xishen_wuxing = xishen.get('wuxing', [])
    ...

# 忌神（独立）
jishen = zhongsheng.get('jishen', {})
if jishen:
    jishen_shishen = jishen.get('shishen', [])
    jishen_wuxing = jishen.get('wuxing', [])
    ...
```

#### 可能的问题

1. **数据源问题**：`extract_xi_ji_data` 函数可能没有正确提取忌神五行数据
2. **数据为空**：如果 `jishen_wuxing` 为空列表，prompt 中就不会包含忌神五行信息
3. **数据格式问题**：数据可能以不同的格式存储，导致提取失败

#### 需要检查的数据流

1. `xishen_jishen_result` 是否正确传递到 `build_general_review_input_data`
2. `extract_xi_ji_data` 函数是否正确提取了忌神五行
3. `zhongsheng_tidian` 中的 `jishen` 字段是否包含 `wuxing` 列表

## 问题影响

### 1. 特殊流年缺失

- **影响**：Coze Bot 无法看到特殊流年数据，导致输出"无特殊流年"
- **严重程度**：高（提示词要求必须列出所有特殊流年）

### 2. 喜忌数据不完整

- **影响**：Coze Bot 无法看到完整的喜忌信息，导致输出不完整
- **严重程度**：中（提示词要求喜忌必须分离）

## 数据流分析

### 特殊流年数据流

```
1. 统一接口获取特殊流年
   ↓
2. build_general_review_input_data 组织数据
   - organize_special_liunians_by_dayun() → dayun_liunians（按大运分组）
   ↓
3. build_general_review_prompt 提取数据
   - ❌ 错误：从 guanjian 顶层获取（不存在）
   - ✅ 应该：从 dayun_liunians 中提取并合并
   ↓
4. Prompt 传递给 Coze Bot
   - 特殊流年数据为空 → Bot 输出"无特殊流年"
```

### 喜忌数据流

```
1. 统一接口获取喜忌数据
   ↓
2. build_general_review_input_data 提取数据
   - extract_xi_ji_data() → 分离的喜忌结构
   ↓
3. build_general_review_prompt 格式化数据
   - 分别提取喜神和忌神
   ↓
4. Prompt 传递给 Coze Bot
   - 如果忌神数据为空 → Bot 不输出忌神信息
```

## 验证方法

### 1. 验证特殊流年数据

使用调试接口 `/general-review/debug` 检查：

```bash
curl -X POST http://localhost:8001/api/v1/general-review/debug \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-01-15",
    "solar_time": "12:00",
    "gender": "male"
  }'
```

检查返回的 `input_data.guanjian_dayun.dayun_liunians` 是否包含特殊流年数据。

### 2. 验证喜忌数据

检查返回的 `input_data.zhongsheng_tidian`：
- `xishen.wuxing` 是否包含喜神五行列表
- `jishen.wuxing` 是否包含忌神五行列表

### 3. 验证 Prompt 内容

在 `build_general_review_prompt` 函数中添加日志，输出构建的 prompt 内容，检查：
- 是否包含特殊流年数据
- 是否包含完整的喜忌数据（喜神和忌神）

## 修复建议

### 修复1：特殊流年数据提取

在 `build_general_review_prompt` 函数中，修改特殊流年数据的提取逻辑：

```python
# 从 dayun_liunians 中提取并合并所有大运的特殊流年
dayun_liunians = guanjian.get('dayun_liunians', {})
tiankedi_chong = []
tianhedi_he = []
suiyun_binglin = []
other_liunian = []

for dayun_step, dayun_data in dayun_liunians.items():
    tiankedi_chong.extend(dayun_data.get('tiankedi_chong', []))
    tianhedi_he.extend(dayun_data.get('tianhedi_he', []))
    suiyun_binglin.extend(dayun_data.get('suiyun_binglin', []))
    other_liunian.extend(dayun_data.get('other', []))
```

### 修复2：喜忌数据验证

在 `extract_xi_ji_data` 函数中添加日志，验证：
- 是否成功提取了忌神五行
- 如果为空，记录警告日志

在 `build_general_review_prompt` 函数中添加验证：
- 如果 `jishen_wuxing` 为空，记录警告日志
- 确保 prompt 中明确标注"忌神五行：无"（如果确实为空）

## 总结

**核心问题**：
1. **特殊流年数据提取路径错误**：代码从错误的路径提取特殊流年数据，导致数据为空
2. **喜忌数据可能不完整**：需要验证数据源和提取逻辑

**修复优先级**：
1. **高优先级**：修复特殊流年数据提取逻辑（直接影响输出）
2. **中优先级**：验证和修复喜忌数据提取逻辑（确保数据完整）


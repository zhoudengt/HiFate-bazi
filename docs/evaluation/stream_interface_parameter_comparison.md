# 流式接口给大模型参数差异对比分析

> 基于 Git commit 历史分析各流式接口构建大模型输入参数的差异

---

## 📋 一、核心发现摘要

### 1.1 格式化方式分类

各流式接口在给大模型传递参数时，使用了**三种不同的格式化方式**：

| 格式化方式 | 使用接口 | 格式类型 | 函数位置 |
|-----------|---------|---------|---------|
| **JSON字符串** | 事业财富、感情婚姻、子女学习、总评分析 | JSON | `server/utils/prompt_builders.py` |
| **自然语言Prompt** | 健康分析 | 文本 | `server/utils/prompt_builders.py` |
| **直接字符串拼接** | 五行占比、喜神忌神 | 自定义 | 接口代码内 |

### 1.2 关键 Commit 说明

- **`68561fc`**: 统一 debug 接口返回 `input_data`，确保评测脚本与流式接口参数一致
- **`aa7180f`**: 对齐测试接口与流式接口的数据获取方式
- **`6b5a164`**: 取消 `format_input_data_for_coze` 中的大运数量限制
- **`7cc9dde`**: 取消流年和大运数量限制，显示所有特殊流年

---

## 🔍 二、各接口详细对比

### 2.1 事业财富分析 (`career-wealth/stream`)

**格式化函数**: `format_career_wealth_input_data_for_coze()`

**位置**: `server/utils/prompt_builders.py`

**格式**: JSON 字符串

**代码**:
```python
# server/api/v1/career_wealth_analysis.py
formatted_data = format_career_wealth_input_data_for_coze(input_data)
# 返回: JSON 字符串，用于 Coze Bot 的 {{input}} 占位符
```

**特点**:
- ✅ 使用统一的格式化函数
- ✅ 数据与模板分离（模板在 Coze Bot System Prompt 中）
- ✅ 支持引用优化，减少 Token 消耗

**Commit 变更**:
- `68561fc`: debug 接口不再返回 `formatted_data`，只返回 `input_data`

---

### 2.2 感情婚姻分析 (`bazi/marriage-analysis/stream`)

**格式化函数**: `format_marriage_input_data_for_coze()`

**位置**: `server/utils/prompt_builders.py`

**格式**: JSON 字符串

**代码**:
```python
# server/api/v1/marriage_analysis.py
formatted_data = format_marriage_input_data_for_coze(input_data)
```

**特点**:
- ✅ 与事业财富接口使用相同的格式化方式（JSON）
- ✅ 数据结构类似，但场景特定层不同

**差异点**:
- `input_data` 结构不同：
  - 事业财富: `mingpan_shiye_caifu_zonglun`, `shiye_xing_gong`, `caifu_xing_gong`
  - 感情婚姻: `mingpan_zonglun`, `peiou_tezheng`, `ganqing_zoushi`

---

### 2.3 子女学习分析 (`children-study/stream`)

**格式化函数**: `format_children_study_input_data_for_coze()`

**位置**: `server/utils/prompt_builders.py`

**格式**: JSON 字符串

**代码**:
```python
# server/api/v1/children_study_analysis.py
formatted_data = format_children_study_input_data_for_coze(input_data)
```

**特点**:
- ✅ 与事业财富、感情婚姻接口使用相同的格式化方式（JSON）

---

### 2.4 总评分析 (`general-review/stream`)

**格式化函数**: `format_general_review_input_data_for_coze()`

**位置**: `server/utils/prompt_builders.py`

**格式**: JSON 字符串

**代码**:
```python
# server/api/v1/general_review_analysis.py
formatted_data = format_general_review_input_data_for_coze(input_data)
```

**特点**:
- ✅ 与事业财富、感情婚姻、子女学习接口使用相同的格式化方式（JSON）

**Commit 变更**:
- `6b5a164`: 取消 `format_input_data_for_coze` 中的大运数量限制
  ```python
  # 变更前: key_dayuns[:5]  # 限制5个大运
  # 变更后: key_dayuns      # 不限制，显示所有包含特殊流年的大运
  ```

---

### 2.5 健康分析 (`health/stream`)

**格式化函数**: `build_health_prompt()`

**位置**: `server/utils/prompt_builders.py`

**格式**: 自然语言 Prompt（文本字符串）

**代码**:
```python
# server/api/v1/health_analysis.py
prompt = build_health_prompt(input_data)
# 返回: 完整的自然语言提示词字符串
```

**特点**:
- ⚠️ **与其他接口不同**：使用自然语言格式，而非 JSON
- ✅ Prompt 结构更灵活，适合复杂分析场景
- ✅ 包含详细的格式化说明和占位符提示

**差异点**:
- 其他接口：发送 JSON 数据，模板在 Coze Bot System Prompt 中
- 健康分析：发送完整的自然语言 Prompt，包含所有指令

**Commit 变更**:
- `68561fc`: debug 接口不再返回 `prompt`，只返回 `input_data`

---

### 2.6 五行占比分析 (`bazi/wuxing-proportion/stream`)

**格式化函数**: `WuxingProportionService.build_llm_prompt()`

**位置**: `server/services/wuxing_proportion_service.py`

**格式**: 自定义格式（文本字符串）

**代码**:
```python
# server/api/v1/wuxing_proportion.py
prompt = WuxingProportionService.build_llm_prompt(proportion_data)
# 返回: 自定义格式的提示词字符串
```

**特点**:
- ⚠️ **与其他接口不同**：使用自定义格式化函数，非统一模块
- ⚠️ 格式化逻辑在 Service 层，而非 `prompt_builders.py`

---

### 2.7 喜神忌神分析 (`bazi/xishen-jishen/stream`)

**格式化方式**: 直接在代码中构建字符串

**位置**: `server/api/v1/xishen_jishen.py`

**格式**: 自定义格式（文本字符串）

**代码**:
```python
# server/api/v1/xishen_jishen.py
prompt = f"""请根据以下八字命理信息，生成详细的喜神忌神分析：

十神命格：{mingge_text}
喜神五行：{xi_elements_text}
忌神五行：{ji_elements_text}
旺衰状态：{data.get('wangshuai', '未知')}
总分：{data.get('total_score', 0)}分

请基于这些信息，生成详细的命理分析内容。"""
```

**特点**:
- ⚠️ **与其他接口不同**：直接在接口代码中构建 Prompt
- ⚠️ 未使用统一的格式化函数

---

### 2.8 每日运势 (`daily-fortune-calendar/stream`)

**格式化方式**: `json.dumps()` 直接序列化

**位置**: `server/api/v1/daily_fortune_calendar.py`

**格式**: JSON 字符串

**代码**:
```python
# server/api/v1/daily_fortune_calendar.py
formatted_data = json.dumps(response_data, ensure_ascii=False)
```

**特点**:
- ⚠️ **与其他接口不同**：直接使用 `json.dumps()`，未经过专门的格式化函数
- ⚠️ 数据结构可能与其他接口不一致

---

## 📊 三、参数构建流程对比

### 3.1 统一的接口（JSON 格式）

**流程**:
```
获取基础数据 → 构建 input_data → 格式化 formatted_data (JSON) → 传递给大模型
```

**接口**: 事业财富、感情婚姻、子女学习、总评分析

**示例**:
```python
# 1. 构建 input_data
input_data = build_input_data_from_result(...)

# 2. 格式化 formatted_data
formatted_data = format_*_input_data_for_coze(input_data)

# 3. 传递给大模型
llm_service.stream_analysis(formatted_data)
```

### 3.2 健康分析（自然语言格式）

**流程**:
```
获取基础数据 → 构建 input_data → 构建 prompt (自然语言) → 传递给大模型
```

**示例**:
```python
# 1. 构建 input_data
input_data = build_health_input_data(...)

# 2. 构建 prompt
prompt = build_health_prompt(input_data)

# 3. 传递给大模型
llm_service.stream_analysis(prompt)
```

### 3.3 其他接口（自定义格式）

**流程**:
```
获取基础数据 → 构建自定义格式 prompt → 传递给大模型
```

**接口**: 五行占比、喜神忌神、每日运势

---

## 🔄 四、Commit 变更影响分析

### 4.1 Commit `68561fc`: 统一 debug 接口返回格式

**变更前**:
```python
# debug 接口返回 formatted_data/prompt
return {
    "success": True,
    "formatted_data": formatted_data,  # 或 "prompt": prompt
    ...
}
```

**变更后**:
```python
# debug 接口只返回 input_data
return {
    "success": True,
    "input_data": input_data,  # 评测脚本自己构建 formatted_data/prompt
    ...
}
```

**影响**:
- ✅ 确保评测脚本与流式接口使用**相同的格式化函数**
- ✅ 消除了 debug 接口和流式接口之间参数不一致的风险

### 4.2 Commit `aa7180f`: 对齐数据获取方式

**变更内容**:
- 测试接口统一使用 `BaziDataService.get_fortune_data()` 获取大运/流年/特殊流年
- 确保测试接口和流式接口使用相同的默认配置（`DEFAULT_DAYUN_MODE`, `DEFAULT_TARGET_YEARS`）

**影响**:
- ✅ 确保 `input_data` 构建时使用的数据源一致
- ✅ 解决了评测脚本 `input_data` 与流式接口不一致的问题

### 4.3 Commit `6b5a164` & `7cc9dde`: 取消数量限制

**变更内容**:
- 取消大运数量限制（`key_dayuns[:5]` → `key_dayuns`）
- 取消流年数量限制，显示所有特殊流年

**影响**:
- ✅ 更完整的数据传递给大模型
- ✅ 但可能增加 Token 消耗

---

## ✅ 五、一致性验证

### 5.1 格式化函数一致性

| 接口 | 格式化函数 | 一致性 |
|------|-----------|--------|
| 事业财富 | `format_career_wealth_input_data_for_coze()` | ✅ |
| 感情婚姻 | `format_marriage_input_data_for_coze()` | ✅ |
| 子女学习 | `format_children_study_input_data_for_coze()` | ✅ |
| 总评分析 | `format_general_review_input_data_for_coze()` | ✅ |
| 健康分析 | `build_health_prompt()` | ⚠️ 不同格式 |
| 五行占比 | `WuxingProportionService.build_llm_prompt()` | ❌ 未统一 |
| 喜神忌神 | 直接字符串拼接 | ❌ 未统一 |
| 每日运势 | `json.dumps()` | ❌ 未统一 |

### 5.2 input_data 构建一致性

| 接口 | 构建函数 | 一致性 |
|------|----------|--------|
| 事业财富 | `build_input_data_from_result()` | ✅ |
| 感情婚姻 | `build_input_data_from_result()` | ✅ |
| 子女学习 | `build_input_data_from_result()` | ✅ |
| 总评分析 | `build_input_data_from_result()` | ✅ |
| 健康分析 | `build_health_input_data()` | ⚠️ 不同函数 |

---

## 📝 六、建议改进

### 6.1 统一格式化方式

**问题**: 健康分析、五行占比、喜神忌神、每日运势使用不同的格式化方式

**建议**:
1. **健康分析**: 考虑迁移到 JSON 格式（如果 Coze Bot 支持）
2. **五行占比**: 提取格式化函数到 `prompt_builders.py`
3. **喜神忌神**: 提取格式化函数到 `prompt_builders.py`
4. **每日运势**: 使用统一的格式化函数

### 6.2 统一 input_data 构建

**问题**: 健康分析使用 `build_health_input_data()`，其他接口使用 `build_input_data_from_result()`

**建议**: 考虑将健康分析的 `input_data` 构建也迁移到 `build_input_data_from_result()`，使用配置化的格式定义

### 6.3 文档完善

**建议**: 为每个流式接口添加文档说明：
- 使用的格式化函数
- 格式化后的数据格式
- Token 消耗估算

---

## 📚 七、参考 Commit 列表

| Commit ID | 说明 | 影响接口 |
|-----------|------|---------|
| `68561fc` | 统一 debug 接口返回 input_data | 所有分析接口 |
| `aa7180f` | 对齐测试接口与流式接口的数据获取方式 | 所有分析接口 |
| `6b5a164` | 取消 format_input_data_for_coze 中的大运数量限制 | 总评分析 |
| `7cc9dde` | 取消流年和大运数量限制 | 所有分析接口 |
| `f252dd2` | 统一所有流年大运接口的 relations 字段 | 所有分析接口 |

---

**文档版本**: v1.0  
**最后更新**: 2024年  
**基于 Commit**: `68561fc`, `aa7180f`, `6b5a164`, `7cc9dde`, `f252dd2`
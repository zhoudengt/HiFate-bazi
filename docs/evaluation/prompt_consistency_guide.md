# 评测脚本与流式接口 Prompt 一致性指南

## 📋 核心原则

**评测脚本使用的 prompt 必须与生产环境流式接口传给大模型的 prompt 完全一致。**

只有这样，评测结果才能真实反映生产环境流式接口的效果。

---

## ✅ 已完成的修改

### 1. 健康分析 (`/health/debug`)
- ✅ Debug 接口返回完整的 `prompt`（不只是前500字符）
- ✅ 使用与流式接口完全相同的逻辑：`build_health_input_data()` + `build_health_prompt()`
- ✅ 配置已更新：`HEALTH_ANALYSIS_TEST = "/health/debug"`

### 2. 婚姻分析 (`/bazi/marriage-analysis/debug`)
- ✅ Debug 接口使用与流式接口完全相同的逻辑：`extract_marriage_analysis_data()` → `format_input_data_for_coze()`
- ✅ 配置已更新：`MARRIAGE_ANALYSIS_TEST = "/bazi/marriage-analysis/debug"`

### 3. 总评分析 (`/general-review/debug`)
- ✅ Debug 接口使用与流式接口完全相同的逻辑
- ✅ 配置已更新：`GENERAL_REVIEW_TEST = "/general-review/debug"`

### 4. 子女学习 (`/children-study/debug`)
- ✅ Debug 接口使用与流式接口完全相同的逻辑
- ✅ 配置已更新：`CHILDREN_STUDY_TEST = "/children-study/debug"`

### 5. 事业财富 (`/career-wealth/debug`)
- ✅ 已创建 debug 接口，调用 test 接口的逻辑（test 接口已与流式接口一致）
- ✅ 配置已更新：`CAREER_WEALTH_TEST = "/career-wealth/debug"`

### 6. 其他接口（已确认一致）
- ✅ `wuxing_proportion` - test 接口与流式接口使用相同逻辑
- ✅ `xishen_jishen` - test 接口与流式接口使用相同逻辑
- ✅ `daily_fortune_calendar` - test 接口与流式接口使用相同逻辑

---

## 🔍 验证方法

### 方法1：使用验证脚本

```bash
# 验证健康分析接口
python3 scripts/evaluation/verify_prompt_consistency.py \
  --scene health \
  --solar-date 1990-01-01 \
  --solar-time 12:00 \
  --gender male

# 验证婚姻分析接口
python3 scripts/evaluation/verify_prompt_consistency.py \
  --scene marriage \
  --solar-date 1990-01-01 \
  --solar-time 12:00 \
  --gender male
```

### 方法2：手动对比

1. **调用流式接口**，记录传给大模型的 prompt：
   ```bash
   curl -X POST "http://localhost:8001/api/v1/health/stream" \
     -H "Content-Type: application/json" \
     -d '{"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male"}' \
     | grep -A 1000 "data:" | head -20
   ```

2. **调用 debug 接口**，获取返回的 prompt：
   ```bash
   curl -X POST "http://localhost:8001/api/v1/health/debug" \
     -H "Content-Type: application/json" \
     -d '{"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male"}' \
     | jq '.prompt' | head -20
   ```

3. **对比两个 prompt**，确保完全一致

---

## 📊 数据流转链路

### 流式接口数据流转

```
用户请求
  ↓
流式接口 (/health/stream)
  ↓
1. 获取基础数据（八字、旺衰、详细数据）
  ↓
2. 获取大运流年数据（BaziDataService.get_fortune_data）
  ↓
3. 获取规则匹配数据（RuleService.match_rules）
  ↓
4. 构建 input_data（build_health_input_data）
  ↓
5. 构建 prompt（build_health_prompt）
  ↓
6. 传给大模型（llm_service.stream_analysis(prompt)）
```

### Debug 接口数据流转

```
用户请求
  ↓
Debug 接口 (/health/debug)
  ↓
1. 获取基础数据（八字、旺衰、详细数据）✅ 与流式接口相同
  ↓
2. 获取大运流年数据（BaziDataService.get_fortune_data）✅ 与流式接口相同
  ↓
3. 获取规则匹配数据（RuleService.match_rules）✅ 与流式接口相同
  ↓
4. 构建 input_data（build_health_input_data）✅ 与流式接口相同
  ↓
5. 构建 prompt（build_health_prompt）✅ 与流式接口相同
  ↓
6. 返回 prompt（供评测脚本使用）
```

### 评测脚本数据流转

```
评测脚本
  ↓
调用 debug 接口获取 formatted_data（prompt）
  ↓
使用 formatted_data 作为 prompt 传给百炼平台
  ↓
收集响应结果
```

---

## ⚠️ 注意事项

### 1. 确保数据来源一致

所有接口必须使用相同的数据来源：
- ✅ `BaziDataService.get_fortune_data()` - 统一的大运流年数据服务
- ✅ `RuleService.match_rules()` - 统一的规则匹配服务
- ✅ `BaziService.calculate_bazi_full()` - 统一的八字计算服务

### 2. 确保构建逻辑一致

所有接口必须使用相同的构建函数：
- ✅ `build_health_input_data()` - 健康分析的 input_data 构建
- ✅ `build_health_prompt()` - 健康分析的 prompt 构建
- ✅ `format_input_data_for_coze()` - 其他分析的 formatted_data 构建

### 3. 确保参数一致

所有接口必须使用相同的参数：
- ✅ `dayun_mode` - 大运模式（`BaziDataService.DEFAULT_DAYUN_MODE`）
- ✅ `target_years` - 目标年份范围（`BaziDataService.DEFAULT_TARGET_YEARS`）
- ✅ `include_special_liunian` - 是否包含特殊流年（`True`）

---

## 🔧 维护指南

### 修改流式接口时

1. **必须同步修改 debug 接口**，确保使用相同的逻辑
2. **必须更新验证脚本**，确保验证通过
3. **必须更新本文档**，记录变更

### 新增流式接口时

1. **必须创建对应的 debug 接口**
2. **必须在评测脚本中添加场景映射**
3. **必须更新配置文件和 API 客户端**

---

## 📝 检查清单

在每次修改流式接口或 debug 接口后，请检查：

- [ ] 流式接口和 debug 接口使用相同的数据来源
- [ ] 流式接口和 debug 接口使用相同的构建函数
- [ ] 流式接口和 debug 接口使用相同的参数
- [ ] Debug 接口返回的 prompt 与流式接口的 prompt 完全一致
- [ ] 评测脚本正确使用 debug 接口返回的 formatted_data
- [ ] 验证脚本通过测试

---

## 🎯 总结

**核心原则**：评测脚本使用的 prompt 必须与生产环境流式接口传给大模型的 prompt 完全一致。

**实现方式**：
1. 所有流式接口都有对应的 debug 接口
2. Debug 接口使用与流式接口完全相同的逻辑构建 prompt
3. 评测脚本调用 debug 接口获取 prompt，然后传给大模型

**验证方法**：
1. 使用验证脚本自动验证
2. 手动对比流式接口和 debug 接口的 prompt

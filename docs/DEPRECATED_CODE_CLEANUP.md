# 废弃代码清理记录

**清理日期**：2025-01-03

## 已清理的废弃代码

### 1. 已移除的函数（方案1废弃）

以下函数已从代码中移除，仅保留注释说明：

- `server/api/v1/marriage_analysis.py` - `build_natural_language_prompt` 函数
- `server/api/v1/children_study_analysis.py` - `build_natural_language_prompt` 函数  
- `server/api/v1/career_wealth_analysis.py` - `build_natural_language_prompt` 函数

**说明**：这些函数属于方案1（自然语言提示词），已废弃，统一使用方案2（`format_input_data_for_coze`）。

### 2. 已废弃但保留的方法（向后兼容）

以下方法标记为废弃，但为了向后兼容暂时保留：

- `server/services/qa_conversation_service.py` - `_build_natural_language_prompt` 方法
  - 状态：已废弃，未发现调用
  - 建议：可以安全移除

- `server/services/qa_question_generator.py` - `_build_question_generation_prompt` 方法
  - 状态：已废弃，未发现调用
  - 建议：可以安全移除

- `server/services/qa_question_generator.py` - `generate_followup_questions` 方法
  - 状态：已废弃，返回空列表，未发现调用
  - 建议：可以安全移除

## 已废弃但仍在使用的参数

以下参数标记为废弃，但代码中仍在内部使用，需要逐步迁移：

### 1. `dayun_index` 参数

**位置**：
- `server/api/v1/bazi_display.py` - `FortuneDisplayRequest.dayun_index`
- `server/services/bazi_display_service.py` - 多个方法参数

**状态**：标记为废弃，但代码中仍在计算和使用

**建议**：
- 保留参数定义（向后兼容）
- 内部逻辑优先使用 `dayun_year_start` 和 `dayun_year_end`
- 逐步迁移调用方到新参数

### 2. `time_range` 参数

**位置**：
- `server/services/fortune_context_service.py` - `get_fortune_context` 方法

**状态**：标记为废弃，但代码中仍在构造和使用

**建议**：
- 保留参数定义（向后兼容）
- 内部逻辑优先使用 `target_years`
- 逐步迁移调用方到新参数

## FormulaRuleService 废弃

**位置**：`server/api/v1/formula_analysis.py`

**状态**：已完全废弃，代码中已使用 `RuleService`

**说明**：原基于 JSON 文件的规则已迁移到数据库，统一使用 `RuleService`。

## 清理建议

### 可以立即清理

1. `server/services/qa_conversation_service.py` - `_build_natural_language_prompt` 方法（100行代码）
2. `server/services/qa_question_generator.py` - `_build_question_generation_prompt` 方法
3. `server/services/qa_question_generator.py` - `generate_followup_questions` 方法

### 需要逐步迁移

1. `dayun_index` 参数 -> `dayun_year_start` / `dayun_year_end`
2. `time_range` 参数 -> `target_years`

### 已完成

1. `build_natural_language_prompt` 函数（已移除）
2. `FormulaRuleService`（已废弃，使用 `RuleService`）


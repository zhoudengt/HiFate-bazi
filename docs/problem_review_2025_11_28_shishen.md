# 问题复盘：十神命格规则匹配失败

**日期**: 2025-11-28  
**问题类型**: 规则匹配失败  
**严重程度**: 高（影响核心功能）

---

## 📋 问题描述

### 现象
- 用户反馈：生日 `1987-01-07 09:00` 无法匹配十神命格规则
- API 返回：`shishen_count: 0`，所有十神命格规则都无法匹配
- 影响范围：所有用户的十神命格分析功能失效

### 复现步骤
```bash
curl -X POST 'http://127.0.0.1:8001/api/v1/bazi/formula-analysis' \
  -H 'Content-Type: application/json' \
  -d '{"solar_date": "1987-01-07", "solar_time": "09:00", "gender": "male"}'
```

**预期结果**: `shishen_count > 0`，至少匹配到 1 条十神命格规则  
**实际结果**: `shishen_count: 0`，无任何匹配

---

## 🔍 根因分析

### 直接原因

1. **匹配服务错误**
   - `formula_analysis.py` 中十神命格使用 `FormulaRuleService` 匹配
   - `FormulaRuleService` 期望旧格式（文本条件描述）
   - 数据库规则已迁移为 JSON 格式，格式不匹配

2. **规则条件格式问题**
   - 规则条件中 `hidden_stars_in_year` 包含文本描述（如"日柱副星有正财"）
   - 规则引擎无法正确解析这种混合格式
   - 导致条件匹配失败

### 根本原因

1. **架构不一致**
   - 规则迁移到数据库后，未统一匹配服务
   - 十神命格仍使用废弃的 `FormulaRuleService`
   - 其他规则类型已使用 `RuleService`

2. **规则引擎不完善**
   - `hidden_stars_in_*` 条件处理不支持文本描述
   - 缺少对混合条件格式的解析能力

3. **测试不充分**
   - 规则迁移后未进行完整的功能测试
   - 缺少规则匹配的自动化测试

### 规范违反

- ❌ **违反规则存储规范**：使用废弃的 `FormulaRuleService` 而非统一的 `RuleService`
- ❌ **违反规则格式规范**：规则条件格式不统一（文本+JSON混合）
- ❌ **违反测试规范**：缺少规则匹配的验证测试

---

## ✅ 解决方案

### 1. 统一匹配服务

**修改文件**: `server/api/v1/formula_analysis.py`

```python
# 修改前：使用 FormulaRuleService（废弃）
if 'shishen' in rule_types and FORMULA_SERVICE_AVAILABLE:
    formula_result = FormulaRuleService.match_rules(rule_data, ['十神命格'])
    ...

# 修改后：统一使用 RuleService
rule_matched = RuleService.match_rules(rule_data, rule_types=rule_types, use_cache=True)
migrated_rules.extend([r for r in rule_matched if r.get('rule_id', '').startswith('FORMULA_')])
```

### 2. 增强规则引擎

**修改文件**: `server/engines/rule_condition.py`

增强 `hidden_stars_in_*` 条件处理，支持解析文本描述：

```python
# 支持解析文本描述（如"日柱副星有正财"）
if '柱副星有' in item or '副星有' in item:
    match = re.search(r'([正偏]?[财官印食伤比劫]+)', item)
    if match:
        star_name = match.group(1)
        # 检查对应柱是否有该十神
        if '日柱' in item:
            day_stars = bazi_data.get('details', {}).get('day', {}).get('hidden_stars', [])
            if star_name in day_stars:
                return True
        # ... 其他柱的处理
```

### 3. 清理废弃代码

- 移除 `FormulaRuleService` 的引用
- 标记废弃方法（`load_from_file`）
- 添加废弃警告

---

## 🛡️ 预防措施

### 1. 规范更新

#### 规则存储规范
- ✅ 所有规则必须存储在数据库中
- ✅ 禁止从文件读取规则（xlsx/docx/json）
- ✅ 所有规则匹配必须使用 `RuleService`

#### 规则匹配规范
- ✅ 统一使用 `RuleService.match_rules()` 匹配所有规则类型
- ✅ 禁止使用 `FormulaRuleService`（已废弃）
- ✅ 规则条件格式必须统一为 JSON

#### 问题复盘规范
- ✅ 每次问题必须完成复盘
- ✅ 复盘记录必须更新到开发规范
- ✅ 必须添加预防措施和检查清单

### 2. 检查清单

新增规则类型时：
- [ ] 是否使用 `RuleService` 匹配？
- [ ] 规则条件格式是否符合 JSON 规范？
- [ ] 前后端是否同步支持新类型？
- [ ] 是否编写了规则匹配测试？

代码审查时：
- [ ] 是否还有使用 `FormulaRuleService` 的代码？
- [ ] 是否还有从文件读取规则的代码？
- [ ] 规则条件格式是否统一？

### 3. 测试要求

- ✅ 新增规则类型必须编写匹配测试
- ✅ 规则迁移后必须进行完整功能测试
- ✅ 规则条件格式变更必须验证匹配逻辑

---

## 📊 影响评估

### 修复前
- ❌ 所有十神命格规则无法匹配
- ❌ 用户无法获得十神命格分析结果
- ❌ 影响核心功能可用性

### 修复后
- ✅ 十神命格规则正常匹配
- ✅ 规则匹配服务统一
- ✅ 规则引擎支持更复杂的条件格式

---

## 🔄 后续行动

1. **代码审查**
   - [ ] 检查所有使用 `FormulaRuleService` 的代码
   - [ ] 检查所有从文件读取规则的代码
   - [ ] 确保所有规则匹配使用 `RuleService`

2. **测试完善**
   - [ ] 编写十神命格规则匹配测试
   - [ ] 编写规则条件格式验证测试
   - [ ] 添加规则匹配的自动化测试

3. **文档更新**
   - [x] 更新开发规范（规则存储规范）
   - [x] 更新开发规范（问题复盘机制）
   - [x] 记录问题复盘文档

---

## 📝 经验总结

1. **统一架构的重要性**
   - 规则迁移后必须统一匹配服务
   - 不能保留多种匹配方式并存

2. **规则格式的一致性**
   - 规则条件格式必须统一
   - 不能混合使用文本和 JSON 格式

3. **测试的必要性**
   - 规则迁移后必须进行完整测试
   - 不能仅依赖代码审查

4. **问题复盘的价值**
   - 及时复盘可以避免类似问题
   - 规范更新可以预防未来问题

---

**复盘人**: AI Assistant  
**审核人**: 待审核  
**状态**: ✅ 已修复并复盘完成


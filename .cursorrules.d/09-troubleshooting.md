# 问题复盘机制 【重要】

## 复盘流程

每次遇到问题后，必须完成以下步骤：

1. **问题记录**
   - 记录问题现象、错误信息、复现步骤
   - 记录问题发生时间、影响范围

2. **根因分析**
   - 分析问题根本原因（不是表面现象）
   - 检查是否违反开发规范
   - 检查是否有类似问题历史

3. **解决方案**
   - 实施修复方案
   - 验证修复效果
   - 确保不会再次出现

4. **规范更新**
   - 将问题复盘记录到开发规范
   - 更新相关检查清单
   - 添加预防措施

5. **代码审查**
   - 检查是否有类似代码需要修复
   - 确保所有相关代码都符合规范

## 复盘记录格式

```markdown
## 问题复盘：[问题标题] - YYYY-MM-DD

### 问题描述
- **现象**：具体问题表现
- **影响**：影响范围和严重程度
- **复现**：复现步骤

### 根因分析
- **直接原因**：表面原因
- **根本原因**：深层原因
- **规范违反**：违反了哪些开发规范

### 解决方案
- **修复内容**：具体修改
- **验证结果**：测试验证情况

### 预防措施
- **规范更新**：更新的规范内容
- **检查清单**：新增的检查项
- **代码审查**：需要检查的代码范围
```

## 🚨 常见问题与解决方案

### 问题复盘：十神命格规则匹配失败 - 2025-11-28

#### 问题描述
- **现象**：生日 1987-01-07 09:00 无法匹配十神命格规则
- **影响**：所有十神命格规则都无法匹配，影响规则分析功能
- **复现**：调用 `/bazi/formula-analysis` API，`shishen_count` 始终为 0

#### 根因分析
1. **直接原因**：
   - `formula_analysis.py` 中十神命格使用 `FormulaRuleService` 匹配
   - `FormulaRuleService` 期望旧格式（文本条件），但数据库规则已迁移为 JSON 格式

2. **根本原因**：
   - 规则迁移后未统一匹配服务
   - 规则引擎未支持混合条件格式

3. **规范违反**：
   - ❌ 未使用统一的 `RuleService` 匹配规则
   - ❌ 规则条件格式不统一

#### 解决方案
1. **修改 `formula_analysis.py`**：
   - 移除 `FormulaRuleService` 特殊处理
   - 统一使用 `RuleService` 匹配所有规则

2. **增强 `rule_condition.py`**：
   - 增强 `hidden_stars_in_*` 条件处理

### 问题1：数据库名配置错误

**症状**：`Unknown database 'bazi_system'`

**原因**：`server/config/mysql_config.py` 中默认数据库名不正确

**解决**：使用 `hifate_bazi` 作为默认数据库名

**预防**：检查 `env.template` 中的 `MYSQL_DATABASE` 值

### 问题2：规则ID包含中文导致解析失败

**症状**：`invalid literal for int() with base 10: '财富_20106'`

**原因**：规则ID格式不统一

**解决**：
```python
# 兼容两种格式
try:
    numeric_id = int(original_id)
except ValueError:
    parts = original_id.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        numeric_id = int(parts[1])
    else:
        numeric_id = hash(original_id) % 1000000
```

### 问题3：规则类型不一致

**症状**：前端显示不出新增的规则类型

**原因**：数据库 `rule_type` 字段值不统一（`formula_career` vs `career`）

**解决**：导入脚本中使用统一的英文类型名，不要使用 `formula_` 前缀

### 问题4：前端类型标签缺失

**症状**：前端页面没有显示新类型的标签页

**原因**：`frontend/formula-analysis.html` 中 `typeLabels` 未定义新类型

**解决**：在 `typeLabels` 中添加新类型映射

### 问题5：新条件类型不支持

**症状**：规则无法匹配，日志显示条件未处理

**原因**：`rule_condition.py` 中未实现对应条件类型

**解决**：在 `EnhancedRuleCondition.match` 中添加条件处理逻辑

### 问题6：gRPC 端点未注册

**症状**：前端调用 API 返回错误或无响应

**原因**：`grpc_gateway.py` 中未注册对应端点

**解决**：
```python
# 在 grpc_gateway.py 中注册
@_register("/bazi/new-feature")
async def _handle_new_feature(payload: Dict[str, Any]):
    request_model = NewFeatureRequest(**payload)
    return await new_feature(request_model)
```


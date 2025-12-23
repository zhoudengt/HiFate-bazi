# 规则开发上下文模板

## 开发步骤

1. **准备规则数据**
   - 格式：Excel/JSON
   - 包含：规则ID、类型、条件、结果

2. **编写解析脚本**
   - 位置：`scripts/migration/import_xxx_rules.py`
   - 使用 `RuleParser` 解析规则条件
   - 生成成功解析和失败解析的统计

3. **编写导入脚本**
   - 位置：`scripts/migration/import_xxx_rules_to_db.py`
   - 连接数据库
   - 插入或更新规则（根据 rule_code 判断）

4. **导入规则到数据库**
   - 运行：`python3 scripts/migration/import_xxx_rules_to_db.py`
   - 验证规则数量和内容

5. **更新前后端类型映射**
   - 前端：`local_frontend/formula-analysis.html`
   - 后端：`server/api/v1/formula_analysis.py`

6. **完整性验证**
   - 运行：`python3 scripts/ai/completeness_validator.py --type rule --name xxx`
   - 确保所有检查项通过

7. **触发热更新**
   - 运行：`python3 scripts/ai/auto_hot_reload.py --trigger`
   - 验证热更新成功

## 必需文件

- `scripts/migration/import_xxx_rules.py` - 解析脚本
- `scripts/migration/import_xxx_rules_to_db.py` - 导入脚本

## 必需更新

- 前端类型映射（`formula-analysis.html`）
- 后端类型映射（`formula_analysis.py`）

## 检查清单

- [ ] 导入脚本已创建
- [ ] 数据库导入脚本已创建
- [ ] 前端类型映射已添加
- [ ] 后端类型映射已添加
- [ ] 规则已导入数据库
- [ ] 热更新已触发


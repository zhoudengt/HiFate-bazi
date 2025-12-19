# 规则开发检查清单

本文档提供了规则开发的完整检查清单，确保功能开发一次性成功。

## 开发前准备

- [ ] 需求分析完成
  - [ ] 规则类型已确认（财富、婚姻、事业、子女、性格、身体、桃花、总评等）
  - [ ] 数据源已确认（Excel/JSON 文件路径）
  - [ ] 前端展示需求已确认（是否需要前端页面展示）

- [ ] 开发环境检查
  ```bash
  python3 scripts/dev/dev_flow_check.py --pre-dev
  ```

- [ ] 创建功能分支
  ```bash
  git checkout -b feature/rule-xxx
  ```

## 数据库设计阶段

- [ ] 数据库表结构设计完成
  - [ ] 表名符合规范（snake_case）
  - [ ] 字段名符合规范（snake_case）
  - [ ] 包含必要字段（id, rule_code, rule_type, conditions, content, description, priority, enabled, version, created_at, updated_at）

- [ ] 创建表脚本已编写
  - [ ] 脚本位置：`scripts/migration/create_xxx_table.py`
  - [ ] 脚本包含 CREATE TABLE 语句
  - [ ] 脚本包含索引创建（如需要）
  - [ ] 脚本包含回滚脚本（DROP TABLE）

- [ ] 创建表脚本已执行
  ```bash
  python3 scripts/migration/create_xxx_table.py
  ```

- [ ] 表结构验证通过
  - [ ] 表已创建
  - [ ] 字段类型正确
  - [ ] 索引已创建

## 数据导入阶段

- [ ] 数据解析脚本已编写
  - [ ] 脚本位置：`scripts/migration/import_xxx_rules.py`
  - [ ] 脚本支持 Excel/JSON 格式
  - [ ] 脚本使用 `RuleParser` 解析规则条件
  - [ ] 脚本生成成功解析和失败解析的统计

- [ ] 数据解析脚本已执行
  ```bash
  python3 scripts/migration/import_xxx_rules.py
  ```

- [ ] 解析结果验证通过
  - [ ] 解析率 >= 80%（目标）
  - [ ] 未解析规则已保存到 JSON 文件（`docs/未解析规则_YYYY_MM_DD_描述.json`）
  - [ ] 未解析规则原因已分析

- [ ] 数据导入脚本已编写
  - [ ] 脚本位置：`scripts/migration/import_xxx_rules_to_db.py`
  - [ ] 脚本支持 `--dry-run` 预览模式
  - [ ] 脚本使用 UNHEX 插入中文字符（如需要）
  - [ ] 脚本支持更新已存在的规则（根据 rule_code）

- [ ] 数据导入脚本已执行（预览模式）
  ```bash
  python3 scripts/migration/import_xxx_rules_to_db.py --dry-run
  ```

- [ ] 数据导入脚本已执行（正式导入）
  ```bash
  python3 scripts/migration/import_xxx_rules_to_db.py
  ```

- [ ] 数据验证通过
  - [ ] 规则数量正确
  - [ ] 规则内容正确
  - [ ] 规则条件格式正确（JSON 格式）
  - [ ] 规则编码正确（FORMULA_类型_编号）

## 后端开发阶段

- [ ] API 接口开发完成
  - [ ] 文件位置：`server/api/v1/xxx.py`
  - [ ] 使用 Pydantic 模型定义请求/响应
  - [ ] 所有字段使用 `Field` 提供描述和示例
  - [ ] 关键字段使用 `@validator` 验证
  - [ ] 响应模型包含 `success` 字段

- [ ] 服务层开发完成
  - [ ] 文件位置：`server/services/xxx_service.py`
  - [ ] 使用 `RuleService` 匹配规则（禁止使用 `FormulaRuleService`）
  - [ ] 规则从数据库读取（禁止从文件读取）
  - [ ] 包含错误处理和日志记录

- [ ] gRPC 端点已注册
  - [ ] 在 `server/api/grpc_gateway.py` 中使用 `@_register` 装饰器注册
  - [ ] 函数名格式：`_handle_功能模块_操作`
  - [ ] 已转换为 Pydantic 模型后再调用

- [ ] 路由已注册
  - [ ] 在 `server/main.py` 的 `_register_all_routers_to_manager()` 函数中注册
  - [ ] 路由信息正确（名称、前缀、标签）
  - [ ] 启用检查函数正确（如需要）

- [ ] 热更新支持验证通过
  ```bash
  curl -X POST http://localhost:8001/api/v1/hot-reload/check
  ```

- [ ] 代码规范检查通过
  ```bash
  python3 scripts/dev/dev_flow_check.py --files server/api/v1/xxx.py
  ```

- [ ] 命名规范检查通过
  ```bash
  python3 scripts/dev/check_naming.py server/api/v1/xxx.py
  ```

## 前端开发阶段

- [ ] 前端页面开发完成
  - [ ] 文件位置：`local_frontend/xxx.html`
  - [ ] 使用 gRPC-Web 调用 API（通过 `api.js`）
  - [ ] 错误处理显示 UI 区域（必须！）
  - [ ] 关键阶段提前显示 UI 区域

- [ ] API 调用正确
  - [ ] 使用 `api.post('/xxx/endpoint', data)` 调用
  - [ ] 错误处理正确（显示错误信息）
  - [ ] 加载状态显示正确

- [ ] 展示逻辑完成
  - [ ] 文件位置：`local_frontend/js/xxx.js`
  - [ ] 数据渲染正确
  - [ ] 交互逻辑正确

- [ ] 前端类型标签已更新（如需要）
  - [ ] `local_frontend/formula-analysis.html` 中 `typeLabels` 包含新类型
  - [ ] `statistics` 统计显示新类型

## 测试阶段

- [ ] 单元测试通过
  ```bash
  pytest tests/unit/test_xxx.py -v
  ```

- [ ] API 测试通过
  ```bash
  pytest tests/api/test_xxx.py -v
  ```

- [ ] 端到端测试通过
  ```bash
  python3 tests/e2e_production_test.py
  ```

- [ ] 前端测试通过（手动/自动化）
  - [ ] 页面可以正常访问
  - [ ] API 调用正常
  - [ ] 数据展示正确
  - [ ] 错误处理正确

- [ ] 测试覆盖率 >= 50%
  ```bash
  pytest --cov=server --cov=src --cov-report=term-missing --cov-fail-under=50
  ```

## 代码审查阶段

- [ ] 代码审查通过
  ```bash
  python3 scripts/review/code_review_check.py
  ```

- [ ] 开发流程检查通过
  ```bash
  python3 scripts/dev/dev_flow_check.py --all
  ```

- [ ] 快速修改工具验证通过
  ```bash
  python3 scripts/dev/quick_fix.py --all
  ```

## 部署阶段

- [ ] 代码已提交到 Git
  ```bash
  git add .
  git commit -m "feat: 新增规则类型 xxx"
  ```

- [ ] 代码已推送到 GitHub
  ```bash
  git push origin master
  ```

- [ ] 增量部署执行
  ```bash
  python3 scripts/deploy/auto_deploy.py --mode incremental
  ```

- [ ] 部署验证通过
  - [ ] Node1 健康检查通过
  - [ ] Node2 健康检查通过
  - [ ] 所有关键接口正常
  - [ ] 前端页面正常
  - [ ] 热更新状态正常

## 完成标准

所有检查项必须全部通过，才能认为功能开发完成。

**成功标准**：
- ✅ 所有检查项通过
- ✅ 所有测试通过
- ✅ 部署验证通过
- ✅ 功能在生产环境正常运行


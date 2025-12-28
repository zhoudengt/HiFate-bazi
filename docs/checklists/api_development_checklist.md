# API 开发检查清单

本文档提供了 API 开发的完整检查清单，确保功能开发一次性成功。

## 开发前准备

- [ ] 需求分析完成
  - [ ] API 功能定义明确
  - [ ] 请求/响应模型设计完成
  - [ ] 权限要求确认（是否需要认证）

- [ ] 开发环境检查
  ```bash
  python3 scripts/dev/dev_flow_check.py --pre-dev
  ```

- [ ] 创建功能分支
  ```bash
  git checkout -b feature/api-xxx
  ```

## 后端开发阶段

- [ ] Pydantic 模型定义完成
  - [ ] 文件位置：`server/api/v1/xxx.py`
  - [ ] **请求模型继承 `BaziBaseRequest`（包含7个标准参数）** ⚠️ **必须！**
  - [ ] 所有字段使用 `Field` 提供描述和示例
  - [ ] 关键字段使用 `@validator` 验证
  - [ ] 响应模型包含 `success` 字段
  - [ ] **7个标准参数已包含**：`solar_date`, `solar_time`, `gender`, `calendar_type`, `location`, `latitude`, `longitude`

- [ ] API 函数实现完成
  - [ ] 使用 `@router.post` 或 `@router.get` 装饰器
  - [ ] 函数参数类型正确
  - [ ] **接口内部传递7个标准参数到 `BaziInputProcessor.process_input`** ⚠️ **必须！**
  - [ ] 错误处理完善（try-except）
  - [ ] 日志记录完善
  - [ ] **缓存键包含7个标准参数（使用 `CacheKeyGenerator`）** ⚠️ **必须！**

- [ ] 服务层开发完成（如需要）
  - [ ] 文件位置：`server/services/xxx_service.py`
  - [ ] 业务逻辑封装在服务层
  - [ ] 包含错误处理和日志记录

- [ ] gRPC 端点已注册
  - [ ] 在 `server/api/grpc_gateway.py` 中使用 `@_register` 装饰器注册
  - [ ] 函数名格式：`_handle_功能模块_操作`
  - [ ] 已转换为 Pydantic 模型后再调用
  - [ ] 接口路径符合规范（`/功能模块/操作`）

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

## 测试阶段

- [ ] 单元测试通过
  ```bash
  pytest tests/unit/test_xxx.py -v
  ```

- [ ] API 测试通过
  ```bash
  pytest tests/api/test_xxx.py -v
  ```

- [ ] 集成测试通过（如需要）
  ```bash
  pytest tests/integration/test_xxx.py -v
  ```

- [ ] 端到端测试通过
  ```bash
  python3 tests/e2e_production_test.py
  ```

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
  git commit -m "feat: 新增 API xxx"
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
  - [ ] API 接口正常响应
  - [ ] 热更新状态正常

## 完成标准

所有检查项必须全部通过，才能认为功能开发完成。

**成功标准**：
- ✅ 所有检查项通过
- ✅ 所有测试通过
- ✅ 部署验证通过
- ✅ API 在生产环境正常运行


# API 开发上下文模板

## 开发步骤

1. **创建 API 文件**
   - 位置：`server/api/v1/xxx.py`
   - 使用 Pydantic 模型定义请求/响应
   - 使用 `Field` 提供字段描述和示例

2. **注册 gRPC 端点**
   - 位置：`server/api/grpc_gateway.py`
   - 使用 `@_register` 装饰器注册
   - 转换为 Pydantic 模型后再调用

3. **注册路由**
   - 位置：`server/main.py`
   - 在 `_register_all_routers_to_manager()` 中注册
   - 使用 `router_manager.register_router()`

4. **编写测试**
   - 位置：`tests/unit/test_xxx.py`
   - 测试正常流程和异常流程
   - 测试覆盖率 ≥ 50%

5. **完整性验证**
   - 运行：`python3 scripts/ai/completeness_validator.py --type api --name xxx`
   - 确保所有检查项通过

6. **触发热更新**
   - 运行：`python3 scripts/ai/auto_hot_reload.py --trigger`
   - 验证热更新成功

## 必需文件

- `server/api/v1/xxx.py` - API 定义
- `tests/unit/test_xxx.py` - 测试文件

## 必需注册

- gRPC 端点注册（`grpc_gateway.py`）
- 路由注册（`main.py`）

## 检查清单

- [ ] API 文件已创建
- [ ] gRPC 端点已注册
- [ ] 路由已注册
- [ ] Pydantic 模型已定义
- [ ] 测试文件已创建
- [ ] 热更新已触发


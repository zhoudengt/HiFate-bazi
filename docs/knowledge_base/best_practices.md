# 最佳实践库

## 开发最佳实践

### 1. 使用智能开发助手
**实践**：开发新功能时，先使用开发助手获取建议

```bash
# 启动开发助手
python3 scripts/ai/dev_assistant.py --start

# 获取开发建议
python3 scripts/ai/dev_assistant.py --suggest "开发新API" --dev-type api

# 完成开发
python3 scripts/ai/dev_assistant.py --complete
```

**好处**：
- 自动加载项目上下文
- 提供完整的开发步骤
- 自动触发热更新
- 自动验证完整性

### 2. 使用自动化热更新
**实践**：开发时启动文件监控，自动触发热更新

```bash
# 启动文件监控（开发时）
python3 scripts/ai/auto_hot_reload.py --watch

# 手动触发一次（部署时）
python3 scripts/ai/auto_hot_reload.py --trigger
```

**好处**：
- 无需手动触发热更新
- 自动验证热更新成功
- 失败自动回滚
- 禁止重启服务

### 3. 使用完整性验证
**实践**：开发完成后，使用完整性验证器检查

```bash
# API 开发
python3 scripts/ai/completeness_validator.py --type api --name xxx

# 规则开发
python3 scripts/ai/completeness_validator.py --type rule --name wealth

# 前端开发
python3 scripts/ai/completeness_validator.py --type frontend --name fortune
```

**好处**：
- 自动检查所有必需文件
- 自动检查所有必需注册
- 生成详细的完整性报告
- 避免交付丢三落四

### 4. 使用智能检查清单
**实践**：根据开发类型自动加载检查清单

```bash
# 运行检查清单
python3 scripts/ai/smart_checklist.py --type api --name xxx
```

**好处**：
- 根据开发类型自动加载对应清单
- 自动执行检查项
- 提供修复建议
- 确保不遗漏任何步骤

### 5. 使用智能决策引擎
**实践**：代码变更后，使用决策引擎判断需要执行的操作

```bash
# 分析文件变更
python3 scripts/ai/decision_engine.py --analyze server/api/v1/xxx.py

# 显示决策摘要
python3 scripts/ai/decision_engine.py --analyze server/api/v1/xxx.py --summary
```

**好处**：
- 自动判断是否需要热更新
- 禁止重启服务（强制热更新）
- 提供明确的执行建议
- 避免错误操作

## 代码编写最佳实践

### 1. 路径配置
**实践**：使用动态路径，禁止硬编码

```python
# ✅ 正确
PROJECT_ROOT = Path(__file__).parent.parent.parent
log_path = PROJECT_ROOT / "logs" / "debug.log"

# ❌ 错误
log_path = "/Users/zhoudt/Downloads/project/HiFate-bazi/logs/debug.log"
```

### 2. 异常处理
**实践**：文件操作必须有异常处理，不影响业务

```python
# ✅ 正确
try:
    with open(log_path, 'a') as f:
        f.write(log_message)
except Exception as e:
    logger.warning(f"日志写入失败（不影响业务）: {e}")

# ❌ 错误
with open(log_path, 'a') as f:
    f.write(log_message)  # 如果路径不存在，整个请求失败
```

### 3. 热更新支持
**实践**：代码必须支持热更新

```python
# ✅ 正确：使用函数/类方法，避免模块级初始化
def get_config():
    return os.getenv("MY_CONFIG", "default")

# ❌ 错误：模块加载时固定配置
MY_CONFIG = os.getenv("MY_CONFIG", "default")  # 热更新后不会变化
```

### 4. gRPC 端点注册
**实践**：新增 API 必须同时注册 gRPC 端点

```python
# 1. 在 server/api/v1/xxx.py 中定义 API
@router.post("/xxx")
async def xxx(request: XxxRequest):
    ...

# 2. 在 server/api/grpc_gateway.py 中注册
@_register("/api/v1/xxx")
async def _handle_xxx(payload: Dict[str, Any]):
    request_model = XxxRequest(**payload)
    return await xxx(request_model)
```

### 5. 路由注册
**实践**：新增路由必须在 `main.py` 中注册

```python
# 在 server/main.py 的 _register_all_routers_to_manager() 中
router_manager.register_router(
    "xxx",
    lambda: xxx_router,
    prefix="/api/v1",
    tags=["XXX"]
)
```

## 测试最佳实践

### 1. 同步编写测试
**实践**：开发功能时同步编写测试用例

```bash
# 创建测试文件
touch tests/unit/test_xxx.py

# 运行测试
pytest tests/unit/test_xxx.py -v
```

### 2. 运行所有测试
**实践**：提交代码前运行所有测试

```bash
python3 scripts/test/auto_test.py --all
```

### 3. 检查测试覆盖率
**实践**：确保测试覆盖率 ≥ 50%

```bash
python3 scripts/test/auto_test.py --coverage
```

## 部署最佳实践

### 1. 使用增量部署
**实践**：日常代码更新使用增量部署（自动热更新）

```bash
bash deploy/scripts/incremental_deploy_production.sh
```

**好处**：
- 零停机部署
- 自动触发热更新
- 自动验证部署结果
- 自动回滚（如果失败）

### 2. 部署后验证
**实践**：部署后立即验证功能正常

```bash
# 健康检查
curl http://8.210.52.217:8001/health

# 功能验证
curl -X POST http://8.210.52.217:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
```

### 3. 使用灰度发布
**实践**：重要变更使用灰度发布

```bash
bash deploy/scripts/grayscale_deploy_production.sh
```

**好处**：
- 先部署到 Node1（灰度节点）
- 完整功能测试通过后再部署 Node2
- 降低上线风险

## 问题排查最佳实践

### 1. 查看日志
**实践**：遇到问题时，先查看详细日志

```bash
# 服务日志
tail -f logs/server_8001.log

# 热更新错误日志
tail -f logs/hot_reload_errors/*.log
```

### 2. 使用诊断工具
**实践**：使用自动化诊断工具

```bash
# 开发流程检查
python3 scripts/dev/dev_flow_check.py --all

# 热更新验证
python3 scripts/hot_reload/verify_hot_reload.py
```

### 3. 根因分析
**实践**：深入分析问题根本原因，而不是表面现象

- 查看详细日志
- 分析错误堆栈
- 检查相关配置
- 验证代码变更


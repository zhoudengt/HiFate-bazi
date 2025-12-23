# 常见问题库

## 热更新相关问题

### 问题1：热更新未自动触发
**症状**：修改代码后，需要手动触发热更新

**原因**：
- 文件监控器未启动
- 热更新 API 调用失败
- 文件变更未检测到

**解决方案**：
1. 使用自动化热更新工具：
   ```bash
   python3 scripts/ai/auto_hot_reload.py --watch
   ```
2. 手动触发：
   ```bash
   python3 scripts/ai/auto_hot_reload.py --trigger
   ```
3. 检查热更新状态：
   ```bash
   curl http://localhost:8001/api/v1/hot-reload/status
   ```

### 问题2：总是需要重启服务
**症状**：开发完成后，总是被要求重启服务

**原因**：
- 未使用热更新
- 热更新未正确触发
- 热更新验证失败

**解决方案**：
1. **禁止重启服务**，必须使用热更新
2. 使用自动化热更新工具自动触发
3. 开发完成后自动验证热更新成功

### 问题3：热更新失败
**症状**：热更新触发后，功能未生效

**原因**：
- 语法错误
- 模块导入失败
- 热更新服务不可用

**解决方案**：
1. 检查语法错误：
   ```bash
   python3 -c "import ast; ast.parse(open('server/api/v1/xxx.py').read())"
   ```
2. 检查热更新日志：
   ```bash
   tail -f logs/hot_reload_errors/*.log
   ```
3. 自动回滚：
   ```bash
   python3 scripts/ai/auto_hot_reload.py --rollback
   ```

## 开发流程问题

### 问题4：交付丢三落四
**症状**：开发完成后，总是发现缺少某些文件或注册

**原因**：
- 未使用完整性验证
- 未使用检查清单
- 手动检查容易遗漏

**解决方案**：
1. 使用完整性验证器：
   ```bash
   python3 scripts/ai/completeness_validator.py --type api --name xxx
   ```
2. 使用智能检查清单：
   ```bash
   python3 scripts/ai/smart_checklist.py --type api --name xxx
   ```
3. 使用开发助手完成流程：
   ```bash
   python3 scripts/ai/dev_assistant.py --complete
   ```

### 问题5：AI 理解率低
**症状**：与 AI 交互时，需要反复解释，AI 只能理解 30%

**原因**：
- 缺乏项目上下文
- 缺乏知识库
- 需求描述不清晰

**解决方案**：
1. 使用开发助手获取建议：
   ```bash
   python3 scripts/ai/dev_assistant.py --suggest "开发新API"
   ```
2. 加载项目上下文：
   ```bash
   python3 scripts/ai/context_loader.py --type api --summary
   ```
3. 提供清晰的开发类型和需求描述

## 代码质量问题

### 问题6：硬编码路径
**症状**：代码中包含硬编码的本地路径（如 `/Users/zhoudt/...`）

**原因**：
- 未使用动态路径
- 未遵循路径配置规范

**解决方案**：
1. 使用项目根目录：
   ```python
   PROJECT_ROOT = Path(__file__).parent.parent.parent
   file_path = PROJECT_ROOT / "logs" / "debug.log"
   ```
2. 使用 `os.path.join` 构建路径
3. 文件操作添加异常处理

### 问题7：gRPC 端点未注册
**症状**：新增 API 后，前端调用失败

**原因**：
- 未在 `grpc_gateway.py` 中注册
- 注册格式错误

**解决方案**：
1. 在 `server/api/grpc_gateway.py` 中注册：
   ```python
   @_register("/api/v1/xxx")
   async def _handle_xxx(payload: Dict[str, Any]):
       request_model = XxxRequest(**payload)
       return await xxx(request_model)
   ```
2. 使用完整性验证器检查：
   ```bash
   python3 scripts/ai/completeness_validator.py --type api --name xxx
   ```

### 问题8：路由未注册
**症状**：新增 API 后，无法访问

**原因**：
- 未在 `main.py` 中注册路由
- 路由注册格式错误

**解决方案**：
1. 在 `server/main.py` 的 `_register_all_routers_to_manager()` 中注册：
   ```python
   router_manager.register_router(
       "xxx",
       lambda: xxx_router,
       prefix="/api/v1",
       tags=["XXX"]
   )
   ```
2. 使用完整性验证器检查

## 部署问题

### 问题9：部署后功能不生效
**症状**：部署到生产环境后，功能未生效

**原因**：
- 热更新未触发
- 代码未同步到服务器
- 缓存未清理

**解决方案**：
1. 使用增量部署脚本（自动触发热更新）：
   ```bash
   bash deploy/scripts/incremental_deploy_production.sh
   ```
2. 验证热更新状态：
   ```bash
   curl http://8.210.52.217:8001/api/v1/hot-reload/status
   ```
3. 清理缓存（如需要）

### 问题10：双机代码不一致
**症状**：Node1 和 Node2 代码版本不一致

**原因**：
- 代码未同步到双机
- 手动修改了服务器代码

**解决方案**：
1. 使用增量部署脚本（自动同步双机）：
   ```bash
   bash deploy/scripts/incremental_deploy_production.sh
   ```
2. 验证双机代码一致性：
   ```bash
   # 检查 Git 版本
   ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git rev-parse HEAD"
   ssh root@47.243.160.43 "cd /opt/HiFate-bazi && git rev-parse HEAD"
   ```


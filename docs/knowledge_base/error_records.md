# HiFate-bazi 问题错误记录本

> **目的**：记录开发过程中遇到的问题及其解决方案，预防类似问题再次发生
> **维护原则**：遇到新问题时主动更新，形成持续改进的知识积累
> **最后更新**：2026-01-06

---

## 📋 问题分类索引

| 分类 | 说明 | 问题数量 |
|------|------|----------|
| [API 注册](#api-注册问题) | API 端点注册、路由配置相关 | 1 |
| [gRPC 网关](#grpc-网关问题) | gRPC-Web 网关、端点映射相关 | 1 |
| [部署问题](#部署问题) | 增量部署、热更新相关 | 0 |
| [环境问题](#环境问题) | SSH、网络、容器相关 | 0 |
| [数据库问题](#数据库问题) | MySQL、Redis 相关 | 0 |

---

## 🔴 API 注册问题

### ERR-API-001：流式接口未注册到 gRPC 网关

**问题发生日期**：2026-01-06

**问题描述**：
前端通过 gRPC-Web 调用流式接口（如 `/bazi/wuxing-proportion/stream`）时，返回 `grpc-status: 12`（UNIMPLEMENTED），表示端点不存在。

**现象**：
```
HTTP Status: 200
grpc-status: 12
grpc-message: Unsupported endpoint: /bazi/wuxing-proportion/stream
```

**根因分析**：
1. 流式接口在 `server/api/v1/` 下有实现（返回 `StreamingResponse`）
2. 非流式接口已注册到 gRPC 网关（`server/api/grpc_gateway.py`）
3. 流式接口**未注册**到 gRPC 网关
4. gRPC-Web 只支持已注册的端点

**影响范围**：
- `/bazi/wuxing-proportion/stream`
- `/bazi/xishen-jishen/stream`
- `/bazi/marriage-analysis/stream`
- `/career-wealth/stream`
- `/children-study/stream`
- `/health/stream`
- `/general-review/stream`
- `/smart-fortune/smart-analyze-stream`

**解决方案**：
1. 在 `grpc_gateway.py` 中添加 `_collect_sse_stream()` 函数，用于收集 SSE 流式响应
2. 为每个流式接口添加 `@_register` 装饰器注册

**预防措施**：
1. ✅ 新增 API 端点时，检查是否需要注册到 gRPC 网关
2. ✅ 新增流式接口时，同步在 gRPC 网关中注册
3. ✅ 使用检查清单验证端点注册完整性

**检查清单**：
- [ ] 新 API 是否在 `server/api/v1/` 中定义？
- [ ] 新 API 是否需要通过 gRPC-Web 访问？
- [ ] 如需 gRPC-Web 访问，是否在 `grpc_gateway.py` 中注册？
- [ ] 如是流式接口，是否使用 `_collect_sse_stream()` 处理？

**相关文件**：
- `server/api/grpc_gateway.py` - gRPC-Web 网关
- `server/api/v1/*.py` - API 实现

**提交记录**：`68fb76e` - feat(grpc): 注册所有流式端点到 gRPC 网关

---

## 🔴 gRPC 网关问题

> 参见 [ERR-API-001](#err-api-001流式接口未注册到-grpc-网关)

---

## 🔴 部署问题

### ERR-DEPLOY-001：SSH 连接超时

**问题描述**：
增量部署时 SSH 连接超时，无法连接到生产服务器。

**常见原因**：
1. 网络不稳定
2. 服务器防火墙规则变更
3. SSH 服务未运行
4. 密码错误

**解决方案**：
```bash
# 1. 检查网络连通性
ping 8.210.52.217

# 2. 检查 SSH 端口是否开放
nc -zv 8.210.52.217 22

# 3. 使用 sshpass 连接（已配置密码）
sshpass -p 'Yuanqizhan@163' ssh -o ConnectTimeout=30 root@8.210.52.217

# 4. 如果仍然失败，检查服务器状态（通过阿里云控制台）
```

**预防措施**：
1. 部署脚本中设置合理的超时时间
2. 添加重试机制
3. 记录详细的错误日志

---

### ERR-DEPLOY-002：热更新失败

**问题描述**：
代码部署后热更新未生效，需要重启服务。

**常见原因**：
1. 修改了不支持热更新的核心模块
2. 热更新服务未运行
3. 模块导入顺序问题

**解决方案**：
```bash
# 1. 检查热更新状态
curl http://8.210.52.217:8001/api/v1/hot-reload/status

# 2. 手动触发热更新
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/trigger

# 3. 验证热更新
curl http://8.210.52.217:8001/api/v1/hot-reload/verify
```

**预防措施**：
1. 部署后自动验证热更新状态
2. 热更新失败时记录详细日志
3. 确保修改的文件在热更新监控范围内

---

## 🔴 环境问题

### ERR-ENV-001：容器名称变更

**问题描述**：
Docker 容器名称变更导致日志查看、重启等操作失败。

**解决方案**：
```bash
# 查看正确的容器名称
docker ps --format '{{.Names}}' | grep hifate

# 正确的容器名称（带连字符）
# hifate-web, hifate-nginx, hifate-mysql-master 等
```

**预防措施**：
1. 使用 `docker ps` 确认容器名称
2. 脚本中使用容器 ID 而非名称（更稳定）

---

## 🔴 数据库问题

*暂无记录*

---

## 📝 问题记录模板

复制以下模板记录新问题：

```markdown
### ERR-分类-编号：问题标题

**问题发生日期**：YYYY-MM-DD

**问题描述**：
简要描述问题现象。

**现象**：
```
错误日志或截图
```

**根因分析**：
1. 原因1
2. 原因2

**影响范围**：
- 受影响的功能/文件

**解决方案**：
具体的解决步骤。

**预防措施**：
1. 措施1
2. 措施2

**检查清单**：
- [ ] 检查项1
- [ ] 检查项2

**相关文件**：
- 文件路径

**提交记录**：`commit_hash` - 提交信息
```

---

## 📊 统计信息

| 指标 | 数量 |
|------|------|
| 总问题数 | 4 |
| API 相关 | 1 |
| 部署相关 | 2 |
| 环境相关 | 1 |
| 数据库相关 | 0 |

---

> **维护说明**：
> - AI 在开发过程中遇到新问题时，应主动更新此文档
> - 每次更新后修改"最后更新"日期
> - 定期回顾并清理已过时的问题记录


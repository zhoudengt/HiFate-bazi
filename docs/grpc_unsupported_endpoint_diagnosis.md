# gRPC-Web "Unsupported endpoint" 问题诊断报告

## 1. 测试结果（不猜测，用数据说话）

### 1.1 endpoint 格式诊断

运行 `scripts/diagnose_grpc_endpoint.py` 结果：

| endpoint 格式 | 结果 |
|---------------|------|
| `/bazi/interface` | ✗ Unsupported |
| `/api/v1/bazi/interface` | ✗ Unsupported |
| `/destiny/frontend/api/v1/bazi/interface` | ✗ Unsupported |
| `/bazi/pan/display` | ✗ Unsupported |
| 其他变体 | ✗ 全部失败 |

**关键发现**：错误信息中 `Available endpoints: ` 后面为空，说明 **SUPPORTED_ENDPOINTS 在该 worker 上为空**。

### 1.2 端点注册状态

- `POST /api/v1/hot-reload/reload-endpoints` 返回：`old: 47, new: 47`，说明**至少有一个 worker 有 47 个端点**
- 但 gRPC-Web 请求仍报 Unsupported，说明**处理 gRPC 请求的 worker 端点列表为空**

## 2. 根因分析

### 2.1 多 Worker 进程隔离

- 生产环境 Web 服务使用多 worker（uvicorn workers）
- 每个 worker 是独立进程，有各自的 `SUPPORTED_ENDPOINTS` 内存
- `reload-endpoints` 只影响**收到该请求的 worker**
- gRPC-Web 请求被负载均衡到**其他 worker**，这些 worker 的端点可能为空

### 2.2 与回退/双节点的关系

| 假设 | 证据 | 结论 |
|------|------|------|
| 5 个 gRPC 提交回退导致 | 诊断显示 `/bazi/interface` 精确格式也失败 | **排除**：格式无关，是端点未注册 |
| 双节点配置导致 | 双节点会改变 Nginx 路由、请求路径 | **可能**：若前端经 destiny 网关，路径不同 |
| 热更新/部署导致 | fix_node1_force_sync 做了 rsync，可能触发热更新 | **可能**：热更新后部分 worker 端点丢失 |

### 2.3 最可能根因

**热更新或代码同步后，部分 worker 的 SUPPORTED_ENDPOINTS 被清空且未正确恢复**。与 5 个 gRPC 提交回退无直接关系，与双节点部署流程中的 rsync/热更新更相关。

## 3. 请求链路（元气八字）

```
浏览器 (yuanqistation.com/ba_zml)
  → 前端 gRPC-Web 调用
  → https://www.yuanqistation.com/destiny/api/grpc-web/...
  → [前端代理] 转发到后端 8.210.52.217:8001
  → 后端多 worker 之一处理
  → 若该 worker 的 SUPPORTED_ENDPOINTS 为空 → Unsupported endpoint
```

## 4. 修复方案（已内置到部署脚本）

**✅ 已修复**：门控发布脚本 `gated_deploy.sh` 已内置 `gate_reload_endpoints_multi` 调用，每次热更新后自动执行 8 次 reload-endpoints，覆盖所有 worker。

### 4.1 正常情况（推荐）

执行标准门控发布，脚本会自动处理：

```bash
bash deploy/scripts/gated_deploy.sh
```

部署脚本会在以下时机自动调用 `gate_reload_endpoints_multi`：
- Node1 主流程部署后
- Node1 回滚后
- Node1 健康检查失败回滚后
- Node2 部署后

### 4.2 紧急手动修复（仅当部署脚本未执行时）

若因特殊原因需手动修复，可执行：

```bash
# 连续调用 8 次，覆盖所有 worker
for i in {1..8}; do
  curl -s -X POST "http://8.210.52.217:8001/api/v1/hot-reload/reload-endpoints"
  sleep 1
done
```

### 4.3 临时修复：重启 Web 容器（最后手段）

```bash
# 在 Node1 上
docker restart hifate-web
```

**注意**：违反「零停机」原则，仅作最后手段。

## 5. 诊断脚本

```bash
# 运行 endpoint 格式诊断
.venv/bin/python scripts/diagnose_grpc_endpoint.py --base http://8.210.52.217:8001
```

## 6. 结论与防复发

### 根因

- **不是** endpoint 格式问题（5 个 gRPC 提交回退）
- **是** 多 worker 下部分进程的 SUPPORTED_ENDPOINTS 为空
- **诱因**：部署脚本只调用 `reload-all`（信号机制），未调用 `reload-endpoints` 多次覆盖

### 已实施的防复发措施

1. **部署脚本强制调用**：`gated_deploy.sh` 在所有热更新后自动执行 `gate_reload_endpoints_multi`
2. **部署后验证**：增加 gRPC 端点验证，失败时自动回滚
3. **文档规范**：在 `.cursor/rules/deploy.mdc` 中明确禁止删除该调用
4. **诊断工具**：保留 `diagnose_grpc_endpoint.py` 用于快速定位

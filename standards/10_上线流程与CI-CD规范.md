# 上线流程与 CI/CD 规范

> **所有 AI 模型（包括 auto 模式）必须遵循本规范进行开发和部署**

## 一、核心原则

```
本地开发 → 本地测试 → Git 提交 → 增量部署 → 生产验证
```

**绝对禁止**：
- ❌ 直接在服务器上修改代码
- ❌ 跳过本地测试直接部署
- ❌ 跳过 Git 提交直接部署
- ❌ 重启服务（必须使用热更新）

---

## 二、开发流程

### 2.1 开发前准备

1. **阅读相关规范**
   - 数据编排：`standards/08_数据编排架构规范.md`
   - 热更新：`standards/hot-reload.md`
   - 接口开发：`standards/grpc-protocol.md`

2. **确认修改范围**
   - 是否涉及底层接口（需用户确认才能修改）
   - 是否需要走数据编排（流式接口必须）

### 2.2 开发规范

1. **数据编排架构**（最高优先级）
   ```
   流式接口/API接口 → BaziDataOrchestrator.fetch_data() → 底层服务
   ```
   - ✅ 所有接口通过 `BaziDataOrchestrator.fetch_data()` 获取数据
   - ❌ 禁止流式接口直接调用底层服务

2. **首包优化原则**
   - 基本信息必须秒出（TTFB < 100ms）
   - 耗时操作放入线程池或并行任务
   - LLM 调用在首包之后

---

## 三、本地测试（必须）

### 3.1 测试接口清单

| 类别 | 接口路径 | 测试命令 | 预期 |
|------|----------|----------|------|
| **核心排盘** | `/api/v1/bazi/data` | 见下方 | 返回完整八字数据 |
| **每日运势** | `/api/v1/daily-fortune-calendar/stream` | 见下方 | TTFB < 100ms |
| **五行占比** | `/api/v1/bazi/wuxing-proportion/stream` | 见下方 | TTFB < 100ms |
| **喜神忌神** | `/api/v1/bazi/xishen-jishen/stream` | 见下方 | TTFB < 100ms |
| **事业财富** | `/api/v1/career-wealth/stream` | 见下方 | 流式返回 |
| **婚姻分析** | `/api/v1/bazi/marriage-analysis/stream` | 见下方 | 流式返回 |
| **健康分析** | `/api/v1/health/stream` | 见下方 | 流式返回 |
| **子女学业** | `/api/v1/children-study/stream` | 见下方 | 流式返回 |
| **总评分析** | `/api/v1/general-review/stream` | 见下方 | 流式返回 |

### 3.2 测试命令

```bash
# 健康检查
curl -s http://localhost:8001/api/v1/health

# 每日运势（测试首包时间）
curl -s -w "\nTTFB: %{time_starttransfer}s\n" --max-time 60 \
  -X POST http://localhost:8001/api/v1/daily-fortune-calendar/stream \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-02-05", "solar_date": "1992-01-15", "solar_time": "12:00", "gender": "male"}' \
  -o /dev/null

# 五行占比
curl -s -w "\nTTFB: %{time_starttransfer}s\n" --max-time 60 \
  -X POST http://localhost:8001/api/v1/bazi/wuxing-proportion/stream \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1992-01-15", "solar_time": "12:00", "gender": "male"}' \
  -o /dev/null

# 事业财富
curl -s -w "\nTTFB: %{time_starttransfer}s\n" --max-time 120 \
  -X POST http://localhost:8001/api/v1/career-wealth/stream \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1992-01-15", "solar_time": "12:00", "gender": "male"}' \
  -o /dev/null
```

### 3.3 验收标准

| 指标 | 标准 |
|------|------|
| TTFB（首包时间） | < 100ms（流式接口基本信息秒出） |
| 字段完整性 | 所有必需字段都返回，无缺失 |
| 功能正确性 | 返回数据符合预期 |
| 无 Linter 错误 | `ReadLints` 检查通过 |

---

## 四、Git 提交规范

### 4.1 提交前检查

```bash
# 1. 检查 linter 错误
# 使用 ReadLints 工具检查修改的文件

# 2. 检查未提交更改
git status

# 3. 查看更改内容
git diff
```

### 4.2 提交信息格式

```
<type>: <简短描述>

<详细说明（可选）>
```

**类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `perf`: 性能优化
- `refactor`: 重构
- `docs`: 文档
- `test`: 测试

**示例**：
```
perf: 优化 daily-fortune-calendar/stream 首包延迟

- 将 daily_fortune_calendar 放入编排器并行任务
- 流式接口走统一编排
- 首包时间从 2-5s 降至 5-25ms
```

---

## 五、增量部署流程

### 5.1 部署命令

```bash
# 在项目根目录执行
./deploy/scripts/incremental_deploy_production.sh
```

### 5.2 部署脚本自动执行的步骤

1. **部署前检查**
   - 分支检查（master）
   - 语法检查
   - 导入验证

2. **代码同步**
   - SSH 连接服务器
   - git pull 最新代码

3. **热更新触发**
   - 调用 `/hot-reload/reload-all`（通知所有 Worker）
   - 等待所有 Worker ACK 确认

4. **部署后功能验证**
   - 调用 `/hot-reload/verify` 检查关键功能
   - 健康检查
   - 核心接口验证

### 5.3 手动部署（备用）

```bash
# 1. 服务器拉取代码
ssh hifate-node1 "cd /opt/HiFate-bazi && git pull origin master"

# 2. 触发全量热更新（必须用 reload-all，不是 check 或 trigger）
curl -s --max-time 60 -X POST http://8.210.52.217:8001/api/v1/hot-reload/reload-all
# 期望返回：{"success":true, "message":"...已通知所有 Worker..."}

# 3. 等待所有 Worker 完成重载
sleep 5

# 4. 功能验证（必须！不能只做健康检查）
curl -s --max-time 15 -X POST http://8.210.52.217:8001/api/v1/hot-reload/verify
# 期望返回：{"success":true, "checks":{...}} 所有检查项通过

# 5. 健康检查
curl -s http://8.210.52.217:8001/api/v1/health
```

> **⚠️ 关键**：必须用 `/hot-reload/reload-all`，不要用 `/hot-reload/check`。
> `/check` 只影响处理请求的单个 Worker，其他 7 个 Worker 仍运行旧代码。

---

## 六、生产环境验证

### 6.1 功能完整性验证（必须！）

```bash
PROD_URL="http://8.210.52.217:8001"

# 1. 功能验证（支付客户端、gRPC端点、数据库、Redis）
curl -s --max-time 15 -X POST $PROD_URL/api/v1/hot-reload/verify
# 检查返回中 success 为 true，所有 checks.*.ok 为 true
# 特别注意 checks.payment_clients.ok（支付功能）

# 2. 健康检查
curl -s $PROD_URL/api/v1/health

# 3. 查看热更新历史（确认所有模块加载成功）
curl -s $PROD_URL/api/v1/hot-reload/history | python3 -m json.tool | head -30
```

### 6.2 接口验证

```bash
# 每日运势（验证首包时间）
curl -s -w "\nTTFB: %{time_starttransfer}s, Total: %{time_total}s\n" \
  --max-time 60 -X POST $PROD_URL/api/v1/daily-fortune-calendar/stream \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-02-05", "solar_date": "1992-01-15", "solar_time": "12:00", "gender": "male"}' \
  -o /dev/null

# 如果修改了支付模块
curl -s --max-time 30 $PROD_URL/api/v1/payment/providers
```

### 6.3 回归测试脚本

```bash
# 运行全量 API 回归测试
python3 scripts/evaluation/api_regression_test.py --env production --category all
```

### 6.4 验证不通过的处理

如果 `/hot-reload/verify` 返回 `success: false`：
1. 查看具体哪个 check 失败
2. 支付客户端失败：再次调用 `/hot-reload/reload-all`，等待 5 秒后重新验证
3. gRPC 端点失败：调用 `/hot-reload/reload-endpoints`
4. 多次重试仍失败：检查日志 `ssh hifate-node1 "docker logs hifate-web --since=5m 2>&1 | tail -50"`

---

## 七、完整流程检查清单

### 开发阶段
- [ ] 阅读相关规范文档
- [ ] 确认是否涉及底层接口修改（需用户确认）
- [ ] 流式接口是否走统一编排
- [ ] 是否保证首包秒出

### 测试阶段
- [ ] 本地服务启动正常
- [ ] 运行测试命令验证功能
- [ ] TTFB < 100ms（流式接口）
- [ ] 字段完整，无缺失
- [ ] 无 Linter 错误

### 提交阶段
- [ ] `git status` 检查更改
- [ ] `git diff` 确认修改内容
- [ ] 提交信息符合规范
- [ ] 推送到远程仓库

### 部署阶段
- [ ] 运行增量部署脚本（或手动执行 git pull + `/reload-all`）
- [ ] 部署脚本无报错
- [ ] `/hot-reload/verify` 返回 `success: true`（功能完整性验证通过）
- [ ] 特别确认 `checks.payment_clients.ok` 为 true（支付功能正常）
- [ ] 生产环境健康检查通过
- [ ] 验证修改的具体接口功能正常
- [ ] TTFB 符合预期

---

## 八、常见问题

### Q1: 热更新不生效（部分请求返回旧版本结果）

**原因**：使用了 `/hot-reload/check`，只更新了单个 Worker，其余 7 个仍运行旧代码。

**解决**：
```bash
# 必须用 reload-all（通知所有 Worker）
curl -s --max-time 60 -X POST http://8.210.52.217:8001/api/v1/hot-reload/reload-all

# 等待 5 秒后验证
sleep 5
curl -s -X POST http://8.210.52.217:8001/api/v1/hot-reload/verify
```

### Q2: 热更新后支付功能异常

**原因**：旧版本中 `RELOAD_ORDER` 顺序不对（singleton 在 source 之前），或代码中存在 `del sys.modules` 导致竞态条件。

**解决**：
1. 确认 `RELOAD_ORDER` 中 `singleton` 在 `source` 之后
2. 确认支付代码中没有 `del sys.modules` 操作
3. 调用 `/hot-reload/reload-all` 重新触发热更新

### Q3: 首包时间过长
- 检查是否走了统一编排
- 检查是否有同步阻塞调用
- 将耗时操作放入线程池

### Q4: 部署后接口报错
```bash
# 查看服务器日志
ssh hifate-node1 "docker logs hifate-web --since=5m 2>&1 | tail -100"

# 查看热更新历史（排查哪个模块加载失败）
curl -s http://8.210.52.217:8001/api/v1/hot-reload/history | python3 -m json.tool

# 如需回滚
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/rollback
```

### Q5: 热更新期间请求返回 503

**正常行为**：热更新期间，支付等关键端点会主动返回 503（"系统正在更新，请稍后重试"），避免在模块不一致状态下处理请求。通常 1-3 秒后恢复。

---

## 九、热更新端点速查表

| 端点 | 用途 | 何时使用 |
|------|------|---------|
| `/hot-reload/reload-all` | 全量重载 + 通知所有 Worker | **生产部署必须用这个** |
| `/hot-reload/verify` | 功能完整性验证 | **部署后必须调用** |
| `/hot-reload/history` | 查看热更新历史 | 排查问题时使用 |
| `/hot-reload/status` | 查看热更新状态 | 一般性状态查询 |
| `/hot-reload/check` | 仅当前 Worker 检查 | **仅开发调试用，禁止用于生产** |
| `/hot-reload/rollback` | 回滚到上一版本 | 紧急回滚 |
| `/hot-reload/sync` | 双机集群同步 | 多节点部署 |

---

## 十、服务器信息

| 环境 | 地址 | 说明 |
|------|------|------|
| 生产 node1 | 8.210.52.217:8001 | 主服务器 |
| 本地 | localhost:8001 | 开发测试 |

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-02-06 | 完善部署流程：增加 /verify 验证、/reload-all 强制要求、常见问题更新、端点速查表 |
| 2026-02-05 | 创建上线流程规范，明确测试接口清单 |

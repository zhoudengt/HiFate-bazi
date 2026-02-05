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
   - 调用热更新 API
   - 等待模块重载

4. **部署后验证**
   - 健康检查
   - 核心接口验证

### 5.3 手动部署（备用）

```bash
# 1. SSH 到服务器
ssh root@8.210.52.217

# 2. 进入项目目录
cd /opt/hifate-bazi

# 3. 拉取代码
git pull origin master

# 4. 触发热更新
curl -X POST http://localhost:8001/api/v1/hot-reload/trigger

# 5. 验证部署
curl -s http://localhost:8001/api/v1/health
```

---

## 六、生产环境验证

### 6.1 必须验证的接口

```bash
# 生产环境地址
PROD_URL="http://8.210.52.217:8001"

# 1. 健康检查
curl -s $PROD_URL/api/v1/health

# 2. 每日运势（验证首包时间）
curl -s -w "\nTTFB: %{time_starttransfer}s, Total: %{time_total}s\n" \
  --max-time 60 -X POST $PROD_URL/api/v1/daily-fortune-calendar/stream \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-02-05", "solar_date": "1992-01-15", "solar_time": "12:00", "gender": "male"}' \
  -o /dev/null

# 3. 如果修改了其他接口，也要验证
```

### 6.2 回归测试脚本

```bash
# 运行 API 回归测试
python3 scripts/evaluation/api_regression_test.py
```

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
- [ ] 运行增量部署脚本
- [ ] 部署脚本无报错
- [ ] 生产环境健康检查通过
- [ ] 验证修改的接口功能正常
- [ ] TTFB 符合预期

---

## 八、常见问题

### Q1: 热更新不生效
```bash
# 检查热更新状态
curl -s http://localhost:8001/api/v1/hot-reload/status

# 手动触发热更新
curl -X POST http://localhost:8001/api/v1/hot-reload/trigger
```

### Q2: 首包时间过长
- 检查是否走了统一编排
- 检查是否有同步阻塞调用
- 将耗时操作放入线程池

### Q3: 部署后接口报错
- 查看服务器日志：`docker logs hifate-web-1 --tail 100`
- 检查代码语法错误
- 回滚到上一版本

---

## 九、服务器信息

| 环境 | 地址 | 说明 |
|------|------|------|
| 生产 node1 | 8.210.52.217:8001 | 主服务器 |
| 本地 | localhost:8001 | 开发测试 |

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-02-05 | 创建上线流程规范，明确测试接口清单 |

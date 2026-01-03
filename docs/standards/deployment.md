# 部署详细规范

> 本文档从 `.cursorrules` 提取，包含部署相关的完整规范。详见 `.cursorrules` 核心规范章节。

## 🚀 增量部署规范 【必须遵守】

### 🔴 核心原则

> **增量部署通过热更新实现零停机快速部署，适用于日常代码更新，必须经过完整的安全检查。**

### 📋 增量部署 vs 完整部署对比

| 对比项 | 完整部署（CI/CD） | 增量部署（热更新） |
|--------|------------------|-------------------|
| **构建镜像** | ✅ 需要（GitHub Actions 构建） | ❌ 不需要（直接使用代码） |
| **容器重启** | ✅ 需要（`docker-compose up -d`） | ❌ 不需要（热更新） |
| **服务中断** | ⚠️ 可能有短暂中断（滚动更新） | ✅ 零中断 |
| **部署速度** | 慢（8-15分钟） | 快（30秒-2分钟） |
| **适用场景** | 首次部署、依赖变更、Dockerfile 变更 | 日常代码更新、规则更新 |
| **资源消耗** | 高（构建镜像、网络传输） | 低（仅代码更新） |
| **回滚速度** | 慢（拉取旧镜像+重启） | 快（热更新回滚，秒级） |

### 🎯 适用场景判断

#### ✅ 使用增量部署的场景

1. **Python 代码更新**
   - 业务逻辑修改
   - Bug 修复
   - 性能优化

2. **规则更新**
   - 数据库规则变更
   - 配置更新
   - 环境变量更新

3. **微服务代码修改**
   - 微服务逻辑更新
   - 服务间调用优化

4. **日常迭代**
   - 快速发布
   - 频繁更新

#### ❌ 必须使用完整部署的场景

1. **依赖变更**
   - 修改 `requirements.txt`
   - 新增 Python 包
   - 需要重建镜像

2. **Dockerfile 变更**
   - 修改构建流程
   - 修改基础镜像
   - 需要重新构建

3. **首次部署**
   - 需要构建完整镜像
   - 需要安装所有依赖

4. **重大架构变更**
   - 需要完整验证
   - 需要回滚保障

### 📋 增量部署标准流程

```
1. 本地开发 → 提交代码
   ↓
2. 推送到 GitHub
   ↓
3. 运行增量部署脚本
   ├─ 部署前检查（语法、导入、分支等）
   ├─ 拉取代码到服务器
   ├─ 服务器端验证
   ├─ 触发热更新
   └─ 部署后验证（健康检查、功能验证）
   ↓
4. 完成部署（零停机）
```

### 🔒 增量部署安全检查

#### 第一层：部署前检查（本地）

**必须检查项**：
- [ ] 当前分支为 `master`（或确认分支）
- [ ] 无未提交的更改
- [ ] 无未推送的提交（或先推送）
- [ ] Python 语法验证通过
- [ ] 关键模块导入验证通过

**检查命令**：
```bash
# 检查分支
git rev-parse --abbrev-ref HEAD

# 检查未提交更改
git status --porcelain

# 语法验证
python3 -c "import ast; import glob; [ast.parse(open(f).read()) for f in glob.glob('server/**/*.py', recursive=True)]"

# 模块导入验证
python3 -c "from server.main import app; from server.services.rule_service import RuleService"
```

#### 第二层：服务器端验证

**必须检查项**：
- [ ] 服务器 SSH 连接正常
- [ ] 代码拉取成功
- [ ] 服务器端语法验证通过
- [ ] 热更新服务可用

**验证命令**：
```bash
# 检查服务可用性
curl -f http://8.210.52.217:8001/health

# 检查热更新状态
curl http://8.210.52.217:8001/api/v1/hot-reload/status
```

#### 第三层：部署后验证

**必须检查项**：
- [ ] 健康检查通过（Node1 和 Node2）
- [ ] 热更新状态正常
- [ ] 关键功能验证通过（可选）

**验证命令**：
```bash
# 健康检查
curl -f http://8.210.52.217:8001/health
curl -f http://47.243.160.43:8001/health

# 功能验证
curl -X POST http://8.210.52.217:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
```

### 🚀 增量部署执行步骤

#### 方式 1：使用增量部署脚本（推荐）

```bash
# 1. 确保代码已提交并推送
git add .
git commit -m "feat: 新功能"
git push origin master

# 2. 运行增量部署脚本
bash deploy/scripts/incremental_deploy_production.sh
```

**脚本功能**：
- ✅ 自动执行所有安全检查
- ✅ 自动拉取代码到双机
- ✅ 自动触发热更新
- ✅ 自动验证部署结果
- ✅ 自动回滚（如果失败）

#### 方式 2：手动增量部署

```bash
# 1. 在 Node1 上拉取代码
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git pull origin master"

# 2. 在 Node2 上拉取代码
ssh root@47.243.160.43 "cd /opt/HiFate-bazi && git pull origin master"

# 3. 在 Node1 上触发热更新（自动同步到 Node2）
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/sync

# 4. 验证部署结果
curl http://8.210.52.217:8001/health
curl http://47.243.160.43:8001/health
```

### 🔄 增量部署回滚机制

**自动回滚触发条件**：
- 健康检查失败（5次重试后）
- 语法验证失败
- 模块导入失败

**手动回滚**：
```bash
# 在 Node1 上回滚
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/rollback

# 在 Node2 上回滚
curl -X POST http://47.243.160.43:8001/api/v1/hot-reload/rollback
```

**回滚机制**：
1. 优先使用代码备份（`.hot_reload_backups/`）
2. 如果备份不可用，使用 Git 回滚
3. 自动重新加载模块
4. 验证回滚结果

### ✅ 增量部署检查清单

每次增量部署前必须检查：

#### 代码路径规范检查（最高优先级）
- [ ] ✅ 所有代码修改都在本地完成（未在服务器上修改）
- [ ] ✅ 代码已提交到 Git（git commit）
- [ ] ✅ 代码已推送到 GitHub（git push origin master）
- [ ] ✅ 未在服务器上直接修改任何代码（sed、vim、nano 等）
- [ ] ✅ 准备使用增量部署脚本（自动同步双机）

#### 代码质量检查
- [ ] 代码已提交到 Git
- [ ] 代码已推送到远程
- [ ] 当前分支为 `master`（或确认分支）
- [ ] 无未提交的更改

#### 语法和导入检查
- [ ] Python 语法验证通过（本地）
- [ ] Python 语法验证通过（服务器）
- [ ] 关键模块可以导入
- [ ] 无循环依赖

#### 数据库变更检查（必须）
- [ ] 数据库变更已检测（运行 `python3 scripts/db/detect_db_changes.py`）
- [ ] 数据库同步脚本已生成（如有变更）
- [ ] 数据库同步脚本已预览（dry-run模式，查看同步内容）
- [ ] 数据库同步已执行（如有变更，Node1和Node2）
- [ ] 数据库同步后已验证（运行 `python3 scripts/db/verify_data_consistency.py`）
- [ ] 数据一致性验证通过（本地和生产数据一致）

#### 配置变更检查（必须）
- [ ] 配置变更已检测（运行 `python3 scripts/config/detect_config_changes.py`）
- [ ] 配置变更报告已查看（新增、修改、删除的配置项）
- [ ] 配置同步已执行（如有变更，Node1和Node2）
- [ ] 配置同步后已验证（验证配置文件格式正确）

#### 服务器连接检查
- [ ] Node1 SSH 连接正常
- [ ] Node2 SSH 连接正常
- [ ] Node1 服务可用（健康检查通过）
- [ ] Node2 服务可用（健康检查通过）

#### 部署后验证
- [ ] Node1 健康检查通过
- [ ] Node2 健康检查通过
- [ ] Node1 与 Node2 Git 版本一致（脚本自动验证）
- [ ] Node1 与 Node2 关键文件哈希一致（脚本自动验证）
- [ ] 热更新状态正常
- [ ] 关键功能验证通过（可选）

### 🔴 数据库和配置同步强制检查 【必须遵守】

#### 数据库变更同步规范

**检测命令**：
```bash
# 检测数据库变更
python3 scripts/db/detect_db_changes.py

# 生成同步脚本
python3 scripts/db/detect_db_changes.py --generate-sync-script

# 预览同步脚本（dry-run模式）
bash scripts/db/sync_production_db.sh --node node1 --deployment-id <ID> --dry-run

# 执行同步
bash scripts/db/sync_production_db.sh --node node1 --deployment-id <ID>
bash scripts/db/sync_production_db.sh --node node2 --deployment-id <ID>

# 验证数据一致性
python3 scripts/db/verify_data_consistency.py
```

**同步流程**：
1. 运行数据库变更检测
2. 如果有变更，生成同步脚本
3. 预览同步脚本内容（dry-run）
4. 确认后同步到 Node1（灰度节点）
5. 验证 Node1 数据一致性
6. 同步到 Node2（生产节点）
7. 验证 Node2 数据一致性

**强制要求**：
- ✅ **部署前必须检测数据库变更**
- ✅ **如有变更，必须生成同步脚本**
- ✅ **必须预览同步脚本内容**
- ✅ **必须同步到双机（Node1 和 Node2）**
- ✅ **同步后必须验证数据一致性**

#### 配置变更同步规范

**检测命令**：
```bash
# 检测配置变更
python3 scripts/config/detect_config_changes.py

# 预览配置同步（dry-run模式）
bash scripts/config/sync_production_config.sh --node node1 --dry-run

# 执行配置同步
bash scripts/config/sync_production_config.sh --node node1
bash scripts/config/sync_production_config.sh --node node2
```

**同步流程**：
1. 运行配置变更检测
2. 查看配置变更报告
3. 确认后同步到 Node1
4. 同步到 Node2
5. 验证配置格式正确性
6. 如需要，重启相关服务

**强制要求**：
- ✅ **部署前必须检测配置变更**
- ✅ **如有变更，必须查看变更报告**
- ✅ **必须同步到双机（Node1 和 Node2）**
- ✅ **同步后必须验证配置正确性**

#### 自动集成检查

**增量部署脚本已集成**：
- ✅ 自动检测数据库变更（`deploy/scripts/incremental_deploy_production.sh` 第 1.7 步）
- ✅ 自动检测配置变更（`deploy/scripts/incremental_deploy_production.sh` 第 1.8 步）
- ✅ 自动提示同步操作
- ✅ 自动验证同步结果

**使用方式**：
```bash
# 运行增量部署脚本（自动检测并提示同步）
bash deploy/scripts/incremental_deploy_production.sh
```

脚本会自动：
1. 检测数据库变更并提示生成同步脚本
2. 检测配置变更并提示同步
3. 要求确认后才继续部署

### 🚨 增量部署注意事项

1. **代码必须已推送**
   - 增量部署脚本会拉取远程代码
   - 未推送的代码不会被部署

2. **数据库变更必须同步**
   - 部署前必须检测数据库变更
   - 如有变更，必须同步到生产环境
   - 同步后必须验证数据一致性

3. **配置变更必须同步**
   - 部署前必须检测配置变更
   - 如有变更，必须同步到生产环境
   - 同步后必须验证配置正确性

4. **不适用依赖变更**
   - 修改 `requirements.txt` 必须使用完整部署
   - 新增系统依赖必须使用完整部署

5. **双机同步**
   - 在 Node1 上触发热更新会自动同步到 Node2
   - 确保 Redis 连接正常（用于双机同步）
   - 数据库和配置必须同步到双机

6. **监控和告警**
   - 部署后持续监控服务状态
   - 发现问题立即回滚

7. **测试优先**
   - 重要变更先在测试环境验证
   - 生产环境部署后立即验证

### 📊 增量部署性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **部署时间** | < 2分钟 | 从拉取代码到完成验证 |
| **服务中断** | 0秒 | 零停机部署 |
| **回滚时间** | < 10秒 | 热更新回滚速度 |
| **成功率** | > 99% | 部署成功率 |

### 🔍 故障排查

**如果增量部署失败**：

1. **检查代码语法**
   ```bash
   python3 -c "import ast; import glob; [ast.parse(open(f).read()) for f in glob.glob('server/**/*.py', recursive=True)]"
   ```

2. **检查热更新状态**
   ```bash
   curl http://8.210.52.217:8001/api/v1/hot-reload/status
   ```

3. **检查服务日志**
   ```bash
   ssh root@8.210.52.217 "docker logs hifate-web --tail 100"
   ```

4. **手动回滚**
   ```bash
   curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/rollback
   ```

5. **查看热更新错误日志**
   ```bash
   ssh root@8.210.52.217 "cat /opt/HiFate-bazi/logs/hot_reload_errors/*.log | tail -50"
   ```

### 📚 相关文档

- **增量部署脚本**：`deploy/scripts/incremental_deploy_production.sh`
- **热更新系统**：见"🔥 热更新强制规范"章节

---


---

# 灰度发布规范 【必须遵守】

### 🔴 核心原则

> **所有生产环境部署必须使用灰度发布流程，先部署到 Node1 进行完整功能测试，通过后再部署到 Node2，确保上线准确率 >95%。**

### 📋 灰度发布流程

```
┌─────────────────────────────────────────────────────────────┐
│                    灰度发布流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 部署前检查（本地）                                       │
│     ├─ Git 状态检查                                         │
│     ├─ 代码语法验证                                         │
│     ├─ 数据库变更检测（对比数据字典）                        │
│     └─ 生成数据库同步脚本（如有变更）                        │
│                                                             │
│  2. 部署到 Node1（灰度节点）                                │
│     ├─ 拉取代码到 Node1                                     │
│     ├─ 执行数据库同步（如有变更）                            │
│     ├─ 触发热更新                                           │
│     └─ 等待热更新完成                                       │
│                                                             │
│  3. Node1 完整功能测试（关键步骤）                          │
│     ├─ 健康检查                                             │
│     ├─ 所有前端调用的接口测试（9-10个接口）                  │
│     │   ├─ 八字计算                                         │
│     │   ├─ 公式分析                                         │
│     │   ├─ 月运势                                           │
│     │   ├─ 日运势                                           │
│     │   ├─ 身宫命宫                                         │
│     │   ├─ 智能分析                                         │
│     │   ├─ 每日运势日历                                     │
│     │   ├─ 行动建议流式                                     │
│     │   └─ 其他前端接口                                     │
│     ├─ 热更新状态检查                                       │
│     └─ 性能检查（响应时间）                                 │
│                                                             │
│  4. 决策点：Node1 测试结果                                 │
│     ├─ ✅ 全部通过 → 继续到步骤5（部署 Node2）              │
│     └─ ❌ 测试失败 → 回滚 Node1，报告问题，停止部署          │
│                                                             │
│  5. 部署到 Node2（生产节点）                                │
│     ├─ 拉取代码到 Node2                                     │
│     ├─ 执行数据库同步（如有变更）                            │
│     ├─ 触发热更新                                           │
│     └─ 等待热更新完成                                       │
│                                                             │
│  6. Node2 验证（快速验证）                                  │
│     ├─ 健康检查                                             │
│     ├─ 关键接口快速测试（3-5个核心接口）                     │
│     └─ 双机代码一致性验证                                    │
│                                                             │
│  7. 完成部署                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 🚀 灰度发布执行步骤

#### 使用灰度发布脚本（推荐）

```bash
# 1. 确保代码已提交并推送
git add .
git commit -m "feat: 新功能"
git push origin master

# 2. 运行灰度发布脚本
bash deploy/scripts/grayscale_deploy_production.sh
```

**脚本功能**：
- ✅ 自动执行所有安全检查
- ✅ 自动检测数据库变更
- ✅ 自动部署到 Node1（灰度节点）
- ✅ 自动运行完整功能测试
- ✅ 测试通过后自动部署到 Node2
- ✅ 测试失败自动回滚 Node1
- ✅ 自动生成失败报告

### 📋 核心功能接口清单

基于前端调用，需要测试的接口：

| 接口 | 路径 | 方法 | 优先级 |
|------|------|------|--------|
| 健康检查 | `/health` | GET | 高 |
| 八字计算 | `/api/v1/bazi/calculate` | POST | 高 |
| 公式分析 | `/api/v1/bazi/formula-analysis` | POST | 高 |
| 月运势 | `/api/v1/bazi/monthly-fortune` | POST | 高 |
| 日运势 | `/api/v1/bazi/daily-fortune` | POST | 高 |
| 身宫命宫 | `/api/v1/bazi/shengong-minggong` | POST | 高 |
| 智能分析 | `/api/v1/smart-analyze` | GET | 高 |
| 每日运势日历 | `/api/v1/daily-fortune-calendar/calendar` | POST | 高 |
| 行动建议流式 | `/api/v1/daily-fortune-calendar/action-suggestions/stream` | POST | 中 |
| 热更新状态 | `/api/v1/hot-reload/status` | GET | 中 |

### 🔄 回滚机制

**自动回滚触发条件**：
- Node1 健康检查失败（5次重试后）
- Node1 功能测试失败（任何接口测试失败）
- 数据库同步失败

**回滚顺序**：
1. 先回滚代码（热更新回滚）
2. 再回滚数据库（执行回滚脚本）
3. 验证回滚成功

**回滚命令**：
```bash
# 代码回滚
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/rollback

# 数据库回滚（如有变更）
bash scripts/db/rollback_db.sh --node node1 --rollback-file scripts/db/rollback/rollback_YYYYMMDD_HHMMSS.sql
```

### ✅ 灰度发布检查清单

每次灰度发布前必须检查：

- [ ] 代码已推送到 GitHub
- [ ] 本地代码语法验证通过
- [ ] 数据库变更已检测并生成同步脚本
- [ ] 回滚脚本已生成
- [ ] Node1 服务健康检查通过
- [ ] Node1 完整功能测试通过（所有接口）
- [ ] Node2 服务健康检查通过
- [ ] Node2 快速验证通过
- [ ] 双机代码一致性验证通过

### 📊 灰度发布性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **上线准确率** | >95% | 通过灰度发布验证 |
| **问题影响范围** | 仅 Node1 | Node2 保持稳定 |
| **回滚速度** | < 30秒 | 自动回滚，秒级恢复 |
| **测试覆盖率** | 100% | 所有前端接口必须测试 |

### 📚 相关文档

- **灰度发布脚本**：`deploy/scripts/grayscale_deploy_production.sh`
- **Node1 测试脚本**：`tests/e2e_node1_test.py`
- **增量部署脚本**：`deploy/scripts/incremental_deploy_production.sh`（旧版本，保留作为备用）

---


---

# 数据库同步规范 【必须遵守】

### 🔴 核心原则

> **所有数据库结构变更必须通过数据库同步机制处理，确保本地、Node1、Node2 数据库结构完全一致，支持自动回滚。**

### 🔤 数据库编码处理规范 【必须遵守】

> **所有包含中文字符的数据库操作必须使用正确的编码方式，确保数据一致性。**

#### 问题复盘：数据库编码异常导致查询失败 - 2025-12-18

**问题描述**：
- **现象**：生产环境"分数"和"幸运颜色"显示"暂无"，但数据库中存在正确数据
- **影响**：用户无法看到建除分数和幸运颜色信息
- **复现**：API 返回 `score: null` 和 `lucky_colors: null`，但数据库查询显示有数据

**根因分析**：
1. **直接原因**：
   - 数据库记录编码异常（UTF-8 字符被错误编码为多字节序列）
   - Python 查询时无法匹配编码异常的记录
   - 使用普通 `WHERE` 条件查询返回 `None`

2. **根本原因**：
   - 数据导入时未使用正确的编码方式
   - 直接使用 SQL 插入中文字符，可能受到客户端编码影响
   - 未使用 `UNHEX` 或 `BINARY` 比较确保编码一致性

3. **规范违反**：
   - ❌ 未使用 `UNHEX` 插入中文字符数据
   - ❌ 未使用 `BINARY` 比较进行精确匹配
   - ❌ 未验证数据编码正确性

**解决方案**：
1. **数据插入使用 UNHEX**：
   ```sql
   -- ✅ 正确：使用 UNHEX 确保编码正确
   INSERT INTO daily_fortune_jianchu (jianchu, content, score, enabled) 
   VALUES (UNHEX('E694B6'), UNHEX('E883BDE9878FE5B08FE7BB93...'), 90, 1);
   
   -- ❌ 错误：直接插入中文字符（可能编码异常）
   INSERT INTO daily_fortune_jianchu (jianchu, content, score, enabled) 
   VALUES ('收', '能量小结：...', 90, 1);
   ```

2. **查询使用 BINARY 比较**：
   ```python
   # ✅ 正确：使用 BINARY 比较确保精确匹配
   cursor.execute(
       "SELECT jianchu, score FROM daily_fortune_jianchu WHERE BINARY jianchu = %s",
       ('收',)
   )
   
   # ❌ 错误：普通比较（可能因编码问题无法匹配）
   cursor.execute(
       "SELECT jianchu, score FROM daily_fortune_jianchu WHERE jianchu = %s",
       ('收',)
   )
   ```

3. **Python 脚本生成 UNHEX SQL**：
   ```python
   # ✅ 正确：生成 UNHEX SQL 语句
   def generate_unhex_sql(text: str) -> str:
       """生成 UNHEX SQL 语句"""
       hex_encoding = text.encode('utf-8').hex().upper()
       return f"UNHEX('{hex_encoding}')"
   
   jianchu = '收'
   sql = f"INSERT INTO daily_fortune_jianchu (jianchu, content, score) VALUES ({generate_unhex_sql(jianchu)}, {generate_unhex_sql(content)}, 90)"
   ```

**预防措施**：
1. **规范更新**：
   - ✅ 所有包含中文字符的数据插入必须使用 `UNHEX`
   - ✅ 所有中文字段查询必须使用 `BINARY` 比较
   - ✅ 数据同步脚本必须验证编码正确性

2. **检查清单**：
   - [ ] 数据插入是否使用 `UNHEX`（中文字符）
   - [ ] 数据查询是否使用 `BINARY` 比较（中文字段）
   - [ ] 数据同步脚本是否验证编码正确性
   - [ ] 是否测试了编码异常场景

3. **代码审查**：
   - 检查所有数据库插入操作（特别是包含中文的）
   - 检查所有数据库查询操作（特别是中文字段匹配）
   - 检查数据同步脚本的编码处理

#### 编码处理标准流程

**数据插入流程**：
```
1. 准备数据（Python Unicode 字符串）
   ↓
2. 转换为 UTF-8 HEX 编码
   ↓
3. 生成 UNHEX SQL 语句
   ↓
4. 执行 SQL（确保编码正确）
   ↓
5. 验证数据编码（查询验证）
```

**数据查询流程**：
```
1. 准备查询条件（Python Unicode 字符串）
   ↓
2. 使用 BINARY 比较确保精确匹配
   ↓
3. 处理查询结果（自动解码）
   ↓
4. 验证结果正确性
```

#### 编码处理检查清单

每次处理包含中文的数据库操作时，必须检查：

- [ ] 数据插入是否使用 `UNHEX`（中文字符）
- [ ] 数据查询是否使用 `BINARY` 比较（中文字段）
- [ ] 数据同步脚本是否验证编码正确性
- [ ] 是否测试了编码异常场景
- [ ] 是否验证了数据在数据库中的实际编码

#### 编码处理工具函数

**Python 工具函数**：
```python
def generate_unhex_sql(text: str) -> str:
    """
    生成 UNHEX SQL 语句
    
    Args:
        text: 要编码的文本（Unicode 字符串）
        
    Returns:
        UNHEX SQL 语句字符串
    """
    hex_encoding = text.encode('utf-8').hex().upper()
    return f"UNHEX('{hex_encoding}')"

def generate_insert_sql(table: str, data: Dict[str, Any]) -> str:
    """
    生成使用 UNHEX 的 INSERT SQL 语句
    
    Args:
        table: 表名
        data: 数据字典（值可以是字符串、数字等）
        
    Returns:
        INSERT SQL 语句
    """
    columns = []
    values = []
    for key, value in data.items():
        columns.append(key)
        if isinstance(value, str):
            values.append(generate_unhex_sql(value))
        else:
            values.append(str(value))
    
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)})"
```

**使用示例**：
```python
# 生成建除数据插入 SQL
jianchu_data = [
    ('收', '能量小结：寓意收获收纳，宜收藏、理财，忌发散之事。', 90),
    ('建', '能量小结：象征建立、开始，宜行事但不宜动土。', 65),
]

for jianchu, content, score in jianchu_data:
    sql = f"INSERT INTO daily_fortune_jianchu (jianchu, content, score, enabled) VALUES ({generate_unhex_sql(jianchu)}, {generate_unhex_sql(content)}, {score}, 1);"
    print(sql)
```

---

### 📋 数据库同步流程

```
┌─────────────────────────────────────────────────────────────┐
│                    数据库同步流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 数据库变更检测（本地）                                   │
│     ├─ 对比本地和生产数据库结构                             │
│     ├─ 检测新增表、新增字段、修改字段                        │
│     └─ 生成变更报告                                         │
│                                                             │
│  2. 生成同步脚本                                             │
│     ├─ 生成 CREATE TABLE 语句（新增表）                     │
│     ├─ 生成 ALTER TABLE 语句（新增字段）                     │
│     └─ 生成回滚脚本（反向操作）                              │
│                                                             │
│  3. 执行数据库同步（Node1 灰度节点）                        │
│     ├─ 上传同步脚本到 Node1                                 │
│     ├─ 执行 SQL 脚本                                        │
│     └─ 验证同步结果                                         │
│                                                             │
│  4. Node1 功能测试                                          │
│     ├─ 如果测试通过 → 继续到步骤5（同步 Node2）             │
│     └─ 如果测试失败 → 回滚数据库变更                        │
│                                                             │
│  5. 执行数据库同步（Node2 生产节点）                        │
│     ├─ 上传同步脚本到 Node2                                 │
│     ├─ 执行 SQL 脚本                                        │
│     └─ 验证同步结果                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 🔧 数据库变更检测

**检测脚本**：`scripts/db/detect_db_changes.py`

**使用方法**：
```bash
# 检测数据库变更并生成同步脚本
python3 scripts/db/detect_db_changes.py --generate-sync-script
```

**检测内容**：
- 新增表（CREATE TABLE）
- 新增字段（ALTER TABLE ADD COLUMN）
- 修改字段（ALTER TABLE MODIFY COLUMN，需要手动确认）
- 新增索引（CREATE INDEX）

**输出文件**：
- `scripts/db/sync_YYYYMMDD_HHMMSS.sql` - 同步脚本
- `scripts/db/rollback/rollback_YYYYMMDD_HHMMSS.sql` - 回滚脚本
- `scripts/db/changes_YYYYMMDD_HHMMSS.json` - 变更信息

### 🔄 数据库同步执行

**同步脚本**：`scripts/db/sync_production_db.sh`

**使用方法**：
```bash
# 同步到 Node1（灰度节点）
bash scripts/db/sync_production_db.sh --node node1 --deployment-id 20250115_143000

# 同步到 Node2（生产节点）
bash scripts/db/sync_production_db.sh --node node2 --deployment-id 20250115_143000

# 预览模式（不执行实际变更）
bash scripts/db/sync_production_db.sh --node node1 --deployment-id 20250115_143000 --dry-run
```

**同步流程**：
1. 上传同步脚本到目标节点
2. 执行 SQL 脚本（使用事务）
3. 验证同步结果
4. 记录同步日志

### 🔙 数据库回滚

**回滚脚本**：`scripts/db/rollback_db.sh`

**使用方法**：
```bash
# 回滚 Node1 数据库
bash scripts/db/rollback_db.sh --node node1 --rollback-file scripts/db/rollback/rollback_20250115_143000.sql

# 预览模式（不执行实际回滚）
bash scripts/db/rollback_db.sh --node node1 --rollback-file scripts/db/rollback/rollback_20250115_143000.sql --dry-run
```

**回滚内容**：
- 删除新增的表（DROP TABLE）
- 删除新增的字段（ALTER TABLE DROP COLUMN）
- 恢复修改的字段（需要手动处理）

### ✅ 数据库同步检查清单

每次数据库变更前必须检查：

- [ ] 数据库变更已检测（运行 `detect_db_changes.py`）
- [ ] 同步脚本已生成（`scripts/db/sync_*.sql`）
- [ ] 回滚脚本已生成（`scripts/db/rollback/rollback_*.sql`）
- [ ] 同步脚本已预览（`--dry-run` 模式）
- [ ] Node1 数据库同步成功
- [ ] Node1 功能测试通过（验证数据库变更不影响功能）
- [ ] Node2 数据库同步成功
- [ ] 双机数据库结构一致

### 🚨 数据库同步注意事项

1. **只增不减原则**
   - 优先使用新增字段，避免删除字段
   - 删除字段需要手动处理，确保数据安全

2. **字段修改谨慎**
   - 修改字段类型可能影响现有数据
   - 需要手动确认并测试

3. **事务保证**
   - 所有同步脚本使用事务（START TRANSACTION / COMMIT）
   - 确保原子性操作

4. **回滚准备**
   - 每次同步前必须生成回滚脚本
   - 回滚脚本必须经过测试验证

5. **数据备份**
   - 重要数据变更前建议手动备份
   - 使用 `mysqldump` 备份关键表

### 📊 数据库同步性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **同步时间** | < 30秒 | 单个节点同步时间 |
| **回滚时间** | < 10秒 | 数据库回滚时间 |
| **一致性** | 100% | 双机数据库结构完全一致 |
| **成功率** | > 99% | 数据库同步成功率 |

### 📚 相关文档

- **数据库变更检测脚本**：`scripts/db/detect_db_changes.py`
- **数据库同步脚本**：`scripts/db/sync_production_db.sh`
- **数据库回滚脚本**：`scripts/db/rollback_db.sh`
- **数据一致性验证**：`scripts/db/verify_data_consistency.py`
- **灰度发布脚本**：`deploy/scripts/grayscale_deploy_production.sh`（集成数据库同步）
- **完整部署流程**：见"🚀 CI/CD 标准流程"章节

---


---

# 配置同步规范 【必须遵守】

### 🔴 核心原则

> **所有配置变更必须通过配置同步机制处理，确保本地、Node1、Node2 配置完全一致，包括 bot_id、支付相关id等所有环境变量。**

### 📋 配置同步流程

```
1. 配置变更检测（本地）
   ├─ 对比本地和生产环境变量文件
   ├─ 检测新增配置项
   ├─ 检测修改的配置项
   ├─ 检测删除的配置项（生产有但本地没有）
   └─ 生成配置变更报告
   ↓
2. 查看配置变更报告
   ├─ 查看新增配置项
   ├─ 查看修改的配置项（敏感信息部分显示）
   └─ 查看删除的配置项
   ↓
3. 执行配置同步（Node1 灰度节点）
   ├─ 备份生产环境配置
   ├─ 上传配置文件到 Node1
   ├─ 验证配置文件格式
   └─ 提示需要重启的服务（如需要）
   ↓
4. Node1 配置验证
   ├─ 验证配置文件格式正确性
   ├─ 验证关键配置项（bot_id、支付相关等）
   └─ 如需要，重启相关服务
   ↓
5. 执行配置同步（Node2 生产节点）
   ├─ 备份生产环境配置
   ├─ 上传配置文件到 Node2
   ├─ 验证配置文件格式
   └─ 提示需要重启的服务（如需要）
   ↓
6. Node2 配置验证
   ├─ 验证配置文件格式正确性
   └─ 确保配置一致性
```

### 🔧 配置变更检测

**检测脚本**：`scripts/config/detect_config_changes.py`

**使用方法**：
```bash
# 检测配置变更
python3 scripts/config/detect_config_changes.py

# 自定义生产环境主机
python3 scripts/config/detect_config_changes.py --prod-host 8.210.52.217

# 输出报告到文件
python3 scripts/config/detect_config_changes.py --output config_changes_report.txt
```

**检测内容**：
- 新增配置项（本地有但生产没有）
- 修改的配置项（值不同）
- 删除的配置项（生产有但本地没有）
- 敏感信息保护（密码、密钥、Token等只显示部分）

**输出报告**：
- 配置变更报告（控制台输出）
- 可选：保存到文件（`--output` 参数）

### 🔄 配置同步执行

**同步脚本**：`scripts/config/sync_production_config.sh`

**使用方法**：
```bash
# 同步到 Node1（灰度节点）
bash scripts/config/sync_production_config.sh --node node1

# 同步到 Node2（生产节点）
bash scripts/config/sync_production_config.sh --node node2

# 预览模式（不执行实际变更）
bash scripts/config/sync_production_config.sh --node node1 --dry-run
```

**同步流程**：
1. 备份生产环境配置文件（`.env.backup.YYYYMMDD_HHMMSS`）
2. 上传本地配置文件到生产环境
3. 验证配置文件格式
4. 提示需要重启的服务（如需要）

### ✅ 配置同步检查清单

每次配置变更前必须检查：

- [ ] 配置变更已检测（运行 `detect_config_changes.py`）
- [ ] 配置变更报告已查看（新增、修改、删除的配置项）
- [ ] 新增配置项已确认（如 bot_id、支付相关id等）
- [ ] 修改配置项已确认（特别是敏感配置）
- [ ] Node1 配置同步成功
- [ ] Node1 配置格式验证通过
- [ ] Node2 配置同步成功
- [ ] Node2 配置格式验证通过
- [ ] 双机配置完全一致
- [ ] 相关服务已重启（如需要）

### 🚨 配置同步注意事项

1. **敏感信息保护**
   - 密码、密钥、Token等敏感信息在报告中只显示部分
   - 同步时确保配置文件权限正确（600）

2. **配置格式验证**
   - 同步后自动验证配置文件格式
   - 格式错误时自动恢复备份

3. **服务重启**
   - 修改应用配置（如 bot_id）可能需要重启 Web 服务
   - 修改数据库配置需要重启数据库服务
   - 修改 Redis 配置需要重启 Redis 服务

4. **配置备份**
   - 每次同步前自动备份生产环境配置
   - 备份文件命名：`.env.backup.YYYYMMDD_HHMMSS`

5. **双机同步**
   - 配置必须同步到双机（Node1 和 Node2）
   - 确保双机配置完全一致

### 📊 配置同步性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **同步时间** | < 10秒 | 单个节点同步时间 |
| **格式验证** | 100% | 配置文件格式验证成功率 |
| **一致性** | 100% | 双机配置完全一致 |
| **成功率** | > 99% | 配置同步成功率 |

### 📚 相关文档

- **配置变更检测脚本**：`scripts/config/detect_config_changes.py`
- **配置同步脚本**：`scripts/config/sync_production_config.sh`
- **增量部署脚本**：`deploy/scripts/incremental_deploy_production.sh`（集成配置检测）
- **环境变量模板**：`env.template`

---


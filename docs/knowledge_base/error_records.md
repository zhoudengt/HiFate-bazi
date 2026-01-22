# HiFate-bazi 问题错误记录本

> **目的**：记录开发过程中遇到的问题及其解决方案，预防类似问题再次发生
> **维护原则**：遇到新问题时主动更新，形成持续改进的知识积累
> **最后更新**：2026-01-22（新增 ERR-CICD-001）

---

## 📋 问题分类索引

| 分类 | 说明 | 问题数量 |
|------|------|----------|
| [API 注册](#api-注册问题) | API 端点注册、路由配置相关 | 1 |
| [gRPC 网关](#grpc-网关问题) | gRPC-Web 网关、端点映射相关 | 1 |
| [Coze API 问题](#coze-api-问题) | Coze API 调用、Bot 配置相关 | 1 |
| [部署问题](#部署问题) | 增量部署、热更新相关 | 1 |
| [CI/CD 问题](#cicd-问题) | GitHub Actions CI/CD 相关 | 1 |
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

## 🔴 Coze API 问题

### ERR-COZE-001：Coze API 返回空内容（感情婚姻接口）

**问题发生日期**：2026-01-06

**问题描述**：
调用感情婚姻接口（`/bazi/marriage-analysis/stream`）时，Coze API 返回空内容，重试 3 次后仍然失败。

**现象**：
```
[WARN]   感情婚姻接口错误: 接口调用失败（已重试 3 次）: Coze API 返回空内容
```

**根因分析**：
1. Coze API 返回了 HTTP 200 响应，但响应中**没有有效内容**
2. 可能原因：
   - **Bot System Prompt 配置问题**：Bot 的 System Prompt 未正确配置，或未包含 `{{input}}` 占位符
   - **输入数据格式问题**：输入数据格式不符合 Bot 期望
   - **过滤逻辑过于严格**：内容被过滤逻辑误过滤（如思考过程过滤）
   - **Bot ID 配置错误**：使用了错误的 Bot ID
   - **Coze API 服务端问题**：暂时性问题（较少见）

**影响范围**：
- `/bazi/marriage-analysis/stream` - 感情婚姻流式分析接口
- 其他使用 `CozeStreamService.stream_custom_analysis()` 的接口（如果遇到相同问题）

**解决方案**：

### 快速诊断（推荐）

1. **运行配置验证工具**：
   ```bash
   python3 scripts/verify_coze_config.py
   ```
   该工具会：
   - 检查数据库配置是否存在
   - 验证 Token 有效性
   - 验证 Bot ID 是否存在
   - 生成详细的验证报告
   - 提供修复建议

2. **运行完整诊断脚本**：
   ```bash
   python3 scripts/diagnose_marriage_api.py
   ```
   该脚本会：
   - 检查配置（Token、Bot ID）
   - 验证 Token 有效性
   - 验证 Bot 配置
   - 获取测试数据
   - 直接测试 Bot API
   - 提供详细的诊断信息和修复建议

3. **使用交互式修复向导**（如果配置有问题）：
   ```bash
   python3 scripts/fix_marriage_bot_config.py
   ```
   该脚本会：
   - 自动检查配置问题
   - 提供交互式修复向导
   - 引导修复 Token、Bot ID 配置
   - 提供 Bot System Prompt 检查指南

### 详细修复步骤

#### 步骤 1: 检查配置

**如果 Token 未配置或无效**：

1. 登录 Coze 平台：https://www.coze.cn
2. 进入个人设置 → API 密钥
3. 创建新的 Token（格式：`pat_xxxxxxxxxxxxx`）
4. 更新数据库配置：
   ```sql
   UPDATE service_configs 
   SET config_value='新Token', updated_at=NOW() 
   WHERE config_key='COZE_ACCESS_TOKEN';
   ```
   或者如果配置不存在：
   ```sql
   INSERT INTO service_configs (config_key, config_value, config_type, description, created_at, updated_at) 
   VALUES ('COZE_ACCESS_TOKEN', '新Token', 'coze', 'Coze API Access Token', NOW(), NOW());
   ```

**如果 Bot ID 未配置或错误**：

1. 登录 Coze 平台：https://www.coze.cn
2. 找到"感情婚姻分析" Bot
3. 复制 Bot ID（数字格式，如：`7587253915310096384`）
4. 更新数据库配置：
   ```sql
   UPDATE service_configs 
   SET config_value='BotID', updated_at=NOW() 
   WHERE config_key='MARRIAGE_ANALYSIS_BOT_ID';
   ```
   或者如果配置不存在：
   ```sql
   INSERT INTO service_configs (config_key, config_value, config_type, description, created_at, updated_at) 
   VALUES ('MARRIAGE_ANALYSIS_BOT_ID', 'BotID', 'coze', '感情婚姻分析 Bot ID', NOW(), NOW());
   ```

#### 步骤 2: 检查 Bot System Prompt

**这是最常见的问题原因**：

1. 登录 Coze 平台：https://www.coze.cn
2. 找到对应的 Bot（通过 Bot ID）
3. 进入 Bot 设置 → System Prompt
4. **关键检查**：确认 System Prompt 包含 `{{input}}` 占位符
5. 如果未配置或配置错误：
   - 打开文档：`docs/需求/Coze_Bot_System_Prompt_感情婚姻分析.md`
   - 复制完整的 System Prompt 内容
   - 粘贴到 Bot 的 System Prompt 设置中
   - **确保包含 `{{input}}` 占位符**
   - 保存设置
6. 验证 Bot 已启用（状态应为"启用"）

#### 步骤 3: 验证输入数据格式

使用测试接口验证数据格式：

```bash
curl -X POST "http://localhost:8001/api/v1/marriage-analysis/test" \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male", "calendar_type": "solar"}'
```

检查返回的 `formatted_data` 格式是否正确，应该是 JSON 字符串格式。

#### 步骤 4: 验证修复

1. **重新运行配置验证**：
   ```bash
   python3 scripts/verify_coze_config.py
   ```
   应该显示所有配置检查通过

2. **运行完整诊断**：
   ```bash
   python3 scripts/diagnose_marriage_api.py
   ```
   应该显示 Bot API 测试通过

3. **测试实际接口**：
   ```bash
   curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
     -H "Content-Type: application/json" \
     -d '{"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male"}'
   ```
   应该能正常返回流式内容

#### 步骤 5: 检查服务日志

如果问题仍然存在，查看服务日志，寻找以下关键信息：
- `⚠️ Coze API 返回空内容`
- `诊断信息: has_content=...`
- `Bot ID=...`
- `Prompt长度: ...`
- `收到 X 行数据，但未提取到有效内容`

查看增强的错误信息，会根据错误类型提供具体的解决方案。

**预防措施**：
1. ✅ 新增 Bot 时，必须配置正确的 System Prompt（包含 `{{input}}` 占位符）
2. ✅ 定期运行诊断脚本验证 Bot 配置
3. ✅ 增强错误日志，记录更多调试信息（已实现）
4. ✅ 在开发环境测试 Bot 配置后再部署到生产环境

**快速排查清单**：

按优先级检查：

1. **配置验证**（最优先）：
   - [ ] 运行 `python3 scripts/verify_coze_config.py` 检查配置
   - [ ] Token 是否存在且有效？
   - [ ] Bot ID 是否存在且有效？

2. **Bot System Prompt**（最常见问题）：
   - [ ] Bot System Prompt 是否包含 `{{input}}` 占位符？（**必须！**）
   - [ ] Bot System Prompt 是否完整（参考文档）？
   - [ ] Bot 是否已启用？

3. **数据格式验证**：
   - [ ] 运行测试接口验证数据格式：`/api/v1/marriage-analysis/test`
   - [ ] 输入数据格式是否符合 Bot 期望？

4. **完整诊断**：
   - [ ] 运行 `python3 scripts/diagnose_marriage_api.py` 完整诊断
   - [ ] 诊断脚本是否通过所有检查？

5. **服务日志检查**：
   - [ ] 查看服务日志中的错误信息
   - [ ] 查看增强的错误提示（提供具体解决方案）

**相关工具和脚本**：

- `scripts/verify_coze_config.py` - **配置验证工具**（快速检查配置）
- `scripts/diagnose_marriage_api.py` - **完整诊断脚本**（详细诊断）
- `scripts/fix_marriage_bot_config.py` - **配置修复向导**（交互式修复）

**相关文件**：
- `server/services/coze_stream_service.py` - Coze 流式服务（已增强错误处理）
- `server/api/v1/marriage_analysis.py` - 感情婚姻分析接口
- `docs/需求/Coze_Bot_System_Prompt_感情婚姻分析.md` - Bot System Prompt 文档

**常见错误码说明**：

| 错误码 | 含义 | 解决方法 |
|--------|------|----------|
| 4101 | Token 错误 | 检查并更新 Token 配置 |
| 4004 | Bot 不存在 | 检查 Bot ID 是否正确 |
| 4028 | 配额用尽 | 等待重置或升级付费计划 |
| 空内容 | Bot System Prompt 问题 | 检查 System Prompt 是否包含 `{{input}}` |

**提交记录**：
- `feat: 增强 Coze API 空内容错误处理和诊断工具`
- `feat: 添加配置验证和修复工具`

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
sshpass -p '${SSH_PASSWORD}' ssh -o ConnectTimeout=30 root@8.210.52.217

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

## 🔴 部署问题

### ERR-DEPLOY-001：违反代码修改流程规范，直接在服务器上修改代码

**问题发生日期**：2026-01-22

**问题描述**：
AI 在修复 Stripe 支付问题时，违反了开发规范，直接在生产服务器上修改代码，而不是遵循标准的"本地开发 → Git提交 → 增量部署"流程。

**现象**：
```
# 错误操作：
1. 直接在服务器上使用 scp 上传文件
   scp services/payment_service/stripe_client.py root@server:/opt/HiFate-bazi/...

2. 直接在服务器上执行 git checkout 撤销修改
   git checkout -- services/payment_service/stripe_client.py

3. 直接在服务器上执行 git pull
   git pull origin master
```

**根因分析**：
1. **未遵循标准流程**：应该使用 `deploy/scripts/incremental_deploy_production.sh` 进行增量部署
2. **未先读部署指南**：规范要求部署前必读 `docs/knowledge_base/deployment_guide.md`
3. **未先读错误记录本**：规范要求开发前必读 `docs/knowledge_base/error_records.md`
4. **急于解决问题**：为了快速修复问题，跳过了标准流程

**影响范围**：
- 破坏了代码版本管理的一致性
- 可能导致服务器代码与 Git 仓库不一致
- 违反了"禁止直接在服务器上修改代码"的核心原则

**解决方案**：
1. ✅ 撤销服务器上的直接修改：`git checkout -- <文件>`
2. ✅ 通过 Git 同步代码：`git pull origin master`
3. ✅ 使用增量部署脚本：`bash deploy/scripts/incremental_deploy_production.sh`
4. ✅ 触发热更新：通过增量部署脚本自动执行

**预防措施**：
1. **开发前必读**：
   - 先读 `docs/knowledge_base/error_records.md` 检查是否有类似问题
   - 先读 `docs/knowledge_base/deployment_guide.md` 了解标准部署流程

2. **严格遵循流程**：
   ```
   本地开发 → Git提交 → 推送远程 → 增量部署 → 验证
   ```

3. **禁止操作清单**：
   - ❌ 禁止使用 `scp` 直接上传文件到服务器
   - ❌ 禁止在服务器上直接执行 `git checkout`、`git pull` 等操作
   - ❌ 禁止在服务器上直接修改代码文件
   - ✅ 必须使用增量部署脚本：`bash deploy/scripts/incremental_deploy_production.sh`

4. **检查清单**（部署前必须确认）：
   - [ ] 代码已在本地测试通过
   - [ ] 代码已提交到 Git
   - [ ] 代码已推送到远程仓库（GitHub 和 Gitee）
   - [ ] 已阅读部署指南和错误记录本
   - [ ] 使用增量部署脚本进行部署
   - [ ] 部署后验证功能正常

**相关文件**：
- `.cursorrules` - 核心原则 0：代码修改流程规范
- `docs/knowledge_base/deployment_guide.md` - 增量部署指南
- `deploy/scripts/incremental_deploy_production.sh` - 增量部署脚本

**提交记录**：`57867ee` - fix(payment): 改进 Stripe 动态导入逻辑，支持运行时安装

---

## 📊 统计信息

| 指标 | 数量 |
|------|------|
| 总问题数 | 5 |
| API 相关 | 1 |
| 部署相关 | 3 |
| 环境相关 | 1 |
| 数据库相关 | 0 |

---

> **维护说明**：
> - AI 在开发过程中遇到新问题时，应主动更新此文档
> - 每次更新后修改"最后更新"日期
> - 定期回顾并清理已过时的问题记录


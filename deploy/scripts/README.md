# HiFate 部署脚本

## 推荐：门控发布（gated_deploy.sh）

门控发布是当前推荐的部署方式，通过 Node2 前哨验证实现物理隔离，确保发布可控可靠。

### 原理

```
Node2（前哨节点，无用户流量）
  ↓ 先部署新代码
  ↓ 运行全量回归测试（23 个接口）
  ↓ 全部通过？
  ├── YES → 继续部署到 Node1（生产节点）
  └── NO  → 停止，Node1 不受任何影响
```

### 常用命令

```bash
# 标准门控发布（推荐）
bash deploy/scripts/gated_deploy.sh

# DRY-RUN：只部署 Node2 跑测试，不动 Node1
bash deploy/scripts/gated_deploy.sh --dry-run

# 紧急模式：跳过 Node2 直接部署 Node1（慎用）
bash deploy/scripts/gated_deploy.sh --skip-node2

# 只跑 Node2 测试，不部署代码
bash deploy/scripts/gated_deploy.sh --test-only

# 回滚 Node1 到上一次成功版本
bash deploy/scripts/gated_deploy.sh --rollback

# 非交互模式（CI/CD 使用）
bash deploy/scripts/gated_deploy.sh --non-interactive
```

### 前置条件

1. 代码已提交并推送到 master 分支
2. 环境变量已配置（通过 `deploy.conf` 或直接 export）：
   - `NODE1_PUBLIC_IP`, `NODE1_PRIVATE_IP`
   - `NODE2_PUBLIC_IP`, `NODE2_PRIVATE_IP`
   - `SSH_PASSWORD`, `MYSQL_PASSWORD`
3. 本地可以通过 SSH 连接到 Node1（`ssh hifate-node1`）

### 部署日志

所有部署记录保存在 `deploy/logs/`（已被 .gitignore 忽略）：
- `deploy_history.jsonl` - 追加式历史记录
- `deploy_<ID>.json` - 单次部署报告
- `last_success_commit.txt` - 回滚参考点

---

## Phase 2: 代码目录隔离（可选增强）

启用 Phase 2 后，`git pull` 不再直接操作容器挂载的目录，实现完全的代码隔离。

### 初始化（一次性，零停机）

```bash
bash deploy/scripts/init_staging.sh          # 在 Node1 创建 staging 目录
bash deploy/scripts/init_staging.sh --node2  # 同时初始化 Node2
bash deploy/scripts/init_staging.sh --check  # 检查状态
```

### 目录结构

| 路径 | 作用 | 容器可见 |
|------|------|----------|
| `/opt/HiFate-bazi/` | 容器挂载源（live） | 是 |
| `/opt/HiFate-bazi-staging/` | Git 仓库（git pull） | 否 |
| `/opt/HiFate-bazi-rollback/` | 上一版本备份 | 否 |

### 工作原理

初始化后 `gated_deploy.sh` 自动检测并启用隔离模式：

```
git pull → staging/（容器看不到）
  ↓ 语法验证（还没进 live）
  ↓ 备份 live → rollback（硬链接，瞬间）
  ↓ rsync staging → live（增量，<3s）
  ↓ 热更新
  ↓ 验证失败？rsync rollback → live（秒级回滚）
```

不影响 Phase 1：未初始化 staging 目录时，脚本自动降级为直接 git pull。

---

## 其他脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `gated_deploy.sh` | **门控发布（推荐，自动识别 Phase 1/2）** | 活跃 |
| `init_staging.sh` | 一次性初始化 staging 目录（Phase 2） | 活跃 |
| `incremental_deploy_production.sh` | 增量部署（CI/CD 用） | 活跃 |
| `grayscale_deploy_production.sh` | 灰度发布（先 Node1 后 Node2） | 活跃 |
| `rollback.sh` | 独立回滚脚本 | 活跃 |
| `deploy_production.sh` | 完整部署（含初始化） | 活跃 |
| `post_deploy_test.sh` | 部署后测试 | 活跃 |
| `health-check.sh` | 健康检查 | 活跃 |

## 函数库

| 文件 | 内容 |
|------|------|
| `lib/common.sh` | 公共函数（日志、健康检查、版本管理） |
| `lib/gate_check.sh` | 门控检查函数（语法验证、热更新、回归测试、回滚） |

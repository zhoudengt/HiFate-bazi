# GitHub Actions 配置分析报告

## 📋 项目 Git 配置

### Git 远程仓库

```
origin  (GitHub): git@github.com:zhoudengt/HiFate-bazi.git
gitee   (Gitee):  https://gitee.com/zhoudengtang/hifate-prod.git
```

**用途说明**：
- `origin`：主要代码仓库（GitHub），用于 CI/CD 自动部署
- `gitee`：国内镜像仓库（Gitee），用于国内服务器快速拉取代码

---

## 🔍 GitHub Actions Workflows 分析

项目中共有 **7 个 workflow 文件**，都在监听 `master` 分支的 push 事件。

### 1. `build-and-push.yml` ✅ **有用**

**作用**：构建 Docker 镜像并推送到阿里云容器镜像服务 (ACR)

**触发条件**：
- 推送到 `master` 或 `develop` 分支
- 手动触发

**功能**：
- 清理磁盘空间
- 构建 Docker 镜像（linux/amd64）
- 推送到 ACR（如果配置了 secrets）

**需要的 Secrets**：
- `ACR_REGISTRY`
- `ACR_NAMESPACE`
- `ACR_USERNAME`
- `ACR_PASSWORD`

**状态**：✅ **推荐保留**（核心构建流程）

---

### 2. `ci.yml` ✅ **有用**

**作用**：CI/CD 管道 - 代码质量检查和单元测试

**触发条件**：
- 推送到 `master` 或 `develop` 分支
- Pull Request 到 `master` 或 `develop`
- 手动触发

**功能**：
- 代码质量检查（Black、isort、pylint、mypy）
- 代码审查检查（6项核心检查）
- 单元测试
- 测试覆盖率报告

**需要的 Secrets**：无（不需要额外 secrets）

**状态**：✅ **推荐保留**（代码质量保障）

---

### 3. `deploy-test.yml` ✅ **有用**

**作用**：自动部署到测试环境

**触发条件**：
- 推送到 `master` 分支
- 手动触发

**功能**：
- 构建 Docker 镜像
- 推送到 ACR
- 部署到测试服务器（123.57.216.15）
- 健康检查和回滚

**需要的 Secrets**：
- `ACR_REGISTRY`
- `ACR_NAMESPACE`
- `ACR_USERNAME`
- `ACR_PASSWORD`
- `TEST_SSH_PRIVATE_KEY`
- `TEST_SERVER_HOST`
- `TEST_SERVER_USER`

**状态**：✅ **推荐保留**（测试环境自动化部署）

---

### 4. `deploy-aliyun-dual.yml` ✅ **有用**

**作用**：部署到阿里云双节点（生产环境）

**触发条件**：
- 推送到 `master` 分支
- 手动触发（可选择部署目标：both/node1/node2）

**功能**：
- 构建 Docker 镜像
- 推送到 ACR
- 滚动部署到 Node1（172.18.121.222）
- 滚动部署到 Node2（172.18.121.223）
- 双机健康检查和回滚

**需要的 Secrets**：
- `ACR_REGISTRY`（或使用默认值：`registry.cn-hangzhou.aliyuncs.com`）
- `ACR_NAMESPACE`（或使用默认值：`hifate`）
- `ACR_USERNAME`
- `ACR_PASSWORD`
- `ALIYUN_NODE1_SSH_KEY`
- `ALIYUN_NODE1_HOST`
- `ALIYUN_NODE1_USER`
- `ALIYUN_NODE2_SSH_KEY`
- `ALIYUN_NODE2_HOST`
- `ALIYUN_NODE2_USER`

**状态**：✅ **推荐保留**（生产环境双机部署）

---

### 5. `deploy-production.yml` ⚠️ **可能重复**

**作用**：部署到生产环境（单节点）

**触发条件**：
- 手动触发（workflow_dispatch）
- 等待 `build-and-push.yml` 完成（workflow_run）

**功能**：
- 备份数据库
- 从 ACR 拉取镜像
- 部署到生产服务器
- 健康检查和回滚

**需要的 Secrets**：
- `ACR_REGISTRY`
- `ACR_NAMESPACE`
- `ACR_USERNAME`
- `ACR_PASSWORD`
- `PROD_SSH_PRIVATE_KEY`
- `PROD_SERVER_HOST`
- `PROD_SERVER_USER`

**问题**：
- ⚠️ 与 `deploy-aliyun-dual.yml` 功能重复
- ⚠️ 仅支持单节点部署（不适用于双机架构）
- ⚠️ 使用的 secrets 名称不同（`PROD_*` vs `ALIYUN_NODE*`）

**状态**：❌ **建议删除或禁用**（已被 `deploy-aliyun-dual.yml` 替代）

---

### 6. `deploy-develop.yml` ✅ **有用**

**作用**：部署到开发环境

**触发条件**：
- 推送到 `develop` 分支
- 手动触发

**功能**：
- 拉取最新代码
- 构建基础镜像（如果不存在）
- 构建应用镜像
- 部署到开发服务器

**需要的 Secrets**：
- `DEV_SSH_PRIVATE_KEY`
- `DEV_SERVER_HOST`
- `DEV_SERVER_USER`

**状态**：✅ **推荐保留**（开发环境自动化部署）

---

### 7. `test-acr-config.yml` ✅ **有用**

**作用**：测试 ACR 配置是否正确

**触发条件**：
- 仅手动触发（workflow_dispatch）

**功能**：
- 检查 ACR secrets 配置
- 测试 Docker 登录
- 可选：构建并推送测试镜像

**需要的 Secrets**：
- `ACR_REGISTRY`
- `ACR_NAMESPACE`
- `ACR_USERNAME`
- `ACR_PASSWORD`

**状态**：✅ **推荐保留**（用于诊断 ACR 配置问题）

---

## 📊 Workflow 对比分析

### 重复的 Workflow

| Workflow | 用途 | 状态 | 建议 |
|---------|------|------|------|
| `deploy-production.yml` | 单节点生产部署 | ⚠️ 重复 | ❌ **删除或禁用** |
| `deploy-aliyun-dual.yml` | 双节点生产部署 | ✅ 推荐 | ✅ **保留** |

**原因**：
- `deploy-aliyun-dual.yml` 支持双机部署，更符合当前架构
- `deploy-production.yml` 仅支持单节点，已过时
- 两个 workflow 监听同一个分支，会同时触发，造成资源浪费

### Workflow 触发关系

```
推送代码到 master
    ↓
┌─────────────────────────────────────┐
│  同时触发多个 workflow（并发执行）    │
└─────────────────────────────────────┘
    ├─ build-and-push.yml          ✅ 构建镜像
    ├─ ci.yml                      ✅ 代码检查
    ├─ deploy-test.yml             ✅ 测试环境部署
    ├─ deploy-aliyun-dual.yml      ✅ 生产环境部署
    └─ deploy-production.yml       ❌ 重复（应禁用）
```

---

## ❌ 报错原因分析

根据 GitHub Actions 截图显示，所有 workflow 都在失败（commit: `e8179f6`）。

### 可能的原因

#### 1. **Secrets 未配置**（最可能）

所有 workflow 都需要 GitHub Secrets 配置，如果 secrets 缺失或配置错误，会导致失败。

**需要检查的 Secrets**：

**ACR 相关**（4个）：
- `ACR_REGISTRY` - 阿里云容器镜像服务地址
- `ACR_NAMESPACE` - 命名空间
- `ACR_USERNAME` - 用户名（AccessKey ID）
- `ACR_PASSWORD` - 密码（AccessKey Secret）

**SSH 相关**（测试环境 - 3个）：
- `TEST_SSH_PRIVATE_KEY` - 测试服务器 SSH 私钥
- `TEST_SERVER_HOST` - 测试服务器地址（123.57.216.15）
- `TEST_SERVER_USER` - 测试服务器用户名（通常是 `root`）

**SSH 相关**（生产环境双节点 - 6个）：
- `ALIYUN_NODE1_SSH_KEY` - Node1 SSH 私钥
- `ALIYUN_NODE1_HOST` - Node1 地址（8.210.52.217 或 172.18.121.222）
- `ALIYUN_NODE1_USER` - Node1 用户名（通常是 `root`）
- `ALIYUN_NODE2_SSH_KEY` - Node2 SSH 私钥
- `ALIYUN_NODE2_HOST` - Node2 地址（47.243.160.43 或 172.18.121.223）
- `ALIYUN_NODE2_USER` - Node2 用户名（通常是 `root`）

**SSH 相关**（开发环境 - 3个，可选）：
- `DEV_SSH_PRIVATE_KEY` - 开发服务器 SSH 私钥
- `DEV_SERVER_HOST` - 开发服务器地址
- `DEV_SERVER_USER` - 开发服务器用户名

#### 2. **ACR 配置错误**

如果 ACR secrets 配置错误（如地址、用户名、密码不正确），会导致：
- 构建镜像失败（无法推送）
- 部署失败（无法拉取镜像）

#### 3. **SSH 密钥配置错误**

如果 SSH 密钥配置错误或服务器地址不正确，会导致：
- 无法连接到服务器
- 部署失败

#### 4. **Docker 镜像构建失败**

如果 Dockerfile 有问题或依赖缺失，会导致：
- 构建阶段失败
- 后续部署无法进行

---

## 🔧 修复建议

### 1. **禁用重复的 Workflow**

**立即操作**：禁用或删除 `deploy-production.yml`

**方法 1**：删除文件（推荐）
```bash
rm .github/workflows/deploy-production.yml
git add .github/workflows/deploy-production.yml
git commit -m "chore: 删除重复的生产环境部署 workflow"
git push origin master
```

**方法 2**：修改触发条件为禁用
```yaml
# 在 deploy-production.yml 开头添加注释，并修改触发条件
on:
  workflow_dispatch:  # 仅手动触发，不会自动触发
  # push:  # 注释掉自动触发
  #   branches: [ master ]
```

### 2. **检查并配置 GitHub Secrets**

**访问 GitHub Secrets 页面**：
1. 打开仓库：https://github.com/zhoudengt/HiFate-bazi
2. 进入 `Settings` > `Secrets and variables` > `Actions`
3. 检查并配置所有需要的 secrets

**配置清单**：

**必须配置的 Secrets**（如果使用 CI/CD）：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `ACR_REGISTRY` | 阿里云容器镜像服务地址 | `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com` |
| `ACR_NAMESPACE` | 命名空间 | `hifate-bazi-namespaces` |
| `ACR_USERNAME` | AccessKey ID | `LTAI5...` |
| `ACR_PASSWORD` | AccessKey Secret | `...` |
| `TEST_SSH_PRIVATE_KEY` | 测试服务器 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `TEST_SERVER_HOST` | 测试服务器地址 | `123.57.216.15` |
| `TEST_SERVER_USER` | 测试服务器用户名 | `root` |
| `ALIYUN_NODE1_SSH_KEY` | Node1 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `ALIYUN_NODE1_HOST` | Node1 地址 | `8.210.52.217` |
| `ALIYUN_NODE1_USER` | Node1 用户名 | `root` |
| `ALIYUN_NODE2_SSH_KEY` | Node2 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `ALIYUN_NODE2_HOST` | Node2 地址 | `47.243.160.43` |
| `ALIYUN_NODE2_USER` | Node2 用户名 | `root` |

**生成 SSH 私钥**（如果还没有）：
```bash
# 在本地生成 SSH 密钥对
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_key

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/github_actions_key.pub root@123.57.216.15

# 将私钥内容复制到 GitHub Secrets
cat ~/.ssh/github_actions_key
# 复制输出的内容到 GitHub Secrets
```

### 3. **测试 ACR 配置**

**使用 test-acr-config.yml 测试**：
1. 在 GitHub Actions 页面点击 `🧪 Test ACR Configuration`
2. 选择 `Run workflow`
3. 选择测试类型：`login_only`（仅测试登录）
4. 查看测试结果

### 4. **逐步启用 Workflow**

**推荐顺序**：
1. ✅ 先启用 `test-acr-config.yml`（手动触发，测试配置）
2. ✅ 再启用 `build-and-push.yml`（构建镜像）
3. ✅ 然后启用 `ci.yml`（代码检查）
4. ✅ 最后启用 `deploy-test.yml` 和 `deploy-aliyun-dual.yml`（部署）

**临时禁用自动触发**（如果不想每次 push 都触发）：
```yaml
# 在各个 workflow 文件中，注释掉 push 触发条件
on:
  # push:
  #   branches: [ master ]
  workflow_dispatch:  # 仅手动触发
```

---

## 📋 推荐的 Workflow 配置

### 当前架构推荐配置

**保留的 Workflow**（5个）：
1. ✅ `build-and-push.yml` - 构建镜像（核心）
2. ✅ `ci.yml` - 代码检查（质量保障）
3. ✅ `deploy-test.yml` - 测试环境部署
4. ✅ `deploy-aliyun-dual.yml` - 生产环境部署（双机）
5. ✅ `test-acr-config.yml` - ACR 配置测试（诊断工具）

**删除的 Workflow**（1个）：
- ✅ `deploy-production.yml` - 已删除（与 `deploy-aliyun-dual.yml` 重复）

**可选的 Workflow**（1个）：
- ⚠️ `deploy-develop.yml` - 如果有开发环境服务器，保留；否则删除

---

## 🎯 快速修复步骤

### 步骤 1：删除重复的 Workflow

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
rm .github/workflows/deploy-production.yml
git add .github/workflows/deploy-production.yml
git commit -m "chore: 删除重复的生产环境部署 workflow"
git push origin master
```

### 步骤 2：配置 GitHub Secrets

1. 访问 https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions
2. 点击 `New repository secret`
3. 依次添加所有需要的 secrets（参考上面的配置清单）

### 步骤 3：测试配置

1. 在 GitHub Actions 页面手动触发 `🧪 Test ACR Configuration`
2. 选择测试类型：`login_only`
3. 查看测试结果

### 步骤 4：验证修复

1. 推送一个小改动到 master 分支
2. 查看 GitHub Actions 页面，确认 workflow 执行情况
3. 如果还有失败，查看具体错误日志

---

## 📝 总结

### 问题汇总

1. **重复的 Workflow**：`deploy-production.yml` 与 `deploy-aliyun-dual.yml` 功能重复
2. **Secrets 未配置**：所有 workflow 都需要 GitHub Secrets，可能未配置或配置错误
3. **触发过于频繁**：所有 workflow 都监听 master 分支，每次 push 都会触发

### 优化方案（已实施）

**采用“GitHub Actions 构建 + 增量部署脚本部署”的架构**：

1. ✅ **GitHub Actions 负责构建**：
   - `build-and-push.yml` - 自动构建镜像并推送到 ACR（保留自动触发）
   - `ci.yml` - 自动代码质量检查（保留自动触发）

2. ✅ **增量部署脚本负责部署**：
   - 使用 `incremental_deploy_production.sh` 进行部署（手动控制）
   - 零停机部署（热更新）
   - 快速部署（30秒-2分钟）

3. ✅ **禁用自动部署 Workflows**：
   - `deploy-test.yml` - 已禁用自动触发（保留为手动触发）
   - `deploy-aliyun-dual.yml` - 已禁用自动触发（保留为手动触发）
   - `deploy-production.yml` - ✅ 已删除（功能重复且已过时）

### 优化后的优势

1. **构建自动化**：每次 push 自动构建镜像
2. **部署可控**：手动控制部署时机，避免误部署
3. **零停机部署**：使用热更新，服务不中断
4. **快速部署**：30秒-2分钟完成部署
5. **减少 Secrets**：只需要 ACR 相关 secrets，不需要 SSH keys

### 下一步行动

1. ✅ **已优化**：禁用自动部署 workflows 的自动触发
2. **配置 Secrets**：只需要配置 ACR 相关的 secrets（4个）
3. **测试验证**：使用 test-acr-config.yml 测试配置
4. **使用增量部署**：使用 `bash deploy/scripts/incremental_deploy_production.sh` 进行部署

**详细优化方案请参考**：`docs/GitHub Actions优化方案.md`


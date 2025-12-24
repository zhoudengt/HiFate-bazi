# GitHub Actions 优化方案

## 🎯 优化原则

**构建与部署分离**：
- ✅ **GitHub Actions 负责构建**：利用 GitHub 的免费构建资源，构建 Docker 镜像并推送到 ACR
- ✅ **增量部署脚本负责部署**：使用热更新实现零停机部署，更灵活可控

## 📋 优化后的 Workflow 配置

### ✅ 保留并启用的 Workflows

#### 1. `build-and-push.yml` ✅ **保留（自动触发）**

**作用**：构建 Docker 镜像并推送到 ACR

**触发条件**：
- ✅ 推送到 `master` 或 `develop` 分支（自动触发）
- ✅ 手动触发（workflow_dispatch）

**功能**：
- 清理磁盘空间
- 构建 Docker 镜像（linux/amd64）
- 推送到 ACR

**需要的 Secrets**：
- `ACR_REGISTRY`
- `ACR_NAMESPACE`
- `ACR_USERNAME`
- `ACR_PASSWORD`

**状态**：✅ **自动触发**（每次 push 自动构建镜像）

---

#### 2. `ci.yml` ✅ **保留（自动触发）**

**作用**：CI/CD 管道 - 代码质量检查和单元测试

**触发条件**：
- ✅ 推送到 `master` 或 `develop` 分支（自动触发）
- ✅ Pull Request 到 `master` 或 `develop`（自动触发）
- ✅ 手动触发

**功能**：
- 代码质量检查（Black、isort、pylint、mypy）
- 代码审查检查（6项核心检查）
- 单元测试
- 测试覆盖率报告

**需要的 Secrets**：无

**状态**：✅ **自动触发**（代码质量保障）

---

#### 3. `test-acr-config.yml` ✅ **保留（仅手动触发）**

**作用**：测试 ACR 配置是否正确

**触发条件**：
- ✅ 仅手动触发（workflow_dispatch）

**功能**：
- 检查 ACR secrets 配置
- 测试 Docker 登录
- 可选：构建并推送测试镜像

**需要的 Secrets**：
- `ACR_REGISTRY`
- `ACR_NAMESPACE`
- `ACR_USERNAME`
- `ACR_PASSWORD`

**状态**：✅ **手动触发**（诊断工具）

---

### ⚠️ 已禁用自动触发的 Workflows

#### 4. `deploy-test.yml` ⚠️ **已禁用自动触发（仅手动触发）**

**作用**：部署到测试环境

**触发条件**：
- ❌ 推送到 `master` 分支（已禁用）
- ✅ 手动触发（workflow_dispatch）

**说明**：
- 已禁用自动触发，避免每次 push 都自动部署
- 如需部署，使用增量部署脚本：`bash deploy/scripts/incremental_deploy_production.sh`
- 保留此 workflow 作为参考或紧急情况使用

**状态**：⚠️ **已禁用自动触发**（保留为手动触发）

---

#### 5. `deploy-aliyun-dual.yml` ⚠️ **已禁用自动触发（仅手动触发）**

**作用**：部署到阿里云双节点（生产环境）

**触发条件**：
- ❌ 推送到 `master` 分支（已禁用）
- ✅ 手动触发（workflow_dispatch）

**说明**：
- 已禁用自动触发，避免每次 push 都自动部署到生产环境
- 推荐使用增量部署脚本：`bash deploy/scripts/incremental_deploy_production.sh`
- 保留此 workflow 作为参考或紧急情况使用

**状态**：⚠️ **已禁用自动触发**（保留为手动触发）

---

#### 6. `deploy-production.yml` ❌ **已删除**

**作用**：部署到生产环境（单节点，已过时）

**说明**：
- ❌ 已删除（与 `deploy-aliyun-dual.yml` 功能重复）
- ❌ 仅支持单节点部署，不符合当前双机架构
- ❌ 已被增量部署脚本替代

**状态**：❌ **已删除**

---

#### 7. `deploy-develop.yml` ⚠️ **保留（根据实际情况）**

**作用**：部署到开发环境

**触发条件**：
- ✅ 推送到 `develop` 分支（自动触发）
- ✅ 手动触发

**说明**：
- 如果有开发环境服务器，保留此 workflow
- 如果没有开发环境，可以禁用或删除

**状态**：⚠️ **根据实际情况决定**

---

## 🚀 推荐的工作流程

### 日常代码更新流程（90% 的情况）

```
1. 本地开发
   ↓
2. 提交代码
   git add .
   git commit -m "feat: 新功能"
   ↓
3. 推送到 GitHub
   git push origin master
   ↓
4. GitHub Actions 自动执行
   ├─ build-and-push.yml ✅ 构建镜像并推送到 ACR（自动）
   └─ ci.yml ✅ 代码质量检查（自动）
   ↓
5. 使用增量部署脚本部署（手动）
   bash deploy/scripts/incremental_deploy_production.sh
   ↓
6. 完成部署（零停机，30秒-2分钟）
```

**优势**：
- ✅ 自动构建镜像（利用 GitHub 免费资源）
- ✅ 自动代码检查（质量保障）
- ✅ 手动控制部署时机（更灵活）
- ✅ 零停机部署（热更新）
- ✅ 快速部署（30秒-2分钟）

---

### 依赖变更流程（需要完整部署的情况）

```
1. 修改 requirements.txt 或 Dockerfile
   ↓
2. 提交并推送
   git add .
   git commit -m "chore: 更新依赖"
   git push origin master
   ↓
3. GitHub Actions 自动构建镜像
   build-and-push.yml ✅ 构建新镜像并推送到 ACR
   ↓
4. 手动触发完整部署（如果需要）
   - 在 GitHub Actions 页面手动触发 deploy-aliyun-dual.yml
   - 或使用服务器上的完整部署脚本
   ↓
5. 完成部署
```

---

## 📊 优化前后对比

| 对比项 | 优化前 | 优化后 |
|--------|--------|--------|
| **构建** | GitHub Actions（自动） | GitHub Actions（自动）✅ |
| **代码检查** | GitHub Actions（自动） | GitHub Actions（自动）✅ |
| **部署** | GitHub Actions（自动）❌ | 增量部署脚本（手动）✅ |
| **部署速度** | 8-15分钟（构建+部署） | 30秒-2分钟（仅部署） |
| **服务中断** | 可能有短暂中断 | 零中断 |
| **部署控制** | 每次 push 自动部署 | 手动控制部署时机 |
| **Secrets 需求** | 需要 SSH keys | 不需要 SSH keys（增量部署使用密码） |

---

## ✅ 优化后的优势

1. **构建自动化**：每次 push 自动构建镜像，无需手动操作
2. **代码质量保障**：每次 push 自动进行代码检查
3. **部署可控**：手动控制部署时机，避免误部署
4. **零停机部署**：使用热更新，服务不中断
5. **快速部署**：30秒-2分钟完成部署（vs 8-15分钟）
6. **减少 Secrets**：不需要配置 SSH keys 到 GitHub Secrets

---

## 🔧 需要的 GitHub Secrets 配置

优化后，只需要配置 **ACR 相关的 Secrets**（用于构建镜像）：

| Secret 名称 | 说明 | 是否必需 |
|------------|------|---------|
| `ACR_REGISTRY` | 阿里云容器镜像服务地址 | ✅ 必需 |
| `ACR_NAMESPACE` | 命名空间 | ✅ 必需 |
| `ACR_USERNAME` | AccessKey ID | ✅ 必需 |
| `ACR_PASSWORD` | AccessKey Secret | ✅ 必需 |

**不再需要的 Secrets**（增量部署脚本使用密码登录）：
- ❌ `TEST_SSH_PRIVATE_KEY`
- ❌ `ALIYUN_NODE1_SSH_KEY`
- ❌ `ALIYUN_NODE2_SSH_KEY`
- ❌ 其他 SSH 相关的 secrets

---

## 📝 下一步操作

### 1. 验证优化效果

```bash
# 推送代码，查看 GitHub Actions 是否只触发构建和代码检查
git push origin master

# 查看 GitHub Actions 页面，确认只有以下 workflow 自动触发：
# - ✅ build-and-push.yml
# - ✅ ci.yml
# - ❌ deploy-test.yml（不会自动触发）
# - ❌ deploy-aliyun-dual.yml（不会自动触发）
```

### 2. 测试增量部署脚本

```bash
# 测试增量部署脚本
bash deploy/scripts/incremental_deploy_production.sh
```

### 3. 清理不需要的 Workflow（已完成）

已删除以下文件：
- ✅ `deploy-production.yml`（已删除，功能重复且已过时）

---

## 🎯 总结

**优化后的架构**：
- ✅ **GitHub Actions**：构建镜像 + 代码检查（自动化）
- ✅ **增量部署脚本**：部署代码（手动控制，零停机）

**核心优势**：
- 构建自动化，无需手动操作
- 部署可控，避免误部署
- 零停机部署，服务不中断
- 快速部署，30秒-2分钟完成


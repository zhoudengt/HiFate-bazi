# GitHub Container Registry 部署方案（方案 B）

> 使用 GitHub Actions 构建镜像并推送到 GitHub Container Registry，服务器直接拉取镜像部署

## 🎯 方案概述

### 架构流程

```
开发者推送代码
    ↓
GitHub Actions (build-and-push.yml)
    ├─ 构建 Docker 镜像
    └─ 推送到 GitHub Container Registry (ghcr.io)
         ↓
GitHub Actions (deploy-production.yml / deploy-test.yml)
    ├─ SSH 到服务器
    ├─ 登录 GitHub Container Registry
    ├─ 拉取最新镜像
    └─ 启动容器（零停机部署）
```

### 优势

| 优势 | 说明 |
|------|------|
| **快速部署** | 服务器只需拉取镜像（10-20秒），无需构建（5-10分钟） |
| **镜像复用** | 同一镜像可用于测试、生产、回滚 |
| **资源节省** | 构建在 GitHub Actions 中完成，不占用服务器资源 |
| **版本管理** | 每个 commit 都有对应的镜像标签 |
| **缓存优化** | GitHub Actions 使用构建缓存，加速构建 |

---

## 📋 环境说明

| 环境 | 服务器地址 | 分支 | Workflow |
|------|-----------|------|----------|
| **开发** | 本地 | develop | - |
| **测试** | 123.57.216.15 | master | `deploy-test.yml` |
| **生产** | 待定 | master | `deploy-production.yml` |

---

## 🚀 快速开始

### 1. 配置 GitHub Secrets

访问：https://github.com/your-username/HiFate-bazi/settings/secrets/actions

#### 必需 Secrets

**测试环境**：
- `TEST_SSH_PRIVATE_KEY` - 测试服务器 SSH 私钥
- `TEST_SERVER_HOST` - `123.57.216.15`
- `TEST_SERVER_USER` - `root`

**生产环境**（待配置）：
- `PROD_SSH_PRIVATE_KEY` - 生产服务器 SSH 私钥
- `PROD_SERVER_HOST` - 生产服务器地址（待定）
- `PROD_SERVER_USER` - `root`

**可选 Secrets**：
- `GHCR_TOKEN` - GitHub Personal Access Token（如果有 packages:write 权限，推荐使用）

> 注意：如果不配置 `GHCR_TOKEN`，系统会使用 `GITHUB_TOKEN`（自动提供，但权限可能受限）

---

### 2. 首次部署流程

#### 步骤 1：推送代码触发构建

```bash
git checkout master
git push origin master
```

#### 步骤 2：查看构建状态

访问：https://github.com/your-username/HiFate-bazi/actions

应该看到两个 workflow：
1. **🐳 Build and Push Docker Image** - 构建并推送镜像
2. **🧪 Deploy to Test Environment** - 部署到测试环境

#### 步骤 3：验证部署

```bash
# SSH 到测试服务器
ssh root@123.57.216.15

# 检查容器状态
cd /opt/HiFate-bazi
docker-compose ps

# 测试健康检查
curl http://localhost:8001/health
```

---

## 🔧 服务器端配置

### 1. 登录 GitHub Container Registry

在服务器上配置登录：

```bash
# 方式 1：使用 Personal Access Token（推荐）
echo "YOUR_GHCR_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# 方式 2：使用 GitHub Actions 自动登录（在 workflow 中已配置）
```

### 2. 拉取镜像测试

```bash
# 拉取最新镜像
docker pull ghcr.io/your-username/hifate-bazi:master

# 查看镜像
docker images | grep hifate-bazi
```

### 3. 使用镜像启动服务

```bash
cd /opt/HiFate-bazi

# 使用镜像启动（不构建）
DOCKER_IMAGE=ghcr.io/your-username/hifate-bazi:master \
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.image.yml up -d
```

---

## 📊 Workflow 说明

### 1. build-and-push.yml

**功能**：构建 Docker 镜像并推送到 GitHub Container Registry

**触发条件**：
- 推送到 `master` 或 `develop` 分支
- 手动触发

**镜像标签**：
- `ghcr.io/owner/repo/hifate-bazi:latest` - 最新版本
- `ghcr.io/owner/repo/hifate-bazi:master` - master 分支
- `ghcr.io/owner/repo/hifate-bazi:develop` - develop 分支
- `ghcr.io/owner/repo/hifate-bazi:sha-xxxxx` - commit SHA

### 2. deploy-test.yml

**功能**：部署到测试环境（123.57.216.15）

**触发条件**：
- 推送到 `master` 分支
- 手动触发

**部署流程**：
1. 等待镜像构建完成
2. SSH 到测试服务器
3. 登录 GitHub Container Registry
4. 拉取最新镜像
5. 滚动更新服务（零停机）
6. 健康检查

### 3. deploy-production.yml

**功能**：部署到生产环境

**触发条件**：
- 推送到 `master` 分支
- 手动触发

**部署流程**：
1. 备份数据库
2. 等待镜像构建完成
3. SSH 到生产服务器
4. 登录 GitHub Container Registry
5. 拉取最新镜像
6. 滚动更新服务（零停机）
7. 健康检查
8. 创建发布标签

---

## 🔄 日常使用

### 开发流程

```bash
# 1. 本地开发
git checkout develop
# ... 修改代码 ...

# 2. 提交并推送
git add .
git commit -m "[新增] 功能描述"
git push origin develop

# 3. 合并到 master（触发测试环境部署）
git checkout master
git merge develop
git push origin master
```

### 查看部署状态

```bash
# 访问 GitHub Actions
# https://github.com/your-username/HiFate-bazi/actions

# 查看镜像
# https://github.com/your-username/HiFate-bazi/pkgs/container/hifate-bazi
```

### 手动触发部署

1. 访问：https://github.com/your-username/HiFate-bazi/actions
2. 选择对应的 workflow
3. 点击 "Run workflow"
4. 选择分支并运行

---

## 🔐 权限配置

### GitHub Container Registry 权限

默认情况下，GitHub Actions 的 `GITHUB_TOKEN` 有 `packages:write` 权限，但如果是私有仓库，可能需要额外配置。

**检查权限**：
1. 访问：https://github.com/your-username/HiFate-bazi/settings/actions
2. 查看 "Workflow permissions"
3. 确保 "Read and write permissions" 已启用

**使用 Personal Access Token**（推荐）：
1. 创建 Token：https://github.com/settings/tokens
2. 权限：`write:packages`, `read:packages`, `delete:packages`
3. 添加到 Secrets：`GHCR_TOKEN`

---

## 🐛 故障排查

### 问题 1：镜像构建失败

**症状**：`build-and-push.yml` 失败

**解决方案**：
```bash
# 查看构建日志
# 在 GitHub Actions 中查看详细错误

# 常见问题：
# 1. Dockerfile 语法错误
# 2. 依赖安装失败
# 3. 权限不足
```

### 问题 2：无法拉取镜像

**症状**：`docker pull` 失败，提示 "unauthorized"

**解决方案**：
```bash
# 1. 检查登录状态
docker login ghcr.io

# 2. 检查镜像权限
# 访问：https://github.com/your-username/HiFate-bazi/pkgs/container/hifate-bazi
# 确保镜像可见性设置正确

# 3. 使用 Personal Access Token
echo "YOUR_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### 问题 3：部署时找不到镜像

**症状**：`docker pull` 提示 "manifest unknown"

**解决方案**：
```bash
# 1. 检查镜像标签是否正确
docker pull ghcr.io/owner/repo/hifate-bazi:master

# 2. 尝试使用 latest 标签
docker pull ghcr.io/owner/repo/hifate-bazi:latest

# 3. 检查 build-and-push workflow 是否成功
```

### 问题 4：容器启动失败

**症状**：镜像拉取成功，但容器无法启动

**解决方案**：
```bash
# 1. 查看容器日志
docker-compose logs web

# 2. 检查环境变量
docker-compose config

# 3. 手动测试镜像
docker run --rm ghcr.io/owner/repo/hifate-bazi:latest python --version
```

---

## 📈 性能对比

| 方案 | 构建时间 | 部署时间 | 总耗时 |
|------|---------|---------|--------|
| **方案 A（本地构建）** | 5-10 分钟 | 10-20 秒 | 5-10 分钟 |
| **方案 B（镜像拉取）** | 3-5 分钟（GitHub Actions） | 10-20 秒 | 3-5 分钟 |

**优势**：
- 构建不占用服务器资源
- 镜像可复用（测试、生产、回滚）
- 支持多平台构建
- 利用 GitHub Actions 缓存加速

---

## 🔄 回滚流程

### 自动回滚

如果健康检查失败，workflow 会自动回滚到上一个版本：

```bash
# 在 deploy-production.yml 中已实现
# 1. 尝试拉取上一个 commit 的镜像
# 2. 如果失败，使用 latest 标签
# 3. 启动容器并验证
```

### 手动回滚

```bash
# 1. 查看可用镜像
docker images | grep hifate-bazi

# 2. 使用指定标签的镜像
DOCKER_IMAGE=ghcr.io/owner/repo/hifate-bazi:sha-xxxxx \
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.image.yml up -d
```

---

## 📝 更新日志

### 2025-12-03
- ✅ 实现方案 B：GitHub Container Registry 部署
- ✅ 创建 `build-and-push.yml` workflow
- ✅ 创建 `deploy-test.yml` workflow（测试环境）
- ✅ 更新 `deploy-production.yml` 使用镜像拉取
- ✅ 创建 `docker-compose.image.yml` 支持镜像部署
- ✅ 添加自动回滚机制

---

## 📚 相关文档

- [GitHub Actions + Docker 部署清单](./GitHub-Actions-Docker部署清单.md)
- [Docker 部署指南](./Docker部署指南.md)
- [部署方案5-Docker自动化部署](./部署方案5-Docker自动化部署.md)

---

## 🎯 下一步

1. **配置 GitHub Secrets**（必需）
2. **首次推送测试**（验证构建和部署）
3. **配置生产环境**（等生产服务器地址确定后）
4. **优化构建缓存**（可选，已启用）

---

**提示**：当前测试环境地址为 `123.57.216.15`，生产环境地址待定。等生产地址确定后，只需更新 `PROD_SERVER_HOST` secret 即可。


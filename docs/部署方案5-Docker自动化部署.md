# 部署方案5：Docker + GitHub Actions 自动化部署

> HiFate-bazi 八字系统完整部署方案 - 企业级标准

## 🎯 方案概述

### 架构图

```
┌─────────────────┐
│   本地开发       │  Docker Compose + 热更新
│   MacBook       │  http://localhost:8001
└────────┬────────┘
         │ git push
         ↓
┌─────────────────┐
│    GitHub       │  代码仓库 + CI/CD
│    Actions     │  自动构建 + 自动部署
└────────┬────────┘
         │ SSH 部署
         ├────────────┐
         ↓            ↓
┌──────────────┐  ┌──────────────┐
│ 开发服务器    │  │ 生产服务器    │
│ (develop分支) │  │ (master分支)  │
│ Docker容器化  │  │ Docker容器化  │
└──────────────┘  └──────────────┘
```

### 工作流程

```
开发者本地（MacBook）
  ├── Docker热更新开发
  ├── 修改代码自动重载
  └── 本地测试通过
       ↓ git push origin feature/xxx
       
GitHub
  ├── 代码审查（可选）
  ├── 合并到 develop 分支
  │    ↓ 自动触发
  │    └── GitHub Actions
  │         ├── 构建 Docker 镜像
  │         ├── SSH 到开发服务器
  │         ├── 拉取最新代码
  │         └── 零停机部署
  │
  └── 测试通过后合并到 master
       ↓ 自动触发
       └── GitHub Actions
            ├── 构建 Docker 镜像
            ├── SSH 到生产服务器
            ├── 拉取最新代码
            └── 零停机部署

开发服务器 (dev.hifate.com)
  ├── 开发环境测试
  └── 功能验证

生产服务器 (hifate.com)
  ├── 线上用户访问
  └── 稳定运行
```

---

## 🚀 快速开始

### 前置要求

- ✅ macOS / Linux / Windows
- ✅ Docker Desktop 已安装
- ✅ Git 已配置
- ✅ 已克隆项目到本地

### 3分钟启动本地开发环境

```bash
# 1. 进入项目目录
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 2. 启动 Docker 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 3. 访问
# http://localhost:8001/frontend/formula-analysis.html

# 4. 修改代码，自动重载！
```

就这么简单！✨

---

## 📋 完整部署步骤

### 第一部分：本地开发环境配置（5分钟）

#### 步骤 1：安装 Docker Desktop

**macOS**：
```bash
# 方式1：使用 Homebrew
brew install --cask docker

# 方式2：下载安装包
# 访问 https://www.docker.com/products/docker-desktop/
```

**验证安装**：
```bash
docker --version
docker-compose --version
```

#### 步骤 2：启动本地开发环境

```bash
# 进入项目目录
cd HiFate-bazi

# 启动开发环境（首次启动会拉取镜像，需要5-10分钟）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 如果要后台运行
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 查看日志
docker-compose logs -f web
```

#### 步骤 3：验证服务

```bash
# 检查容器状态
docker-compose ps

# 应该看到以下容器运行中：
# - hifate-mysql (MySQL数据库)
# - hifate-redis (Redis缓存)
# - hifate-web (主服务)
# - hifate-bazi-analyzer (八字分析服务)
# - 其他微服务...

# 访问测试
open http://localhost:8001/frontend/formula-analysis.html
```

#### 步骤 4：热更新测试

```bash
# 修改任意 Python 文件
vim server/api/v1/bazi.py

# 保存后，观察容器日志，应该自动重载
# 无需重启容器！
```

---

### 第二部分：生产服务器配置（首次部署，20分钟）

#### 步骤 1：服务器准备

**服务器要求**：
- Ubuntu 20.04+ / CentOS 8+
- 2核 4GB 内存（最低配置）
- 50GB 磁盘空间
- 开放端口：80, 443, 22

**SSH 登录服务器**：
```bash
ssh root@your-server-ip
```

#### 步骤 2：安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 启动 Docker
systemctl start docker
systemctl enable docker

# 验证
docker --version
docker-compose --version
```

#### 步骤 3：创建部署用户

```bash
# 创建部署用户
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# 切换到部署用户
su - deploy
```

#### 步骤 4：克隆项目

```bash
# 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -C "deploy@your-server"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到 GitHub
# https://github.com/settings/keys

# 克隆项目
cd /opt
git clone git@github.com:zhoudengt/HiFate-bazi.git
cd HiFate-bazi
```

#### 步骤 5：配置环境变量

```bash
# 复制配置文件
cp config/services.env.example config/services.env

# 编辑配置
vim config/services.env

# 修改以下配置：
# MYSQL_ROOT_PASSWORD=生产环境密码
# REDIS_PASSWORD=生产环境密码
# SECRET_KEY=生产环境密钥
```

#### 步骤 6：首次部署

```bash
# 启动生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看日志
docker-compose logs -f

# 等待所有服务启动（约2-3分钟）
```

#### 步骤 7：验证部署

```bash
# 检查容器状态
docker-compose ps

# 测试 API
curl http://localhost:8001/api/health

# 应该返回：{"status": "ok"}
```

---

### 第三部分：GitHub Actions 自动部署配置（10分钟）

#### 步骤 1：配置 GitHub Secrets

访问：https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions

添加以下 Secrets：

| Name | Value | 说明 |
|------|-------|------|
| `DEV_SERVER_HOST` | `dev.hifate.com` | 开发服务器地址 |
| `DEV_SERVER_USER` | `deploy` | 开发服务器用户 |
| `DEV_SSH_PRIVATE_KEY` | `-----BEGIN...` | 开发服务器 SSH 私钥 |
| `PROD_SERVER_HOST` | `hifate.com` | 生产服务器地址 |
| `PROD_SERVER_USER` | `deploy` | 生产服务器用户 |
| `PROD_SSH_PRIVATE_KEY` | `-----BEGIN...` | 生产服务器 SSH 私钥 |

**如何获取 SSH 私钥**：
```bash
# 在服务器上
cat ~/.ssh/id_ed25519

# 复制完整内容（包括 BEGIN 和 END 行）
```

#### 步骤 2：GitHub Actions 配置文件已创建

项目已包含以下配置文件：
- `.github/workflows/deploy-develop.yml` - 开发环境自动部署
- `.github/workflows/deploy-production.yml` - 生产环境自动部署

#### 步骤 3：测试自动部署

```bash
# 本地修改代码
echo "# Test" >> README.md

# 提交到 develop 分支
git checkout develop
git add README.md
git commit -m "[测试] 测试自动部署"
git push origin develop

# 访问 GitHub Actions 查看部署进度
# https://github.com/zhoudengt/HiFate-bazi/actions
```

---

## 🔧 日常使用

### 本地开发流程

```bash
# 1. 启动开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 2. 修改代码（自动重载）
vim server/api/v1/some_file.py

# 3. 本地测试
open http://localhost:8001

# 4. 提交代码
git add .
git commit -m "[新增] 功能描述"
git push origin feature/my-feature

# 5. 合并到 develop（触发开发环境部署）
git checkout develop
git merge feature/my-feature
git push origin develop
# 自动部署到开发服务器！

# 6. 测试通过后发布到生产
git checkout master
git merge develop
git push origin master
# 自动部署到生产服务器！
```

### Docker 常用命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f web  # 只看主服务日志

# 重启某个服务
docker-compose restart web

# 进入容器
docker-compose exec web bash

# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a
```

---

## 📊 环境对比

| 项目 | 本地开发 | 开发服务器 | 生产服务器 |
|------|----------|------------|------------|
| **分支** | feature/* | develop | master |
| **域名** | localhost:8001 | dev.hifate.com | hifate.com |
| **数据库** | 本地 MySQL | 开发 MySQL | 生产 MySQL |
| **热更新** | ✅ 启用 | ⚠️ 可选 | ❌ 禁用 |
| **调试模式** | ✅ 开启 | ✅ 开启 | ❌ 关闭 |
| **日志级别** | DEBUG | INFO | WARNING |
| **缓存** | 短期 | 中期 | 长期 |
| **备份** | 无 | 每日 | 每小时 |

---

## 🔍 故障排查

### 问题 1：Docker 容器无法启动

**症状**：`docker-compose up` 报错

**解决方案**：
```bash
# 1. 查看详细日志
docker-compose logs

# 2. 检查端口占用
lsof -i :8001
lsof -i :13306

# 3. 清理旧容器
docker-compose down
docker system prune -a

# 4. 重新启动
docker-compose up -d
```

### 问题 2：热更新不工作

**症状**：修改代码后没有自动重载

**解决方案**：
```bash
# 1. 确认使用开发配置
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 2. 检查代码卷挂载
docker-compose exec web ls -la /app

# 3. 重启容器
docker-compose restart web
```

### 问题 3：自动部署失败

**症状**：GitHub Actions 显示失败

**解决方案**：
```bash
# 1. 查看 Actions 日志
# 访问 https://github.com/zhoudengt/HiFate-bazi/actions

# 2. 检查 Secrets 配置
# https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions

# 3. 测试 SSH 连接
ssh deploy@your-server

# 4. 手动在服务器上拉取代码测试
cd /opt/HiFate-bazi
git pull origin master
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 问题 4：数据库连接失败

**症状**：服务启动后无法连接数据库

**解决方案**：
```bash
# 1. 检查 MySQL 容器状态
docker-compose ps mysql

# 2. 查看 MySQL 日志
docker-compose logs mysql

# 3. 进入 MySQL 容器测试
docker-compose exec mysql mysql -u root -p

# 4. 检查网络连接
docker-compose exec web ping mysql
```

---

## 🔐 安全最佳实践

### 1. 敏感信息管理

```bash
# ❌ 不要提交敏感信息到 Git
config/services.env

# ✅ 使用环境变量
# .env 文件已在 .gitignore 中

# ✅ 使用 GitHub Secrets
# 敏感配置保存在 GitHub Secrets
```

### 2. SSH 密钥管理

```bash
# 为每个服务器生成独立密钥
ssh-keygen -t ed25519 -f ~/.ssh/hifate_dev
ssh-keygen -t ed25519 -f ~/.ssh/hifate_prod

# 配置 ~/.ssh/config
Host hifate-dev
    HostName dev.hifate.com
    User deploy
    IdentityFile ~/.ssh/hifate_dev

Host hifate-prod
    HostName hifate.com
    User deploy
    IdentityFile ~/.ssh/hifate_prod
```

### 3. 生产环境加固

```bash
# 1. 关闭调试模式
DEBUG=False

# 2. 使用强密码
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)

# 3. 启用防火墙
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable

# 4. 定期更新
apt update && apt upgrade -y
```

---

## 📈 性能优化

### Docker 镜像优化

```dockerfile
# 使用多阶段构建
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
```

### 资源限制

```yaml
# docker-compose.prod.yml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

## 📝 部署检查清单

### 首次部署前

- [ ] 服务器已安装 Docker
- [ ] SSH 密钥已配置
- [ ] GitHub Secrets 已设置
- [ ] 环境变量已配置
- [ ] 域名已解析

### 每次部署前

- [ ] 本地测试通过
- [ ] 代码已提交到 Git
- [ ] 提交信息清晰
- [ ] 已通知团队

### 部署后验证

- [ ] 服务启动正常
- [ ] API 响应正常
- [ ] 前端页面可访问
- [ ] 数据库连接正常
- [ ] 日志无错误

---

## 🎉 部署成功

完成以上步骤后，你的 HiFate-bazi 项目已经：

✅ **本地开发环境**：Docker 热更新，修改即生效  
✅ **开发服务器**：Push 到 develop 自动部署  
✅ **生产服务器**：Push 到 master 自动部署  
✅ **零停机部署**：Docker 滚动更新  
✅ **完整监控**：日志、状态、性能监控  

---

## 📞 需要帮助？

遇到问题时：

1. **查看文档**
   - Git Flow: `docs/Git-Flow工作流程.md`
   - 开发规范: `.cursorrules`

2. **查看日志**
   ```bash
   docker-compose logs -f
   ```

3. **咨询 AI 助手**
   ```
   "Docker 容器启动失败怎么办？"
   "如何查看部署日志？"
   "热更新不工作是什么原因？"
   ```

---

**享受自动化部署带来的便捷！** 🚀


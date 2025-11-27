# HiFate-bazi Docker 部署指南

> 完整的 Docker 部署方案，支持本地开发、开发环境和生产环境部署

## 📋 目录

- [部署架构](#部署架构)
- [服务器准备](#服务器准备)
- [方式一：手动部署（首次部署）](#方式一手动部署首次部署)
- [方式二：GitHub Actions 自动部署](#方式二github-actions-自动部署)
- [环境变量配置](#环境变量配置)
- [服务管理](#服务管理)
- [常见问题](#常见问题)

---

## 🏗️ 部署架构

### 环境说明

```
本地开发环境（Docker）
  ↓
开发服务器（develop 分支）
  ↓
生产服务器（master 分支）
```

### 服务列表

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| 主服务 | hifate-web | 8001 | Web API 服务器 |
| 八字分析 | hifate-bazi-analyzer | 50051 | gRPC 微服务 |
| 运势分析 | hifate-fortune-analyzer | 50052 | gRPC 微服务 |
| 规则服务 | hifate-rule-service | 50053 | gRPC 微服务 |
| MySQL | hifate-mysql | 3306 | 数据库（内部） |
| Redis | hifate-redis | 6379 | 缓存（内部） |

---

## 🖥️ 服务器准备

### 1. 系统要求

- **操作系统**：Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **内存**：至少 4GB（推荐 8GB+）
- **磁盘**：至少 20GB 可用空间
- **网络**：可访问 GitHub（用于拉取代码）

### 2. 安装 Docker 和 Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 3. 安装 Git

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y git

# CentOS
sudo yum install -y git
```

### 4. 配置 SSH 密钥（用于 GitHub 拉取代码）

```bash
# 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 将公钥添加到 GitHub
cat ~/.ssh/id_ed25519.pub
# 复制输出内容，添加到 GitHub Settings > SSH and GPG keys
```

### 5. 创建项目目录

```bash
# 创建项目目录
sudo mkdir -p /opt/HiFate-bazi
sudo chown $USER:$USER /opt/HiFate-bazi
cd /opt/HiFate-bazi
```

---

## 🚀 方式一：手动部署（首次部署）

### 步骤 1：克隆代码

```bash
cd /opt/HiFate-bazi

# 克隆仓库
git clone git@github.com:zhoudengt/HiFate-bazi.git .

# 或者使用 HTTPS（需要输入密码）
git clone https://github.com/zhoudengt/HiFate-bazi.git .
```

### 步骤 2：配置环境变量

```bash
# 创建生产环境变量文件
cat > .env << 'EOF'
# MySQL 配置
MYSQL_ROOT_PASSWORD=your_strong_password_here
MYSQL_USER=root
MYSQL_DATABASE=bazi_system

# Redis 配置（可选）
REDIS_PASSWORD=your_redis_password_here

# 应用配置
APP_ENV=production
DEBUG=False
SECRET_KEY=your_secret_key_here_change_me
WEB_PORT=8001

# 时区
TZ=Asia/Shanghai
EOF

# 修改权限（保护敏感信息）
chmod 600 .env
```

**⚠️ 重要**：请修改 `.env` 文件中的密码和密钥！

### 步骤 3：初始化数据库

```bash
# 如果数据库脚本在 scripts/ 目录下
# 先启动 MySQL 容器（仅数据库）
docker-compose up -d mysql

# 等待 MySQL 启动（约 30 秒）
sleep 30

# 执行数据库初始化脚本（如果有）
# docker-compose exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} bazi_system < scripts/init.sql
```

### 步骤 4：构建和启动服务

```bash
# 构建生产镜像
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 步骤 5：验证部署

```bash
# 健康检查
curl http://localhost:8001/health

# 查看所有容器状态
docker ps

# 查看服务日志
docker-compose logs web
docker-compose logs bazi-analyzer
```

### 步骤 6：配置 Nginx 反向代理（可选）

如果需要通过域名访问，配置 Nginx：

```bash
# 安装 Nginx
sudo apt-get install -y nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/hifate-bazi
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/hifate-bazi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🤖 方式二：GitHub Actions 自动部署

### 前提条件

1. ✅ 服务器已安装 Docker 和 Docker Compose
2. ✅ 服务器可以 SSH 访问
3. ✅ GitHub 仓库已配置

### 步骤 1：配置 GitHub Secrets

在 GitHub 仓库中配置以下 Secrets：

**Settings > Secrets and variables > Actions > New repository secret**

#### 开发环境 Secrets

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `DEV_SSH_PRIVATE_KEY` | 服务器 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEV_SERVER_HOST` | 开发服务器 IP/域名 | `192.168.1.100` 或 `dev.example.com` |
| `DEV_SERVER_USER` | SSH 用户名 | `ubuntu` 或 `root` |

#### 生产环境 Secrets

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `PROD_SSH_PRIVATE_KEY` | 服务器 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `PROD_SERVER_HOST` | 生产服务器 IP/域名 | `192.168.1.200` 或 `prod.example.com` |
| `PROD_SERVER_USER` | SSH 用户名 | `ubuntu` 或 `root` |

### 步骤 2：生成 SSH 密钥对

在服务器上生成 SSH 密钥：

```bash
# 在服务器上执行
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N ""

# 查看公钥（添加到 GitHub Secrets）
cat ~/.ssh/github_deploy.pub

# 查看私钥（添加到 GitHub Secrets）
cat ~/.ssh/github_deploy
```

**重要**：
- 公钥添加到服务器的 `~/.ssh/authorized_keys`
- 私钥添加到 GitHub Secrets

```bash
# 将公钥添加到 authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 步骤 3：首次手动部署（初始化）

在服务器上执行一次手动部署（见[方式一](#方式一手动部署首次部署)），确保：
- ✅ 项目目录已创建：`/opt/HiFate-bazi`
- ✅ `.env` 文件已配置
- ✅ 数据库已初始化

### 步骤 4：触发自动部署

#### 开发环境部署

```bash
# 推送到 develop 分支
git checkout develop
git push origin develop

# 或者手动触发
# GitHub > Actions > Deploy to Development > Run workflow
```

#### 生产环境部署

```bash
# 推送到 master 分支
git checkout master
git merge develop
git push origin master

# 或者手动触发
# GitHub > Actions > Deploy to Production > Run workflow
```

### 步骤 5：查看部署状态

访问 GitHub Actions 页面：
```
https://github.com/zhoudengt/HiFate-bazi/actions
```

---

## ⚙️ 环境变量配置

### 生产环境变量（`.env` 文件）

```bash
# MySQL 配置
MYSQL_ROOT_PASSWORD=your_strong_password_here
MYSQL_USER=root
MYSQL_DATABASE=bazi_system

# Redis 配置
REDIS_PASSWORD=your_redis_password_here

# 应用配置
APP_ENV=production
DEBUG=False
SECRET_KEY=your_secret_key_here_change_me
WEB_PORT=8001

# 时区
TZ=Asia/Shanghai

# gRPC 服务地址（Docker 内部使用服务名）
BAZI_CORE_SERVICE_URL=bazi-core:9001
BAZI_FORTUNE_SERVICE_URL=bazi-fortune:9002
BAZI_ANALYZER_SERVICE_URL=bazi-analyzer:50051
BAZI_RULE_SERVICE_URL=rule-service:50053
FORTUNE_ANALYSIS_SERVICE_URL=fortune-analyzer:50052

# Coze API 配置（如果需要）
COZE_ACCESS_TOKEN=your_coze_token
COZE_BOT_ID=your_bot_id

# Stripe 支付配置（如果需要）
STRIPE_SECRET_KEY=your_stripe_key
FRONTEND_BASE_URL=https://your-domain.com
```

### 开发环境变量

开发环境使用 `docker-compose.dev.yml`，会自动设置：
- `APP_ENV=development`
- `DEBUG=True`
- 源代码挂载（支持热更新）

---

## 🔧 服务管理

### 启动服务

```bash
# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 停止服务

```bash
# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 重启单个服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 查看单个服务日志
docker-compose logs -f web
docker-compose logs -f bazi-analyzer

# 查看最近 100 行日志
docker-compose logs --tail=100 web
```

### 更新服务

```bash
# 拉取最新代码
cd /opt/HiFate-bazi
git pull origin master

# 重新构建镜像
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 滚动更新（零停机）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build web
```

### 备份数据库

```bash
# 创建备份目录
mkdir -p backups

# 备份数据库
docker-compose exec mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} bazi_system > backups/mysql_backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker-compose exec -T mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} bazi_system < backups/mysql_backup_20250101_120000.sql
```

### 清理资源

```bash
# 清理未使用的镜像
docker image prune -f

# 清理未使用的容器
docker container prune -f

# 清理所有未使用的资源
docker system prune -a
```

---

## ❓ 常见问题

### 1. 容器启动失败

**问题**：容器启动后立即退出

**排查**：
```bash
# 查看容器日志
docker-compose logs web

# 查看容器状态
docker ps -a

# 进入容器调试
docker-compose exec web bash
```

**常见原因**：
- 环境变量未配置
- 数据库连接失败
- 端口被占用

### 2. 数据库连接失败

**问题**：服务无法连接 MySQL

**排查**：
```bash
# 检查 MySQL 容器状态
docker-compose ps mysql

# 测试 MySQL 连接
docker-compose exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT 1"

# 检查网络
docker network ls
docker network inspect hifate-bazi_hifate-network
```

**解决**：
- 确保 MySQL 容器已启动
- 检查 `.env` 文件中的数据库密码
- 等待 MySQL 完全启动（约 30 秒）

### 3. 端口被占用

**问题**：端口 8001 已被占用

**排查**：
```bash
# 查看端口占用
sudo lsof -i :8001
sudo netstat -tulpn | grep 8001

# 修改端口（在 .env 文件中）
WEB_PORT=8002
```

### 4. 内存不足

**问题**：容器因内存不足被杀死

**排查**：
```bash
# 查看系统内存
free -h

# 查看容器资源使用
docker stats

# 减少资源限制（在 docker-compose.prod.yml 中）
deploy:
  resources:
    limits:
      memory: 1G  # 降低内存限制
```

### 5. GitHub Actions 部署失败

**问题**：SSH 连接失败

**排查**：
- ✅ 检查 SSH 私钥是否正确添加到 GitHub Secrets
- ✅ 检查服务器 IP/域名是否正确
- ✅ 检查服务器防火墙是否开放 SSH 端口（22）
- ✅ 测试 SSH 连接：`ssh user@server`

**问题**：部署脚本执行失败

**排查**：
```bash
# 在服务器上手动执行部署命令
cd /opt/HiFate-bazi
git pull origin master
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 6. 健康检查失败

**问题**：`/health` 接口返回错误

**排查**：
```bash
# 检查服务日志
docker-compose logs web

# 手动测试健康检查
curl -v http://localhost:8001/health

# 检查服务是否正常启动
docker-compose ps
```

### 7. 前端无法访问

**问题**：浏览器无法访问前端页面

**排查**：
- ✅ 检查服务是否启动：`docker-compose ps`
- ✅ 检查端口是否正确：`curl http://localhost:8001`
- ✅ 检查防火墙：`sudo ufw status`
- ✅ 检查 Nginx 配置（如果使用反向代理）

---

## 📚 相关文档

- [开发规范](DEVELOPMENT_GUIDELINES.md)
- [快速启动指南](quick_start.md)
- [API 文档](bazi_api_structure.json)
- [微服务管理](微服务管理快速参考.md)

---

## 🆘 获取帮助

如果遇到问题，请：

1. 查看日志：`docker-compose logs -f`
2. 检查 GitHub Issues
3. 联系项目维护者

---

**最后更新**：2025-01-23


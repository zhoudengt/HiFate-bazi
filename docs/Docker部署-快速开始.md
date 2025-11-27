# Docker 部署快速开始

> 5 分钟快速部署 HiFate-bazi 到远程服务器

## 🚀 快速部署步骤

### 方式一：使用部署脚本（推荐）

```bash
# 1. 克隆代码到服务器
cd /opt
git clone git@github.com:zhoudengt/HiFate-bazi.git
cd HiFate-bazi

# 2. 配置环境变量
cp env.template .env
nano .env  # 修改密码和配置

# 3. 运行部署脚本
./scripts/deploy.sh production

# 完成！访问 http://your-server-ip:8001
```

### 方式二：手动部署

```bash
# 1. 克隆代码
cd /opt
git clone git@github.com:zhoudengt/HiFate-bazi.git
cd HiFate-bazi

# 2. 配置环境变量
cp env.template .env
nano .env  # 修改密码和配置

# 3. 构建和启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 查看状态
docker-compose ps
docker-compose logs -f
```

### 方式三：GitHub Actions 自动部署（推荐生产环境）

1. **配置 GitHub Secrets**（见下方）
2. **推送到 master 分支**
3. **自动部署完成**

---

## ⚙️ 环境变量配置

### 必需配置

编辑 `.env` 文件，至少修改以下配置：

```bash
# 数据库密码（必须修改）
MYSQL_ROOT_PASSWORD=your_strong_password_here

# 应用密钥（必须修改）
SECRET_KEY=your_secret_key_here_change_me

# Redis 密码（可选，但建议设置）
REDIS_PASSWORD=your_redis_password_here
```

### 生成随机密钥

```bash
# 生成 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 生成强密码
openssl rand -base64 32
```

---

## 🔐 GitHub Actions 配置

### 1. 生成 SSH 密钥

在服务器上执行：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 2. 添加 GitHub Secrets

访问：`https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions`

添加以下 Secrets：

| Secret 名称 | 值 | 说明 |
|------------|-----|------|
| `PROD_SSH_PRIVATE_KEY` | `cat ~/.ssh/github_deploy` | 服务器 SSH 私钥 |
| `PROD_SERVER_HOST` | `your-server-ip` | 服务器 IP 或域名 |
| `PROD_SERVER_USER` | `ubuntu` | SSH 用户名 |

### 3. 首次手动部署

在服务器上执行一次手动部署（初始化）：

```bash
cd /opt/HiFate-bazi
./scripts/deploy.sh production
```

### 4. 触发自动部署

```bash
git push origin master
```

---

## ✅ 验证部署

### 检查服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f web

# 健康检查
curl http://localhost:8001/health
```

### 访问前端

- 主服务：`http://your-server-ip:8001`
- 算法公式：`http://your-server-ip:8001/frontend/formula-analysis.html`
- 运势分析：`http://your-server-ip:8001/frontend/fortune.html`

---

## 🔧 常用命令

```bash
# 启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 查看日志
docker-compose logs -f

# 更新服务
git pull origin master
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## ❓ 常见问题

### 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8001

# 修改端口（在 .env 文件中）
WEB_PORT=8002
```

### 数据库连接失败

```bash
# 检查 MySQL 容器
docker-compose ps mysql
docker-compose logs mysql

# 等待 MySQL 启动（约 30 秒）
sleep 30
```

### 内存不足

```bash
# 查看内存使用
free -h
docker stats

# 减少资源限制（编辑 docker-compose.prod.yml）
```

---

## 📚 详细文档

- [完整部署指南](Docker部署指南.md)
- [开发规范](DEVELOPMENT_GUIDELINES.md)
- [API 文档](bazi_api_structure.json)

---

**需要帮助？** 查看完整部署指南或联系项目维护者。


# HiFate-bazi Docker 部署指南

> 基于 Docker 的一键部署方案，支持快速部署到生产环境

[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-1.29+-blue.svg)](https://docs.docker.com/compose/)

---

## 📋 目录

- [快速开始](#快速开始)
- [环境要求](#环境要求)
- [部署步骤](#部署步骤)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [故障排查](#故障排查)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 一键部署（推荐）

```bash
# 1. 克隆代码
git clone https://github.com/zhoudengt/HiFate-bazi.git
cd HiFate-bazi

# 2. 配置环境变量
cp env.template .env
vim .env  # 修改 MYSQL_ROOT_PASSWORD 和 SECRET_KEY

# 3. 执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

**部署完成后访问**：`http://localhost:8001`

---

## 📦 环境要求

### 服务器要求

- **操作系统**：Linux (Ubuntu 20.04+ / CentOS 7+)
- **内存**：至少 4GB（推荐 8GB+）
- **磁盘**：至少 20GB 可用空间
- **网络**：可访问 GitHub（拉取代码）

### 软件要求

- **Docker**：20.10+
- **Docker Compose**：1.29+
- **Git**：2.0+（用于拉取代码）

### 安装 Docker（如果还没有）

#### Ubuntu/Debian：

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install -y docker-compose-plugin
```

#### CentOS/RHEL：

```bash
sudo yum install -y docker docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
```

---

## 📝 部署步骤

### 步骤 1：从 GitHub 拉取代码

```bash
# 创建项目目录
mkdir -p /opt/HiFate-bazi
cd /opt/HiFate-bazi

# 克隆代码
git clone https://github.com/zhoudengt/HiFate-bazi.git .

# 如果网络慢，使用镜像：
# git clone https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git .
```

### 步骤 2：配置环境变量

```bash
# 复制环境变量模板
cp env.template .env

# 编辑配置文件
vim .env
```

**必须修改的配置**：

```bash
# MySQL 数据库密码（必须修改为强密码）
MYSQL_ROOT_PASSWORD=your_strong_password_here

# 应用密钥（必须修改，随机字符串）
SECRET_KEY=your_secret_key_here_change_me

# Redis 密码（可选，但建议设置）
REDIS_PASSWORD=your_redis_password_here

# 应用环境
APP_ENV=production
DEBUG=False
```

**保护配置文件**：

```bash
chmod 600 .env
```

### 步骤 3：执行部署

#### 方式 A：使用部署脚本（推荐）

```bash
# 执行部署脚本
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

部署脚本会自动：
- ✅ 检查 Docker 环境
- ✅ 构建 Docker 镜像
- ✅ 启动所有服务
- ✅ 执行健康检查

#### 方式 B：手动部署

```bash
# 构建镜像
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

---

## ⚙️ 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 | 必须修改 |
|--------|------|--------|----------|
| `MYSQL_ROOT_PASSWORD` | MySQL root 密码 | - | ✅ 是 |
| `SECRET_KEY` | 应用密钥 | - | ✅ 是 |
| `REDIS_PASSWORD` | Redis 密码 | - | ⚠️ 建议 |
| `APP_ENV` | 应用环境 | `production` | - |
| `DEBUG` | 调试模式 | `False` | - |
| `WEB_PORT` | Web 服务端口 | `8001` | - |

### 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Web 主服务 | 8001 | 前端访问端口 |
| MySQL | 13306 | 数据库端口（仅开发环境暴露） |
| Redis | 16379 | 缓存端口（仅开发环境暴露） |
| gRPC 服务 | 50051-50053 | 微服务端口 |

### 数据持久化

Docker 会自动创建数据卷：

- `mysql_data`：MySQL 数据
- `redis_data`：Redis 数据

数据存储在 Docker 卷中，删除容器不会丢失数据。

---

## 🔧 服务管理

### 查看服务状态

```bash
# 查看所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看资源使用
docker stats
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f mysql
```

### 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 停止并删除数据卷（谨慎使用）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

### 更新代码

```bash
# 拉取最新代码
git pull origin master

# 重新构建并启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 🐛 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100

# 检查容器状态
docker ps -a

# 检查端口占用
netstat -tlnp | grep 8001
```

### 数据库连接失败

```bash
# 检查 MySQL 容器状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps mysql

# 查看 MySQL 日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs mysql

# 进入 MySQL 容器
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec mysql mysql -u root -p
```

### 网络连接问题

```bash
# 测试服务健康
curl http://localhost:8001/health

# 检查 Docker 网络
docker network ls
docker network inspect hifate-bazi_hifate-network
```

### 清理并重新部署

```bash
# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 清理未使用的镜像
docker image prune -f

# 重新构建并启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## ❓ 常见问题

### Q1: Docker 未安装怎么办？

**A**: 参考 [环境要求](#环境要求) 部分安装 Docker。

### Q2: 端口 8001 被占用怎么办？

**A**: 
```bash
# 修改 .env 文件中的端口
WEB_PORT=8002

# 或停止占用端口的服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Q3: 如何备份数据库？

**A**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec mysql \
  mysqldump -u root -p${MYSQL_ROOT_PASSWORD} bazi_system > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Q4: 如何恢复数据库？

**A**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p${MYSQL_ROOT_PASSWORD} bazi_system < backup.sql
```

### Q5: 如何查看服务资源使用？

**A**:
```bash
# 实时查看
docker stats

# 查看特定容器
docker stats hifate-web
```

### Q6: 如何进入容器调试？

**A**:
```bash
# 进入 Web 容器
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web bash

# 进入 MySQL 容器
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec mysql bash
```

---

## 📚 相关文档

- [从 GitHub 部署到服务器完整指南](docs/从GitHub部署到服务器-完整指南.md)
- [Docker 远程部署指南](docs/Docker远程部署指南.md)
- [用户权限说明](docs/用户权限说明.md)
- [服务器环境配置](docs/服务器环境配置.md)

---

## 🔗 访问地址

部署完成后，访问以下地址：

- **主服务**：`http://你的服务器IP:8001`
- **算法公式**：`http://你的服务器IP:8001/frontend/formula-analysis.html`
- **运势分析**：`http://你的服务器IP:8001/frontend/fortune.html`
- **面相分析 V2**：`http://你的服务器IP:8001/frontend/face-analysis-v2.html`
- **办公桌风水**：`http://你的服务器IP:8001/frontend/desk-fengshui.html`

---

## 📊 服务架构

```
┌─────────────────────────────────────────┐
│         Nginx / 负载均衡器                │
└─────────────────┬───────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼────┐      ┌────▼────┐
    │  Web    │      │  gRPC   │
    │ Service │      │Services │
    └────┬────┘      └────┬────┘
         │                 │
    ┌────┴─────────────────┴────┐
    │                            │
┌───▼────┐              ┌───────▼────┐
│ MySQL  │              │   Redis     │
│  8.0   │              │    7.0     │
└────────┘              └─────────────┘
```

---

## 🛠️ 开发环境

### 本地开发（热更新）

```bash
# 使用开发配置
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 修改代码后自动重载，无需重启
```

### 生产环境

```bash
# 使用生产配置
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 📝 更新日志

### v1.0.0
- ✅ 支持 Docker 一键部署
- ✅ 支持生产环境配置
- ✅ 支持自动健康检查
- ✅ 支持数据持久化

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 📞 支持

如有问题，请查看：
- [故障排查](#故障排查)
- [常见问题](#常见问题)
- [GitHub Issues](https://github.com/zhoudengt/HiFate-bazi/issues)

---

**Happy Deploying! 🚀**


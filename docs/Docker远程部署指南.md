# HiFate-bazi Docker 远程服务器部署指南

## 📋 部署前准备

### 1. 服务器要求

- **操作系统**：Linux (Ubuntu 20.04+ / CentOS 7+)
- **Docker**：20.10+
- **Docker Compose**：1.29+
- **内存**：至少 4GB（推荐 8GB+）
- **磁盘**：至少 20GB 可用空间
- **网络**：可访问 GitHub（拉取代码）

### 2. 服务器环境检查

```bash
# 检查 Docker
docker --version
docker-compose --version

# 如果没有安装，执行：
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin

# CentOS/RHEL
sudo yum install -y docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
```

---

## 🚀 部署步骤

### 方式一：手动部署（推荐首次部署）

#### 步骤 1：SSH 连接到服务器

```bash
ssh user@your-server-ip
```

#### 步骤 2：创建项目目录

```bash
# 创建项目目录
sudo mkdir -p /opt/HiFate-bazi
sudo chown $USER:$USER /opt/HiFate-bazi
cd /opt/HiFate-bazi
```

#### 步骤 3：克隆代码

```bash
# 克隆仓库
git clone git@github.com:zhoudengt/HiFate-bazi.git .

# 或者使用 HTTPS
git clone https://github.com/zhoudengt/HiFate-bazi.git .
```

#### 步骤 4：配置环境变量

```bash
# 复制环境变量模板
cp env.template .env

# 编辑环境变量（使用 vim 或 nano）
vim .env
```

**重要配置项**：

```bash
# MySQL 密码（必须修改为强密码）
MYSQL_ROOT_PASSWORD=your_strong_password_here

# Redis 密码（可选，但建议设置）
REDIS_PASSWORD=your_redis_password_here

# 应用密钥（必须修改）
SECRET_KEY=your_secret_key_here_change_me

# 应用环境
APP_ENV=production
DEBUG=False

# 端口（默认 8001）
WEB_PORT=8001
```

**保护配置文件**：

```bash
chmod 600 .env
```

#### 步骤 5：执行部署脚本

```bash
# 给脚本执行权限
chmod +x scripts/deploy.sh

# 执行部署（生产环境）
./scripts/deploy.sh production
```

部署脚本会自动：
1. ✅ 检查 Docker 环境
2. ✅ 检查环境变量配置
3. ✅ 停止旧容器
4. ✅ 拉取最新代码
5. ✅ 构建 Docker 镜像
6. ✅ 启动所有服务
7. ✅ 执行健康检查

#### 步骤 6：验证部署

```bash
# 查看服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 健康检查
curl http://localhost:8001/health
```

---

### 方式二：使用 GitHub Actions 自动部署（推荐持续部署）

#### 前提条件

1. **配置 GitHub Secrets**：
   - 进入 GitHub 仓库 → Settings → Secrets and variables → Actions
   - 添加以下 Secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `PROD_SERVER_HOST` | 服务器 IP 或域名 | `192.168.1.100` |
| `PROD_SERVER_USER` | SSH 用户名 | `root` 或 `ubuntu` |
| `PROD_SSH_PRIVATE_KEY` | SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

2. **生成 SSH 密钥对**（如果还没有）：

```bash
# 在本地生成密钥对
ssh-keygen -t ed25519 -C "deploy@hifate" -f ~/.ssh/hifate_deploy

# 将公钥添加到服务器
ssh-copy-id -i ~/.ssh/hifate_deploy.pub user@your-server-ip

# 复制私钥内容（添加到 GitHub Secrets）
cat ~/.ssh/hifate_deploy
```

3. **服务器准备**：

```bash
# 在服务器上创建项目目录
sudo mkdir -p /opt/HiFate-bazi
sudo chown $USER:$USER /opt/HiFate-bazi

# 初始化 Git 仓库（如果还没有）
cd /opt/HiFate-bazi
git clone git@github.com:zhoudengt/HiFate-bazi.git .

# 创建 .env 文件
cp env.template .env
vim .env  # 编辑配置
chmod 600 .env
```

#### 自动部署流程

1. **推送到 master 分支**：
   ```bash
   git push origin master
   ```

2. **GitHub Actions 自动触发**：
   - 自动备份数据库
   - 拉取最新代码
   - 构建新镜像
   - 滚动更新服务（零停机）
   - 健康检查
   - 失败自动回滚

3. **查看部署状态**：
   - 访问：`https://github.com/zhoudengt/HiFate-bazi/actions`
   - 查看最新的 "🚀 Deploy to Production" workflow

---

## 🔧 常用运维命令

### 查看服务状态

```bash
# 查看所有容器状态
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

### 更新代码

```bash
# 拉取最新代码
cd /opt/HiFate-bazi
git pull origin master

# 重新构建并启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 备份数据库

```bash
# 手动备份
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec mysql \
  mysqldump -u root -p${MYSQL_ROOT_PASSWORD} bazi_system > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p${MYSQL_ROOT_PASSWORD} bazi_system < backup_20241127_120000.sql
```

### 清理资源

```bash
# 清理未使用的镜像
docker image prune -f

# 清理未使用的容器和网络
docker system prune -f

# 查看磁盘使用
docker system df
```

---

## 🔒 安全配置

### 1. 防火墙配置

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8001/tcp
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

### 2. 使用 Nginx 反向代理（推荐）

```nginx
# /etc/nginx/sites-available/hifate
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

### 3. SSL 证书（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
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
sudo netstat -tlnp | grep 8001
```

### 数据库连接失败

```bash
# 检查 MySQL 容器
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec mysql mysql -u root -p

# 检查环境变量
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web env | grep MYSQL
```

### 内存不足

```bash
# 查看内存使用
free -h
docker stats

# 调整 docker-compose.prod.yml 中的资源限制
```

---

## 📊 监控建议

### 1. 健康检查

```bash
# 定期检查服务健康状态
curl http://localhost:8001/health
```

### 2. 日志监控

```bash
# 使用 logrotate 管理日志
# 或集成 ELK/EFK 日志系统
```

### 3. 性能监控

```bash
# 使用 Prometheus + Grafana
# 或使用 Docker 内置监控
docker stats
```

---

## ✅ 部署检查清单

- [ ] Docker 和 Docker Compose 已安装
- [ ] 服务器端口已开放（8001）
- [ ] 环境变量已配置（.env 文件）
- [ ] 代码已拉取到服务器
- [ ] 所有服务容器运行正常
- [ ] 健康检查通过
- [ ] 数据库连接正常
- [ ] Redis 连接正常
- [ ] 前端页面可访问
- [ ] gRPC-Web 网关正常工作
- [ ] 日志输出正常

---

## 📞 技术支持

如遇到问题，请查看：
- 项目文档：`docs/` 目录
- 日志文件：`docker-compose logs`
- GitHub Issues：https://github.com/zhoudengt/HiFate-bazi/issues

---

**部署完成后，访问地址**：
- 主服务：`http://your-server-ip:8001`
- 算法公式：`http://your-server-ip:8001/frontend/formula-analysis.html`
- 运势分析：`http://your-server-ip:8001/frontend/fortune.html`
- 面相分析 V2：`http://your-server-ip:8001/frontend/face-analysis-v2.html`
- 办公桌风水：`http://your-server-ip:8001/frontend/desk-fengshui.html`


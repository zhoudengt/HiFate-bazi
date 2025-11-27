# 从 GitHub 部署到服务器 - 完整指南

## 📋 目录

1. [服务器准备](#服务器准备)
2. [从 GitHub 拉取代码](#从-github-拉取代码)
3. [配置环境变量](#配置环境变量)
4. [Docker 部署](#docker-部署)
5. [验证部署](#验证部署)
6. [常见问题](#常见问题)

---

## 1. 服务器准备

### 1.1 登录服务器

```bash
# 使用 root 用户登录（推荐，最简单）
ssh root@你的服务器IP

# 或者使用普通用户
ssh ubuntu@你的服务器IP
```

### 1.2 安装必要工具

#### Ubuntu/Debian 系统：

```bash
# 更新系统
apt-get update

# 安装 Git
apt-get install -y git

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# 安装 Docker Compose
apt-get install -y docker-compose-plugin

# 验证安装
git --version
docker --version
docker compose version
```

#### CentOS/RHEL 系统：

```bash
# 安装 Git
yum install -y git

# 安装 Docker
yum install -y docker
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
yum install -y docker-compose-plugin

# 验证安装
git --version
docker --version
docker compose version
```

---

## 2. 从 GitHub 拉取代码

### 2.1 创建项目目录

```bash
# 创建项目目录
mkdir -p /opt/HiFate-bazi

# 进入目录
cd /opt/HiFate-bazi
```

### 2.2 从 GitHub 克隆代码

#### 方式 A：使用 HTTPS（推荐，最简单）

```bash
# 克隆代码
git clone https://github.com/zhoudengt/HiFate-bazi.git .

# 如果网络慢，使用镜像：
# git clone https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git .
```

#### 方式 B：使用 SSH（需要配置 SSH 密钥）

```bash
# 克隆代码
git clone git@github.com:zhoudengt/HiFate-bazi.git .
```

### 2.3 验证代码已拉取

```bash
# 检查文件是否存在
ls -la

# 检查脚本是否存在
ls -la scripts/deploy_remote.sh

# 应该能看到项目文件
```

---

## 3. 配置环境变量

### 3.1 创建环境变量文件

```bash
# 在项目目录中执行
cd /opt/HiFate-bazi

# 复制模板
cp env.template .env

# 编辑配置文件
vim .env
# 或使用 nano
# nano .env
```

### 3.2 必须修改的配置

```bash
# MySQL 数据库密码（必须修改为强密码）
MYSQL_ROOT_PASSWORD=你的强密码

# 应用密钥（必须修改，随机字符串）
SECRET_KEY=你的随机密钥字符串

# Redis 密码（可选，但建议设置）
REDIS_PASSWORD=你的Redis密码

# 应用环境
APP_ENV=production
DEBUG=False
```

### 3.3 保护配置文件

```bash
# 设置文件权限（只有所有者可读）
chmod 600 .env
```

---

## 4. Docker 部署

### 4.1 使用部署脚本（推荐）

```bash
# 在项目目录中执行
cd /opt/HiFate-bazi

# 给脚本执行权限
chmod +x scripts/deploy_remote.sh

# 执行部署脚本
./scripts/deploy_remote.sh
```

**部署脚本会自动**：
1. ✅ 检查 Docker 环境
2. ✅ 检查项目目录
3. ✅ 更新代码（可选，可以跳过）
4. ✅ 配置环境变量
5. ✅ 构建 Docker 镜像
6. ✅ 启动所有服务
7. ✅ 执行健康检查

### 4.2 手动部署（不使用脚本）

```bash
# 在项目目录中执行
cd /opt/HiFate-bazi

# 1. 停止旧容器（如果有）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 2. 构建镜像
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

# 3. 启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 查看服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 5. 查看日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

---

## 5. 验证部署

### 5.1 检查服务状态

```bash
# 查看所有容器状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 应该看到所有服务都是 "Up" 状态
```

### 5.2 健康检查

```bash
# 检查主服务
curl http://localhost:8001/health

# 应该返回健康状态
```

### 5.3 访问前端页面

在浏览器中访问：

```
http://你的服务器IP:8001/frontend/formula-analysis.html
http://你的服务器IP:8001/frontend/fortune.html
http://你的服务器IP:8001/frontend/face-analysis-v2.html
http://你的服务器IP:8001/frontend/desk-fengshui.html
```

### 5.4 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f mysql
```

---

## 6. 常见问题

### 6.1 Git 克隆失败（网络问题）

**问题**：`Failed to connect to github.com`

**解决**：

```bash
# 使用 GitHub 镜像
git clone https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git .

# 或使用其他镜像
git clone https://github.com.cnpmjs.org/zhoudengt/HiFate-bazi.git .
```

### 6.2 Docker 未安装

**问题**：`docker: command not found`

**解决**：

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# CentOS/RHEL
yum install -y docker
systemctl start docker
systemctl enable docker
```

### 6.3 端口被占用

**问题**：`port 8001 is already allocated`

**解决**：

```bash
# 查看端口占用
netstat -tlnp | grep 8001

# 停止占用端口的服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 或修改 .env 文件中的端口
# WEB_PORT=8002
```

### 6.4 数据库连接失败

**问题**：`Can't connect to MySQL server`

**解决**：

```bash
# 检查 MySQL 容器状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps mysql

# 查看 MySQL 日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs mysql

# 重启 MySQL
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart mysql
```

### 6.5 环境变量未配置

**问题**：`.env file not found`

**解决**：

```bash
# 创建 .env 文件
cp env.template .env
vim .env  # 编辑配置
chmod 600 .env
```

---

## 7. 完整部署命令（一键执行）

### 在服务器上执行（复制粘贴）：

```bash
# ============================================
# HiFate-bazi Docker 完整部署
# ============================================

# 1. 安装 Git（如果还没有）
if ! command -v git &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y git
    elif command -v yum &> /dev/null; then
        yum install -y git
    fi
fi

# 2. 安装 Docker（如果还没有）
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# 3. 安装 Docker Compose（如果还没有）
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        apt-get install -y docker-compose-plugin
    elif command -v yum &> /dev/null; then
        yum install -y docker-compose-plugin
    fi
fi

# 4. 创建项目目录
mkdir -p /opt/HiFate-bazi
cd /opt/HiFate-bazi

# 5. 从 GitHub 克隆代码
if [ ! -d ".git" ]; then
    echo "正在从 GitHub 克隆代码..."
    git clone https://github.com/zhoudengt/HiFate-bazi.git . || \
    git clone https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git .
else
    echo "代码已存在，更新代码..."
    git pull origin master || echo "更新失败，使用当前代码"
fi

# 6. 配置环境变量
if [ ! -f ".env" ]; then
    echo "创建环境变量文件..."
    cp env.template .env
    echo "⚠️  请编辑 .env 文件，修改密码和密钥："
    echo "   vim .env"
    echo "   必须修改：MYSQL_ROOT_PASSWORD 和 SECRET_KEY"
    read -p "按 Enter 继续（已编辑 .env 文件）..."
    chmod 600 .env
fi

# 7. 执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh

# 8. 查看服务状态
echo ""
echo "=========================================="
echo "部署完成！查看服务状态："
echo "=========================================="
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo ""
echo "访问地址："
echo "  http://$(hostname -I | awk '{print $1}'):8001"
```

---

## 8. 部署后操作

### 8.1 更新代码

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 拉取最新代码
git pull origin master

# 重新构建并启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 8.2 重启服务

```bash
# 重启所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart web
```

### 8.3 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 停止并删除数据卷（谨慎使用）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

### 8.4 备份数据库

```bash
# 备份数据库
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec mysql \
  mysqldump -u root -p${MYSQL_ROOT_PASSWORD} bazi_system > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## 9. 快速参考

### 项目信息

- **GitHub 地址**：`https://github.com/zhoudengt/HiFate-bazi`
- **项目目录**：`/opt/HiFate-bazi`
- **主服务端口**：`8001`
- **环境变量文件**：`.env`

### 常用命令

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 查看服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 重启服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# 启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 10. 总结

### 部署流程（3 步）

1. **从 GitHub 拉取代码**：
   ```bash
   cd /opt
   mkdir -p HiFate-bazi
   cd HiFate-bazi
   git clone https://github.com/zhoudengt/HiFate-bazi.git .
   ```

2. **配置环境变量**：
   ```bash
   cp env.template .env
   vim .env  # 修改密码和密钥
   chmod 600 .env
   ```

3. **执行部署**：
   ```bash
   chmod +x scripts/deploy_remote.sh
   ./scripts/deploy_remote.sh
   ```

### 关键点

- ✅ **目录**：`/opt/HiFate-bazi`（项目根目录）
- ✅ **代码来源**：GitHub（`https://github.com/zhoudengt/HiFate-bazi`）
- ✅ **部署方式**：Docker Compose
- ✅ **配置文件**：`.env`（必须修改密码和密钥）

---

**部署完成后，访问**：`http://你的服务器IP:8001`


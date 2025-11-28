# HiFate-bazi Docker 生产部署完整指南

> **最后更新**：2025-11-28  
> **适用版本**：v1.0+  
> **维护原则**：操作更新时，本文档同步更新

---

## 📋 目录

1. [服务器信息](#服务器信息)
2. [Docker 基础镜像优化](#docker-基础镜像优化)
3. [首次部署](#首次部署)
4. [日常部署](#日常部署)
5. [数据库同步](#数据库同步)
6. [故障排查](#故障排查)
7. [性能优化](#性能优化)

---

## 📋 服务器信息

| 项目 | 值 |
|------|-----|
| **服务器 IP** | 123.57.216.15 |
| **SSH 用户** | root |
| **SSH 端口** | 22 |
| **代码仓库** | https://gitee.com/zhoudengtang/hifate-prod.git |
| **部署目录** | /opt/HiFate-bazi |
| **访问地址** | http://123.57.216.15/ |

---

## 🐳 Docker 基础镜像优化

### 📋 原理

使用预构建的基础镜像（包含所有 Python 依赖），将部署时间从 **5-10 分钟**缩短到 **10-20 秒**。

```
传统方式：每次部署都安装依赖（5-10分钟）
优化方式：基础镜像已含依赖，只需复制代码（10-20秒）
```

### 🚀 使用流程

**1. 首次构建基础镜像**（仅需一次，约 5-10 分钟）

```bash
./scripts/docker/build_base.sh
```

**2. 检查基础镜像状态**

```bash
./scripts/docker/check_base.sh
```

**3. 正常部署**（快速，10-20秒）

```bash
docker compose up -d --build web
```

### ⚠️ 何时需要重建基础镜像

| 场景 | 是否需要重建 | 说明 |
|------|------------|------|
| 修改代码 | ❌ 不需要 | 直接部署即可 |
| 修改 requirements.txt | ✅ **必须重建** | 依赖变更 |
| 修改 Dockerfile.base | ✅ 需要重建 | 基础镜像配置变更 |

### 🔒 安全机制

1. **跨平台兼容**：使用 `--platform linux/amd64` 确保 Mac M1/Intel 都能构建
2. **保险层**：应用 Dockerfile 会再次执行 `pip install`，确保依赖完整
3. **自动检查**：`check_base.sh` 会检测 requirements.txt 是否变更

### 📊 性能对比

| 场景 | 传统方式 | 基础镜像 | 提升 |
|------|---------|---------|------|
| 首次部署 | 10-15分钟 | 5-10分钟（构建基础镜像） | 1次性 |
| 代码更新 | 1-2分钟 | **10-20秒** | **6-12倍** |
| 依赖更新 | 10-15分钟 | 5-10分钟（重建基础镜像） | 1次性 |

### 🛠️ 维护命令

```bash
# 构建基础镜像
./scripts/docker/build_base.sh

# 检查是否需要更新
./scripts/docker/check_base.sh

# 查看基础镜像信息
docker images hifate-base

# 删除旧版本（可选）
docker rmi hifate-base:20241128
```

---

## 🚀 首次部署

### 步骤 1：服务器初始化

```bash
# 使用部署脚本（推荐）
./deploy.sh
# 选择 7) 首次部署：初始化服务器

# 或手动执行
ssh root@123.57.216.15 'bash -s' < scripts/deploy/server_init.sh
```

### 步骤 2：构建基础镜像（本地或服务器）

**本地构建**（推荐，利用本地高速网络）：

```bash
# 本地执行
./scripts/docker/build_base.sh

# 推送到服务器（可选）
docker save hifate-base:latest | ssh root@123.57.216.15 'docker load'
```

**服务器构建**：

```bash
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && ./scripts/docker/build_base.sh'
```

### 步骤 3：创建环境变量

```bash
ssh root@123.57.216.15 'cat > /opt/HiFate-bazi/.env << "EOF"
APP_ENV=production
DEBUG=False
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=HiFate_Prod_2024!
MYSQL_DATABASE=hifate_bazi
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=HiFate_Redis_2024!
WEB_PORT=8001
SECRET_KEY=your-super-secret-key-change-me
LOG_LEVEL=WARNING
EOF
chmod 600 /opt/HiFate-bazi/.env'
```

### 步骤 4：启动服务

```bash
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && docker compose up -d'
```

### 步骤 5：同步数据库

```bash
# 本地执行
./scripts/db/sync_db.sh
# 选择 3) 完整同步
```

### 步骤 6：配置 Nginx（可选）

```bash
ssh root@123.57.216.15 'cat > /etc/nginx/conf.d/hifate.conf << "EOF"
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }
}
EOF
nginx -t && systemctl reload nginx'
```

### 步骤 7：开放安全组端口

在阿里云控制台 → 安全组 → 入方向添加：

| 端口 | 协议 | 授权对象 |
|------|------|----------|
| 22 | TCP | 你的 IP |
| 80 | TCP | 0.0.0.0/0 |
| 8001 | TCP | 0.0.0.0/0（可选） |

---

## 🔄 日常部署

### 方法 1：使用部署脚本（推荐）

```bash
./deploy.sh

# 选择操作：
# 1) 完整部署（推送 Gitee → 服务器 pull → Docker 重启）
# 2) 仅推送到 Gitee
# 3) 仅更新服务器（代码已推送）
```

### 方法 2：手动部署

**代码已推送到 Gitee**：

```bash
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && git pull && docker compose up -d --build web'
```

**仅前端修改**（无需重建）：

```bash
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && git pull'
```

### 增量部署原则

| 场景 | 操作 | 命令 |
|------|------|------|
| 仅代码修改 | `git pull` + 重建 web | `git pull && docker compose up -d --build web` |
| 仅前端修改 | `git pull` | `git pull` |
| 依赖修改 | 重建基础镜像 + 部署 | `./scripts/docker/build_base.sh` 然后部署 |
| 数据库修改 | 同步数据库 | `./scripts/db/sync_db.sh` |

---

## 🗄️ 数据库同步

### 何时需要同步

- ✅ 首次部署
- ✅ 规则表有更新（bazi_rules）
- ✅ 新增数据表
- ❌ 仅代码修改（不需要）

### 同步方法

**方法 1：使用同步脚本（推荐）**

```bash
./scripts/db/sync_db.sh

# 选择操作：
# 1) 导出本地数据库
# 2) 同步到生产环境
# 3) 完整同步（导出 + 同步）
```

**方法 2：手动同步**

```bash
# 1. 导出本地数据
mysqldump -h 127.0.0.1 -P 3306 -u root -p123456 \
    --default-character-set=utf8mb4 \
    hifate_bazi > scripts/db/init_data.sql

# 2. 上传到服务器
scp scripts/db/init_data.sql root@123.57.216.15:/tmp/

# 3. 导入到 Docker MySQL
ssh root@123.57.216.15 "docker exec -i hifate-mysql \
    mysql -uroot -p'HiFate_Prod_2024!' hifate_bazi < /tmp/init_data.sql"
```

---

## 🔍 故障排查

### 问题 1：ModuleNotFoundError

**原因**：缺少 Python 依赖

**解决**：
```bash
# 检查 requirements.txt 是否变更
./scripts/docker/check_base.sh

# 如果变更，重建基础镜像
./scripts/docker/build_base.sh

# 重新部署
docker compose up -d --build web
```

### 问题 2：MySQL 连接失败

**检查**：
```bash
# 检查 .env 配置
ssh root@123.57.216.15 'cat /opt/HiFate-bazi/.env | grep MYSQL'

# 检查容器状态
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && docker compose ps mysql'

# 检查容器网络
ssh root@123.57.216.15 'docker network ls'
```

**解决**：
- 确保 `.env` 中 `MYSQL_HOST=mysql`（不是 localhost）
- 确保 MySQL 容器正常运行
- 检查容器是否在同一网络

### 问题 3：端口无法访问

**检查**：
```bash
# 检查服务监听
ssh root@123.57.216.15 'netstat -tlnp | grep 80'

# 检查防火墙
ssh root@123.57.216.15 'firewall-cmd --list-ports 2>/dev/null || iptables -L INPUT -n'
```

**解决**：
- 检查阿里云安全组是否开放端口
- 检查服务器防火墙规则
- 检查 Nginx 配置

### 问题 4：构建太慢

**原因**：未使用基础镜像或基础镜像过期

**解决**：
```bash
# 检查基础镜像
./scripts/docker/check_base.sh

# 构建基础镜像
./scripts/docker/build_base.sh
```

### 问题 5：基础镜像不存在

**解决**：
```bash
# 本地构建
./scripts/docker/build_base.sh

# 或服务器构建
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && ./scripts/docker/build_base.sh'
```

---

## ⚡ 性能优化

### 1. 使用基础镜像

**效果**：代码更新部署从 1-2 分钟缩短到 10-20 秒

**操作**：
```bash
./scripts/docker/build_base.sh  # 首次构建
docker compose up -d --build web  # 后续部署
```

### 2. 利用 Docker 缓存

**不要使用** `--no-cache`，让 Docker 使用构建缓存：

```bash
# ✅ 正确
docker compose up -d --build web

# ❌ 错误（会清除缓存）
docker compose build --no-cache
```

### 3. 精简构建上下文

已配置 `.dockerignore`，排除：
- `.git/`
- `logs/`
- `docs/`
- `node_modules/`
- `*.pyc`

### 4. 使用国内镜像源

已配置：
- 系统包：阿里云镜像
- Python 包：清华镜像

---

## 📝 维护清单

### 日常检查

```bash
# 检查服务状态
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && docker compose ps'

# 检查日志
ssh root@123.57.216.15 'cd /opt/HiFate-bazi && docker compose logs web --tail=50'

# 检查基础镜像
./scripts/docker/check_base.sh
```

### 定期维护

- **每周**：检查服务状态和日志
- **每月**：清理无用 Docker 镜像和容器
- **依赖更新**：及时更新 requirements.txt 并重建基础镜像

---

## 🔗 相关文档

- [Docker 基础镜像优化详细说明](./Docker基础镜像优化.md)
- [开发部署全流程](./开发部署全流程.md)
- [数据库同步脚本说明](../scripts/db/sync_db.sh)

---

## 📌 重要提醒

1. **修改 requirements.txt 后必须重建基础镜像**
2. **数据库变更后必须同步**
3. **部署前检查基础镜像状态**
4. **保持文档与操作同步更新**

---

## 📚 文档维护

### 🔄 同步更新原则

**核心原则**：操作更新时，本文档必须同步更新

### 📝 需要更新的场景

| 场景 | 需要更新的章节 | 示例 |
|------|--------------|------|
| 新增部署步骤 | 对应章节 | 添加新步骤说明 |
| 修改部署命令 | 对应章节 | 更新命令和参数 |
| 新增故障排查 | 故障排查章节 | 添加问题描述和解决方案 |
| 修改配置项 | 对应章节 | 更新配置说明和示例 |
| 新增脚本 | 对应章节 | 添加脚本使用说明 |
| 性能优化 | 性能优化章节 | 添加优化方法和效果 |

### ✅ 更新检查清单

每次修改部署相关操作时：

- [ ] 更新对应的章节内容
- [ ] 更新"最后更新"日期
- [ ] 验证命令和步骤的准确性
- [ ] 检查链接和引用是否正确
- [ ] 提交代码时同时提交文档更新

### 📋 更新流程

1. **修改操作** → 立即更新文档对应章节
2. **验证准确性** → 测试文档中的命令和步骤
3. **提交更新** → 代码和文档一起提交
4. **更新日期** → 修改文档顶部的"最后更新"日期

### 🔗 相关文档

- [开发规范](../.cursorrules) - 包含文档维护规范
- [Docker 基础镜像优化](./Docker基础镜像优化.md) - 基础镜像详细说明

---

**最后更新**：2025-11-28  
**维护者**：HiFate 开发团队  
**维护原则**：操作更新时，本文档同步更新


# Docker 跨平台依赖处理指南

## 📋 概述

本文档说明 Docker 如何在 Mac（开发）和 Linux（生产）环境下处理各种依赖，包括 Python 包、MySQL、Redis 等。

---

## 🎯 核心原理

### Docker 的跨平台机制

Docker 通过以下机制实现跨平台：

1. **容器化隔离**：所有依赖都打包在容器内，与宿主机系统隔离
2. **镜像分层**：基础镜像（如 `python:3.11-slim`）已包含系统依赖
3. **架构适配**：Docker 自动选择适合的镜像架构（ARM/x86）
4. **环境变量注入**：通过环境变量配置，无需修改代码

### 架构差异处理

| 平台 | 架构 | Docker 处理方式 |
|------|------|----------------|
| **Mac (Intel)** | x86_64 (amd64) | 使用 amd64 镜像 |
| **Mac (Apple Silicon)** | arm64 | 使用 arm64 镜像（自动转换） |
| **Linux 服务器** | x86_64 (amd64) | 使用 amd64 镜像 |

**Docker 自动处理**：
- Docker Desktop for Mac 自动处理架构转换
- 生产服务器通常使用 amd64，镜像默认支持

---

## 🐍 Python 依赖处理

### 1. 依赖安装流程

```dockerfile
# Dockerfile 中的处理流程
FROM python:3.11-slim          # 1. 基础镜像（已包含 Python 3.11）
COPY requirements.txt .         # 2. 复制依赖列表
RUN pip install -r requirements.txt  # 3. 安装依赖（在容器内）
```

### 2. 跨平台兼容性

**Python 包分类**：

| 包类型 | Mac 开发 | Linux 生产 | 处理方式 |
|--------|----------|------------|----------|
| **纯 Python 包** | ✅ 直接安装 | ✅ 直接安装 | 无需特殊处理 |
| **C 扩展包** | ✅ 本地编译 | ✅ 容器内编译 | Docker 自动处理 |
| **二进制包** | ⚠️ 可能架构不同 | ✅ 容器内编译 | 使用预编译 wheel |

**示例**：
- `fastapi`, `pydantic` → 纯 Python，跨平台兼容
- `numpy`, `pandas` → C 扩展，Docker 在容器内编译
- `torch`, `torchvision` → 大型二进制包，Docker 自动选择架构

### 3. 当前项目的依赖处理

查看 `requirements.txt`：

```python
# 基础依赖（纯 Python，跨平台）
fastapi==0.104.1
pydantic==2.11.9
PyMySQL==1.1.2
redis==7.0.1

# C 扩展依赖（Docker 自动编译）
numpy==2.0.2
cryptography==46.0.3

# 大型二进制依赖（Docker 自动选择架构）
torch>=2.4.0          # PyTorch（几GB，Docker 自动选择 ARM/x86）
torchvision>=0.19.0
opencv-python>=4.12.0.88
mediapipe>=0.10.0

# 需要编译的依赖（Docker 自动处理）
dlib>=19.24.0         # 需要 cmake、gfortran（已在 Dockerfile 中安装）
face-recognition>=1.3.0
```

**Dockerfile 中的处理**：

```dockerfile
# 1. 安装编译工具（跨平台通用）
RUN apt-get install -y \
    build-essential \
    cmake \
    gfortran \
    libopenblas-dev

# 2. 安装 Python 依赖（Docker 自动处理架构）
RUN pip install -r requirements.txt
```

### 4. 架构特定依赖的处理

**问题**：某些包（如 `torch`）有架构特定的二进制文件

**解决方案**：

```dockerfile
# 方法1：让 pip 自动选择（推荐）
RUN pip install torch torchvision
# Docker 会根据容器架构自动选择正确的 wheel

# 方法2：显式指定平台（如果需要）
# 在 docker-compose.yml 中：
services:
  web:
    platform: linux/amd64  # 强制使用 amd64（生产环境）
```

---

## 🗄️ MySQL 依赖处理

### 1. 使用官方镜像

```yaml
# docker-compose.yml
services:
  mysql:
    image: mysql:8.0  # Docker 自动选择架构
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
```

**跨平台处理**：
- ✅ `mysql:8.0` 镜像支持多架构（amd64、arm64）
- ✅ Docker 自动选择适合的架构
- ✅ 配置通过环境变量，跨平台一致

### 2. 数据持久化

```yaml
volumes:
  mysql_data:
    driver: local
```

**跨平台差异**：
- **Mac**：数据存储在 Docker Desktop 的虚拟磁盘
- **Linux**：数据存储在宿主机文件系统

**处理方式**：Docker Volume 自动处理，无需关心底层差异

### 3. 连接配置

```python
# 代码中的连接（跨平台一致）
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql')  # Docker 服务名
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
```

**环境变量注入**：

```yaml
# docker-compose.yml
environment:
  MYSQL_HOST: mysql      # Docker 网络中的服务名
  MYSQL_PORT: 3306
```

---

## 🔴 Redis 依赖处理

### 1. 使用官方镜像

```yaml
services:
  redis:
    image: redis:7-alpine  # 轻量级，跨平台支持
    command: redis-server --appendonly yes
```

**跨平台处理**：
- ✅ `redis:7-alpine` 支持多架构
- ✅ Alpine Linux 基础镜像，体积小
- ✅ 配置通过 command 参数，跨平台一致

### 2. 连接配置

```python
# 代码中的连接（跨平台一致）
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
```

---

## 🔧 开发 vs 生产环境

### 开发环境（Mac）

**特点**：
- 需要热更新（代码修改立即生效）
- 需要调试支持
- 数据可以重置

**配置**（`docker-compose.dev.yml`）：

```yaml
services:
  web:
    build:
      dockerfile: Dockerfile.dev
    volumes:
      - ./:/app  # 挂载源代码，支持热更新
    environment:
      DEBUG: "True"
      APP_ENV: development
    restart: "no"  # 失败不自动重启，方便调试
```

### 生产环境（Linux）

**特点**：
- 代码打包在镜像内（不挂载）
- 性能优化
- 自动重启

**配置**（`docker-compose.prod.yml`）：

```yaml
services:
  web:
    environment:
      DEBUG: "False"
      APP_ENV: production
    volumes: []  # 不挂载源代码，使用镜像内代码
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

---

## 📦 依赖管理最佳实践

### 1. 分层构建（利用缓存）

```dockerfile
# ✅ 好的做法：先安装依赖，再复制代码
COPY requirements.txt .
RUN pip install -r requirements.txt  # 依赖层（缓存）
COPY . /app                            # 代码层（经常变化）

# ❌ 不好的做法：一起复制
COPY . /app
RUN pip install -r requirements.txt   # 代码变化导致依赖重新安装
```

### 2. 使用 .dockerignore

```dockerignore
# 排除不必要文件，减少构建上下文
.git
__pycache__/
*.pyc
venv/
.env
logs/
```

### 3. 多阶段构建（可选）

```dockerfile
# 阶段1：构建依赖
FROM python:3.11-slim AS builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 阶段2：运行环境
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
ENV PATH=/root/.local/bin:$PATH
```

### 4. 架构显式指定（生产环境）

```yaml
# docker-compose.prod.yml
services:
  web:
    platform: linux/amd64  # 生产环境强制使用 amd64
    build:
      context: .
      dockerfile: Dockerfile
```

---

## 🚀 实际使用场景

### 场景1：Mac 开发环境

```bash
# 1. 启动开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 2. 修改代码（自动热更新）
vim server/main.py  # 修改后自动生效

# 3. 查看日志
docker-compose logs -f web
```

**依赖处理**：
- Python 包：在容器内安装，Mac 架构自动适配
- MySQL：使用 `mysql:8.0` 镜像，自动选择架构
- Redis：使用 `redis:7-alpine` 镜像，自动选择架构

### 场景2：Linux 生产环境

```bash
# 1. 构建生产镜像
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 2. 启动生产服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. 查看状态
docker-compose ps
```

**依赖处理**：
- Python 包：在容器内安装，Linux amd64 架构
- MySQL：使用 `mysql:8.0` 镜像，Linux amd64
- Redis：使用 `redis:7-alpine` 镜像，Linux amd64

### 场景3：Mac 开发，Linux 生产

**工作流**：

```bash
# Mac 开发
1. 本地开发测试
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

2. 提交代码
   git add .
   git commit -m "新功能"
   git push origin develop

# Linux 生产
3. 服务器拉取代码
   git pull origin master

4. 构建并部署
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

**依赖一致性**：
- ✅ 相同的 `requirements.txt` → 相同的 Python 包版本
- ✅ 相同的 `Dockerfile` → 相同的系统依赖
- ✅ 相同的 `docker-compose.yml` → 相同的服务配置

---

## ⚠️ 常见问题

### Q1: Mac 上构建的镜像能在 Linux 上运行吗？

**答案**：可以，但需要注意架构。

```bash
# 方法1：使用多架构构建（推荐）
docker buildx build --platform linux/amd64 -t hifate-bazi:latest .

# 方法2：在 Linux 服务器上构建（最简单）
# 直接在服务器上 git pull 后构建
```

### Q2: torch 等大型包在不同架构上会出问题吗？

**答案**：不会，Docker 自动处理。

```dockerfile
# Docker 会自动选择正确的 wheel
RUN pip install torch torchvision
# Mac ARM → 下载 ARM 版本
# Linux x86 → 下载 x86 版本
```

### Q3: dlib 编译失败怎么办？

**原因**：缺少编译依赖

**解决**：已在 Dockerfile 中添加：

```dockerfile
RUN apt-get install -y \
    cmake \
    gfortran \
    libopenblas-dev
```

### Q4: 如何确保开发和生产环境一致？

**最佳实践**：

1. ✅ 使用相同的 `requirements.txt`
2. ✅ 使用相同的 `Dockerfile`
3. ✅ 使用环境变量区分配置
4. ✅ 使用 `docker-compose.prod.yml` 覆盖生产配置

### Q5: MySQL 数据在 Mac 和 Linux 之间如何迁移？

```bash
# 1. Mac 导出数据
docker exec hifate-mysql mysqldump -u root -p bazi_system > backup.sql

# 2. 传输到 Linux 服务器
scp backup.sql user@server:/opt/HiFate-bazi/

# 3. Linux 导入数据
docker exec -i hifate-mysql mysql -u root -p bazi_system < backup.sql
```

---

## 📊 架构对比表

| 组件 | Mac 开发 | Linux 生产 | 处理方式 |
|------|----------|------------|----------|
| **Python** | 3.11 (容器内) | 3.11 (容器内) | ✅ 一致 |
| **Python 包** | 容器内安装 | 容器内安装 | ✅ 一致 |
| **MySQL** | mysql:8.0 (ARM/x86) | mysql:8.0 (amd64) | ✅ Docker 自动选择 |
| **Redis** | redis:7-alpine (ARM/x86) | redis:7-alpine (amd64) | ✅ Docker 自动选择 |
| **数据存储** | Docker Volume | Docker Volume | ✅ 一致 |
| **网络** | Docker Network | Docker Network | ✅ 一致 |

---

## 🎯 总结

### Docker 跨平台的核心优势

1. **环境一致性**：开发和生产使用相同的容器环境
2. **依赖隔离**：所有依赖都在容器内，不污染宿主机
3. **架构自动适配**：Docker 自动选择正确的镜像架构
4. **配置统一**：通过环境变量和 docker-compose 统一管理

### 关键要点

- ✅ **Python 包**：在容器内安装，Docker 自动处理架构差异
- ✅ **MySQL/Redis**：使用官方镜像，Docker 自动选择架构
- ✅ **开发环境**：挂载源代码，支持热更新
- ✅ **生产环境**：代码打包在镜像内，性能优化
- ✅ **跨平台部署**：相同的配置文件，不同的平台自动适配

---

## 🔗 相关文档

- [Docker 部署优化指南](./Docker部署优化指南.md)
- [Docker 部署指南](./docker_deployment.md)
- [部署方案5-Docker自动化部署.md](./部署方案5-Docker自动化部署.md)


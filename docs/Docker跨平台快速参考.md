# Docker 跨平台快速参考

## 🎯 核心概念

**Docker 如何实现跨平台？**

1. **容器隔离**：所有依赖都在容器内，与宿主机隔离
2. **镜像分层**：基础镜像（如 `python:3.11-slim`）已包含系统依赖
3. **架构自动适配**：Docker 自动选择适合的镜像架构（ARM/x86）
4. **环境变量配置**：通过环境变量统一配置，无需修改代码

## 📦 依赖处理方式

### Python 包

```dockerfile
# Dockerfile 中
COPY requirements.txt .
RUN pip install -r requirements.txt
```

**处理方式**：
- ✅ 纯 Python 包：直接安装，跨平台兼容
- ✅ C 扩展包：Docker 在容器内自动编译
- ✅ 二进制包（如 torch）：Docker 自动选择架构

### MySQL

```yaml
# docker-compose.yml
services:
  mysql:
    image: mysql:8.0  # Docker 自动选择架构
```

**处理方式**：
- ✅ 使用官方镜像，支持多架构
- ✅ 配置通过环境变量，跨平台一致
- ✅ 数据通过 Volume 持久化

### Redis

```yaml
services:
  redis:
    image: redis:7-alpine  # 轻量级，跨平台支持
```

**处理方式**：
- ✅ 使用官方镜像，支持多架构
- ✅ Alpine Linux 基础，体积小
- ✅ 配置通过 command 参数，跨平台一致

## 🔄 开发 vs 生产

### Mac 开发环境

```bash
# 启动开发环境（支持热更新）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**特点**：
- 源代码挂载（`./:/app`），修改立即生效
- 调试模式（`DEBUG=True`）
- 数据可重置

### Linux 生产环境

```bash
# 构建并启动生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**特点**：
- 代码打包在镜像内（不挂载）
- 性能优化（资源限制）
- 自动重启

## 🚀 常用命令

### 开发环境（Mac）

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 后台运行
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 查看日志
docker-compose logs -f web

# 进入容器
docker exec -it hifate-web bash

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### 生产环境（Linux）

```bash
# 构建镜像（使用缓存）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 重启服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

## ⚙️ 架构处理

### Mac (Apple Silicon) → Linux (x86)

**问题**：Mac ARM 架构构建的镜像可能无法在 Linux x86 上运行

**解决方案**：

```bash
# 方法1：在 Linux 服务器上构建（推荐）
# 直接在服务器上 git pull 后构建

# 方法2：使用多架构构建
docker buildx build --platform linux/amd64 -t hifate-bazi:latest .

# 方法3：在 docker-compose.prod.yml 中指定平台
services:
  web:
    platform: linux/amd64
```

## 🔧 配置一致性

### 确保开发和生产环境一致

1. ✅ **相同的 requirements.txt** → 相同的 Python 包版本
2. ✅ **相同的 Dockerfile** → 相同的系统依赖
3. ✅ **相同的 docker-compose.yml** → 相同的服务配置
4. ✅ **使用环境变量** → 区分开发和生产配置

### 环境变量配置

```yaml
# docker-compose.yml（基础配置）
environment:
  MYSQL_HOST: mysql
  MYSQL_PORT: 3306
  REDIS_HOST: redis
  REDIS_PORT: 6379

# docker-compose.dev.yml（开发覆盖）
environment:
  DEBUG: "True"
  APP_ENV: development

# docker-compose.prod.yml（生产覆盖）
environment:
  DEBUG: "False"
  APP_ENV: production
```

## 📊 架构对比

| 组件 | Mac 开发 | Linux 生产 | 处理方式 |
|------|----------|------------|----------|
| Python | 3.11 (容器) | 3.11 (容器) | ✅ 一致 |
| Python 包 | 容器内安装 | 容器内安装 | ✅ 一致 |
| MySQL | mysql:8.0 | mysql:8.0 | ✅ Docker 自动选择 |
| Redis | redis:7-alpine | redis:7-alpine | ✅ Docker 自动选择 |

## ⚠️ 常见问题

### Q: Mac 构建的镜像能在 Linux 运行吗？

**A**: 可以，但建议在 Linux 服务器上构建，或使用 `--platform linux/amd64`

### Q: torch 等大型包会出问题吗？

**A**: 不会，Docker 自动选择正确的架构版本

### Q: 如何确保依赖版本一致？

**A**: 使用相同的 `requirements.txt` 和 `Dockerfile`

### Q: 开发和生产环境如何切换？

**A**: 使用不同的 docker-compose 文件：
- 开发：`docker-compose.dev.yml`
- 生产：`docker-compose.prod.yml`

## 🔗 相关文档

- [Docker 跨平台依赖处理指南](./Docker跨平台依赖处理指南.md) - 详细说明
- [Docker 部署优化指南](./Docker部署优化指南.md) - 性能优化
- [Docker 部署指南](./docker_deployment.md) - 基础部署


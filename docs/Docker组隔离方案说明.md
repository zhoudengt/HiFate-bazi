# Docker 组隔离方案说明

## 📋 问题

能否建立两个独立的 Docker 组（前端组和后端组），让它们可以独立部署但可以访问？

## 🔍 技术分析

### Docker 架构限制

**Docker 本身的限制**：
- Docker daemon 只绑定一个 Unix socket：`/var/run/docker.sock`
- 只有一个 `docker` 组可以访问这个 socket
- **无法创建两个独立的 docker 组同时访问同一个 daemon**

### 可能的解决方案

#### 方案 1：使用 Docker Context（不推荐）

Docker Context 主要用于连接不同的 Docker daemon（远程或本地），但：
- ❌ 不能实现权限隔离
- ❌ 仍然需要 docker 组权限

#### 方案 2：运行两个 Docker daemon（复杂且不推荐）

理论上可以运行两个独立的 Docker daemon：
- ✅ 可以实现完全隔离
- ❌ 资源消耗大（两套 daemon）
- ❌ 配置复杂
- ❌ 容器之间无法直接通信
- ❌ 不推荐在生产环境使用

#### 方案 3：使用 Docker 网络隔离（推荐）

**最佳实践**：使用同一个 Docker daemon，但通过网络和命名进行隔离：

```bash
# 创建两个独立的网络
docker network create backend-network
docker network create frontend-network

# 后端容器使用 backend-network
docker run -d --name backend-app --network backend-network ...

# 前端容器使用 frontend-network
docker run -d --name frontend-app --network frontend-network ...
```

**优点**：
- ✅ 网络隔离（容器无法直接通信）
- ✅ 使用同一个 daemon（资源高效）
- ✅ 配置简单
- ✅ 可以设置网络间通信规则

**缺点**：
- ⚠️ 仍然可以看到所有容器（通过 `docker ps`）
- ⚠️ 仍然可以管理所有容器（但可以通过策略限制）

#### 方案 4：使用 Docker Swarm 或 Kubernetes

**Docker Swarm**：
- ✅ 支持命名空间（namespace）
- ✅ 可以实现权限隔离
- ❌ 需要切换到 Swarm 模式
- ❌ 配置较复杂

**Kubernetes**：
- ✅ 支持命名空间和 RBAC
- ✅ 可以实现完整的权限隔离
- ❌ 需要迁移到 K8s
- ❌ 学习曲线陡峭

#### 方案 5：使用 Docker Rootless（实验性）

Docker Rootless 允许非 root 用户运行 Docker：
- ✅ 可以实现用户级别的隔离
- ❌ 性能可能受影响
- ❌ 某些功能受限
- ❌ 仍处于实验阶段

## 🎯 推荐方案

### 方案 A：网络隔离 + 命名规范（最简单实用）

**实现方式**：

1. **使用独立的 Docker 网络**

```bash
# 创建前端网络
docker network create frontend-network

# 创建后端网络
docker network create backend-network

# 前端容器使用 frontend-network
docker run -d \
  --name frontend-app \
  --network frontend-network \
  -p 8080:80 \
  nginx:alpine

# 后端容器使用 backend-network
docker run -d \
  --name backend-app \
  --network backend-network \
  -p 8001:8001 \
  backend-image
```

2. **使用命名规范区分容器**

```bash
# 前端容器使用前缀：frontend-*
docker run -d --name frontend-app ...

# 后端容器使用前缀：hifate-* 或 backend-*
docker run -d --name hifate-web ...
```

3. **设置容器标签**

```bash
docker run -d \
  --name frontend-app \
  --label owner=frontend \
  --label environment=production \
  nginx:alpine
```

**优点**：
- ✅ 网络隔离
- ✅ 简单易用
- ✅ 不需要额外配置

**缺点**：
- ⚠️ 仍然可以看到所有容器
- ⚠️ 权限层面没有隔离

### 方案 B：使用 Docker Compose 项目隔离（推荐）

**实现方式**：

1. **前端使用独立的 docker-compose.yml**

```yaml
# /opt/hifate-frontend/docker-compose.yml
version: '3.8'

networks:
  frontend-network:
    driver: bridge
    name: frontend-network

services:
  frontend-app:
    image: nginx:alpine
    container_name: frontend-app
    networks:
      - frontend-network
    ports:
      - "8080:80"
```

2. **后端使用独立的 docker-compose.yml**

```yaml
# /opt/HiFate-bazi/deploy/docker/docker-compose.prod.yml
version: '3.8'

networks:
  backend-network:
    driver: bridge
    name: backend-network

services:
  web:
    # ... 后端配置
    networks:
      - backend-network
```

3. **使用项目名称隔离**

```bash
# 前端使用项目名 frontend
docker-compose -p frontend up -d

# 后端使用项目名 hifate
docker-compose -p hifate up -d
```

**优点**：
- ✅ 项目级别隔离
- ✅ 网络自动隔离
- ✅ 便于管理
- ✅ 可以通过项目名筛选容器

**缺点**：
- ⚠️ 仍然可以看到所有容器（但可以通过项目名区分）

### 方案 C：使用 Docker 插件（Docker Authorization Plugin）

**实现方式**：

使用 Docker 授权插件（如 casbin、OPA）来控制权限：
- ✅ 可以实现细粒度的权限控制
- ✅ 可以限制用户只能操作特定容器
- ❌ 需要开发或配置插件
- ❌ 配置较复杂

## 💡 最佳实践建议

### 当前推荐方案（网络隔离 + 命名规范）

考虑到你的需求，**推荐使用方案 A（网络隔离 + 命名规范）**：

1. **前端用户部署容器时**：
   ```bash
   # 使用独立网络
   docker network create frontend-network
   
   # 使用前端命名规范
   docker run -d \
     --name frontend-app \
     --network frontend-network \
     -p 8080:80 \
     nginx:alpine
   ```

2. **后端容器**：
   ```bash
   # 使用后端网络
   docker network create backend-network
   
   # 使用后端命名规范（hifate-*）
   docker run -d \
     --name hifate-web \
     --network backend-network \
     ...
   ```

3. **如果需要通信**：
   ```bash
   # 将容器连接到两个网络
   docker network connect backend-network frontend-app
   ```

## ❌ 无法实现的功能

**不能实现的**：
- ❌ 创建两个独立的 docker 组同时访问同一个 daemon
- ❌ 完全隐藏对方的容器（仍然可以通过 `docker ps` 看到）
- ❌ 在权限层面完全隔离（如果都在 docker 组中）

**可以实现的**：
- ✅ 网络隔离（容器无法直接通信）
- ✅ 通过命名规范区分容器
- ✅ 通过项目名称隔离（docker-compose）
- ✅ 资源限制和监控

## 📝 总结

**回答你的问题**：
- ❌ **不能**创建两个独立的 docker 组同时访问同一个 Docker daemon
- ✅ **可以**通过网络隔离、命名规范、项目隔离来实现独立部署
- ✅ **可以**设置网络间通信规则，允许前端访问后端

**推荐做法**：
1. 前端和后端都使用同一个 docker 组（或者不给前端 docker 权限）
2. 使用独立的 Docker 网络实现网络隔离
3. 使用命名规范（frontend-* vs hifate-*）区分容器
4. 如果需要通信，通过 Docker 网络连接


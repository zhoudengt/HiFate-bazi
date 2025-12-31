# frontend-gateway 失败原因诊断报告

## 问题概述

在 `/opt/hifate-frontend` 目录下执行 `docker-compose up -d frontend-gateway` 失败。

## 根本原因分析

### 1. frontend-gateway 不是 Docker Compose 服务

**关键发现**：
- `frontend-gateway` **不是 Docker Compose 服务**，而是一个 **gRPC 服务**
- 它定义在 `proto/frontend_gateway.proto` 中，作为 `FrontendGateway` gRPC 服务
- 通过主 Web 服务的 gRPC-Web 网关访问，而不是独立的 Docker 容器

### 2. 服务定义位置

**gRPC 服务定义**：
- 文件：`proto/frontend_gateway.proto`
- 服务名：`FrontendGateway`
- 方法：`Call(FrontendJsonRequest) returns (FrontendJsonResponse)`

**gRPC-Web 网关实现**：
- 文件：`server/api/grpc_gateway.py`
- 端点：`/api/grpc-web/frontend.gateway.FrontendGateway/Call`
- 实现函数：`grpc_web_gateway(request: Request)`

### 3. 正确的访问方式

**不应该**：
```bash
# ❌ 错误：尝试启动 frontend-gateway 容器
cd /opt/hifate-frontend
docker-compose up -d frontend-gateway
```

**应该**：
```bash
# ✅ 正确：通过主 Web 服务访问 gRPC-Web 网关
curl -X POST http://8.210.52.217:8001/api/grpc-web/frontend.gateway.FrontendGateway/Call \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### 4. /opt/hifate-frontend 目录的用途

根据项目配置，`/opt/hifate-frontend` 目录用于：

1. **前端用户专用目录**（frontend-user）
2. **前端 Nginx 服务部署**（不是 frontend-gateway）
3. **前端静态文件服务**

**相关配置文件**：
- `docker-compose.frontend.yml` - 定义 `nginx-frontend` 服务（不是 frontend-gateway）
- `frontend-config/nginx.conf` - Nginx 配置文件

## 可能的具体错误场景

### 场景 1：docker-compose.yml 中不存在 frontend-gateway 服务

**错误信息**：
```
ERROR: Service 'frontend-gateway' not found
```

**原因**：
- `/opt/hifate-frontend` 目录下的 docker-compose.yml 文件中没有定义 `frontend-gateway` 服务
- 该目录只包含 `nginx-frontend` 服务定义

### 场景 2：buildx 版本问题

**错误信息**：
```
compose build requires buildx 0.17 or later
```

**原因**：
- Docker Buildx 版本过低（< 0.17.0）
- 即使服务存在，也无法构建

**解决方案**：
```bash
# 升级 buildx
sudo yum update -y docker-buildx-plugin
# 或
sudo apt-get install -y docker-buildx-plugin
```

### 场景 3：端口冲突

**错误信息**：
```
Error response from daemon: driver failed programming external connectivity on endpoint: Bind for 0.0.0.0:80 failed: port is already allocated
```

**原因**：
- 如果尝试创建 frontend-gateway 服务并使用 80/443 端口
- 这些端口可能已被 `nginx-frontend` 或后端 `hifate-nginx` 占用

## 诊断检查清单

### 1. 检查目录结构

```bash
# 检查 /opt/hifate-frontend 目录
ls -la /opt/hifate-frontend

# 查找 docker-compose 文件
find /opt/hifate-frontend -name "docker-compose*.yml"
```

### 2. 检查服务定义

```bash
# 检查是否有 frontend-gateway 服务定义
grep -r "frontend-gateway" /opt/hifate-frontend/docker-compose*.yml

# 检查实际定义的服务
cat /opt/hifate-frontend/docker-compose.yml
```

### 3. 检查容器状态

```bash
# 检查是否有 frontend-gateway 容器
docker ps -a | grep frontend-gateway

# 检查 nginx-frontend 容器（应该存在）
docker ps -a | grep nginx-frontend
```

### 4. 检查 gRPC 服务状态

```bash
# 检查主 Web 服务是否运行
docker ps | grep hifate-web

# 测试 gRPC-Web 网关是否可用
curl -X POST http://8.210.52.217:8001/api/grpc-web/frontend.gateway.FrontendGateway/Call \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/health", "payload_json": "{}"}'
```

### 5. 检查错误日志

```bash
# 如果容器存在，查看日志
docker logs frontend-gateway 2>&1 | tail -50

# 检查 docker-compose 错误
cd /opt/hifate-frontend
docker-compose config 2>&1
```

## 解决方案

### 方案 1：使用正确的访问方式（推荐）

**如果目标是访问 FrontendGateway 服务**：

1. **确保主 Web 服务运行**：
   ```bash
   docker ps | grep hifate-web
   ```

2. **通过 gRPC-Web 网关访问**：
   ```bash
   curl -X POST http://8.210.52.217:8001/api/grpc-web/frontend.gateway.FrontendGateway/Call \
     -H "Content-Type: application/json" \
     -d '{"endpoint": "/health", "payload_json": "{}"}'
   ```

### 方案 2：如果需要独立的 frontend-gateway 容器

**如果确实需要创建独立的 frontend-gateway 容器**（不推荐）：

1. **创建 docker-compose.frontend-gateway.yml**：
   ```yaml
   version: '3.8'
   
   services:
     frontend-gateway:
       image: nginx:alpine
       container_name: hifate-frontend-gateway
       ports:
         - "8080:80"  # 使用非后端端口
       volumes:
         - ./local_frontend:/usr/share/nginx/html:ro
       networks:
         - frontend-network
       restart: always
   
   networks:
     frontend-network:
       driver: bridge
   ```

2. **启动服务**：
   ```bash
   cd /opt/hifate-frontend
   docker-compose -f docker-compose.frontend-gateway.yml up -d
   ```

**注意**：这个方案会创建一个独立的 Nginx 容器，但不会提供 gRPC 服务功能。

### 方案 3：修复 buildx 版本问题

**如果错误是 buildx 版本问题**：

```bash
# 使用自动修复脚本
cd /opt/HiFate-bazi
bash scripts/fix_buildx_version.sh

# 或手动升级
sudo yum update -y docker-buildx-plugin
# 或
sudo apt-get install -y docker-buildx-plugin
```

## 验证步骤

### 1. 验证 gRPC 服务可用性

```bash
# 测试 FrontendGateway 服务
python3 scripts/test_frontend_gateway.py
```

### 2. 验证主 Web 服务

```bash
# 检查健康状态
curl http://8.210.52.217:8001/health

# 检查 gRPC-Web 网关
curl -X POST http://8.210.52.217:8001/api/grpc-web/frontend.gateway.FrontendGateway/Call \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/health", "payload_json": "{}"}'
```

### 3. 验证前端 Nginx 服务

```bash
# 检查 nginx-frontend 容器
docker ps | grep nginx-frontend

# 测试前端服务
curl http://8.210.52.217/
```

## 总结

**核心问题**：
- `frontend-gateway` 不是 Docker Compose 服务，而是 gRPC 服务
- 应该通过主 Web 服务的 gRPC-Web 网关访问，而不是启动独立容器

**建议**：
1. 不要尝试在 `/opt/hifate-frontend` 目录下启动 `frontend-gateway` 容器
2. 使用正确的 gRPC-Web 网关路径访问 FrontendGateway 服务
3. 如果确实需要独立容器，先明确需求，然后创建正确的服务定义

## 相关文档

- `docs/fix_buildx_version_guide.md` - buildx 版本问题修复指南
- `proto/frontend_gateway.proto` - FrontendGateway gRPC 服务定义
- `server/api/grpc_gateway.py` - gRPC-Web 网关实现
- `docker-compose.frontend.yml` - 前端 Docker Compose 配置（nginx-frontend）







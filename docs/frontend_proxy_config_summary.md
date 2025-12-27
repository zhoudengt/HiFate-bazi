# 前端代理配置说明

## 📋 配置概述

为前端用户添加了两个 Nginx 反向代理配置，用于将前端请求转发到后端服务。

## 🔧 配置详情

### 1. Nacos 配置中心代理

**配置位置**：`frontend-config/nginx.conf`

**路径**：`/nacos`  
**目标**：`http://127.0.0.1:9060`

**作用**：
- 将前端对 `/nacos` 的请求代理到本地 9060 端口的 Nacos 服务
- 支持 Nacos 配置中心的 Web 界面访问
- 支持 WebSocket（用于实时配置更新）

**使用场景**：
- 前端需要访问 Nacos 配置中心管理界面
- 通过统一的 Nginx 入口访问，避免直接暴露 9060 端口

**配置特点**：
- WebSocket 支持（`Upgrade` 和 `Connection` 头）
- 禁用缓冲（`proxy_buffering off`）
- 60 秒超时设置

### 2. Destiny gRPC-Web 网关代理

**配置位置**：`frontend-config/nginx.conf`

**路径**：`/destiny/api/grpc-web/`  
**目标**：`http://127.0.0.1:9070`

**作用**：
- 将前端对 `/destiny/api/grpc-web/` 的请求代理到本地 9070 端口的 Destiny 服务
- 支持 gRPC-Web 协议（前端通过 HTTP 调用 gRPC 服务）
- 完整路径：`/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call`

**使用场景**：
- 前端通过 gRPC-Web 调用 Destiny 服务的 `FrontendGateway`
- 统一的 API 网关入口
- 支持流式传输

**配置特点**：
- gRPC-Web 协议支持（`Content-Type: application/grpc-web+proto`）
- 流式传输支持（禁用缓冲）
- CORS 支持（跨域请求）
- 300 秒超时设置（适合长时间运行的 gRPC 调用）

## 🚀 部署方法

### 方法 1：使用自动部署脚本（推荐）

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
export SSH_PASSWORD="Yuanqizhan@163"
bash scripts/deploy_frontend_proxy_dual_nodes.sh
```

### 方法 2：手动部署

#### 在 Node1 上部署

```bash
# 1. SSH 连接到 Node1
ssh frontend-user@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码
git pull origin master

# 4. 重启前端 Nginx 服务
docker-compose -f docker-compose.frontend.yml restart nginx-frontend

# 5. 验证配置
docker exec hifate-frontend-nginx nginx -t
```

#### 在 Node2 上部署

```bash
# 1. SSH 连接到 Node2
ssh frontend-user@47.243.160.43

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码
git pull origin master

# 4. 重启前端 Nginx 服务
docker-compose -f docker-compose.frontend.yml restart nginx-frontend

# 5. 验证配置
docker exec hifate-frontend-nginx nginx -t
```

## ✅ 验证配置

### 检查 Nginx 配置语法

```bash
docker exec hifate-frontend-nginx nginx -t
```

应该显示：
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 测试 Nacos 代理

```bash
# 测试 Nacos 代理（需要 Nacos 服务运行在 9060 端口）
curl http://localhost/nacos/
```

### 测试 Destiny gRPC-Web 代理

```bash
# 测试 Destiny gRPC-Web 代理（需要 Destiny 服务运行在 9070 端口）
curl -X POST http://localhost/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/test", "payload_json": "{}"}'
```

## 📝 技术说明

### 为什么使用 Nginx 反向代理？

1. **统一入口**：所有前端请求通过同一个 Nginx 入口，便于管理和监控
2. **安全隔离**：不直接暴露后端服务端口（9060、9070）
3. **负载均衡**：可以轻松扩展为多后端服务
4. **SSL/TLS**：可以在 Nginx 层面统一处理 HTTPS

### 为什么使用 `127.0.0.1`？

- `127.0.0.1` 表示本地回环地址
- 如果服务运行在 Docker 容器中，需要使用 Docker 网络或 `host` 网络模式
- 如果服务运行在宿主机上，使用 `127.0.0.1` 即可

### gRPC-Web 协议说明

- gRPC-Web 是 gRPC 的 Web 版本，允许浏览器通过 HTTP 调用 gRPC 服务
- 需要设置正确的 `Content-Type: application/grpc-web+proto`
- 支持流式传输，需要禁用缓冲

## ⚠️ 注意事项

1. **端口要求**：
   - Nacos 服务必须运行在 `localhost:9060`
   - Destiny 服务必须运行在 `localhost:9070`
   - 确保这些服务在 Nginx 容器内可以访问

2. **网络配置**：
   - 如果服务运行在 Docker 容器中，需要使用 Docker 网络
   - 如果服务运行在宿主机上，使用 `127.0.0.1` 或宿主机 IP

3. **服务依赖**：
   - 确保 Nacos 和 Destiny 服务已启动
   - 如果服务未启动，代理会返回 502 Bad Gateway

4. **CORS 配置**：
   - Destiny 代理已配置 CORS 支持（允许所有来源）
   - 如果需要限制来源，修改 `Access-Control-Allow-Origin` 头

## 📚 相关文件

- `frontend-config/nginx.conf` - 前端 Nginx 配置文件
- `docker-compose.frontend.yml` - 前端 Docker Compose 配置
- `scripts/deploy_frontend_proxy_dual_nodes.sh` - 双机部署脚本
- `docs/frontend_proxy_config_guide.md` - 详细配置指南


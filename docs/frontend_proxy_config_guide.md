# 前端用户 Nginx 代理配置指南

## 📋 配置说明

为前端用户添加了两个 Nginx 反向代理配置：

### 1. Nacos 配置中心代理

- **路径**：`/nacos`
- **目标**：`localhost:9060`
- **用途**：代理到 Nacos 配置中心服务
- **支持**：WebSocket（用于 Nacos 实时配置更新）

### 2. Destiny gRPC-Web 网关代理

- **路径**：`/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call`
- **目标**：`localhost:9070`
- **用途**：代理到 Destiny 服务的 gRPC-Web 网关
- **支持**：gRPC-Web 协议、流式传输、CORS

## 🔧 配置位置

配置文件：`frontend-config/nginx.conf`

## 🚀 部署到双机

### 方法 1：使用自动部署脚本（推荐）

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
bash scripts/deploy_frontend_proxy_dual_nodes.sh
```

### 方法 2：手动部署

#### Node1 部署

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

#### Node2 部署

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

## 📝 配置详情

### Nacos 代理配置

```nginx
location /nacos {
    proxy_pass http://127.0.0.1:9060;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket 支持
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # 缓冲设置
    proxy_buffering off;
}
```

### Destiny gRPC-Web 代理配置

```nginx
location /destiny/api/grpc-web/ {
    proxy_pass http://127.0.0.1:9070;
    proxy_http_version 1.1;
    
    # gRPC-Web 特定配置
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Content-Type application/grpc-web+proto;
    
    # 超时设置（gRPC 可能需要更长时间）
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # 禁用缓冲（流式传输）
    proxy_buffering off;
    proxy_cache off;
    
    # CORS 支持
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    
    # 处理 OPTIONS 预检请求
    if ($request_method = OPTIONS) {
        return 204;
    }
}
```

## ⚠️ 注意事项

1. **端口要求**：
   - Nacos 服务必须运行在 `localhost:9060`
   - Destiny 服务必须运行在 `localhost:9070`
   - 确保这些服务在 Nginx 容器内可以访问（使用 `127.0.0.1` 或容器网络）

2. **网络配置**：
   - 如果服务运行在 Docker 容器中，需要使用 Docker 网络或 `host` 网络模式
   - 如果服务运行在宿主机上，使用 `127.0.0.1` 或宿主机 IP

3. **权限要求**：
   - frontend-user 需要有权限重启 Nginx 容器
   - 确保 Nginx 容器可以访问目标服务

4. **CORS 配置**：
   - Destiny gRPC-Web 代理已配置 CORS 支持
   - 如果需要限制来源，修改 `Access-Control-Allow-Origin` 头

## 🔍 故障排查

### 问题 1：502 Bad Gateway

**原因**：目标服务未运行或无法访问

**解决**：
```bash
# 检查服务是否运行
netstat -tlnp | grep 9060  # Nacos
netstat -tlnp | grep 9070  # Destiny

# 检查 Nginx 容器网络
docker exec hifate-frontend-nginx ping 127.0.0.1
```

### 问题 2：404 Not Found

**原因**：路径配置错误

**解决**：
- 检查 Nginx 配置中的 `location` 路径
- 检查目标服务的实际路径

### 问题 3：CORS 错误

**原因**：CORS 头未正确设置

**解决**：
- 检查 Nginx 配置中的 CORS 头
- 确保 `Access-Control-Allow-Origin` 设置正确

## 📚 相关文件

- `frontend-config/nginx.conf` - 前端 Nginx 配置文件
- `docker-compose.frontend.yml` - 前端 Docker Compose 配置
- `scripts/deploy_frontend_proxy_dual_nodes.sh` - 双机部署脚本


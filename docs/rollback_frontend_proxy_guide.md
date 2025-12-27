# 撤回前端代理配置指南

## 📋 撤回内容

需要撤回以下两个代理配置：
1. **Nacos 代理**：`/nacos` -> `localhost:9060`
2. **Destiny gRPC-Web 代理**：`/destiny/api/grpc-web/` -> `localhost:9070`

## ✅ 本地配置已撤回

本地配置文件 `frontend-config/nginx.conf` 已移除这两个配置。

## 🚀 在双机上撤回配置

### 方法 1：使用自动撤回脚本（推荐）

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
export SSH_PASSWORD="Yuanqizhan@163"
bash scripts/rollback_frontend_proxy_dual_nodes.sh --yes
```

### 方法 2：手动撤回

#### Node1 撤回步骤

```bash
# 1. SSH 连接到 Node1
ssh root@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码（包含撤回的配置）
git pull origin master

# 4. 验证配置文件已更新（应该不包含 /nacos 和 /destiny/api/grpc-web）
grep -n "/nacos\|/destiny/api/grpc-web" frontend-config/nginx.conf
# 如果没有输出，说明配置已移除

# 5. 如果配置文件中仍有旧配置，手动移除
# 编辑配置文件
vim frontend-config/nginx.conf
# 删除以下两个 location 块：
#   - location /nacos { ... }
#   - location /destiny/api/grpc-web/ { ... }

# 6. 重启前端 Nginx 服务
docker-compose -f docker-compose.frontend.yml restart nginx-frontend

# 7. 验证配置
docker exec hifate-frontend-nginx nginx -t
```

#### Node2 撤回步骤

```bash
# 1. SSH 连接到 Node2
ssh root@47.243.160.43

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码（包含撤回的配置）
git pull origin master

# 4. 验证配置文件已更新（应该不包含 /nacos 和 /destiny/api/grpc-web）
grep -n "/nacos\|/destiny/api/grpc-web" frontend-config/nginx.conf
# 如果没有输出，说明配置已移除

# 5. 如果配置文件中仍有旧配置，手动移除
# 编辑配置文件
vim frontend-config/nginx.conf
# 删除以下两个 location 块：
#   - location /nacos { ... }
#   - location /destiny/api/grpc-web/ { ... }

# 6. 重启前端 Nginx 服务
docker-compose -f docker-compose.frontend.yml restart nginx-frontend

# 7. 验证配置
docker exec hifate-frontend-nginx nginx -t
```

## ✅ 验证撤回

### 检查配置文件

```bash
# 在服务器上检查配置文件
grep -n "/nacos\|/destiny/api/grpc-web" /opt/HiFate-bazi/frontend-config/nginx.conf
# 如果没有输出，说明配置已移除
```

### 检查 Nginx 配置语法

```bash
docker exec hifate-frontend-nginx nginx -t
```

应该显示：
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 测试代理是否已移除

```bash
# 测试 Nacos 代理（应该返回 404 或错误）
curl http://localhost/nacos/
# 应该返回 404 或无法连接

# 测试 Destiny 代理（应该返回 404 或错误）
curl http://localhost/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call
# 应该返回 404 或无法连接
```

## 📝 撤回的配置内容

### 已移除的配置 1：Nacos 代理

```nginx
# ============================================
# Nacos 配置中心代理
# 路径：/nacos -> localhost:9060
# ============================================
location /nacos {
    proxy_pass http://127.0.0.1:9060;
    # ... 其他配置 ...
}
```

### 已移除的配置 2：Destiny gRPC-Web 代理

```nginx
# ============================================
# Destiny gRPC-Web 网关代理
# 路径：/destiny/api/grpc-web/ -> localhost:9070
# ============================================
location /destiny/api/grpc-web/ {
    proxy_pass http://127.0.0.1:9070;
    # ... 其他配置 ...
}
```

## 🔍 故障排查

### 问题 1：配置文件仍有旧配置

**原因**：Git 拉取失败或配置文件未更新

**解决**：
```bash
# 手动编辑配置文件
vim /opt/HiFate-bazi/frontend-config/nginx.conf

# 删除以下内容：
#   - location /nacos { ... } 块（第 64-87 行）
#   - location /destiny/api/grpc-web/ { ... } 块（第 89-122 行）

# 保存后重启 Nginx
docker-compose -f docker-compose.frontend.yml restart nginx-frontend
```

### 问题 2：Nginx 配置验证失败

**原因**：配置文件语法错误

**解决**：
```bash
# 检查配置文件语法
docker exec hifate-frontend-nginx nginx -t

# 查看错误信息，修复语法错误
# 然后重新验证
```

### 问题 3：服务重启失败

**原因**：Docker Compose 配置问题或容器不存在

**解决**：
```bash
# 检查容器是否存在
docker ps -a | grep nginx-frontend

# 如果容器不存在，重新创建
docker-compose -f docker-compose.frontend.yml up -d nginx-frontend

# 如果容器存在但无法重启，强制重新创建
docker-compose -f docker-compose.frontend.yml up -d --force-recreate nginx-frontend
```

## 📚 相关文件

- `frontend-config/nginx.conf` - 前端 Nginx 配置文件（已移除配置）
- `scripts/rollback_frontend_proxy_dual_nodes.sh` - 双机撤回脚本
- `scripts/deploy_frontend_proxy_dual_nodes.sh` - 双机部署脚本（已废弃）

## ✅ 撤回检查清单

- [ ] 本地配置文件已移除两个代理配置
- [ ] Node1 配置文件已更新（拉取最新代码）
- [ ] Node2 配置文件已更新（拉取最新代码）
- [ ] Node1 Nginx 服务已重启
- [ ] Node2 Nginx 服务已重启
- [ ] Node1 Nginx 配置验证通过
- [ ] Node2 Nginx 配置验证通过
- [ ] 验证代理路径已无法访问（404 或错误）


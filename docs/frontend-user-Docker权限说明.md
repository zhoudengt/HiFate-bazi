# frontend-user Docker 权限说明

## 📋 权限状态

**已授权**：frontend-user 在双机上都可以使用 Docker

- ✅ Node1 (8.210.52.217): frontend-user 在 docker 组中
- ✅ Node2 (47.243.160.43): frontend-user 在 docker 组中

## 🔓 授权内容

frontend-user 现在拥有完整的 Docker 权限：

| 功能 | 权限 |
|------|------|
| 查看容器 | ✅ `docker ps` |
| 查看镜像 | ✅ `docker images` |
| 部署容器 | ✅ `docker run` |
| 停止容器 | ✅ `docker stop` |
| 启动容器 | ✅ `docker start` |
| 删除容器 | ✅ `docker rm` |
| 查看日志 | ✅ `docker logs` |
| 执行命令 | ✅ `docker exec` |

## ⚠️ 安全提示

### 当前权限范围

- **可以看到所有 Docker 容器**（包括后端容器）
- **可以管理所有 Docker 容器**（包括停止/删除后端容器）
- **可以部署新容器**（需要确保不影响后端服务）

### 建议的安全措施

1. **网络隔离**
   - 建议 frontend-user 部署的容器使用独立的 Docker 网络
   - 避免与后端容器在同一网络中

2. **资源限制**
   - 建议使用 Docker 资源限制（CPU、内存）
   - 避免影响后端服务性能

3. **端口管理**
   - 确保 frontend-user 部署的容器不占用后端服务的端口
   - 后端服务端口：8001, 9001-9010, 3306, 6379

4. **命名规范**
   - 建议 frontend-user 部署的容器使用特定前缀（如 `frontend-*`）
   - 便于识别和管理

5. **定期检查**
   - 定期检查 frontend-user 部署的容器
   - 确保没有影响后端服务

## 🛠️ 管理脚本

### 授权 Docker 访问

```bash
bash scripts/grant_docker_access_to_frontend_user.sh
```

功能：
- 将 frontend-user 添加到 docker 组（双机）
- 检查 docker.sock 权限
- 验证 docker 命令可用

### 验证 Docker 访问

```bash
bash scripts/verify_frontend_user_docker_access.sh
```

功能：
- 验证 frontend-user 可以执行 docker 命令
- 检查 docker 组权限
- 测试 docker ps/images/run 命令

### 撤销 Docker 访问（如果需要）

```bash
bash scripts/remove_frontend_user_from_docker_group.sh
```

功能：
- 从 docker 组中移除 frontend-user
- 禁止 frontend-user 使用 Docker

## 📝 使用示例

### frontend-user 部署自己的容器

```bash
# 切换到 frontend-user
su - frontend-user

# 查看现有容器
docker ps

# 部署新容器（示例）
docker run -d \
  --name frontend-app \
  --network bridge \
  -p 8080:80 \
  nginx:alpine

# 查看容器日志
docker logs frontend-app

# 停止容器
docker stop frontend-app

# 删除容器
docker rm frontend-app
```

### 创建独立网络（推荐）

```bash
# 作为 root 创建前端专用网络
docker network create frontend-network

# frontend-user 可以使用这个网络
docker run -d \
  --name frontend-app \
  --network frontend-network \
  -p 8080:80 \
  nginx:alpine
```

## 🔍 当前权限配置

### 用户组

```
frontend-user: frontend-group, docker
```

### Docker Socket 权限

```
/var/run/docker.sock: srw-rw---- root:docker
```

### 目录权限

| 目录 | 权限 | frontend-user 权限 |
|------|------|-------------------|
| `/opt/hifate-frontend` | 775 + ACL | 读写执行 |
| `/opt/HiFate-bazi` | 750 | 无权限 |
| `/opt` | 751 | 无法列出其他目录 |

## 📊 权限总结

| 功能 | 权限状态 |
|------|---------|
| 访问 `/opt/hifate-frontend` | ✅ 有 |
| 访问 `/opt/HiFate-bazi` | ❌ 无 |
| 使用 Docker | ✅ 有 |
| 查看所有容器 | ✅ 可以 |
| 部署自己的容器 | ✅ 可以 |
| 管理后端容器 | ⚠️ 可以（需谨慎） |

## ⚠️ 重要提醒

1. **不要停止后端容器**
   - frontend-user 可以停止后端容器，但不要这样做
   - 后端容器名称：`hifate-*`

2. **不要占用后端端口**
   - 后端服务端口：8001, 9001-9010, 3306, 6379
   - 使用其他端口（如 8080, 8081 等）

3. **不要删除后端镜像**
   - 后端镜像：`registry.cn-hangzhou.aliyuncs.com/hifate/hifate-bazi:*`
   - 只管理自己的镜像

4. **资源使用**
   - 注意 CPU 和内存使用
   - 避免影响后端服务性能

## 📅 最后更新

- 授权时间：2025-01-XX
- Node1: ✅ 已授权
- Node2: ✅ 已授权


# Docker Compose buildx 版本问题修复指南

## 问题描述

执行 `docker-compose up -d frontend-gateway` 时遇到错误：
```
compose build requires buildx 0.17 or later
```

## 原因分析

1. **buildx 版本过低**：当前安装的 Docker Buildx 版本低于 0.17.0
2. **服务定义问题**：`frontend-gateway` 可能不是 Docker Compose 服务，而是 gRPC 服务

## 快速修复

### 方法 1：使用自动修复脚本（推荐）

在服务器上执行：

```bash
cd /opt/HiFate-bazi
bash scripts/fix_buildx_version.sh
```

脚本会自动：
- 检查当前 buildx 版本
- 如果版本 < 0.17，自动升级
- 查找 frontend-gateway 服务定义
- 验证修复结果

### 方法 2：手动升级 buildx

#### 对于 Alibaba Cloud Linux 3（使用 yum）

```bash
# 检查当前版本
docker buildx version

# 升级 buildx
sudo yum update -y docker-buildx-plugin

# 验证版本
docker buildx version
```

#### 对于 Ubuntu/Debian（使用 apt）

```bash
# 检查当前版本
docker buildx version

# 升级 buildx
sudo apt-get update
sudo apt-get install -y docker-buildx-plugin

# 验证版本
docker buildx version
```

#### 手动安装最新版本

如果包管理器升级失败，可以手动安装：

```bash
# 创建插件目录
mkdir -p ~/.docker/cli-plugins

# 检测架构
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    BUILDX_ARCH="linux-amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    BUILDX_ARCH="linux-arm64"
else
    echo "不支持的架构：$ARCH"
    exit 1
fi

# 下载 buildx 0.17.0
curl -L "https://github.com/docker/buildx/releases/download/v0.17.0/buildx-v0.17.0-${BUILDX_ARCH}" \
    -o ~/.docker/cli-plugins/docker-buildx

# 设置执行权限
chmod +x ~/.docker/cli-plugins/docker-buildx

# 验证安装
docker buildx version
```

## 关于 frontend-gateway 服务

### 检查服务定义

查找包含 `frontend-gateway` 的 docker-compose 文件：

```bash
cd /opt/HiFate-bazi
find . -name "docker-compose*.yml" -o -name "docker-compose*.yaml" | xargs grep -l "frontend-gateway"
```

### 如果服务不存在

`frontend-gateway` 实际上是一个 **gRPC 服务**（`FrontendGateway`），定义在：
- `proto/frontend_gateway.proto` - gRPC 服务定义
- `server/api/grpc_gateway.py` - gRPC-Web 网关实现

**不是 Docker Compose 服务**，应该通过主 Web 服务访问：
- 路径：`/api/grpc-web/frontend.gateway.FrontendGateway/Call`

### 如果需要创建 Docker Compose 服务

如果确实需要独立的 `frontend-gateway` 服务，可以创建 `docker-compose.frontend-gateway.yml`：

```yaml
version: '3.8'

services:
  frontend-gateway:
    image: nginx:alpine  # 或使用其他镜像
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

然后使用：
```bash
docker-compose -f docker-compose.frontend-gateway.yml up -d
```

## 验证修复

1. **检查 buildx 版本**：
   ```bash
   docker buildx version
   # 应该显示 v0.17.0 或更高
   ```

2. **测试 Docker Compose**：
   ```bash
   docker-compose --version
   docker compose version
   ```

3. **如果 frontend-gateway 服务存在，测试启动**：
   ```bash
   docker-compose up -d frontend-gateway
   ```

4. **如果不需要构建，使用 --no-build**：
   ```bash
   docker-compose up -d --no-build frontend-gateway
   ```

## 常见问题

### Q1: 升级后仍然报错

**原因**：可能需要重启 Docker 或重新加载插件

**解决**：
```bash
# 重新加载 Docker
sudo systemctl restart docker

# 或者重新登录（如果使用 SSH）
exit
# 重新登录后再次尝试
```

### Q2: 权限不足

**原因**：`frontend-user` 可能没有 sudo 权限

**解决**：
1. 使用手动安装方法（不需要 sudo）
2. 或联系管理员升级 buildx

### Q3: 找不到 frontend-gateway 服务

**原因**：服务可能不存在或名称不同

**解决**：
1. 检查所有 docker-compose 文件
2. 确认是否需要创建新服务
3. 如果 frontend-gateway 是 gRPC 服务，应该通过主服务访问

## 相关文件

- `scripts/fix_buildx_version.sh` - 自动修复脚本
- `deploy/scripts/init-ecs.sh` - ECS 初始化脚本（安装 buildx）
- `proto/frontend_gateway.proto` - FrontendGateway gRPC 服务定义
- `docker-compose.frontend.yml` - 前端 Docker Compose 配置

## 技术支持

如果问题仍然存在，请提供以下信息：

1. buildx 版本：`docker buildx version`
2. Docker Compose 版本：`docker-compose --version`
3. 系统信息：`cat /etc/os-release`
4. 错误日志：完整的错误信息


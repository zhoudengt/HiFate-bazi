# frontend-user Docker Rootless 使用指南

## 📋 概述

**Docker Rootless** 为 `frontend-user`（外包账户）提供了完全隔离的 Docker 环境：

- ✅ **完全隔离**：无法看到后端容器（hifate-*）
- ✅ **无需 sudo**：不需要 root 或 sudo 权限
- ✅ **独立环境**：拥有自己的 Docker daemon 和网络
- ✅ **安全可靠**：无法影响后端服务

## 🔧 安装状态

✅ **已安装并配置**：Docker Rootless 已在双机上安装并配置

- ✅ Node1 (8.210.52.217): Docker Rootless 已安装并运行
- ✅ Node2 (47.243.160.43): Docker Rootless 已安装并运行

## 📍 关键路径

| 项目 | 路径 | 说明 |
|------|------|------|
| **Docker 客户端** | `~/bin/docker` | Rootless Docker 客户端 |
| **Docker daemon** | `~/bin/dockerd-rootless.sh` | Rootless Docker daemon |
| **Docker socket** | `~/.docker/run/docker.sock` | Rootless Docker socket |
| **环境变量** | `~/.bashrc` | DOCKER_HOST 等环境变量 |

## 🔐 环境变量配置

环境变量已自动配置在 `~/.bashrc` 中：

```bash
# Docker Rootless 环境变量
export XDG_RUNTIME_DIR=$HOME/.docker/run
export PATH=$HOME/bin:$PATH
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
```

**重要**：重新登录或执行 `source ~/.bashrc` 后环境变量才会生效。

## 📝 使用方式

### 基本命令

```bash
# 切换到 frontend-user
su - frontend-user

# 或者如果已登录，重新加载环境变量
source ~/.bashrc

# 查看 Docker 版本
docker version

# 查看所有容器（只显示 Rootless Docker 的容器）
docker ps

# 查看所有容器（包括停止的）
docker ps -a

# 查看镜像
docker images

# 查看网络
docker network ls

# 查看卷
docker volume ls
```

### 创建容器

```bash
# 创建容器（使用 frontend-network）
docker run -d \
  --name frontend-app \
  --network frontend-network \
  -p 8080:80 \
  nginx:alpine

# 创建容器（使用默认网络）
docker run -d \
  --name frontend-app2 \
  -p 8081:80 \
  nginx:alpine
```

### 管理容器

```bash
# 停止容器
docker stop frontend-app

# 启动容器
docker start frontend-app

# 重启容器
docker restart frontend-app

# 删除容器
docker rm frontend-app

# 强制删除容器
docker rm -f frontend-app
```

### 查看日志

```bash
# 查看容器日志
docker logs frontend-app

# 实时查看日志
docker logs -f frontend-app

# 查看最近 100 行日志
docker logs --tail 100 frontend-app
```

### 进入容器

```bash
# 进入容器
docker exec -it frontend-app sh

# 执行命令
docker exec frontend-app ls -la
```

### 网络管理

```bash
# 查看网络列表
docker network ls

# 查看网络详情
docker network inspect frontend-network

# 创建新网络
docker network create frontend-network2

# 删除网络
docker network rm frontend-network2
```

## 🔒 隔离特性

### 1. 容器隔离

**Rootless Docker 无法看到后端容器**：

```bash
# Rootless Docker 中的容器列表（只显示自己的容器）
docker ps

# 后端容器（hifate-*）不会出现在列表中
```

### 2. 网络隔离

**Rootless Docker 使用独立的网络命名空间**：

```bash
# Rootless Docker 网络（只显示自己的网络）
docker network ls

# 后端网络（docker_hifate-network）不会出现在列表中
```

### 3. Socket 隔离

**Rootless Docker 使用独立的 socket**：

```bash
# Rootless Docker socket
~/.docker/run/docker.sock

# 后端 Docker socket（无法访问）
/var/run/docker.sock  # permission denied
```

## ⚠️ 重要限制

### 1. 端口范围

**Rootless Docker 只能绑定 > 1024 的端口**：

- ✅ **可以使用**：8080, 8081, 9000, 10000 等
- ❌ **不能使用**：80, 443, 22, 3306 等（< 1024）

**后端端口（禁止使用）**：
- 8001 (Web 服务)
- 9001-9010 (微服务)
- 3306 (MySQL)
- 6379 (Redis)

**前端端口（推荐使用）**：
- 8080-8999 (前端服务)

### 2. 功能限制

**某些 Docker 功能在 Rootless 模式下可能受限**：

- ⚠️ 某些存储驱动可能不可用
- ⚠️ 某些网络模式可能受限
- ⚠️ 性能可能略低于 root Docker（通常 < 5%）

**对于前端部署场景，这些限制通常不影响使用。**

## 🚀 启动和停止 Rootless Docker

### 启动服务

```bash
# 方式 1: 使用 systemd（推荐）
systemctl --user start docker

# 方式 2: 手动启动
nohup ~/bin/dockerd-rootless.sh > /tmp/dockerd-rootless.log 2>&1 &
```

### 停止服务

```bash
# 方式 1: 使用 systemd
systemctl --user stop docker

# 方式 2: 手动停止
pkill dockerd-rootless
```

### 查看服务状态

```bash
# 查看 systemd 服务状态
systemctl --user status docker

# 查看 Docker 版本（验证服务是否运行）
docker version
```

### 自动启动

服务已配置为自动启动（通过 systemd user service）：

```bash
# 启用自动启动
systemctl --user enable docker

# 检查是否已启用
systemctl --user is-enabled docker
```

## 🔍 故障排查

### 问题 1: docker 命令找不到

**症状**：`docker: command not found`

**原因**：PATH 环境变量未设置

**解决**：
```bash
# 重新加载环境变量
source ~/.bashrc

# 或手动设置
export PATH=$HOME/bin:$PATH
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
```

### 问题 2: Cannot connect to Docker daemon

**症状**：`Cannot connect to the Docker daemon at unix://...`

**原因**：Rootless Docker daemon 未启动

**解决**：
```bash
# 启动 Rootless Docker
systemctl --user start docker

# 或手动启动
nohup ~/bin/dockerd-rootless.sh > /tmp/dockerd-rootless.log 2>&1 &

# 等待几秒后重试
sleep 3
docker ps
```

### 问题 3: 端口绑定失败

**症状**：`bind: permission denied` 或 `port is already allocated`

**原因**：
- 端口 < 1024（Rootless Docker 不支持）
- 端口已被占用

**解决**：
```bash
# 使用 > 1024 的端口
docker run -d -p 8080:80 nginx:alpine  # ✅ 正确
docker run -d -p 80:80 nginx:alpine    # ❌ 错误

# 检查端口占用
netstat -tlnp | grep :8080
```

### 问题 4: 网络创建失败

**症状**：`network create failed`

**原因**：Rootless Docker daemon 未运行或权限问题

**解决**：
```bash
# 确保 Rootless Docker 正在运行
docker version

# 检查网络列表
docker network ls

# 如果 frontend-network 不存在，创建它
docker network create frontend-network
```

## 📊 与 root Docker 对比

| 功能 | Root Docker | Rootless Docker |
|------|------------|----------------|
| **权限要求** | root 或 docker 组 | 无需特殊权限 |
| **Socket 位置** | `/var/run/docker.sock` | `~/.docker/run/docker.sock` |
| **容器可见性** | 所有容器 | 只看到自己的容器 |
| **网络隔离** | 共享网络命名空间 | 独立网络命名空间 |
| **端口范围** | 所有端口 | 只能使用 > 1024 |
| **性能** | 100% | 95-99% |
| **功能完整性** | 100% | 95-98% |

## ✅ 验证清单

使用前请验证：

- [ ] 环境变量已设置（`echo $DOCKER_HOST`）
- [ ] Rootless Docker 正在运行（`docker version`）
- [ ] 无法看到后端容器（`docker ps` 不显示 hifate-*）
- [ ] 无法访问后端 socket（`test -r /var/run/docker.sock` 失败）
- [ ] 可以创建和管理自己的容器
- [ ] 网络隔离正常（无法看到后端网络）

## 📚 相关文档

- [frontend-user Docker 受限权限说明](./frontend-user-Docker受限权限说明.md) - 旧方案说明（已废弃）
- [frontend-user 权限配置说明](./frontend-user权限配置说明.md) - 目录权限说明

## 📅 配置信息

- **安装时间**：2025-12-27
- **Docker Rootless 版本**：29.1.3
- **Node1**: ✅ 已安装并运行
- **Node2**: ✅ 已安装并运行
- **最后更新**：2025-12-27

## 🎯 总结

**Docker Rootless 方案的优势**：

1. ✅ **完全隔离**：无法看到或操作后端容器
2. ✅ **无需 sudo**：不需要 root 或 sudo 权限
3. ✅ **安全可靠**：无法影响后端服务
4. ✅ **简单易用**：使用方式与普通 Docker 相同

**适合场景**：
- 外包账户需要独立的 Docker 环境
- 需要完全隔离前端和后端容器
- 不需要 root 权限的 Docker 使用场景


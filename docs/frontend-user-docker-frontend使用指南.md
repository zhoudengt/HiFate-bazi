# frontend-user docker-frontend 使用指南

## ⚠️ 重要提示

**本方案已废弃**，已升级为 **Docker Rootless 方案**。

**新方案优势**：
- ✅ 完全隔离（无法看到后端容器）
- ✅ 无需 sudo/root 权限
- ✅ 更安全可靠

**请使用新方案**：查看 [frontend-user Docker Rootless 使用指南](./frontend-user-Docker-Rootless使用指南.md)

---

## 📋 安装状态（旧方案，已废弃）

✅ **已安装**：`docker-frontend` 已在双机上安装并配置权限

- ✅ Node1 (8.210.52.217): docker-frontend 已安装，frontend-user 有权限
- ✅ Node2 (47.243.160.43): docker-frontend 已安装，frontend-user 有权限

## 🔧 安装位置

```
/usr/local/bin/docker-frontend
```

## 🔐 权限配置

### sudo 规则

frontend-user 可以通过 sudo 无密码执行 docker-frontend：

```bash
# 配置文件：/etc/sudoers.d/frontend-docker
frontend-user ALL=(ALL) NOPASSWD: /usr/local/bin/docker-frontend
```

### 验证权限

```bash
# 检查 sudo 权限
sudo -l -U frontend-user
# 应该显示：NOPASSWD: /usr/local/bin/docker-frontend
```

## 📝 使用方式

### 基本命令

```bash
# 切换到 frontend-user
su - frontend-user

# 查看所有容器（只读，可以查看所有容器）
sudo docker-frontend ps

# 查看运行中的容器
sudo docker-frontend ps

# 查看所有容器（包括停止的）
sudo docker-frontend ps -a

# 查看镜像
sudo docker-frontend images

# 查看网络
sudo docker-frontend network ls

# 查看卷
sudo docker-frontend volume ls
```

### 创建容器

```bash
# ✅ 正确：使用 frontend-* 前缀
sudo docker-frontend run -d \
  --name frontend-app \
  --network frontend-network \
  -p 8080:80 \
  nginx:alpine

# ❌ 错误：不使用 frontend-* 前缀（会失败）
sudo docker-frontend run -d \
  --name app \
  nginx:alpine
# 错误：容器名称必须使用 frontend-* 前缀

# ❌ 错误：使用 hifate-* 前缀（会失败）
sudo docker-frontend run -d \
  --name hifate-app \
  nginx:alpine
# 错误：容器名称必须使用 frontend-* 前缀
```

### 管理容器

```bash
# 停止容器（只能停止 frontend-* 容器）
sudo docker-frontend stop frontend-app

# 启动容器
sudo docker-frontend start frontend-app

# 重启容器
sudo docker-frontend restart frontend-app

# 删除容器
sudo docker-frontend rm frontend-app

# 强制删除容器
sudo docker-frontend rm -f frontend-app
```

### 查看日志

```bash
# 查看容器日志
sudo docker-frontend logs frontend-app

# 实时查看日志
sudo docker-frontend logs -f frontend-app

# 查看最近 100 行日志
sudo docker-frontend logs --tail 100 frontend-app
```

### 进入容器

```bash
# 进入容器
sudo docker-frontend exec -it frontend-app sh

# 执行命令
sudo docker-frontend exec frontend-app ls -la
```

### 禁止的操作

```bash
# ❌ 禁止：直接使用 docker 命令
docker ps
# 错误：permission denied

# ❌ 禁止：操作后端容器
sudo docker-frontend stop hifate-web
# 错误：禁止操作非 frontend-* 容器: hifate-web

sudo docker-frontend rm hifate-web
# 错误：禁止操作非 frontend-* 容器: hifate-web

sudo docker-frontend exec hifate-web sh
# 错误：禁止操作非 frontend-* 容器: hifate-web
```

## 🔍 权限验证

### 验证安装

```bash
# 在服务器上执行
# 1. 检查脚本是否存在
ls -l /usr/local/bin/docker-frontend

# 2. 检查 sudo 规则
cat /etc/sudoers.d/frontend-docker

# 3. 检查 frontend-user 权限
sudo -l -U frontend-user
```

### 测试功能

```bash
# 切换到 frontend-user
su - frontend-user

# 测试 1: 直接使用 docker（应该失败）
docker ps
# 应该显示：permission denied

# 测试 2: 使用包装脚本（应该成功）
sudo docker-frontend ps
# 应该显示容器列表

# 测试 3: 操作后端容器（应该失败）
sudo docker-frontend stop hifate-web
# 应该显示：错误：禁止操作非 frontend-* 容器
```

## ⚠️ 重要提醒

### 1. 必须使用 sudo docker-frontend

```bash
# ✅ 正确
sudo docker-frontend ps

# ❌ 错误
docker ps  # 会失败
```

### 2. 容器命名规范

```bash
# ✅ 正确：使用 frontend-* 前缀
--name frontend-app
--name frontend-nginx
--name frontend-api

# ❌ 错误：不使用前缀或使用其他前缀
--name app          # 会失败
--name hifate-app   # 会失败
--name backend-app  # 会失败
```

### 3. 重新登录

**重要**：配置后，frontend-user 需要重新登录才能生效。

```bash
# 如果 frontend-user 已登录，需要退出并重新登录
exit
su - frontend-user

# 然后才能使用 sudo docker-frontend
```

### 4. 后端容器保护

- ❌ **完全禁止**操作 `hifate-*` 容器
- ✅ 后端服务正常运行，不受影响
- ✅ 配置过程不会停止或重启后端服务

## 📊 权限对比

| 操作 | 之前（完整权限） | 现在（受限权限） |
|------|----------------|----------------|
| 查看所有容器 | ✅ `docker ps` | ✅ `sudo docker-frontend ps` |
| 操作前端容器 | ✅ `docker stop frontend-app` | ✅ `sudo docker-frontend stop frontend-app` |
| 操作后端容器 | ⚠️ `docker stop hifate-web`（可以但禁止） | ❌ `sudo docker-frontend stop hifate-web`（完全禁止） |
| 直接使用 docker | ✅ 可以 | ❌ 禁止（必须使用包装脚本） |

## 🔄 故障排查

### 问题 1: sudo docker-frontend 提示输入密码

**原因**：sudo 规则未生效或用户未重新登录

**解决**：
```bash
# 检查 sudo 规则
sudo -l -U frontend-user

# 如果规则不存在，重新运行配置脚本
bash scripts/configure_frontend_docker_restricted.sh

# frontend-user 需要重新登录
exit
su - frontend-user
```

### 问题 2: 无法操作 frontend-* 容器

**原因**：容器名称不符合规范

**解决**：
```bash
# 确保容器名称使用 frontend-* 前缀
sudo docker-frontend run --name frontend-app ...
```

### 问题 3: 可以操作后端容器

**原因**：包装脚本未正确限制

**解决**：
```bash
# 重新运行配置脚本
bash scripts/configure_frontend_docker_restricted.sh

# 验证配置
bash scripts/test_frontend_docker_restricted.sh
```

## 📚 相关文档

- [frontend-user Docker 受限权限说明](./frontend-user-Docker受限权限说明.md)
- [frontend-user 权限配置说明](./frontend-user权限配置说明.md)

## 📅 配置信息

- **安装时间**：2025-01-XX
- **Node1**: ✅ 已安装并配置权限
- **Node2**: ✅ 已安装并配置权限
- **脚本版本**：v1.0
- **最后更新**：2025-01-XX


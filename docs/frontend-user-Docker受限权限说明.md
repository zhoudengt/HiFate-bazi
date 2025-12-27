# frontend-user Docker 受限权限说明

## ⚠️ 重要提示

**本方案已废弃**，已升级为 **Docker Rootless 方案**。

**新方案优势**：
- ✅ 完全隔离（无法看到后端容器）
- ✅ 无需 sudo/root 权限
- ✅ 更安全可靠

**请使用新方案**：查看 [frontend-user Docker Rootless 使用指南](./frontend-user-Docker-Rootless使用指南.md)

---

## 📋 权限状态（旧方案，已废弃）

**已配置**：frontend-user 在双机上已配置受限 Docker 权限

- ✅ Node1 (8.210.52.217): 受限权限已配置（已升级为 Rootless）
- ✅ Node2 (47.243.160.43): 受限权限已配置（已升级为 Rootless）

## 🔒 权限限制

### 当前权限范围

| 功能 | 权限状态 | 说明 |
|------|---------|------|
| **查看所有容器** | ✅ 可以 | 使用 `sudo docker-frontend ps` |
| **操作 frontend-* 容器** | ✅ 可以 | stop/start/rm/exec 等 |
| **操作 hifate-* 容器** | ❌ **禁止** | 后端容器完全禁止操作 |
| **直接使用 docker 命令** | ❌ **禁止** | 必须使用 `sudo docker-frontend` |
| **创建非 frontend-* 容器** | ❌ **禁止** | 容器名必须使用 frontend-* 前缀 |

### 安全机制

1. **从 docker 组中移除**：frontend-user 不在 docker 组中，无法直接访问 Docker socket
2. **包装脚本限制**：只能通过 `/usr/local/bin/docker-frontend` 包装脚本操作
3. **命名规范检查**：包装脚本自动检查容器名称，只允许操作 `frontend-*` 前缀的容器
4. **sudo 权限控制**：只能无密码执行包装脚本，不能执行其他命令

## 🛠️ 使用方式

### 基本命令

```bash
# 切换到 frontend-user
su - frontend-user

# 查看所有容器（只读，可以查看）
sudo docker-frontend ps

# 查看镜像
sudo docker-frontend images

# 创建容器（必须使用 frontend-* 前缀）
sudo docker-frontend run -d \
  --name frontend-app \
  --network frontend-network \
  -p 8080:80 \
  nginx:alpine

# 停止自己的容器
sudo docker-frontend stop frontend-app

# 启动自己的容器
sudo docker-frontend start frontend-app

# 删除自己的容器
sudo docker-frontend rm frontend-app

# 查看容器日志
sudo docker-frontend logs frontend-app

# 进入容器
sudo docker-frontend exec -it frontend-app sh
```

### 禁止的操作

```bash
# ❌ 禁止：直接使用 docker 命令
docker ps  # 会报错：permission denied

# ❌ 禁止：操作后端容器
sudo docker-frontend stop hifate-web
# 会报错：禁止操作非 frontend-* 容器: hifate-web

# ❌ 禁止：创建非 frontend-* 容器
sudo docker-frontend run --name test-app ...
# 会报错：容器名称必须使用 frontend-* 前缀
```

## 🔍 权限验证

### 验证配置

```bash
# 运行验证脚本
bash scripts/verify_frontend_docker_restricted.sh

# 或运行快速测试
bash scripts/test_frontend_docker_restricted.sh
```

### 手动验证

```bash
# 1. 检查是否在 docker 组中（应该不在）
groups frontend-user
# 应该显示：frontend-user : frontend-group（没有 docker）

# 2. 测试直接使用 docker（应该失败）
su - frontend-user
docker ps
# 应该显示：permission denied

# 3. 测试使用包装脚本（应该成功）
sudo docker-frontend ps
# 应该显示容器列表

# 4. 测试操作后端容器（应该失败）
sudo docker-frontend stop hifate-web
# 应该显示：错误：禁止操作非 frontend-* 容器
```

## 📝 配置详情

### 包装脚本位置

```
/usr/local/bin/docker-frontend
```

### sudo 配置文件

```
/etc/sudoers.d/frontend-docker
```

内容：
```
frontend-user ALL=(ALL) NOPASSWD: /usr/local/bin/docker-frontend
Defaults:frontend-user !requiretty
```

### 用户组

```
frontend-user: frontend-group
（不在 docker 组中）
```

## 🔧 管理脚本

### 配置受限权限

```bash
bash scripts/configure_frontend_docker_restricted.sh
```

功能：
- 从 docker 组中移除 frontend-user
- 创建包装脚本 `/usr/local/bin/docker-frontend`
- 配置 sudo 规则
- 在双机上执行

### 验证受限权限

```bash
bash scripts/verify_frontend_docker_restricted.sh
```

功能：
- 验证 frontend-user 不在 docker 组中
- 验证无法直接使用 docker 命令
- 验证可以操作 frontend-* 容器
- 验证禁止操作 hifate-* 容器
- 验证后端服务不受影响

### 快速测试

```bash
bash scripts/test_frontend_docker_restricted.sh
```

功能：
- 快速测试所有关键功能
- 验证权限限制是否生效

## ⚠️ 重要提醒

### 使用规范

1. **必须使用包装脚本**：
   - ✅ 正确：`sudo docker-frontend <command>`
   - ❌ 错误：`docker <command>`（会失败）

2. **容器命名规范**：
   - ✅ 正确：`--name frontend-app`
   - ❌ 错误：`--name app`（会失败）
   - ❌ 错误：`--name hifate-app`（会失败）

3. **禁止操作后端容器**：
   - ❌ 禁止：`sudo docker-frontend stop hifate-web`
   - ❌ 禁止：`sudo docker-frontend rm hifate-web`
   - ❌ 禁止：`sudo docker-frontend exec hifate-web ...`

### 重新登录

**重要**：配置后，frontend-user 需要重新登录才能生效。

```bash
# 如果 frontend-user 已登录，需要退出并重新登录
exit
su - frontend-user

# 然后才能使用 sudo docker-frontend
```

### 后端服务保护

- ✅ 后端容器（hifate-*）完全禁止操作
- ✅ 后端服务正常运行，不受影响
- ✅ 配置过程不会停止或重启后端服务

## 📊 权限对比

| 功能 | 之前（完整权限） | 现在（受限权限） |
|------|----------------|----------------|
| 查看所有容器 | ✅ `docker ps` | ✅ `sudo docker-frontend ps` |
| 操作前端容器 | ✅ `docker stop frontend-app` | ✅ `sudo docker-frontend stop frontend-app` |
| 操作后端容器 | ⚠️ `docker stop hifate-web`（可以但禁止） | ❌ `sudo docker-frontend stop hifate-web`（完全禁止） |
| 直接使用 docker | ✅ 可以 | ❌ 禁止（必须使用包装脚本） |

## 🔄 恢复完整权限（如果需要）

如果需要恢复 frontend-user 的完整 Docker 权限：

```bash
# 运行授权脚本
bash scripts/grant_docker_access_to_frontend_user.sh

# 删除包装脚本和 sudo 规则
# （在服务器上执行）
rm -f /usr/local/bin/docker-frontend
rm -f /etc/sudoers.d/frontend-docker
```

## 📅 配置信息

- **配置时间**：2025-01-XX
- **Node1**: ✅ 已配置
- **Node2**: ✅ 已配置
- **包装脚本版本**：v1.0
- **最后更新**：2025-01-XX

## 🎯 总结

通过受限权限配置，实现了：

1. ✅ **完全禁止操作后端容器**：frontend-user 无法停止、删除、修改任何 `hifate-*` 容器
2. ✅ **只能管理自己的容器**：只能操作 `frontend-*` 前缀的容器
3. ✅ **不影响现有功能**：后端服务正常运行，不受任何影响
4. ✅ **安全隔离**：通过包装脚本和 sudo 规则实现权限隔离

**核心安全机制**：
- 从 docker 组中移除（无直接权限）
- 包装脚本检查容器名称（只允许 frontend-*）
- sudo 规则限制（只能执行包装脚本）


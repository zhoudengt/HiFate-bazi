# 修复前端 Docker 容器内存限制问题

## 问题描述

前端容器（frontend-gateway）在 rootless Docker 模式下，使用 `mem_limit` 和 `mem_reservation` 配置内存限制不生效，导致容器被 OOM Killer 杀死（退出代码 137）。

## 解决方案

将旧的内存限制配置方式（`mem_limit`/`mem_reservation`）改为新方式（`deploy.resources.limits.memory`/`deploy.resources.reservations.memory`），确保在 rootless Docker 模式下生效。

## 修复方法

### 方法 1：远程修复（推荐）

在本地执行脚本，自动修复双机配置：

```bash
# 设置 SSH 密码（如果需要）
export SSH_PASSWORD="${SSH_PASSWORD}"

# 执行修复脚本
bash scripts/fix_frontend_docker_memory_limit.sh
```

**功能**：
- 自动备份配置文件
- 修改内存限制配置
- 验证配置正确性
- 双机同时修复

### 方法 2：本地修复（在服务器上执行）

在服务器上切换到 frontend-user，直接执行修复脚本：

```bash
# 1. 切换到 frontend-user
su - frontend-user

# 2. 进入前端目录
cd /opt/hifate-frontend

# 3. 下载修复脚本（从项目仓库）
# 或直接复制脚本内容到服务器

# 4. 执行修复脚本
bash fix_frontend_memory_limit_local.sh
```

## 配置变更说明

### 旧配置（不生效）

```yaml
services:
  frontend-mysql:
    mem_limit: 512m
    mem_reservation: 256m
```

### 新配置（生效）

```yaml
services:
  frontend-mysql:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## 内存分配建议

确保所有前端容器总内存限制 ≤ 4G：

| 服务 | 内存限制 | 内存预留 | 说明 |
|------|---------|---------|------|
| frontend-mysql | 512M | 256M | MySQL 数据库 |
| frontend-gateway | 2G | 1G | 前端网关服务 |
| 其他服务 | 根据需求 | 根据需求 | 其他前端服务 |
| **总计** | **≤ 4G** | **≤ 2G** | **总内存控制** |

## 修复后操作

### 1. 停止现有容器

```bash
cd /opt/hifate-frontend
docker-compose down
```

### 2. 启动容器（使用新配置）

```bash
docker-compose up -d
```

### 3. 验证内存限制

```bash
# 查看容器内存使用情况
docker stats --no-stream

# 检查容器状态
docker-compose ps
```

### 4. 验证容器正常运行

```bash
# 检查容器日志
docker-compose logs frontend-gateway

# 检查容器是否正常运行（不再出现 137 错误）
docker-compose ps
```

## 验证清单

- [ ] 配置已从 `mem_limit` 改为 `deploy.resources.limits.memory`
- [ ] 所有容器内存限制总和 ≤ 4G
- [ ] 配置验证通过（`docker-compose config`）
- [ ] 容器可以正常启动（不再出现 137 错误）
- [ ] 内存限制生效（`docker stats` 显示限制值）
- [ ] 容器由 frontend-user 启动

## 故障排查

### 问题 1：配置验证失败

**症状**：`docker-compose config` 报错

**解决**：
1. 检查 YAML 语法是否正确
2. 检查缩进是否正确（使用空格，不是 Tab）
3. 恢复备份文件：`cp docker-compose.yml.backup.* docker-compose.yml`

### 问题 2：容器仍然被 OOM 杀死

**症状**：容器仍然退出代码 137

**可能原因**：
1. 内存限制仍然不生效（rootless Docker 限制）
2. 总内存分配超过系统可用内存
3. 其他进程占用内存

**解决**：
1. 检查系统可用内存：`free -h`
2. 检查容器内存限制：`docker stats --no-stream`
3. 减少容器内存限制
4. 考虑使用 `docker run --memory` 直接限制

### 问题 3：deploy.resources 仍然不生效

**症状**：使用 `deploy.resources` 后内存限制仍然不生效

**可能原因**：
- rootless Docker 对 `deploy.resources` 的支持有限
- 需要额外的 cgroup v2 配置

**解决**：
1. 检查 Docker 版本：`docker --version`
2. 检查 rootless 模式：`docker info | grep rootless`
3. 考虑使用 `docker run --memory` 方式启动容器
4. 配置 systemd user slice 限制

## 相关文件

- `scripts/fix_frontend_docker_memory_limit.sh` - 远程修复脚本
- `scripts/fix_frontend_memory_limit_local.sh` - 本地修复脚本
- `/opt/hifate-frontend/docker-compose.yml` - 前端 Docker Compose 配置

## 注意事项

- **不要修改权限**：保持 frontend-user 的权限不变
- **必须由 frontend-user 启动**：确保容器由 frontend-user 启动
- **总内存控制**：所有容器内存限制总和必须 ≤ 4G
- **备份文件**：修复前自动备份，可在需要时恢复


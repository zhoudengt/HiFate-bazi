# Node1 本地代码修改清理方案

## 📋 问题描述

Node1 的 `deploy/nginx/conf.d/hifate.conf` 文件有本地修改（未提交到 Git）：
- **修改内容**：IP 占位符 `NODE1_IP` 和 `NODE2_IP` 已被替换为实际 IP 地址
- **GitHub 状态**：文件仍使用占位符（这是正确的模板）
- **当前状态**：Nginx 容器正常工作，使用的是替换后的配置

## ✅ 为什么可以安全清理

### 1. Nginx 容器配置独立于 Git 仓库

**关键点**：
- Nginx 容器通过 **文件系统挂载** 使用配置文件
- 挂载路径：`/opt/HiFate-bazi/deploy/nginx/conf.d/hifate.conf` → `/etc/nginx/conf.d/hifate.conf`
- **容器内的配置是文件系统的实际内容，不是 Git 仓库的内容**

### 2. 清理不会影响运行中的容器

**原因**：
- Docker 容器在启动时读取配置文件
- 配置文件通过 **volume 挂载** 映射到容器内
- 恢复 Git 文件只影响文件系统，**不会自动重新加载容器内的配置**
- 容器会继续使用启动时读取的配置

### 3. 部署脚本会自动重新替换

**保证**：
- 增量部署脚本会在每次部署时自动替换 IP 占位符
- 脚本位置：`deploy/scripts/incremental_deploy_production.sh` (第 283-290 行)
- 即使恢复文件，下次部署时会自动重新替换

## 🔧 安全清理步骤

### 方案 1：使用 git stash（推荐，最安全）

```bash
# 1. SSH 到 Node1
ssh root@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 使用 git stash 保存本地修改（不会丢失）
git stash save "Nginx IP 占位符替换（由部署脚本自动完成）"

# 4. 验证文件已恢复
git status
# 应该显示：working tree clean

# 5. 验证 Nginx 容器仍然正常工作
docker exec hifate-nginx nginx -t
# 应该显示：configuration file test is successful

# 6. 测试 Nginx 服务
curl -I http://localhost/health
# 应该返回 200 OK
```

**优点**：
- ✅ 完全安全，不会影响运行中的容器
- ✅ 修改被保存到 stash，可以随时恢复
- ✅ 符合 Git 工作流

### 方案 2：直接恢复文件（简单直接）

```bash
# 1. SSH 到 Node1
ssh root@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 直接恢复文件（从 Git 仓库）
git checkout -- deploy/nginx/conf.d/hifate.conf

# 4. 验证文件已恢复
git status
# 应该显示：working tree clean

# 5. 验证 Nginx 容器仍然正常工作
docker exec hifate-nginx nginx -t
# 应该显示：configuration file test is successful

# 6. 测试 Nginx 服务
curl -I http://localhost/health
# 应该返回 200 OK
```

**优点**：
- ✅ 简单直接
- ✅ 不会影响运行中的容器
- ⚠️ 修改会丢失（但部署脚本会自动重新替换）

## ⚠️ 重要注意事项

### 1. 不要重启 Nginx 容器

**原因**：
- 如果恢复文件后立即重启 Nginx 容器，容器会读取恢复后的文件（包含占位符）
- 这会导致 Nginx 配置错误，服务不可用

**正确做法**：
- 先恢复文件
- **不要重启 Nginx 容器**
- 等待下次增量部署时，脚本会自动替换占位符并重启容器

### 2. 如果必须重启 Nginx

**场景**：如果确实需要重启 Nginx 容器（例如配置其他内容）

**正确步骤**：
```bash
# 1. 先恢复文件
git checkout -- deploy/nginx/conf.d/hifate.conf

# 2. 手动替换 IP 占位符（临时）
sed -i "s/NODE1_IP/172.18.121.222/g" deploy/nginx/conf.d/hifate.conf
sed -i "s/NODE2_IP/172.18.121.223/g" deploy/nginx/conf.d/hifate.conf

# 3. 验证配置
docker exec hifate-nginx nginx -t

# 4. 重启 Nginx 容器
docker restart hifate-nginx

# 5. 验证服务正常
curl -I http://localhost/health
```

### 3. 最佳实践

**推荐流程**：
1. 使用 `git stash` 保存本地修改（方案 1）
2. **不要立即重启 Nginx 容器**
3. 等待下次增量部署时，脚本会自动处理

## 📊 验证清单

清理后必须验证：

- [ ] Git 状态显示 `working tree clean`
- [ ] Nginx 容器正常运行（`docker ps | grep hifate-nginx`）
- [ ] Nginx 配置测试通过（`docker exec hifate-nginx nginx -t`）
- [ ] Nginx 服务响应正常（`curl -I http://localhost/health`）
- [ ] 负载均衡正常工作（访问前端页面）

## 🔄 后续处理

### 下次增量部署时

增量部署脚本会自动：
1. 拉取最新代码（包含占位符的模板）
2. 自动替换 IP 占位符（使用 `.env` 文件中的值）
3. 重启 Nginx 容器（应用新配置）

**无需手动干预**。

## 📝 总结

**核心原则**：
- ✅ Nginx 容器配置独立于 Git 仓库
- ✅ 恢复 Git 文件不会影响运行中的容器
- ✅ 部署脚本会自动处理 IP 占位符替换
- ⚠️ 恢复文件后不要立即重启 Nginx 容器

**推荐方案**：使用 `git stash` 保存修改，等待下次增量部署自动处理。

---

**生成时间**: 2025-01-17  
**适用场景**: Node1 本地代码修改清理，确保服务不中断


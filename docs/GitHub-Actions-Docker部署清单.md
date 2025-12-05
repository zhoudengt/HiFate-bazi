# GitHub Actions + Docker 部署完整清单

> 本文档提供基于 GitHub Actions 和 Docker 的完整部署配置清单

## 📋 部署前检查清单

### ✅ 服务器端准备

#### 1. 服务器初始化
- [ ] 运行服务器初始化脚本
  ```bash
  ssh root@123.57.216.15
  cd /opt/HiFate-bazi
  bash scripts/setup_server.sh
  ```

#### 2. 环境变量配置
- [ ] 创建 `.env` 文件
  ```bash
  cd /opt/HiFate-bazi
  cp env.template .env
  vim .env  # 修改以下配置：
  ```
- [ ] 配置项检查：
  - [ ] `MYSQL_ROOT_PASSWORD` - 强密码
  - [ ] `MYSQL_DATABASE` - 数据库名（默认：`hifate_bazi`）
  - [ ] `REDIS_PASSWORD` - Redis 密码
  - [ ] `SECRET_KEY` - 应用密钥
  - [ ] `COZE_ACCESS_TOKEN` - Coze API Token（如需要）
  - [ ] `COZE_BOT_ID` - Coze Bot ID（如需要）
- [ ] 设置文件权限
  ```bash
  chmod 600 .env
  ```

#### 3. SSH 密钥配置（用于 GitHub Actions）
- [ ] 生成 SSH 密钥对
  ```bash
  ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
  # 或使用 RSA：
  # ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions
  ```
- [ ] 查看私钥（复制完整内容，包括 BEGIN 和 END 行）
  ```bash
  cat ~/.ssh/github_actions
  ```
- [ ] 将公钥添加到 authorized_keys
  ```bash
  cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
  ```

#### 4. 基础镜像构建（可选，但推荐）
- [ ] 首次构建基础镜像
  ```bash
  cd /opt/HiFate-bazi
  chmod +x scripts/docker/build_base.sh
  ./scripts/docker/build_base.sh
  ```
  > 注意：首次构建需要 5-10 分钟，但后续部署只需 10-20 秒

#### 5. 测试本地部署
- [ ] 测试 Docker Compose 启动
  ```bash
  cd /opt/HiFate-bazi
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
  ```
- [ ] 验证服务健康
  ```bash
  sleep 30
  curl http://localhost:8001/health
  ```
- [ ] 查看服务日志
  ```bash
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
  ```

---

### ✅ GitHub 配置

#### 1. 访问 GitHub Secrets 配置页面
- [ ] 打开仓库：https://github.com/your-username/HiFate-bazi
- [ ] 进入：Settings → Secrets and variables → Actions
- [ ] 点击 "New repository secret"

#### 2. 配置开发环境 Secrets
- [ ] `DEV_SSH_PRIVATE_KEY`
  - 值：开发服务器 SSH 私钥（从 `~/.ssh/github_actions` 复制）
  - 格式：包括 `-----BEGIN ... KEY-----` 和 `-----END ... KEY-----`
- [ ] `DEV_SERVER_HOST`
  - 值：开发服务器 IP 或域名（如：`dev.hifate.com` 或 `192.168.1.100`）
- [ ] `DEV_SERVER_USER`
  - 值：SSH 用户名（通常是 `root`）

#### 3. 配置生产环境 Secrets
- [ ] `PROD_SSH_PRIVATE_KEY`
  - 值：生产服务器 SSH 私钥（从 `~/.ssh/github_actions` 复制）
  - 格式：包括 `-----BEGIN ... KEY-----` 和 `-----END ... KEY-----`
- [ ] `PROD_SERVER_HOST`
  - 值：生产服务器 IP 或域名（如：`123.57.216.15` 或 `hifate.com`）
- [ ] `PROD_SERVER_USER`
  - 值：SSH 用户名（通常是 `root`）

---

### ✅ Workflow 文件检查

#### 1. 检查 Workflow 文件
- [ ] `.github/workflows/ci.yml` - CI/CD 流水线
- [ ] `.github/workflows/deploy-develop.yml` - 开发环境部署
- [ ] `.github/workflows/deploy-production.yml` - 生产环境部署

#### 2. 验证 Workflow 配置
- [ ] 触发条件正确（`push` 到对应分支）
- [ ] 支持手动触发（`workflow_dispatch`）
- [ ] 使用基础镜像优化（已优化）
- [ ] 数据库备份使用环境变量（已修正）
- [ ] 健康检查有重试机制（已添加）

---

## 🚀 部署流程

### 开发环境部署

1. **推送代码到 develop 分支**
   ```bash
   git checkout develop
   git add .
   git commit -m "[测试] 测试开发环境部署"
   git push origin develop
   ```

2. **查看 GitHub Actions**
   - 访问：https://github.com/your-username/HiFate-bazi/actions
   - 查看 "🚀 Deploy to Development" workflow
   - 等待部署完成（约 2-5 分钟）

3. **验证部署**
   ```bash
   ssh root@<DEV_SERVER_HOST>
   curl http://localhost:8001/health
   ```

### 生产环境部署

1. **合并到 master 分支**
   ```bash
   git checkout master
   git merge develop
   git push origin master
   ```

2. **查看 GitHub Actions**
   - 访问：https://github.com/your-username/HiFate-bazi/actions
   - 查看 "🚀 Deploy to Production" workflow
   - 等待部署完成（约 3-8 分钟，包含数据库备份）

3. **验证部署**
   ```bash
   ssh root@<PROD_SERVER_HOST>
   curl http://localhost:8001/health
   ```

---

## 🔧 故障排查

### 问题 1：SSH 连接失败

**症状**：GitHub Actions 显示 "Permission denied (publickey)"

**解决方案**：
```bash
# 在服务器上检查 SSH 密钥
cat ~/.ssh/authorized_keys | grep github-actions

# 检查权限
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh

# 测试 SSH 连接
ssh -i ~/.ssh/github_actions root@localhost
```

### 问题 2：Docker 构建失败

**症状**：GitHub Actions 显示 "docker build failed"

**解决方案**：
```bash
# 在服务器上手动测试构建
cd /opt/HiFate-bazi
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# 查看详细错误
docker-compose logs
```

### 问题 3：健康检查失败

**症状**：部署后健康检查返回错误

**解决方案**：
```bash
# 检查服务状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs web

# 手动测试健康检查
curl -v http://localhost:8001/health
```

### 问题 4：数据库备份失败

**症状**：备份步骤失败

**解决方案**：
```bash
# 检查数据库容器
docker-compose ps mysql

# 手动测试备份
docker-compose exec mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} ${MYSQL_DATABASE} > /tmp/test_backup.sql

# 检查环境变量
docker-compose exec mysql env | grep MYSQL
```

---

## 📊 部署监控

### GitHub Actions 监控

- **访问地址**：https://github.com/your-username/HiFate-bazi/actions
- **查看日志**：点击具体的 workflow run，查看详细日志
- **重新运行**：失败的 workflow 可以点击 "Re-run jobs" 重新运行

### 服务器监控

```bash
# 查看容器状态
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看资源使用
docker stats

# 查看服务日志
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web

# 查看系统资源
top
htop
```

---

## 🔐 安全建议

1. **SSH 密钥安全**
   - 使用强密码保护私钥
   - 定期轮换 SSH 密钥
   - 限制 SSH 访问 IP

2. **环境变量安全**
   - `.env` 文件权限设置为 600
   - 不要将 `.env` 提交到 Git
   - 使用强密码和密钥

3. **数据库安全**
   - 使用强密码
   - 限制数据库访问 IP
   - 定期备份数据库

4. **Docker 安全**
   - 定期更新 Docker 镜像
   - 使用非 root 用户运行容器（如可能）
   - 限制容器资源使用

---

## 📝 更新日志

### 2025-12-03
- ✅ 优化 Workflow 使用基础镜像（部署速度提升 6-12 倍）
- ✅ 修正数据库备份使用环境变量
- ✅ 添加健康检查重试机制
- ✅ 改进错误处理和日志输出
- ✅ 创建服务器初始化脚本
- ✅ 创建部署清单文档

---

## 📚 相关文档

- [Docker 部署指南](../docs/Docker部署指南.md)
- [部署方案5-Docker自动化部署](../docs/部署方案5-Docker自动化部署.md)
- [Docker基础镜像优化](../docs/Docker基础镜像优化.md)


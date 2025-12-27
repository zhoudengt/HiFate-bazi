# 双机 buildx 版本修复指南

## 快速修复（一键修复双机）

### 方法 1：使用双机修复脚本（推荐）

在本地项目目录执行：

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 设置 SSH 密码（如果需要）
export SSH_PASSWORD="Yuanqizhan@163"

# 执行双机修复
bash scripts/fix_buildx_dual_nodes.sh
```

脚本会自动：
1. 检查 Node1 和 Node2 的 SSH 连接
2. 检查每台机器的 buildx 版本
3. 如果版本 < 0.17，自动执行修复
4. 验证修复结果
5. 显示修复总结

### 方法 2：分别在每台机器上执行

#### Node1 修复

```bash
# SSH 连接到 Node1
ssh root@8.210.52.217

# 进入项目目录
cd /opt/HiFate-bazi

# 拉取最新代码（如果脚本已提交）
git pull origin master

# 执行修复脚本
bash scripts/fix_buildx_version.sh

# 验证
docker buildx version
```

#### Node2 修复

```bash
# SSH 连接到 Node2
ssh root@47.243.160.43

# 进入项目目录
cd /opt/HiFate-bazi

# 拉取最新代码（如果脚本已提交）
git pull origin master

# 执行修复脚本
bash scripts/fix_buildx_version.sh

# 验证
docker buildx version
```

## 验证双机修复

### 检查 Node1

```bash
ssh root@8.210.52.217 "docker buildx version"
# 应该显示 v0.17.0 或更高
```

### 检查 Node2

```bash
ssh root@47.243.160.43 "docker buildx version"
# 应该显示 v0.17.0 或更高
```

### 测试 frontend-gateway（如果服务存在）

```bash
# Node1
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && docker-compose up -d frontend-gateway"

# Node2
ssh root@47.243.160.43 "cd /opt/HiFate-bazi && docker-compose up -d frontend-gateway"
```

## 故障排查

### 问题 1：SSH 连接失败

**原因**：SSH 密码错误或网络问题

**解决**：
```bash
# 检查 SSH 连接
ssh root@8.210.52.217 "echo 'test'"

# 如果使用密钥，确保密钥已配置
ssh -i ~/.ssh/id_rsa root@8.210.52.217 "echo 'test'"
```

### 问题 2：修复脚本不存在

**原因**：代码未同步到服务器

**解决**：
```bash
# 在服务器上拉取最新代码
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git pull origin master"
```

### 问题 3：需要 sudo 权限

**原因**：frontend-user 可能没有 sudo 权限

**解决**：
1. 使用 root 用户执行修复
2. 或联系管理员升级 buildx

## 相关文件

- `scripts/fix_buildx_dual_nodes.sh` - 双机修复脚本
- `scripts/fix_buildx_version.sh` - 单机修复脚本
- `docs/fix_buildx_version_guide.md` - 详细修复指南

## 生产环境信息

- **Node1**: 8.210.52.217 (公网), 172.18.121.222 (内网)
- **Node2**: 47.243.160.43 (公网), 172.18.121.223 (内网)
- **SSH 密码**: Yuanqizhan@163（从环境变量读取）


# HiFate-bazi SSH 连接配置指南

> **目的**：配置SSH密钥认证，实现快速自动部署  
> **最后更新**：2026-01-09

---

## 📋 配置概述

为了提升自动部署的速度和安全性，我们配置了SSH密钥认证，避免每次部署时输入密码。

### 配置内容

1. **SSH密钥对**：`~/.ssh/id_rsa_hifate`（专用密钥）
2. **SSH Config别名**：
   - `hifate-node1` → 8.210.52.217
   - `hifate-node2` → 47.243.160.43
3. **自动降级**：密钥认证失败时自动使用密码认证

---

## 🔧 配置步骤

### 1. 生成SSH密钥（如果尚未生成）

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_hifate -N "" -C "hifate-deploy"
```

### 2. 配置SSH Config

编辑 `~/.ssh/config`，添加以下内容：

```
# HiFate-bazi 生产环境
Host hifate-node1
    HostName 8.210.52.217
    User root
    IdentityFile ~/.ssh/id_rsa_hifate
    StrictHostKeyChecking no
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host hifate-node2
    HostName 47.243.160.43
    User root
    IdentityFile ~/.ssh/id_rsa_hifate
    StrictHostKeyChecking no
    ConnectTimeout 10
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

设置权限：
```bash
chmod 600 ~/.ssh/config
```

### 3. 将公钥复制到服务器

**Node1**：
```bash
sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@8.210.52.217 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
   echo '$(cat ~/.ssh/id_rsa_hifate.pub)' >> ~/.ssh/authorized_keys && \
   chmod 600 ~/.ssh/authorized_keys"
```

**Node2**：
```bash
sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@47.243.160.43 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
   echo '$(cat ~/.ssh/id_rsa_hifate.pub)' >> ~/.ssh/authorized_keys && \
   chmod 600 ~/.ssh/authorized_keys"
```

### 4. 测试连接

```bash
# 测试 Node1
ssh hifate-node1 "echo 'Node1连接成功'"

# 测试 Node2
ssh hifate-node2 "echo 'Node2连接成功'"
```

或使用测试脚本：
```bash
bash scripts/test_ssh_connection.sh
```

---

## 🚀 部署脚本优化

部署脚本 `deploy/scripts/incremental_deploy_production.sh` 已优化：

1. **优先使用SSH密钥**：自动检测并使用SSH config别名
2. **自动降级**：密钥认证失败时自动使用密码认证
3. **快速连接**：减少连接超时时间，提升部署速度

### 连接优先级

1. SSH Config别名（`hifate-node1`, `hifate-node2`）
2. 直接使用密钥文件（`~/.ssh/id_rsa_hifate`）
3. 密码认证（使用 `sshpass`）

---

## ✅ 验证配置

### 快速测试

```bash
# 测试连接速度
time ssh hifate-node1 "echo 'test'"
time ssh hifate-node2 "echo 'test'"
```

### 完整测试

```bash
bash scripts/test_ssh_connection.sh
```

---

## 🔍 故障排查

### 问题1：连接超时

**现象**：`Connection timed out`

**解决方案**：
1. 检查网络连通性：`ping 8.210.52.217`
2. 检查SSH端口：`nc -zv 8.210.52.217 22`
3. 增加超时时间：在SSH config中设置 `ConnectTimeout 30`

### 问题2：权限被拒绝

**现象**：`Permission denied (publickey)`

**解决方案**：
1. 检查密钥权限：`chmod 600 ~/.ssh/id_rsa_hifate`
2. 检查服务器authorized_keys权限：`chmod 600 ~/.ssh/authorized_keys`
3. 重新复制公钥到服务器

### 问题3：Node2连接慢

**现象**：Node2连接需要50+秒

**可能原因**：
- 网络延迟
- DNS解析慢
- 服务器负载高

**解决方案**：
1. 使用IP地址直接连接（已在SSH config中配置）
2. 检查服务器负载：`ssh hifate-node2 "uptime"`
3. 考虑使用内网IP（如果可能）

---

## 📝 注意事项

1. **密钥安全**：不要将私钥提交到Git仓库
2. **权限设置**：确保SSH密钥和config文件权限正确
3. **备份密钥**：建议备份SSH密钥到安全位置
4. **定期更新**：建议定期更换SSH密钥（如每6个月）

---

## 🔄 更新密钥

如果需要更新SSH密钥：

1. 生成新密钥
2. 将新公钥添加到服务器
3. 更新SSH config中的密钥路径
4. 测试连接
5. 删除旧密钥（可选）

---

**配置完成日期**：2026-01-09  
**配置状态**：✅ 已配置并测试通过

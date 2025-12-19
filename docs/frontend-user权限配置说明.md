# frontend-user 权限配置说明

## 📋 配置目标

- ✅ `frontend-user` 只能访问 `/opt/hifate-frontend` 目录（读写执行权限）
- ✅ `frontend-user` 无法访问 `/opt/HiFate-bazi` 目录
- ✅ `frontend-user` 无法看到 `/opt` 下的其他目录

## 🔒 权限配置详情

### 目录权限设置

| 目录 | 权限 | 说明 |
|------|------|------|
| `/opt/hifate-frontend` | `775` (rwxrwxr-x) + ACL | frontend-user 拥有完整读写执行权限 |
| `/opt` | `751` (drwxr-x--x) | 允许执行（进入）但不允许列出内容 |
| `/opt/HiFate-bazi` | `750` (drwxr-x---) | 完全禁止其他用户访问 |
| `/opt` 下其他目录 | `750` | 禁止其他用户访问 |

### 权限说明

1. **`/opt/hifate-frontend: 775`**
   - 所有者：root (rwx)
   - 组：root (rwx)
   - 其他用户：r-x（只读执行）
   - 通过 ACL 给 `frontend-user` 添加完整权限 (rwx)

2. **`/opt: 751`**
   - 所有者：root (rwx)
   - 组：root (r-x)
   - 其他用户：--x（只能执行，不能列出）
   - 效果：`frontend-user` 知道路径可以进入（如 `cd /opt/hifate-frontend`），但 `ls /opt` 会显示 Permission denied

3. **`/opt/HiFate-bazi: 750`**
   - 所有者：root (rwx)
   - 组：root (r-x)
   - 其他用户：---（完全无权限）
   - 效果：`frontend-user` 无法访问，无法列出，无法读取

## ✅ 验证结果

所有测试均已通过：

- ✅ `frontend-user` 可以访问 `/opt/hifate-frontend`
- ✅ `frontend-user` 可以在 `/opt/hifate-frontend` 创建和删除文件
- ✅ `frontend-user` 无法访问 `/opt/HiFate-bazi`（Permission denied）
- ✅ `frontend-user` 无法列出 `/opt` 下的其他目录（Permission denied）
- ✅ 所有目录权限设置正确（751/775/750）

## 🛠️ 管理脚本

### 配置权限脚本

```bash
bash scripts/configure_frontend_user_permissions.sh
```

功能：
- 创建/检查 `frontend-user` 用户
- 创建 `/opt/hifate-frontend` 目录
- 设置目录权限
- 使用 ACL 给 `frontend-user` 完整权限
- 禁止访问其他目录

### 验证权限脚本

```bash
bash scripts/verify_frontend_user_permissions.sh
```

功能：
- 验证 `frontend-user` 可以访问 `/opt/hifate-frontend`
- 验证 `frontend-user` 无法访问 `/opt/HiFate-bazi`
- 验证 `frontend-user` 无法列出 `/opt` 下的其他目录
- 检查目录权限设置

## 📝 手动验证命令

在服务器上可以手动验证：

```bash
# 切换到 frontend-user
su - frontend-user

# 测试 1: 可以访问 /opt/hifate-frontend
cd /opt/hifate-frontend
ls -la
touch test.txt
rm test.txt

# 测试 2: 无法访问 /opt/HiFate-bazi
ls /opt/HiFate-bazi
# 应该显示: Permission denied

# 测试 3: 无法列出 /opt 下的其他目录
ls /opt
# 应该显示: Permission denied

# 测试 4: 但是可以进入已知的路径
cd /opt/hifate-frontend  # 可以
cd /opt/HiFate-bazi      # 应该显示: Permission denied
```

## 🔧 维护说明

### 如果需要在 /opt/hifate-frontend 添加新文件

`frontend-user` 拥有完整权限，可以直接操作：

```bash
# 作为 frontend-user
cd /opt/hifate-frontend
# 可以创建、修改、删除文件
```

### 如果需要修改权限

```bash
# 作为 root
# 修改 /opt/hifate-frontend 权限
chmod 775 /opt/hifate-frontend

# 给 frontend-user 添加 ACL 权限
setfacl -R -m u:frontend-user:rwx /opt/hifate-frontend
setfacl -R -d -m u:frontend-user:rwx /opt/hifate-frontend
```

### 如果需要恢复权限配置

重新运行配置脚本即可：

```bash
bash scripts/configure_frontend_user_permissions.sh
```

## ⚠️ 注意事项

1. **不要降低 `/opt/HiFate-bazi` 的权限**
   - 保持 750，确保 `frontend-user` 无法访问

2. **不要改变 `/opt` 的权限**
   - 保持 751，确保 `frontend-user` 无法列出其他目录

3. **ACL 权限**
   - 如果系统支持 ACL，使用 ACL 更灵活
   - 如果系统不支持 ACL，脚本会自动使用组权限方案

4. **文件权限**
   - `/opt/HiFate-bazi` 下的文件权限保持 640（不影响服务运行）
   - 只修改目录权限为 750

## 📊 配置状态

- ✅ Node1 (8.210.52.217): 已配置
- ✅ Node2 (47.243.160.43): 已配置

最后更新：2025-01-XX


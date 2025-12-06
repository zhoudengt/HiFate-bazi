# 阿里云 ACR 个人版配置说明

## 测试结果

✅ **格式验证通过**：所有配置项的格式都正确

❌ **Docker 登录失败**：`unauthorized: authentication required`

## 问题分析

阿里云 ACR 个人版支持两种认证方式：

### 方式 1：使用访问凭证（推荐）

**适用场景**：个人版实例，简单易用

**配置方法**：

1. 在阿里云控制台设置访问密码：
   - 进入：容器镜像服务 > 仓库管理 > 访问凭证
   - 设置访问密码（如果还没有设置）

2. GitHub Secrets 配置：
   ```
   ACR_REGISTRY = crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
   ACR_NAMESPACE = hifate-bazi-namespaces
   ACR_USERNAME = 你的阿里云账号（邮箱或手机号）
   ACR_PASSWORD = 访问密码（在访问凭证中设置的密码）
   ```

### 方式 2：使用 AccessKey（当前配置）

**适用场景**：需要更细粒度的权限控制

**配置方法**：

1. 确保 AccessKey 已启用：
   - 进入：阿里云控制台 > 访问控制（RAM）> 用户 > AccessKey 管理
   - 确认 AccessKey 状态为"启用"

2. 确保 AccessKey 有 ACR 权限：
   - 检查 RAM 用户是否有 `AliyunContainerRegistryFullAccess` 权限
   - 或者自定义策略包含 ACR 相关权限

3. GitHub Secrets 配置（当前配置）：
   ```
   ACR_REGISTRY = crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
   ACR_NAMESPACE = hifate-bazi-namespaces
   ACR_USERNAME = <你的 AccessKey ID> (格式: LTAI...)
   ACR_PASSWORD = <你的 AccessKey Secret>
   ```

## 当前配置状态

根据测试结果，当前配置的 AccessKey 可能存在问题：

- ✅ 格式正确
- ❌ 登录失败（可能是权限问题或 AccessKey 未启用）

## 解决方案

### 方案 1：切换到访问凭证（推荐）

1. 在阿里云控制台设置访问密码
2. 更新 GitHub Secrets：
   - `ACR_USERNAME` = 你的阿里云账号
   - `ACR_PASSWORD` = 访问密码

### 方案 2：修复 AccessKey 权限

1. 检查 AccessKey 是否启用
2. 检查 RAM 用户权限
3. 确保有 ACR 访问权限

### 方案 3：在 GitHub Actions 中测试

即使本地测试失败，GitHub Actions 中可能仍然可以正常工作，因为：
- GitHub Actions 的网络环境不同
- 可能有不同的认证机制

**建议**：先在 GitHub Actions 中测试，如果仍然失败，再切换到访问凭证方式。

## 验证步骤

### 1. 检查访问凭证设置

在阿里云控制台：
1. 容器镜像服务 > 仓库管理 > 访问凭证
2. 查看是否已设置访问密码
3. 如果未设置，点击"设置访问密码"

### 2. 更新 GitHub Secrets

根据选择的认证方式，更新 GitHub Secrets：

**访问凭证方式**：
```
ACR_USERNAME = 你的阿里云账号
ACR_PASSWORD = 访问密码
```

**AccessKey 方式**（当前）：
```
ACR_USERNAME = <你的 AccessKey ID> (格式: LTAI...)
ACR_PASSWORD = <你的 AccessKey Secret>
```

### 3. 触发 GitHub Actions 测试

1. 推送到 master 分支
2. 查看 workflow 日志
3. 检查 Docker 登录是否成功

## 参考信息

- **ACR Registry**: `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`
- **Namespace**: `hifate-bazi-namespaces`
- **最终镜像名称格式**:
  ```
  crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:master
  crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:latest
  ```

## 下一步

1. ✅ 格式验证已通过
2. ⚠️  需要确认认证方式（访问凭证 vs AccessKey）
3. 📝 更新 GitHub Secrets（如果需要）
4. 🚀 触发 GitHub Actions 测试


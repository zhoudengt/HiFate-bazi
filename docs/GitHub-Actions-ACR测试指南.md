# GitHub Actions ACR 配置测试指南

## 概述

已创建测试工作流 `.github/workflows/test-acr-config.yml`，用于验证 GitHub Secrets 中的 ACR 配置是否正确。

## 使用步骤

### 1. 确保 GitHub Secrets 已配置

在 GitHub 仓库设置中配置以下 Secrets：

- `ACR_REGISTRY` - 阿里云容器镜像服务地址
- `ACR_NAMESPACE` - 命名空间
- `ACR_USERNAME` - 用户名（AccessKey ID 或阿里云账号）
- `ACR_PASSWORD` - 密码（AccessKey Secret 或访问密码）

**配置路径**：
1. 打开仓库：https://github.com/zhoudengt/HiFate-bazi
2. 进入：Settings > Secrets and variables > Actions
3. 添加或更新上述 4 个 Secrets

### 2. 触发测试工作流

有两种方式触发测试：

#### 方式 1：手动触发（推荐）

1. 打开 GitHub 仓库的 Actions 页面
2. 在左侧工作流列表中找到 "🧪 Test ACR Configuration"
3. 点击 "Run workflow" 按钮
4. 选择测试类型：
   - `login_only` - 仅测试登录（快速）
   - `build_and_push` - 测试登录、构建和推送（完整测试）
5. 点击 "Run workflow" 开始测试

#### 方式 2：推送到仓库

将测试工作流文件推送到仓库后，也可以手动触发。

### 3. 查看测试结果

1. 在 Actions 页面找到运行中的工作流
2. 点击进入查看详细日志
3. 检查以下步骤的结果：

   - ✅ **检查 ACR Secrets 配置**：验证所有 Secrets 是否已配置
   - ✅ **测试 Docker 登录到 ACR**：验证登录是否成功
   - ✅ **构建并推送测试镜像**（如果选择了 build_and_push）：验证完整流程

## 测试结果解读

### ✅ 成功情况

如果所有步骤都成功，你会看到：

```
✅ ACR Secrets 配置: 完整
✅ Docker 登录: 成功
✅ 测试镜像构建并推送成功（如果选择了 build_and_push）
```

**下一步**：
- 可以正常使用 `build-and-push.yml` 和 `deploy-test.yml` 工作流

### ❌ 失败情况

#### 情况 1：Secrets 未配置

```
❌ ACR_REGISTRY: 未配置
❌ ACR_NAMESPACE: 未配置
...
```

**解决方案**：
- 在 GitHub Secrets 中添加缺失的配置项

#### 情况 2：Docker 登录失败

```
❌ Docker 登录: 失败
错误: unauthorized: authentication required
```

**可能的原因和解决方案**：

1. **如果使用 AccessKey**：
   - 检查 AccessKey 是否已启用
   - 检查 AccessKey 是否有 ACR 访问权限
   - 确认 `ACR_USERNAME` 是 AccessKey ID（格式：`LTAI...`）
   - 确认 `ACR_PASSWORD` 是 AccessKey Secret

2. **如果使用访问凭证**：
   - 在阿里云控制台设置访问密码
   - 确认 `ACR_USERNAME` 是阿里云账号（邮箱或手机号）
   - 确认 `ACR_PASSWORD` 是访问密码（不是 AccessKey Secret）

3. **网络问题**：
   - 检查 GitHub Actions 的网络连接
   - 确认 ACR 地址是否正确

## 当前配置值

根据从阿里云控制台提取的信息：

```
ACR_REGISTRY = crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
ACR_NAMESPACE = hifate-bazi-namespaces
ACR_USERNAME = <你的 AccessKey ID> (格式: LTAI...)
ACR_PASSWORD = <你的 AccessKey Secret>
```

## 测试工作流功能

### 1. 检查 Secrets 配置

- 验证所有 4 个 Secrets 是否已配置
- 显示配置的值（密码会被隐藏）
- 显示镜像名称格式

### 2. 测试 Docker 登录

- 尝试登录到 ACR
- 验证认证信息是否正确
- 提供详细的错误诊断信息

### 3. 构建并推送测试镜像（可选）

- 创建一个简单的测试镜像
- 推送到 ACR
- 验证完整的构建和推送流程

## 相关文档

- [ACR 配置说明](./ACR配置说明.md) - 详细的配置说明和问题排查
- [Docker 生产部署完整指南](./Docker生产部署完整指南.md) - 完整的部署流程

## 下一步

1. ✅ 配置 GitHub Secrets
2. ✅ 触发测试工作流
3. ✅ 查看测试结果
4. ✅ 根据结果修复配置（如果需要）
5. ✅ 测试成功后，使用正常的 CI/CD 流程

## 注意事项

1. **Secrets 安全**：
   - 不要在代码中硬编码 Secrets
   - 不要在日志中输出完整的密码
   - 定期轮换 AccessKey 和访问密码

2. **测试频率**：
   - 首次配置后必须测试
   - 修改 Secrets 后需要重新测试
   - 建议定期测试（如每月一次）

3. **网络环境**：
   - GitHub Actions 的网络环境可能与本地不同
   - 即使本地测试失败，GitHub Actions 中可能仍然可以正常工作
   - 反之亦然


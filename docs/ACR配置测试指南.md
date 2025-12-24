# ACR 配置测试指南

## 🧪 使用 GitHub Actions 测试 ACR 配置

### 步骤 1: 访问 GitHub Actions 页面

打开以下链接：
```
https://github.com/zhoudengt/HiFate-bazi/actions
```

### 步骤 2: 选择测试 Workflow

在左侧工作流列表中找到：
```
🧪 Test ACR Configuration
```

点击进入该 workflow。

### 步骤 3: 手动触发测试

1. 点击右上角的 **"Run workflow"** 按钮（绿色）
2. 在弹出窗口中选择：
   - **测试类型**：`login_only`（仅测试登录，推荐）
   - 或者：`build_and_push`（完整测试，包括构建和推送）
3. 点击绿色的 **"Run workflow"** 按钮

### 步骤 4: 查看测试结果

1. 等待 workflow 运行（通常 1-2 分钟）
2. 点击最新的运行记录
3. 查看测试结果：

#### ✅ 如果测试通过

您会看到：
- ✅ `ACR Secrets 配置: 完整`
- ✅ `Docker 登录: 成功`
- ✅ 所有配置值显示正确

**说明**：配置正确，可以正常使用！

#### ❌ 如果测试失败

查看错误信息：

**错误 1: Secrets 未配置**
- 检查 GitHub Secrets 中是否配置了所有 4 个值
- 参考：`docs/ACR配置验证清单.md`

**错误 2: Docker 登录失败**
- 检查 `ACR_USERNAME` 和 `ACR_PASSWORD` 是否正确
- 如果使用 AccessKey，确认 AccessKey 已启用
- 如果使用账号密码，确认密码正确

**错误 3: 格式错误**
- 检查 `ACR_REGISTRY` 是否使用公网地址
- 检查 `ACR_NAMESPACE` 大小写是否正确

---

## 📋 期望的配置值（参考）

基于阿里云控制台，正确的配置值应该是：

| Secret 名称 | 期望值 |
|------------|--------|
| `ACR_REGISTRY` | `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com` |
| `ACR_NAMESPACE` | `hifate-bazi-namespaces` |
| `ACR_USERNAME` | `aliyun3959725177` (或 AccessKey ID) |
| `ACR_PASSWORD` | `[您的访问密码或 AccessKey Secret]` |

---

## 📊 测试结果解读

### 成功的测试输出示例

```
==========================================
🔍 检查 ACR Secrets 配置
==========================================

✅ ACR_REGISTRY: 已配置
   值: crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
✅ ACR_NAMESPACE: 已配置
   值: hifate-bazi-namespaces
✅ ACR_USERNAME: 已配置
   值: aliyun3959725177
✅ ACR_PASSWORD: 已配置（隐藏）
   长度: 30 字符

✅ 所有 ACR Secrets 已配置

==========================================
📦 镜像名称格式
==========================================
完整镜像名称: crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:<tag>
示例:
  - crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:master
  - crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:latest

==========================================
🔐 测试 Docker 登录到 ACR
==========================================

尝试登录到: crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
用户名: aliyun3959725177

✅ Docker 登录成功！

==========================================
📊 测试总结
==========================================

✅ ACR Secrets 配置: 完整
✅ Docker 登录: 成功
```

---

## 🔧 如果测试失败，如何修复

### 问题 1: Secrets 未配置

**解决方法**：
1. 访问 GitHub Secrets 页面：
   ```
   https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions
   ```
2. 点击 "New repository secret"
3. 依次添加 4 个 secrets：
   - `ACR_REGISTRY`
   - `ACR_NAMESPACE`
   - `ACR_USERNAME`
   - `ACR_PASSWORD`

### 问题 2: Docker 登录失败

**错误信息**：
```
❌ Docker 登录失败！
Error response from daemon: Get "...": unauthorized: authentication required
```

**解决方法**：

1. **如果使用账号密码**：
   - 确认 `ACR_USERNAME` 是阿里云账号名（如：`aliyun3959725177`）
   - 确认 `ACR_PASSWORD` 是访问密码（在阿里云控制台"访问凭证"中设置）

2. **如果使用 AccessKey**：
   - 确认 `ACR_USERNAME` 是 AccessKey ID（格式：`LTAI...`）
   - 确认 `ACR_PASSWORD` 是 AccessKey Secret
   - 确认 AccessKey 已启用且有 ACR 访问权限

3. **检查配置值**：
   - 确认没有多余的空格
   - 确认没有换行符
   - 确认值完整（没有遗漏字符）

### 问题 3: 镜像推送失败

**错误信息**：
```
denied: repository does not exist
```

**解决方法**：
1. 检查 `ACR_NAMESPACE` 是否正确：`hifate-bazi-namespaces`
2. 确认命名空间在阿里云控制台中存在
3. 确认大小写正确（全小写）

---

## ✅ 测试通过后的下一步

1. **推送代码触发构建**：
   ```bash
   git push origin master
   ```

2. **查看构建结果**：
   - 访问 GitHub Actions 页面
   - 查看 `🐳 Build and Push Docker Image` workflow
   - 确认镜像成功推送到 ACR

3. **验证镜像**：
   - 在阿里云控制台查看镜像仓库
   - 确认有新镜像（tag: `master`, `latest`, 或 commit SHA）

---

## 📝 快速链接

- **GitHub Secrets 配置**：https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions
- **GitHub Actions 测试**：https://github.com/zhoudengt/HiFate-bazi/actions/workflows/test-acr-config.yml
- **GitHub Actions 构建**：https://github.com/zhoudengt/HiFate-bazi/actions/workflows/build-and-push.yml


# ACR 配置验证清单

## 从阿里云控制台提取的信息

根据您提供的阿里云容器镜像服务截图，以下是需要配置到 GitHub Secrets 的信息：

### 配置信息

```
ACR_REGISTRY = crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
ACR_NAMESPACE = hifate-bazi-namespaces
ACR_USERNAME = <你的 AccessKey ID 或阿里云账号>
ACR_PASSWORD = <你的 AccessKey Secret 或访问密码>
```

## GitHub Secrets 配置检查清单

### 1. 访问 GitHub Secrets 页面

1. 打开仓库：https://github.com/zhoudengt/HiFate-bazi
2. 进入 Settings > Secrets and variables > Actions
3. 检查以下 4 个 secrets 是否存在：

   - [ ] `ACR_REGISTRY`
   - [ ] `ACR_NAMESPACE`
   - [ ] `ACR_USERNAME`
   - [ ] `ACR_PASSWORD`

### 2. 验证每个 Secret 的值

#### ACR_REGISTRY
- **期望值**：`crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`
- **检查点**：
  - ✅ 使用公网地址（不是 VPC 地址）
  - ✅ 不包含 `http://` 或 `https://` 前缀
  - ✅ 格式：`实例ID.地域.personal.cr.aliyuncs.com`

#### ACR_NAMESPACE
- **期望值**：`hifate-bazi-namespaces`
- **检查点**：
  - ✅ 与阿里云控制台中的命名空间名称完全一致
  - ✅ 注意大小写

#### ACR_USERNAME
- **期望值**：`<你的 AccessKey ID>`（格式：`LTAI...`）
- **检查点**：
  - ✅ 使用 AccessKey ID（不是用户名）
  - ✅ 格式：以 `LTAI` 开头

#### ACR_PASSWORD
- **期望值**：`<你的 AccessKey Secret>`
- **检查点**：
  - ✅ 使用 AccessKey Secret（不是密码）
  - ✅ 完整复制，没有多余空格

### 3. 验证镜像名称格式

根据 workflow 文件，最终镜像名称格式应该是：
```
${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi:${TAG}
```

**示例**：
```
crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:master
crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:latest
```

## 本地测试验证

### 测试 Docker 登录

```bash
# 设置环境变量
export ACR_REGISTRY="crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com"
export ACR_NAMESPACE="hifate-bazi-namespaces"
export ACR_USERNAME="<你的 AccessKey ID 或阿里云账号>"
export ACR_PASSWORD="<你的 AccessKey Secret 或访问密码>"

# 测试登录
echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" -u "$ACR_USERNAME" --password-stdin

# 如果登录成功，应该看到：
# Login Succeeded
```

### 测试拉取镜像（如果已有镜像）

```bash
# 尝试拉取镜像
docker pull "${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi:latest"
```

## 常见问题

### 问题 1：登录失败 "unauthorized: authentication required"
- **原因**：AccessKey ID 或 Secret 错误
- **解决**：检查 `ACR_USERNAME` 和 `ACR_PASSWORD` 是否正确

### 问题 2：镜像名称格式错误
- **原因**：`ACR_REGISTRY` 或 `ACR_NAMESPACE` 配置错误
- **解决**：检查格式是否正确，注意不要有多余的前缀或后缀

### 问题 3：找不到命名空间
- **原因**：`ACR_NAMESPACE` 名称不匹配
- **解决**：在阿里云控制台确认命名空间名称，注意大小写

## 下一步

1. ✅ 在 GitHub Secrets 中配置上述 4 个值
2. ✅ 触发一次 workflow 运行（推送到 master 分支）
3. ✅ 检查 workflow 日志，确认：
   - Docker 登录成功
   - 镜像构建成功
   - 镜像推送成功


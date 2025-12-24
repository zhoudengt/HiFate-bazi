# ACR 配置验证清单

## 📋 从阿里云控制台提取的配置信息

基于您提供的阿里云容器镜像服务截图，以下是正确的配置值：

### ✅ 正确的配置值

| Secret 名称 | 期望值 | 说明 |
|------------|--------|------|
| `ACR_REGISTRY` | `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com` | 公网地址（不是 VPC 地址） |
| `ACR_NAMESPACE` | `hifate-bazi-namespaces` | 命名空间（注意大小写） |
| `ACR_USERNAME` | `aliyun3959725177` | 阿里云账号名（或 AccessKey ID） |
| `ACR_PASSWORD` | `[您的访问密码或 AccessKey Secret]` | 访问密码或 AccessKey Secret |

### 📦 完整镜像地址格式

```
crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:<tag>
```

**示例**：
- `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:master`
- `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:latest`

---

## 🔍 配置格式验证

### 1. ACR_REGISTRY

**期望值**：`crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`

**检查点**：
- ✅ 使用公网地址（不是 VPC 地址 `-vpc`）
- ✅ 不包含 `http://` 或 `https://` 前缀
- ✅ 格式：`实例ID.地域.personal.cr.aliyuncs.com`
- ✅ 与阿里云控制台显示的"公网地址"一致

**常见错误**：
- ❌ 使用 VPC 地址：`crpi-llets4xvyuzoxiyx-vpc.cn-beijing.personal.cr.aliyuncs.com`
- ❌ 包含协议前缀：`https://crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`
- ❌ 多空格或换行

---

### 2. ACR_NAMESPACE

**期望值**：`hifate-bazi-namespaces`

**检查点**：
- ✅ 与阿里云控制台中的命名空间名称**完全一致**
- ✅ 注意大小写（全小写）
- ✅ 不包含前后空格

**常见错误**：
- ❌ 大小写错误：`Hifate-Bazi-Namespaces` 或 `HIFATE-BAZI-NAMESPACES`
- ❌ 拼写错误：`hifate-bazi-namespace`（少了一个 s）
- ❌ 前后空格

---

### 3. ACR_USERNAME

**期望值**：`aliyun3959725177`（阿里云账号名）

**说明**：
- ✅ 可以使用阿里云账号名（如：`aliyun3959725177`）
- ✅ 也可以使用 AccessKey ID（格式：`LTAI...`，通常以 `LTAI` 开头）
- ⚠️ 注意：如果是 RAM 子账号，不支持包含点号的别名

**检查点**：
- ✅ 如果使用账号名：与登录阿里云控制台的账号一致
- ✅ 如果使用 AccessKey ID：格式为 `LTAI` 开头
- ✅ 不包含前后空格

**常见错误**：
- ❌ 使用了 AccessKey Secret 作为用户名（应该是 AccessKey ID）
- ❌ 使用了包含点号的 RAM 子账号别名

---

### 4. ACR_PASSWORD

**期望值**：`[您的访问密码或 AccessKey Secret]`

**说明**：
- ✅ 如果使用账号密码：是在开通容器镜像服务时设置的访问密码
- ✅ 如果使用 AccessKey：是 AccessKey Secret（不是 AccessKey ID）
- ✅ 完整复制，不要有多余的空格或换行

**检查点**：
- ✅ 如果使用账号密码：在阿里云控制台"访问凭证"中可以设置/查看
- ✅ 如果使用 AccessKey Secret：格式通常较长（30+ 字符）
- ✅ 没有前后空格或换行

**如何查找**：
1. **使用访问密码**：
   - 登录阿里云控制台
   - 进入"容器镜像服务" > "访问凭证"
   - 设置或查看访问密码

2. **使用 AccessKey**（推荐）：
   - 登录阿里云控制台
   - 进入"访问控制" > "AccessKey 管理"
   - 创建 AccessKey（获取 AccessKey ID 和 AccessKey Secret）
   - `ACR_USERNAME` = AccessKey ID
   - `ACR_PASSWORD` = AccessKey Secret

---

## 🧪 验证方法

### 方法 1: 使用 GitHub Actions 测试（推荐）

**步骤**：
1. 访问 GitHub Actions 页面：
   ```
   https://github.com/zhoudengt/HiFate-bazi/actions
   ```

2. 选择 `🧪 Test ACR Configuration` workflow

3. 点击右上角的 `Run workflow` 按钮

4. 选择测试类型：`login_only`（仅测试登录）

5. 点击绿色的 `Run workflow` 按钮

6. 查看测试结果：
   - ✅ 如果所有检查通过，说明配置正确
   - ❌ 如果登录失败，查看错误信息并修正配置

**测试内容**：
- ✅ 检查所有 4 个 secrets 是否已配置
- ✅ 显示配置的值（密码隐藏）
- ✅ 测试 Docker 登录到 ACR
- ✅ 显示镜像名称格式

---

### 方法 2: 本地测试 Docker 登录

**步骤**：
1. 确保本地已安装 Docker

2. 运行 Docker 登录命令：
   ```bash
   docker login crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com -u aliyun3959725177
   ```

3. 输入密码（AccessKey Secret 或访问密码）

4. 查看结果：
   - ✅ `Login Succeeded` - 配置正确
   - ❌ `Error response from daemon: Get ... unauthorized` - 用户名或密码错误

---

### 方法 3: 运行本地检查脚本

**步骤**：
1. 运行检查脚本：
   ```bash
   bash scripts/check_acr_secrets.sh
   ```

2. 查看输出，确认格式是否正确

**注意**：本地脚本只能检查格式，无法测试实际的登录（因为无法访问 GitHub Secrets）

---

## ✅ 配置检查清单

在 GitHub Secrets 中逐一检查：

### 步骤 1: 访问 GitHub Secrets 页面

```
https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions
```

### 步骤 2: 检查每个 Secret

#### ACR_REGISTRY
- [ ] 是否存在
- [ ] 值是否为：`crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`
- [ ] 是否使用公网地址（不是 VPC 地址）
- [ ] 是否不包含 `http://` 或 `https://` 前缀

#### ACR_NAMESPACE
- [ ] 是否存在
- [ ] 值是否为：`hifate-bazi-namespaces`
- [ ] 大小写是否正确（全小写）
- [ ] 是否与阿里云控制台中的命名空间名称一致

#### ACR_USERNAME
- [ ] 是否存在
- [ ] 值是否为：`aliyun3959725177` 或 AccessKey ID
- [ ] 如果使用 AccessKey ID，格式是否为 `LTAI...` 开头
- [ ] 是否不包含前后空格

#### ACR_PASSWORD
- [ ] 是否存在
- [ ] 值是否为访问密码或 AccessKey Secret
- [ ] 是否完整复制（没有遗漏字符）
- [ ] 是否不包含前后空格或换行

---

## ⚠️ 常见问题和解决方案

### 问题 1: Docker 登录失败 - unauthorized

**错误信息**：
```
Error response from daemon: Get "https://...": unauthorized: authentication required
```

**可能原因**：
1. `ACR_USERNAME` 不正确
2. `ACR_PASSWORD` 不正确
3. AccessKey 未启用或没有 ACR 访问权限

**解决方案**：
1. 确认 `ACR_USERNAME` 是账号名或 AccessKey ID（不是 AccessKey Secret）
2. 确认 `ACR_PASSWORD` 是访问密码或 AccessKey Secret
3. 如果使用 AccessKey，确认 AccessKey 已启用且有 ACR 访问权限

---

### 问题 2: 镜像推送失败 - repository does not exist

**错误信息**：
```
Error response from daemon: repository does not exist
```

**可能原因**：
1. `ACR_NAMESPACE` 不正确（大小写或拼写错误）
2. 命名空间不存在

**解决方案**：
1. 检查 `ACR_NAMESPACE` 是否与阿里云控制台中的命名空间名称完全一致
2. 在阿里云控制台确认命名空间是否存在
3. 注意大小写（应该是全小写：`hifate-bazi-namespaces`）

---

### 问题 3: 镜像推送失败 - denied: requested access to the resource is denied

**错误信息**：
```
denied: requested access to the resource is denied
```

**可能原因**：
1. 账号没有推送镜像的权限
2. AccessKey 权限不足

**解决方案**：
1. 确认账号有容器镜像服务的推送权限
2. 如果使用 RAM 子账号，确认已授予 ACR 相关权限
3. 检查 AccessKey 的权限范围

---

### 问题 4: 构建成功但推送失败

**可能原因**：
1. `ACR_REGISTRY` 使用了 VPC 地址（GitHub Actions 无法访问）
2. 网络问题

**解决方案**：
1. 确认 `ACR_REGISTRY` 使用公网地址（不是 `-vpc` 地址）
2. 检查 GitHub Actions 的网络连接
3. 查看构建日志获取详细错误信息

---

## 📊 配置验证结果

### 验证步骤

1. ✅ **格式验证**：使用 `scripts/check_acr_secrets.sh` 检查格式
2. ✅ **GitHub Actions 测试**：使用 `test-acr-config.yml` 测试登录
3. ✅ **构建测试**：推送代码，查看 `build-and-push.yml` 是否成功

### 验证结果

如果所有测试通过，配置正确！

---

## 📝 快速参考

### GitHub Secrets 配置页面
```
https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions
```

### GitHub Actions 测试页面
```
https://github.com/zhoudengt/HiFate-bazi/actions/workflows/test-acr-config.yml
```

### 正确的配置值
```
ACR_REGISTRY = crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com
ACR_NAMESPACE = hifate-bazi-namespaces
ACR_USERNAME = aliyun3959725177  (或 AccessKey ID)
ACR_PASSWORD = [您的访问密码或 AccessKey Secret]
```

---

## 🎯 下一步

1. ✅ 确认 GitHub Secrets 配置正确
2. ✅ 使用 GitHub Actions 测试配置（`test-acr-config.yml`）
3. ✅ 如果测试通过，推送代码触发 `build-and-push.yml`
4. ✅ 查看构建日志，确认镜像成功推送到 ACR


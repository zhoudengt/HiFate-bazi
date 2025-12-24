# ACR 配置快速检查

## 📋 配置值清单

### ✅ 基于阿里云控制台的正确配置值

| Secret 名称 | 正确值 | GitHub Secrets 中的值 |
|------------|--------|---------------------|
| **ACR_REGISTRY** | `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com` | [ ] 已配置 |
| **ACR_NAMESPACE** | `hifate-bazi-namespaces` | [ ] 已配置 |
| **ACR_USERNAME** | `aliyun3959725177` | [ ] 已配置 |
| **ACR_PASSWORD** | `[您的密码]` | [ ] 已配置 |

---

## 🧪 立即测试（3步完成）

### 步骤 1: 访问测试页面

打开：
```
https://github.com/zhoudengt/HiFate-bazi/actions/workflows/test-acr-config.yml
```

### 步骤 2: 触发测试

1. 点击右上角 **"Run workflow"** 按钮
2. 选择测试类型：`login_only`
3. 点击 **"Run workflow"**

### 步骤 3: 查看结果

等待 1-2 分钟，查看测试结果：
- ✅ 全部通过 = 配置正确
- ❌ 有错误 = 根据错误信息修正

---

## 📊 配置验证清单

在 GitHub Secrets 页面（https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions）检查：

### ACR_REGISTRY

- [ ] 值是否为：`crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`
- [ ] 是否使用公网地址（不是 VPC 地址，不要有 `-vpc`）
- [ ] 是否不包含 `http://` 或 `https://` 前缀

**常见错误**：
- ❌ `crpi-llets4xvyuzoxiyx-vpc.cn-beijing.personal.cr.aliyuncs.com`（VPC 地址）
- ❌ `https://crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com`（有协议前缀）

---

### ACR_NAMESPACE

- [ ] 值是否为：`hifate-bazi-namespaces`
- [ ] 大小写是否正确（全小写）
- [ ] 是否与阿里云控制台中的命名空间名称一致

**常见错误**：
- ❌ `Hifate-Bazi-Namespaces`（大小写错误）
- ❌ `hifate-bazi-namespace`（少了一个 s）

---

### ACR_USERNAME

- [ ] 值是否为：`aliyun3959725177`（阿里云账号名）
- [ ] 或者是否为 AccessKey ID（格式：`LTAI...`）
- [ ] 是否不包含前后空格

**说明**：
- 可以使用阿里云账号名（如：`aliyun3959725177`）
- 也可以使用 AccessKey ID（如：`LTAI5...`）

---

### ACR_PASSWORD

- [ ] 是否为访问密码（开通服务时设置的）
- [ ] 或者是否为 AccessKey Secret
- [ ] 是否完整复制（没有遗漏字符或多余空格）

**如何查找**：
1. **访问密码**：阿里云控制台 > 容器镜像服务 > 访问凭证 > 设置访问密码
2. **AccessKey Secret**：阿里云控制台 > 访问控制 > AccessKey 管理 > 创建 AccessKey

---

## ✅ 完整镜像地址格式

```
crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:<tag>
```

**示例**：
- `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:master`
- `crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com/hifate-bazi-namespaces/hifate-bazi:latest`

---

## 🔍 验证结果

### ✅ 如果 GitHub Actions 测试通过

说明配置正确，可以正常使用！

**下一步**：
1. 推送代码触发 `build-and-push.yml`
2. 查看构建日志，确认镜像成功推送

### ❌ 如果测试失败

根据错误信息修正：
1. **Secrets 未配置** → 添加缺失的 secrets
2. **登录失败** → 检查用户名和密码
3. **格式错误** → 检查格式要求

详细错误处理参考：`docs/ACR配置测试指南.md`

---

## 📝 快速链接

- **GitHub Secrets**：https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions
- **测试 Workflow**：https://github.com/zhoudengt/HiFate-bazi/actions/workflows/test-acr-config.yml
- **详细文档**：`docs/ACR配置验证清单.md`


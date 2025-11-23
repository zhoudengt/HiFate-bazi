# 切换到 Cursor Pro+ 服务说明

**日期**: 2025-11-23  
**操作**: 从自定义 API 代理切换到 Cursor Pro+ 内置服务

---

## ✅ 已完成的操作

### 1. 移除了自定义 API 配置
从配置文件中移除了以下项：
- ❌ `cursor.anthropicApiKey` (自定义 API Key)
- ❌ `cursor.anthropicApiBaseUrl` (代理服务地址)
- ❌ `cursor.useCustomApi` (自定义 API 标志)
- ❌ `cursor.chat.useCustomApi`
- ❌ `cursor.chat.anthropicApiKey`
- ❌ `cursor.chat.anthropicApiBaseUrl`
- ❌ `anthropic.apiKey`
- ❌ `anthropic.apiBaseUrl`
- ❌ `cursor.bypassRegionCheck` (不再需要绕过区域检查)
- ❌ `cursor.disableRegionCheck`
- ❌ `cursor.general.disableHttp2`

### 2. 保留的配置
- ✅ `cursor.aiProvider: "anthropic"` (使用 Anthropic/Claude)
- ✅ `cursor.model: "claude-sonnet-4-20250514"` (Claude Sonnet 4.5)
- ✅ `cursor.chat.model: "claude-sonnet-4-20250514"`
- ✅ 基础的窗口和浏览器设置

---

## 🔄 如何使配置生效

### 方式1：完全重启 Cursor（推荐）
```bash
# Mac
1. 按 Cmd + Q 完全退出 Cursor
2. 重新打开 Cursor 应用
```

### 方式2：重新加载窗口
```
1. 按 Cmd + Shift + P 打开命令面板
2. 输入 "Developer: Reload Window"
3. 按 Enter
```

---

## 💰 Cursor Pro+ vs 自定义代理

| 对比项 | Cursor Pro+ ($60/月) | 自定义代理 (之前的配置) |
|--------|---------------------|----------------------|
| **费用** | ✅ 包含在订阅中 | ❌ 需额外付费 |
| **请求限额** | ✅ 更高额度 (通常无限) | ⚠️ 取决于代理服务商 |
| **稳定性** | ✅ 官方保障 | ⚠️ 依赖第三方 |
| **速度** | ✅ 优化的服务器 | ⚠️ 可能有延迟 |
| **隐私** | ✅ 直连官方 | ❌ 经过第三方代理 |
| **支持** | ✅ 官方客服 | ⚠️ 代理商客服 |
| **配置** | ✅ 零配置 | ❌ 需要配置 |

---

## 🎯 Cursor Pro+ 的优势

### 1. 更高的使用限额
- **Pro+ ($60/月)** 提供比 Pro ($20/月) 更高的额度
- 通常包含：
  - 无限的 Claude Sonnet 请求
  - 大量的 GPT-4 请求
  - 优先访问新功能

### 2. 更好的性能
- 直连 Cursor 优化的服务器
- 更快的响应速度
- 更稳定的连接

### 3. 更好的隐私保护
- 对话不经过第三方代理
- 符合企业级隐私标准
- Cursor 官方隐私政策保护

### 4. 简化的管理
- 无需管理 API Key
- 无需担心余额不足
- 无需配置代理

---

## 🔍 如何验证配置

### 1. 重启 Cursor 后，检查：
- 打开一个新的对话
- 发送消息给 AI
- 如果正常响应，说明配置成功

### 2. 检查模型选择：
- 打开 Cursor 设置 (`Cmd + ,`)
- 查看 `Models` 选项卡
- 应该看到可用的模型列表，无需配置 API Key

### 3. 查看订阅状态：
- 打开 Cursor 设置
- 查看 `Account` 或 `Subscription` 选项卡
- 应该显示 "Pro+" 订阅状态

---

## 🆘 如果遇到问题

### 问题1：重启后无法使用 Claude
**解决方案**：
1. 检查订阅状态是否为 Pro+
2. 确认已完全重启 Cursor（不是只关闭窗口）
3. 检查网络连接
4. 尝试退出登录并重新登录

### 问题2：提示需要 API Key
**解决方案**：
1. 确认配置文件已正确修改
2. 确认没有项目级的 `.cursor/config.json` 覆盖全局配置
3. 重新加载窗口或完全重启

### 问题3：想继续使用代理服务
**解决方案**：
如果您仍然想使用之前的代理配置，可以恢复：

```json
{
    "cursor.useCustomApi": true,
    "cursor.anthropicApiKey": "sk-TsJb5SqalyBePCL3B9jA44ikrBElCJP7P3yxIdAJk65PflPv",
    "cursor.anthropicApiBaseUrl": "https://cc.zhihuiapi.top",
    "cursor.chat.useCustomApi": true,
    "cursor.chat.anthropicApiKey": "sk-TsJb5SqalyBePCL3B9jA44ikrBElCJP7P3yxIdAJk65PflPv",
    "cursor.chat.anthropicApiBaseUrl": "https://cc.zhihuiapi.top"
}
```

但建议使用 Pro+ 内置服务，因为您已经付费了。

---

## 💡 建议

### ✅ 推荐使用 Cursor Pro+ 内置服务
因为：
1. 您已经支付了 $60/月
2. 不需要额外为代理服务付费
3. 更稳定、更快速、更安全
4. 官方支持和保障

### ⚠️ 保留代理配置作为备份
- 可以将之前的 API Key 保存在安全的地方
- 如果遇到 Cursor 服务问题，可以临时切换回代理
- 但日常使用建议使用 Pro+ 内置服务

---

## 📞 获取帮助

### Cursor 官方支持
- **网站**: https://cursor.sh
- **文档**: https://docs.cursor.sh
- **Discord**: https://discord.gg/cursor
- **邮件**: support@cursor.sh

### 订阅管理
- 打开 Cursor 设置
- 进入 `Account` → `Subscription`
- 查看和管理您的订阅

---

## 📊 Pro+ 订阅详情

### Cursor Pro+ ($60/月) 包含：
- ✅ 无限的 Claude Sonnet 3.5/4.5 请求
- ✅ 大量的 GPT-4/GPT-4 Turbo 请求
- ✅ 优先访问新功能和模型
- ✅ 更高的上下文窗口限制
- ✅ 更快的代码补全
- ✅ 高级代码分析功能

---

## ✅ 总结

**之前**：使用自定义 API Key + 智慧API代理  
**现在**：使用 Cursor Pro+ 内置服务  

**优势**：
- 💰 节省代理服务费用
- 🚀 更快更稳定
- 🔒 更好的隐私保护
- ✅ 官方支持

**下一步**：
1. 完全重启 Cursor (Cmd+Q 然后重新打开)
2. 开始使用！

---

**配置文件位置**: `~/Library/Application Support/Cursor/User/settings.json`  
**修改时间**: 2025-11-23  
**生效方式**: 重启 Cursor





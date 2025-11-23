# 使用 Clash Verge 直接访问 Cursor Pro+ 服务

**日期**: 2025-11-23  
**方案**: 通过系统代理（Clash Verge）直接使用 Pro+ 服务，无需配置 API Key

---

## ✅ 检测结果

### Clash Verge 状态
- ✅ **已安装**: `/Applications/Clash Verge.app`
- ✅ **正在运行**: 进程 ID 495
- ✅ **系统代理已启用**: `127.0.0.1:7897`
- ✅ **所有网络请求通过 Clash 代理**

---

## 🔧 配置说明

### 已移除的配置
- ❌ `cursor.anthropicApiKey` (不再需要)
- ❌ `cursor.anthropicApiBaseUrl` (不再需要)
- ❌ `cursor.useCustomApi` (不再需要)
- ❌ `cursor.chat.useCustomApi` (不再需要)
- ❌ `cursor.chat.anthropicApiKey` (不再需要)
- ❌ `cursor.chat.anthropicApiBaseUrl` (不再需要)
- ❌ `anthropic.apiKey` (不再需要)
- ❌ `anthropic.apiBaseUrl` (不再需要)
- ❌ `cursor.bypassRegionCheck` (不再需要)
- ❌ `cursor.disableRegionCheck` (不再需要)

### 保留的配置
- ✅ `cursor.aiProvider: "anthropic"` (使用 Claude)
- ✅ `cursor.model: "claude-sonnet-4-20250514"` (Sonnet 4.5)
- ✅ `cursor.chat.model: "claude-sonnet-4-20250514"`
- ✅ `http.proxySupport: "on"` (使用系统代理)
- ✅ `http.systemCertificates: true` (系统证书)

---

## 🔗 工作原理

### 网络流程
```
您的电脑
  ↓
Clash Verge (127.0.0.1:7897) ← 系统代理
  ↓
Cursor 官方服务器 (通过 Clash 代理)
  ↓
Claude API
```

### 关键点
1. **系统级代理**: Clash Verge 配置为系统代理
2. **自动使用**: Cursor 会自动使用系统代理设置
3. **无需配置**: 不需要在 Cursor 中单独配置代理
4. **直接访问**: 通过代理直接访问 Cursor 官方服务

---

## 💰 成本对比

### 之前（使用代理 API）
- Cursor Pro+: $60/月
- 代理服务商: $X/月（额外）
- **总计**: $60+ /月

### 现在（使用系统代理 + Pro+）
- Cursor Pro+: $60/月（包含所有）
- Clash Verge: 免费（或您已有的订阅）
- **总计**: $60/月

**节省**: 代理服务商的费用 💰

---

## ✅ 优势

### 1. 充分利用订阅
- ✅ 直接使用 Pro+ 官方服务
- ✅ 不需要额外付费给代理服务商
- ✅ 更高的请求限额
- ✅ 更快的响应速度

### 2. 更好的性能
- ✅ 直连 Cursor 官方服务器（通过 Clash）
- ✅ 不经过第三方代理服务
- ✅ 更稳定的连接
- ✅ 更快的响应

### 3. 更简单的配置
- ✅ 不需要管理 API Key
- ✅ 不需要配置代理地址
- ✅ 系统代理自动生效
- ✅ 配置更简洁

### 4. 更好的隐私
- ✅ 不经过第三方代理服务商
- ✅ 对话内容只经过 Clash（本地）和 Cursor 官方
- ✅ 更好的隐私保护

---

## ⚠️ 重要提醒

### 1. 确保 Clash Verge 运行
```
如果 Clash Verge 关闭，Cursor 可能无法连接。

建议：
- 将 Clash Verge 设置为开机自启
- 定期检查 Clash 是否正常运行
- 如果遇到连接问题，先检查 Clash 状态
```

### 2. 检查系统代理设置
```
如果系统代理被禁用，Cursor 无法通过代理访问。

检查方法：
- 系统设置 → 网络 → 代理
- 或运行：networksetup -getwebproxy "Wi-Fi"
```

### 3. 如果 Clash 不可用
```
如果 Clash 暂时不可用，可以临时切换回代理 API 配置。

但建议优先修复 Clash 连接，因为：
- 更稳定
- 更快速
- 更安全
```

---

## 🔍 验证方法

### 1. 检查 Clash Verge 状态
```bash
# 检查是否运行
ps aux | grep clash-verge

# 检查系统代理
networksetup -getwebproxy "Wi-Fi"
```

### 2. 测试 Cursor 连接
```
1. 重启 Cursor
2. 打开 AI 对话窗口
3. 发送测试消息
4. 如果正常回复，说明配置成功
```

### 3. 检查订阅状态
```
1. Cursor 设置 → Account → Subscription
2. 应该显示 "Pro+" 状态
3. 不应该提示需要 API Key
```

---

## 🆘 故障排查

### 问题 1：Cursor 无法连接
**可能原因**: Clash Verge 未运行或系统代理未启用

**解决方案**:
```
1. 检查 Clash Verge 是否运行
2. 检查系统代理设置
3. 重启 Clash Verge
4. 重启 Cursor
```

### 问题 2：提示区域限制
**可能原因**: Clash 代理未正确配置或未生效

**解决方案**:
```
1. 检查 Clash Verge 的代理规则
2. 确保 Cursor 相关域名被代理
3. 尝试切换 Clash 的代理节点
4. 检查系统代理是否启用
```

### 问题 3：速度慢
**可能原因**: Clash 代理节点速度慢

**解决方案**:
```
1. 在 Clash Verge 中切换更快的节点
2. 检查 Clash 的延迟和速度
3. 选择延迟低的节点
```

---

## 📊 配置对比

### 优化前（代理 API）
```json
{
    "cursor.useCustomApi": true,
    "cursor.anthropicApiKey": "sk-...",
    "cursor.anthropicApiBaseUrl": "https://cc.zhihuiapi.top",
    "cursor.bypassRegionCheck": true
}
```
- ❌ 需要额外付费
- ❌ 经过第三方代理
- ❌ 速度可能较慢

### 优化后（系统代理 + Pro+）
```json
{
    "cursor.aiProvider": "anthropic",
    "cursor.model": "claude-sonnet-4-20250514",
    "http.proxySupport": "on"
}
```
- ✅ 充分利用订阅
- ✅ 直连官方服务器
- ✅ 速度更快

---

## 💡 最佳实践

### 1. 保持 Clash 运行
- 设置为开机自启
- 定期检查运行状态
- 使用稳定的代理节点

### 2. 监控使用情况
- 定期查看 Pro+ 订阅使用情况
- 了解剩余额度
- 优化使用习惯

### 3. 备用方案
- 如果 Clash 不可用，可以临时切换回代理 API
- 但建议优先修复 Clash 连接

---

## ✅ 总结

**配置方式**: 系统代理（Clash Verge）+ Pro+ 直接访问

**优势**:
- 💰 节省代理服务费用
- 🚀 更快的响应速度
- 🔒 更好的隐私保护
- ✅ 充分利用 Pro+ 订阅

**要求**:
- ⚠️ 确保 Clash Verge 保持运行
- ⚠️ 确保系统代理已启用

**下一步**:
1. 重启 Cursor
2. 测试 AI 对话功能
3. 享受更快的速度！

---

**配置文件位置**: `~/Library/Application Support/Cursor/User/settings.json`  
**Clash 配置位置**: `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/`  
**完成时间**: 2025-11-23  
**生效方式**: 需要完全重启 Cursor




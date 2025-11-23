# Coze API 认证问题排查

## 当前问题

测试时出现错误：`Login verification is invalid`

## 可能的原因

### 1. Token 格式问题

Coze API 的 Token 应该以 `pat_` 开头。请检查：

```bash
# 查看 Token 格式
echo $COZE_ACCESS_TOKEN
```

Token 应该类似：`pat_xxxxxxxxxxxxx`

### 2. Token 权限问题

在 Coze 平台创建 Token 时，需要确保勾选以下权限：
- ✅ Bot 管理权限
- ✅ 会话权限
- ✅ 消息权限
- ✅ 文件权限（如果需要）

### 3. Bot 未发布

某些情况下，Bot 需要先发布才能通过 API 调用。

**解决步骤**：
1. 在 Coze 平台，进入你的 Bot
2. 点击 **"发布"** 按钮
3. 确保 Bot 已发布状态

### 4. API 端点问题

Coze API 可能有不同的端点格式。当前代码会尝试多个端点：
- `/open_api/v2/chat`
- `/open_api/v1/chat`
- `/api/v2/chat`
- `/api/v1/chat`
- `/v2/chat`
- `/v1/chat`
- `/chat`

### 5. 需要先创建会话

某些 Coze API 版本可能需要先创建会话（conversation），然后再发送消息。

## 排查步骤

### 步骤1：验证 Token

```bash
# 检查 Token 是否正确设置
echo $COZE_ACCESS_TOKEN

# 检查 Token 格式
echo $COZE_ACCESS_TOKEN | grep -E "^pat_"
```

### 步骤2：重新生成 Token

如果 Token 有问题，重新生成：

1. 访问 Coze 平台：https://www.coze.cn
2. 点击右上角头像 → **个人设置**
3. 找到 **API 密钥** 或 **Access Token**
4. 删除旧的 Token（如果有）
5. 创建新的 Token
6. **立即复制** Token
7. 更新到 `.env` 文件

### 步骤3：检查 Bot 状态

1. 在 Coze 平台，进入你的 Bot（Bot ID: 7573909067308695606）
2. 确认 Bot 已保存
3. 确认 Bot 已发布（如果有发布选项）
4. 确认 Bot 是启用状态

### 步骤4：检查 Bot 权限

1. 在 Bot 设置中，检查是否有权限设置
2. 确保 Bot 允许通过 API 调用

### 步骤5：测试 API 调用

运行测试脚本查看详细错误：

```bash
python scripts/test_coze_config.py
```

查看详细的错误信息，包括：
- 状态码
- 错误消息
- 响应内容

### 步骤6：查看 Coze API 文档

访问 Coze API 文档，确认正确的调用方式：
- https://www.coze.cn/docs/developer_guides/api_overview
- 查看认证方式
- 查看 API 端点
- 查看请求格式

## 常见错误及解决方案

### 错误1：Login verification is invalid

**可能原因**：
- Token 已过期
- Token 格式不对
- Token 权限不足

**解决方案**：
1. 重新生成 Token
2. 确保 Token 以 `pat_` 开头
3. 确保 Token 有足够的权限

### 错误2：Bot not found

**可能原因**：
- Bot ID 不正确
- Bot 未发布

**解决方案**：
1. 检查 Bot ID 是否正确
2. 在 Coze 平台发布 Bot

### 错误3：Endpoint not found (404)

**可能原因**：
- API 端点路径不对
- API 版本不对

**解决方案**：
- 代码会自动尝试多个端点
- 如果都失败，查看 Coze API 文档确认正确的端点

## 参考资源

- Coze API 文档：https://www.coze.cn/docs/developer_guides/api_overview
- Coze 平台：https://www.coze.cn
- 项目配置指南：`docs/Coze_Bot配置指南.md`

## 如果仍然无法解决

1. **检查网络连接**：确保可以访问 `https://api.coze.cn`
2. **查看详细日志**：运行测试脚本查看完整错误信息
3. **联系 Coze 支持**：如果 Token 和 Bot 都正确，可能是 Coze 平台的问题
4. **使用备用方案**：如果 Coze API 暂时不可用，面相手相分析的基础功能仍然可用（只是没有 AI 增强）

---

**注意**：即使 Coze API 配置失败，面相手相分析的基础功能仍然可以正常使用。AI 增强是可选的。


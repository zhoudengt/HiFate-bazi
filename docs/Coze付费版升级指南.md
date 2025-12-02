# Coze 付费版升级指南

## 📋 问题说明

当前 Coze API 免费额度已用完，错误信息：
```
错误码: 4028
错误信息: Your free quota has been used up. Please upgrade to a paid plan to continue
```

## 🚀 升级步骤

### 步骤1：访问火山引擎控制台

1. 打开浏览器，访问：**https://console.volcengine.com/coze-pro**
2. 使用您的账号登录（如果没有账号，需要先注册）

### 步骤2：选择付费计划

Coze 提供以下付费计划：

| 计划 | 价格 | 每日消息积分 | GPT-4o (8k) 每日次数 | 其他功能 |
|------|------|------------|---------------------|---------|
| **免费版** | $0/月 | 有限 | 5次 | 基础功能 |
| **Premium** | $9/月 | 更多 | 更多次数 | 更多机器人、工作流 |
| **Premium Plus** | $39/月 | 最多 | 500次 | 全部功能、高并发 |

### 步骤3：完成支付

1. 在控制台中选择适合您需求的计划
2. 点击"升级"或"订阅"
3. 完成支付流程（支持多种支付方式）

### 步骤4：验证升级状态

1. 升级完成后，返回控制台
2. 查看您的账户状态，确认已升级到付费版
3. 检查 API 额度是否已更新

## ⚙️ 配置更新（通常不需要）

升级到付费版后，**通常不需要更新 Access Token**，因为：
- Access Token 是账户级别的，不会因为升级而改变
- 升级只影响额度限制，不影响 API 调用方式

### 如果需要重新生成 Token

如果遇到问题，可以重新生成 Access Token：

1. 访问：**https://console.volcengine.com/coze-pro**
2. 进入"API 密钥"或"Access Token"页面
3. 生成新的 Token
4. 更新 `.env` 文件中的 `COZE_ACCESS_TOKEN`

```bash
# 编辑 .env 文件
vim .env

# 更新 COZE_ACCESS_TOKEN
COZE_ACCESS_TOKEN=pat_你的新Token
```

## 🔍 验证升级是否生效

升级完成后，可以通过以下方式验证：

### 方法1：查看控制台

1. 登录火山引擎控制台
2. 查看"使用量"或"额度"页面
3. 确认额度已更新

### 方法2：测试 API 调用

运行测试脚本：

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
python3 scripts/tools/test_coze_api_direct.py
```

如果升级成功，应该不再出现 4028 错误。

### 方法3：测试智能运势分析

1. 访问：`http://localhost:8001/frontend/smart-fortune-stream.html`
2. 填写表单并点击"开始分析"
3. 如果升级成功，应该能看到 AI 深度解读结果

## 📝 注意事项

1. **升级后立即生效**：升级完成后，新的额度会立即生效，无需重启服务

2. **Token 不变**：升级通常不需要更新 Access Token，除非您主动重新生成

3. **额度监控**：建议定期查看控制台的使用量，避免再次用完额度

4. **成本控制**：如果使用量大，建议：
   - 设置每日/每月使用上限
   - 监控 API 调用频率
   - 优化提示词，减少不必要的调用

## 🔗 相关链接

- **火山引擎控制台**：https://console.volcengine.com/coze-pro
- **Coze 官网**：https://www.coze.cn
- **API 文档**：https://www.coze.cn/open/docs

## ❓ 常见问题

### Q1: 升级后还是提示额度不足？

**A**: 请检查：
1. 是否选择了正确的账户
2. 支付是否成功完成
3. 等待几分钟后重试（系统可能需要时间同步）

### Q2: 需要更新 Access Token 吗？

**A**: 通常不需要。Access Token 是账户级别的，升级不会改变它。只有在以下情况才需要更新：
- Token 过期或被撤销
- 需要重新生成 Token

### Q3: 如何查看当前额度？

**A**: 
1. 登录火山引擎控制台
2. 进入 Coze 服务页面
3. 查看"使用量"或"额度"统计

### Q4: 升级后多久生效？

**A**: 通常立即生效，最多等待 1-2 分钟系统同步。

---

**升级完成后，请测试智能运势分析功能，确认 AI 深度解读正常工作。**


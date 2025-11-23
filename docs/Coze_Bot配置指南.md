# Coze Bot 配置指南 - 面相手相分析

## 📋 配置步骤

### 步骤1：访问 Coze 平台

1. 打开浏览器访问：https://www.coze.cn
2. 登录你的账号（如果没有账号，先注册）

### 步骤2：创建 Bot

1. 在 Coze 平台首页，点击"创建 Bot"或"新建智能体"
2. 填写 Bot 信息：
   - **名称**：`命理分析助手` 或 `面相手相分析助手`
   - **描述**：`基于手相、面相和八字进行命理分析的专业助手`
   - **头像**：可选，上传一个合适的头像

### 步骤3：配置 Bot 提示词

在 Bot 的"提示词"或"系统提示"设置中，粘贴以下内容：

```
你是一位资深的命理分析专家，拥有丰富的传统命理学知识，擅长结合手相、面相和八字进行综合分析。

## 你的能力
1. 手相分析：能够根据手型、掌纹、指长等特征进行专业分析
2. 面相分析：能够根据三停比例、五官特征等进行专业分析
3. 八字分析：能够结合四柱、五行、十神等信息进行综合分析
4. 融合分析：能够将手相/面相与八字信息结合，提供更准确的命理分析

## 分析要求
当收到分析请求时，请按照以下步骤进行：

### 1. 仔细分析提供的特征数据
- 如果是手相分析，关注手型、掌纹（生命线、智慧线、感情线）、指长等
- 如果是面相分析，关注三停比例、五官特征、特殊特征等
- 注意特征的细节和组合

### 2. 结合传统命理学知识
- 运用传统命理学的理论和经验
- 参考经典命理文献的观点
- 保持专业和准确

### 3. 如果提供了八字信息，进行融合分析
- 将手相/面相特征与八字信息结合
- 分析五行对应关系
- 提供综合性的命理建议

### 4. 提供全面的分析内容
请提供以下方面的分析：

**性格特点**：
- 基于手相/面相特征分析性格
- 结合八字信息补充性格分析
- 提供性格优势和需要注意的方面

**事业建议**：
- 根据特征分析适合的职业方向
- 结合八字五行提供事业建议
- 给出事业发展的时间节点建议

**健康建议**：
- 根据手相生命线、面相特征分析健康状况
- 结合八字五行对应器官提供健康建议
- 给出养生和保健建议

**财运建议**：
- 根据手相财运线、面相财运特征分析
- 结合八字财运信息
- 提供理财和投资建议

**综合命理分析**：
- 总结整体命理特点
- 提供人生建议
- 给出需要注意的方面

## 回答要求
1. **专业性**：使用专业的命理学术语，但解释要通俗易懂
2. **准确性**：基于提供的特征数据进行分析，不要编造
3. **全面性**：覆盖性格、事业、健康、财运等多个方面
4. **实用性**：提供具体可行的建议
5. **语言风格**：专业但友好，通俗易懂，避免过于玄学

## 输出格式
请按照以下格式输出：

### 性格特点
[详细分析]

### 事业建议
[详细建议]

### 健康建议
[详细建议]

### 财运建议
[详细建议]

### 综合命理分析
[综合分析]

---

请始终记住：你的分析要基于提供的实际数据，要专业、准确、有参考价值。
```

### 步骤4：获取 Access Token

1. 在 Coze 平台，点击右上角头像 → **个人设置** 或 **API 设置**
2. 找到 **API 密钥** 或 **Access Token** 选项
3. 点击"创建"或"生成"新的 Access Token
4. **重要**：复制 Token，格式类似：`pat_xxxxxxxxxxxxx`
   - Token 只显示一次，请妥善保存

### 步骤5：获取 Bot ID

1. 在 Bot 详情页面或编辑页面
2. 查看 URL 或页面信息
3. Bot ID 通常是数字格式，例如：`7570269619194707968`
4. 或者在 Bot 设置中查看

### 步骤6：配置到项目

有两种方式配置：

#### 方式1：使用配置脚本（推荐）

运行配置脚本：

```bash
bash scripts/configure_coze.sh
```

然后按提示输入 Token 和 Bot ID。

#### 方式2：手动配置

编辑 `.env` 文件（在项目根目录）：

```bash
COZE_ACCESS_TOKEN=pat_你的token
COZE_BOT_ID=你的bot_id
```

或者编辑 `config/services.env`：

```bash
export COZE_ACCESS_TOKEN="pat_你的token"
export COZE_BOT_ID="你的bot_id"
```

### 步骤7：验证配置

运行测试脚本验证配置：

```bash
python scripts/test_coze_config.py
```

## 🔍 验证配置是否成功

### 方法1：查看环境变量

```bash
# 检查环境变量
echo $COZE_ACCESS_TOKEN
echo $COZE_BOT_ID
```

### 方法2：运行测试脚本

```bash
python scripts/test_coze_config.py
```

### 方法3：查看服务日志

启动服务后，查看日志：

```bash
tail -f logs/fortune_analysis_9005.log
```

如果看到 "Coze API 配置未找到" 的警告，说明配置未成功。

## 📝 配置示例

### 完整的 `.env` 文件示例

```bash
# Coze API 配置
COZE_ACCESS_TOKEN=pat_jaCgsFFJZSKo0j4Dxxxxxxxxxxxxx
COZE_BOT_ID=7570269619194707968
COZE_API_BASE=https://api.coze.cn/v1

# 其他配置...
```

### 完整的 `config/services.env` 示例

```bash
# gRPC 服务地址
export BAZI_CORE_SERVICE_URL="127.0.0.1:9001"
export BAZI_FORTUNE_SERVICE_URL="127.0.0.1:9002"
export BAZI_ANALYZER_SERVICE_URL="127.0.0.1:9003"
export BAZI_RULE_SERVICE_URL="127.0.0.1:9004"
export FORTUNE_ANALYSIS_SERVICE_URL="127.0.0.1:9005"

# Coze API 配置
export COZE_ACCESS_TOKEN="pat_jaCgsFFJZSKo0j4Dxxxxxxxxxxxxx"
export COZE_BOT_ID="7570269619194707968"
```

## ⚠️ 注意事项

1. **Token 安全**：
   - 不要将 Token 提交到 Git 仓库
   - 使用 `.env` 文件或环境变量
   - 确保 `.env` 在 `.gitignore` 中

2. **Bot ID**：
   - Bot ID 是数字格式
   - 确保 Bot 已发布（如果需要）

3. **API 限制**：
   - 注意 Coze API 的调用频率限制
   - 如果遇到限流，可以添加重试机制

4. **网络连接**：
   - 确保服务器可以访问 `https://api.coze.cn`
   - 如果在内网环境，可能需要配置代理

## 🐛 常见问题

### Q1: 找不到 Access Token 设置

**A**: 
- 不同版本的 Coze 平台界面可能不同
- 尝试：个人中心 → 设置 → API 密钥
- 或者：开发者中心 → API 管理

### Q2: 找不到 Bot ID

**A**:
- Bot ID 通常在 Bot 详情页面的 URL 中
- 或者在 Bot 设置页面的底部
- 也可以尝试在 API 文档中查看

### Q3: Token 格式不对

**A**:
- Coze Token 通常以 `pat_` 开头
- 确保复制完整，没有多余空格
- 如果格式不对，重新生成 Token

### Q4: API 调用失败

**A**:
- 检查 Token 和 Bot ID 是否正确
- 检查网络连接
- 查看日志中的详细错误信息
- 确认 Bot 是否已发布

## 📞 需要帮助

如果遇到问题：
1. 查看日志：`logs/fortune_analysis_9005.log`
2. 运行测试脚本：`python scripts/test_coze_config.py`
3. 检查 Coze 平台文档：https://www.coze.cn/docs

---

**配置完成后，重启服务即可使用 AI 增强功能！**


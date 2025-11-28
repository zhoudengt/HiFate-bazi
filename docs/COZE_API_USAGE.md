# Coze AI 分析功能使用说明

## 框架架构

基于 Coze API 的 AI 分析框架，支持用户在 Coze 平台可视化配置服务，然后通过 API 调用。

## 目录结构

```
src/
  ai/
    __init__.py
    bazi_ai_analyzer.py          # Coze AI分析器核心类

server/
  services/
    bazi_ai_service.py           # Coze AI分析服务层
  api/
    v1/
      bazi_ai.py                 # Coze AI分析API接口
```

## 配置 Coze 服务

### 1. 在 Coze 平台创建 Bot

1. 访问 [Coze 平台](https://www.coze.cn)
2. 注册并登录账户
3. 创建新的 Bot（智能体）
4. 在 Bot 中配置工作流和提示词

### 2. 获取必要信息

- **Access Token**: 在 Coze 平台获取 API Access Token
- **Bot ID**: 创建 Bot 后获得的 Bot ID

### 3. 可视化配置服务

在 Coze 平台可以：
- 配置工作流节点
- 设置提示词模板
- 配置输入输出格式
- 设置响应规则

## 环境变量设置

```bash
# 设置 Coze Access Token
export COZE_ACCESS_TOKEN="pat-your-access-token"

# 设置 Coze Bot ID
export COZE_BOT_ID="your-bot-id"
```

## API 接口调用

### 接口地址
`POST /api/v1/bazi/ai-analyze`

### 请求参数

```json
{
  "solar_date": "1990-05-15",           // 必填：阳历日期 (YYYY-MM-DD)
  "solar_time": "14:30",                 // 必填：出生时间 (HH:MM)
  "gender": "male",                      // 必填：性别 (male/female)
  "user_question": "请分析我的财运",     // 可选：用户的问题或分析需求
  "access_token": "pat-...",             // 可选：Coze Access Token（不提供则使用环境变量）
  "bot_id": "1234567890",                // 可选：Coze Bot ID（不提供则使用环境变量）
  "api_base": "https://api.coze.cn/v1",  // 可选：Coze API 基础URL
  "include_rizhu_analysis": true         // 可选：是否包含日柱性别分析（默认 true）
}
```

### 响应示例

```json
{
  "success": true,
  "bazi_data": {
    "bazi": {...},                       // 完整的八字数据
    "rizhu": "庚辰",
    "matched_rules": [...]
  },
  "ai_analysis": {
    "success": true,
    "analysis": "根据您提供的八字信息...",  // Coze AI分析结果
    "raw_response": {...},                // Coze 原始响应（供调试）
    "bazi_summary": {
      "rizhu": "庚辰",
      "gender": "male"
    }
  },
  "rizhu_analysis": "【性格与命运解析】\n=..."  // 日柱性别分析文本
}
```

## 使用示例

### 1. 使用 curl

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "user_question": "请分析我的财运和事业",
    "access_token": "pat-...",
    "bot_id": "1234567890"
  }'
```

### 2. 使用 Python

```python
import requests

url = "http://127.0.0.1:8001/api/v1/bazi/ai-analyze"
data = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "user_question": "请分析我的财运和事业",
    "access_token": "pat-...",  # 可选
    "bot_id": "1234567890"      # 可选
}
response = requests.post(url, json=data)
result = response.json()
print(result['ai_analysis']['analysis'])
```

## 数据流程

1. **调用八字接口**: 自动调用 `BaziService.calculate_bazi_full()` 获取八字数据
2. **获取日柱分析**: 调用 `RizhuGenderAnalyzer` 获取日柱性别分析（类似 `print_rizhu_gender_analysis()` 的输出）
3. **格式化数据**: 将八字数据和日柱分析结果格式化为文本
4. **调用 Coze API**: 通过 HTTP POST 请求调用您在 Coze 平台配置的服务
5. **返回结果**: 返回完整的八字数据和 Coze AI 分析结果

## Coze API 调用说明

### API 端点
默认使用：`https://api.coze.cn/v1/chat`

### 请求格式
```json
{
  "bot_id": "your-bot-id",
  "user_id": "bazi_user",
  "query": "用户消息内容",
  "stream": false,
  "chat_id": null
}
```

### 响应格式
Coze 返回的响应格式可能因您的配置而异，代码会自动解析以下格式：
- `data.messages[].content`
- `data.content`
- `content`
- `message`
- `text`
- `answer`

如果格式不匹配，会返回完整的 JSON 响应供调试。

## 自定义 Coze API 端点

如果您的 Coze 服务使用不同的 API 端点，可以在请求中指定 `api_base`：

```json
{
  "api_base": "https://your-custom-api.coze.cn/v1",
  ...
}
```

## 注意事项

1. **API Key**: 需要有效的 Coze Access Token
2. **Bot ID**: 需要在 Coze 平台创建 Bot 并获取 ID
3. **可视化配置**: 在 Coze 平台配置 Bot 的工作流和提示词
4. **响应格式**: 代码会自动适配多种响应格式
5. **容错处理**: 如果 Coze API 调用失败，会返回错误信息但不影响其他功能

## 对现有代码的影响

✅ **零影响**：
- 所有现有接口完全不受影响
- 所有现有服务完全不受影响
- 只是将 AI 后端从 OpenAI 改为 Coze
- 移除了 langchain 依赖，只使用 requests

## 依赖更新

### 移除的依赖
- `langchain`
- `langchain-openai`
- `openai`

### 保留的依赖
- `requests` (已包含在 uvicorn[standard] 中，但明确列出以确保可用)














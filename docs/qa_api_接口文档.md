# QA多轮对话API接口文档

## 概述

QA多轮对话系统提供智能问答功能，支持用户通过预设问题或直接输入问题进行提问，答案以流式方式输出。

## 主要接口

### 1. 开始对话

**接口路径**：`POST /api/v1/qa/start`

**功能**：开始新的对话会话，获取会话ID和初始问题

**请求格式**：
```json
{
  "solar_date": "1990-05-15",    // 出生日期，格式：YYYY-MM-DD
  "solar_time": "14:30",         // 出生时间，格式：HH:MM
  "gender": "male",              // 性别：male(男) 或 female(女)
  "user_id": "user123"            // 用户ID（可选）
}
```

**响应格式**：
```json
{
  "success": true,
  "session_id": "ee88859c-ce1f-4ed4-9b1b-1cc5a984ba26",
  "initial_question": "看了命盘解读，你是最关注哪一方面呢",
  "categories": [
    {
      "key": "career_wealth",
      "name": "事业财富"
    },
    {
      "key": "marriage",
      "name": "婚姻"
    },
    {
      "key": "health",
      "name": "健康"
    },
    {
      "key": "children",
      "name": "子女"
    },
    {
      "key": "liunian",
      "name": "流年运势"
    },
    {
      "key": "yearly_report",
      "name": "年运报告"
    }
  ]
}
```

---

### 2. 提问（流式）⭐ **核心接口**

**接口路径**：`POST /api/v1/qa/ask`

**功能**：用户提问，AI生成答案（流式输出）

**请求格式**：
```json
{
  "session_id": "ee88859c-ce1f-4ed4-9b1b-1cc5a984ba26",  // 会话ID（从/qa/start获取）
  "question": "想了解事业整体运势发展？"                  // 用户问题
}
```

**响应格式**：Server-Sent Events (SSE) 流式响应

**Content-Type**：`text/event-stream`

**响应数据格式**：
```
data: {"type": "progress", "content": "根据您的八字命理分析..."}
data: {"type": "progress", "content": "事业方面..."}
data: {"type": "complete", "content": "完整答案内容"}
data: {"type": "questions_after", "content": ["问题1", "问题2", "问题3"]}
data: {"type": "error", "content": "错误信息"}
```

**响应字段说明**：
- `type: "progress"` - 增量答案内容（流式输出中）
- `type: "complete"` - 完整答案内容（流式输出完成）
- `type: "questions_after"` - 生成的相关问题（3个追问）
- `type: "error"` - 错误信息

**前端处理示例**：
```javascript
const response = await fetch(`${API_CONFIG.baseURL}/qa/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_id: currentSessionId,
        question: question
    })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
let fullAnswer = '';

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6));
            
            if (data.type === 'progress') {
                fullAnswer += data.content || '';
                // 实时更新UI
                updateAnswer(fullAnswer);
            } else if (data.type === 'complete') {
                fullAnswer += data.content || '';
                updateAnswer(fullAnswer, false); // 完成，移除光标
            } else if (data.type === 'questions_after') {
                displayGeneratedQuestions(data.content || []);
            } else if (data.type === 'error') {
                showError(data.content || '生成失败');
            }
        }
    }
}
```

---

### 3. 获取分类问题列表

**接口路径**：`GET /api/v1/qa/categories/{category}/questions`

**功能**：获取指定分类下的预设问题列表

**路径参数**：
- `category` - 分类名称（career_wealth/marriage/health/children/liunian/yearly_report）

**响应格式**：
```json
{
  "success": true,
  "category": "career_wealth",
  "questions": [
    {
      "text": "想了解事业整体运势发展？"
    },
    {
      "text": "想了解财运如何？"
    },
    {
      "text": "想了解事业发展方向？"
    }
  ]
}
```

**替代接口**（POST方式）：
- `POST /api/v1/qa/category-questions`
- 请求体：`{"category": "career_wealth"}`

---

### 4. 获取对话历史

**接口路径**：`GET /api/v1/qa/sessions/{session_id}/history`

**功能**：获取指定会话的对话历史

**路径参数**：
- `session_id` - 会话ID

**响应格式**：
```json
{
  "success": true,
  "session_id": "ee88859c-ce1f-4ed4-9b1b-1cc5a984ba26",
  "history": [
    {
      "question": "想了解事业整体运势发展？",
      "answer": "根据您的八字命理分析...",
      "intent": "career_wealth",
      "category": "career_wealth",
      "generated_questions": ["问题1", "问题2", "问题3"],
      "created_at": "2025-01-15T10:30:00"
    }
  ]
}
```

---

## 接口调用流程

```
1. 用户输入生辰信息
   ↓
2. 调用 POST /api/v1/qa/start
   ↓ 获取 session_id 和初始问题
3. 用户选择分类或直接提问
   ↓
4. 调用 GET /api/v1/qa/categories/{category}/questions（可选）
   ↓ 获取预设问题列表
5. 用户选择预设问题或输入问题
   ↓
6. 调用 POST /api/v1/qa/ask（流式）
   ↓ 实时接收答案
7. 显示答案和生成的追问
   ↓
8. 用户可以继续提问（重复步骤5-7）
```

---

## 技术要点

### 1. 流式输出处理

- **格式**：Server-Sent Events (SSE)
- **Content-Type**：`text/event-stream`
- **数据格式**：每行以 `data: ` 开头，后跟JSON字符串
- **处理方式**：使用 `fetch` + `ReadableStream` + `getReader()` 逐行解析

### 2. 预设问题

- 从分类问题列表中选择
- 点击后直接调用 `/qa/ask` 接口
- 支持多个分类的预设问题

### 3. 直接输入提问

- 用户在输入框中输入问题
- 提交后调用 `/qa/ask` 接口
- 支持回车键快速提交

### 4. 生成的追问

- 每次回答后，AI会生成3个相关问题
- 用户可以直接点击追问继续对话
- 追问问题存储在 `questions_after` 字段中

---

## 错误处理

**错误响应格式**：
```json
{
  "success": false,
  "error": "错误信息描述"
}
```

**流式错误格式**：
```
data: {"type": "error", "content": "错误信息"}
```

**常见错误**：
- `session_id` 不存在或已过期
- 生辰信息格式错误
- 问题为空或格式不正确
- 服务内部错误

---

## 注意事项

1. **会话管理**：`session_id` 在开始对话时获取，后续所有提问都需要携带此ID
2. **流式输出**：答案以流式方式输出，前端需要实时更新UI
3. **追问生成**：每次回答后会生成3个追问，建议在UI中展示供用户选择
4. **多轮对话**：系统支持多轮对话，会记住之前的对话上下文
5. **意图识别**：系统会自动识别用户问题意图，匹配相应的命理分析

---

## 开发团队参考

**核心接口**：`POST /api/v1/qa/ask`（流式）

**关键点**：
- 必须使用SSE格式处理流式响应
- 需要实时更新UI显示增量内容
- 处理完成后显示生成的追问问题
- 错误处理要友好，不中断用户流程

**前端实现建议**：
- 使用 `fetch` + `ReadableStream` 处理SSE
- 实时更新答案显示区域
- 添加流式输出光标动画
- 显示生成的追问问题供用户选择


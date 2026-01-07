# smart-analyze-stream gRPC-Web 网关返回值说明

## 返回值格式

通过 gRPC-Web 网关调用时，返回的是 JSON 格式，所有流式数据会被收集后统一返回。

### 场景1返回示例（点击选择项）

```json
{
  "success": true,
  "data": {
    "brief_response": "根据您的八字分析，您的事业运势在2024年会有较好的发展机会...",
    "preset_questions": [
      "我的八字适合从事什么类型的行业或职业？",
      "今年事业发展是否有贵人相助？",
      "未来三年我的事业能否有晋升机会？"
    ],
    "performance": {
      "total_time_ms": 48068,
      "stages": [...]
    },
    "last_status": {
      "stage": "preset_questions",
      "message": "正在生成预设问题..."
    }
  },
  "stream_content": "根据您的八字分析，您的事业运势在2024年会有较好的发展机会..."
}
```

### 场景2返回示例（点击预设问题）

```json
{
  "success": true,
  "data": {
    "basic_analysis": {
      "intent": {...},
      "bazi_info": {...},
      "matched_rules_count": 10
    },
    "related_questions": [
      "问题1",
      "问题2"
    ],
    "performance": {
      "total_time_ms": 95627,
      "stages": [...]
    },
    "last_status": {
      "stage": "related_questions",
      "message": "正在生成相关问题..."
    },
    "llm_completed": true
  },
  "stream_content": "所有llm_chunk内容合并后的完整文本"
}
```

## 字段说明

### 通用字段

- `success` (boolean): 是否成功
- `data` (object): 结构化数据
- `stream_content` (string): 所有流式内容块的合并

### data 字段说明

#### 场景1特有字段

- `brief_response` (string): 简短答复的完整内容（来自 `brief_response_end` 事件）
- `preset_questions` (array): 预设问题列表（来自 `preset_questions` 事件）

#### 场景2特有字段

- `basic_analysis` (object): 基础分析结果（来自 `basic_analysis` 事件）
- `related_questions` (array): 相关问题列表（来自 `related_questions` 事件）
- `llm_completed` (boolean): LLM 是否完成（来自 `llm_end` 事件）

#### 通用字段

- `performance` (object): 性能数据（来自 `performance` 事件）
- `last_status` (object): 最后一个状态信息（来自 `status` 事件）

## 如果字段为 null

如果 `data` 或 `stream_content` 为 `null`，可能的原因：

1. **流式数据还未收集完成**：gRPC-Web 网关需要等待所有数据收集完成后才返回（可能需要较长时间）
2. **没有对应的事件**：如果流中没有发送对应的事件，字段就是 `null`
   - 场景1如果没有 `brief_response_chunk` 事件，`stream_content` 就是 `null`
   - 场景2如果没有 `llm_chunk` 事件，`stream_content` 就是 `null`
3. **解析错误**：SSE 消息格式不正确导致解析失败

## 使用示例

### JavaScript 处理返回值

```javascript
// 调用 gRPC-Web 网关
const result = await api.post('/smart-fortune/smart-analyze-stream', {
    category: '事业财富',
    year: 1990,
    month: 5,
    day: 15,
    hour: 14,
    gender: 'male',
    user_id: 'test_user_001'
});

// 检查是否成功
if (result.success) {
    // 获取简短答复
    if (result.data && result.data.brief_response) {
        console.log('简短答复:', result.data.brief_response);
    }
    
    // 获取预设问题
    if (result.data && result.data.preset_questions) {
        console.log('预设问题:', result.data.preset_questions);
    }
    
    // 获取流式内容
    if (result.stream_content) {
        console.log('流式内容:', result.stream_content);
    }
    
    // 获取性能数据
    if (result.data && result.data.performance) {
        console.log('总耗时:', result.data.performance.total_time_ms, 'ms');
    }
} else {
    console.error('错误:', result.error);
}
```

## 推荐使用方式

**前端实时显示**：使用 GET 请求 + EventSource，可以实时看到流式输出，无需等待所有数据收集完成。

**后端处理**：使用 gRPC-Web 网关，等待所有数据收集完成后统一处理。



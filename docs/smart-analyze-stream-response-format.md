# smart-analyze-stream 接口返回值说明

## 直接 GET 请求返回值（SSE 流式）

直接使用 GET 请求时，返回的是 SSE (Server-Sent Events) 流式响应，格式如下：

```
event: status
data: {"stage": "bazi", "message": "正在计算八字..."}

event: brief_response_start
data: {}

event: brief_response_chunk
data: {"content": "根据您的八字分析"}

event: brief_response_chunk
data: {"content": "，您的事业运势..."}

event: brief_response_end
data: {"content": "根据您的八字分析，您的事业运势在2024年会有较好的发展机会..."}

event: preset_questions
data: {"questions": ["问题1", "问题2", "问题3"]}

event: performance
data: {"total_time_ms": 1234, "stages": [...]}

event: end
data: {}
```

**前端使用 EventSource 监听这些事件即可。**

## gRPC-Web 网关返回值（JSON 格式）

通过 gRPC-Web 网关调用时，返回的是 JSON 格式，所有流式数据会被收集后统一返回：

```json
{
  "success": true,
  "data": {
    "brief_response": "完整的简短答复内容",
    "preset_questions": ["问题1", "问题2", "问题3"],
    "performance": {
      "total_time_ms": 1234,
      "stages": [...]
    },
    "last_status": {
      "stage": "preset_questions",
      "message": "正在生成预设问题..."
    }
  },
  "stream_content": "所有brief_response_chunk内容合并后的完整文本"
}
```

### 字段说明

- `success`: 是否成功
- `data`: 结构化数据
  - `brief_response`: 简短答复的完整内容（来自 `brief_response_end` 事件）
  - `preset_questions`: 预设问题列表（来自 `preset_questions` 事件）
  - `performance`: 性能数据（来自 `performance` 事件）
  - `last_status`: 最后一个状态信息（来自 `status` 事件）
- `stream_content`: 所有流式内容块的合并（来自所有 `brief_response_chunk` 事件）

### 如果字段为 null

如果 `data` 或 `stream_content` 为 `null`，可能的原因：

1. **流式数据还未收集完成**：gRPC-Web 网关需要等待所有数据收集完成后才返回
2. **没有对应的事件**：如果流中没有发送 `brief_response_chunk` 或 `preset_questions` 事件，对应字段就是 `null`
3. **解析错误**：SSE 消息格式不正确导致解析失败

### 使用建议

1. **前端实时显示**：使用 GET 请求 + EventSource，可以实时看到流式输出
2. **后端处理**：使用 gRPC-Web 网关，等待所有数据收集完成后统一处理
3. **检查字段**：使用前检查字段是否为 `null`：
   ```javascript
   if (result.data && result.data.brief_response) {
       // 使用 brief_response
   }
   if (result.stream_content) {
       // 使用 stream_content
   }
   ```



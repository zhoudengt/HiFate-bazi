# smart-analyze-stream 接口调用参考

## 前端调用代码

**前端开发者请查看：** `docs/smart-analyze-stream-frontend-code.md`

包含完整的 JavaScript/HTML 代码示例，可直接复制使用。

---

## curl 命令参考（后端测试用）

## 正确的 curl 命令

### ⭐ 方法1：直接 GET 请求（推荐，可直接复制执行）

**直接复制下面的命令执行即可，无需任何额外处理！**

#### 场景1：点击选择项（需要生辰信息）

**生产环境：**
```bash
curl -N "http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?category=%E4%BA%8B%E4%B8%9A%E8%B4%A2%E5%AF%8C&year=1990&month=5&day=15&hour=14&gender=male&user_id=test_user_001"
```

**本地环境：**
```bash
curl -N "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream?category=%E4%BA%8B%E4%B8%9A%E8%B4%A2%E5%AF%8C&year=1990&month=5&day=15&hour=14&gender=male&user_id=test_user_001"
```

#### 场景2：点击预设问题（从会话缓存获取生辰信息）

**生产环境：**
```bash
curl -N "http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?category=%E4%BA%8B%E4%B8%9A%E8%B4%A2%E5%AF%8C&question=%E6%88%91%E4%BB%8A%E5%B9%B4%E7%9A%84%E4%BA%8B%E4%B8%9A%E8%BF%90%E5%8A%BF%E5%A6%82%E4%BD%95%EF%BC%9F&user_id=test_user_001"
```

**本地环境：**
```bash
curl -N "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream?category=%E4%BA%8B%E4%B8%9A%E8%B4%A2%E5%AF%8C&question=%E6%88%91%E4%BB%8A%E5%B9%B4%E7%9A%84%E4%BA%8B%E4%B8%9A%E8%BF%90%E5%8A%BF%E5%A6%82%E4%BD%95%EF%BC%9F&user_id=test_user_001"
```

#### 默认场景（兼容旧接口）

**生产环境：**
```bash
curl -N "http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?question=%E6%88%91%E4%BB%8A%E5%B9%B4%E7%9A%84%E4%BA%8B%E4%B8%9A%E8%BF%90%E5%8A%BF%E5%A6%82%E4%BD%95%EF%BC%9F&year=1990&month=5&day=15&hour=14&gender=male&user_id=test_user_001"
```

**本地环境：**
```bash
curl -N "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream?question=%E6%88%91%E4%BB%8A%E5%B9%B4%E7%9A%84%E4%BA%8B%E4%B8%9A%E8%BF%90%E5%8A%BF%E5%A6%82%E4%BD%95%EF%BC%9F&year=1990&month=5&day=15&hour=14&gender=male&user_id=test_user_001"
```

---

### 方法1.5：使用 Python 自动生成 URL（如果需要修改参数）

**场景1：点击选择项**
```bash
python3 -c "import urllib.parse; params = {'category': '事业财富', 'year': 1990, 'month': 5, 'day': 15, 'hour': 14, 'gender': 'male', 'user_id': 'test_user_001'}; print('http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' + urllib.parse.urlencode(params, encoding='utf-8'))"
```

**场景2：点击预设问题**
```bash
python3 -c "import urllib.parse; params = {'category': '事业财富', 'question': '我今年的事业运势如何？', 'user_id': 'test_user_001'}; print('http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' + urllib.parse.urlencode(params, encoding='utf-8'))"
```

---

### 方法2：使用 gRPC-Web 网关（POST 请求）

**注意**：gRPC-Web 网关会收集所有流式数据后才返回，需要等待较长时间。推荐使用 GET 请求（方法1）。

**使用完整脚本（推荐，已测试可用）：**
```bash
# 生产环境
python3 scripts/test_grpc_web_smart_analyze_stream.py http://8.210.52.217:8001

# 本地环境
python3 scripts/test_grpc_web_smart_analyze_stream.py http://localhost:8001

# 或指定其他服务器
python3 scripts/test_grpc_web_smart_analyze_stream.py <服务器地址>
```

**脚本位置：** `scripts/test_grpc_web_smart_analyze_stream.py`

**脚本功能：**
- ✅ 完整实现 gRPC-Web protobuf 编码
- ✅ 支持场景1（点击选择项）和场景2（点击预设问题）
- ✅ 自动处理响应解析（支持 JSON 和二进制格式）
- ✅ 包含完整的错误处理和超时处理
- ✅ 已在生产环境测试通过

## 参数说明

### 场景1参数（点击选择项）
- `category` (必填): 分类，如 "事业财富"、"健康"、"婚姻" 等
- `year` (必填): 出生年份
- `month` (必填): 出生月份
- `day` (必填): 出生日期
- `hour` (可选): 出生时辰，默认 12
- `gender` (必填): 性别，male 或 female
- `user_id` (必填): 用户ID

### 场景2参数（点击预设问题）
- `category` (必填): 分类
- `question` (必填): 问题内容
- `user_id` (必填): 用户ID
- （生辰信息从会话缓存获取）

### 默认场景参数（兼容旧接口）
- `question` (必填): 用户问题
- `year` (必填): 出生年份
- `month` (必填): 出生月份
- `day` (必填): 出生日期
- `hour` (可选): 出生时辰，默认 12
- `gender` (必填): 性别
- `user_id` (可选): 用户ID

## 返回值格式

### 直接 GET 请求（SSE 流式）

接口返回 SSE (Server-Sent Events) 流式响应，格式如下：

**场景1事件：**
```
event: status
data: {"stage": "bazi", "message": "正在计算八字..."}

event: brief_response_start
data: {}

event: brief_response_chunk
data: {"content": "根据您的八字分析"}

event: brief_response_end
data: {"content": "完整的简短答复内容"}

event: preset_questions
data: {"questions": ["问题1", "问题2", "问题3"]}

event: performance
data: {"total_time_ms": 1234, "stages": [...]}

event: end
data: {}
```

**场景2事件：**
```
event: basic_analysis
data: {"intent": {...}, "bazi_info": {...}, "matched_rules_count": 10}

event: status
data: {"stage": "llm", "message": "正在生成深度解读..."}

event: llm_start
data: {}

event: llm_chunk
data: {"content": "根据您的八字分析"}

event: llm_end
data: {}

event: related_questions
data: {"questions": ["问题1", "问题2"]}

event: performance
data: {"total_time_ms": 1234, "stages": [...]}

event: end
data: {}
```

### gRPC-Web 网关（JSON 格式）

通过 gRPC-Web 网关调用时，返回 JSON 格式，所有流式数据会被收集后统一返回：

**场景1返回示例：**
```json
{
  "success": true,
  "data": {
    "brief_response": "完整的简短答复内容",
    "preset_questions": ["问题1", "问题2", "问题3"],
    "performance": {"total_time_ms": 1234, "stages": [...]},
    "last_status": {"stage": "preset_questions", "message": "正在生成预设问题..."}
  },
  "stream_content": "所有brief_response_chunk内容合并后的完整文本"
}
```

**场景2返回示例：**
```json
{
  "success": true,
  "data": {
    "basic_analysis": {"intent": {...}, "bazi_info": {...}},
    "related_questions": ["问题1", "问题2"],
    "performance": {"total_time_ms": 1234, "stages": [...]},
    "last_status": {"stage": "related_questions", "message": "正在生成相关问题..."},
    "llm_completed": true
  },
  "stream_content": "所有llm_chunk内容合并后的完整文本"
}
```

**字段说明：**
- `success`: 是否成功
- `data`: 结构化数据（可能包含 `brief_response`, `preset_questions`, `related_questions`, `basic_analysis`, `performance`, `last_status` 等）
- `stream_content`: 所有流式内容块的合并（来自 `brief_response_chunk` 或 `llm_chunk` 事件）

**注意：** 如果某些字段为 `null`，说明对应的流式事件没有发送或解析失败。

## 常见问题

### Q: 返回 "Invalid HTTP request received"
**A:** 可能是 URL 编码问题，使用上面的正确编码命令，或使用 Python 自动生成 URL。

### Q: gRPC-Web 返回 "Not Found" 或解析错误
**A:** 
1. 检查路径是否正确：`/api/grpc-web/frontend.gateway.FrontendGateway/Call`（不是 `/api/v1/grpc-web/...`）
2. 必须使用 `Content-Type: application/grpc-web+proto`（不是 `application/json`）
3. 推荐使用 GET 请求（方法1），更简单直接
4. 如需使用 gRPC-Web，请使用完整脚本：`python3 scripts/test_grpc_web_smart_analyze_stream.py`

### Q: 没有返回数据
**A:** 
1. 检查服务器是否运行：`curl http://8.210.52.217:8001/health`
2. 检查参数是否完整
3. 使用 `-v` 参数查看详细错误信息：`curl -N -v "URL"`

### Q: 如何查看流式输出
**A:** 使用 `-N` 参数禁用缓冲，实时显示流式数据：
```bash
curl -N "URL"
```
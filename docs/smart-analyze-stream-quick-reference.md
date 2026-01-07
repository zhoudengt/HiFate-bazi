# smart-analyze-stream 接口快速参考

## 问题诊断

如果接口没有返回值，请按以下步骤排查：

### 1. 运行诊断脚本
```bash
python3 scripts/diagnose_smart_analyze_stream.py
```

### 2. 检查服务器状态
```bash
# 生产环境
curl http://8.210.52.217:8001/health

# 本地环境
curl http://localhost:8001/health
```

### 3. 使用正确的 URL 编码

**重要**：中文参数必须正确 URL 编码！

#### 方法1：使用 Python 自动生成（推荐）
```bash
python3 -c "
import urllib.parse
params = {
    'category': '事业财富',
    'year': 1990,
    'month': 5,
    'day': 15,
    'hour': 14,
    'gender': 'male',
    'user_id': 'test_user_001'
}
print('http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?' + urllib.parse.urlencode(params, encoding='utf-8'))
"
```

#### 方法2：使用测试脚本（最简单）
```bash
./scripts/test_smart_analyze_stream.sh
```

## 快速测试命令

### 场景1：点击选择项（生产环境）

```bash
curl -N "http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?category=%E4%BA%8B%E4%B8%9A%E8%B4%A2%E5%AF%8C&year=1990&month=5&day=15&hour=14&gender=male&user_id=test_user_001"
```

### 场景2：点击预设问题（生产环境）

```bash
curl -N "http://8.210.52.217:8001/api/v1/smart-fortune/smart-analyze-stream?category=%E4%BA%8B%E4%B8%9A%E8%B4%A2%E5%AF%8C&question=%E6%88%91%E4%BB%8A%E5%B9%B4%E7%9A%84%E4%BA%8B%E4%B8%9A%E8%BF%90%E5%8A%BF%E5%A6%82%E4%BD%95%EF%BC%9F&user_id=test_user_001"
```

### 使用 gRPC-Web 网关（POST 请求）

**⚠️ 重要**：gRPC-Web 网关需要 protobuf 编码的请求体，不能直接使用 JSON！

**推荐**：直接使用 GET 请求（方法1），更简单且无需处理 protobuf 编码。

如需使用 gRPC-Web 网关，请使用 Python 脚本：
```bash
python3 scripts/test_grpc_web_smart_analyze_stream.py http://8.210.52.217:8001
```

## 接口信息

- **路径**: `/api/v1/smart-fortune/smart-analyze-stream`
- **方法**: GET（直接调用）或 POST（通过 gRPC-Web 网关）
- **返回格式**: SSE (Server-Sent Events) 流式响应
- **gRPC-Web 端点**: `/smart-fortune/smart-analyze-stream`（已注册）

## 返回值示例

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
data: {"total_time_ms": 1234}

event: end
data: {}
```

## 常见错误

### "Invalid HTTP request received"
- **原因**: URL 编码问题或服务器未运行
- **解决**: 使用 Python 生成正确编码的 URL，或使用 gRPC-Web 网关

### "Not Found" (gRPC-Web)
- **原因**: 端点未注册
- **解决**: 运行诊断脚本检查端点注册情况

### 没有返回数据
- **原因**: 服务器未运行、参数不完整或网络问题
- **解决**: 
  1. 检查服务器状态
  2. 验证参数完整性
  3. 使用 `-v` 参数查看详细错误

## 相关文档

- 详细 curl 命令参考: `docs/smart-analyze-stream-curl-commands.md`
- 诊断脚本: `scripts/diagnose_smart_analyze_stream.py`
- 测试脚本: `scripts/test_smart_analyze_stream.sh`

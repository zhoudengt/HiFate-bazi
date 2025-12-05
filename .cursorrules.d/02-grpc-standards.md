# gRPC 交互规范 【重要】

## 架构概览
```
┌─────────────┐    gRPC-Web     ┌─────────────────┐     gRPC      ┌─────────────┐
│   前端      │ ───────────────→ │  Web 服务      │ ─────────────→ │  微服务     │
│  (Browser)  │                 │  (Port 8001)   │               │ (9001-9010) │
└─────────────┘                 └─────────────────┘               └─────────────┘
      │                                │                                │
      │                                ↓                                │
      │                         ┌─────────────┐                         │
      │                         │   MySQL     │←────────────────────────┘
      │                         │   Redis     │
      └─────────────────────────└─────────────┘
```

## 前端调用规范
```javascript
// ✅ 正确：使用 gRPC-Web 网关
const result = await api.post('/bazi/formula-analysis', {
    solar_date: '2025-01-15',
    solar_time: '12:00',
    gender: 'male'
});

// ❌ 错误：直接使用 REST API
const result = await fetch('/api/v1/bazi/formula-analysis', {...});
```

## 🔴 前端错误处理规范 【必须遵守】

### 1. 错误处理必须显示UI区域

**要求**：
- 所有错误处理函数必须同时更新内容和显示状态
- 如果UI区域初始为 `display:none`，错误处理时必须显示

**错误示例**：
```javascript
// ❌ 错误：只更新内容，不显示区域
function displayError(message) {
    const content = document.getElementById('content');
    content.innerHTML = `<div class="error">${message}</div>`;
    // 缺少：section.style.display = 'block';
}
```

**正确示例**：
```javascript
// ✅ 正确：同时更新内容和显示状态
function displayError(message) {
    const section = document.getElementById('section');
    const content = document.getElementById('content');
    
    section.style.display = 'block';  // 显示区域
    content.innerHTML = `<div class="error">${message}</div>`;
    section.scrollIntoView({ behavior: 'smooth' });  // 滚动到错误区域
}
```

### 2. 关键阶段提前显示UI区域

**要求**：
- 在进入关键处理阶段时，提前显示相关UI区域
- 确保用户能看到处理进度和结果

**示例**：
```javascript
eventSource.addEventListener('status', function(e) {
    const data = JSON.parse(e.data);
    updateProgress(data.stage, data.message);
    
    // ⭐ 当进入关键阶段时，提前显示相关UI区域
    if (data.stage === 'llm') {
        document.getElementById('llmAnalysisSection').style.display = 'block';
    }
});
```

### 3. 错误处理与正常流程保持一致

**要求**：
- 错误处理函数的UI操作必须与正常流程函数一致
- 确保错误场景下用户体验不中断

**检查清单**：
- [ ] 错误处理函数是否显示相关UI区域
- [ ] 是否在关键阶段提前显示UI区域
- [ ] 错误处理逻辑是否与正常流程一致
- [ ] 是否添加了用户可见的错误提示
- [ ] 是否测试了所有错误场景

**相关复盘**：见 `docs/问题复盘-AI深度解读区域不显示.md`

## 后端注册规范
```python
# 1. 在 server/api/v1/ 下创建 REST API
@router.post("/bazi/new-feature")
async def new_feature(request: NewFeatureRequest):
    ...

# 2. 在 server/api/grpc_gateway.py 注册 gRPC 端点（必须！）
@_register("/bazi/new-feature")
async def _handle_new_feature(payload: Dict[str, Any]):
    request_model = NewFeatureRequest(**payload)
    return await new_feature(request_model)
```

## 服务间调用规范
```python
# ✅ 正确：使用 gRPC 客户端
from src.clients.bazi_core_client_grpc import BaziCoreClientGrpc
result = BaziCoreClientGrpc.calculate_bazi(...)

# ❌ 错误：直接 HTTP 调用
import requests
result = requests.get('http://localhost:9001/api/...')
```


# 性能监控详细规范

> 本文档从 `.cursorrules` 提取，包含性能监控的完整规范。详见 `.cursorrules` 核心规范章节。

## 核心原则

> **所有智能运势分析流程必须记录端到端日志和性能监控，确保每个阶段的响应时间可控。**

### 📋 性能监控要求

**必须监控的阶段**：
1. **意图识别** (`intent_recognition`) - 目标：< 100ms
2. **八字计算** (`bazi_calculation`) - 目标：< 50ms
3. **规则匹配** (`rule_matching`) - 目标：< 200ms
4. **流年大运分析** (`fortune_context`) - 目标：< 1000ms（可选）
5. **LLM深度解读** (`llm_analysis`) - 目标：< 2000ms（可选）
6. **生成响应文本** (`response_generation`) - 目标：< 50ms

### 🔧 实现方式

**使用 `PerformanceMonitor` 工具类**：

```python
from server.utils.performance_monitor import PerformanceMonitor

# 初始化监控器
monitor = PerformanceMonitor()

# 使用上下文管理器记录阶段
with monitor.stage("intent_recognition", "意图识别", question=question):
    intent_result = intent_client.classify(question=question)
    monitor.add_metric("intent_recognition", "intents_count", len(intent_result.get("intents", [])))

# 输出性能摘要
monitor.log_summary()

# 在响应中包含性能摘要
result = {
    "success": True,
    "response": response_text,
    "performance": monitor.get_summary()  # ⭐ 添加性能摘要
}
```

### 📊 性能摘要格式

性能摘要包含以下信息：
- `total_duration_ms`: 总耗时（毫秒）
- `stages`: 各阶段详细信息（耗时、成功/失败、指标等）
- `bottlenecks`: 性能瓶颈（>1秒的阶段）
- `failed_stages`: 失败的阶段

### ✅ 检查清单

每次修改智能运势分析相关代码时，必须检查：

- [ ] 是否使用 `PerformanceMonitor` 记录所有阶段
- [ ] 是否在响应中包含性能摘要
- [ ] 是否输出性能摘要到日志
- [ ] 是否识别并记录性能瓶颈（>1秒）
- [ ] 是否记录失败的阶段和错误信息

### 🚨 性能优化建议

**常见性能瓶颈**：
1. **LLM深度解读**：通常是最慢的阶段（500-2000ms），建议：
   - 使用流式输出提升用户体验
   - 考虑缓存常见问题的结果
   - 优化提示词减少响应时间

2. **流年大运分析**：可能较慢（500-1000ms），建议：
   - 仅在需要时启用（`include_fortune_context=True`）
   - 优化数据库查询
   - 考虑缓存计算结果

3. **规则匹配**：可能较慢（100-300ms），建议：
   - 优化规则匹配算法
   - 使用索引加速数据库查询
   - 考虑缓存匹配结果

### 📝 日志输出示例

```
================================================================================
[PerformanceMonitor] [req_1234567890] 性能摘要
================================================================================
总耗时: 2249ms (2.249s)
阶段数: 6

各阶段耗时:
  ✅ intent_recognition: 50ms (intents_count: 1, confidence: 0.85, method: local_model)
  ✅ bazi_calculation: 23ms
  ✅ rule_matching: 155ms (matched_rules_count: 25, rule_types_count: 1)
  ✅ fortune_context: 803ms (liunian_count: 3)
  ✅ llm_analysis: 1202ms (analysis_length: 500)
  ✅ response_generation: 12ms (response_length: 2000)

⚠️ 性能瓶颈（>1秒）:
  - llm_analysis: 1202ms - LLM深度解读
================================================================================
```

### 🎯 性能目标

| 阶段 | 目标耗时 | 警告阈值 | 说明 |
|------|---------|---------|------|
| 意图识别 | < 100ms | > 200ms | 使用混合架构，大部分请求应 < 100ms |
| 八字计算 | < 50ms | > 100ms | 本地计算，应该很快 |
| 规则匹配 | < 200ms | > 500ms | 数据库查询，可能较慢 |
| 流年大运 | < 1000ms | > 2000ms | 可选功能，可能较慢 |
| LLM深度解读 | < 2000ms | > 5000ms | 可选功能，通常最慢 |
| 生成响应 | < 50ms | > 100ms | 文本生成，应该很快 |

**总耗时目标**：
- 不包含流年大运和LLM：< 500ms
- 包含流年大运：< 2000ms
- 包含流年大运和LLM：< 5000ms

---

**核心要点**：
- **所有智能运势分析流程必须使用 `PerformanceMonitor` 记录性能**
- **性能摘要必须包含在API响应中**
- **必须识别并记录性能瓶颈（>1秒）**
- **必须记录失败的阶段和错误信息**

---


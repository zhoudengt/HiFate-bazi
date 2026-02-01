# 流式接口各环节耗时测试工具（Stream Profiler）

**正式名称**：流式接口各环节耗时测试工具（英文：Stream Profiler）

**代码路径**：`tools/stream_profiler/`

独立于 server/api 的纯客户端工具，通过 HTTP 调用流式接口并解析 SSE，测量各阶段时间与内容体量。**不修改、不依赖**任何 server/core 代码，不影响流式接口运行时性能。用于后续各流式接口的性能测试与优化验证。

## 文档与规范同步约定

**工具修改时，须同步更新以下文档**：

- 本文件 `tools/stream_profiler/README.md`：使用方式、指标定义、参数说明
- `standards/04_测试规范.md` 中「十一、流式接口性能测试工具」：工具名称、路径、命令、指标说明
- `standards/llm-development.md` 中流式接口优化规范相关段落：若工具能力或命令变更，须更新引用

新增指标、新增 CLI 参数、或端点列表变更时，应同步更新上述文档。

## 目录与依赖

- **目录**：`tools/stream_profiler/`，与 `server/`、`core/` 解耦。
- **依赖**：仅标准库 + `requests`。禁止 `from server.*`、`from core.*`、`from services.*`。

## 指标说明（按接口阶段理解）

报告里用「阶段」来对应接口内部流程，便于看结论：

| 阶段 | 报告中的指标名 | 含义 |
|------|----------------|------|
| 从统一编排获取数据 | **编排取数** | 从请求开始到收到首条「结构化数据」的时间（接口从 BaziDataOrchestrator 取数并返回首包） |
| 数据交给大模型 → 大模型开始输出 | **大模型首字延迟** | 从首包(data)到首条流式内容(progress)的时间（含：数据交 LLM、LLM 计算、首字返回） |
| 大模型逐字/逐段反馈 | **大模型流式输出** | 从首条 progress 到 complete 的时间（大模型持续输出内容的耗时） |
| 整次请求结束 | **总耗时** | 从请求开始到收到 complete 的时间 |

**结论怎么看**：报告末尾有「结论」小节，会写：编排取数 Xs、大模型首字延迟 Xs、大模型流式输出 Xs、总耗时 Xs。若大模型首字延迟和总耗时都很短，多为缓存命中；若大模型首字延迟较长（如十几秒），多为冷请求（真实调用了大模型）。

**喜神忌神优化效果**：当本次测试包含「喜神忌神」时，会额外拉取测试接口一次，在报告中增加「喜神忌神优化（LLM 入参体量）」：**响应时间**见上表总耗时；**入参体量**为优化前（完整 JSON）字符数、优化后（描述文）字符数及降低百分比。

原始指标（T_data、T_first_progress、T_llm_first_token、T_complete 等）仍在报告「原始指标说明」中保留，供排查用。

## 使用方式

在项目根目录执行：

```bash
# 测所有配置的流式接口，各 1 次，报告打屏
python -m tools.stream_profiler.cli --base-url http://localhost:8001

# 只测五行占比流式接口，测 3 次，输出 Markdown 文件
python -m tools.stream_profiler.cli --base-url http://localhost:8001 --endpoint /api/v1/bazi/wuxing-proportion/stream --runs 3 --output report.md

# 按接口名称过滤
python -m tools.stream_profiler.cli --base-url http://localhost:8001 --endpoint 五行占比 --runs 2

# 输出 JSON 便于后续脚本处理
python -m tools.stream_profiler.cli --base-url http://localhost:8001 --format json --output report.json

# 指定超时与输出路径
python -m tools.stream_profiler.cli --base-url http://localhost:8001 --timeout 60 --output stream_report.md
```

### 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| --base-url | API 基准 URL | http://localhost:8001 |
| --endpoint | 只测该接口（path 或 name） | 不指定则测全部非 skip 接口 |
| --runs | 每个接口测试次数（多次时取平均） | 1 |
| --timeout | 单次请求超时秒数 | 120 |
| --output, -o | 报告输出文件 | 不指定则打印到 stdout |
| --format | 输出格式：markdown / json | markdown |
| --with-image | 包含需要上传图片的接口 | 默认跳过 |

## 接口列表

端点定义在 `endpoints.py` 中，与 `scripts/evaluation/stream_ttft_report.py` 的流式接口列表对齐（人工维护，不 import 该文件）。默认包含：总评分析、事业财富、感情婚姻、健康分析、子女学习、五行占比、喜神忌神、每日运势日历、行动建议流式、年运报告、智能分析流等；需要上传图片的接口默认跳过，可用 `--with-image` 包含。

## 与现有脚本的关系

- **stream_ttft_report.py**：只测「第一条 data 行」的 TTFT，不区分 type。
- **本工具**：测 data / progress / complete / error 的首次出现时间及 content 体量，用于分析数据准备 vs LLM 首 token vs 总耗时等环节。
- 二者职责不同，可并存；本工具不依赖、不替换 stream_ttft_report，也不被服务端引用。

## 喜神忌神优化效果测试（响应时间 + 入参体量）

要实测「**多长时间响应**」和「**输入从多少降到了多少**」：

1. **响应时间**（冷请求 vs 缓存命中）  
   用本工具测喜神忌神流式接口两次，看报告里的「总耗时」等：
   ```bash
   python -m tools.stream_profiler.cli --base-url http://localhost:8001 --endpoint 喜神忌神 --runs 2 -o xishen_report.md
   ```
   第一次多为冷请求（总耗时长），第二次多为缓存命中（总耗时短）。若需分开看两次，可执行两次并各写一个文件。

2. **入参体量**（优化前 vs 优化后）  
   调喜神忌神**测试接口**，响应里会带优化前/后字符数：
   ```bash
   curl -s -X POST "http://localhost:8001/api/v1/bazi/xishen-jishen/test" \
     -H "Content-Type: application/json" \
     -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male","calendar_type":"solar"}' | jq '.formatted_data_length, .formatted_data_length_optimized'
   ```
   - `formatted_data_length`：优化前（完整 JSON）字符数  
   - `formatted_data_length_optimized`：优化后（描述文）字符数  
   **结论**：入参从「优化前」降到「优化后」，降低比例 = `(1 - 优化后/优化前) * 100%`。

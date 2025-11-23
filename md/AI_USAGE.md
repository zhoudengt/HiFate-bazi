# AI 分析功能使用说明

## 框架架构

基于 LangChain 架构的 AI 分析框架，将八字计算结果传递给 AI 进行智能分析。

## 目录结构

```
src/
  ai/
    __init__.py
    bazi_ai_analyzer.py          # AI分析器核心类（基于LangChain）

server/
  services/
    bazi_ai_service.py           # AI分析服务层
  api/
    v1/
      bazi_ai.py                 # AI分析API接口
```

## 安装依赖

```bash
# 安装 LangChain 和 OpenAI
pip install langchain langchain-openai openai

# 或者使用 requirements.txt
pip install -r requirements.txt
```

## 环境变量设置

```bash
# 设置 OpenAI API Key
export OPENAI_API_KEY="sk-your-api-key-here"
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
  "api_key": "sk-...",                   // 可选：OpenAI API Key（不提供则使用环境变量）
  "model": "gpt-3.5-turbo",              // 可选：AI模型（默认 gpt-3.5-turbo）
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
    "analysis": "根据您提供的八字信息...",  // AI分析结果
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
    "user_question": "请分析我的财运和事业"
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
    "api_key": "sk-..."  # 可选
}
response = requests.post(url, json=data)
result = response.json()
print(result['ai_analysis']['analysis'])
```

### 3. 使用 Swagger UI

访问：`http://127.0.0.1:8001/docs`

在 Swagger UI 中找到 `POST /api/v1/bazi/ai-analyze` 接口进行测试。

## 数据流程

1. **调用八字接口**: 自动调用 `BaziService.calculate_bazi_full()` 获取八字数据
2. **获取日柱分析**: 调用 `RizhuGenderAnalyzer` 获取日柱性别分析（类似 `print_rizhu_gender_analysis()` 的输出）
3. **格式化数据**: 将八字数据和日柱分析结果格式化为文本
4. **AI分析**: 使用 LangChain 调用 OpenAI 进行智能分析
5. **返回结果**: 返回完整的八字数据和AI分析结果

## 功能特点

1. **自动集成**: 自动调用现有八字接口，无需手动获取数据
2. **日柱分析**: 自动包含日柱性别分析结果（类似 `print_rizhu_gender_analysis()`）
3. **灵活配置**: 支持自定义AI模型、API Key等
4. **问题导向**: 支持用户提问，AI针对性回答
5. **完全独立**: 不影响现有任何功能

## 注意事项

1. **API Key**: 需要有效的 OpenAI API Key
2. **费用**: 使用 OpenAI API 会产生费用
3. **依赖**: 需要安装 langchain 和 openai 包
4. **容错**: 如果 langchain 未安装，代码不会崩溃，但AI功能不可用

## 对现有代码的影响

✅ **零影响**：
- 所有现有接口完全不受影响
- 所有现有服务完全不受影响
- 只是新增了独立的功能模块

详细影响分析请查看：`AI_FRAMEWORK_ANALYSIS.md`














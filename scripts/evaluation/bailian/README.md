# 百炼平台（通义千问）集成模块

用于评测对比 Coze 平台和阿里云百炼平台（通义千问）的大模型输出。

## 功能特性

- 支持流式输出（与 Coze 保持一致的接口）
- 支持多场景智能体调用
- 独立模块，不影响现有功能

## 已配置的智能体

| 场景 | App ID |
|-----|--------|
| 五行解析 | d326e553a5764d9bac629e87019ac380 |
| 喜神与忌神 | b9188eacd5bc4e1d8b91bd66ef8671df |
| 事业财富 | 0f97307f05d041d2b643c967f98f4cbb |
| 感情婚姻 | 4bf72d82f83d439cb575856e5bcb8502 |
| 身体健康 | 1e9186468bf743a0be8748e0cddd5f44 |
| 子女学习 | a7d2174380be49508ecb5e014c54fc3a |
| 总评分析 | 75d9a46f55374ea2be1ea28db10c8d03 |
| 每日运势 | df11520293eb479a985916d977904a8a |
| QA-问题生成 | 835867a183cd4a0db861c61f632bbaa6 |
| QA-命理分析 | b9188eacd5bc4e1d8b91bd66ef8671df |

## 安装依赖

```bash
pip install dashscope>=1.14.0
```

## 配置 API Key

方式一：环境变量
```bash
export DASHSCOPE_API_KEY=sk-91ad3ec784b64fe78c4015827dfd982d
```

方式二：命令行参数
```bash
python bazi_evaluator.py --input test.xlsx --platform bailian --bailian-api-key sk-xxx
```

## 使用方式

### 仅使用 Coze（默认）
```bash
python bazi_evaluator.py --input test.xlsx
# 或
python bazi_evaluator.py --input test.xlsx --platform coze
```

### 仅使用百炼
```bash
python bazi_evaluator.py --input test.xlsx --platform bailian
```

### 双平台对比评测
```bash
python bazi_evaluator.py --input test.xlsx --platform both
```

### 其他参数
```bash
# 单条测试
python bazi_evaluator.py --input test.xlsx --platform both --row 2

# 显示详细进度
python bazi_evaluator.py --input test.xlsx --platform both --verbose

# 指定并发数
python bazi_evaluator.py --input test.xlsx --platform both --concurrency 5
```

## 输出说明

使用 `--platform both` 时，Excel 输出会包含两组结果列：

1. **Coze 结果列**（原有位置）：
   - 五行占比分析、喜神忌神、事业财富、感情婚姻、身体健康、子女学习、总评、每日运势

2. **百炼结果列**（新增，在 AI 问答列之后）：
   - 百炼-五行占比分析、百炼-喜神忌神、百炼-事业财富、百炼-感情婚姻、百炼-身体健康、百炼-子女学习、百炼-总评、百炼-每日运势

## 测试客户端

```bash
# 测试百炼客户端连接
python -m scripts.evaluation.bailian.bailian_client
```

## 文件结构

```
scripts/evaluation/bailian/
├── __init__.py          # 模块导出
├── bailian_client.py    # 百炼 API 客户端
├── config.py            # 配置和 App ID 映射
└── README.md            # 本文档
```

## 注意事项

1. 百炼平台的智能体需要在阿里云百炼控制台预先创建
2. 每个场景对应一个独立的智能体（app_id）
3. API Key 需要有足够的调用配额
4. 流式输出可能比同步调用消耗更多 token


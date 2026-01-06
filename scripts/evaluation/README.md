# 八字评测工具

批量调用八字分析API接口，生成评测数据并写入Excel。

## 功能特点

- **独立运行**：不影响现有系统功能，只做API调用
- **批量处理**：支持批量处理Excel中的多条数据
- **全面覆盖**：调用所有八字分析接口，包括：
  - 基础八字数据（日元、五行、十神、喜忌、旺衰等）
  - 大模型分析（五行占比、事业财富、婚姻、健康等）
  - AI多轮问答（3轮对话）
- **进度显示**：支持显示详细的评测进度

## 使用方法

### 基本用法

```bash
# 进入项目目录
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 批量评测所有数据
python scripts/evaluation/bazi_evaluator.py --input /Users/zhoudt/Desktop/10.xlsx

# 只评测第2行数据
python scripts/evaluation/bazi_evaluator.py --input /Users/zhoudt/Desktop/10.xlsx --row 2

# 显示详细进度
python scripts/evaluation/bazi_evaluator.py --input /Users/zhoudt/Desktop/10.xlsx --verbose
```

### 命令行参数

| 参数 | 简写 | 说明 | 必填 |
|------|------|------|------|
| --input | -i | Excel文件路径 | 是 |
| --row | -r | 只处理指定行（从2开始） | 否 |
| --verbose | -v | 显示详细进度 | 否 |
| --base-url | | API服务地址 | 否 |

### 示例

```bash
# 测试单条数据
python scripts/evaluation/bazi_evaluator.py -i /Users/zhoudt/Desktop/10.xlsx -r 2 -v

# 批量测试所有数据
python scripts/evaluation/bazi_evaluator.py -i /Users/zhoudt/Desktop/10.xlsx -v

# 使用本地开发环境
python scripts/evaluation/bazi_evaluator.py -i /Users/zhoudt/Desktop/10.xlsx --base-url http://localhost:8001
```

## Excel格式要求

### 输入列（必填）

| 列索引 | 列名 | 示例 |
|--------|------|------|
| A (0) | USER_ID | 1 |
| B (1) | 用户名 | 董文强 |
| C (2) | USER_birth（生辰八字） | 1985 年 10 月 21 日 |
| D (3) | 性别（男/女） | 男 |

### 输出列（自动填充）

| 列索引 | 列名 | 数据来源 |
|--------|------|----------|
| E (4) | 日元 | /bazi/rizhu-liujiazi |
| F (5) | 五行 | /bazi/rizhu-liujiazi |
| G (6) | 十神 | /bazi/rizhu-liujiazi |
| H (7) | 喜忌 | /bazi/rizhu-liujiazi |
| I (8) | 旺衰 | /bazi/rizhu-liujiazi |
| P (15) | 日元-六十甲子 | /bazi/rizhu-liujiazi |
| Q (16) | 五行占比分析 | /bazi/wuxing-proportion/stream |
| R (17) | 喜神与忌神 | /bazi/xishen-jishen/stream |
| S (18) | 事业财富 | /career-wealth/stream |
| T (19) | 感情婚姻 | /bazi/marriage-analysis/stream |
| U (20) | 身体健康 | /health/stream |
| V (21) | 子女学习 | /children-study/stream |
| W (22) | 总评 | /general-review/stream |
| X (23) | 每日运势 | /daily-fortune-calendar/stream |
| AA (26) | 业务场景（菜单） | 随机选择 |
| AB (27) | output模型回答 | /smart-analyze-stream |
| AC (28) | CUSMOTER_input2 | 从预设问题选择 |
| AD (29) | output2模型回答 | /smart-analyze-stream |
| AE (30) | CUSMOTER_input3 | 从相关问题选择 |
| AF (31) | output3模型回答 | /smart-analyze-stream |

## 配置说明

默认配置在 `config.py` 中：

```python
# API服务地址（生产环境Node1）
base_url = "http://8.210.52.217:8001"

# 默认出生时辰
default_hour = "12:00"

# 请求超时（秒）
request_timeout = 60
stream_timeout = 120

# AI问答业务场景
ai_qa_categories = ["事业财富", "婚姻", "健康", "子女", "流年运势", "年运报告"]
```

## 注意事项

1. **网络要求**：需要能访问生产环境 API 服务
2. **权限要求**：需要有Excel文件的读写权限
3. **运行时间**：每条数据约需要 10-15 分钟（取决于网络和API响应速度，大模型接口响应较慢）
4. **数据安全**：评测完成后会直接修改原Excel文件
5. **超时处理**：流式接口默认超时5分钟，超时后会记录"[请求超时]"到对应列

## 依赖

```
pandas
openpyxl
aiohttp
```

安装依赖：
```bash
pip install pandas openpyxl aiohttp
```

## 目录结构

```
scripts/evaluation/
├── __init__.py         # 模块初始化
├── bazi_evaluator.py   # 主评测脚本（入口）
├── api_client.py       # API客户端封装
├── excel_handler.py    # Excel读写处理
├── data_parser.py      # 数据解析器
├── config.py           # 配置管理
└── README.md           # 使用说明
```


# 八字评测工具

批量调用八字分析API接口，生成评测数据并写入Excel。

**流式评测数据工程化（方法论、阶段、门禁、扩展）**：见 `数据评测/流式接口评测数据工程化方法论.md`。

## 功能特点

- **独立运行**：不影响现有系统功能，只做API调用
- **数据同源**：批量调用流式接口，基础数据从 type=data 事件提取，与流式接口完全一致
- **批量处理**：支持批量处理Excel中的多条数据
- **全面覆盖**：调用所有流式分析接口（五行占比、喜神忌神、事业财富、婚姻、健康、子女、总评、每日运势、年运报告）
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
| --row | -r | 只处理指定行（从1开始） | 否 |
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
| F (5) | 日柱 | wuxing_proportion/stream type=data |
| G (6) | 五行 | wuxing_proportion/stream type=data |
| H (7) | 十神 | wuxing_proportion/stream type=data |
| I (8) | 喜忌 | wuxing_proportion/stream type=data |
| J (9) | 旺衰 | wuxing_proportion/stream type=data |
| K (10) | 格局 | xishen_jishen/stream type=data |
| L (11) | 大运流年 | wuxing_proportion/stream type=data |
| M (12) | 日元六十甲子 | /bazi/rizhu-liujiazi |
| N (13) | 五行占比分析 | wuxing_proportion/stream content |
| O (14) | 喜神与忌神 | xishen_jishen/stream content |
| P (15) | 事业财富 | career-wealth/stream |
| Q (16) | 感情婚姻 | marriage-analysis/stream |
| R (17) | 身体健康 | health/stream |
| S (18) | 子女学习 | children-study/stream |
| T (19) | 总评 | general-review/stream |
| U (20) | 每日运势 | daily-fortune-calendar/stream |
| V (21) | 年运报告 | annual-report/stream |

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

# 批量并发数
batch_concurrency = 3
```

## 注意事项

1. **网络要求**：需要能访问生产环境 API 服务
2. **权限要求**：需要有Excel文件的读写权限
3. **运行时间**：每条数据约需数分钟（取决于网络和 LLM 响应速度，已去除 AI 多轮问答以节省时间）
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

## 接口回归测试（上一版 vs 下一版）

用于在代码调整后，验证接口返回**格式与内容**与上一版是否一致。

```bash
# 模式1：双环境对比（上一版=旧环境 URL，下一版=新环境 URL）
python scripts/evaluation/api_regression_test.py --old-url http://旧环境:8001 --new-url http://新环境:8001

# 模式2：先保存基线，改代码后再对比
python scripts/evaluation/api_regression_test.py --save-baseline -o api_baseline.json
# ... 改代码、热更新 ...
python scripts/evaluation/api_regression_test.py --baseline api_baseline.json --new-url http://localhost:8001

# 仅对比格式/结构（不对比 LLM 文本等内容）
python scripts/evaluation/api_regression_test.py --old-url ... --new-url ... --format-only
```

**覆盖范围**：共 **38 个接口**，包括：
- 八字核心：`/bazi/data`、`/bazi/interface`、排盘、旺衰、身宫命宫、日元六十甲子、公式分析、五行/喜忌 等
- 流式分析：五行/喜忌/事业/婚姻/健康/子女/总评/年运/每日运势 的 stream 与 debug、test
- 日历与智能：万年历、每日运势日历查询、智能分析
- 支付/首页/管理：支付渠道、首页内容、面相/办公桌风水、Proto 列表

**说明**：依赖 Coze 的流式接口（事业/婚姻/健康/子女/总评/年运）在配额用尽时会返回 4028，属环境限制，不影响格式回归结论。

## 感情婚姻 - 百炼模型评测数据集

为百炼平台「模型评测」生成感情婚姻场景的评测数据集（Prompt + Completion）。

### 从「内部人员」类 Excel 转换（批导出的千问/排盘表）

若你已有内部批量表（第二行为列名，含 `USER_ID`、`性别`、`日元`、`八字`、`十神`、`五行喜忌`、`旺衰`、`大运流年`、**`感情婚姻`** 等），可转为百炼格式；**Completion 使用「感情婚姻」列**，比一般模型生成的参考答案更贴近业务。

```bash
.venv/bin/python scripts/evaluation/convert_internal_excel_to_marriage_eval.py \
  --input /path/to/内部人员.xlsx \
  --output scripts/evaluation/data/感情婚姻_评测集_内部.xlsx
```

- 输出：`Prompt` + `Completion` 两列（上传百炼）；同目录另有 `*_含USER_ID.xlsx` 便于对照，**勿将含真实姓名/ID 的文件提交 Git**。
- 表中若无独立「地支关系」「婚姻判词」列，脚本在 Prompt 里会标 `待完善」，评测时仍以「数据忠实性」约束模型勿编造。

### 多流式接口一次生成（五行 / 喜忌 / 事业 / 婚姻 / 健康 / 子女 / 总评 / 年运）

默认写入 **`~/Desktop/评测数据/`**，按场景分子目录；**Prompt 仅含命盘事实列**，不包含各模块长文输出列，避免把参考答案写进 Prompt。

```bash
.venv/bin/python scripts/evaluation/convert_internal_excel_to_stream_eval_sets.py \
  --input /path/to/内部人员.xlsx

# 自定义输出根目录
.venv/bin/python scripts/evaluation/convert_internal_excel_to_stream_eval_sets.py \
  --input /path/to/内部人员.xlsx --output-dir ~/Desktop/评测数据
```

### 脚本合成评测集（覆盖矩阵 / qwen-max 生成 Completion）

```bash
# 仅生成 Prompt（Completion 留空）
.venv/bin/python scripts/evaluation/generate_marriage_eval_data.py --prompt-only -o scripts/evaluation/data/感情婚姻_评测集.xlsx

# 生成 Prompt + 调用 qwen-max 生成 Completion（需 DASHSCOPE_API_KEY）
.venv/bin/python scripts/evaluation/generate_marriage_eval_data.py -o scripts/evaluation/data/感情婚姻_评测集.xlsx
```

评测维度配置与任务创建步骤见：`数据评测/感情婚姻_百炼评测维度配置.md`、`数据评测/子女学习_百炼评测维度配置.md`。  
**小白向全流程（Prompt/Completion、数据生成、维度、任务）**：根目录 `百炼感情婚姻模型评测_完整指南.md`。

## 目录结构

```
scripts/evaluation/
├── __init__.py              # 模块初始化
├── api_regression_test.py   # 接口回归测试（上一版 vs 下一版）
├── bazi_evaluator.py        # 主评测脚本（入口）
├── generate_marriage_eval_data.py  # 感情婚姻评测数据集生成
├── convert_internal_excel_to_marriage_eval.py  # 内部排盘表 → 感情婚姻评测集
├── convert_internal_excel_to_stream_eval_sets.py  # 内部表 → 8 类流式评测集（桌面评测数据）
├── data/
│   ├── 感情婚姻_评测集.xlsx # 百炼模型评测格式（Prompt + Completion）
│   └── README.md
├── bailian/                 # 百炼平台客户端
├── api_client.py            # API客户端封装
├── excel_handler.py         # Excel读写处理
├── data_parser.py           # 数据解析器
├── config.py                # 配置管理
└── README.md                # 使用说明
```


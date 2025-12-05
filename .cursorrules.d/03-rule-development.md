# 规则开发规范 【核心】

## 🔴 规则存储规范 【必须遵守】

> **所有规则必须存储在数据库中，禁止从文件读取！**

| 存储方式 | 状态 | 说明 |
|---------|------|------|
| **MySQL 数据库** | ✅ **唯一来源** | 所有规则存储在 `bazi_rules` 表 |
| Excel 文件 (.xlsx) | ❌ **禁止** | 仅用于导入，导入后删除或归档 |
| Word 文件 (.docx) | ❌ **禁止** | 仅用于导入，导入后删除或归档 |
| JSON 文件 (.json) | ❌ **禁止** | 仅用于导入，导入后删除或归档 |
| 配置文件 | ❌ **禁止** | 不允许在代码中硬编码规则 |

**实现要求**：
```python
# ✅ 正确：从数据库加载规则
from server.services.rule_service import RuleService
rules = RuleService.match_rules(bazi_data, rule_types=['wealth'])

# ❌ 错误：从文件读取规则
import json
with open('rules.json') as f:
    rules = json.load(f)  # 禁止！

# ❌ 错误：从 Excel 读取规则
import pandas as pd
df = pd.read_excel('rules.xlsx')  # 禁止！
```

**代码检查清单**：
- [ ] 所有规则匹配使用 `RuleService`
- [ ] 没有 `load_from_file`、`read_excel`、`read_json` 等文件读取调用
- [ ] 没有硬编码的规则数据
- [ ] 规则导入脚本仅用于一次性导入，不用于运行时读取

**废弃代码标记**：
```python
# ⚠️ 已废弃：以下方法仅用于兼容，新代码禁止使用
# - RuleEngine.load_from_file()  # 已废弃
# - FormulaRuleService.load_rules()  # 已废弃，改用 RuleService
```

## 规则开发完整流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           规则开发标准流程                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 准备阶段                                                                │
│     ├── 获取规则文档（Excel/JSON）                                           │
│     ├── 分析规则结构（类型、条件、结果）                                       │
│     └── 识别新条件类型（是否需要扩展规则引擎）                                  │
│                                                                             │
│  2. 条件类型检查                                                             │
│     ├── 检查 rule_condition.py 是否支持所需条件                               │
│     ├── 如不支持 → 先扩展规则引擎                                             │
│     └── 扩展后编写单元测试验证                                                │
│                                                                             │
│  3. 编写导入脚本                                                             │
│     ├── 位置：scripts/migration/import_xxx_rules.py                         │
│     ├── 解析规则文档                                                         │
│     ├── 转换为数据库格式                                                     │
│     ├── 标记歧义规则待确认                                                   │
│     └── 支持 --dry-run 预览                                                  │
│                                                                             │
│  4. 执行导入                                                                 │
│     ├── 先 --dry-run 确认无误                                                │
│     ├── 处理歧义规则（与用户确认）                                            │
│     ├── 正式导入数据库                                                       │
│     └── 验证规则数量和内容                                                   │
│                                                                             │
│  5. 前端适配                                                                 │
│     ├── 检查 typeLabels 是否包含新类型                                       │
│     ├── 检查 statistics 统计是否显示                                         │
│     └── 测试前端页面展示                                                     │
│                                                                             │
│  6. 后端适配                                                                 │
│     ├── 检查 formula_analysis.py 类型映射                                    │
│     ├── 检查 matched_rules 初始化                                            │
│     └── 检查 statistics 返回字段                                             │
│                                                                             │
│  7. 测试验证                                                                 │
│     ├── API 测试：curl 验证返回数据                                          │
│     ├── 前端测试：页面展示正常                                               │
│     └── 规则匹配：抽样验证规则匹配准确性                                      │
│                                                                             │
│  8. 提交代码                                                                 │
│     ├── 提交导入脚本                                                         │
│     ├── 提交规则引擎扩展（如有）                                             │
│     ├── 提交前后端适配代码                                                   │
│     └── 同步生产数据库                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 规则数据库结构

**表：`bazi_rules`**
```sql
CREATE TABLE bazi_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_code VARCHAR(100) NOT NULL UNIQUE,    -- 规则编码：FORMULA_类型_编号
    rule_name VARCHAR(200),                     -- 规则名称
    rule_type VARCHAR(50) NOT NULL,             -- 规则类型（英文）
    conditions JSON,                            -- 匹配条件（JSON格式）
    content JSON,                               -- 规则内容/结果
    description JSON,                           -- 原始描述信息
    priority INT DEFAULT 100,                   -- 优先级
    enabled TINYINT DEFAULT 1,                  -- 是否启用
    version INT DEFAULT 1,                      -- 版本号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 规则编码规范

| 格式 | 示例 | 说明 |
|------|------|------|
| `FORMULA_类型_编号` | `FORMULA_事业_80001` | 新版格式（推荐） |
| `FORMULA_编号` | `FORMULA_10901` | 旧版格式（兼容） |

**类型映射（中英文）：**
| 中文 | 英文 | 说明 |
|------|------|------|
| 财富 | wealth | 财运相关 |
| 婚姻 | marriage | 婚配相关 |
| 事业 | career | 事业相关 |
| 子女 | children | 子女相关 |
| 性格 | character | 性格特征 |
| 总评 | summary | 综合评价 |
| 身体 | health | 健康相关 |
| 桃花 | peach_blossom | 桃花运 |
| 十神命格 | shishen | 十神分析 |

## 规则条件类型清单

### 基础条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `gender` | `"male"` / `"female"` / `"*"` | 性别条件 |
| `wangshuai` | `["身旺"]` / `["身弱"]` | 旺衰条件 |

### 四柱条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `pillar_in` | `{"pillar": "day", "part": "stem", "values": ["甲", "乙"]}` | 柱位匹配 |
| `pillar_equals` | `{"pillar": "day", "values": ["庚辰"]}` | 完整柱匹配 |
| `pillar_relation` | `{"pillar_a": "day", "pillar_b": "hour", "relation": "chong"}` | 柱间关系 |

### 十神条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `ten_gods_main` | `{"names": ["正官", "七杀"], "min": 2}` | 主星数量 |
| `ten_gods_sub` | `{"names": ["食神"], "pillars": ["day"], "min": 1}` | 副星数量 |
| `ten_gods_total` | `{"names": ["比肩", "劫财"], "min": 3}` | 总十神数量 |
| `main_star_in_day` | `"七杀"` | 日柱主星 |
| `main_star_in_any_pillar` | `"食神"` | 任意柱主星 |
| `ten_gods_main_chong_count` | `{"min": 2}` | 主星被冲次数 |

### 五行条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `element_total` | `{"element": "木", "min": 3}` | 五行数量 |
| `elements_count` | `{"木": {"min": 2}, "火": {"max": 1}}` | 多五行数量 |

### 神煞条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `deities_in_any_pillar` | `"天乙贵人"` | 任意柱有神煞 |
| `deities_in_year` | `"华盖"` | 年柱有神煞 |
| `deities_in_month` | `"空亡"` | 月柱有神煞 |
| `deities_in_day` | `"桃花"` | 日柱有神煞 |
| `deities_in_hour` | `"驿马"` | 时柱有神煞 |
| `deities_same_pillar` | `["华盖", "空亡"]` | 同柱多神煞 |

### 十二长生条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `star_fortune_in_day` | `"帝旺"` / `["死", "绝"]` | 日支十二长生 |
| `star_fortune_in_hour` | `"墓"` | 时支十二长生 |
| `liunian_star_fortune` | `"绝"` | 流年十二长生 |

### 关系条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `branch_sanxing` | `true` | 地支三刑 |
| `stem_wuhe_pairs` | `{"min": 1}` | 天干五合对数 |
| `pillar_branch_xing_chong` | `true` | 柱地支被刑冲 |
| `multi_chong` | `{"min": 2}` | 多重冲 |

### 特殊条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `xishen` | `"比肩"` | 喜用神匹配 |
| `xishen_in` | `["食神", "伤官"]` | 喜用神在列表中 |
| `taiyuan_shengong_minggong` | `{"taiyuan": "癸丑"}` | 胎元身宫命宫 |
| `stems_branches_count` | `{"names": ["壬", "癸", "子"], "min": 3}` | 天干地支混合计数 |
| `not` | `{...条件...}` | 否定条件 |

### 组合条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `all` | `[条件1, 条件2, ...]` | 所有条件都满足（AND） |
| `any` | `[条件1, 条件2, ...]` | 任一条件满足（OR） |

## 规则导入脚本模板

详细模板请参考原始 `.cursorrules` 文件中的完整代码示例（行 398-585）。

**关键要点**：
- 位置：`scripts/migration/import_xxx_rules.py`
- 支持 `--dry-run` 预览模式
- 使用 `RuleConverter` 转换规则格式
- 使用参数化查询防止 SQL 注入
- 支持更新已存在的规则（版本号递增）


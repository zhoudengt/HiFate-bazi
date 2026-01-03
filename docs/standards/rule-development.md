# 规则开发详细规范

> 本文档从 `.cursorrules` 提取，包含规则开发的完整规范。详见 `.cursorrules` 核心规范章节。

## 规则存储规范 【必须遵守】

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

---

### 规则开发完整流程

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
│  3. 编写解析脚本                                                             │
│     ├── 位置：scripts/migration/import_xxx_rules.py                         │
│     ├── 解析规则文档                                                         │
│     ├── 转换为数据库格式                                                     │
│     ├── 标记歧义规则待确认                                                   │
│     └── 生成未解析规则JSON（包含详细说明）                                    │
│                                                                             │
│  4. 解析规则                                                                 │
│     ├── 运行解析脚本：python scripts/migration/import_xxx_rules.py         │
│     ├── 检查解析率（目标：>80%）                                             │
│     ├── 分析未解析规则原因                                                   │
│     └── 生成未解析规则详细说明JSON                                           │
│                                                                             │
│  5. 扩展解析能力（如需要）                                                   │
│     ├── 在 RuleParser 中添加新的解析方法                                     │
│     ├── 在 rule_condition.py 中添加新的条件匹配逻辑                          │
│     ├── 重新运行解析脚本验证                                                 │
│     └── 确保解析率提升                                                       │
│                                                                             │
│  6. 导入数据库                                                               │
│     ├── 编写导入脚本：scripts/migration/import_xxx_rules_to_db.py           │
│     ├── 先 --dry-run 预览                                                    │
│     ├── 正式导入数据库                                                       │
│     └── 验证规则数量和内容                                                   │
│                                                                             │
│  7. 前端适配                                                                 │
│     ├── 检查 local_frontend/formula-analysis.html 中 typeLabels 是否包含新类型     │
│     ├── 检查 statistics 统计是否显示                                         │
│     └── 测试前端页面展示                                                     │
│                                                                             │
│  8. 后端适配                                                                 │
│     ├── 检查 server/api/v1/formula_analysis.py 类型映射                     │
│     ├── 检查 matched_rules 初始化                                            │
│     └── 检查 statistics 返回字段                                             │
│                                                                             │
│  9. 端到端测试                                                               │
│     ├── API 测试：curl 验证返回数据                                          │
│     ├── 前端测试：页面展示正常                                               │
│     └── 规则匹配：抽样验证规则匹配准确性                                      │
│                                                                             │
│  10. 提交代码                                                                │
│     ├── 提交解析脚本                                                         │
│     ├── 提交导入脚本                                                         │
│     ├── 提交规则引擎扩展（如有）                                             │
│     ├── 提交前后端适配代码                                                   │
│     ├── 提交未解析规则详细说明JSON                                           │
│     └── 同步生产数据库                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 规则解析脚本标准模板

**文件命名**：`scripts/migration/import_YYYY_MM_DD_rules.py`

**核心功能**：
1. 解析Excel规则文件
2. 使用 `RuleParser` 解析规则条件
3. 生成成功解析和失败解析的统计
4. 保存未解析规则到JSON文件

**标准输出**：
- 解析率统计
- 失败原因统计
- 未解析规则JSON文件（`docs/未解析规则_YYYY_MM_DD_描述.json`）

## 规则导入脚本标准模板

**文件命名**：`scripts/migration/import_YYYY_MM_DD_rules_to_db.py`

**核心功能**：
1. 调用解析脚本获取已解析规则
2. 连接数据库
3. 插入或更新规则（根据 rule_code 判断）
4. 支持 --dry-run 预览模式

**标准流程**：
```bash
# 1. 预览模式
python scripts/migration/import_YYYY_MM_DD_rules_to_db.py --dry-run

# 2. 正式导入
python scripts/migration/import_YYYY_MM_DD_rules_to_db.py
```

## 未解析规则详细说明JSON标准格式

**文件命名**：`docs/未解析规则_YYYY_MM_DD_描述_详细说明.json`

**标准结构**：
```json
{
  "统计": {
    "总规则数": 60,
    "成功解析": 53,
    "无法解析": 7,
    "解析成功率": "88.3%"
  },
  "未解析规则详细说明": [
    {
      "ID": 80102,
      "类型": "事业",
      "筛选条件1": "十神",
      "筛选条件2": "...",
      "结果": "...",
      "rule_code": "FORMULA_事业_80102",
      "解析失败原因": "...",
      "不理解点说明": {
        "不理解的点": ["问题1", "问题2"],
        "需要澄清的概念": {
          "概念1": "说明1",
          "概念2": "说明2"
        },
        "歧义说明": "为什么无法解析",
        "案例说明": {
          "示例1": {
            "八字": "...",
            "验证": {
              "条件1": "...",
              "结果": "..."
            }
          }
        },
        "解决方案": "如何解决这个问题"
      }
    }
  ],
  "总结": {
    "主要问题类型": ["类型1", "类型2"],
    "优先级建议": ["高优先级", "中优先级", "低优先级"]
  }
}
```

## 规则解析增强标准流程

**当解析率 < 80% 时，需要增强解析能力**：

1. **分析未解析规则**
   - 统计失败原因
   - 识别常见模式
   - 确定需要扩展的功能

2. **扩展解析器**
   - 在 `RuleParser._parse_ten_gods` 等方法中添加新逻辑
   - 支持新的条件模式
   - 处理复杂组合条件

3. **扩展规则引擎**
   - 在 `server/engines/rule_condition.py` 中添加新条件类型
   - 实现条件匹配逻辑
   - 确保不影响现有功能

4. **验证增强效果**
   - 重新运行解析脚本
   - 检查解析率提升
   - 确保没有破坏现有功能

5. **迭代优化**
   - 重复上述步骤，直到解析率 > 80%
   - 记录无法解析的规则到详细说明JSON
   - 标记需要进一步开发的复杂功能

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

## 基础条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `gender` | `"male"` / `"female"` / `"*"` | 性别条件 |
| `wangshuai` | `["身旺"]` / `["身弱"]` | 旺衰条件 |

## 四柱条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `pillar_in` | `{"pillar": "day", "part": "stem", "values": ["甲", "乙"]}` | 柱位匹配 |
| `pillar_equals` | `{"pillar": "day", "values": ["庚辰"]}` | 完整柱匹配 |
| `pillar_relation` | `{"pillar_a": "day", "pillar_b": "hour", "relation": "chong"}` | 柱间关系 |

## 十神条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `ten_gods_main` | `{"names": ["正官", "七杀"], "min": 2}` | 主星数量 |
| `ten_gods_sub` | `{"names": ["食神"], "pillars": ["day"], "min": 1}` | 副星数量 |
| `ten_gods_total` | `{"names": ["比肩", "劫财"], "min": 3}` | 总十神数量 |
| `main_star_in_day` | `"七杀"` | 日柱主星 |
| `main_star_in_any_pillar` | `"食神"` | 任意柱主星 |
| `ten_gods_main_chong_count` | `{"min": 2}` | 主星被冲次数 |

## 五行条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `element_total` | `{"element": "木", "min": 3}` | 五行数量 |
| `elements_count` | `{"木": {"min": 2}, "火": {"max": 1}}` | 多五行数量 |

## 神煞条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `deities_in_any_pillar` | `"天乙贵人"` | 任意柱有神煞 |
| `deities_in_year` | `"华盖"` | 年柱有神煞 |
| `deities_in_month` | `"空亡"` | 月柱有神煞 |
| `deities_in_day` | `"桃花"` | 日柱有神煞 |
| `deities_in_hour` | `"驿马"` | 时柱有神煞 |
| `deities_same_pillar` | `["华盖", "空亡"]` | 同柱多神煞 |

## 十二长生条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `star_fortune_in_day` | `"帝旺"` / `["死", "绝"]` | 日支十二长生 |
| `star_fortune_in_hour` | `"墓"` | 时支十二长生 |
| `liunian_star_fortune` | `"绝"` | 流年十二长生 |

## 关系条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `branch_sanxing` | `true` | 地支三刑 |
| `stem_wuhe_pairs` | `{"min": 1}` | 天干五合对数 |
| `pillar_branch_xing_chong` | `true` | 柱地支被刑冲 |
| `multi_chong` | `{"min": 2}` | 多重冲 |

## 特殊条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `xishen` | `"比肩"` | 喜用神匹配 |
| `xishen_in` | `["食神", "伤官"]` | 喜用神在列表中 |
| `taiyuan_shengong_minggong` | `{"taiyuan": "癸丑"}` | 胎元身宫命宫 |
| `stems_branches_count` | `{"names": ["壬", "癸", "子"], "min": 3}` | 天干地支混合计数 |
| `not` | `{...条件...}` | 否定条件 |

## 组合条件
| 条件类型 | 格式 | 说明 |
|---------|------|------|
| `all` | `[条件1, 条件2, ...]` | 所有条件都满足（AND） |
| `any` | `[条件1, 条件2, ...]` | 任一条件满足（OR） |

## 规则导入脚本模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则导入脚本：import_xxx_rules.py

使用方法：
  python scripts/migration/import_xxx_rules.py --dry-run  # 预览
  python scripts/migration/import_xxx_rules.py            # 正式导入
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, Tuple, Optional, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection


class RuleConverter:
    """规则转换器"""
    
    # 类型映射
    TYPE_MAPPING = {
        '财富': 'wealth',
        '婚姻': 'marriage',
        '事业': 'career',
        '子女': 'children',
        '性格': 'character',
        '总评': 'summary',
        '身体': 'health',
        '桃花': 'peach_blossom',
    }
    
    def convert(self, raw_rule: Dict) -> Tuple[Optional[Dict], Optional[str]]:
        """
        转换原始规则为数据库格式
        
        Returns:
            (rule_dict, ambiguity_reason) - 如果有歧义返回原因
        """
        # 1. 提取字段
        rule_id = raw_rule.get('ID')
        rule_type_cn = raw_rule.get('类型', '')
        condition1 = raw_rule.get('筛选条件1', '')
        condition2 = raw_rule.get('筛选条件2', '')
        result = raw_rule.get('结果', '')
        gender = raw_rule.get('性别', '')
        
        # 2. 转换类型
        rule_type = self.TYPE_MAPPING.get(rule_type_cn, rule_type_cn.lower())
        
        # 3. 解析条件
        conditions, ambiguity = self._parse_conditions(condition1, condition2, gender)
        if ambiguity:
            return None, f"ID {rule_id}: {ambiguity}"
        
        # 4. 构建规则
        rule = {
            'rule_code': f'FORMULA_{rule_type_cn}_{rule_id}',
            'rule_name': f'{rule_type_cn}规则-{rule_id}',
            'rule_type': rule_type,
            'conditions': conditions,
            'content': {'text': result},
            'description': {
                '筛选条件1': condition1,
                '筛选条件2': condition2,
                '性别': gender
            }
        }
        
        return rule, None
    
    def _parse_conditions(self, cond1: str, cond2: str, gender: str) -> Tuple[Dict, Optional[str]]:
        """解析条件文本为JSON格式"""
        conditions = {}
        
        # 解析性别
        if gender == '男':
            conditions['gender'] = 'male'
        elif gender == '女':
            conditions['gender'] = 'female'
        
        # 解析具体条件（根据实际规则格式实现）
        # ...
        
        return conditions, None


def import_rules(rules: List[Dict], dry_run: bool = False) -> Tuple[int, int, List[str]]:
    """
    导入规则到数据库
    
    Returns:
        (inserted, updated, ambiguous_rules)
    """
    inserted = 0
    updated = 0
    ambiguous = []
    
    if dry_run:
        print("=== DRY RUN 模式，不会修改数据库 ===\n")
    
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            for rule in rules:
                if dry_run:
                    print(f"将导入: {rule['rule_code']}")
                    continue
                
                # 检查是否存在
                cursor.execute(
                    "SELECT id FROM bazi_rules WHERE rule_code = %s",
                    (rule['rule_code'],)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 更新
                    cursor.execute("""
                        UPDATE bazi_rules SET
                            rule_name = %s,
                            rule_type = %s,
                            conditions = %s,
                            content = %s,
                            description = %s,
                            version = version + 1
                        WHERE rule_code = %s
                    """, (
                        rule['rule_name'],
                        rule['rule_type'],
                        json.dumps(rule['conditions'], ensure_ascii=False),
                        json.dumps(rule['content'], ensure_ascii=False),
                        json.dumps(rule['description'], ensure_ascii=False),
                        rule['rule_code']
                    ))
                    updated += 1
                else:
                    # 插入
                    cursor.execute("""
                        INSERT INTO bazi_rules 
                        (rule_code, rule_name, rule_type, conditions, content, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        rule['rule_code'],
                        rule['rule_name'],
                        rule['rule_type'],
                        json.dumps(rule['conditions'], ensure_ascii=False),
                        json.dumps(rule['content'], ensure_ascii=False),
                        json.dumps(rule['description'], ensure_ascii=False)
                    ))
                    inserted += 1
            
            if not dry_run:
                conn.commit()
    finally:
        return_mysql_connection(conn)
    
    return inserted, updated, ambiguous


def main():
    parser = argparse.ArgumentParser(description='规则导入脚本')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    # 加载规则数据
    # ...
    
    # 导入规则
    inserted, updated, ambiguous = import_rules(rules, args.dry_run)
    
    print(f"\n=== 导入结果 ===")
    print(f"新增: {inserted} 条")
    print(f"更新: {updated} 条")
    print(f"歧义: {len(ambiguous)} 条")


if __name__ == '__main__':
    main()
```

---


# input_data 实现方案对比

## 方案概述

### 方案一：结构化 input_data（当前方案）

**实现方式**：
- 构建完整的结构化 `input_data` 字典（JSON格式）
- 通过 `build_natural_language_prompt` 函数将 JSON 转换为自然语言格式的提示词
- 数据包含所有字段，可能在不同部分重复出现

**代码示例**：
```python
# 1. 构建结构化 input_data
input_data = {
    'mingpan_zinv_zonglun': {
        'day_master': {...},
        'bazi_pillars': {...},
        'elements': {...},
        'wangshuai': '极弱',
        'gender': 'male'
    },
    'zinvxing_zinvgong': {
        'zinv_xing_type': '男命子女星：正官（官杀）',
        'ten_gods': {...},
        'deities': {...}
    },
    'shengyu_shiji': {
        'current_dayun': {...},
        'key_dayuns': [...],
        'ten_gods': {...}  # ⚠️ 重复
    },
    'yangyu_jianyi': {
        'ten_gods': {...},  # ⚠️ 重复
        'wangshuai': {...},  # ⚠️ 重复
        'xi_ji': {...}
    }
}

# 2. 转换为自然语言提示词
prompt = build_natural_language_prompt(input_data)
```

---

### 方案二：占位符 + 提示词模板（新方案）

**实现方式**：
- 使用提示词模板，包含 `{{input}}` 占位符
- 按照提示词中的字段说明，只提取需要的数据
- 数据不重复，只在需要的地方出现
- 提示词和数据紧密结合

**代码示例**：
```python
# 1. 提示词模板（包含字段说明）
PROMPT_TEMPLATE = """
你是一个资深的命理师，基于用户的八字命理数据，按照以下格式生成子女分析。

## 用户八字数据

{{input}}

## 数据字段说明

用户输入数据包含以下结构：
- 【命盘子女总论】：日主信息、四柱排盘、五行分布、身旺身弱、月令、性别
- 【子女星与子女宫】：子女星类型、时柱分析、十神配置、神煞分布
- 【生育时机】：当前年龄、当前大运、关键大运分析、关键流年
- 【养育建议】：十神配置、喜神、忌神、喜用五行、忌用五行

...
"""

# 2. 按需提取数据（不重复）
input_data = {
    # 命盘子女总论（只提取一次）
    'mingpan_zinv_zonglun': {
        'day_master': {...},
        'bazi_pillars': {...},
        'elements': {...},
        'wangshuai': '极弱',
        'gender': 'male'
    },
    # 子女星与子女宫（只提取一次）
    'zinvxing_zinvgong': {
        'zinv_xing_type': '男命子女星：正官（官杀）',
        'ten_gods': {...},  # ✅ 只在这里提取
        'deities': {...}
    },
    # 生育时机（引用十神，不重复）
    'shengyu_shiji': {
        'current_dayun': {...},
        'key_dayuns': [...],
        'ten_gods_ref': 'zinvxing_zinvgong.ten_gods'  # ✅ 引用，不重复
    },
    # 养育建议（引用旺衰和十神，不重复）
    'yangyu_jianyi': {
        'ten_gods_ref': 'zinvxing_zinvgong.ten_gods',  # ✅ 引用
        'wangshuai_ref': 'mingpan_zinv_zonglun.wangshuai',  # ✅ 引用
        'xi_ji': {...}
    }
}

# 3. 替换占位符
prompt = PROMPT_TEMPLATE.replace('{{input}}', format_input_data(input_data))
```

---

## 详细对比

| 对比项 | 方案一：结构化 input_data | 方案二：占位符 + 提示词模板 |
|--------|-------------------------|---------------------------|
| **数据重复** | ❌ 数据可能重复（如旺衰、喜忌、十神在多个地方出现） | ✅ 数据不重复，使用引用或只提取一次 |
| **Token 消耗** | ⚠️ 较高（数据重复导致） | ✅ 较低（数据不重复） |
| **数据完整性** | ✅ 易于验证（结构化数据） | ⚠️ 需要确保所有占位符都有数据 |
| **代码复杂度** | ⚠️ 中等（需要构建完整结构 + 转换函数） | ✅ 较低（只需按需提取 + 替换占位符） |
| **维护性** | ⚠️ 中等（修改提示词需要同时修改转换函数） | ✅ 较高（提示词和数据提取分离） |
| **灵活性** | ⚠️ 较低（固定结构） | ✅ 较高（可以根据提示词灵活组织数据） |
| **调试难度** | ✅ 较易（可以查看完整的 input_data） | ⚠️ 中等（需要查看替换后的完整提示词） |
| **类型安全** | ✅ 可以（使用 Pydantic 验证） | ⚠️ 较难（字符串模板） |
| **数据复用** | ✅ 可以（结构化数据可以复用） | ⚠️ 较难（需要重新提取） |
| **提示词与数据结合** | ⚠️ 分离（先构建数据，再转换） | ✅ 紧密结合（提示词直接说明需要的数据） |

---

## 具体问题分析

### 1. 数据重复问题

**方案一（当前）**：
```python
# 旺衰数据在多个地方出现
input_data = {
    'mingpan_zinv_zonglun': {
        'wangshuai': '极弱'  # 第一次
    },
    'yangyu_jianyi': {
        'wangshuai': {...}  # 第二次（完整对象）
    }
}

# 十神数据在多个地方出现
input_data = {
    'zinvxing_zinvgong': {
        'ten_gods': {...}  # 第一次
    },
    'shengyu_shiji': {
        'ten_gods': {...}  # 第二次（重复）
    },
    'yangyu_jianyi': {
        'ten_gods': {...}  # 第三次（重复）
    }
}
```

**方案二（新方案）**：
```python
# 数据只提取一次，其他地方引用
input_data = {
    'mingpan_zinv_zonglun': {
        'wangshuai': '极弱'  # 只在这里
    },
    'zinvxing_zinvgong': {
        'ten_gods': {...}  # 只在这里
    },
    'shengyu_shiji': {
        'ten_gods_ref': 'zinvxing_zinvgong.ten_gods'  # 引用
    },
    'yangyu_jianyi': {
        'wangshuai_ref': 'mingpan_zinv_zonglun.wangshuai',  # 引用
        'ten_gods_ref': 'zinvxing_zinvgong.ten_gods'  # 引用
    }
}
```

### 2. Token 消耗对比

**方案一（当前）**：
- 假设每个字段平均 50 tokens
- 旺衰数据重复：50 + 200 = 250 tokens
- 十神数据重复：200 + 200 + 200 = 600 tokens
- **总重复消耗**：约 850 tokens

**方案二（新方案）**：
- 数据只提取一次：50 + 200 = 250 tokens
- 引用不消耗额外 tokens
- **节省**：约 600 tokens（约 70%）

### 3. 代码实现对比

**方案一（当前）**：
```python
# 1. 构建完整结构（约 200 行代码）
def build_children_study_input_data(...):
    input_data = {
        'mingpan_zinv_zonglun': {...},
        'zinvxing_zinvgong': {...},
        'shengyu_shiji': {...},
        'yangyu_jianyi': {...}
    }
    return input_data

# 2. 转换为自然语言（约 150 行代码）
def build_natural_language_prompt(data: dict) -> str:
    prompt_lines = []
    # 转换逻辑...
    return '\n'.join(prompt_lines)

# 总代码量：约 350 行
```

**方案二（新方案）**：
```python
# 1. 按需提取数据（约 150 行代码）
def build_children_study_input_data(...):
    input_data = {
        'mingpan_zinv_zonglun': {...},  # 只提取一次
        'zinvxing_zinvgong': {...},  # 只提取一次
        'shengyu_shiji': {
            'ten_gods_ref': 'zinvxing_zinvgong.ten_gods'  # 引用
        },
        'yangyu_jianyi': {
            'wangshuai_ref': 'mingpan_zinv_zonglun.wangshuai',  # 引用
            'ten_gods_ref': 'zinvxing_zinvgong.ten_gods'  # 引用
        }
    }
    return input_data

# 2. 替换占位符（约 50 行代码）
def format_input_data(input_data: dict) -> str:
    # 解析引用，格式化数据
    ...

# 3. 提示词模板（外部文件，约 100 行）
PROMPT_TEMPLATE = """
...
{{input}}
...
"""

# 总代码量：约 200 行（减少 43%）
```

---

## 推荐方案

### 推荐：方案二（占位符 + 提示词模板）

**理由**：
1. **Token 节省**：减少约 70% 的重复数据，显著降低 LLM 调用成本
2. **代码简化**：减少约 43% 的代码量，更易维护
3. **灵活性高**：提示词和数据提取分离，修改提示词不影响数据提取逻辑
4. **数据不重复**：符合 DRY（Don't Repeat Yourself）原则

**实施建议**：
1. 保留当前方案作为备选（向后兼容）
2. 实现新方案，使用配置开关控制使用哪个方案
3. 逐步迁移，先在新接口使用，验证效果后再全面推广

---

## 实施步骤

### 阶段一：实现新方案（1-2天）
1. 创建提示词模板文件（`server/prompts/children_study_template.txt`）
2. 修改 `build_children_study_input_data` 函数，按需提取数据，使用引用
3. 实现 `format_input_data` 函数，解析引用并格式化数据
4. 实现 `replace_placeholder` 函数，替换占位符

### 阶段二：对比测试（1天）
1. 同时支持两种方案（通过配置开关）
2. 对比 Token 消耗、响应质量、响应时间
3. 收集用户反馈

### 阶段三：优化和推广（1-2天）
1. 根据测试结果优化新方案
2. 如果效果好，推广到其他接口（健康、事业财富、总评等）
3. 逐步废弃旧方案

---

## 注意事项

1. **数据完整性**：确保所有占位符都有对应的数据，避免 LLM 收到不完整信息
2. **引用解析**：实现可靠的引用解析机制，确保引用路径正确
3. **向后兼容**：保留旧方案一段时间，确保平滑过渡
4. **错误处理**：如果引用路径不存在，要有降级方案
5. **测试覆盖**：充分测试各种数据场景，确保新方案稳定可靠


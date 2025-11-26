# 规则分类与LLM融合系统

## 概述

本系统实现了将规则匹配结果与LLM深度分析融合的功能，使得大模型可以基于规则内容进行更精准的分析。

**核心特性**：
- ✅ 模块化设计，不影响现有功能
- ✅ 规则按意图自动分类
- ✅ 只传递用户查询意图相关的规则
- ✅ 十神命格规则映射到性格意图
- ✅ 输出格式与现有系统一致

---

## 架构设计

### 1. 核心模块

#### RuleClassifier（规则分类器）
**文件**：`server/services/rule_classifier.py`

**职责**：
- 将 `rule_type` 映射到用户意图（intent）
- 按意图分组规则
- 提取规则摘要供 LLM 使用

**映射规则**：
```python
rule_type                → intent
------------------------------------
marriage_*               → marriage
wealth_*                 → wealth
health_*                 → health
character                → character
shishen*                 → character  # 十神命格
rizhu_gender*            → character  # 日柱性格
career                   → character  # 事业（性格影响）
general                  → general
```

---

## 数据流程

### 旧流程（优化前）
```
用户问题 → Intent识别 → 规则匹配 → LLM分析
                                     ↑
                         只传递：八字、流年大运
```

### 新流程（优化后）
```
用户问题 → Intent识别 → 规则匹配 → 规则分类 → LLM分析
                                     ↓           ↑
                         按意图过滤规则  八字+流年大运+规则内容
```

---

## 使用示例

### 1. 用户查询性格

**输入**：
```
问题："我的性格怎么样？"
意图：character
```

**传递给LLM的数据**：
```json
{
  "intent": "character",
  "question": "我的性格怎么样？",
  "bazi": { ... },
  "liunian": { ... },
  "matched_rules": {
    "character": [
      "规则1: 甲木日主，头脑聪明有智慧...",
      "规则2: 正官透干，为人正直守规则...",
      "规则3: 伤官见官，性格叛逆不服管..."
    ]
  },
  "rules_count": {
    "character": 3,
    "total": 3
  }
}
```

### 2. LLM输出

LLM 接收规则内容后，会融合八字数据进行深度分析：

```markdown
【性格与命运分析】

根据您的八字，综合日柱、十神等多方面信息：

1. **基础性格**
   从日柱甲子来看，甲为头，子为水为智慧，您天生头脑聪明，思维敏捷...

2. **行为特征**
   八字中正官透干，说明您为人正直，做事守规则...
   
3. **人际关系**
   伤官见官的格局，显示您性格中有叛逆的一面...

【综合评价】
您是一个智慧与原则并存的人...
```

---

## API 接口

### 无需修改

现有 API 接口保持不变，系统会自动：
1. 识别用户意图
2. 匹配相关规则
3. 分类并传递给 LLM
4. 返回融合分析结果

**示例请求**：
```http
GET /api/v1/smart-analyze?
  question=我的性格怎么样？
  &year=1990
  &month=5
  &day=15
  &hour=14
  &gender=male
  &include_fortune_context=true
```

**响应格式**（保持不变）：
```json
{
  "success": true,
  "question": "我的性格怎么样？",
  "intent_result": { ... },
  "bazi_info": { ... },
  "matched_rules_count": 15,
  "response": "根据您的问题...",
  "fortune_context": { ... }
}
```

---

## 规则分类映射表

| 规则类型 | 意图 | 说明 |
|---------|------|------|
| `marriage_*` | marriage | 婚姻相关所有规则 |
| `taohua_general` | marriage | 桃花运归入婚姻 |
| `wealth_*` | wealth | 财富相关规则 |
| `health_*` | health | 健康相关规则 |
| `FORMULA_HEALTH_*` | health | 健康算法规则 |
| `character` | character | 性格规则 |
| `personality` | character | 性格规则 |
| `career` | character | 事业（性格影响事业） |
| `shishen*` | character | **十神命格规则** ⭐ |
| `rizhu_gender*` | character | **日柱性格分析** ⭐ |
| `general` | general | 综合规则 |
| `summary` | general | 总评规则 |

---

## 技术特性

### 1. 模块化设计

```python
# 规则分类器（独立模块）
from server.services.rule_classifier import RuleClassifier

# 分类单个规则
intent = RuleClassifier.classify_rule(rule)

# 批量分组
grouped = RuleClassifier.group_rules_by_intent(rules, target_intents=['character'])

# 构建 LLM 输入
llm_data = RuleClassifier.build_rules_for_llm(
    matched_rules=rules,
    target_intents=['character'],
    max_rules_per_intent=10
)
```

### 2. 可扩展性

添加新规则类型映射：

```python
# 在 RuleClassifier.RULE_TYPE_TO_INTENT 中添加
RULE_TYPE_TO_INTENT = {
    # ... 现有映射 ...
    
    # 新增映射
    'new_rule_type': 'character',
    'another_type': 'wealth',
}
```

### 3. 性能优化

- 只传递用户查询意图相关的规则（减少 token）
- 每个意图最多 10 条规则（可配置）
- 规则内容限制 200 字符（避免过长）
- 使用缓存机制（避免重复计算）

---

## 向后兼容

### 现有功能完全不受影响

1. ✅ 规则匹配逻辑不变
2. ✅ API 响应结构不变
3. ✅ 前端展示逻辑不变
4. ✅ `matched_rules` 参数可选（默认 None）

### 渐进式增强

- 不传递 `matched_rules` → LLM 使用原有数据
- 传递 `matched_rules` → LLM 融合规则内容分析

---

## 测试验证

### 单元测试
```bash
python3 tests/test_rule_classifier.py
```

**测试结果**：
```
✅ 规则分类映射测试通过（16个测试用例）
✅ 规则分组测试通过
✅ 按意图过滤测试通过（character 过滤）
✅ LLM 数据构建测试通过
```

### 集成测试

测试场景：
1. ✅ 查询性格 → 只传递 character 规则
2. ✅ 查询财富 → 只传递 wealth 规则
3. ✅ 查询婚姻 → 传递 marriage 规则（含桃花）
4. ✅ 查询健康 → 传递 health 规则
5. ✅ 综合查询 → 传递所有规则

---

## 配置参数

### RuleClassifier 参数

```python
build_rules_for_llm(
    matched_rules: List[Dict],       # 匹配到的规则列表
    target_intents: List[str] = None,  # 目标意图（None=所有）
    max_rules_per_intent: int = 10     # 每个意图最多规则数
)
```

### FortuneLLMClient 参数

```python
analyze_fortune(
    intent: str,                     # 用户意图
    question: str,                   # 用户问题
    bazi_data: Dict,                 # 八字数据
    fortune_context: Dict,           # 流年大运
    matched_rules: List[Dict] = None,  # ⭐ 新增：规则列表
    stream: bool = False,            # 流式输出
    use_cache: bool = True           # 使用缓存
)
```

---

## 注意事项

### 1. Token 消耗

- 每条规则约 50-200 tokens
- 10 条规则约 500-2000 tokens
- 建议每个意图不超过 10 条规则

### 2. 规则质量

- 规则内容应简洁明确
- 避免重复或冗余规则
- 规则描述应具有命理专业性

### 3. 意图映射

- 十神命格规则 → character（确认）
- 事业规则 → character（性格影响事业）
- 桃花规则 → marriage（桃花影响婚姻）

---

## 未来扩展

### 1. 多意图支持

当前只支持单意图查询，未来可支持：
```python
target_intents=['character', 'wealth']  # 同时查询性格和财富
```

### 2. 规则优先级

根据规则 `priority` 字段排序，优先传递高优先级规则。

### 3. 动态规则数量

根据 token 预算动态调整每个意图的规则数量。

---

## 总结

✅ **模块化**：独立的规则分类模块
✅ **结构化**：清晰的数据流和映射关系
✅ **科学化**：合理的分类逻辑和性能优化
✅ **可扩展**：易于添加新规则类型
✅ **向后兼容**：不影响现有功能

**关键成果**：
- 十神命格规则正确映射到性格意图
- 只输出用户查询意图相关的分析
- 只传递用户查询意图相关的规则
- 输出格式与现有系统一致

---

**文档版本**：v1.0
**更新日期**：2025-11-26
**作者**：AI Assistant


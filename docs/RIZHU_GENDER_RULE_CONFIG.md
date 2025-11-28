# 日柱性别规则配置说明

## 📋 概述

本文档说明如何配置和使用**日柱性别动态查询规则**。该规则使用动态查询适配器机制，不需要预先配置所有60×2=120个日柱性别组合，而是根据计算出的八字信息动态查询。

## 🔧 配置方法

### 1. 规则配置文件位置

规则配置文件位于：`server/config/rules.json`

### 2. 日柱性别动态规则配置

在 `rules.json` 中添加以下配置：

```json
{
  "rule_id": "DYNAMIC_RIZHU_GENDER",
  "rule_name": "日柱性别动态查询",
  "rule_type": "rizhu_gender_dynamic",
  "priority": 100,
  "enabled": true,
  "conditions": {
    "all": [
      {"day_pillar": "*"},
      {"gender": "*"}
    ]
  },
  "content": {
    "type": "dynamic",
    "query_adapter": "RizhuGenderAnalyzer",
    "query_method": "analyze_rizhu_gender",
    "default_content": {
      "type": "description",
      "text": "暂无分析数据"
    }
  },
  "description": "根据日柱和性别动态查询命理分析（使用RizhuGenderAnalyzer适配器）"
}
```

### 3. 配置字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `rule_id` | 规则唯一标识 | `DYNAMIC_RIZHU_GENDER` |
| `rule_name` | 规则名称 | `日柱性别动态查询` |
| `rule_type` | 规则类型 | `rizhu_gender_dynamic` |
| `priority` | 优先级（数字越大优先级越高） | `100` |
| `enabled` | 是否启用 | `true` |
| `conditions` | 匹配条件 | 见下方说明 |
| `content` | 规则内容配置 | 见下方说明 |
| `description` | 规则描述 | 描述文本 |

#### 条件配置（conditions）

```json
{
  "all": [
    {"day_pillar": "*"},  // "*" 表示匹配任意日柱
    {"gender": "*"}       // "*" 表示匹配任意性别
  ]
}
```

**说明**：
- `day_pillar: "*"` - 通配符，匹配任意日柱（如"甲子"、"乙丑"等）
- `gender: "*"` - 通配符，匹配任意性别（"male"或"female"）
- `all` - 表示所有条件都必须满足（AND逻辑）

#### 内容配置（content）

```json
{
  "type": "dynamic",                      // 动态查询类型
  "query_adapter": "RizhuGenderAnalyzer", // 查询适配器名称
  "query_method": "analyze_rizhu_gender", // 查询方法名
  "default_content": {                     // 默认内容（查询失败时使用）
    "type": "description",
    "text": "暂无分析数据"
  }
}
```

**说明**：
- `type: "dynamic"` - 表示这是动态查询规则
- `query_adapter` - 查询适配器名称（已注册的适配器）
- `query_method` - 适配器的查询方法名
- `default_content` - 查询失败时的默认内容

## 📡 API 接口使用

### 1. 查询日柱性别规则（专用接口）

**接口**: `POST /api/v1/bazi/rules/query-rizhu-gender`

**请求示例**:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/query-rizhu-gender \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'
```

**响应示例**:
```json
{
  "success": true,
  "rizhu": "甲子",
  "gender": "male",
  "matched_rules": [
    {
      "rule_id": "DYNAMIC_RIZHU_GENDER",
      "rule_code": "DYNAMIC_RIZHU_GENDER",
      "rule_name": "日柱性别动态查询",
      "rule_type": "rizhu_gender_dynamic",
      "priority": 100,
      "content": {
        "type": "description",
        "items": [
          {
            "type": "description",
            "text": "为人聪明有智慧，富于同情心，个性温顺"
          },
          {
            "type": "description",
            "text": "多少会带些神经过敏，因此也常常自讨苦吃"
          }
          // ... 更多描述
        ]
      },
      "description": "根据日柱和性别动态查询命理分析（使用RizhuGenderAnalyzer适配器）"
    }
  ],
  "rule_count": 1,
  "message": "日柱甲子男命分析"
}
```

### 2. 通用规则匹配接口

**接口**: `POST /api/v1/bazi/rules/match`

**请求示例**（指定规则类型）:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "rule_types": ["rizhu_gender_dynamic"]
  }'
```

## 🔍 工作原理

### 1. 规则匹配流程

```
用户输入 → 计算八字 → 提取日柱和性别 → 匹配规则条件 → 匹配成功
```

### 2. 动态查询流程

```
匹配成功 → 检查规则内容类型 → 发现是 "dynamic" 类型
→ 调用查询适配器 QueryAdapterRegistry.query()
→ 实例化 RizhuGenderAnalyzer
→ 调用 analyze_rizhu_gender() 方法
→ 从 RIZHU_GENDER_CONFIG 字典动态查询
→ 返回查询结果
→ 格式化返回给用户
```

### 3. 查询适配器机制

- **注册机制**: `QueryAdapterRegistry` 自动注册现有分析器
- **已注册适配器**:
  - `RizhuGenderAnalyzer` - 日柱性别分析器
  - `DeitiesAnalyzer` - 神煞分析器

## ✅ 优势

1. **无需预配置**: 不需要预先配置120条规则（60日柱×2性别）
2. **动态查询**: 根据计算出的八字信息动态查询
3. **灵活扩展**: 可以轻松添加新的查询适配器
4. **统一接口**: 使用统一的规则引擎接口
5. **缓存支持**: 支持多级缓存，提高性能

## 🔧 扩展新的查询适配器

如果需要添加新的查询适配器，在 `server/engines/query_adapters.py` 中注册：

```python
from src.analyzers.your_analyzer import YourAnalyzer

QueryAdapterRegistry.register(
    'YourAnalyzer',
    YourAnalyzer,
    'analyze_method'  # 查询方法名
)
```

然后在规则配置中使用：

```json
{
  "content": {
    "type": "dynamic",
    "query_adapter": "YourAnalyzer",
    "query_method": "analyze_method"
  }
}
```

## 📝 注意事项

1. **规则文件格式**: 确保 `rules.json` 是有效的 JSON 格式
2. **适配器注册**: 确保查询适配器已正确注册
3. **通配符支持**: 使用 `"*"` 表示匹配任意值
4. **缓存机制**: 查询结果会自动缓存，提高性能
5. **错误处理**: 查询失败时会使用 `default_content`

## 🧪 测试

### 测试规则配置

```bash
# 测试规则加载
python -c "import sys; sys.path.insert(0, '.'); from server.services.rule_service import RuleService; engine = RuleService.get_engine(); print(f'规则数: {len(engine.rules)}')"
```

### 测试API接口

```bash
# 测试专用接口
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/query-rizhu-gender \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "14:30", "gender": "male"}'

# 测试通用接口
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "14:30", "gender": "male", "rule_types": ["rizhu_gender_dynamic"]}'
```

## 📚 相关文档

- **规则引擎使用文档**: `RULES_ENGINE_USAGE.md`
- **新增模块文档**: `NEW_MODULES_DOCUMENTATION.md`

---

**文档版本**: 1.0  
**最后更新**: 2025-11-05













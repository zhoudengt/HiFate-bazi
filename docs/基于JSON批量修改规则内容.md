# 基于 JSON 文件批量修改规则内容

## 概述

`scripts/batch_update_content_from_json.py` 是一个专门用于基于 JSON 文件批量修改规则内容的工具。

**核心特点：**
- ✅ **只修改 `content` 字段**
- ✅ **其他字段不可改动**（`rule_code`、`conditions`、`rule_name` 等保持不变）
- ✅ 支持批量处理
- ✅ 支持模拟运行（`--dry-run`）

## 使用流程

### 步骤 1：导出规则内容到 JSON 文件

```bash
# 导出所有规则
python scripts/batch_update_content_from_json.py --mode export \
  --output rules_content.json

# 导出特定规则
python scripts/batch_update_content_from_json.py --mode export \
  --output rules_content.json \
  --rule-code-pattern "MARR-10156"

# 导出特定类型的规则
python scripts/batch_update_content_from_json.py --mode export \
  --output marriage_rules_content.json \
  --rule-type marriage_ten_gods
```

### 步骤 2：编辑 JSON 文件

导出的 JSON 文件格式：

```json
[
  {
    "rule_code": "MARR-10156",
    "content": {
      "text": "外来女人争丈夫。",
      "type": "description"
    }
  },
  {
    "rule_code": "MARR-10157",
    "content": {
      "text": "其他规则内容",
      "type": "description"
    }
  }
]
```

**只修改 `content` 字段**，例如：

```json
[
  {
    "rule_code": "MARR-10156",
    "content": {
      "text": "注意关注，外来女人争丈夫。",
      "type": "description"
    }
  }
]
```

**注意：**
- `rule_code` 用于匹配规则，不要修改
- 只修改 `content` 字段的内容
- 保持 JSON 格式正确

### 步骤 3：测试更新（模拟运行）

```bash
python scripts/batch_update_content_from_json.py --mode import \
  --file rules_content.json \
  --dry-run
```

这会显示：
- 原内容 vs 新内容对比
- 哪些字段保持不变（`rule_name`、`conditions` 等）
- 不会实际更新数据库

### 步骤 4：执行实际更新

```bash
python scripts/batch_update_content_from_json.py --mode import \
  --file rules_content.json
```

## 完整示例

### 示例：修改规则 MARR-10156

```bash
# 1. 导出规则内容
python scripts/batch_update_content_from_json.py --mode export \
  --output rule_10156.json \
  --rule-code-pattern "MARR-10156"

# 2. 编辑 rule_10156.json，将 content.text 改为 "注意关注，外来女人争丈夫。"

# 3. 测试
python scripts/batch_update_content_from_json.py --mode import \
  --file rule_10156.json \
  --dry-run

# 4. 执行更新
python scripts/batch_update_content_from_json.py --mode import \
  --file rule_10156.json
```

## 参数说明

### Export 模式

- `--mode export` - 导出模式
- `--output` - 输出文件路径（必需）
- `--rule-type` - 规则类型筛选（可选）
- `--rule-code-pattern` - 规则代码模式（可选，支持 SQL LIKE）

### Import 模式

- `--mode import` - 导入模式
- `--file` - JSON 文件路径（必需）
- `--dry-run` - 模拟运行（可选，推荐先测试）

## 重要说明

1. **只修改 content 字段**：工具只会更新 `content` 字段，其他字段（`rule_code`、`conditions`、`rule_name`、`priority` 等）保持不变

2. **rule_code 用于匹配**：JSON 文件中的 `rule_code` 用于匹配数据库中的规则，不要修改

3. **自动更新版本号**：更新完成后会自动更新规则版本号，触发热加载

4. **建议先测试**：使用 `--dry-run` 参数先测试，确认无误后再执行实际更新

5. **JSON 格式**：确保 JSON 格式正确，特别是 `content` 字段的结构

## 常见问题

### Q: 如果规则不存在怎么办？

A: 工具会跳过不存在的规则，并在结果中显示 "未找到" 的数量。

### Q: 可以批量修改多个规则吗？

A: 可以，在 JSON 文件中添加多个规则对象即可。

### Q: 如何确保只修改了 content 字段？

A: 使用 `--dry-run` 参数可以看到对比信息，确认只修改了 `content` 字段。

### Q: 更新后规则没有生效？

A: 检查规则版本号是否已更新，服务是否支持热加载。可能需要重启服务。


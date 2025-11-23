# Excel 转规则内容 JSON 说明

## Excel 文件格式要求

### 必需的列

| 列名 | 说明 | 示例 |
|------|------|------|
| `rule_code` | 规则编号 | `MARR-10156` |
| `content_text` | 规则内容文本 | `注意关注，外来女人争丈夫。` |

### 可选的列

| 列名 | 说明 | 默认值 |
|------|------|--------|
| `content_type` | 内容类型 | `description` |

## Excel 文件示例

```
| rule_code   | content_text                    | content_type |
|-------------|--------------------------------|--------------|
| MARR-10156  | 注意关注，外来女人争丈夫。      | description  |
| MARR-10157  | 其他规则内容1                   | description  |
| MARR-10158  | 其他规则内容2                   | description  |
```

## 使用流程

### 步骤 1：创建 Excel 模板

```bash
python scripts/excel_to_rules_content_json.py --mode template \
  --template-output rules_template.xlsx
```

这会创建一个包含示例数据的 Excel 模板文件。

### 步骤 2：编辑 Excel 文件

在 Excel 中打开 `rules_template.xlsx`，编辑数据：

- **rule_code**: 填写规则编号（如 `MARR-10156`）
- **content_text**: 填写规则内容文本（如 `注意关注，外来女人争丈夫。`）
- **content_type**: 可选，默认为 `description`

### 步骤 3：转换为 JSON

```bash
python scripts/excel_to_rules_content_json.py --mode convert \
  --excel rules_template.xlsx \
  --output rules_content.json
```

### 步骤 4：导入更新

```bash
# 先测试
python scripts/batch_update_content_from_json.py --mode import \
  --file rules_content.json \
  --dry-run

# 执行实际更新
python scripts/batch_update_content_from_json.py --mode import \
  --file rules_content.json
```

## 高级用法

### 自定义列名

如果 Excel 文件的列名不同，可以指定：

```bash
python scripts/excel_to_rules_content_json.py --mode convert \
  --excel rules.xlsx \
  --output rules_content.json \
  --rule-code-column "规则编号" \
  --content-text-column "规则内容" \
  --content-type-column "内容类型"
```

### 指定工作表

如果 Excel 文件有多个工作表：

```bash
python scripts/excel_to_rules_content_json.py --mode convert \
  --excel rules.xlsx \
  --output rules_content.json \
  --sheet "规则表"
```

## 转换后的 JSON 格式

转换后的 JSON 文件格式：

```json
[
  {
    "rule_code": "MARR-10156",
    "content": {
      "text": "注意关注，外来女人争丈夫。",
      "type": "description"
    }
  },
  {
    "rule_code": "MARR-10157",
    "content": {
      "text": "其他规则内容1",
      "type": "description"
    }
  }
]
```

## 依赖安装

如果提示缺少 `pandas` 或 `openpyxl`，需要安装：

```bash
pip install pandas openpyxl
```

## 注意事项

1. **列名必须匹配**：Excel 文件必须包含 `rule_code` 和 `content_text` 列
2. **数据不能为空**：`rule_code` 和 `content_text` 不能为空
3. **只修改 content**：转换后的 JSON 只包含 `rule_code` 和 `content`，用于批量更新规则内容
4. **其他字段不变**：导入更新时，只修改 `content` 字段，其他字段（`conditions`、`rule_name` 等）保持不变


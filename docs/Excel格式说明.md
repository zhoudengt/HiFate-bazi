# Excel 文件格式说明

## Excel 文件列格式要求

### 必需的列

| 列名 | 说明 | 示例 | 是否必需 |
|------|------|------|---------|
| `rule_code` | 规则编号 | `MARR-10156` | ✅ 必需 |
| `content_text` | 规则内容文本 | `注意关注，外来女人争丈夫。` | ✅ 必需 |

### 可选的列

| 列名 | 说明 | 默认值 | 是否必需 |
|------|------|--------|---------|
| `content_type` | 内容类型 | `description` | ⭕ 可选 |

## Excel 文件示例

### 标准格式（推荐：rule_code 不带前缀）

```
| rule_code | content_text                    | content_type |
|-----------|--------------------------------|--------------|
| 10156     | 注意关注，外来女人争丈夫。      | description  |
| 10157     | 其他规则内容1                   | description  |
| 10158     | 其他规则内容2                   | description  |
```

**注意**：`rule_code` 列可以不带 `MARR-` 前缀，程序会自动添加。

### 带前缀格式（也支持）

```
| rule_code   | content_text                    | content_type |
|-------------|--------------------------------|--------------|
| MARR-10156  | 注意关注，外来女人争丈夫。      | description  |
| MARR-10157  | 其他规则内容1                   | description  |
```

如果 `rule_code` 已包含前缀，程序会保持不变。

### 最小格式（不包含 content_type）

```
| rule_code | content_text                    |
|-----------|--------------------------------|
| 10156     | 注意关注，外来女人争丈夫。      |
| 10157     | 其他规则内容1                   |
```

如果缺少 `content_type` 列，会自动使用默认值 `description`。

## 转换后的 JSON 格式

Excel 文件会转换为以下 JSON 格式：

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

## 使用步骤

### 1. 创建 Excel 模板

```bash
python scripts/excel_to_rules_content_json.py --mode template \
  --template-output rules_template.xlsx
```

### 2. 编辑 Excel 文件

在 Excel 中打开 `rules_template.xlsx`，填写数据：

- **rule_code**: 规则编号（如 `MARR-10156`）
- **content_text**: 规则内容文本（如 `注意关注，外来女人争丈夫。`）
- **content_type**: 内容类型（可选，默认为 `description`）

### 3. 转换为 JSON

```bash
python scripts/excel_to_rules_content_json.py --mode convert \
  --excel rules_template.xlsx \
  --output rules_content.json
```

### 4. 导入更新到数据库

```bash
# 先测试
python scripts/batch_update_content_from_json.py --mode import \
  --file rules_content.json \
  --dry-run

# 执行实际更新
python scripts/batch_update_content_from_json.py --mode import \
  --file rules_content.json
```

## 自定义列名

如果您的 Excel 文件使用不同的列名，可以指定：

```bash
python scripts/excel_to_rules_content_json.py --mode convert \
  --excel rules.xlsx \
  --output rules_content.json \
  --rule-code-column "规则编号" \
  --content-text-column "规则内容" \
  --content-type-column "内容类型"
```

## 自动添加前缀说明

程序会自动处理 `rule_code` 前缀：

- **纯数字**（如 `10156`）→ 自动添加 `MARR-` → `MARR-10156`
- **已有前缀**（如 `MARR-10156`）→ 保持不变
- **不含 '-' 的格式** → 自动添加前缀

**示例：**
- Excel 中写 `10156` → 转换为 `MARR-10156`
- Excel 中写 `MARR-10156` → 保持 `MARR-10156`

## 注意事项

1. **列名必须匹配**：Excel 文件必须包含 `rule_code` 和 `content_text` 列（或使用自定义列名）
2. **数据不能为空**：`rule_code` 和 `content_text` 不能为空，空行会被跳过
3. **自动添加前缀**：`rule_code` 可以不带 `MARR-` 前缀，程序会自动添加
4. **只修改 content**：转换后的 JSON 只包含 `rule_code` 和 `content`，用于批量更新规则内容
5. **其他字段不变**：导入更新时，只修改 `content` 字段，其他字段（`conditions`、`rule_name` 等）保持不变
6. **支持多个工作表**：如果 Excel 有多个工作表，可以使用 `--sheet` 参数指定

## 依赖安装

如果提示缺少依赖，需要安装：

```bash
pip install pandas openpyxl
```


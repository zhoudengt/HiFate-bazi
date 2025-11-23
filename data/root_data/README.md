# 根目录数据文件归档

本目录包含从项目根目录移动过来的所有 JSON 和 Excel 数据文件。

## 📋 文件列表

### 规则内容模板文件

#### JSON 模板
- `rules_content_template.json` - 规则内容JSON模板

#### Excel 模板
- `rules_content_template.xlsx` - 规则内容Excel模板（原始版本）
- `rules_content_template_final.xlsx` - 规则内容Excel模板（最终版本）
- `rules_content_template_new.xlsx` - 规则内容Excel模板（新版本）

### 规则内容示例/测试文件

#### JSON 示例
- `rules_content_example.json` - 规则内容示例数据
- `rules_content_final.json` - 规则内容最终数据
- `rules_content_from_excel.json` - 从Excel转换的规则内容数据
- `rules_content_test.json` - 规则内容测试数据

## 📝 使用说明

这些文件主要用于：
1. **模板文件**：作为批量导入/更新规则内容的模板
2. **示例文件**：展示规则内容的数据格式
3. **测试文件**：用于测试规则内容导入功能

## 🔗 相关脚本

- `scripts/excel_to_rules_content_json.py` - Excel转JSON脚本
- `scripts/batch_update_content_from_json.py` - 批量更新规则内容脚本

---

**归档日期**：2025-01-21  
**说明**：这些文件原本位于项目根目录，已统一移动到本目录以便管理。


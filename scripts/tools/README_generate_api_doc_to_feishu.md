# 接口文档生成工具使用说明

## 功能

自动解析 FastAPI 接口代码，生成标准格式的接口文档，并导出为 Markdown 文件供追加到飞书文档。

## 使用方法

### 基本用法

```bash
python3 scripts/tools/generate_api_doc_to_feishu.py \
  --file server/api/v1/unified_payment.py \
  --route /payment/unified/create \
  --provider stripe \
  --feishu-url https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb
```

### 参数说明

- `--file`: 接口文件路径（必填）
- `--route`: 接口路径，如 `/payment/unified/create`（可选，默认解析所有路由）
- `--provider`: 特定提供者，用于支付接口（可选），如 `stripe`, `payermax`
- `--feishu-url`: 飞书文档URL（必填）
- `--output`: 输出格式，默认 `markdown`（可选）

### 使用示例

#### 1. 生成 Stripe 支付接口文档

```bash
python3 scripts/tools/generate_api_doc_to_feishu.py \
  --file server/api/v1/unified_payment.py \
  --route /payment/unified/create \
  --provider stripe \
  --feishu-url https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb
```

#### 2. 生成 PayerMax 支付接口文档

```bash
python3 scripts/tools/generate_api_doc_to_feishu.py \
  --file server/api/v1/unified_payment.py \
  --route /payment/unified/create \
  --provider payermax \
  --feishu-url https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb
```

#### 3. 生成其他接口文档

```bash
python3 scripts/tools/generate_api_doc_to_feishu.py \
  --file server/api/v1/daily_fortune_calendar.py \
  --route /daily-fortune/calendar \
  --feishu-url https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb
```

## 设置 @ 别名（可选）

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
alias @generate_api_doc='python3 /Users/zhoudt/Downloads/project/HiFate-bazi/scripts/tools/generate_api_doc_to_feishu.py'
```

然后就可以使用：

```bash
@generate_api_doc --file server/api/v1/unified_payment.py --route /payment/unified/create --provider stripe --feishu-url https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb
```

## 飞书 API 配置（启用直接写入功能）

### 方式1：环境变量（推荐）

```bash
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"
```

### 方式2：命令行参数

```bash
python3 scripts/tools/generate_api_doc_to_feishu.py \
  --file server/api/v1/unified_payment.py \
  --route /payment/unified/create \
  --provider stripe \
  --feishu-url https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb \
  --feishu-app-id your_app_id \
  --feishu-app-secret your_app_secret
```

### 获取飞书 App ID 和 App Secret

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建应用或使用现有应用
3. 在"凭证与基础信息"中获取 App ID 和 App Secret
4. 确保应用已发布
5. 配置应用权限：需要"云文档"相关权限（查看、编辑文档）

### 文档权限设置

确保飞书文档的权限设置为"获得链接可编辑"或"所有人可编辑"。

## 输出

### 如果配置了飞书 API

工具会**直接追加内容到飞书文档**，无需手动操作。

### 如果未配置飞书 API

工具会在项目根目录或指定目录下生成 Markdown 文件，文件名格式：`api_doc_append_YYYYMMDD_HHMMSS.md`

生成的文件包含：
- 接口基本信息表格
- 请求参数表格
- 响应格式表格
- 弱网/断网处理说明
- 30分钟待支付流程说明（如果是支付接口）
- 使用说明（包含 curl 示例）

## 注意事项

1. **只追加不覆盖**：工具只追加内容到文档末尾，不会覆盖现有内容
2. **自动写入**：配置飞书 API 后，内容会自动写入飞书文档，无需手动操作
3. **降级处理**：如果飞书 API 配置失败，会自动降级为导出 Markdown 文件
4. **支持任何接口**：不限于支付接口，支持所有 FastAPI 接口
5. **自动解析**：自动从代码中提取路由、请求模型、响应模型等信息

## 测试工具

运行测试脚本验证功能：

```bash
python3 -c "
import sys
from pathlib import Path
project_root = Path('.').resolve()
sys.path.insert(0, str(project_root))
from scripts.tools.generate_api_doc_to_feishu import FeishuClient, FastAPIParser, DocGenerator

# 测试文档 ID 提取
client = FeishuClient('https://kgo2k5dye3.feishu.cn/docx/IHTKdY4rvop4BHx0N8Zc69N5nRb')
print(f'✅ 文档 ID: {client.document_id}')

# 测试 Markdown 转 blocks
test_md = '## 测试\n| 字段 | 值 |\n|------|-----|'
blocks = client._markdown_to_blocks(test_md)
print(f'✅ 成功转换 {len(blocks)} 个 blocks')
"
```

## 故障排除

### 解析失败
1. 检查文件路径是否正确
2. 检查接口路径是否匹配
3. 检查 Pydantic 模型定义格式是否正确
4. 查看工具输出的错误信息

### 飞书 API 写入失败
1. **检查 App ID 和 App Secret**：确保环境变量或命令行参数正确
2. **检查应用权限**：确保飞书应用有"云文档"相关权限
3. **检查文档权限**：确保文档设置为"获得链接可编辑"或"所有人可编辑"
4. **检查应用状态**：确保应用已发布
5. **查看错误信息**：工具会输出详细的错误信息，根据提示排查

### 降级到文件导出
如果飞书 API 配置失败，工具会自动降级为导出 Markdown 文件，可以手动复制到飞书文档。

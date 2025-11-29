# API接口文档生成说明

## 概述

本项目提供了自动生成API接口文档的工具，可以生成包含所有REST API和gRPC接口的Word文档。

## 使用方法

### 1. 安装依赖

```bash
# 激活虚拟环境（如果有）
source .venv/bin/activate

# 安装依赖
pip install python-docx
```

或者直接安装项目所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 生成文档

```bash
# 激活虚拟环境（如果有）
source .venv/bin/activate

# 运行生成脚本
python scripts/tools/generate_api_docs.py
```

### 3. 查看文档

生成的文档保存在：`docs/API接口文档.docx`

## 文档内容

生成的Word文档包含以下内容：

### 1. 接口汇总
- REST API统计（按请求方法分类）
- gRPC服务统计（按服务分类）

### 2. REST API接口文档
- 按模块分组的所有REST API接口
- 每个接口包含：
  - 请求方法和路径
  - 接口说明
  - 请求参数（字段名、类型、说明）
  - 请求示例
  - 响应示例

### 3. gRPC接口文档
- 所有gRPC服务定义
- 每个服务包含：
  - 服务名称
  - RPC方法列表
  - 消息定义（请求/响应类型）

### 4. gRPC-Web接口文档
- gRPC-Web网关支持的所有端点
- 调用方式和示例

## 扫描范围

### REST API
扫描目录：`server/api/v1/*.py`

包含的接口类型：
- 八字计算接口
- 运势分析接口
- 规则匹配接口
- 支付接口
- 认证接口
- 等等...

### gRPC服务
扫描目录：`proto/*.proto`

包含的服务：
- bazi_core (八字核心服务)
- bazi_fortune (大运流年服务)
- bazi_analyzer (八字分析服务)
- bazi_rule (规则匹配服务)
- fortune_analysis (运势分析服务)
- payment_service (支付服务)
- 等等...

## 注意事项

1. **依赖要求**：需要安装 `python-docx` 库
2. **Python版本**：建议使用 Python 3.9+
3. **文档格式**：生成的是Word文档（.docx格式）
4. **自动更新**：每次运行脚本都会重新扫描所有接口并生成最新文档

## 更新文档

当添加新的API接口或修改现有接口时，重新运行生成脚本即可更新文档：

```bash
python scripts/tools/generate_api_docs.py
```

## 文档结构

```
API接口文档.docx
├── 封面
├── 接口汇总
│   ├── REST API统计
│   └── gRPC服务统计
├── REST API接口文档
│   ├── bazi接口
│   ├── fortune接口
│   ├── payment接口
│   └── ...
├── gRPC接口文档
│   ├── BaziCoreService
│   ├── BaziFortuneService
│   └── ...
└── gRPC-Web接口文档
    ├── 支持的端点列表
    └── 调用示例
```

## 故障排查

### 问题1：ModuleNotFoundError: No module named 'docx'

**解决方案**：
```bash
pip install python-docx
```

### 问题2：文档生成失败

**检查项**：
1. 确认项目结构完整（server/api/v1/ 和 proto/ 目录存在）
2. 确认Python版本 >= 3.9
3. 查看错误日志，定位具体问题

### 问题3：文档内容不完整

**可能原因**：
1. API文件格式不符合规范
2. proto文件格式错误
3. 解析逻辑需要更新

**解决方案**：
检查具体的API文件，确保符合FastAPI和gRPC规范。

## 相关文件

- 生成脚本：`scripts/tools/generate_api_docs.py`
- 输出文档：`docs/API接口文档.docx`
- 依赖配置：`requirements.txt`


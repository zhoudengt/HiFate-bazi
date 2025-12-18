# 代码审查工具使用指南

## 📋 概述

本目录包含完整的代码审查检查工具，用于确保代码符合开发规范、安全性和质量要求。

## 🔍 核心检查项

### 1. 开发规范符合性检查
- 检查是否符合 `.cursorrules` 中的规范要求
- 检查硬编码路径
- 检查文件操作异常处理
- 检查 JSON 序列化规范
- 检查规则存储方式

**脚本**：`check_cursorrules.py`

### 2. 安全漏洞检查
- 检查 SQL 注入风险
- 检查 XSS 风险
- 检查敏感信息泄露
- 检查文件上传安全

**脚本**：`check_security.py`

### 3. 热更新支持检查
- 检查模块级全局状态初始化
- 检查单例类是否有 reset 方法

**脚本**：`check_hot_reload.py`

### 4. 编码方式检查
- 检查数据插入是否使用 UNHEX
- 检查数据查询是否使用 BINARY 比较

**脚本**：`check_encoding.py`

### 5. gRPC 端点注册检查
- 检查新增 API 端点是否已注册
- 检查注册方式是否正确

**脚本**：`check_grpc.py`

### 6. 测试覆盖检查
- 检查是否有对应的测试文件
- 检查测试覆盖率

**脚本**：`check_tests.py`

## 🚀 使用方法

### 方式 1：运行所有检查（推荐）

```bash
# 运行所有代码审查检查
bash scripts/review/run_all_checks.sh
```

**功能**：
- 自动检查所有变更的文件
- 运行 6 项核心检查
- 输出详细的检查报告
- 发现错误时退出（用于 CI/CD）

### 方式 2：运行单项检查

```bash
# 1. 开发规范符合性检查
python3 scripts/review/check_cursorrules.py

# 2. 安全漏洞检查
python3 scripts/review/check_security.py

# 3. 热更新支持检查
python3 scripts/review/check_hot_reload.py

# 4. 编码方式检查
python3 scripts/review/check_encoding.py

# 5. gRPC 端点注册检查
python3 scripts/review/check_grpc.py

# 6. 测试覆盖检查
python3 scripts/review/check_tests.py

# 7. 综合代码审查检查
python3 scripts/review/code_review_check.py
```

### 方式 3：检查指定文件

```bash
# 检查指定文件
python3 scripts/review/check_cursorrules.py server/api/v1/bazi.py
python3 scripts/review/check_security.py server/services/rule_service.py
```

## 📋 检查清单

每次提交 PR 前必须检查：

### 核心检查项（必须全部通过）
- [ ] 开发规范符合性检查通过
- [ ] 安全漏洞检查通过
- [ ] 热更新支持检查通过
- [ ] 编码方式检查通过
- [ ] gRPC 端点注册检查通过
- [ ] 测试覆盖检查通过

## 🔧 CI/CD 集成

代码审查检查已集成到 CI/CD 流程中（`.github/workflows/ci.yml`）：

1. **代码质量检查**（lint）
2. **代码审查检查**（code-review）- 运行所有 6 项核心检查
3. **单元测试**（test）

**检查结果**：
- ✅ 所有检查通过 → PR 可以合并
- ❌ 任何检查失败 → PR 无法合并（必须修复）

## 📚 相关文档

- **开发规范**：`.cursorrules` - "🔍 代码审查规范"章节
- **PR 模板**：`.github/pull_request_template.md`
- **CI/CD 配置**：`.github/workflows/ci.yml`

## ⚠️ 注意事项

1. **提交前检查**：建议在提交 PR 前本地运行检查脚本
2. **修复错误**：发现错误必须修复后才能合并
3. **警告处理**：警告不影响合并，但建议修复


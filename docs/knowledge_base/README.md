# 项目知识库

## 概述

项目知识库提供开发规范、常见问题、最佳实践、历史问题复盘等信息，帮助 AI 快速理解项目上下文，提高交互效率。

## 文件结构

```
docs/knowledge_base/
├── development_rules.md          # 开发规范摘要
├── common_issues.md              # 常见问题库
├── best_practices.md             # 最佳实践库
├── problem_history.md            # 历史问题复盘
└── context_templates/            # 上下文模板
    ├── api_development.md
    ├── rule_development.md
    └── frontend_development.md
```

## 使用方式

### AI 自动加载

开发助手会自动加载项目上下文和知识库：
```bash
python3 scripts/ai/dev_assistant.py --start
```

### 手动加载

使用上下文加载器：
```bash
# 加载项目上下文
python3 scripts/ai/context_loader.py --type api --summary

# 输出 JSON 格式
python3 scripts/ai/context_loader.py --type api --json
```

## 更新机制

### 开发规范更新

当 `.cursorrules` 更新时，同步更新 `development_rules.md`：
- 提取核心原则
- 提取开发规范摘要
- 提取热更新规范

### 问题复盘更新

每次问题复盘后，更新 `problem_history.md`：
- 记录问题描述
- 记录根因分析
- 记录解决方案
- 记录预防措施

### 最佳实践更新

发现新的最佳实践时，更新 `best_practices.md`：
- 记录实践内容
- 记录使用场景
- 记录效果评估

## 维护建议

1. **定期更新**：每次规范变更、问题复盘、发现最佳实践时更新
2. **保持简洁**：摘要控制在 1000 字符以内
3. **分类清晰**：按开发类型、问题类型分类
4. **易于查找**：使用清晰的标题和关键词


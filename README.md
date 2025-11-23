# HiFate-bazi 八字系统

> 完整的八字命理分析系统，基于 868 条专业规则

## 📋 项目简介

HiFate-bazi 是一个完整的八字命理分析系统，提供算法公式分析、运势预测、月运日运等功能。

### ✨ 核心功能

- 🔮 **算法公式分析**：基于 868 条规则的全面八字分析
- 💰 **财富分析**：财运、事业运势预测
- 💑 **婚配分析**：婚姻配对、感情运势
- 🏥 **身体分析**：健康状况、体质特征
- 🎭 **性格分析**：性格特点、命格分析
- 📅 **运势预测**：大运、流年、月运、日运
- 🔮 **十神命格**：十神分析、命格判断

### 🏗️ 技术架构

#### 后端服务（8个微服务）
- **主服务**（端口 8001）：Web API 服务器
- **八字核心**（端口 9001）：核心八字计算
- **八字运势**（端口 9002）：运势计算服务
- **八字分析**（端口 9003）：综合分析服务
- **规则服务**（端口 9004）：规则引擎服务
- **运势分析**（端口 9005）：运势分析服务
- **支付服务**（端口 9006）：支付集成服务
- **规则匹配**（端口 9007）：规则匹配服务

#### 前端页面
- 算法公式分析页面
- 运势分析页面
- 月运查询页面
- 日运查询页面
- 十神命格调试工具

#### 技术栈
- **后端**：Python 3.x, Flask, gRPC
- **前端**：HTML5, CSS3, JavaScript
- **数据库**：MySQL 8.0 (端口 13306)
- **缓存**：Redis (端口 16379)
- **协议**：gRPC, RESTful API

### 📁 项目结构

```
HiFate-bazi/
├── server/              # 主服务
│   ├── api/            # API 路由
│   ├── services/       # 业务逻辑
│   ├── engines/        # 规则引擎
│   └── db/             # 数据库连接
├── services/            # 微服务
│   ├── bazi_analyzer/  # 八字分析服务
│   ├── fortune_analysis/ # 运势分析服务
│   └── ...
├── src/                 # 核心计算库
│   ├── bazi_calculator.py
│   └── ...
├── frontend/            # 前端页面
│   ├── html/           # HTML 页面
│   ├── js/             # JavaScript
│   └── css/            # 样式文件
├── proto/               # gRPC 协议定义
├── scripts/             # 工具脚本
├── docs/                # 文档
└── tests/               # 测试

总计：443 个文件，130,904+ 行代码
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 8.0+
- Redis 6.0+
- Node.js 14+ (可选，用于前端开发)

### 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 配置数据库
mysql -h 127.0.0.1 -P 13306 -u root -p < server/db/schema.sql
```

### 启动服务

```bash
# 启动所有微服务
./start_all_services.sh

# 检查服务状态
./check_services.sh

# 停止所有服务
./stop_all_services.sh
```

### 访问前端

打开浏览器访问：
- 算法公式分析：http://localhost:8001/frontend/formula-analysis.html
- 运势分析：http://localhost:8001/frontend/fortune.html
- 月运查询：http://localhost:8001/frontend/bazi-monthly-fortune.html
- 日运查询：http://localhost:8001/frontend/bazi-daily-fortune.html

## 📖 文档

详细文档请查看 `docs/` 目录：

- [快速启动指南](docs/quick_start.md)
- [开发规范](docs/DEVELOPMENT_GUIDELINES.md)
- [API 文档](docs/bazi_api_structure.json)
- [规则系统架构](docs/rule_system_architecture.md)
- [微服务管理](docs/微服务管理快速参考.md)

## 🔧 开发规范

本项目遵循严格的开发规范，详见 [.cursorrules](.cursorrules) 和 [开发规范文档](docs/DEVELOPMENT_GUIDELINES.md)。

### 核心原则

1. **最小影响原则**：修改代码时不影响无关功能
2. **分层架构**：API → Service → Core 单向依赖
3. **代码质量**：完善的注释、错误处理、测试覆盖

## 🧪 测试

```bash
# 运行测试
python -m pytest tests/

# API 测试
./scripts/test_api.sh

# 前端测试
open frontend/formula-analysis.html
```

## 📊 规则系统

### 规则类型

- **FORMULA_WEALTH**：财富类规则
- **FORMULA_MARRIAGE**：婚配类规则
- **FORMULA_HEALTH**：身体类规则
- **FORMULA_CHARACTER**：性格类规则
- **FORMULA_SUMMARY**：总评类规则
- **FORMULA_SHISHEN**：十神命格规则

### 规则管理

规则存储在 MySQL 数据库 `bazi_rules` 表中，支持热更新和缓存管理。

详见：[规则系统架构](docs/rule_system_architecture.md)

## 🔐 安全性

- 数据库连接使用 `utf8mb4` 编码
- API 接口支持认证和授权
- 敏感配置使用环境变量
- 完善的错误处理和日志记录

## 📝 更新日志

### v1.0.0 (2025-11-23)
- ✅ 项目初始化
- ✅ 8个微服务架构搭建
- ✅ 868条规则系统完成
- ✅ 前端页面开发完成
- ✅ MCP 浏览器集成
- ✅ 完整的开发文档

## 👥 贡献指南

本项目为私有项目，如需参与开发请联系项目负责人。

## 📄 许可证

Copyright © 2025 HiFate. All rights reserved.

---

## 📮 联系方式

- Email: 643795362@qq.com
- GitHub: [@zhoudengt](https://github.com/zhoudengt)

---

**Built with ❤️ by HiFate Team**


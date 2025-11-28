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

---

## 📁 项目结构

```
HiFate-bazi/
├── server/                 # 主服务（HTTP API）
│   ├── api/               # API 路由层
│   │   └── v1/           # v1 版本 API
│   ├── services/          # 业务逻辑层
│   ├── engines/           # 规则引擎
│   ├── db/                # 数据库连接
│   ├── config/            # 服务配置
│   └── utils/             # 工具函数
│
├── services/               # 微服务（gRPC）
│   ├── bazi_core/         # 八字核心计算
│   ├── bazi_fortune/      # 运势计算
│   ├── bazi_analyzer/     # 八字分析
│   ├── bazi_rule/         # 规则引擎
│   ├── fortune_analysis/  # 运势分析
│   ├── payment_service/   # 支付服务
│   ├── intent_service/    # 意图识别
│   └── prompt_optimizer/  # 提示优化
│
├── src/                    # 核心计算库
│   ├── bazi_calculator.py # 八字计算核心
│   ├── bazi_config/       # 八字配置数据
│   ├── analyzers/         # 分析器
│   └── clients/           # 微服务客户端
│
├── frontend/               # 前端页面
│   ├── *.html             # HTML 页面
│   ├── js/                # JavaScript
│   └── css/               # 样式文件
│
├── proto/                  # gRPC 协议定义
│   ├── *.proto            # 协议文件
│   └── generated/         # 生成的 Python 代码
│
├── scripts/                # 脚本工具
│   ├── services/          # 服务管理脚本
│   ├── tests/             # 测试脚本
│   └── tools/             # 工具脚本
│
├── config/                 # 配置文件
│   └── services.env       # 服务配置
│
├── docs/                   # 文档
│   ├── README_DOCKER.md   # Docker 部署
│   ├── README_FACE_V2.md  # 面相分析
│   └── ...                # 其他文档
│
├── tests/                  # 测试代码
│
├── start.sh               # 快捷启动脚本
├── stop.sh                # 快捷停止脚本
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 构建
└── docker-compose.yml     # Docker 编排
```

### 🏗️ 架构分层

```
┌─────────────────────────────────────────────────┐
│                   前端 (Frontend)                │
│              HTML + JavaScript + CSS             │
└─────────────────────┬───────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────┐
│                主服务 (Server)                   │
│           FastAPI + Uvicorn (8001)              │
│  ┌─────────┬─────────┬─────────┬─────────┐     │
│  │   API   │ Service │ Engine  │   DB    │     │
│  └────┬────┴────┬────┴────┬────┴────┬────┘     │
└───────┼─────────┼─────────┼─────────┼──────────┘
        │ gRPC    │         │         │
┌───────▼─────────▼─────────▼─────────▼──────────┐
│                微服务 (Services)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │bazi_core │ │ fortune  │ │  rule    │ ...    │
│  │  (9001)  │ │  (9002)  │ │ (9004)   │        │
│  └──────────┘ └──────────┘ └──────────┘        │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                核心库 (Src)                      │
│        bazi_calculator + 配置 + 分析器           │
└─────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- MySQL 8.0+ (端口 13306)
- Redis 7.0+ (端口 16379)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 方式一：快捷脚本
./start.sh

# 方式二：指定脚本
./scripts/services/start_all_services.sh

# 停止服务
./stop.sh
```

### 访问页面

| 功能 | 地址 |
|------|------|
| 算法公式分析 | http://localhost:8001/frontend/formula-analysis.html |
| 运势分析 | http://localhost:8001/frontend/fortune.html |
| 月运查询 | http://localhost:8001/frontend/bazi-monthly-fortune.html |
| 日运查询 | http://localhost:8001/frontend/bazi-daily-fortune.html |

---

## 🐳 Docker 部署

```bash
# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

详见：[Docker 部署指南](docs/README_DOCKER.md)

---

## 📖 文档索引

| 文档 | 说明 |
|------|------|
| [开发规范](docs/DEVELOPMENT_GUIDELINES.md) | 开发规范和代码标准 |
| [Docker 部署](docs/README_DOCKER.md) | Docker 部署指南 |
| [快速开始](docs/快速开始-开发者必读.md) | 开发者入门指南 |
| [规则系统](docs/rule_system_architecture.md) | 规则引擎架构 |
| [API 文档](docs/接口测试命令.md) | API 接口说明 |

---

## 🔧 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Web API | 8001 | HTTP API 主服务 |
| bazi_core | 9001 | 八字核心计算 |
| bazi_fortune | 9002 | 运势计算 |
| bazi_analyzer | 9003 | 八字分析 |
| bazi_rule | 9004 | 规则引擎 |
| fortune_analysis | 9005 | 运势分析 |
| payment_service | 9006 | 支付服务 |
| fortune_rule | 9007 | 规则匹配 |
| intent_service | 9008 | 意图识别 |
| prompt_optimizer | 9009 | 提示优化 |
| MySQL | 13306 | 数据库 |
| Redis | 16379 | 缓存 |

---

## 📝 开发规范

1. **最小影响原则**：修改代码时不影响无关功能
2. **分层架构**：API → Service → Core 单向依赖
3. **不读取外部文件**：配置数据固化到代码/数据库

详见：[.cursorrules](.cursorrules)

---

## 📄 许可证

Copyright © 2025 HiFate. All rights reserved.

---

**Built with ❤️ by HiFate Team**

# HiFate-bazi 八字系统

> 完整的八字命理分析系统，基于 868+ 条专业规则，支持 AI 驱动的智能运势分析

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![gRPC](https://img.shields.io/badge/gRPC-1.60+-blue.svg)](https://grpc.io/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

## 📋 项目简介

HiFate-bazi 是一个完整的八字命理分析系统，采用微服务架构，提供算法公式分析、运势预测、智能运势分析、面相手相、办公桌风水等功能。

### ✨ 核心功能

- 🔮 **算法公式分析**：基于 868+ 条规则的全面八字分析（财富、婚姻、事业、性格、健康等）
- 📅 **运势预测**：大运、流年、月运、日运全方位运势分析
- 🤖 **智能运势分析**：AI 驱动的智能运势分析，支持自然语言提问
- 🎭 **十神命格**：十神分析、命格判断
- 👤 **面相手相**：基于 AI 的面相手相分析
- 🏢 **办公桌风水**：基于 YOLOv8 的物品检测和风水分析
- 💰 **支付服务**：集成 Stripe 支付
- 🧪 **A/B 测试**：支持功能开关和灰度发布

---

## 🏗️ 系统架构

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Frontend)                        │
│              HTML + JavaScript + CSS (静态页面)                │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/gRPC-Web
┌───────────────────────────▼─────────────────────────────────┐
│                    主服务 (Web API)                           │
│              FastAPI + Uvicorn (Port 8001)                    │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐       │
│  │   API   │ Service │ Engine  │   DB    │  Utils  │       │
│  └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┘       │
└───────┼─────────┼─────────┼─────────┼─────────┼────────────┘
        │ gRPC    │         │         │         │
┌───────▼─────────▼─────────▼─────────▼─────────▼────────────┐
│                    微服务层 (gRPC Services)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │bazi_core │ │ fortune   │ │ analyzer  │ │  rule    │ ...  │
│  │  (9001)  │ │  (9002)   │ │  (9003)   │ │ (9004)   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │fortune_  │ │ payment   │ │  intent  │ │optimizer │ ...  │
│  │analysis  │ │  (9006)   │ │  (9008)   │ │  (9009)   │      │
│  │  (9005)  │ └──────────┘ └──────────┘ └──────────┘      │
│  └──────────┘                                                │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                    数据存储层                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                      │
│  │  MySQL   │ │  Redis    │ │  Models  │                      │
│  │  (13306) │ │ (16379)   │ │  Cache   │                      │
│  └──────────┘ └──────────┘ └──────────┘                      │
└───────────────────────────────────────────────────────────────┘
```

### 服务端口清单

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| **Web API** | 8001 | HTTP/gRPC-Web | 主服务，对外提供 API |
| **bazi_core** | 9001 | gRPC | 八字核心计算服务 |
| **bazi_fortune** | 9002 | gRPC | 大运流年计算服务 |
| **bazi_analyzer** | 9003 | gRPC | 八字分析服务 |
| **bazi_rule** | 9004 | gRPC | 规则匹配服务 |
| **fortune_analysis** | 9005 | gRPC | 运势分析服务 |
| **payment_service** | 9006 | gRPC | 支付服务 |
| **fortune_rule** | 9007 | gRPC | 运势规则服务 |
| **intent_service** | 9008 | gRPC | 意图识别服务（混合架构） |
| **prompt_optimizer** | 9009 | gRPC | 提示优化服务 |
| **desk_fengshui** | 9010 | gRPC | 办公桌风水分析服务 |
| **MySQL** | 13306 | TCP | 数据库 |
| **Redis** | 16379 | TCP | 缓存 |

---

## 📁 项目结构

```
HiFate-bazi/
├── server/                 # 主服务（HTTP API）
│   ├── api/               # API 路由层
│   │   ├── v1/           # v1 版本 API
│   │   │   ├── smart_fortune.py    # 智能运势分析 API
│   │   │   ├── formula_analysis.py # 算法公式分析 API
│   │   │   └── ...                # 其他 API
│   │   └── grpc_gateway.py        # gRPC-Web 网关
│   ├── services/          # 业务逻辑层
│   ├── engines/           # 规则引擎
│   ├── utils/             # 工具函数
│   │   ├── ab_test.py            # A/B 测试工具
│   │   ├── feature_flag.py       # 功能开关工具
│   │   └── performance_monitor.py # 性能监控工具
│   ├── config/            # 服务配置
│   └── db/                # 数据库连接
│
├── services/               # 微服务（gRPC）
│   ├── bazi_core/        # 八字核心计算
│   ├── bazi_fortune/     # 运势计算
│   ├── bazi_analyzer/    # 八字分析
│   ├── bazi_rule/        # 规则引擎
│   ├── fortune_analysis/ # 运势分析
│   ├── payment_service/  # 支付服务
│   ├── intent_service/   # 意图识别（混合架构）
│   │   ├── classifier.py         # 混合分类器
│   │   ├── local_classifier.py   # 本地 BERT 模型
│   │   └── rule_postprocessor.py # 规则后处理
│   ├── prompt_optimizer/ # 提示优化
│   └── desk_fengshui/    # 办公桌风水（YOLOv8）
│
├── src/                   # 核心计算库
│   ├── bazi_calculator.py # 八字计算核心
│   ├── bazi_config/       # 八字配置数据
│   ├── analyzers/         # 分析器
│   └── clients/           # 微服务客户端
│
├── frontend/              # 前端页面
│   ├── index.html                    # 主页面
│   ├── formula-analysis.html         # 算法公式分析
│   ├── smart-fortune.html            # 智能运势分析
│   ├── smart-fortune-stream.html     # 智能运势分析（流式版）
│   ├── fortune.html                  # 运势分析
│   ├── desk-fengshui.html           # 办公桌风水
│   ├── face-analysis-v2.html        # 面相分析
│   └── ...                          # 其他页面
│
├── proto/                 # gRPC 协议定义
│   ├── *.proto            # 协议文件
│   └── generated/         # 生成的 Python 代码
│
├── scripts/                # 脚本工具
│   ├── services/          # 服务管理脚本
│   ├── migration/         # 数据迁移脚本
│   ├── deployment/        # 部署脚本（灰度发布、回滚）
│   ├── tests/             # 测试脚本
│   └── tools/             # 工具脚本
│
├── docs/                   # 文档
│   ├── Docker生产部署完整指南.md
│   ├── A_B测试和灰度发布指南.md
│   ├── 智能运势分析Bot提示词-知识库优先版.md
│   └── ...                # 其他文档
│
├── tests/                  # 测试代码
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── api/               # API 测试
│
├── config/                 # 配置文件
│   └── services.env       # 服务配置
│
├── start.sh               # 快捷启动脚本
├── stop.sh                # 快捷停止脚本
├── deploy.sh              # 一键部署脚本
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 构建
└── docker-compose.yml     # Docker 编排
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **MySQL**: 8.0+ (端口 13306)
- **Redis**: 7.0+ (端口 16379)
- **操作系统**: macOS / Linux / Windows

### 安装依赖

```bash
# 克隆项目
git clone https://gitee.com/zhoudengtang/hifate-prod.git
cd HiFate-bazi

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

复制 `env.template` 并配置：

```bash
cp env.template .env
```

编辑 `.env` 文件，配置数据库、Redis、AI 服务等：

```bash
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=13306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=hifate_bazi

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=16379

# Coze AI 配置（智能运势分析）
COZE_ACCESS_TOKEN=your_token
COZE_BOT_ID=your_bot_id
```

### 启动服务

```bash
# 方式一：一键启动（推荐）
./start.sh

# 方式二：手动启动
python3 server/start.py

# 停止服务
./stop.sh
```

### 访问页面

| 功能 | 地址 |
|------|------|
| 首页 | http://localhost:8001/frontend/index.html |
| 算法公式分析 | http://localhost:8001/frontend/formula-analysis.html |
| 智能运势分析 | http://localhost:8001/frontend/smart-fortune-stream.html |
| 运势分析 | http://localhost:8001/frontend/fortune.html |
| 月运查询 | http://localhost:8001/frontend/bazi-monthly-fortune.html |
| 日运查询 | http://localhost:8001/frontend/bazi-daily-fortune.html |
| 办公桌风水 | http://localhost:8001/frontend/desk-fengshui.html |
| 面相分析 | http://localhost:8001/frontend/face-analysis-v2.html |

---

## 🐳 Docker 部署

### 开发环境

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 生产环境

```bash
# 使用一键部署脚本（推荐）
./deploy.sh
# 选择 1) 完整部署

# 或手动部署
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Docker 基础镜像优化

项目支持 Docker 基础镜像优化，大幅加速部署：

```bash
# 首次构建基础镜像（仅需一次）
./scripts/docker/build_base.sh

# 检查基础镜像状态
./scripts/docker/check_base.sh

# 正常部署（快速，10-20秒）
docker compose up -d --build web
```

详见：[Docker 生产部署完整指南](docs/Docker生产部署完整指南.md)

---

## 🎯 核心功能详解

### 1. 算法公式分析

基于 868+ 条专业规则的全面八字分析，支持：

- 💰 **财富分析**：财运、投资、收入预测
- 💑 **婚配分析**：婚姻配对、感情运势
- 🎭 **性格分析**：性格特点、命格分析
- 🏥 **身体分析**：健康状况、体质特征
- 📜 **总评分析**：综合命理评价

**API**: `POST /api/v1/bazi/formula-analysis`

### 2. 智能运势分析

AI 驱动的智能运势分析，支持自然语言提问：

- 🤖 **意图识别**：混合架构（关键词过滤 + 本地 BERT 模型 + LLM 兜底）
- 📊 **规则匹配**：自动匹配相关规则类型
- 🔮 **LLM 深度解读**：基于 Coze AI 的深度分析
- 📈 **性能监控**：端到端性能监控和优化
- ⚡ **流式输出**：支持流式响应，提升用户体验

**API**: `GET /api/v1/smart-fortune/smart-analyze-stream`

**响应时间**: 平均 < 100ms（不包含 LLM 分析）

### 3. 意图识别混合架构

高性能意图识别系统，响应时间 < 1秒：

- **第1层**：关键词过滤（0ms，处理 60% 的明确问题）
- **第2层**：本地 BERT 模型（50-100ms，处理 20% 的简单问题）
- **第3层**：规则后处理（10-20ms，时间意图解析）
- **第4层**：LLM 兜底（500-1000ms，仅处理 5% 的模糊问题）

**平均响应时间**: < 100ms

### 4. 办公桌风水分析

基于 YOLOv8 的物品检测和传统风水规则：

- 📸 **物品检测**：YOLOv8 自动识别办公桌物品
- 🧭 **方位计算**：青龙位、白虎位、朱雀位、玄武位
- 🔮 **风水分析**：结合八字喜用神、忌神进行个性化分析
- 📊 **规则匹配**：基于数据库的风水规则匹配

**技术栈**: YOLOv8 (ultralytics>=8.0.0)

---

## 🧪 A/B 测试和灰度发布

项目支持完整的 A/B 测试和灰度发布功能：

### 功能开关

```python
from server.utils.feature_flag import get_feature_flag_manager

manager = get_feature_flag_manager()
if manager.is_enabled("新功能", user_id=user_id):
    # 使用新功能
    result = new_feature.process()
else:
    # 使用旧功能
    result = old_feature.process()
```

### A/B 测试

```python
from server.utils.ab_test import get_ab_test_manager

manager = get_ab_test_manager()
variant = manager.assign_variant("新算法测试", user_id=user_id)
if variant == "A":
    result = old_algorithm.calculate()
else:
    result = new_algorithm.calculate()
```

详见：[A/B 测试和灰度发布指南](docs/A_B测试和灰度发布指南.md)

---

## 📖 文档索引

| 文档 | 说明 |
|------|------|
| [开发规范](.cursorrules) | 完整的开发规范和代码标准 |
| [Docker 生产部署完整指南](docs/Docker生产部署完整指南.md) | Docker 部署详细指南 |
| [A/B 测试和灰度发布指南](docs/A_B测试和灰度发布指南.md) | A/B 测试和灰度发布使用指南 |
| [智能运势分析 Bot 提示词](docs/智能运势分析Bot提示词-知识库优先版.md) | Coze Bot 配置和提示词 |
| [快速开始-开发者必读](docs/快速开始-开发者必读.md) | 开发者入门指南 |
| [规则系统架构](docs/rule_system_architecture.md) | 规则引擎架构说明 |
| [API 接口文档](docs/接口测试命令.md) | API 接口说明和测试命令 |

---

## 🔧 开发规范

### 核心原则

1. **🔴 零停机原则**：所有设计必须支持不停机更新
2. **🔌 gRPC 优先**：服务间交互必须使用 gRPC
3. **📜 规则数据库化**：规则存数据库，支持热更新，禁止从文件读取
4. **🔄 向后兼容**：只加不删，保持兼容
5. **✅ 先测试后提交**：修改后立即测试
6. **🔐 安全优先**：遵循安全最佳实践
7. **🧪 A/B 测试优先**：新功能必须支持 A/B 测试和灰度发布

详见：[.cursorrules](.cursorrules)

---

## 🛠️ 技术栈

### 后端

- **Web 框架**: FastAPI + Uvicorn
- **RPC 框架**: gRPC + Protobuf
- **数据库**: MySQL 8.0
- **缓存**: Redis 7.0
- **AI 模型**: 
  - Coze AI (智能运势分析)
  - BERT/RoBERTa (意图识别)
  - YOLOv8 (物品检测)

### 前端

- **技术**: HTML5 + JavaScript (ES6+) + CSS3
- **通信**: gRPC-Web + REST API
- **UI 框架**: 原生 JavaScript（无框架依赖）

### 部署

- **容器化**: Docker + Docker Compose
- **基础镜像优化**: 支持预构建基础镜像，加速部署
- **部署脚本**: 一键部署脚本（`deploy.sh`）

---

## 📊 性能指标

### 意图识别性能

| 场景 | 占比 | 响应时间 | 准确率 |
|------|------|---------|--------|
| 关键词明确 | 60% | <10ms | 95%+ |
| 简单问题 | 20% | 50-100ms | 85-90% |
| 复杂问题 | 15% | 100-200ms | 80-85% |
| 模糊问题 | 5% | 500-1000ms | 90%+ |

**平均响应时间**: < 100ms

### 智能运势分析性能

| 阶段 | 目标耗时 | 说明 |
|------|---------|------|
| 意图识别 | < 100ms | 混合架构 |
| 八字计算 | < 50ms | 本地计算 |
| 规则匹配 | < 200ms | 数据库查询 |
| LLM 深度解读 | < 2000ms | 可选功能 |

**总耗时目标**：
- 不包含流年大运和 LLM：< 500ms
- 包含流年大运：< 2000ms
- 包含流年大运和 LLM：< 5000ms

---

## 🚀 部署到生产

### Gitee 仓库

- **仓库地址**: https://gitee.com/zhoudengtang/hifate-prod.git
- **默认分支**: master

### 一键部署

```bash
# 使用部署脚本
./deploy.sh

# 选择操作：
# 1) 完整部署（推荐）
# 2) 仅推送到 Gitee
# 3) 仅更新服务器
# ...
```

### 生产服务器

- **服务器**: 123.57.216.15 (阿里云 ECS)
- **部署路径**: /opt/HiFate-bazi

详见：[Docker 生产部署完整指南](docs/Docker生产部署完整指南.md)

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行 API 测试
pytest tests/api/
```

### 测试脚本

```bash
# 端到端测试
./scripts/tests/test_e2e_all_functions.sh

# 架构改进测试
./scripts/tests/test_architecture_improvements.py
```

---

## 📝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m '[新增] 添加新功能'`)
4. 推送到分支 (`git push gitee feature/AmazingFeature`)
5. 创建 Pull Request

### 提交规范

```
[类型] 简短描述

- 修改文件：列出文件
- 功能说明：详细说明
- 测试情况：测试结果
```

**类型标签**：
- `[新增]` - 新功能
- `[修复]` - Bug 修复
- `[优化]` - 性能优化
- `[重构]` - 代码重构
- `[规则]` - 规则相关变更
- `[配置]` - 配置修改

---

## 📄 许可证

Copyright © 2025 HiFate. All rights reserved.

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [gRPC](https://grpc.io/) - 高性能 RPC 框架
- [Coze AI](https://www.coze.cn/) - AI 能力支持
- [YOLOv8](https://github.com/ultralytics/ultralytics) - 物品检测模型

---

**Built with ❤️ by HiFate Team**

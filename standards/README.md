# HiFate-bazi 开发标准（规范文档统一入口）

## 概述

本目录为项目**规范文档统一入口**，包含架构规范、命名规范、运维规范等。

- **架构与编码** - 目录结构、命名、测试、服务治理
- **运维与流程** - 热更新、gRPC、规则开发、部署、安全、LLM 开发

---

## 一、架构与编码规范

| 文档 | 说明 | 适用人员 |
|------|------|----------|
| [01_目录结构标准.md](01_目录结构标准.md) | 项目目录结构规范 | 所有开发者 |
| [02_命名规范.md](02_命名规范.md) | 代码命名约定 | 所有开发者 |
| [03_开发者手册.md](03_开发者手册.md) | 快速开始、开发流程、检查清单 | 新人必读 |
| [04_测试规范.md](04_测试规范.md) | 测试编写规范 | 所有开发者 |
| [06_服务治理规范.md](06_服务治理规范.md) | 服务注册、熔断、限流 | 所有开发者 |
| [07_可观测性规范.md](07_可观测性规范.md) | 日志、监控、追踪 | 所有开发者 |
| [09_关键年份架构规范.md](09_关键年份架构规范.md) | 关键年份数据层统一 + 业务层策略 | 流式接口开发者 |

---

## 二、运维与流程规范

| 文档 | 说明 | 对应 .cursorrules |
|------|------|-------------------|
| [08_数据编排架构规范.md](08_数据编排架构规范.md) | 数据编排 + 流式接口基类（BaseAnalysisStreamHandler） | 数据编排、流式接口 |
| [hot-reload.md](hot-reload.md) | 热更新详细规范 | 热更新 |
| [grpc-protocol.md](grpc-protocol.md) | gRPC 协议与序列化 | gRPC |
| [rule-development.md](rule-development.md) | 规则开发详细规范 | 规则开发 |
| [deployment.md](deployment.md) | 部署（增量、灰度、门控） | 部署 |
| [security.md](security.md) | 安全规范 | 安全 |
| [llm-development.md](llm-development.md) | 大模型开发流程 | LLM |
| [database-connection.md](database-connection.md) | 数据库连接 + 增量同步无锁 | - |
| [payment.md](payment.md) | 支付系统（Stripe + PayerMax） | 支付 |
| [标准测试接口清单.md](标准测试接口清单.md) | 21 个标准测试接口 | 回归测试 |

---

## 三、变更记录

| 日期 | 变更 |
|------|------|
| 2026-02-17 | 规范精简：9 mdc→6；26 standards→20。合并 00-global+01-quick-commands→.cursorrules；gated-deploy+release-workflow→deploy.mdc；11_流式接口→08；incremental-sync→database-connection |
| 2026-02-10 | 新增 09_关键年份架构规范 |
| 2026-02-06 | 编排层两阶段并行；新增 标准测试接口清单 |
| 2026-01-31 | 规范统一入口为 standards/ |

---

## 四、代码模板

templates/：api_template.py、service_template.py

---

## 五、独立工具

Stream Profiler：tools/stream_profiler/（流式接口耗时测量）

---

## 六、使用说明

1. 开发时：参考 .cursorrules
2. 深入学习：本目录详细文档
3. 部署/上线：@deploy.mdc 或 standards/deployment.md

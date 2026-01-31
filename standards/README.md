# 📋 HiFate-bazi 开发标准（规范文档统一入口）

## 概述

本目录为项目**规范文档统一入口**，包含架构规范、命名规范、运维规范等。

- 📁 **架构与编码** - 目录结构、命名、测试、检查清单、服务治理
- 📋 **运维与流程** - 热更新、gRPC、规则开发、部署、安全、LLM 开发

---

## 一、架构与编码规范（01-07）

| 文档 | 说明 | 适用人员 |
|------|------|----------|
| [01_目录结构标准.md](01_目录结构标准.md) | 项目目录结构规范 | 所有开发者 |
| [02_命名规范.md](02_命名规范.md) | 代码命名约定 | 所有开发者 |
| [03_开发者手册.md](03_开发者手册.md) | 快速开始指南 | 新人必读 |
| [04_测试规范.md](04_测试规范.md) | 测试编写规范 | 所有开发者 |
| [05_功能开发检查清单.md](05_功能开发检查清单.md) | 开发检查清单 | 所有开发者 |
| [06_服务治理规范.md](06_服务治理规范.md) | 服务注册、熔断、限流 | 所有开发者 |
| [07_可观测性规范.md](07_可观测性规范.md) | 日志、监控、追踪 | 所有开发者 |

---

## 二、运维与流程规范

| 文档 | 说明 | 对应 .cursorrules 章节 |
|------|------|----------------------|
| [08_数据编排架构规范.md](08_数据编排架构规范.md) | 🔴 数据编排架构（最高优先级） | 数据编排架构原则 |
| [hot-reload.md](hot-reload.md) | 热更新详细规范 | 热更新强制规范 |
| [grpc-protocol.md](grpc-protocol.md) | gRPC 协议与序列化 | gRPC 交互规范 |
| [rule-development.md](rule-development.md) | 规则开发详细规范 | 规则开发规范 |
| [deployment.md](deployment.md) | 部署（增量部署、灰度发布） | 部署规范 |
| [security.md](security.md) | 安全规范 | 安全规范 |
| [testing.md](testing.md) | 测试开发详细规范 | 测试规范 |
| [llm-development.md](llm-development.md) | 大模型开发流程 | LLM 规范 |
| [performance-monitoring.md](performance-monitoring.md) | 性能监控 | 性能监控 |
| [database-connection.md](database-connection.md) | 数据库连接规范 | - |
| [incremental-sync-no-lock.md](incremental-sync-no-lock.md) | 增量同步无锁方案 | - |

---

## 三、变更记录

| 日期 | 变更 |
|------|------|
| 2026-01-31 | 文档精简：删除 docs/、knowledge_base、checklists、需求等；规范统一入口为 standards/；详见 `01_目录结构标准.md` 迁移记录 |

---

## 四、代码模板

`templates/` 目录包含标准代码模板：

| 模板 | 说明 |
|------|------|
| `api_template.py` | API 路由模板 |
| `service_template.py` | 服务类模板 |

---

## 五、使用说明

1. **开发时**：参考 `.cursorrules` 获取核心规范和快速参考
2. **深入学习**：查看本目录下的详细规范文档
3. **规范更新**：先更新本目录文档，再同步 `.cursorrules` 中的核心要点


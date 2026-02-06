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
| [10_上线流程与CI-CD规范.md](10_上线流程与CI-CD规范.md) | 🔴 **上线流程（AI必读）** | 所有开发者/AI模型 |

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
| [payment.md](payment.md) | 支付系统规范（Stripe + PayerMax） | 支付开发 |

---

## 三、变更记录

| 日期 | 变更 |
|------|------|
| 2026-02-06 | 完善热更新与上线流程规范：新增 /verify、/history 端点文档，修正 RELOAD_ORDER，新增 Reload Guard、Worker ACK 机制说明，更新常见问题 |
| 2026-02-05 | 新增 `10_上线流程与CI-CD规范.md`：完整上线流程、测试接口清单、所有AI模型必须遵循 |
| 2026-02-05 | 新增 `.cursor/rules/release-workflow.mdc`：上线流程规则文件 |
| 2026-02-04 | 新增 API 回归测试规范：`scripts/evaluation/api_regression_test.py`、CI/CD 集成、部署后验证 |
| 2026-02-04 | 支付渠道优化：只启用 Stripe + PayerMax，添加客户端缓存，接口秒出 |
| 2026-01-31 | 文档精简：删除 docs/、knowledge_base、checklists、需求等；规范统一入口为 standards/；详见 `01_目录结构标准.md` 迁移记录 |

---

## 四、代码模板

`templates/` 目录包含标准代码模板：

| 模板 | 说明 |
|------|------|
| `api_template.py` | API 路由模板 |
| `service_template.py` | 服务类模板 |

---

## 五、独立工具（与 server 解耦）

| 工具名称 | 路径 | 说明 | 规范引用 |
|----------|------|------|----------|
| 流式接口各环节耗时测试工具（Stream Profiler） | `tools/stream_profiler/` | 流式接口各阶段耗时与效率测量，用于后续各流式接口测试 | [04_测试规范.md](04_测试规范.md) 十一、[llm-development.md](llm-development.md) 流式接口优化规范 |

**约定**：工具修改时，须同步更新 `tools/stream_profiler/README.md` 及本目录中引用该工具的规范（如 04_测试规范、llm-development）。

---

## 六、使用说明

1. **开发时**：参考 `.cursorrules` 获取核心规范和快速参考
2. **深入学习**：查看本目录下的详细规范文档
3. **规范更新**：先更新本目录文档，再同步 `.cursorrules` 中的核心要点


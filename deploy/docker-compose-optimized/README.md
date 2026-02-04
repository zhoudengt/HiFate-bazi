# Docker Compose 优化配置

## 概述

这是优化后的 Docker Compose 配置，使用 `x-` 扩展减少重复配置，提高可维护性。

## 目录结构

```
deploy/docker-compose-optimized/
├── base.yml              # 基础配置（包含所有服务定义和 x- 扩展）
├── envs/
│   ├── production.yml    # 生产环境覆盖
│   └── development.yml   # 开发环境覆盖
└── README.md             # 本文档
```

## 优化内容

### 1. 使用 x- 扩展减少重复

原来的配置中，每个微服务都有重复的：
- 环境变量配置
- 网络配置
- 重启策略
- 资源限制

现在通过 `x-microservice-base`、`x-grpc-service` 等扩展模板统一定义。

### 2. 环境分离

- `base.yml`: 包含所有服务的基础定义
- `envs/production.yml`: 生产环境特定配置（资源限制、日志级别等）
- `envs/development.yml`: 开发环境特定配置（源代码挂载、调试模式等）

## 使用方式

### 开发环境

```bash
docker-compose -f deploy/docker-compose-optimized/base.yml \
               -f deploy/docker-compose-optimized/envs/development.yml up -d
```

### 生产环境

```bash
docker-compose -f deploy/docker-compose-optimized/base.yml \
               -f deploy/docker-compose-optimized/envs/production.yml up -d
```

## 迁移说明

### 从现有配置迁移

1. **备份现有配置**
   ```bash
   cp docker-compose.yml docker-compose.yml.backup
   cp docker-compose.prod.yml docker-compose.prod.yml.backup
   ```

2. **测试新配置**
   ```bash
   # 开发环境测试
   docker-compose -f deploy/docker-compose-optimized/base.yml \
                  -f deploy/docker-compose-optimized/envs/development.yml config
   
   # 生产环境测试
   docker-compose -f deploy/docker-compose-optimized/base.yml \
                  -f deploy/docker-compose-optimized/envs/production.yml config
   ```

3. **验证服务启动**
   ```bash
   docker-compose -f deploy/docker-compose-optimized/base.yml \
                  -f deploy/docker-compose-optimized/envs/development.yml up -d
   
   # 检查服务状态
   docker-compose -f deploy/docker-compose-optimized/base.yml \
                  -f deploy/docker-compose-optimized/envs/development.yml ps
   ```

4. **确认无误后替换原文件**

### 注意事项

- 迁移前务必备份现有配置
- 在测试环境验证后再应用到生产环境
- 确保环境变量（.env 文件）配置正确

## 配置对比

| 项目 | 原配置 | 优化后 |
|------|--------|--------|
| 文件数量 | 11 | 3 |
| 重复代码 | 90%+ | <10% |
| 可维护性 | 低 | 高 |
| 环境切换 | 复杂 | 简单 |

## 扩展新服务

在 `base.yml` 中添加新服务：

```yaml
services:
  new-service:
    <<: *grpc-service  # 复用 gRPC 服务模板
    container_name: hifate-new-service
    ports:
      - "${NEW_SERVICE_PORT:-9011}:9011"
    command: python services/new_service/grpc_server.py
```

然后在各环境覆盖文件中添加特定配置。

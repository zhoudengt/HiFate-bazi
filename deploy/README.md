# HiFate 双机 Docker 部署方案

## 架构概览

```
用户请求 → DNS → Node1/Node2 公网IP
                    │
    ┌───────────────┴───────────────┐
    │                               │
┌───▼───┐                       ┌───▼───┐
│ Node1 │ (2C8G)                │ Node2 │ (2C8G)
├───────┤                       ├───────┤
│Nginx  │◄─────负载均衡─────────►│Nginx  │
│Web    │                       │Web    │
│微服务 │                       │微服务 │
│MySQL主│───────复制───────────►│MySQL从│
│Redis主│───────复制───────────►│Redis从│
└───────┘                       └───────┘
```

## 目录结构

```
deploy/
├── README.md                    # 本文件
├── docs/                        # 部署文档
│   ├── 01-架构说明.md
│   ├── 02-ECS初始化.md
│   ├── 03-首次部署.md
│   ├── 04-日常运维.md
│   └── 05-故障处理.md
├── docker/                      # Docker Compose 配置
│   ├── docker-compose.prod.yml  # 生产环境主配置
│   ├── docker-compose.node1.yml # Node1 专用（主库）
│   └── docker-compose.node2.yml # Node2 专用（从库）
├── nginx/                       # Nginx 配置
│   ├── nginx.conf
│   └── conf.d/hifate.conf
├── mysql/                       # MySQL 主从配置
│   ├── master.cnf
│   └── slave.cnf
├── redis/                       # Redis 主从配置
│   ├── master.conf
│   └── slave.conf
├── scripts/                     # 部署脚本
│   ├── init-ecs.sh
│   ├── deploy.sh
│   ├── rollback.sh
│   └── health-check.sh
└── env/                         # 环境变量
    └── env.template
```

## 快速开始

### 1. ECS 初始化（两台机器都执行）

```bash
curl -fsSL https://raw.githubusercontent.com/your-repo/HiFate-bazi/master/deploy/scripts/init-ecs.sh | bash
```

### 2. 配置环境变量

```bash
cd /opt/HiFate-bazi
cp deploy/env/env.template .env
vim .env  # 编辑配置
```

### 3. 部署

```bash
# Node1（主节点）
bash deploy/scripts/deploy.sh node1

# Node2（从节点）
bash deploy/scripts/deploy.sh node2
```

## 详细文档

- [01-架构说明](docs/01-架构说明.md) - 整体架构和设计原理
- [02-ECS初始化](docs/02-ECS初始化.md) - 服务器初始化步骤
- [03-首次部署](docs/03-首次部署.md) - 首次部署完整流程
- [04-日常运维](docs/04-日常运维.md) - 日常运维命令
- [05-故障处理](docs/05-故障处理.md) - 故障排查和处理

## CI/CD

推送代码到 master 分支会自动触发部署：
1. 构建 Docker 镜像
2. 推送到 ACR
3. 滚动部署到 Node1 → Node2

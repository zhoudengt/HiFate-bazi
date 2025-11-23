# gRPC 迁移指南

## 概述

本项目已完成从 HTTP RESTful API 到 gRPC + Protocol Buffers 的迁移。所有微服务现在支持 gRPC 协议进行内部通信。

## 架构变更

### 服务列表

- **bazi_core** (端口 9001): 八字排盘核心计算服务
- **bazi_fortune** (端口 9002): 大运流年计算服务
- **bazi_analyzer** (端口 9003): 八字分析服务
- **bazi_rule** (端口 9004): 规则匹配服务
- **web_app** (端口 8001): Web 应用（仍使用 HTTP，对外提供 RESTful API）

### 协议选择

- **内部微服务通信**: 使用 gRPC（唯一协议）
- **外部 API**: 仍使用 HTTP RESTful API

## 使用方法

### 启动服务

所有微服务现在**仅支持 gRPC 协议**：

```bash
./start_all_services.sh
```

### 环境变量配置

```bash
# gRPC 格式（host:port，不带 http://）
export BAZI_CORE_SERVICE_URL="127.0.0.1:9001"
export BAZI_FORTUNE_SERVICE_URL="127.0.0.1:9002"
export BAZI_ANALYZER_SERVICE_URL="127.0.0.1:9003"
export BAZI_RULE_SERVICE_URL="127.0.0.1:9004"
```

### 客户端使用

所有客户端现在**仅支持 gRPC 协议**：

```python
from src.clients.bazi_core_client_grpc import BaziCoreClient

client = BaziCoreClient(base_url="127.0.0.1:9001")
result = client.calculate_bazi("1990-05-15", "14:30", "male")
```

## 文件结构

```
proto/
├── bazi_core.proto          # bazi_core 服务定义
├── bazi_fortune.proto       # bazi_fortune 服务定义
├── bazi_analyzer.proto      # bazi_analyzer 服务定义
├── bazi_rule.proto          # bazi_rule 服务定义
└── generated/               # 生成的 Python 代码
    ├── bazi_core_pb2.py
    ├── bazi_core_pb2_grpc.py
    └── ...

services/
├── bazi_core/
│   ├── main.py              # HTTP 服务（向后兼容）
│   └── grpc_server.py       # gRPC 服务
├── bazi_fortune/
│   ├── main.py
│   └── grpc_server.py
├── bazi_analyzer/
│   ├── main.py
│   └── grpc_server.py
└── bazi_rule/
    ├── main.py
    └── grpc_server.py

src/clients/
├── bazi_core_client.py      # HTTP 客户端（向后兼容）
├── bazi_core_client_grpc.py # gRPC 客户端
├── bazi_fortune_client.py
├── bazi_fortune_client_grpc.py
├── bazi_rule_client.py
└── bazi_rule_client_grpc.py
```

## 重新生成 gRPC 代码

如果修改了 `.proto` 文件，需要重新生成 Python 代码：

```bash
bash scripts/generate_grpc_code.sh
```

## 性能优势

gRPC 相比 HTTP RESTful API 的优势：

1. **性能**: 使用 Protocol Buffers 二进制序列化，比 JSON 更快更小
2. **类型安全**: 强类型定义，编译时检查
3. **流式处理**: 支持客户端流、服务器流和双向流
4. **跨语言**: Protocol Buffers 支持多种编程语言
5. **HTTP/2**: 基于 HTTP/2，支持多路复用和头部压缩

## 迁移完成

- ✅ 所有微服务已完全迁移到 gRPC
- ✅ 所有客户端代码已更新为使用 gRPC
- ✅ HTTP 服务代码已保留但不再使用（可删除）
- ✅ 外部 API（web_app）仍使用 HTTP RESTful API

## 测试

### 测试 gRPC 服务

```python
from src.clients.bazi_core_client_grpc import BaziCoreClient

client = BaziCoreClient(base_url="127.0.0.1:9001")
result = client.calculate_bazi("1990-05-15", "14:30", "male")
print(result)
```

### 健康检查

```python
client = BaziCoreClient(base_url="127.0.0.1:9001")
is_healthy = client.health_check()
print(f"服务健康状态: {is_healthy}")
```

## 故障排查

### 服务无法启动

1. 检查端口是否被占用：`lsof -ti:9001`
2. 查看日志：`tail -f logs/bazi_core_9001.log`
3. 检查 gRPC 代码是否已生成：`ls proto/generated/`

### 客户端连接失败

1. 确认服务已启动：`ps aux | grep grpc_server`
2. 检查环境变量：`echo $BAZI_CORE_SERVICE_URL`
3. 确认 URL 格式正确（gRPC: `host:port`，HTTP: `http://host:port`）

## 依赖项

已添加到 `requirements.txt`:

```
grpcio==1.70.0
grpcio-tools==1.70.0
protobuf==5.28.3
```

安装依赖：

```bash
pip install -r requirements.txt
```


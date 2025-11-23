# HiFate系统操作指南

## 目录

- [系统架构](#系统架构)
- [环境准备](#环境准备)
- [启动服务](#启动服务)
- [停止服务](#停止服务)
- [服务状态检查](#服务状态检查)
- [接口测试](#接口测试)
- [日志查看](#日志查看)
- [故障排查](#故障排查)

---

## 系统架构

### 服务列表

| 服务名称 | 端口 | 协议 | 说明 |
|---------|------|------|------|
| **web_app** | 8001 | HTTP (FastAPI) | Web 应用，对外提供 RESTful API |
| **bazi_core** | 9001 | gRPC | 八字排盘核心计算服务 |
| **bazi_fortune** | 9002 | gRPC | 大运流年计算服务 |
| **bazi_analyzer** | 9003 | gRPC | 八字分析服务 |
| **bazi_rule** | 9004 | gRPC | 规则匹配服务 |

### 架构图

```
外部客户端
    ↓ HTTP RESTful API
[FastAPI Web App] (端口 8001)
    ↓ gRPC 调用
    ├─→ [bazi_core] (gRPC, 端口 9001)
    ├─→ [bazi_fortune] (gRPC, 端口 9002)
    ├─→ [bazi_analyzer] (gRPC, 端口 9003)
    └─→ [bazi_rule] (gRPC, 端口 9004)
```

---

## 环境准备

### 1. 安装依赖

```bash
# 进入项目目录
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境变量配置（可选）

创建或编辑 `.env` 文件：

```bash
# 微服务地址（gRPC 格式：host:port）
BAZI_CORE_SERVICE_URL=127.0.0.1:9001
BAZI_FORTUNE_SERVICE_URL=127.0.0.1:9002
BAZI_ANALYZER_SERVICE_URL=127.0.0.1:9003
BAZI_RULE_SERVICE_URL=127.0.0.1:9004

# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=testdb

# Redis 配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379

# Coze AI 配置（可选）
COZE_ACCESS_TOKEN=your_token
COZE_BOT_ID=your_bot_id
```

---

## 启动服务

### 方式一：一键启动所有服务（推荐）

```bash
# 进入项目根目录
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 确保脚本有执行权限
chmod +x start_all_services.sh

# 启动所有服务
./start_all_services.sh
```

**输出示例：**
```
>>> 使用 gRPC 协议启动微服务
>>> 启动 bazi_core（gRPC，端口 9001） …
    ✓ 已启动 PID=12345，日志: logs/bazi_core_9001.log
>>> 启动 bazi_fortune（gRPC，端口 9002） …
    ✓ 已启动 PID=12346，日志: logs/bazi_fortune_9002.log
>>> 启动 bazi_analyzer（gRPC，端口 9003） …
    ✓ 已启动 PID=12347，日志: logs/bazi_analyzer_9003.log
>>> 启动 bazi_rule（gRPC，端口 9004） …
    ✓ 已启动 PID=12348，日志: logs/bazi_rule_9004.log
>>> 启动 web_app（端口 8001） …
    ✓ 已启动 PID=12349，日志: logs/web_app_8001.log
✅ 所有服务启动流程完成。
```

### 方式二：手动启动单个服务

#### 启动 gRPC 微服务

```bash
# 启动 bazi_core
python services/bazi_core/grpc_server.py --port 9001

# 启动 bazi_fortune
python services/bazi_fortune/grpc_server.py --port 9002

# 启动 bazi_analyzer
python services/bazi_analyzer/grpc_server.py --port 9003

# 启动 bazi_rule
python services/bazi_rule/grpc_server.py --port 9004
```

#### 启动 Web 应用

```bash
# 方式1：使用启动脚本
python server/start.py

# 方式2：使用 uvicorn 直接启动
uvicorn server.main:app --host 0.0.0.0 --port 8001
```

---

## 停止服务

### 方式一：一键停止所有服务（推荐）

```bash
# 进入项目根目录
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 确保脚本有执行权限
chmod +x stop_all_services.sh

# 停止所有服务
./stop_all_services.sh
```

**输出示例：**
```
>>> 停止 web_app（端口 8001，PID=12349） …
    ✓ 已停止。
>>> 停止 bazi_rule（端口 9004，PID=12348） …
    ✓ 已停止。
>>> 停止 bazi_analyzer（端口 9003，PID=12347） …
    ✓ 已停止。
>>> 停止 bazi_fortune（端口 9002，PID=12346） …
    ✓ 已停止。
>>> 停止 bazi_core（端口 9001，PID=12345） …
    ✓ 已停止。
✅ 所有服务停止流程完成。
```

### 方式二：手动停止单个服务

```bash
# 查找进程 PID
ps aux | grep grpc_server
ps aux | grep "server/start.py"

# 停止指定进程
kill <PID>

# 或强制停止
kill -9 <PID>
```

### 方式三：通过端口停止服务

```bash
# 查找占用端口的进程
lsof -ti:8001  # Web 应用
lsof -ti:9001  # bazi_core
lsof -ti:9002  # bazi_fortune
lsof -ti:9003  # bazi_analyzer
lsof -ti:9004  # bazi_rule

# 停止进程
kill $(lsof -ti:8001)
kill $(lsof -ti:9001)
```

---

## 服务状态检查

### 检查服务是否运行

```bash
# 检查所有 Python 进程
ps aux | grep -E "grpc_server|server/start.py" | grep -v grep

# 检查端口是否被占用
lsof -ti:8001,9001,9002,9003,9004

# 或使用 netstat
netstat -an | grep -E "8001|9001|9002|9003|9004"
```

### 健康检查

#### Web 应用健康检查

```bash
curl http://127.0.0.1:8001/health
```

**预期响应：**
```json
{
  "status": "ok"
}
```

#### gRPC 服务健康检查（使用 Python）

```python
import grpc
from proto.generated import bazi_core_pb2, bazi_core_pb2_grpc

channel = grpc.insecure_channel('127.0.0.1:9001')
stub = bazi_core_pb2_grpc.BaziCoreServiceStub(channel)
response = stub.HealthCheck(bazi_core_pb2.HealthCheckRequest())
print(response.status)  # 应该输出 "ok"
```

---

## 接口测试

### 1. 基础八字计算

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'
```

**预期响应：**
```json
{
  "success": true,
  "data": {
    "bazi": {
      "basic_info": {
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "lunar_date": {...},
        "gender": "male"
      },
      "bazi_pillars": {
        "year": {"stem": "庚", "branch": "午"},
        "month": {"stem": "辛", "branch": "巳"},
        "day": {"stem": "甲", "branch": "子"},
        "hour": {"stem": "辛", "branch": "未"}
      },
      "details": {...},
      "ten_gods_stats": {...},
      "elements": {...}
    },
    "rizhu": "甲子",
    "matched_rules": [...]
  }
}
```

### 2. 生成界面信息（包含命宫、身宫等）

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/interface \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "name": "张三",
    "location": "北京",
    "latitude": 39.9042,
    "longitude": 116.4074
  }'
```

### 3. 计算详细八字（包含大运流年序列）

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/detail \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "current_time": "2025-01-15 10:00"
  }'
```

### 4. AI 分析接口

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "user_question": "请分析我的财运和事业"
  }'
```

### 5. 规则匹配接口

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "rule_types": ["marriage_ten_gods", "marriage_element"],
    "include_bazi": true
  }'
```

### 6. 获取规则类型列表

```bash
curl http://127.0.0.1:8001/api/v1/bazi/rules/types
```

### 使用 Python 测试

```python
import requests

# 基础八字计算
url = "http://127.0.0.1:8001/api/v1/bazi/calculate"
data = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
}

response = requests.post(url, json=data)
print(response.json())
```

### 使用 Postman 测试

1. 导入以下配置到 Postman：

```json
{
  "info": {
    "name": "HiFateAPI",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "基础八字计算",
      "request": {
        "method": "POST",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"solar_date\": \"1990-05-15\",\n  \"solar_time\": \"14:30\",\n  \"gender\": \"male\"\n}"
        },
        "url": {
          "raw": "http://127.0.0.1:8001/api/v1/bazi/calculate",
          "protocol": "http",
          "host": ["127", "0", "0", "1"],
          "port": "8001",
          "path": ["api", "v1", "bazi", "calculate"]
        }
      }
    }
  ]
}
```

---

## 日志查看

### 查看所有服务日志

```bash
# 查看 Web 应用日志
tail -f logs/web_app_8001.log

# 查看微服务日志
tail -f logs/bazi_core_9001.log
tail -f logs/bazi_fortune_9002.log
tail -f logs/bazi_analyzer_9003.log
tail -f logs/bazi_rule_9004.log
```

### 查看最近的错误日志

```bash
# 查看所有服务的错误日志
grep -i error logs/*.log

# 查看最近的错误（最近100行）
tail -n 100 logs/*.log | grep -i error
```

### 实时监控所有日志

```bash
# 使用 multitail（需要安装：brew install multitail）
multitail logs/*.log

# 或使用 tail -f 组合
tail -f logs/*.log
```

---

## 故障排查

### 问题1：服务启动失败

**症状：** 启动脚本显示启动失败或进程立即退出

**排查步骤：**

1. 检查端口是否被占用：
```bash
lsof -ti:8001,9001,9002,9003,9004
```

2. 查看日志文件：
```bash
tail -n 50 logs/<service_name>_<port>.log
```

3. 检查依赖是否安装：
```bash
pip list | grep -E "grpcio|fastapi|uvicorn"
```

4. 检查 Python 版本：
```bash
python --version  # 需要 Python 3.8+
```

### 问题2：gRPC 服务连接失败

**症状：** 客户端报错 "Connection refused" 或 "Failed to connect"

**排查步骤：**

1. 确认服务是否运行：
```bash
ps aux | grep grpc_server
```

2. 检查端口监听状态：
```bash
lsof -ti:9001  # 应该返回 PID
```

3. 检查环境变量：
```bash
echo $BAZI_CORE_SERVICE_URL  # 应该是 127.0.0.1:9001（不带 http://）
```

4. 测试 gRPC 连接：
```python
import grpc
channel = grpc.insecure_channel('127.0.0.1:9001')
try:
    grpc.channel_ready_future(channel).result(timeout=5)
    print("连接成功")
except grpc.FutureTimeoutError:
    print("连接超时")
```

### 问题3：API 返回 500 错误

**排查步骤：**

1. 查看 Web 应用日志：
```bash
tail -f logs/web_app_8001.log
```

2. 检查微服务是否正常运行：
```bash
ps aux | grep -E "grpc_server|server/start"
```

3. 检查数据库连接：
```bash
# 测试 MySQL 连接
mysql -h localhost -u root -p testdb
```

4. 检查 Redis 连接（如果使用）：
```bash
redis-cli ping  # 应该返回 PONG
```

### 问题4：PID 文件残留

**症状：** 启动时提示服务已在运行，但实际未运行

**解决方法：**

```bash
# 清理所有 PID 文件
rm -f logs/*.pid

# 或清理特定服务的 PID 文件
rm -f logs/bazi_core_9001.pid
```

### 问题5：依赖缺失

**症状：** 导入错误 "ModuleNotFoundError"

**解决方法：**

```bash
# 重新安装依赖
pip install -r requirements.txt

# 或安装特定包
pip install grpcio grpcio-tools protobuf fastapi uvicorn
```

---

## 常用命令速查

```bash
# 启动所有服务
./start_all_services.sh

# 停止所有服务
./stop_all_services.sh

# 查看服务状态
ps aux | grep -E "grpc_server|server/start"

# 查看端口占用
lsof -ti:8001,9001,9002,9003,9004

# 查看日志
tail -f logs/web_app_8001.log

# 健康检查
curl http://127.0.0.1:8001/health

# 测试接口
curl -X POST http://127.0.0.1:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"1990-05-15","solar_time":"14:30","gender":"male"}'
```

---

## 性能优化建议

### 1. 调整线程池大小

编辑 `server/start.py`：
```python
uvicorn.run(
    "server.main:app",
    workers=4,  # 根据 CPU 核心数调整
    limit_concurrency=1000,
)
```

### 2. 启用缓存

确保 Redis 运行，系统会自动使用缓存。

### 3. 监控资源使用

```bash
# 查看进程资源使用
top -p $(pgrep -f "grpc_server|server/start")

# 或使用 htop
htop
```

---

## 附录

### API 文档

启动服务后，访问 Swagger UI：
```
http://127.0.0.1:8001/docs
```

### 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `BAZI_CORE_SERVICE_URL` | bazi_core 服务地址 | `127.0.0.1:9001` |
| `BAZI_FORTUNE_SERVICE_URL` | bazi_fortune 服务地址 | `127.0.0.1:9002` |
| `BAZI_ANALYZER_SERVICE_URL` | bazi_analyzer 服务地址 | `127.0.0.1:9003` |
| `BAZI_RULE_SERVICE_URL` | bazi_rule 服务地址 | `127.0.0.1:9004` |
| `MYSQL_HOST` | MySQL 主机 | `localhost` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_DATABASE` | MySQL 数据库名 | `testdb` |

---

**最后更新：** 2025-01-15


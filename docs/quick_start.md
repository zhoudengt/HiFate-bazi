# 快速开始指南

## 🚀 快速启动

```bash
# 1. 进入项目目录
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 启动所有服务
./start_all_services.sh
```

## 🛑 快速停止

```bash
# 停止所有服务
./stop_all_services.sh
```

## ✅ 健康检查

```bash
# 检查 Web 应用
curl http://127.0.0.1:8001/health

# 检查服务进程
ps aux | grep -E "grpc_server|server/start"
```

## 📝 接口测试示例

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

### 2. 详细八字（含大运流年）

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/detail \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'
```

### 3. AI 分析

```bash
curl -X POST http://127.0.0.1:8001/api/v1/bazi/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "user_question": "请分析我的财运"
  }'
```

## 📚 完整文档

详细操作指南请查看：[操作指南](./operation_guide.md)

## 🔍 常用命令

```bash
# 查看日志
tail -f logs/web_app_8001.log

# 查看服务状态
lsof -ti:8001,9001,9002,9003,9004

# 查看 API 文档
open http://127.0.0.1:8001/docs
```


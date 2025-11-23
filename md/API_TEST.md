# API接口测试指南

## 接口信息

- **服务地址**: http://127.0.0.1:8001
- **API文档**: http://127.0.0.1:8001/docs (Swagger UI)
- **健康检查**: http://127.0.0.1:8001/health

## 接口列表

### 1. 健康检查
```
GET /health
```

**响应示例**:
```json
{
  "status": "healthy"
}
```

---

### 2. 八字计算接口
```
POST /api/v1/bazi/calculate
```

**请求参数**:
```json
{
  "solar_date": "1990-05-15",    // 阳历日期，格式：YYYY-MM-DD
  "solar_time": "14:30",          // 出生时间，格式：HH:MM
  "gender": "male"               // 性别：male(男) 或 female(女)
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "rizhu": "庚辰",
    "bazi": {
      "basic_info": {
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male",
        "lunar_date": {...}
      },
      "bazi_pillars": {
        "year": {"stem": "庚", "branch": "午"},
        "month": {"stem": "辛", "branch": "巳"},
        "day": {"stem": "庚", "branch": "辰"},
        "hour": {"stem": "癸", "branch": "未"}
      },
      "details": {...}
    },
    "matched_rules": [...]
  }
}
```

## 测试方法

### 方法1: 使用Python测试脚本（推荐）

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行测试脚本（使用默认测试用例）
python test_api.py

# 使用自定义参数测试
python test_api.py 1990-05-15 14:30 male
```

### 方法2: 使用curl命令

```bash
# 健康检查
curl http://127.0.0.1:8001/health

# 八字计算
curl -X POST http://127.0.0.1:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'
```

### 方法3: 使用bash脚本

```bash
chmod +x test_api.sh
./test_api.sh
```

### 方法4: 使用Swagger UI（浏览器）

1. 启动服务: `python server/start.py`
2. 打开浏览器访问: http://127.0.0.1:8001/docs
3. 在Swagger UI界面中直接测试接口

## 测试用例

### 测试用例1: 男性
```json
{
  "solar_date": "1990-05-15",
  "solar_time": "14:30",
  "gender": "male"
}
```

### 测试用例2: 女性
```json
{
  "solar_date": "1988-01-07",
  "solar_time": "08:00",
  "gender": "female"
}
```

## 常见错误

### 1. 端口被占用
如果端口8001被占用，启动脚本会自动切换到下一个可用端口（8002, 8003...）

### 2. 日期格式错误
- 正确格式: `YYYY-MM-DD` (例如: 1990-05-15)
- 错误格式: `1990/05/15` 或 `1990-5-15`

### 3. 时间格式错误
- 正确格式: `HH:MM` (例如: 14:30)
- 错误格式: `14:30:00` 或 `2:30 PM`

### 4. 性别参数错误
- 正确值: `male` 或 `female`
- 错误值: `男`、`女`、`M`、`F` 等

## 注意事项

1. 确保服务已启动: `python server/start.py`
2. 如果服务运行在其他端口，请修改测试脚本中的 `BASE_URL`
3. 八字计算可能需要几秒钟时间，请耐心等待















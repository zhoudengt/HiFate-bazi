# 居家风水接口 curl 调用示例

## 一、流式分析接口（推荐）

**端点**：`POST /api/v2/home-fengshui/analyze/stream`  
**Content-Type**：`multipart/form-data`  
**响应**：`text/event-stream`（SSE 流式）

### 基础调用（仅照片 + 房间类型）

```bash
curl -X POST "http://127.0.0.1:8001/api/v2/home-fengshui/analyze/stream" \
  -F "photos=@你的房间照片.jpg" \
  -F "room_type=bedroom" \
  --max-time 120 \
  -N
```

### 完整参数（含八字/命卦）

```bash
curl -X POST "http://127.0.0.1:8001/api/v2/home-fengshui/analyze/stream" \
  -F "photos=@卧室.jpg" \
  -F "room_type=bedroom" \
  -F "door_direction=南" \
  -F "solar_date=1990-05-15" \
  -F "solar_time=08:30" \
  -F "gender=male" \
  --max-time 120 \
  -N
```

### 多张照片

```bash
curl -X POST "http://127.0.0.1:8001/api/v2/home-fengshui/analyze/stream" \
  -F "photos=@卧室1.jpg" \
  -F "photos=@卧室2.jpg" \
  -F "room_type=bedroom" \
  --max-time 120 \
  -N
```

### 生产环境

```bash
curl -X POST "https://你的域名/api/v2/home-fengshui/analyze/stream" \
  -F "photos=@房间照片.jpg" \
  -F "room_type=bedroom" \
  -F "door_direction=南" \
  -F "solar_date=1990-05-15" \
  -F "gender=male" \
  -H "Authorization: Bearer 你的token" \
  --max-time 120 \
  -N
```

---

## 二、参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `photos` | File | ✅ | 房间照片，1-4 张 |
| `room_type` | string | ✅ | 房间类型：`bedroom` / `living_room` / `study` / `kitchen` / `dining_room` |
| `door_direction` | string | ❌ | 大门朝向：北/东北/东/东南/南/西南/西/西北 |
| `solar_date` | string | ❌ | 出生日期，如 `1990-05-15` |
| `solar_time` | string | ❌ | 出生时间，如 `08:30` |
| `gender` | string | ❌ | 性别：`male` / `female` |
| `bot_id` | string | ❌ | 百炼报告智能体 App ID（默认从配置读取） |

---

## 三、SSE 事件类型

| type | 说明 |
|------|------|
| `request_id` | 请求 ID |
| `progress_msg` | 进度提示 |
| `data` | 结构化分析结果（家具、问题、建议、命卦等） |
| `annotated_image` | 标注图 base64 |
| `mingua_result` | 命卦信息 |
| `progress` | LLM 报告流式文本（多条） |
| `complete` | 流式结束 |
| `ideal_layout_image` | 理想布局图 base64 |
| `error` | 错误信息 |

---

## 四、快速测试（使用项目内测试图）

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 确保服务已启动：.venv/bin/python server/main.py

curl -X POST "http://127.0.0.1:8001/api/v2/home-fengshui/analyze/stream" \
  -F "photos=@scripts/test_annotated.png" \
  -F "room_type=bedroom" \
  -F "door_direction=南" \
  -F "solar_date=1990-05-15" \
  -F "gender=male" \
  --max-time 90 2>&1 | head -50
```

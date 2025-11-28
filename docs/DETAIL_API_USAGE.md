# 八字详细计算接口使用说明

## 新增接口

### 接口地址
`POST /api/v1/bazi/detail`

### 功能说明
计算详细八字信息，包含：
- 基本八字信息
- 大运序列（包含起运、交运信息）
- 流年序列
- 流月、流日、流时信息
- 详细的四柱信息（十神、藏干、神煞等）

## 请求参数

```json
{
  "solar_date": "1990-05-15",           // 必填：阳历日期 (YYYY-MM-DD)
  "solar_time": "14:30",                 // 必填：出生时间 (HH:MM)
  "gender": "male",                      // 必填：性别 (male/female)
  "current_time": "2024-01-01 12:00"    // 可选：当前时间 (YYYY-MM-DD HH:MM)，用于计算大运流年
}
```

## 响应示例

```json
{
  "success": true,
  "data": {
    "basic_info": {
      "solar_date": "1990-05-15",
      "solar_time": "14:30",
      "lunar_date": {...},
      "gender": "male",
      "current_time": "2024-01-01 12:00:00"
    },
    "bazi_pillars": {
      "year": {
        "stem": "庚",
        "branch": "午",
        "main_star": "比肩",
        "hidden_stars": [...],
        "hidden_stems": [...],
        "star_fortune": "...",
        "self_sitting": "...",
        "kongwang": "...",
        "nayin": "路旁土",
        "deities": [...]
      },
      ...
    },
    "dayun_info": {
      "current_dayun": {...},
      "next_dayun": {...},
      "qiyun_date": "1990-06-15",
      "qiyun_age": "0岁",
      "jiaoyun_date": "1990-07-15",
      "jiaoyun_age": "0岁"
    },
    "liunian_info": {
      "current_liunian": {...},
      "next_liunian": {...}
    },
    "dayun_sequence": [
      {
        "start_date": "1990-06-15",
        "end_date": "2000-06-15",
        "ganzhi": "壬午",
        "nayin": "杨柳木",
        "age": "0-10岁",
        "details": {...}
      },
      ...
    ],
    "liunian_sequence": [
      {
        "year": "2024",
        "ganzhi": "甲辰",
        "nayin": "覆灯火",
        "details": {...}
      },
      ...
    ],
    "liuyue_info": [...],
    "liuri_info": [...],
    "liushi_info": [...]
  }
}
```

## 调用示例

### 使用 curl

```bash
# 基本调用
curl -X POST http://127.0.0.1:8001/api/v1/bazi/detail \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'

# 指定当前时间
curl -X POST http://127.0.0.1:8001/api/v1/bazi/detail \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "current_time": "2024-01-01 12:00"
  }'
```

### 使用 Python

```python
import requests

url = "http://127.0.0.1:8001/api/v1/bazi/detail"
data = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "current_time": "2024-01-01 12:00"  # 可选
}
response = requests.post(url, json=data)
result = response.json()
print(result)
```

## 直接执行脚本

### 修改默认参数

在 `src/bazi_calculator_detail.py` 文件的第 20-24 行可以修改默认参数：

```python
# ========== 可在此处直接修改默认参数 ==========
DEFAULT_DATE = '1991-02-15'  # 出生日期 (YYYY-MM-DD)
DEFAULT_TIME = '10:30'  # 出生时间 (HH:MM)
DEFAULT_GENDER = 'male'  # 性别 (male/female 或 男/女)
DEFAULT_CURRENT_TIME = None  # 当前时间，None表示使用当前系统时间
# ============================================
```

### 使用方式

```bash
# 使用默认参数
python src/bazi_calculator_detail.py

# 使用命令行参数
python src/bazi_calculator_detail.py --date 1990-05-15 --time 14:30 --gender male

# 指定当前时间
python src/bazi_calculator_detail.py --date 1990-05-15 --time 14:30 --current-time "2024-01-01 12:00"
```

## 三个接口对比

| 接口 | 路径 | 功能 | 返回内容 |
|------|------|------|----------|
| 基础八字 | `/api/v1/bazi/calculate` | 计算基本八字信息 | 四柱、十神、藏干、神煞等 |
| 界面信息 | `/api/v1/bazi/interface` | 生成界面展示信息 | 命宫、身宫、胎元、胎息、命卦等 |
| 详细计算 | `/api/v1/bazi/detail` | 计算详细八字（含大运流年） | 四柱、大运序列、流年序列、流月流日流时等 |

## 注意事项

1. **原有接口不受影响**：所有原有接口功能完全保留
2. **current_time 参数**：如果不提供，默认使用系统当前时间计算大运流年
3. **计算时间**：详细计算接口需要更多时间，因为要计算大运流年序列
4. **数据量**：返回的数据量较大，包含完整的大运流年序列

## 文件清单

新增文件：
- `server/services/bazi_detail_service.py` - 详细计算服务层

修改文件：
- `src/bazi_calculator_detail.py` - 增加可修改的参数
- `server/api/v1/bazi.py` - 新增 `/api/v1/bazi/detail` 接口














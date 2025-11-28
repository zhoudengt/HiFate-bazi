# 八字界面接口使用说明

## 目录结构说明

### 新增目录和文件

1. **src/printer/** - 打印输出模块
   - `bazi_interface_printer.py` - 负责将分析结果格式化为 JSON 输出

2. **src/analyzers/bazi_interface_analyzer.py** - 逻辑分析模块
   - 包含所有逻辑转化方法：星座、生肖、命宫、身宫、胎元、胎息、命卦等

3. **src/bazi_interface_generator.py** - 主生成器（已重构）
   - 使用 `tool/LunarConverter` 进行公历转农历
   - 使用 `analyzers/bazi_interface_analyzer` 进行逻辑计算
   - 使用 `printer/bazi_interface_printer` 进行输出

4. **server/services/bazi_interface_service.py** - 服务层
   - 封装八字界面信息生成逻辑

### 文件关系

```
bazi_interface_generator.py (主生成器)
    ↓ 使用
tool/LunarConverter.py (公历转农历)
    ↓ 使用
analyzers/bazi_interface_analyzer.py (逻辑计算)
    ↓ 使用
printer/bazi_interface_printer.py (格式化输出)
    ↓ 被调用
server/services/bazi_interface_service.py (服务层)
    ↓ 被调用
server/api/v1/bazi.py (API接口)
```

## API 接口调用

### 1. 新接口：八字界面信息生成

**接口地址**: `POST /api/v1/bazi/interface`

**请求参数**:
```json
{
  "solar_date": "1990-05-15",    // 必填：阳历日期 (YYYY-MM-DD)
  "solar_time": "14:30",          // 必填：出生时间 (HH:MM)
  "gender": "male",                // 必填：性别 (male/female)
  "name": "张三",                  // 可选：姓名
  "location": "北京",              // 可选：出生地点
  "latitude": 39.90,               // 可选：纬度
  "longitude": 116.40              // 可选：经度
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "basic_info": {
      "name": "张三",
      "gender": "男",
      "solar_date": "1990-05-15",
      "solar_time": "14:30",
      "lunar_date": "1990年四月廿一",
      "location": "北京"
    },
    "bazi_pillars": {
      "year": "庚午",
      "month": "辛巳",
      "day": "庚辰",
      "hour": "癸未"
    },
    "astrology": {
      "zodiac": "马",
      "constellation": "金牛座",
      "mansion": "昴宿",
      "bagua": "震卦"
    },
    "palaces": {
      "life_palace": {
        "ganzhi": "丁丑",
        "nayin": "涧下水"
      },
      "body_palace": {
        "ganzhi": "丙寅",
        "nayin": "炉中火"
      },
      "fetal_origin": {
        "ganzhi": "壬戌",
        "nayin": "大海水"
      },
      "fetal_breath": {
        "ganzhi": "乙卯",
        "nayin": "大溪水"
      }
    },
    "solar_terms": {
      "current_jieqi": "立夏",
      "current_jieqi_time": "1990-05-06 02:35:00",
      "next_jieqi": "小满",
      "next_jieqi_time": "1990-05-21 15:37:00",
      "days_to_current": 9,
      "days_to_next": 6
    },
    "other_info": {
      "commander_element": "丁火用事",
      "void_emptiness": "申酉",
      "day_master": "庚金"
    },
    "formatted_text": {
      "姓名": "姓名：张三 (阴 乾造)",
      "性别": "性别：男",
      "农历": "农历：1990年四月廿一 未时",
      "四柱": "四柱：庚午 辛巳 庚辰 癸未",
      ...
    }
  }
}
```

### 2. 原有接口：八字计算（不受影响）

**接口地址**: `POST /api/v1/bazi/calculate`

原有接口功能完全保留，不受影响。

## 调用示例

### 使用 curl

```bash
# 新接口：八字界面信息
curl -X POST http://127.0.0.1:8001/api/v1/bazi/interface \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "name": "张三",
    "location": "北京"
  }'

# 原有接口：八字计算
curl -X POST http://127.0.0.1:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }'
```

### 使用 Python

```python
import requests

# 新接口
url = "http://127.0.0.1:8001/api/v1/bazi/interface"
data = {
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "name": "张三",
    "location": "北京"
}
response = requests.post(url, json=data)
result = response.json()
print(result)
```

### 使用测试脚本

```bash
# 启动服务
python server/start.py

# 在另一个终端运行测试
python test_interface_api.py
```

## 功能说明

### 新增功能

1. **命宫计算** - 根据年、月、日、时计算命宫
2. **身宫计算** - 根据年、月、日、时计算身宫
3. **胎元计算** - 根据月柱计算胎元
4. **胎息计算** - 根据日柱计算胎息
5. **命卦计算** - 根据年、性别计算命卦
6. **二十八宿** - 根据农历日期计算星宿
7. **人元司令分野** - 计算人元司令
8. **空亡** - 计算空亡地支
9. **节气信息** - 详细的节气时间和距离

### 技术改进

1. **公历转农历** - 统一使用 `tool/LunarConverter` 方法
2. **模块化设计** - 逻辑计算、格式化输出分离
3. **JSON 输出** - 结构化 JSON 格式，便于前端使用
4. **向后兼容** - 原有接口和功能完全保留

## 注意事项

1. **服务端口**: 默认 8001，如果被占用会自动切换到下一个可用端口
2. **性别格式**: 支持 `male`/`female` 或 `男`/`女`
3. **日期格式**: 必须为 `YYYY-MM-DD` 格式
4. **时间格式**: 必须为 `HH:MM` 格式
5. **原有接口**: `/api/v1/bazi/calculate` 完全不受影响，可以正常使用

## 测试

运行测试脚本验证功能：

```bash
# 确保服务已启动
python server/start.py

# 运行测试
python test_interface_api.py
```

测试脚本会：
1. 测试原有接口 `/api/v1/bazi/calculate` 是否正常
2. 测试新接口 `/api/v1/bazi/interface` 是否正常
3. 验证返回数据格式

## 文件清单

新增文件：
- `src/printer/__init__.py`
- `src/printer/bazi_interface_printer.py`
- `src/analyzers/bazi_interface_analyzer.py`
- `server/services/bazi_interface_service.py`

修改文件：
- `src/bazi_interface_generator.py` (重构，使用新模块)
- `server/api/v1/bazi.py` (新增接口)

测试文件：
- `test_interface_api.py`














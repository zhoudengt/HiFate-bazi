# 规则引擎使用文档

## 概述

规则引擎系统支持高性能的八字规则匹配，可以处理1000-2000条规则，支持复杂的条件配置。

## 文件夹结构

```
server/
├── engines/              # 规则引擎核心模块
│   ├── __init__.py
│   ├── rule_condition.py    # 规则条件匹配器
│   └── rule_engine.py        # 规则引擎核心类
├── config/               # 配置文件
│   ├── __init__.py
│   ├── redis_config.py       # Redis 配置
│   ├── mysql_config.py       # MySQL 配置
│   └── rules.json            # 规则配置文件（示例）
├── db/                   # 数据库相关
│   ├── __init__.py
│   ├── mysql_connector.py    # MySQL 连接器
│   ├── schema.sql            # 数据库表结构
│   └── init_database.py     # 数据库初始化脚本
└── services/
    └── rule_service.py       # 规则服务层
```

## 功能特性

### 1. 多级缓存系统
- **L1缓存（内存）**：存储最热的数据，5万条，5分钟过期
- **L2缓存（Redis）**：分布式缓存，支持多服务器共享，1小时过期
- **自动回填**：L2命中后自动回填L1

### 2. 规则引擎
- **复杂条件支持**：
  - 年柱、月柱、日柱、时柱条件
  - 四柱神煞条件（任意柱/特定柱）
  - 星运条件
  - 组合条件（AND/OR/NOT）
- **索引优化**：快速筛选候选规则
- **并行匹配**：多线程并行处理规则匹配

### 3. 数据库支持
- MySQL 数据库存储规则
- 支持动态规则管理
- 规则匹配日志记录

## API 接口

### 1. 匹配规则

**接口**: `POST /api/v1/bazi/rules/match`

**请求参数**:
```json
{
  "solar_date": "1990-05-15",
  "solar_time": "14:30",
  "gender": "male",
  "rule_types": ["rizhu_gender", "deity"],  // 可选
  "include_bazi": true  // 可选，是否包含八字计算结果
}
```

**响应示例**:
```json
{
  "success": true,
  "bazi_data": {
    // 八字计算结果（如果 include_bazi=true）
  },
  "matched_rules": [
    {
      "rule_id": "RZ_甲子_male",
      "rule_code": "RZ_甲子_male",
      "rule_name": "甲子男命分析",
      "rule_type": "rizhu_gender",
      "priority": 100,
      "content": {
        "type": "description",
        "text": "甲为头，子为水为智慧，直读头脑聪明而有智慧"
      },
      "description": "甲子男命的特征分析"
    }
  ],
  "rule_count": 1
}
```

### 2. 获取规则类型列表

**接口**: `GET /api/v1/bazi/rules/types`

**响应示例**:
```json
{
  "success": true,
  "rule_types": ["rizhu_gender", "deity", "star_fortune", "combined"],
  "count": 4
}
```

### 3. 获取规则统计信息

**接口**: `GET /api/v1/bazi/rules/stats`

**响应示例**:
```json
{
  "success": true,
  "total_rules": 100,
  "enabled_rules": 95,
  "rule_types": {
    "rizhu_gender": 30,
    "deity": 40,
    "star_fortune": 20,
    "combined": 10
  },
  "cache_stats": {
    "l1": {
      "size": 1000,
      "max_size": 50000,
      "ttl": 300
    },
    "l2": {
      "status": "available",
      "used_memory": "10.5M",
      "connected_clients": 2
    }
  }
}
```

## 规则配置格式

### 规则JSON格式

```json
{
  "rule_id": "规则唯一标识",
  "rule_name": "规则名称",
  "rule_type": "规则类型",
  "priority": 100,
  "enabled": true,
  "conditions": {
    // 匹配条件
  },
  "content": {
    "type": "description",
    "text": "规则内容"
  },
  "description": "规则描述"
}
```

### 支持的条件类型

#### 1. 四柱条件
```json
{
  "year_pillar": "甲子",      // 年柱
  "month_pillar": "乙丑",     // 月柱
  "day_pillar": "丙寅",       // 日柱
  "hour_pillar": "丁卯"       // 时柱
}
```

#### 2. 神煞条件
```json
{
  "deities_in_any_pillar": ["天乙贵人"],        // 四柱中任意一柱存在
  "deities_in_year": ["天乙贵人"],              // 年柱神煞
  "deities_in_month": ["天乙贵人"],             // 月柱神煞
  "deities_in_day": ["天乙贵人"],               // 日柱神煞
  "deities_in_hour": ["天乙贵人"]                // 时柱神煞
}
```

#### 3. 星运条件
```json
{
  "star_fortune_in_year": "长生",
  "star_fortune_in_day": ["长生", "沐浴"]
}
```

#### 4. 组合条件
```json
{
  "all": [  // 所有条件都必须满足
    {"year_pillar": "甲子"},
    {"deities_in_any_pillar": ["天乙贵人"]}
  ],
  "any": [  // 任一条件满足即可
    {"day_pillar": "甲子"},
    {"day_pillar": "乙丑"}
  ],
  "not": {  // 条件不满足
    "gender": "female"
  }
}
```

### 规则配置示例

```json
{
  "rule_id": "COMBINED_年柱甲子_天乙贵人",
  "rule_name": "年柱甲子且四柱存在天乙贵人",
  "rule_type": "combined",
  "priority": 100,
  "enabled": true,
  "conditions": {
    "all": [
      {"year_pillar": "甲子"},
      {"deities_in_any_pillar": ["天乙贵人"]}
    ]
  },
  "content": {
    "type": "description",
    "text": "年柱甲子，四柱带天乙贵人，主大富大贵"
  },
  "description": "复合条件规则示例"
}
```

## 数据库初始化

### 1. 创建数据库和表

```bash
# 方式1：使用初始化脚本
cd /Users/zhoudt/Downloads/project/HiFate-bazi
source .venv/bin/activate
python -c "import sys; sys.path.insert(0, '.'); from server.db.init_database import init_database; init_database()"

# 方式2：直接执行SQL
mysql -u root -p123456 < server/db/schema.sql
```

### 2. 验证数据库

```bash
mysql -u root -p123456 -e "USE hifate_bazi; SHOW TABLES;"
```

## 使用示例

### Python 代码示例

```python
from server.services.rule_service import RuleService
from server.services.bazi_service import BaziService

# 1. 计算八字
bazi_result = BaziService.calculate_bazi_full(
    solar_date="1990-05-15",
    solar_time="14:30",
    gender="male"
)

# 2. 匹配规则
bazi_data = {
    'basic_info': bazi_result['bazi']['basic_info'],
    'bazi_pillars': bazi_result['bazi']['bazi_pillars'],
    'details': bazi_result['bazi']['details']
}

matched_rules = RuleService.match_rules(
    bazi_data=bazi_data,
    rule_types=['rizhu_gender', 'deity'],  # 可选
    use_cache=True
)

# 3. 处理匹配结果
for rule in matched_rules:
    print(f"规则: {rule['rule_name']}")
    print(f"内容: {rule['content']['text']}")
```

### cURL 示例

```bash
# 匹配规则
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "rule_types": ["rizhu_gender", "deity"]
  }'

# 获取规则类型
curl http://127.0.0.1:8001/api/v1/bazi/rules/types

# 获取统计信息
curl http://127.0.0.1:8001/api/v1/bazi/rules/stats
```

## 性能优化

### 1. 缓存策略
- L1缓存：5万条热点数据，5分钟过期
- L2缓存：Redis分布式缓存，1小时过期
- 自动回填机制

### 2. 索引优化
- 按年柱、日柱建立索引
- 按神煞建立索引
- 按规则类型建立索引

### 3. 并行处理
- 多线程并行匹配规则
- 根据CPU核心数动态调整线程数

## 注意事项

1. **不影响现有功能**：所有新功能都是新增的，不会修改现有代码
2. **可选依赖**：Redis 和 MySQL 是可选的，如果未安装/配置，系统会降级使用基础功能
3. **规则加载**：优先从配置文件加载，如果数据库可用，也可以从数据库加载
4. **缓存失效**：规则更新后需要调用 `RuleService.reload_rules()` 重新加载

## 故障排查

### Redis 连接失败
```bash
# 检查 Redis 是否运行
redis-cli ping

# 启动 Redis
brew services start redis
```

### MySQL 连接失败
```bash
# 检查 MySQL 是否运行
mysql -u root -p123456 -e "SELECT 1"

# 检查数据库是否存在
mysql -u root -p123456 -e "SHOW DATABASES;"
```

### 规则未匹配
1. 检查规则文件格式是否正确
2. 检查规则是否启用（enabled: true）
3. 检查条件是否匹配
4. 查看日志输出

## 扩展开发

### 添加新条件类型

在 `server/engines/rule_condition.py` 的 `EnhancedRuleCondition.match()` 方法中添加新的条件判断逻辑。

### 从数据库加载规则

在 `server/services/rule_service.py` 的 `get_engine()` 方法中取消注释数据库加载代码。

### 添加新的规则类型

1. 在规则配置中添加新的 `rule_type`
2. 在规则匹配逻辑中处理新类型
3. 更新索引构建逻辑（如需要）













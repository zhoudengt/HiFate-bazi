# HiFate规则系统整体方案

## 📋 目录

- [系统概述](#系统概述)
- [架构设计](#架构设计)
- [核心组件](#核心组件)
- [规则存储](#规则存储)
- [规则匹配流程](#规则匹配流程)
- [规则类型体系](#规则类型体系)
- [条件匹配能力](#条件匹配能力)
- [性能优化](#性能优化)
- [热加载机制](#热加载机制)
- [规则导入导出](#规则导入导出)
- [API 接口](#api-接口)
- [使用示例](#使用示例)
- [技术栈](#技术栈)
- [性能指标](#性能指标)
- [扩展性](#扩展性)

---

## 系统概述

HiFate规则系统是一个**基于数据库的、高性能的、支持热加载的规则引擎**，用于根据用户的生辰八字信息匹配相应的命理规则。

### 核心特性

- ✅ **数据库存储**：规则存储在 MySQL 数据库中，支持动态更新
- ✅ **高性能匹配**：使用索引优化和并行匹配，支持 462+ 条规则
- ✅ **热加载机制**：支持规则和内容的热更新，无需重启服务
- ✅ **复杂条件支持**：支持 50+ 种条件类型，包括四柱、神煞、十神、大运流年等
- ✅ **动态查询**：支持动态内容查询（如日柱性别分析）
- ✅ **多级缓存**：L1 内存缓存 + L2 Redis 缓存
- ✅ **规则分类**：支持多种规则类型（婚姻、桃花、日柱等）

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     外部请求层                                │
│  (FastAPI RESTful API / gRPC Service)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    规则服务层                                 │
│  RuleService (单例模式)                                      │
│  - 规则匹配入口                                              │
│  - 缓存管理                                                  │
│  - 热加载管理                                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌───▼──────────┐
│  规则引擎     │ │  条件匹配器  │ │  查询适配器  │
│ RuleEngine   │ │ RuleCondition│ │ QueryAdapter│
│ - 索引优化    │ │ - 50+条件类型 │ │ - 动态查询  │
│ - 并行匹配    │ │ - 组合条件   │ │ - 内容缓存  │
└───────┬──────┘ └─────────────┘ └─────────────┘
        │
┌───────▼──────────────────────────────────────┐
│              数据存储层                       │
│  MySQL (bazi_rules 表)                      │
│  - 规则定义 (conditions, content)            │
│  - 规则元数据 (rule_code, rule_type, etc.)   │
└─────────────────────────────────────────────┘
```

### 数据流

```
用户请求
  ↓
API 接口 (/api/v1/bazi/rules/match)
  ↓
BaziCalculator.build_rule_input()  (构建八字数据)
  ↓
RuleService.match_rules()  (规则匹配服务)
  ↓
  ├─→ 检查缓存 (MultiLevelCache)
  ├─→ EnhancedRuleEngine.match_rules()  (规则引擎)
  │     ├─→ 索引过滤 (快速定位候选规则)
  │     └─→ 并行匹配 (ThreadPoolExecutor)
  │           └─→ EnhancedRuleCondition.match()  (条件匹配)
  │                 ├─→ 静态条件匹配
  │                 └─→ 动态查询 (QueryAdapterRegistry)
  └─→ 格式化结果并缓存
```

---

## 核心组件

### 1. RuleService（规则服务层）

**位置：** `server/services/rule_service.py`

**职责：**
- 规则引擎单例管理
- 缓存管理（L1 + L2）
- 热加载管理
- 规则匹配入口

**关键方法：**
```python
RuleService.get_engine()           # 获取规则引擎实例
RuleService.match_rules()          # 匹配规则
RuleService.reload_rules()         # 重新加载规则
RuleService.start_auto_reload()    # 启动自动刷新
```

**核心代码：**
```python
class RuleService:
    _engine: Optional[EnhancedRuleEngine] = None
    _cache = None
    _reloader: Optional[RuleReloader] = None
    
    @classmethod
    def match_rules(cls, bazi_data: Dict, rule_types: List[str] = None, 
                     use_cache: bool = True) -> List[Dict]:
        # 1. 生成缓存键
        cache_key = cls._generate_cache_key(bazi_data, rule_types)
        
        # 2. 检查缓存
        if use_cache:
            cached_result = cls.get_cache().get(cache_key)
            if cached_result is not None:
                return cached_result
        
        # 3. 匹配规则
        engine = cls.get_engine()
        matched_rules = engine.match_rules(bazi_data, rule_types)
        
        # 4. 格式化结果（支持动态查询）
        formatted_rules = cls._format_rules(matched_rules, bazi_data)
        
        # 5. 缓存结果
        if use_cache:
            cls.get_cache().set(cache_key, formatted_rules)
        
        return formatted_rules
```

### 2. EnhancedRuleEngine（规则引擎）

**位置：** `server/engines/rule_engine.py`

**职责：**
- 规则索引构建
- 规则匹配执行
- 并行匹配优化

**核心特性：**
- **索引优化**：按年柱、月柱、日柱、时柱、神煞、规则类型建立索引
- **并行匹配**：使用 ThreadPoolExecutor 并行匹配规则
- **优先级排序**：按 priority 字段排序匹配结果

**索引结构：**
```python
{
    'by_year_pillar': {},    # 年柱索引
    'by_month_pillar': {},   # 月柱索引
    'by_day_pillar': {},     # 日柱索引
    'by_hour_pillar': {},    # 时柱索引
    'by_deity': {},          # 神煞索引
    'by_rule_type': {},      # 规则类型索引
}
```

**匹配算法：**
```python
def match_rules(self, bazi_data: Dict, rule_types: List[str] = None):
    # 1. 使用索引快速过滤候选规则
    candidate_rules = self._get_candidate_rules(bazi_data, rule_types)
    
    # 2. 并行匹配规则
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(self._match_single_rule, rule, bazi_data)
            for rule in candidate_rules
        ]
        matched_rules = [
            rule for rule, future in zip(candidate_rules, futures)
            if future.result()
        ]
    
    # 3. 按优先级排序
    matched_rules.sort(key=lambda r: r.get('priority', 100), reverse=True)
    
    return matched_rules
```

### 3. EnhancedRuleCondition（条件匹配器）

**位置：** `server/engines/rule_condition.py`

**职责：**
- 解析和匹配规则条件
- 支持 50+ 种条件类型
- 支持组合条件（AND/OR/NOT）

**支持的条件类型：**

#### 四柱条件
- `year_pillar`, `month_pillar`, `day_pillar`, `hour_pillar`
- `pillar_equals`, `pillar_in`, `pillar_relation`

#### 神煞条件
- `deities_in_year`, `deities_in_month`, `deities_in_day`, `deities_in_hour`
- `deities_in_any_pillar`, `deities_count`

#### 十神条件
- `ten_gods_main`, `ten_gods_sub`, `ten_gods_total`
- `ten_gods_main_count`, `ten_god_order`

#### 天干地支条件
- `stems_count`, `branches_count`
- `stems_chong`, `stems_wuhe_pairs`
- `stems_sequence`, `day_branch_simple`

#### 大运流年条件
- `dayun_branch_equals`, `dayun_branch_in`
- `liunian_combines_pillar`, `liunian_ganzhi_equals`
- `suiyun_binglin_kongwang`, `month_ten_gods_with_dayun_liunian`

#### 其他条件
- `element_total`, `element_relation`
- `nayin_count_in_pillars`, `branch_liuhe_sanhe_count`
- `lunar_month_in`, `lunar_day_in`
- `gender`, `star_fortune_in_*`

**条件匹配示例：**
```python
# 简单条件
{"year_pillar": "甲子", "gender": "male"}

# 组合条件
{
  "all": [
    {"day_pillar": "庚辰"},
    {"gender": "male"},
    {
      "any": [
        {"deities_in_any_pillar": ["天乙贵人"]},
        {"ten_gods_main": {"names": ["正官"], "pillars": ["year"]}}
      ]
    }
  ]
}
```

### 4. QueryAdapterRegistry（查询适配器）

**位置：** `server/engines/query_adapters.py`

**职责：**
- 动态内容查询
- 适配器注册和管理
- 内容缓存

**已注册的适配器：**
- `RizhuGenderAnalyzer`：日柱性别分析

**使用示例：**
```json
{
  "type": "dynamic",
  "query_adapter": "RizhuGenderAnalyzer",
  "query_method": "analyze_rizhu_gender",
  "default_content": {
    "type": "description",
    "text": "暂无分析数据"
  }
}
```

---

## 规则存储

### 数据库表结构

#### bazi_rules（规则主表）

```sql
CREATE TABLE `bazi_rules` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    `rule_code` VARCHAR(50) UNIQUE NOT NULL COMMENT '规则代码（唯一）',
    `rule_name` VARCHAR(200) NOT NULL COMMENT '规则名称',
    `rule_type` VARCHAR(50) NOT NULL COMMENT '规则类型',
    `priority` INT DEFAULT 100 COMMENT '优先级（数字越大优先级越高）',
    `conditions` JSON NOT NULL COMMENT '匹配条件（JSON格式）',
    `content` JSON NOT NULL COMMENT '规则内容（JSON格式）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `description` TEXT COMMENT '规则描述',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_rule_type` (`rule_type`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_rule_code` (`rule_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='八字规则表';
```

#### rizhu_gender_contents（日柱性别内容表）

```sql
CREATE TABLE `rizhu_gender_contents` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '内容ID',
    `rizhu` VARCHAR(10) NOT NULL COMMENT '日柱（如：甲子）',
    `gender` VARCHAR(10) NOT NULL COMMENT '性别（male/female）',
    `descriptions` JSON NOT NULL COMMENT '描述列表（JSON数组）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `version` INT DEFAULT 1 COMMENT '版本号（用于热加载）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_rizhu_gender` (`rizhu`, `gender`),
    INDEX `idx_rizhu` (`rizhu`),
    INDEX `idx_gender` (`gender`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日柱性别内容表';
```

#### rule_version（版本号表）

```sql
CREATE TABLE `rule_version` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '版本ID',
    `rule_version` INT DEFAULT 1 COMMENT '规则版本号',
    `content_version` INT DEFAULT 1 COMMENT '内容版本号',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='规则版本号表';
```

### 规则数据格式

#### 规则条件（conditions）

**简单条件：**
```json
{
  "year_pillar": "甲子",
  "gender": "male"
}
```

**组合条件：**
```json
{
  "all": [
    {"year_pillar": "甲子"},
    {"gender": "male"},
    {
      "any": [
        {"deities_in_any_pillar": ["天乙贵人"]},
        {"ten_gods_main": {"names": ["正官"], "pillars": ["year"]}}
      ]
    }
  ]
}
```

**复杂条件：**
```json
{
  "all": [
    {"stems_count": {"stems": ["戊", "丁"], "eq": [3, 1]}},
    {"day_branch_simple": {"branches": ["子", "午"], "min": 1}},
    {
      "any": [
        {"dayun_branch_equals": {"branch": "子"}},
        {"liunian_ganzhi_equals": {"ganzhi": "甲子"}}
      ]
    }
  ]
}
```

#### 规则内容（content）

**静态内容：**
```json
{
  "type": "description",
  "items": [
    {"type": "description", "text": "规则描述内容1"},
    {"type": "description", "text": "规则描述内容2"}
  ]
}
```

**动态内容：**
```json
{
  "type": "dynamic",
  "query_adapter": "RizhuGenderAnalyzer",
  "query_method": "analyze_rizhu_gender",
  "default_content": {
    "type": "description",
    "text": "暂无分析数据"
  }
}
```

---

## 规则匹配流程

### 完整流程

```
1. 用户请求
   ↓
2. 构建八字数据 (BaziCalculator.build_rule_input)
   - 包含：四柱、神煞、十神、大运流年等完整信息
   ↓
3. 生成缓存键
   - 基于：日期、时间、性别、四柱、规则类型
   ↓
4. 检查缓存
   - L1 缓存（内存）
   - L2 缓存（Redis）
   ↓
5. 规则引擎匹配
   ├─→ 索引过滤（快速定位候选规则）
   ├─→ 并行匹配（ThreadPoolExecutor）
   │     └─→ 条件匹配（EnhancedRuleCondition）
   │           ├─→ 静态条件匹配
   │           └─→ 动态查询（QueryAdapterRegistry）
   └─→ 优先级排序
   ↓
6. 格式化结果
   - 处理动态内容
   - 格式化输出
   ↓
7. 缓存结果
   ↓
8. 返回匹配的规则列表
```

### 匹配算法

1. **索引过滤**：根据八字数据快速定位候选规则
   - 通过年柱、月柱、日柱、时柱、神煞等索引快速过滤
   - 通常可过滤 80%+ 的规则

2. **并行匹配**：使用线程池并行匹配多个规则
   - 线程数 = min(CPU核心数 × 2, 20)
   - 多核 CPU 下可提升 3-5 倍性能

3. **条件评估**：递归评估条件树（all/any/not）
   - 支持嵌套组合条件
   - 支持 50+ 种条件类型

4. **结果排序**：按 priority 降序排序
   - 优先级高的规则排在前面

---

## 规则类型体系

### 支持的规则类型（21+ 种）

| 规则类型 | 说明 | 数量 |
|---------|------|------|
| `marriage_ten_gods` | 婚姻十神规则 | ~50 |
| `marriage_element` | 婚姻五行规则 | ~30 |
| `marriage_day_stem` | 婚姻日干规则 | ~20 |
| `marriage_day_branch` | 婚姻日支规则 | ~30 |
| `marriage_day_pillar` | 婚姻日柱规则 | ~40 |
| `marriage_stem_pattern` | 婚姻天干模式 | ~15 |
| `marriage_branch_pattern` | 婚姻地支模式 | ~20 |
| `marriage_bazi_pattern` | 婚姻八字模式 | ~25 |
| `marriage_deity` | 婚姻神煞规则 | ~30 |
| `marriage_month_branch` | 婚姻月支规则 | ~15 |
| `marriage_year_branch` | 婚姻年支规则 | ~10 |
| `marriage_year_stem` | 婚姻年干规则 | ~10 |
| `marriage_year_pillar` | 婚姻年柱规则 | ~15 |
| `marriage_nayin` | 婚姻纳音规则 | ~20 |
| `marriage_lunar_birthday` | 婚姻农历生日规则 | ~15 |
| `marriage_hour_pillar` | 婚姻时柱规则 | ~10 |
| `marriage_year_event` | 婚姻年事规则 | ~10 |
| `marriage_luck_cycle` | 婚姻运势周期 | ~15 |
| `marriage_general` | 婚姻通用规则 | ~20 |
| `taohua_general` | 桃花通用规则 | ~15 |
| `rizhu_gender_dynamic` | 日柱性别动态查询 | 1 |
| **总计** | | **462+** |

### 规则类型说明

- **婚姻类规则**：主要关注婚姻相关的命理分析
- **桃花类规则**：关注桃花运相关的分析
- **日柱类规则**：基于日柱的性别动态分析

---

## 条件匹配能力

### 组合条件

支持三种逻辑组合：

```json
{
  "all": [...],    // 所有条件都必须满足（AND）
  "any": [...],    // 任一条件满足即可（OR）
  "not": {...}     // 条件不满足（NOT）
}
```

### 条件示例

#### 示例1：简单条件
```json
{
  "year_pillar": "甲子",
  "gender": "male"
}
```

#### 示例2：组合条件
```json
{
  "all": [
    {"day_pillar": "庚辰"},
    {"gender": "male"},
    {
      "any": [
        {"deities_in_any_pillar": ["天乙贵人"]},
        {"ten_gods_main": {"names": ["正官"], "pillars": ["year"]}}
      ]
    }
  ]
}
```

#### 示例3：复杂条件（天干特定数量）
```json
{
  "all": [
    {"stems_count": {"stems": ["戊", "丁"], "eq": [3, 1]}},
    {"day_branch_simple": {"branches": ["子", "午"], "min": 1}}
  ]
}
```

#### 示例4：大运流年条件
```json
{
  "all": [
    {"dayun_branch_equals": {"branch": "子"}},
    {
      "any": [
        {"liunian_ganzhi_equals": {"ganzhi": "甲子"}},
        {"month_ten_gods_with_dayun_liunian": {
          "ten_gods": ["正官", "七杀"],
          "check_dayun": true,
          "check_liunian": true
        }}
      ]
    }
  ]
}
```

---

## 性能优化

### 1. 索引优化

- **多维度索引**：年柱、月柱、日柱、时柱、神煞、规则类型
- **快速过滤**：先通过索引过滤候选规则，减少匹配数量
- **索引命中率**：通常可过滤 80%+ 的规则

**索引构建示例：**
```python
# 年柱索引
if 'year_pillar' in conditions:
    year_pillar = conditions['year_pillar']
    self._index['by_year_pillar'][year_pillar].append(rule)

# 神煞索引
if 'deities_in_any_pillar' in conditions:
    for deity in conditions['deities_in_any_pillar']:
        self._index['by_deity'][deity].append(rule)
```

### 2. 并行匹配

- **线程池**：使用 ThreadPoolExecutor，线程数 = CPU核心数 × 2
- **并行度**：最多 20 个线程并行匹配
- **性能提升**：多核 CPU 下可提升 3-5 倍性能

**并行匹配代码：**
```python
cpu_count = os.cpu_count() or 4
max_workers = min(cpu_count * 2, 20)

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [
        executor.submit(self._match_single_rule, rule, bazi_data)
        for rule in candidate_rules
    ]
    matched_rules = [
        rule for rule, future in zip(candidate_rules, futures)
        if future.result()
    ]
```

### 3. 多级缓存

- **L1 缓存**：内存缓存（Python dict）
- **L2 缓存**：Redis 缓存（可选）
- **缓存键**：基于八字数据 MD5 哈希
- **缓存命中率**：通常 > 90%

**缓存键生成：**
```python
def _generate_cache_key(bazi_data: Dict, rule_types: List[str] = None) -> str:
    key_parts = [
        bazi_data.get('basic_info', {}).get('solar_date', ''),
        bazi_data.get('basic_info', {}).get('solar_time', ''),
        bazi_data.get('basic_info', {}).get('gender', ''),
    ]
    # 添加四柱信息
    for pillar_type in ['year', 'month', 'day', 'hour']:
        pillar = bazi_data.get('bazi_pillars', {}).get(pillar_type, {})
        key_parts.append(f"{pillar.get('stem', '')}{pillar.get('branch', '')}")
    
    # 添加规则类型
    if rule_types:
        key_parts.append(str(sorted(rule_types)))
    
    key_str = ':'.join(key_parts)
    return f"bazi:rules:{hashlib.md5(key_str.encode()).hexdigest()}"
```

### 4. 延迟加载

- **单例模式**：规则引擎单例，首次访问时加载
- **按需加载**：只加载启用的规则（enabled = 1）

---

## 热加载机制

### 热加载架构

```
┌─────────────────────────────────────┐
│      HotReloadManager (单例)        │
│  - 统一管理所有模块的热更新          │
│  - 定时检查版本号变化                │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼────┐
│规则   │ │内容   │ │其他    │
│热加载 │ │热加载 │ │模块    │
└───────┘ └───────┘ └────────┘
```

### 热加载流程

1. **版本号检查**：每 5 分钟检查一次 `rule_version` 表
2. **规则更新**：如果 `rule_version` 变化，重新加载规则
3. **内容更新**：如果 `content_version` 变化，清空内容缓存
4. **自动刷新**：无需重启服务，自动生效

### 版本号管理

**更新规则版本号（触发规则热加载）：**
```sql
UPDATE rule_version SET rule_version = rule_version + 1;
```

**更新内容版本号（触发内容缓存清理）：**
```sql
UPDATE rule_version SET content_version = content_version + 1;
```

**热加载代码：**
```python
class RuleReloader:
    def _reload_loop(self):
        while self.running:
            time.sleep(self.interval)  # 默认 300 秒
            try:
                # 检查版本号
                current_version = RuleContentDAO.get_content_version()
                current_rule_version = RuleContentDAO.get_rule_version()
                
                # 规则更新
                if current_rule_version > RuleService._cached_rule_version:
                    RuleService.reload_rules()
                    RuleService._cached_rule_version = current_rule_version
                
                # 内容更新
                if current_version > RuleService._cached_content_version:
                    QueryAdapterRegistry._content_cache.clear()
                    RuleService._cached_content_version = current_version
            except Exception as e:
                print(f"⚠ 规则刷新失败: {e}")
```

---

## 规则导入导出

### 规则导入

#### 从 Excel/JSON 导入

**脚本：** `scripts/import_cc_confirm_rules.py`

**功能：**
- 解析 Excel/JSON 格式的规则数据
- 自动识别规则类型
- 转换条件格式
- 批量写入数据库

**使用：**
```bash
python scripts/import_cc_confirm_rules.py \
  --input docs/cc确认.json \
  --sheet "Sheet1"
```

#### 条件处理器

**位置：** `scripts/import_cc_confirm_rules.py`

**功能：**
- 将自然语言条件转换为结构化条件
- 支持 30+ 种条件处理器
- 自动识别条件类型

**主要处理器：**

| 处理器 | 功能 | 示例 |
|--------|------|------|
| `handle_day_pillar_combines` | 日柱组合条件 | "日柱是甲子或乙丑" |
| `handle_stems_sequence` | 天干顺序条件 | "天干出现顺序为甲、乙、丙" |
| `handle_ten_god_order` | 十神顺序条件 | "七杀在前，正官在后" |
| `handle_deities_huagai_liuhe_sanhe` | 神煞条件 | "带有华盖，六合三合数量≥3" |
| `handle_dayun_branch_equals` | 大运条件 | "大运地支等于日支" |
| `handle_liunian_combines_pillar` | 流年条件 | "流年与月柱组合" |
| `handle_stems_specific_count` | 天干特定数量 | "天干出现三个戊一个丁" |
| `handle_stems_chong` | 天干四冲 | "天干出现四冲" |
| `handle_stems_wuhe_pairs` | 天干五合 | "天干出现五合" |
| `handle_branch_liuhe_sanhe_count` | 地支六合三合 | "六合三合数量≥3" |

**处理器映射：**
```python
EXTENDED_CONDITION_HANDLERS = {
    "日柱": {
        "组合": handle_day_pillar_combines,
        "简单": handle_day_pillar_simple,
    },
    "天干": {
        "顺序": handle_stems_sequence,
        "特定数量": handle_stems_specific_count,
        "四冲": handle_stems_chong,
        "五合": handle_stems_wuhe_pairs,
    },
    "十神": {
        "顺序": handle_ten_god_order,
    },
    "大运": {
        "地支等于日支": handle_dayun_branch_equals,
    },
    "流年": {
        "与月柱组合": handle_liunian_combines_pillar,
        "干支等于": handle_liunian_ganzhi_equals,
    },
    # ... 更多处理器
}
```

### 规则导出

**脚本：** `scripts/export_rules_to_json.py`（可选）

**功能：**
- 从数据库导出规则到 JSON
- 支持按规则类型过滤
- 支持格式转换

---

## API 接口

### 1. 匹配规则

**接口：** `POST /api/v1/bazi/rules/match`

**请求：**
```json
{
  "solar_date": "1990-05-15",
  "solar_time": "14:30",
  "gender": "male",
  "rule_types": ["marriage_ten_gods", "marriage_element"],
  "include_bazi": true
}
```

**响应：**
```json
{
  "success": true,
  "bazi_data": {
    "bazi": {...},
    "rizhu": "甲子",
    "matched_rules": [...]
  },
  "matched_rules": [
    {
      "rule_id": "MARR_001",
      "rule_code": "MARR_001",
      "rule_name": "规则名称",
      "rule_type": "marriage_ten_gods",
      "priority": 100,
      "content": {
        "type": "description",
        "items": [
          {"type": "description", "text": "规则描述内容"}
        ]
      },
      "description": "规则描述"
    }
  ],
  "rule_count": 1
}
```

### 2. 获取规则类型

**接口：** `GET /api/v1/bazi/rules/types`

**响应：**
```json
{
  "success": true,
  "rule_types": [
    "marriage_ten_gods",
    "marriage_element",
    "marriage_day_stem",
    "marriage_day_branch",
    "marriage_day_pillar",
    "marriage_stem_pattern",
    "marriage_branch_pattern",
    "marriage_bazi_pattern",
    "marriage_deity",
    "marriage_month_branch",
    "marriage_year_branch",
    "marriage_year_stem",
    "marriage_year_pillar",
    "marriage_nayin",
    "marriage_lunar_birthday",
    "marriage_hour_pillar",
    "marriage_year_event",
    "marriage_luck_cycle",
    "marriage_general",
    "taohua_general",
    "rizhu_gender_dynamic"
  ],
  "count": 21
}
```

### 3. 获取规则统计

**接口：** `GET /api/v1/bazi/rules/stats`

**响应：**
```json
{
  "success": true,
  "total_rules": 462,
  "enabled_rules": 462,
  "rule_type_count": {
    "marriage_ten_gods": 50,
    "marriage_element": 30,
    "marriage_day_stem": 20,
    ...
  },
  "cache_stats": {
    "l1_hit_rate": 0.95,
    "l2_hit_rate": 0.90,
    "total_hit_rate": 0.92
  }
}
```

---

## 使用示例

### Python 代码示例

```python
from server.services.rule_service import RuleService
from src.tool.BaziCalculator import BaziCalculator

# 1. 构建八字数据
calculator = BaziCalculator("1990-05-15", "14:30", "male")
bazi_data = calculator.build_rule_input()

# 2. 匹配规则
matched_rules = RuleService.match_rules(
    bazi_data=bazi_data,
    rule_types=["marriage_ten_gods", "marriage_element"],
    use_cache=True
)

# 3. 处理结果
for rule in matched_rules:
    print(f"{rule['rule_name']}: {rule['content']}")
```

### gRPC 调用示例

```python
from src.clients.bazi_rule_client_grpc import BaziRuleClient

client = BaziRuleClient(base_url="127.0.0.1:9004")
result = client.match_rules(
    solar_date="1990-05-15",
    solar_time="14:30",
    gender="male",
    rule_types=["marriage_ten_gods"],
    use_cache=True
)

print(f"匹配到 {len(result['matched'])} 条规则")
```

### HTTP API 调用示例

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

---

## 技术栈

- **语言**：Python 3.8+
- **数据库**：MySQL 5.7+（JSON 字段支持）
- **缓存**：Redis（可选，L2 缓存）
- **并发**：ThreadPoolExecutor（并行匹配）
- **序列化**：JSON（规则条件/内容）
- **框架**：FastAPI（API 层），gRPC（微服务通信）

---

## 性能指标

- **规则数量**：462+ 条规则
- **规则类型**：21+ 种
- **条件类型**：50+ 种
- **匹配速度**：
  - 无缓存：< 100ms
  - 有缓存：< 10ms
- **并发支持**：1000+ 并发请求
- **缓存命中率**：> 90%
- **索引过滤率**：> 80%

---

## 扩展性

### 添加新规则类型

1. 在 `import_cc_confirm_rules.py` 中添加条件处理器
2. 在 `rule_condition.py` 中添加匹配逻辑（如需要）
3. 导入规则到数据库

**示例：**
```python
# 1. 添加条件处理器
def handle_new_condition(cond2: str, qty: str):
    # 解析条件
    # 返回结构化条件字典
    return [{"new_condition": {...}}], None

# 2. 注册处理器
EXTENDED_CONDITION_HANDLERS["新类型"] = {
    "新条件": handle_new_condition
}

# 3. 在 rule_condition.py 中添加匹配逻辑
elif key == "new_condition":
    # 匹配逻辑
    return match_new_condition(value, bazi_data)
```

### 添加新条件类型

1. 在 `rule_condition.py` 的 `EnhancedRuleCondition.match()` 中添加条件处理
2. 在 `rule_engine.py` 的索引构建中添加索引（如需要）

**示例：**
```python
# 在 rule_condition.py 中添加
elif key == "new_condition_type":
    # 匹配逻辑
    condition_value = value
    bazi_value = bazi_data.get('...')
    return condition_value == bazi_value
```

### 添加新查询适配器

1. 在 `query_adapters.py` 中注册适配器
2. 在规则内容中使用 `"type": "dynamic"` 和 `"query_adapter"`

**示例：**
```python
# 1. 注册适配器
QueryAdapterRegistry.register(
    adapter_name="NewAnalyzer",
    adapter_class=NewAnalyzer,
    query_method="analyze_new"
)

# 2. 在规则中使用
{
  "type": "dynamic",
  "query_adapter": "NewAnalyzer",
  "query_method": "analyze_new"
}
```

---

## 核心文件清单

```
server/
├── engines/
│   ├── rule_engine.py          # 规则引擎（索引优化、并行匹配）
│   ├── rule_condition.py      # 条件匹配器（1500+ 行，50+ 条件类型）
│   └── query_adapters.py      # 查询适配器（动态内容查询）
├── services/
│   └── rule_service.py        # 规则服务层（单例、缓存、热加载）
├── db/
│   ├── schema.sql             # 数据库表结构
│   └── rule_content_dao.py    # 规则内容 DAO
├── hot_reload/
│   ├── hot_reload_manager.py  # 热加载管理器
│   └── version_manager.py    # 版本号管理
└── api/v1/
    └── bazi_rules.py          # API 接口

scripts/
├── import_cc_confirm_rules.py  # 规则导入脚本（主导入）
├── import_zhuijia_rules.py    # 追加规则导入
└── handle_deities_huagai_liuhe_sanhe.py  # 特殊条件处理器

src/
└── bazi_calculator.py         # 八字计算器（调用规则匹配）
```

---

## 总结

HiFate规则系统是一个**高性能、可扩展、支持热加载的规则引擎**，具有以下特点：

### 核心优势

1. ✅ **数据库驱动**：规则存储在 MySQL，支持动态更新
2. ✅ **高性能**：索引优化 + 并行匹配 + 多级缓存
3. ✅ **热加载**：支持规则和内容的热更新，无需重启服务
4. ✅ **复杂条件**：支持 50+ 种条件类型和组合条件
5. ✅ **动态查询**：支持动态内容查询
6. ✅ **易于扩展**：模块化设计，易于添加新规则类型和条件类型

### 当前状态

- **规则数量**：462+ 条
- **规则类型**：21+ 种
- **条件类型**：50+ 种
- **性能**：< 100ms（无缓存），< 10ms（有缓存）
- **缓存命中率**：> 90%
- **索引过滤率**：> 80%

### 适用场景

- ✅ 命理分析系统
- ✅ 规则匹配引擎
- ✅ 条件判断系统
- ✅ 动态内容查询

---

**最后更新：** 2025-01-15  
**文档版本：** 1.0


# 流式接口 input_data 数据流明细文档

> **目的**：详细记录每个流式接口传给大模型的 `input_data` 的每个数据项来源，包括从底层服务到接口组装的完整数据流路径
> **最后更新**：2026-01-16

---

## 📋 目录

1. [总评分析（General Review）](#1-总评分析-general-review)
2. [事业财运分析（Career Wealth）](#2-事业财运分析-career-wealth)
3. [感情婚姻分析（Marriage）](#3-感情婚姻分析-marriage)
4. [身体健康分析（Health）](#4-身体健康分析-health)
5. [子女学习分析（Children Study）](#5-子女学习分析-children-study)
6. [年度报告分析（Annual Report）](#6-年度报告分析-annual-report)
7. [数据源服务说明](#数据源服务说明)

---

## 1. 总评分析（General Review）

### 接口信息
- **路径**：`/api/v1/bazi/general-review/stream`
- **流式生成器**：`general_review_analysis_stream_generator()`
- **input_data 构建函数**：`build_general_review_input_data()`
- **文件位置**：`server/api/v1/general_review_analysis.py`

### input_data 结构

```python
input_data = {
    'mingpan_hexin_geju': {...},      # 命盘核心格局
    'xingge_tezhi': {...},             # 性格特质
    'shiye_caiyun': {...},             # 事业财运轨迹
    'jiating_liuqin': {...},           # 家庭六亲关系
    'jiankang_yaodian': {...},          # 健康要点
    'guanjian_dayun': {...},           # 关键大运与人生节点
    'zhongsheng_tidian': {...},        # 终生提点与建议
    'rizhu_xinming_jiexi': {...}       # 日柱性命解析
}
```

### 数据流明细

#### 1.1 命盘核心格局（mingpan_hexin_geju）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `day_master` | `bazi_data['bazi_pillars']['day']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 日主信息（天干地支） |
| `bazi_pillars` | `bazi_data['bazi_pillars']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 四柱干支（年月日时） |
| `ten_gods` | `detail_result['ten_gods']` 或 `bazi_data['ten_gods']` | `BaziDetailService.calculate_detail_full()` → `detail_result` → `extract_ten_gods_data()` → `build_general_review_input_data()` | 十神数据（主星、藏干） |
| `wangshuai` | `wangshuai_result['data']['wangshuai']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `extract_wangshuai_data()` → `build_general_review_input_data()` | 旺衰判断（身旺/身弱等） |
| `wangshuai_detail` | `wangshuai_result['data']['wangshuai_detail']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `extract_wangshuai_data()` → `build_general_review_input_data()` | 旺衰详细说明 |
| `yue_ling` | `bazi_data['bazi_pillars']['month']['branch']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 月令（月支） |
| `geju_type` | `determine_geju_type()` | `month_branch` + `ten_gods_full` + `wangshuai_result` → `determine_geju_type()` → `build_general_review_input_data()` | 格局类型（正官格、偏财格等） |
| `wuxing_liutong` | `analyze_wuxing_liutong()` | `element_counts` + `bazi_pillars` → `analyze_wuxing_liutong()` → `build_general_review_input_data()` | 五行流通情况分析 |

**底层服务**：
- `BaziService.calculate_bazi_full()` - 计算八字基础数据（四柱、五行统计等）
- `BaziDetailService.calculate_detail_full()` - 计算详细数据（十神、神煞等）
- `WangShuaiService.calculate_wangshuai()` - 计算旺衰分析

#### 1.2 性格特质（xingge_tezhi）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `day_master_personality` | `personality_result['descriptions']` | `BaziDataOrchestrator.fetch_data(modules={'personality': True})` → `personality_result` → `build_general_review_input_data()` | 日主性格描述 |
| `rizhu_algorithm` | `rizhu_result['analysis']` | `BaziDataOrchestrator.fetch_data(modules={'rizhu': True})` → `rizhu_result` → `build_general_review_input_data()` | 日柱算法分析 |
| `ten_gods_effect` | `analyze_ten_gods_effect()` | `ten_gods_data` + `ten_gods_full` → `analyze_ten_gods_effect()` → `build_general_review_input_data()` | 十神对性格的影响 |

**底层服务**：
- `BaziDataOrchestrator.fetch_data()` - 统一数据获取接口（调用多个服务）
- `RizhuLiujiaziService` - 日柱六甲子分析服务

#### 1.3 事业财运轨迹（shiye_caiyun）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `shiye_xing` | `extract_career_star()` | `bazi_data['ten_gods_stats']` → `extract_career_star()` → `build_general_review_input_data()` | 事业星（正官、七杀等） |
| `caifu_xing` | `extract_wealth_star()` | `bazi_data['ten_gods_stats']` → `extract_wealth_star()` → `build_general_review_input_data()` | 财富星（正财、偏财等） |
| `dayun_effect` | `analyze_dayun_effect()` | `dayun_sequence` + `shiye_xing` + `caifu_xing` + `ten_gods_data` → `analyze_dayun_effect()` → `build_general_review_input_data()` | 大运对事业财运的影响 |

**底层服务**：
- `BaziService.calculate_bazi_full()` - 提供 `ten_gods_stats`（十神统计）

#### 1.4 家庭六亲关系（jiating_liuqin）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `year_pillar` | `bazi_data['bazi_pillars']['year']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 年柱（祖辈） |
| `month_pillar` | `bazi_data['bazi_pillars']['month']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 月柱（父母） |
| `day_pillar` | `bazi_data['bazi_pillars']['day']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 日柱（自己） |
| `hour_pillar` | `bazi_data['bazi_pillars']['hour']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_general_review_input_data()` | 时柱（子女） |

**底层服务**：
- `BaziService.calculate_bazi_full()` - 提供四柱数据

#### 1.5 健康要点（jiankang_yaodian）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `wuxing_balance` | `health_result['wuxing_balance']` | `BaziDataOrchestrator.fetch_data(modules={'health': True})` → `health_result` → `build_general_review_input_data()` | 五行平衡情况 |
| `zangfu_duiying` | `health_result['body_algorithm']` | `BaziDataOrchestrator.fetch_data(modules={'health': True})` → `health_result` → `build_general_review_input_data()` | 五行与五脏对应 |
| `jiankang_ruodian` | `health_result['pathology_tendency']` | `BaziDataOrchestrator.fetch_data(modules={'health': True})` → `health_result` → `build_general_review_input_data()` | 健康弱点分析 |

**底层服务**：
- `BaziDataOrchestrator.fetch_data()` - 统一数据获取接口（调用健康分析服务）

#### 1.6 关键大运与人生节点（guanjian_dayun）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `current_dayun` | `build_enhanced_dayun_structure()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` + `special_liunians` → `build_enhanced_dayun_structure()` → `build_general_review_input_data()` | 当前大运（包含流年） |
| `key_dayuns` | `build_enhanced_dayun_structure()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` + `special_liunians` → `build_enhanced_dayun_structure()` → `build_general_review_input_data()` | 关键大运列表（包含流年） |
| `dayun_sequence` | `BaziDataService.get_fortune_data()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` → `build_general_review_input_data()` | 完整大运序列 |
| `chonghe_xinghai` | `analyze_chonghe_xinghai()` | `bazi_pillars` + `dayun_sequence` + `detail_result` → `analyze_chonghe_xinghai()` → `build_general_review_input_data()` | 大运流年冲合刑害分析 |

**底层服务**：
- `BaziDataService.get_fortune_data()` - 统一数据服务，获取大运流年数据
  - 内部调用 `BaziDetailService.calculate_detail_full()` 获取大运序列
  - 内部调用 `BaziDisplayService.get_fortune_display()` 获取特殊流年（**关键：确保与排盘接口一致**）

**特殊流年数据流**：
1. `BaziDisplayService.get_fortune_display()` - 获取排盘数据（包含所有流年的 relations）
2. `BaziDataService.get_fortune_data(include_special_liunian=True)` - 从排盘数据中提取特殊流年
3. `build_enhanced_dayun_structure()` - 按大运分组特殊流年，添加优先级、描述等
4. `build_general_review_input_data()` - 组装到 `current_dayun` 和 `key_dayuns` 的 `liunians` 字段

#### 1.7 终生提点与建议（zhongsheng_tidian）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `xishen` | `extract_xi_ji_data()` | `xishen_jishen_result` + `wangshuai_result` → `extract_xi_ji_data()` → `build_general_review_input_data()` | 喜神（十神） |
| `jishen` | `extract_xi_ji_data()` | `xishen_jishen_result` + `wangshuai_result` → `extract_xi_ji_data()` → `build_general_review_input_data()` | 忌神（十神） |
| `xishen_wuxing` | `extract_xi_ji_data()` | `xishen_jishen_result` → `extract_xi_ji_data()` → `build_general_review_input_data()` | 喜神五行 |
| `jishen_wuxing` | `extract_xi_ji_data()` | `xishen_jishen_result` → `extract_xi_ji_data()` → `build_general_review_input_data()` | 忌神五行 |
| `fangwei_xuanze` | `get_directions_from_elements()` | `xishen_wuxing` + `jishen_wuxing` → `get_directions_from_elements()` → `build_general_review_input_data()` | 方位选择建议 |
| `hangye_xuanze` | `get_industries_from_elements()` | `xishen_wuxing` + `jishen_wuxing` → `get_industries_from_elements()` → `build_general_review_input_data()` | 行业选择建议 |

**底层服务**：
- `BaziDataOrchestrator.fetch_data(modules={'xishen_jishen': True})` - 获取喜忌数据
- `WangShuaiService.calculate_wangshuai()` - 提供十神喜忌

#### 1.8 日柱性命解析（rizhu_xinming_jiexi）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `rizhu_analysis` | `_build_rizhu_xinming_node()` | `day_pillar` + `gender` + `personality_result` → `_build_rizhu_xinming_node()` → `build_general_review_input_data()` | 日柱性格与命运分析 |

---

## 2. 事业财运分析（Career Wealth）

### 接口信息
- **路径**：`/api/v1/bazi/career-wealth/stream`
- **流式生成器**：`career_wealth_stream_generator()`
- **input_data 构建函数**：`build_career_wealth_input_data()`
- **文件位置**：`server/api/v1/career_wealth_analysis.py`

### input_data 结构

```python
input_data = {
    'mingpan_shiye_caiyun': {...},     # 命盘事业财运
    'dayun_shiye_caiyun': {...},        # 大运事业财运
    'liunian_shiye_caiyun': {...}       # 流年事业财运
}
```

### 数据流明细

#### 2.1 命盘事业财运（mingpan_shiye_caiyun）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `day_master` | `bazi_data['bazi_pillars']['day']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_career_wealth_input_data()` | 日主信息 |
| `bazi_pillars` | `bazi_data['bazi_pillars']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_career_wealth_input_data()` | 四柱干支 |
| `shiye_xing` | `extract_career_star()` | `bazi_data['ten_gods_stats']` → `extract_career_star()` → `build_career_wealth_input_data()` | 事业星 |
| `caifu_xing` | `extract_wealth_star()` | `bazi_data['ten_gods_stats']` → `extract_wealth_star()` → `build_career_wealth_input_data()` | 财富星 |
| `wangshuai` | `wangshuai_result['data']['wangshuai']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `extract_wangshuai_data()` → `build_career_wealth_input_data()` | 旺衰判断 |
| `xi_ji` | `extract_xi_ji_data()` | `wangshuai_result` → `extract_xi_ji_data()` → `build_career_wealth_input_data()` | 喜忌数据 |
| `ten_gods` | `extract_ten_gods_data()` | `detail_result` 或 `bazi_data` → `extract_ten_gods_data()` → `build_career_wealth_input_data()` | 十神数据 |
| `deities` | `bazi_data['details']` | `BaziService.calculate_bazi_full()` → `bazi_data['details']` → `build_career_wealth_input_data()` | 神煞数据 |

#### 2.2 大运事业财运（dayun_shiye_caiyun）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `current_dayun` | `identify_key_dayuns()` | `dayun_sequence` + `element_counts` + `current_age` → `identify_key_dayuns()` → `build_career_wealth_input_data()` | 当前大运 |
| `key_dayuns` | `identify_key_dayuns()` | `dayun_sequence` + `element_counts` + `current_age` → `identify_key_dayuns()` → `build_career_wealth_input_data()` | 关键大运 |
| `all_dayuns` | `BaziDataService.get_fortune_data()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` → `build_career_wealth_input_data()` | 所有大运 |

**底层服务**：
- `BaziDataService.get_fortune_data()` - 统一数据服务，获取大运序列

#### 2.3 流年事业财运（liunian_shiye_caiyun）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `special_liunians` | `BaziDataService.get_fortune_data()` | `BaziDisplayService.get_fortune_display()` → `BaziDataService.get_fortune_data()` → `special_liunians` → `build_career_wealth_input_data()` | 特殊流年（与排盘一致） |

**特殊流年数据流**：
1. `BaziDisplayService.get_fortune_display()` - 获取排盘数据
2. `BaziDataService.get_fortune_data(include_special_liunian=True)` - 提取特殊流年
3. `build_career_wealth_input_data()` - 组装到 `special_liunians` 字段

---

## 3. 感情婚姻分析（Marriage）

### 接口信息
- **路径**：`/api/v1/bazi/marriage-analysis/stream`
- **流式生成器**：`marriage_analysis_stream_generator()`
- **input_data 构建函数**：`build_marriage_input_data()`
- **文件位置**：`server/api/v1/marriage_analysis.py`

### input_data 结构

```python
input_data = {
    'mingpan_hunyin': {...},            # 命盘婚姻
    'dayun_hunyin': {...},              # 大运婚姻
    'liunian_hunyin': {...}             # 流年婚姻
}
```

### 数据流明细

#### 3.1 命盘婚姻（mingpan_hunyin）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `day_pillar` | `bazi_data['bazi_pillars']['day']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_marriage_input_data()` | 日柱（配偶宫） |
| `hour_pillar` | `bazi_data['bazi_pillars']['hour']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_marriage_input_data()` | 时柱（子女宫） |
| `hunyin_xing` | `determine_marriage_star()` | `ten_gods_data` + `gender` → `determine_marriage_star()` → `build_marriage_input_data()` | 婚姻星（男命看财，女命看官） |
| `wangshuai` | `wangshuai_result['data']['wangshuai']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `extract_wangshuai_data()` → `build_marriage_input_data()` | 旺衰判断 |
| `xi_ji` | `extract_xi_ji_data()` | `wangshuai_result` → `extract_xi_ji_data()` → `build_marriage_input_data()` | 喜忌数据 |
| `branch_relations` | `bazi_data['relationships']['branch_relations']` | `BaziService.calculate_bazi_full()` → `bazi_data['relationships']` → `build_marriage_input_data()` | 地支刑冲破害 |
| `deities` | `bazi_data['details']` | `BaziService.calculate_bazi_full()` → `bazi_data['details']` → `build_marriage_input_data()` | 神煞数据（桃花、红鸾等） |

#### 3.2 大运婚姻（dayun_hunyin）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `current_dayun` | `identify_key_dayuns()` | `dayun_sequence` + `element_counts` + `current_age` → `identify_key_dayuns()` → `build_marriage_input_data()` | 当前大运 |
| `key_dayuns` | `identify_key_dayuns()` | `dayun_sequence` + `element_counts` + `current_age` → `identify_key_dayuns()` → `build_marriage_input_data()` | 关键大运 |

#### 3.3 流年婚姻（liunian_hunyin）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `special_liunians` | `BaziDataService.get_fortune_data()` | `BaziDisplayService.get_fortune_display()` → `BaziDataService.get_fortune_data()` → `special_liunians` → `build_marriage_input_data()` | 特殊流年（与排盘一致） |

---

## 4. 身体健康分析（Health）

### 接口信息
- **路径**：`/api/v1/bazi/health/stream`
- **流式生成器**：`health_analysis_stream_generator()`
- **input_data 构建函数**：`build_health_input_data()`
- **文件位置**：`server/api/v1/health_analysis.py`

### input_data 结构

```python
input_data = {
    'mingpan_tizhi_zonglun': {...},     # 命盘体质总论
    'wuxing_bingli': {...},             # 五行病理推演
    'dayun_jiankang': {...},            # 大运流年健康警示
    'tizhi_tiaoli': {...}               # 体质调理建议
}
```

### 数据流明细

#### 4.1 命盘体质总论（mingpan_tizhi_zonglun）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `day_master` | `bazi_data['bazi_pillars']['day']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_health_input_data()` | 日主信息 |
| `bazi_pillars` | `bazi_data['bazi_pillars']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_health_input_data()` | 四柱干支 |
| `elements` | `bazi_data['element_counts']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_health_input_data()` | 五行统计 |
| `wangshuai` | `wangshuai_result['data']['wangshuai']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `wangshuai_data` → `build_health_input_data()` | 旺衰判断 |
| `yue_ling` | `bazi_data['bazi_pillars']['month']['branch']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_health_input_data()` | 月令 |
| `wuxing_balance` | `health_result['wuxing_balance']` | `HealthAnalysisService.analyze()` → `health_result` → `build_health_input_data()` | 五行平衡情况 |

**底层服务**：
- `BaziService.calculate_bazi_full()` - 提供八字基础数据
- `WangShuaiService.calculate_wangshuai()` - 提供旺衰数据（**注意：需要从 `wangshuai_result['data']` 提取**）
- `HealthAnalysisService.analyze()` - 提供健康分析结果

#### 4.2 五行病理推演（wuxing_bingli）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `wuxing_shengke` | `health_result['pathology_tendency']['wuxing_relations']` | `HealthAnalysisService.analyze()` → `health_result` → `build_health_input_data()` | 五行生克关系 |
| `body_algorithm` | `health_result['body_algorithm']` | `HealthAnalysisService.analyze()` → `health_result` → `build_health_input_data()` | 五行与五脏对应 |
| `pathology_tendency` | `health_result['pathology_tendency']` | `HealthAnalysisService.analyze()` → `health_result` → `build_health_input_data()` | 病理倾向分析 |

**底层服务**：
- `HealthAnalysisService.analyze()` - 健康分析服务
  - `calculate_body_algorithm()` - 计算五行与五脏对应
  - `analyze_pathology_tendency()` - 分析病理倾向

#### 4.3 大运流年健康警示（dayun_jiankang）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `current_dayun` | `identify_key_dayuns()` + `organize_special_liunians_by_dayun()` | `dayun_sequence` + `special_liunians` → `identify_key_dayuns()` + `organize_special_liunians_by_dayun()` → `build_health_input_data()` | 当前大运（包含流年） |
| `key_dayuns` | `identify_key_dayuns()` + `organize_special_liunians_by_dayun()` | `dayun_sequence` + `special_liunians` → `identify_key_dayuns()` + `organize_special_liunians_by_dayun()` → `build_health_input_data()` | 关键大运（包含流年） |
| `all_dayuns` | `BaziDataService.get_fortune_data()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` → `build_health_input_data()` | 所有大运列表 |
| `ten_gods` | `detail_result['ten_gods']` | `BaziDetailService.calculate_detail_full()` → `detail_result` → `build_health_input_data()` | 十神数据 |

**特殊流年数据流**：
1. `BaziDisplayService.get_fortune_display()` - 获取排盘数据
2. `BaziDataService.get_fortune_data(include_special_liunian=True)` - 提取特殊流年
3. `organize_special_liunians_by_dayun()` - 按大运分组特殊流年（天克地冲、天合地合、岁运并临等）
4. `build_health_input_data()` - 组装到 `current_dayun` 和 `key_dayuns` 的 `liunians` 字段

#### 4.4 体质调理建议（tizhi_tiaoli）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `xi_ji` | `wangshuai_result['data']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `wangshuai_data` → `build_health_input_data()` | 喜忌数据 |
| `wuxing_tiaohe` | `health_result['wuxing_tuning']` | `HealthAnalysisService.analyze()` → `health_result` → `build_health_input_data()` | 五行调和方案 |
| `zangfu_yanghu` | `health_result['zangfu_care']` | `HealthAnalysisService.analyze()` → `health_result` → `build_health_input_data()` | 脏腑养护建议 |

**底层服务**：
- `HealthAnalysisService.analyze()` - 健康分析服务
  - `generate_wuxing_tuning()` - 生成五行调和方案
  - `generate_zangfu_care()` - 生成脏腑养护建议

---

## 5. 子女学习分析（Children Study）

### 接口信息
- **路径**：`/api/v1/bazi/children-study/stream`
- **流式生成器**：`children_study_analysis_stream_generator()`
- **input_data 构建函数**：`build_children_study_input_data()`
- **文件位置**：`server/api/v1/children_study_analysis.py`

### input_data 结构

```python
input_data = {
    'mingpan_zinu_xuexi': {...},       # 命盘子女学习
    'dayun_zinu_xuexi': {...},         # 大运子女学习
    'liunian_zinu_xuexi': {...}        # 流年子女学习
}
```

### 数据流明细

#### 5.1 命盘子女学习（mingpan_zinu_xuexi）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `day_master` | `bazi_data['bazi_pillars']['day']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_children_study_input_data()` | 日主信息 |
| `hour_pillar` | `bazi_data['bazi_pillars']['hour']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_children_study_input_data()` | 时柱（子女宫） |
| `zinv_xing` | `determine_children_star_type()` | `ten_gods_data` + `gender` → `determine_children_star_type()` → `build_children_study_input_data()` | 子女星（男命看官杀，女命看食伤） |
| `wangshuai` | `wangshuai_result['data']['wangshuai']` | `WangShuaiService.calculate_wangshuai()` → `wangshuai_result` → `extract_wangshuai_data()` → `build_children_study_input_data()` | 旺衰判断 |
| `elements` | `bazi_data['element_counts']` | `BaziService.calculate_bazi_full()` → `bazi_data` → `build_children_study_input_data()` | 五行统计 |
| `deities` | `detail_result['deities']` | `BaziDetailService.calculate_detail_full()` → `detail_result` → `build_children_study_input_data()` | 神煞数据 |

#### 5.2 大运子女学习（dayun_zinu_xuexi）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `current_dayun` | `build_enhanced_dayun_structure()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` + `special_liunians` → `build_enhanced_dayun_structure()` → `build_children_study_input_data()` | 当前大运（包含流年） |
| `key_dayuns` | `build_enhanced_dayun_structure()` | `BaziDataService.get_fortune_data()` → `dayun_sequence` + `special_liunians` → `build_enhanced_dayun_structure()` → `build_children_study_input_data()` | 关键大运（包含流年） |

#### 5.3 流年子女学习（liunian_zinu_xuexi）

| 数据项 | 来源 | 数据流路径 | 说明 |
|--------|------|-----------|------|
| `special_liunians` | `BaziDataService.get_fortune_data()` | `BaziDisplayService.get_fortune_display()` → `BaziDataService.get_fortune_data()` → `special_liunians` → `build_children_study_input_data()` | 特殊流年（与排盘一致） |

---

## 6. 年度报告分析（Annual Report）

### 接口信息
- **路径**：`/api/v1/bazi/annual-report/stream`
- **流式生成器**：`annual_report_stream_generator()`
- **文件位置**：`server/api/v1/annual_report_analysis.py`

### 数据流说明

年度报告分析接口使用统一数据获取接口 `BaziDataOrchestrator.fetch_data()`，获取多个模块的数据后组装成 `input_data`。

**主要数据源**：
- `BaziDataOrchestrator.fetch_data()` - 统一数据获取接口
  - `bazi` - 八字基础数据
  - `wangshuai` - 旺衰分析
  - `detail` - 详细计算
  - `dayun` - 大运序列
  - `liunian` - 流年序列
  - `special_liunians` - 特殊流年（通过 `BaziDisplayService.get_fortune_display()` 获取）

---

## 数据源服务说明

### 核心服务

#### 1. BaziService
- **文件**：`server/services/bazi_service.py`
- **方法**：`calculate_bazi_full()`
- **返回数据**：
  - `bazi_pillars` - 四柱干支
  - `element_counts` - 五行统计
  - `ten_gods_stats` - 十神统计
  - `relationships` - 刑冲破害关系
  - `details` - 详细数据（神煞等）

#### 2. WangShuaiService
- **文件**：`server/services/wangshuai_service.py`
- **方法**：`calculate_wangshuai()`
- **返回格式**：`{'success': True, 'data': {...}}`
- **返回数据**（在 `data` 字段中）：
  - `wangshuai` - 旺衰判断
  - `wangshuai_detail` - 旺衰详细说明
  - `xi_shen` - 喜神（十神）
  - `ji_shen` - 忌神（十神）
  - `xi_shen_elements` - 喜神五行
  - `ji_shen_elements` - 忌神五行
  - `tiaohou` - 调候信息

**⚠️ 重要**：使用 `WangShuaiService` 返回的数据时，需要从 `wangshuai_result['data']` 中提取，不能直接使用 `wangshuai_result`。

#### 3. BaziDetailService
- **文件**：`server/services/bazi_detail_service.py`
- **方法**：`calculate_detail_full()`
- **返回数据**：
  - `ten_gods` - 十神数据（主星、藏干）
  - `deities` - 神煞数据
  - `details` - 详细数据（各柱的详细信息）

#### 4. BaziDataService
- **文件**：`server/services/bazi_data_service.py`
- **方法**：`get_fortune_data()`
- **功能**：统一管理大运流年、特殊流年数据的获取
- **返回数据**：
  - `dayun_sequence` - 大运序列（`List[DayunModel]`）
  - `liunian_sequence` - 流年序列（`List[LiunianModel]`）
  - `special_liunians` - 特殊流年（`List[SpecialLiunianModel]`）

**特殊流年获取逻辑**：
1. 调用 `BaziDisplayService.get_fortune_display()` 获取排盘数据
2. 从排盘数据的 `liunian_list` 中提取有 `relations` 的流年
3. 匹配原始流年数据，添加 `dayun_step` 和 `dayun_ganzhi` 信息
4. 排序并返回

#### 5. BaziDisplayService
- **文件**：`server/services/bazi_display_service.py`
- **方法**：`get_fortune_display()`
- **功能**：专业排盘服务，提供大运流年流月数据
- **返回数据**：
  - `liunian['list']` - 流年列表（包含 `relations` 字段）
  - `dayun['list']` - 大运列表

**⚠️ 关键**：所有流式接口的特殊流年数据必须从 `BaziDisplayService.get_fortune_display()` 获取，确保与排盘接口 `/api/v1/bazi/fortune/display` 一致。

#### 6. BaziDataOrchestrator
- **文件**：`server/services/bazi_data_orchestrator.py`
- **方法**：`fetch_data()`
- **功能**：统一数据获取接口，并行调用多个服务
- **支持模块**：
  - `bazi` - 八字基础数据
  - `wangshuai` - 旺衰分析
  - `xishen_jishen` - 喜忌分析
  - `detail` - 详细计算
  - `dayun` - 大运序列
  - `liunian` - 流年序列
  - `special_liunians` - 特殊流年
  - `personality` - 性格分析
  - `rizhu` - 日柱分析
  - `health` - 健康分析
  - `rules` - 规则匹配

#### 7. HealthAnalysisService
- **文件**：`server/services/health_analysis_service.py`
- **方法**：`analyze()`
- **返回数据**：
  - `body_algorithm` - 五行与五脏对应
  - `pathology_tendency` - 病理倾向分析
  - `wuxing_tuning` - 五行调和方案
  - `zangfu_care` - 脏腑养护建议
  - `wuxing_balance` - 五行平衡情况

---

## 数据流关键路径

### 特殊流年数据流（统一路径）

```
用户输入（生辰八字）
    ↓
BaziInputProcessor.process_input() - 处理农历转换、时区转换
    ↓
BaziDisplayService.get_fortune_display() - 获取排盘数据（包含所有流年的 relations）
    ↓
BaziDataService.get_fortune_data(include_special_liunian=True) - 提取特殊流年
    ↓
build_*_input_data() - 组装到 input_data
    ↓
LLM Service - 传给大模型
```

### 旺衰数据流（统一路径）

```
用户输入（生辰八字）
    ↓
BaziInputProcessor.process_input() - 处理农历转换、时区转换
    ↓
WangShuaiService.calculate_wangshuai() - 返回 {'success': True, 'data': {...}}
    ↓
extract_wangshuai_data() - 提取 wangshuai_data = wangshuai_result['data']
    ↓
build_*_input_data() - 使用 wangshuai_data（不是 wangshuai_result）
    ↓
LLM Service - 传给大模型
```

**⚠️ 重要**：所有使用 `WangShuaiService` 的接口都必须先提取 `wangshuai_data = wangshuai_result.get('data', {})`，然后使用 `wangshuai_data`，不能直接使用 `wangshuai_result`。

---

## 注意事项

### 1. 数据一致性
- **特殊流年**：必须从 `BaziDisplayService.get_fortune_display()` 获取，确保与排盘接口一致
- **大运流年**：统一使用 `BaziDataService.get_fortune_data()` 获取

### 2. 数据格式
- **旺衰数据**：`WangShuaiService` 返回格式是 `{'success': True, 'data': {...}}`，需要提取 `data` 字段
- **十神数据**：可能来自 `detail_result['ten_gods']` 或 `bazi_data['ten_gods']`，需要统一提取逻辑

### 3. 数据提取辅助函数
所有 `build_*_input_data()` 函数都包含以下辅助函数：
- `extract_wangshuai_data()` - 从 `wangshuai_result` 中提取旺衰数据
- `extract_ten_gods_data()` - 从 `detail_result` 或 `bazi_data` 中提取十神数据

### 4. 特殊流年分组
- `build_enhanced_dayun_structure()` - 按大运分组特殊流年，添加优先级、描述等
- `organize_special_liunians_by_dayun()` - 按大运分组特殊流年（用于健康分析）

---

## 更新日志

- **2026-01-16**：创建文档，详细记录所有流式接口的 input_data 数据流
- **2026-01-16**：补充旺衰数据提取说明（从 `wangshuai_result['data']` 提取）
- **2026-01-16**：补充特殊流年数据流说明（从 `BaziDisplayService.get_fortune_display()` 获取）

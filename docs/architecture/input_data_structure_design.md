# input_data 数据结构设计思路

## 核心设计原则

### 1. 分层设计：原始数据 → input_data → formatted_data (prompt)

```
[基础服务数据] → [input_data] → [formatted_data] → [大模型]
   (bazi_data)    (结构化)      (JSON字符串)      (LLM Prompt)
```

### 2. 统一构建入口，差异化格式化

- **input_data 构建**：各场景使用相同的 `build_input_data_from_result()` 函数，但传入不同的 `format_name`
- **formatted_data 构建**：各场景使用不同的格式化函数（`format_*_input_data_for_coze()` 或 `build_*_prompt()`）

## input_data 结构设计

### 通用结构模式

所有场景的 `input_data` 都遵循以下分层结构：

```
input_data = {
    # 1. 命盘基础层（各场景不同命名，但都包含八字核心数据）
    "mingpan_*_zonglun": {
        "bazi_pillars": {...},      # 四柱信息
        "day_master": {...},         # 日主信息
        "wangshuai": "...",          # 旺衰
        "ten_gods": {...},           # 十神配置
        "elements": {...},           # 五行分布
        ...
    },
    
    # 2. 场景特定数据层（根据场景需求组织）
    "scene_specific_data": {
        "current_dayun": {...},      # 当前大运
        "key_dayuns": [...],         # 关键大运
        "rules": [...],              # 匹配的规则
        ...
    },
    
    # 3. 建议/调理层（可选的后续分析数据）
    "suggestions": {
        "xi_ji": {...},              # 喜忌神
        ...
    }
}
```

### 各场景 input_data 结构对比

| 场景 | 命盘基础层 | 场景特定层 | 格式化函数 |
|------|-----------|-----------|-----------|
| **健康分析** | `mingpan_tizhi_zonglun` | `wuxing_bingli`, `dayun_jiankang`, `tizhi_tiaoli`, `health_rules` | `build_health_prompt()` (自然语言) |
| **事业财富** | `mingpan_shiye_caifu_zonglun` | `shiye_xing_gong`, `caifu_xing_gong`, `shiye_yunshi`, `caifu_yunshi`, `tiyun_jianyi` | `format_career_wealth_input_data_for_coze()` (JSON) |
| **感情婚姻** | `mingpan_zonglun` | `peiou_tezheng`, `ganqing_zoushi`, `shensha_dianjing`, `jianyi_fangxiang` | `format_marriage_input_data_for_coze()` (JSON) |
| **子女学习** | `mingpan_zinv_zonglun` | `zinvxing_zinvgong`, `shengyu_shiji`, `yangyu_jianyi`, `children_rules` | `format_children_study_input_data_for_coze()` (JSON) |
| **总评分析** | `mingpan_hexin_geju` | `xingge_tezhi`, `shiye_caiyun`, `jiating_liuqin`, `jiankang_yaodian`, `guanjian_dayun`, `zhongsheng_tidian` | `format_general_review_input_data_for_coze()` (JSON) |

### 数据引用优化策略（避免重复）

在 `formatted_data` 构建时，使用**引用而非复制**来减少 Token 消耗：

```python
# ✅ 优化后（引用）
optimized_data = {
    'mingpan_zonglun': mingpan,  # 完整数据只存储一次
    'peiou_tezheng': {
        'ten_gods': mingpan.get('ten_gods', {}),  # 引用，不重复存储
        'deities': peiou.get('deities', {}),
        ...
    }
}

# ❌ 优化前（重复）
unoptimized_data = {
    'mingpan_zonglun': {
        'ten_gods': {...},  # 第一次存储
        ...
    },
    'peiou_tezheng': {
        'ten_gods': {...},  # 重复存储，浪费 Token
        ...
    }
}
```

## formatted_data 两种格式

### 格式 1：JSON 字符串（大多数场景）

```python
formatted_data = json.dumps(optimized_data, ensure_ascii=False, indent=2)
```

**使用场景**：
- 事业财富、感情婚姻、子女学习、总评分析

**特点**：
- Coze Bot 的 System Prompt 中配置模板，使用 `{{input}}` 占位符
- 代码只发送数据，不发送模板文本
- **优点**：节省 Token，数据与模板分离

### 格式 2：自然语言 Prompt（健康分析）

```python
prompt = build_health_prompt(input_data)
# 返回完整的自然语言提示词字符串
```

**使用场景**：
- 健康分析

**特点**：
- 直接返回完整的 Prompt 文本
- **优点**：Prompt 结构更灵活，适合复杂分析场景

## 数据流转链路

### 流式接口（生产环境）

```
前端请求 → API 接口 (/xxx/stream)
  ↓
1. 获取基础数据（bazi_data, wangshuai_result, detail_result）
  ↓
2. 获取大运流年数据（BaziDataService.get_fortune_data）
  ↓
3. 匹配规则（RuleService.match_rules）
  ↓
4. 构建 input_data（build_input_data_from_result）
  ↓
5. 格式化 formatted_data（format_*_input_data_for_coze / build_*_prompt）
  ↓
6. 传递给大模型（llm_service.stream_analysis(formatted_data)）
```

### 评测接口（评测环境）

```
评测脚本 → Debug 接口 (/xxx/debug)
  ↓
1-4. 与流式接口相同（步骤 1-4）
  ↓
5. 返回 input_data（不返回 formatted_data）
  ↓
评测脚本：
  ↓
6. 构建 formatted_data（使用相同的格式化函数）
  ↓
7. 传递给大模型（bailian_client.call_stream(formatted_data)）
```

**关键一致性保证**：
- 步骤 1-4 使用相同的数据获取和构建逻辑
- 步骤 5/6 使用相同的格式化函数（`prompt_builders.py`）

## 设计亮点

### 1. 统一与灵活的平衡

- **统一**：input_data 构建使用统一函数，数据获取逻辑一致
- **灵活**：各场景的 formatted_data 格式可定制（JSON 或自然语言）

### 2. 评测与生产的一致性

- **同一套数据构建逻辑**：确保 `input_data` 一致
- **同一个格式化函数**：确保 `formatted_data` 一致
- **结果**：评测结果与生产环境完全一致

### 3. Token 优化

- **引用而非复制**：减少重复数据
- **数据与模板分离**：JSON 格式场景中，模板存储在 Coze Bot 配置中
- **精简大运数据**：`_simplify_dayun()` 只保留关键字段

### 4. 可维护性

- **集中管理**：所有格式化函数集中在 `prompt_builders.py`
- **易于扩展**：新增场景只需添加新的格式化函数
- **向后兼容**：API 接口导入函数，无需修改调用代码

## 关键文件

| 文件 | 职责 |
|------|------|
| `server/config/input_format_loader.py` | input_data 构建（数据库格式定义） |
| `server/utils/prompt_builders.py` | formatted_data 构建（所有格式化函数） |
| `server/api/v1/*_analysis.py` | 流式接口（使用上述函数构建数据） |
| `scripts/evaluation/api_client.py` | 评测脚本（使用相同函数确保一致性） |

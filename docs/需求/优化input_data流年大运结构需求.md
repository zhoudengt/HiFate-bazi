# 优化 input_data 流年大运结构需求文档

## 一、需求背景

当前 `input_data` 中的流年大运结构不完善，存在以下问题：

1. **大运数量不足**：只获取当前大运及前后各一个（共3个），无法满足分析需求
2. **流年归属不准确**：可能出现大运A，但流年却是B大运下的情况
3. **缺少优先级机制**：无法区分哪些大运和流年更重要
4. **缺少描述信息**：没有年龄段标签、人生阶段标签等，不利于LLM理解和检索
5. **年龄和大运计算不一致**：可能与排盘系统不一致

## 二、核心需求

### 2.1 统一接口不能变

- ✅ **不能修改** `BaziDataService.get_fortune_data()` 等统一接口
- ✅ **不能修改** `BaziDataService.DEFAULT_DAYUN_MODE` 等默认配置
- ✅ 只调整 `input_data` 的流年大运结构，其他功能不受影响

### 2.2 工具函数需求（公共功能）

需要创建公共工具函数，供所有 `input_data` 构建函数使用：

#### 2.2.1 计算用户年龄

**函数名**：`calculate_user_age(solar_date: str, current_time: Optional[datetime] = None) -> int`

**计算方式**：与排盘系统保持一致，使用**虚岁**
```python
current_year = current_time.year if current_time else datetime.now().year
birth_year = int(solar_date.split('-')[0])
current_age = current_year - birth_year + 1  # 虚岁计算
```

**位置**：`server/utils/dayun_liunian_helper.py`（新建工具文件）

#### 2.2.2 确定用户当前大运

**函数名**：`get_current_dayun(dayun_sequence: List[Dict[str, Any]], current_age: int) -> Optional[Dict[str, Any]]`

**确定方式**：与排盘系统保持一致
- 遍历 `dayun_sequence`，找到 `age_range.start <= current_age <= age_range.end` 的大运
- 必须与排盘系统显示的大运一致（例如排盘显示"甲午"，这里也必须返回"甲午"）

**位置**：`server/utils/dayun_liunian_helper.py`

### 2.3 基于当前大运和年龄计算10个大运

#### 2.3.1 大运选择规则

1. **以当前大运为中心**，向前向后各选择若干个大运，总共至少10个
2. **优先级规则**（按距离当前大运的远近）：
   - 优先级1：当前大运（最高优先级）
   - 优先级2：下一个大运（未来第一个）
   - 优先级3：前一个大运（过去第一个）
   - 优先级4：再下一个大运（未来第二个）
   - 优先级5：再前一个大运（过去第二个）
   - ...以此类推

**示例**（假设当前大运是第4步）：
```
优先级1: 第4步（当前大运）
优先级2: 第5步（下一个）
优先级3: 第3步（前一个）
优先级4: 第6步（再下一个）
优先级5: 第2步（再前一个）
优先级6: 第7步
优先级7: 第1步
优先级8: 第8步
优先级9: 第0步
优先级10: 第9步
```

#### 2.3.2 大运数据结构

每个大运包含以下字段：

```python
{
    'step': 4,                    # 大运步骤
    'stem': '戊',                 # 天干
    'branch': '辰',               # 地支
    'ganzhi': '戊辰',             # 干支
    'year_start': 2025,           # 起始年份
    'year_end': 2034,             # 结束年份
    'age_range': {'start': 40, 'end': 49},  # 年龄范围
    'age_display': '40-49岁',     # 年龄显示
    'priority': 1,                # 优先级（1最高，数字越大优先级越低）
    'life_stage': '中年',          # 人生阶段标签（童年/青年/中年/老年）
    'description': '当前大运，重点关注',  # 描述信息
    'note': '用户当前处于此大运，需要重点分析',  # 备注信息
    'main_star': '正官',          # 主星
    'hidden_stars': ['正财'],     # 副星列表
    'nayin': '大林木',            # 纳音
    'deities': ['天乙贵人'],       # 神煞列表
    'liunians': [...]            # 特殊流年列表（见下方）
}
```

### 2.4 特殊流年处理

#### 2.4.1 流年归属规则

- **流年必须归属到对应的大运**：不能出现大运A，流年却是B大运下的情况
- 通过 `special_liunian.dayun_step` 字段确定流年归属
- 每个大运下的流年，必须满足 `liunian.dayun_step == dayun.step`

#### 2.4.2 流年优先级规则

1. **大运优先级决定流年优先级**：优先级高的大运，其下的流年优先级也高
2. **同一大运内流年的优先级**（按原有方式）：
   - 优先级1：天克地冲流年
   - 优先级2：天合地合流年
   - 优先级3：岁运并临流年
   - 优先级4：其他特殊流年

#### 2.4.3 流年数据结构

每个流年包含以下字段：

```python
{
    'year': 2025,                 # 年份
    'stem': '乙',                 # 天干
    'branch': '巳',               # 地支
    'ganzhi': '乙巳',             # 干支
    'age': 40,                    # 用户年龄
    'age_display': '40岁',        # 年龄显示
    'life_stage': '中年',          # 人生阶段标签
    'priority': 1,                # 优先级（继承自大运优先级 + 流年类型优先级）
    'type': 'tiankedi_chong',     # 流年类型（tiankedi_chong/tianhedi_he/suiyun_binglin/other）
    'type_display': '天克地冲',    # 流年类型显示
    'description': '天克地冲流年，需重点关注',  # 描述信息
    'note': '此流年与日柱天克地冲，对子女学习有重要影响',  # 备注信息
    'dayun_step': 4,              # 所属大运步骤（必须与父大运的step一致）
    'dayun_ganzhi': '戊辰',       # 所属大运干支
    'relations': [{'type': '冲', 'target': '日柱'}],  # 关系列表
    'main_star': '正财',           # 主星
    'nayin': '覆灯火',             # 纳音
    'deities': ['天乙贵人'],       # 神煞列表
    'details': {...}              # 详细信息
}
```

### 2.5 描述与备注信息

#### 2.5.1 人生阶段标签

**标准定义**：
- **童年**：0-12岁
- **青年**：13-30岁
- **中年**：31-60岁
- **老年**：61岁及以上

**应用规则**：
- 大运的 `life_stage`：根据大运的 `age_range` 的中点年龄确定
- 流年的 `life_stage`：根据流年的 `age` 确定

#### 2.5.2 描述信息生成规则

**大运描述**：
- 优先级1（当前大运）：`"当前大运，重点关注"`
- 优先级2-3：`"近期大运，需要关注"`
- 优先级4-6：`"重要大运，值得参考"`
- 优先级7-10：`"参考大运"`

**流年描述**：
- 根据流年类型生成：
  - 天克地冲：`"天克地冲流年，需重点关注"`
  - 天合地合：`"天合地合流年，需要关注"`
  - 岁运并临：`"岁运并临流年，值得注意"`
  - 其他：`"特殊流年，可参考"`

#### 2.5.3 备注信息生成规则

**大运备注**：
- 优先级1：`"用户当前处于此大运，需要重点分析"`
- 优先级2-3：`"用户即将进入/刚离开此大运，需要关注"`
- 其他：`"参考大运，可简要提及"`

**流年备注**：
- 根据流年类型和关系生成，例如：
  - `"此流年与日柱天克地冲，对子女学习有重要影响"`
  - `"此流年与大运天合地合，对运势有积极影响"`

### 2.6 优先级在描述中的应用

**描述优先级规则**：
- **优先级1（最高）**：重点说，多说，详细分析
- **优先级2-3（高）**：次之，适当展开
- **优先级4-6（中）**：简要提及
- **优先级7-10（低）**：提一下即可

**实现方式**：
- 在 `input_data` 中添加 `priority_description` 字段，说明优先级规则
- LLM可以根据优先级决定描述详细程度

## 三、数据结构设计

### 3.1 优化后的 input_data 结构

```python
input_data = {
    # ... 其他字段保持不变 ...
    
    # 3. 生育时机（优化后）
    'shengyu_shiji': {
        'zinv_xing_type': zinv_xing_type,
        
        # 当前大运（优先级1）
        'current_dayun': {
            'step': 4,
            'stem': '戊',
            'branch': '辰',
            'ganzhi': '戊辰',
            'year_start': 2025,
            'year_end': 2034,
            'age_range': {'start': 40, 'end': 49},
            'age_display': '40-49岁',
            'priority': 1,  # 最高优先级
            'life_stage': '中年',
            'description': '当前大运，重点关注',
            'note': '用户当前处于此大运，需要重点分析',
            'main_star': '正官',
            'hidden_stars': ['正财'],
            'nayin': '大林木',
            'deities': ['天乙贵人'],
            'liunians': [  # 特殊流年列表（按优先级排序）
                {
                    'year': 2025,
                    'stem': '乙',
                    'branch': '巳',
                    'ganzhi': '乙巳',
                    'age': 40,
                    'age_display': '40岁',
                    'life_stage': '中年',
                    'priority': 1,  # 继承大运优先级 + 流年类型优先级
                    'type': 'tiankedi_chong',
                    'type_display': '天克地冲',
                    'description': '天克地冲流年，需重点关注',
                    'note': '此流年与日柱天克地冲，对子女学习有重要影响',
                    'dayun_step': 4,  # 必须与父大运的step一致
                    'dayun_ganzhi': '戊辰',
                    'relations': [{'type': '冲', 'target': '日柱'}],
                    'main_star': '正财',
                    'nayin': '覆灯火',
                    'deities': ['天乙贵人'],
                    'details': {...}
                },
                # ... 更多流年
            ]
        },
        
        # 关键大运列表（优先级2-10，按优先级排序）
        'key_dayuns': [
            {
                'step': 5,
                'stem': '己',
                'branch': '巳',
                'ganzhi': '己巳',
                'year_start': 2035,
                'year_end': 2044,
                'age_range': {'start': 50, 'end': 59},
                'age_display': '50-59岁',
                'priority': 2,  # 下一个大运
                'life_stage': '中年',
                'description': '近期大运，需要关注',
                'note': '用户即将进入此大运，需要关注',
                'main_star': '偏印',
                'hidden_stars': ['正财'],
                'nayin': '大林木',
                'deities': [],
                'liunians': [...]  # 此大运下的特殊流年
            },
            {
                'step': 3,
                'stem': '丁',
                'branch': '卯',
                'ganzhi': '丁卯',
                'year_start': 2015,
                'year_end': 2024,
                'age_range': {'start': 30, 'end': 39},
                'age_display': '30-39岁',
                'priority': 3,  # 前一个大运
                'life_stage': '青年',
                'description': '近期大运，需要关注',
                'note': '用户刚离开此大运，需要关注',
                'main_star': '偏印',
                'hidden_stars': ['正财'],
                'nayin': '炉中火',
                'deities': [],
                'liunians': [...]  # 此大运下的特殊流年
            },
            # ... 至少10个大运，按优先级排序
        ],
        
        # 所有大运列表（用于参考，按step排序）
        'all_dayuns': [
            # ... 所有大运，保持原有结构
        ],
        
        'ten_gods': ten_gods_data,
        
        # 新增：优先级说明
        'priority_description': {
            'rule': '优先级1（当前大运）重点说，多说；优先级2-3次之；优先级4-6简要提及；优先级7-10提一下即可',
            'current_dayun_priority': 1,
            'total_dayuns': 10
        }
    },
    
    # ... 其他字段保持不变 ...
}
```

## 四、实现方案

### 4.1 创建工具函数文件

**文件**：`server/utils/dayun_liunian_helper.py`（新建）

**函数列表**：
1. `calculate_user_age(solar_date: str, current_time: Optional[datetime] = None) -> int`
2. `get_current_dayun(dayun_sequence: List[Dict[str, Any]], current_age: int) -> Optional[Dict[str, Any]]`
3. `select_dayuns_with_priority(dayun_sequence: List[Dict[str, Any]], current_dayun: Dict[str, Any], count: int = 10) -> List[Dict[str, Any]]`
4. `organize_liunians_by_dayun_with_priority(special_liunians: List[Dict[str, Any]], dayun_sequence: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]`
5. `add_life_stage_label(age: int) -> str`
6. `add_dayun_description(dayun: Dict[str, Any], priority: int) -> Dict[str, Any]`
7. `add_liunian_description(liunian: Dict[str, Any], priority: int) -> Dict[str, Any]`

### 4.2 修改 build_children_study_input_data 函数

**文件**：`server/api/v1/children_study_analysis.py`

**修改内容**：
1. 导入工具函数
2. 使用工具函数计算年龄和当前大运
3. 使用工具函数选择10个大运（带优先级）
4. 使用工具函数组织流年（确保归属正确）
5. 使用工具函数添加描述和备注信息
6. 构建优化后的 `input_data` 结构

### 4.3 其他接口复用

工具函数设计为公共功能，其他接口（健康、事业财富、总评、婚姻等）也可以使用。

## 五、数据格式示例

### 5.1 完整案例数据

**假设用户**：1985-05-15 14:30，male，当前2025年，40岁（虚岁）

**当前大运**：第4步，戊辰（2025-2034，40-49岁）

**优化后的 input_data.shengyu_shiji**：

```python
{
    'zinv_xing_type': '官杀',  # 男命看官杀
    
    'current_dayun': {
        'step': 4,
        'stem': '戊',
        'branch': '辰',
        'ganzhi': '戊辰',
        'year_start': 2025,
        'year_end': 2034,
        'age_range': {'start': 40, 'end': 49},
        'age_display': '40-49岁',
        'priority': 1,
        'life_stage': '中年',
        'description': '当前大运，重点关注',
        'note': '用户当前处于此大运，需要重点分析',
        'main_star': '正官',
        'hidden_stars': ['正财', '比肩'],
        'nayin': '大林木',
        'deities': ['天乙贵人'],
        'liunians': [
            {
                'year': 2025,
                'stem': '乙',
                'branch': '巳',
                'ganzhi': '乙巳',
                'age': 40,
                'age_display': '40岁',
                'life_stage': '中年',
                'priority': 1,
                'type': 'tiankedi_chong',
                'type_display': '天克地冲',
                'description': '天克地冲流年，需重点关注',
                'note': '此流年与日柱天克地冲，对子女学习有重要影响',
                'dayun_step': 4,
                'dayun_ganzhi': '戊辰',
                'relations': [{'type': '冲', 'target': '日柱'}],
                'main_star': '正财',
                'nayin': '覆灯火',
                'deities': ['天乙贵人']
            },
            {
                'year': 2027,
                'stem': '丁',
                'branch': '未',
                'ganzhi': '丁未',
                'age': 42,
                'age_display': '42岁',
                'life_stage': '中年',
                'priority': 1,
                'type': 'tianhedi_he',
                'type_display': '天合地合',
                'description': '天合地合流年，需要关注',
                'note': '此流年与大运天合地合，对运势有积极影响',
                'dayun_step': 4,
                'dayun_ganzhi': '戊辰',
                'relations': [{'type': '合', 'target': '大运'}],
                'main_star': '偏印',
                'nayin': '天河水',
                'deities': []
            }
        ]
    },
    
    'key_dayuns': [
        {
            'step': 5,
            'stem': '己',
            'branch': '巳',
            'ganzhi': '己巳',
            'year_start': 2035,
            'year_end': 2044,
            'age_range': {'start': 50, 'end': 59},
            'age_display': '50-59岁',
            'priority': 2,
            'life_stage': '中年',
            'description': '近期大运，需要关注',
            'note': '用户即将进入此大运，需要关注',
            'main_star': '偏印',
            'hidden_stars': ['正财'],
            'nayin': '大林木',
            'deities': [],
            'liunians': [
                {
                    'year': 2035,
                    'stem': '乙',
                    'branch': '卯',
                    'ganzhi': '乙卯',
                    'age': 50,
                    'age_display': '50岁',
                    'life_stage': '中年',
                    'priority': 2,
                    'type': 'suiyun_binglin',
                    'type_display': '岁运并临',
                    'description': '岁运并临流年，值得注意',
                    'note': '此流年与大运岁运并临，对运势有重要影响',
                    'dayun_step': 5,
                    'dayun_ganzhi': '己巳',
                    'relations': [{'type': '并临', 'target': '大运'}],
                    'main_star': '正财',
                    'nayin': '大溪水',
                    'deities': []
                }
            ]
        },
        {
            'step': 3,
            'stem': '丁',
            'branch': '卯',
            'ganzhi': '丁卯',
            'year_start': 2015,
            'year_end': 2024,
            'age_range': {'start': 30, 'end': 39},
            'age_display': '30-39岁',
            'priority': 3,
            'life_stage': '青年',
            'description': '近期大运，需要关注',
            'note': '用户刚离开此大运，需要关注',
            'main_star': '偏印',
            'hidden_stars': ['正财'],
            'nayin': '炉中火',
            'deities': [],
            'liunians': []
        },
        # ... 至少10个大运
    ],
    
    'all_dayuns': [
        # ... 所有大运列表（用于参考）
    ],
    
    'ten_gods': ten_gods_data,
    
    'priority_description': {
        'rule': '优先级1（当前大运）重点说，多说；优先级2-3次之；优先级4-6简要提及；优先级7-10提一下即可',
        'current_dayun_priority': 1,
        'total_dayuns': 10
    }
}
```

## 六、实现约束

### 6.1 不能修改的内容

- ❌ 不能修改 `BaziDataService.get_fortune_data()` 等统一接口
- ❌ 不能修改 `BaziDataService.DEFAULT_DAYUN_MODE` 等默认配置
- ❌ 不能修改其他接口的 `input_data` 结构（除非明确需要）
- ❌ 不能影响其他功能

### 6.2 只涉及的内容

- ✅ 只调整 `input_data` 的流年大运结构
- ✅ 只修改 `build_children_study_input_data()` 函数
- ✅ 创建公共工具函数供其他接口复用

## 七、验证要点

1. ✅ 年龄计算与排盘系统一致（虚岁）
2. ✅ 当前大运与排盘系统一致
3. ✅ 大运数量 ≥ 10个
4. ✅ 大运按优先级排序（当前大运优先级1，距离越近优先级越高）
5. ✅ 流年归属正确（流年的 `dayun_step` 必须与父大运的 `step` 一致）
6. ✅ 流年优先级正确（继承大运优先级 + 流年类型优先级）
7. ✅ 人生阶段标签正确（童年/青年/中年/老年）
8. ✅ 描述和备注信息完整
9. ✅ 优先级说明清晰

## 八、后续扩展

其他接口（健康、事业财富、总评、婚姻等）也可以使用相同的工具函数和数据结构，保持一致性。


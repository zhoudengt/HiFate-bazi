# 优化 input_data 流年大运结构 - 事业财富分析

## 需求背景

参考"八字命理-子女学习"和"八字命理-感情婚姻"的优化方案，对"八字命理-事业财富"的 `input_data` 进行优化，使用方案2（占位符模板），确保大运流年格式与取数规则与其他接口一致。

## 当前问题

### 1. 使用方案1（自然语言 Prompt）
- 代码中包含提示词模板（`build_natural_language_prompt` 函数）
- 不符合"提示词必须存储在 Coze Bot 中"的要求

### 2. 大运流年格式不一致
- 使用 `identify_key_dayuns` 函数，而非 `build_enhanced_dayun_structure`
- 没有优先级、描述、备注、人生阶段等信息
- 没有使用工具函数计算年龄和当前大运
- 与排盘系统不一致

### 3. 年龄计算不一致
- 使用 `calculate_age` 函数，可能与其他接口不一致
- 应该使用 `calculate_user_age`（虚岁，与排盘一致）

### 4. 数据重复
- 十神数据在多个地方出现
- 旺衰数据可能重复
- 大运流年数据重复

### 5. 数据提取不完整
- 十神从 `bazi_data.get('ten_gods_stats', {})` 获取，可能为空
- 旺衰从 `wangshuai_data.get('wangshuai', '')` 获取，但 `wangshuai_data` 可能未正确提取
- 喜忌数据提取逻辑不完整

### 6. 流年数据不完整
- 没有使用增强的大运流年结构
- 没有优先级排序
- 没有描述和备注信息
- 没有清理流月流日字段
- 没有限制流年数量

## 优化目标

### 1. 使用方案2（占位符模板）
- ✅ 移除代码中的提示词模板
- ✅ 提示词存储在 Coze Bot 的 System Prompt 中
- ✅ 代码只负责数据提取和格式化

### 2. 大运流年格式与其他接口一致
- ✅ 使用 `calculate_user_age` 计算年龄（虚岁，与排盘一致）
- ✅ 使用 `get_current_dayun` 确定当前大运（与排盘一致）
- ✅ 使用 `build_enhanced_dayun_structure` 构建增强的大运流年结构
- ✅ 当前大运 + 关键大运（共10个），按优先级排序
- ✅ 每个大运包含：优先级、描述、备注、人生阶段、年龄范围等
- ✅ 每个大运下只保留3个优先级最高的流年
- ✅ 移除流月流日字段

### 3. 数据不重复
- ✅ 使用引用避免重复存储
- ✅ 十神数据只提取一次，其他地方引用
- ✅ 旺衰数据只提取一次，其他地方引用
- ✅ 大运流年数据只提取一次，其他地方引用

### 4. 数据提取完整
- ✅ 修复旺衰数据提取（从 `wangshuai_result.get('data', {})` 提取）
- ✅ 修复十神数据提取（从 `detail_result.details` 或 `bazi_data.details` 提取）
- ✅ 修复喜忌数据提取（从 `wangshuai_data` 提取，包括 `final_xi_ji`）

## 实施步骤

### 阶段一：创建需求文档 ✅

创建本文档，说明当前问题、优化目标和实施步骤。

### 阶段二：优化数据提取逻辑

1. **添加数据提取辅助函数**（参考感情婚姻和子女学习）：
   - `extract_wangshuai_data()` - 从 `wangshuai_result` 中提取旺衰数据
   - `extract_ten_gods_data()` - 从 `detail_result` 或 `bazi_data` 中提取十神数据

2. **使用工具函数**：
   - 导入 `dayun_liunian_helper` 中的工具函数
   - 使用 `calculate_user_age` 计算年龄（替代 `calculate_age`）
   - 使用 `get_current_dayun` 确定当前大运
   - 使用 `build_enhanced_dayun_structure` 构建增强的大运流年结构（替代 `identify_key_dayuns`）

3. **优化大运流年提取**：
   - 移除 `identify_key_dayuns` 的使用
   - 使用与子女学习/感情婚姻一致的逻辑：当前大运 + 关键大运（共10个）
   - 清理流月流日字段
   - 限制每个大运下流年数量为3个

### 阶段三：创建数据构建和格式化函数

1. **创建 `build_career_wealth_input_data` 函数**：
   - 参考 `build_marriage_input_data` 和 `build_children_study_input_data` 的结构
   - 提取所有必需数据
   - 使用引用避免重复

2. **创建 `format_input_data_for_coze` 函数**：
   - 参考感情婚姻和子女学习的实现
   - 将结构化数据格式化为 JSON 字符串
   - 使用引用避免重复

### 阶段四：修改接口调用

1. **修改 `career_wealth_stream_generator` 函数**：
   - 移除 `build_natural_language_prompt` 调用
   - 使用 `format_input_data_for_coze` 格式化数据
   - 直接发送格式化后的数据给 Bot
   - 添加 `detail_result` 的获取（用于提取十神数据）

2. **创建测试接口**：
   - `POST /api/v1/career-wealth/test` - 返回格式化后的数据

3. **更新 debug 接口**（如果存在）：
   - 添加 `formatted_data` 字段

### 阶段五：创建 Coze Bot System Prompt 文档

1. **创建文档**：`docs/需求/Coze_Bot_System_Prompt_事业财富分析.md`
   - 基于用户提供的提示词
   - 优化和完善提示词
   - 提供可直接复制粘贴的完整版本

### 阶段六：更新开发规范（已完成）

已在 `docs/standards/llm-development.md` 中添加了方案2的说明。

## 数据完整性要求

确保以下字段都有值：

1. **旺衰数据**：
   - `mingpan_shiye_caifu_zonglun.wangshuai` 不为空
   - `tiyun_jianyi.xi_ji` 中的 `xi_shen`、`ji_shen` 不为空

2. **十神数据**：
   - `mingpan_shiye_caifu_zonglun.ten_gods` 不为空（格式：`{'year': {...}, 'month': {...}, 'day': {...}, 'hour': {...}}`）
   - `shiye_xing_gong.ten_gods` 引用 `mingpan_shiye_caifu_zonglun.ten_gods`
   - `caifu_xing_gong.ten_gods` 引用 `mingpan_shiye_caifu_zonglun.ten_gods`
   - `tiyun_jianyi.ten_gods_summary` 引用 `mingpan_shiye_caifu_zonglun.ten_gods`

3. **喜忌数据**：
   - `tiyun_jianyi.xi_ji.xi_shen` 不为空
   - `tiyun_jianyi.xi_ji.ji_shen` 不为空
   - `tiyun_jianyi.xi_ji.xi_ji_elements` 不为空

4. **大运流年**：
   - `shiye_yunshi.current_dayun` 不为空（包含优先级、描述、备注、流年等）
   - `shiye_yunshi.key_dayuns` 不为空（至少9个关键大运）
   - `shiye_yunshi.current_dayun.liunians` 每个大运下最多3个流年
   - `caifu_yunshi.current_dayun` 引用 `shiye_yunshi.current_dayun`
   - `caifu_yunshi.key_dayuns` 引用 `shiye_yunshi.key_dayuns`

## 约束条件

- ✅ **只修改**：`server/api/v1/career_wealth_analysis.py`
- ❌ **不修改**：统一接口（`BaziDataService`）、底层服务、其他接口、前端接口

## 验证标准

1. **数据完整性**：所有必需字段都有值，无缺失
2. **大运流年格式**：与子女学习/感情婚姻一致（优先级、描述、备注等）
3. **数据不重复**：使用引用，节省 Token
4. **输出质量**：与方案1的输出质量一致

## 参考文档

- `docs/需求/优化input_data流年大运结构-子女学习.md` - 子女学习的优化方案
- `docs/需求/优化input_data流年大运结构-感情婚姻.md` - 感情婚姻的优化方案
- `docs/需求/优化input_data流年大运结构需求.md` - 通用需求文档
- `server/utils/dayun_liunian_helper.py` - 工具函数文件
- `server/api/v1/children_study_analysis.py` - 子女学习的实现参考
- `server/api/v1/marriage_analysis.py` - 感情婚姻的实现参考


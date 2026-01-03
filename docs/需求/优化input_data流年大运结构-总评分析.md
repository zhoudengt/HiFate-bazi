# 优化 input_data 流年大运结构 - 总评分析

## 需求背景

参考"八字命理-子女学习"、"八字命理-感情婚姻"、"八字命理-事业财富"和"八字命理-身体健康"的优化方案，对"八字命理-总评分析"的 `input_data` 进行优化，使用方案2（占位符模板），确保大运流年格式与取数规则与其他接口一致。

## 当前问题

### 1. 使用方案1（自然语言 Prompt）
- 代码中包含提示词模板（`build_general_review_prompt` 函数）
- 不符合"提示词必须存储在 Coze Bot 中"的要求

### 2. 大运流年格式不一致
- 使用简单的日期差值计算年龄（非虚岁），而非 `calculate_user_age`
- 手动遍历大运序列找当前大运，而非 `get_current_dayun`
- 只获取关键大运（第2-4步），而非使用 `build_enhanced_dayun_structure`（当前大运 + 关键大运，共10个）
- 大运数据结构简单，没有优先级、描述、备注、人生阶段等字段
- 没有限制流年数量，没有清理流月流日字段
- 与排盘系统不一致

### 3. 年龄计算不一致
- 使用简单的日期差值计算，可能与其他接口不一致
- 应该使用 `calculate_user_age`（虚岁，与排盘一致）

### 4. 数据提取可能不完整
- 旺衰数据提取可能不正确
- 十神数据提取可能不完整
- 喜忌数据提取逻辑需要验证

### 5. 流年数据不完整
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

1. **添加数据提取辅助函数**（参考其他接口）：
   - `extract_wangshuai_data()` - 从 `wangshuai_result` 中提取旺衰数据
   - `extract_ten_gods_data()` - 从 `detail_result` 或 `bazi_data` 中提取十神数据

2. **使用工具函数**：
   - 导入 `dayun_liunian_helper` 中的工具函数
   - 使用 `calculate_user_age` 计算年龄（替代当前的计算方式）
   - 使用 `get_current_dayun` 确定当前大运
   - 使用 `build_enhanced_dayun_structure` 构建增强的大运流年结构

3. **优化大运流年提取**：
   - 使用与子女学习/感情婚姻/事业财富/身体健康一致的逻辑：当前大运 + 关键大运（共10个）
   - 清理流月流日字段
   - 限制每个大运下流年数量为3个

### 阶段三：创建数据构建和格式化函数

1. **优化 `build_general_review_input_data` 函数**：
   - 参考其他接口的实现
   - 使用新的工具函数
   - 使用引用避免重复

2. **创建 `format_input_data_for_coze` 函数**：
   - 参考其他接口的实现
   - 将结构化数据格式化为 JSON 字符串
   - 使用引用避免重复

### 阶段四：修改接口调用

1. **修改 `general_review_analysis_stream_generator` 函数**：
   - 移除 `build_general_review_prompt` 调用
   - 使用 `format_input_data_for_coze` 格式化数据
   - 直接发送格式化后的数据给 Bot

2. **创建测试接口**：
   - `POST /api/v1/general-review/test` - 返回格式化后的数据

3. **更新 debug 接口**：
   - 添加 `formatted_data` 字段

### 阶段五：更新 Coze Bot System Prompt 文档

1. **更新文档**：`docs/需求/Coze_Bot_System_Prompt_总评分析.md`
   - 确保数据字段说明与新的 input_data 结构一致
   - 确保输出格式要求与新的数据结构匹配

### 阶段六：更新开发规范（已完成）

已在 `docs/standards/llm-development.md` 中添加了方案2的说明。

## 数据完整性要求

确保以下字段都有值：

1. **旺衰数据**：
   - `mingpan_hexin_geju.wangshuai` 不为空

2. **十神数据**：
   - `mingpan_hexin_geju.ten_gods` 不为空（格式：`{'year': {...}, 'month': {...}, 'day': {...}, 'hour': {...}}`）

3. **喜忌数据**：
   - `zhongsheng_tidian.xishen` 不为空
   - `zhongsheng_tidian.jishen` 不为空
   - `zhongsheng_tidian.xishen_wuxing` 不为空
   - `zhongsheng_tidian.jishen_wuxing` 不为空

4. **大运流年**：
   - `guanjian_dayun.current_dayun` 不为空（包含优先级、描述、备注、流年等）
   - `guanjian_dayun.key_dayuns` 不为空（至少9个关键大运）
   - `guanjian_dayun.current_dayun.liunians` 每个大运下最多3个流年

## 约束条件

- ✅ **只修改**：`server/api/v1/general_review_analysis.py`
- ❌ **不修改**：统一接口（`BaziDataOrchestrator`）、底层服务、其他接口、前端接口

## 验证标准

1. **数据完整性**：所有必需字段都有值，无缺失
2. **大运流年格式**：与其他接口一致（优先级、描述、备注等）
3. **数据不重复**：使用引用，节省 Token
4. **输出质量**：与方案1的输出质量一致

## 参考文档

- `docs/需求/优化input_data流年大运结构-子女学习.md` - 子女学习的优化方案
- `docs/需求/优化input_data流年大运结构-感情婚姻.md` - 感情婚姻的优化方案
- `docs/需求/优化input_data流年大运结构-事业财富.md` - 事业财富的优化方案
- `docs/需求/优化input_data流年大运结构-身体健康.md` - 身体健康的优化方案
- `docs/需求/优化input_data流年大运结构需求.md` - 通用需求文档
- `server/utils/dayun_liunian_helper.py` - 工具函数文件
- `server/api/v1/children_study_analysis.py` - 子女学习的实现参考
- `server/api/v1/marriage_analysis.py` - 感情婚姻的实现参考
- `server/api/v1/career_wealth_analysis.py` - 事业财富的实现参考
- `server/api/v1/health_analysis_v2.py` - 身体健康的实现参考


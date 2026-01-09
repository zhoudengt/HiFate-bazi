# 优化 input_data 流年大运结构 - 年运报告

## 需求背景

开发"八字命理-年运报告"功能，针对特定年份（从数据库配置读取，默认2026年）生成完整的年运分析报告。参考"八字命理-身体健康"、"八字命理-感情婚姻"等接口的实现模式，使用方案2（占位符模板），确保大运流年格式与取数规则与其他接口一致。

## 功能概述

年运报告包含5个核心模块：
- **命盘分析**：八字、五行数量、身强弱旺衰、调候喜忌用神
- **人生大事**：身体健康、感情婚姻、事业财富、六亲关系（由大模型基于命盘分析、年运、流年、流月、太岁、闭星等信息综合生成，每个模块1-2句话总结+建议）
- **流月解读**：1-12月逐月分析，结合五运六气、节气，给出影响、风险、养生建议
- **流年太岁**：指定年份太岁介绍、犯太岁属相及影响、化解建议、躲星时间
- **九宫飞星避煞**：指定年份九宫飞星、五黄二黑方位、影响及规避建议、避煞时间按方位

## 优化目标

### 1. 使用方案2（占位符模板）
- ✅ 提示词存储在 Coze Bot 的 System Prompt 中
- ✅ 代码只负责数据提取和格式化
- ✅ 使用数据库配置规则（input_data格式从数据库读取）

### 2. 大运流年格式与其他接口一致
- ✅ 使用 `calculate_user_age` 计算年龄（虚岁，与排盘一致）
- ✅ 使用 `get_current_dayun` 确定当前大运（与排盘一致）
- ✅ 使用 `build_enhanced_dayun_structure` 构建增强的大运流年结构（如需要）
- ✅ 当前大运 + 关键大运（共10个），按优先级排序
- ✅ 每个大运包含：优先级、描述、备注、人生阶段、年龄范围等
- ✅ 每个大运下只保留3个优先级最高的流年

### 3. 数据不重复
- ✅ 使用引用避免重复存储
- ✅ 十神数据只提取一次，其他地方引用
- ✅ 旺衰数据只提取一次，其他地方引用
- ✅ 大运流年数据只提取一次，其他地方引用

### 4. 数据提取完整
- ✅ 修复旺衰数据提取（从 `wangshuai_result.get('data', {})` 提取）
- ✅ 修复十神数据提取（从 `detail_result.details` 或 `bazi_data.details` 提取）
- ✅ 修复喜忌数据提取（从 `wangshuai_data` 提取，包括 `final_xi_ji`）

### 5. 层次化开发
- ✅ 一级接口（路由层）：`server/api/v1/annual_report_analysis.py`
- ✅ 二级接口（业务逻辑层）：`server/services/annual_report_service.py`
- ✅ 三级服务（数据服务层）：太岁服务、风水服务、流月服务

### 6. 数据库配置
- ✅ Bot ID 从数据库读取：`get_config_from_db_only("ANNUAL_REPORT_BOT_ID")`
- ✅ 年份从数据库读取：`get_config_from_db_only("ANNUAL_REPORT_YEAR")`，默认2026
- ✅ input_data 格式从数据库读取：`build_input_data_from_result('annual_report', ...)`

## 实施步骤

### 阶段一：创建需求文档 ✅

创建本文档，说明需求背景、优化目标和实施步骤。

### 阶段二：基础服务开发

1. **开发太岁服务**（`server/services/taisui_service.py`）：
   - `get_taisui_info(year: int)` - 获取指定年份太岁信息
   - `check_fanshaisui(user_zodiac: str, taisui_zodiac: str)` - 判断是否犯太岁
   - `get_resolution_suggestions()` - 获取化解建议（结合命盘八字及属相）
   - `get_duoxing_times(year: int)` - 获取躲星时间

2. **开发风水服务**（`server/services/fengshui_service.py`）：
   - `get_jiugong_feixing(year: int)` - 获取九宫飞星分布
   - `get_wuhuang_erhei(year: int)` - 获取五黄二黑方位
   - `get_bixing_times(year: int, direction: str)` - 获取避煞时间
   - `get_lichun_suggestions(year: int)` - 获取立春建议

3. **扩展流月服务**（`server/services/monthly_fortune_service.py`）：
   - `get_wuyun_liuqi(year: int, month: int)` - 获取五运六气信息
   - `get_jieqi_info(year: int, month: int)` - 获取节气信息（扩展）
   - `analyze_monthly_impact()` - 分析流月影响（扩展）

### 阶段三：数据库配置准备

1. **创建input_data格式配置**：
   - 在数据库 `llm_input_formats` 表中插入格式配置
   - 格式名称：`annual_report`
   - 包含字段：`mingpan_analysis`、`monthly_analysis`、`taisui_info`、`fengshui_info`

2. **创建数据库配置项**：
   - `ANNUAL_REPORT_BOT_ID` - Coze Bot ID
   - `ANNUAL_REPORT_YEAR` - 年运报告年份（默认2026）

### 阶段四：主接口开发

1. **创建二级接口**（`server/services/annual_report_service.py`）：
   - `build_annual_report_input_data()` - 构建输入数据（使用数据库格式配置）
   - `format_input_data_for_coze()` - 格式化数据为JSON字符串
   - `validate_annual_report_input_data()` - 数据完整性验证

2. **创建一级接口**（`server/api/v1/annual_report_analysis.py`）：
   - `annual_report_stream()` - 流式接口路由
   - `annual_report_test()` - 测试接口路由
   - 调用二级接口，不包含业务逻辑

### 阶段五：前端集成

1. **创建前端页面**：`local_frontend/annual-report-analysis.html`
2. **创建前端脚本**：`local_frontend/js/annual-report-analysis.js`
3. **更新侧边栏菜单**：在"命书"栏目下添加"八字命理-年月报告"

### 阶段六：接口注册和路由

1. **注册到gRPC网关**：`server/api/grpc_gateway.py`
2. **更新路由注册**：`server/api/v1/__init__.py`

### 阶段七：数据完整性验证

1. **实现验证函数**：`validate_annual_report_input_data()`
2. **添加错误处理**：数据缺失时的降级方案

### 阶段八：测试和优化

1. **回归测试**：验证现有功能不受影响
2. **单元测试**：测试各个服务函数
3. **集成测试**：测试完整流程
4. **性能优化**：数据获取并行化、缓存优化、Token优化

## 数据完整性要求

确保以下字段都有值：

1. **命盘分析**：
   - `mingpan_analysis.bazi_pillars` - 四柱八字
   - `mingpan_analysis.element_counts` - 五行数量
   - `mingpan_analysis.wangshuai` - 身强弱旺衰
   - `mingpan_analysis.xi_ji` - 调候喜忌用神

2. **流月解读**：
   - `monthly_analysis.months` - 1-12月数据
   - 每个月包含：节气、五运六气、气的流动、影响、风险、养生建议

3. **流年太岁**：
   - `taisui_info.year` - 年份（从数据库配置读取）
   - `taisui_info.taisui_name` - 太岁名称
   - `taisui_info.fanshaisui` - 犯太岁属相及影响
   - `taisui_info.resolution` - 化解建议
   - `taisui_info.duoxing_times` - 躲星时间

4. **九宫飞星避煞**：
   - `fengshui_info.year` - 年份（从数据库配置读取）
   - `fengshui_info.jiugong_feixing` - 九宫飞星分布
   - `fengshui_info.wuhuang` - 五黄星信息
   - `fengshui_info.erhei` - 二黑星信息
   - `fengshui_info.bixing_times` - 避煞时间
   - `fengshui_info.lichun_suggestions` - 立春建议

**注意**：人生大事数据不需要在input_data中提供，由大模型基于提供的基础数据综合生成。

## 约束条件

- ✅ **只修改/新建**：
  - `server/api/v1/annual_report_analysis.py`（新建，一级接口）
  - `server/services/annual_report_service.py`（新建，二级接口）
  - `server/services/taisui_service.py`（新建，三级服务）
  - `server/services/fengshui_service.py`（新建，三级服务）
  - `local_frontend/annual-report-analysis.html`（新建）
  - `local_frontend/js/annual-report-analysis.js`（新建）
- ✅ **扩展**：
  - `server/services/monthly_fortune_service.py`（扩展，添加新方法，不修改现有方法）
- ✅ **修改**：
  - `local_frontend/js/sidebar.js`（仅添加菜单项，不修改现有菜单）
- ❌ **严格禁止修改**：
  - 统一接口（`BaziDataOrchestrator`）
  - 底层服务（`BaziService`、`WangShuaiService`、`BaziDetailService`等）
  - 其他现有接口（`health_analysis_v2.py`、`marriage_analysis.py`等）
  - 其他前端文件（除非需要注册新路由）

## 验证标准

1. **数据完整性**：所有4个模块的数据都有值，无缺失
2. **年份配置**：正确从数据库读取年份配置，默认2026年
3. **输出格式**：严格按照System Prompt要求的5个模块输出（包含人生大事，由大模型生成）
4. **数据不重复**：使用引用，节省Token
5. **流式响应**：正确返回SSE格式
6. **错误处理**：数据缺失时给出友好提示
7. **数据准确性**：不影响现有数据的准确性
8. **功能隔离**：不影响与其无关的功能
9. **前端接口**：不引起对应前端接口报错

## 参考文档

- `docs/需求/优化input_data流年大运结构-身体健康.md` - 身体健康分析的优化方案
- `docs/需求/优化input_data流年大运结构-感情婚姻.md` - 感情婚姻的优化方案
- `docs/需求/优化input_data流年大运结构-事业财富.md` - 事业财富的优化方案
- `server/utils/dayun_liunian_helper.py` - 工具函数文件
- `server/api/v1/health_analysis_v2.py` - 身体健康分析的实现参考
- `server/api/v1/marriage_analysis.py` - 感情婚姻的实现参考
- `server/config/input_format_loader.py` - 数据库格式配置加载器

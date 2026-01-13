# LLM 平台切换配置指南

## 概述

系统支持在 Coze 和百炼（通义千问）两个 LLM 平台之间切换，每个分析接口都可以独立配置使用哪个平台。

## 架构说明

- **统一接口**：所有 LLM 服务都实现 `BaseLLMStreamService` 接口
- **工厂模式**：通过 `LLMServiceFactory` 根据配置自动选择平台
- **配置驱动**：通过数据库 `service_configs` 表配置平台选择
- **向后兼容**：不配置时默认使用 Coze，与现有行为一致

## 配置方式

### 1. 全局配置

设置所有接口的默认平台：

```sql
-- 设置全局默认平台为 Coze（默认值）
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('LLM_PLATFORM', 'coze', 'string', '默认 LLM 平台: coze 或 bailian', 'llm');

-- 或设置为百炼
UPDATE service_configs SET config_value='bailian' WHERE config_key='LLM_PLATFORM';
```

### 2. 场景级配置

为特定接口单独配置平台：

```sql
-- 让感情婚姻接口使用百炼
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '感情婚姻接口使用的 LLM 平台', 'llm');

-- 让事业财富接口使用百炼
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('CAREER_WEALTH_LLM_PLATFORM', 'bailian', 'string', '事业财富接口使用的 LLM 平台', 'llm');
```

**配置优先级**：场景级配置 > 全局配置 > 默认值（coze）

### 3. 支持的场景配置键

| 场景 | 配置键 | 说明 |
|------|--------|------|
| 感情婚姻 | `MARRIAGE_LLM_PLATFORM` | 感情婚姻分析接口 |
| 事业财富 | `CAREER_WEALTH_LLM_PLATFORM` | 事业财富分析接口 |
| 身体健康 | `HEALTH_LLM_PLATFORM` | 身体健康分析接口 |
| 子女学习 | `CHILDREN_STUDY_LLM_PLATFORM` | 子女学习分析接口 |
| 总评分析 | `GENERAL_REVIEW_LLM_PLATFORM` | 总评分析接口 |
| 每日运势 | `DAILY_FORTUNE_LLM_PLATFORM` | 每日运势接口 |
| 五行占比 | `WUXING_PROPORTION_LLM_PLATFORM` | 五行占比分析接口 |
| 喜神忌神 | `XISHEN_JISHEN_LLM_PLATFORM` | 喜神忌神分析接口 |

## 平台配置

### Coze 平台配置

```sql
-- Coze Access Token
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('COZE_ACCESS_TOKEN', 'pat_xxxxxxxxxxxxx', 'string', 'Coze 平台 Access Token', 'coze');

-- Coze 默认 Bot ID
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('COZE_BOT_ID', 'bot_id_xxxxx', 'string', 'Coze 默认 Bot ID', 'coze');

-- 各场景的 Bot ID（可选，不配置则使用默认 Bot ID）
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('MARRIAGE_ANALYSIS_BOT_ID', 'bot_id_xxxxx', 'string', '感情婚姻分析 Bot ID', 'coze');
```

### 百炼平台配置

```sql
-- 百炼 API Key
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES ('BAILIAN_API_KEY', 'sk-xxxxxxxxxxxxx', 'string', '百炼平台 API Key (DashScope)', 'bailian');

-- 各场景的 App ID
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES 
  ('BAILIAN_MARRIAGE_APP_ID', '4bf72d82f83d439cb575856e5bcb8502', 'string', '百炼-感情婚姻 App ID', 'bailian'),
  ('BAILIAN_CAREER_WEALTH_APP_ID', '0f97307f05d041d2b643c967f98f4cbb', 'string', '百炼-事业财富 App ID', 'bailian'),
  ('BAILIAN_HEALTH_APP_ID', '1e9186468bf743a0be8748e0cddd5f44', 'string', '百炼-身体健康 App ID', 'bailian'),
  ('BAILIAN_CHILDREN_STUDY_APP_ID', 'a7d2174380be49508ecb5e014c54fc3a', 'string', '百炼-子女学习 App ID', 'bailian'),
  ('BAILIAN_GENERAL_REVIEW_APP_ID', '75d9a46f55374ea2be1ea28db10c8d03', 'string', '百炼-总评分析 App ID', 'bailian'),
  ('BAILIAN_DAILY_FORTUNE_APP_ID', 'df11520293eb479a985916d977904a8a', 'string', '百炼-每日运势 App ID', 'bailian'),
  ('BAILIAN_WUXING_PROPORTION_APP_ID', 'd326e553a5764d9bac629e87019ac380', 'string', '百炼-五行解析 App ID', 'bailian'),
  ('BAILIAN_XISHEN_JISHEN_APP_ID', 'b9188eacd5bc4e1d8b91bd66ef8671df', 'string', '百炼-喜神忌神 App ID', 'bailian');
```

## 使用示例

### 示例 1：全部使用 Coze（默认）

无需配置，系统默认使用 Coze。

### 示例 2：全部切换到百炼

```sql
-- 1. 设置全局平台为百炼
UPDATE service_configs SET config_value='bailian' WHERE config_key='LLM_PLATFORM';

-- 2. 配置百炼 API Key 和 App IDs（见上方配置）
```

### 示例 3：混合使用（部分接口用百炼，部分用 Coze）

```sql
-- 1. 全局默认使用 Coze
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';

-- 2. 只让感情婚姻和事业财富使用百炼
INSERT INTO service_configs (config_key, config_value, config_type, description, category)
VALUES 
  ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '感情婚姻接口使用百炼', 'llm'),
  ('CAREER_WEALTH_LLM_PLATFORM', 'bailian', 'string', '事业财富接口使用百炼', 'llm');
```

## 热更新

配置修改后立即生效，无需重启服务。系统每次调用时都会从数据库读取最新配置。

## 依赖要求

使用百炼平台需要安装 `dashscope` SDK：

```bash
pip install dashscope
```

## 故障排查

### 1. 检查配置是否正确

```sql
-- 查看全局平台配置
SELECT * FROM service_configs WHERE config_key='LLM_PLATFORM';

-- 查看场景级配置
SELECT * FROM service_configs WHERE config_key LIKE '%_LLM_PLATFORM';

-- 查看百炼配置
SELECT * FROM service_configs WHERE category='bailian';
```

### 2. 检查日志

查看服务日志，确认使用的平台：

```
INFO: 为场景 marriage 选择平台: bailian
INFO: 百炼流式服务初始化完成: scene=marriage
```

### 3. 回滚方案

如果出现问题，可以快速回滚到 Coze：

```sql
-- 回滚全局配置
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';

-- 删除场景级配置（让它们使用全局配置）
DELETE FROM service_configs WHERE config_key LIKE '%_LLM_PLATFORM';
```

## 注意事项

1. **评测脚本兼容性**：`scripts/evaluation/bazi_evaluator.py` 不受影响，它直接使用 `scripts/evaluation/bailian/` 目录下的代码
2. **配置优先级**：场景级配置 > 全局配置 > 默认值（coze）
3. **错误处理**：如果百炼服务创建失败，系统会自动回退到 Coze
4. **性能**：配置从数据库读取，有 5 分钟缓存，支持热更新

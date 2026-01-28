-- ============================================
-- LLM 平台配置同步脚本 - 生产环境
-- ============================================
-- 说明：此脚本将8个接口场景的LLM平台配置同步到生产数据库
-- 使用 INSERT ... ON DUPLICATE KEY UPDATE 确保配置更新而非重复插入
-- ============================================

-- ============================================
-- 1. 感情婚姻 (Marriage)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('MARRIAGE_LLM_PLATFORM', 'coze', 'string', '感情婚姻接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('MARRIAGE_ANALYSIS_BOT_ID', '7587253915310096384', 'string', '感情婚姻分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_MARRIAGE_APP_ID', '4bf72d82f83d439cb575856e5bcb8502', 'string', '百炼-感情婚姻 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 2. 事业财富 (Career Wealth)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('CAREER_WEALTH_LLM_PLATFORM', 'coze', 'string', '事业财富接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('CAREER_WEALTH_BOT_ID', '7587392141568114722', 'string', '事业财富分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_CAREER_WEALTH_APP_ID', '0f97307f05d041d2b643c967f98f4cbb', 'string', '百炼-事业财富 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 3. 身体健康 (Health)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('HEALTH_LLM_PLATFORM', 'coze', 'string', '身体健康接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('HEALTH_ANALYSIS_BOT_ID', '7587390000288120847', 'string', '身体健康分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_HEALTH_APP_ID', '1e9186468bf743a0be8748e0cddd5f44', 'string', '百炼-身体健康 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 4. 子女学习 (Children Study)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('CHILDREN_STUDY_LLM_PLATFORM', 'coze', 'string', '子女学习接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('CHILDREN_STUDY_BOT_ID', '7587388446759665710', 'string', '子女学习分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_CHILDREN_STUDY_APP_ID', 'a7d2174380be49508ecb5e014c54fc3a', 'string', '百炼-子女学习 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 5. 总评分析 (General Review)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('GENERAL_REVIEW_LLM_PLATFORM', 'coze', 'string', '总评分析接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('GENERAL_REVIEW_BOT_ID', '7587605351932297257', 'string', '总评分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_GENERAL_REVIEW_APP_ID', '75d9a46f55374ea2be1ea28db10c8d03', 'string', '百炼-总评分析 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 5.5. 年运报告 (Annual Report)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('ANNUAL_REPORT_LLM_PLATFORM', 'bailian', 'string', '年运报告接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('ANNUAL_REPORT_BOT_ID', '7593296393016508450', 'string', '年运报告 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_ANNUAL_REPORT_APP_ID', 'a2a45b93d4c04ee1b363bdaa8cd26d35', 'string', '百炼-年运报告 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 6. 每日运势 (Daily Fortune)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('DAILY_FORTUNE_LLM_PLATFORM', 'coze', 'string', '每日运势接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('DAILY_FORTUNE_ACTION_BOT_ID', '7584766797639958555', 'string', '每日运势行动建议 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_DAILY_FORTUNE_APP_ID', 'df11520293eb479a985916d977904a8a', 'string', '百炼-每日运势 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 7. 五行占比 (Wuxing Proportion)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('WUXING_PROPORTION_LLM_PLATFORM', 'coze', 'string', '五行占比接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('WUXING_PROPORTION_BOT_ID', '', 'string', '五行占比分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_WUXING_PROPORTION_APP_ID', 'd326e553a5764d9bac629e87019ac380', 'string', '百炼-五行解析 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 8. 喜神忌神 (Xishen Jishen)
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('XISHEN_JISHEN_LLM_PLATFORM', 'coze', 'string', '喜神忌神接口使用的 LLM 平台: coze 或 bailian', 'llm', 1, 'production'),
  ('XISHEN_JISHEN_BOT_ID', '7585861629750181926', 'string', '喜神忌神分析 Coze Bot ID', 'coze', 1, 'production'),
  ('BAILIAN_XISHEN_JISHEN_APP_ID', 'b9188eacd5bc4e1d8b91bd66ef8671df', 'string', '百炼-喜神忌神 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
  config_value = VALUES(config_value),
  description = VALUES(description),
  updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 验证配置
-- ============================================
-- 执行以下查询验证配置是否正确写入

-- SELECT config_key, config_value, description, category 
-- FROM service_configs 
-- WHERE config_key IN (
--   'MARRIAGE_LLM_PLATFORM', 'MARRIAGE_ANALYSIS_BOT_ID', 'BAILIAN_MARRIAGE_APP_ID',
--   'CAREER_WEALTH_LLM_PLATFORM', 'CAREER_WEALTH_BOT_ID', 'BAILIAN_CAREER_WEALTH_APP_ID',
--   'HEALTH_LLM_PLATFORM', 'HEALTH_ANALYSIS_BOT_ID', 'BAILIAN_HEALTH_APP_ID',
--   'CHILDREN_STUDY_LLM_PLATFORM', 'CHILDREN_STUDY_BOT_ID', 'BAILIAN_CHILDREN_STUDY_APP_ID',
--   'GENERAL_REVIEW_LLM_PLATFORM', 'GENERAL_REVIEW_BOT_ID', 'BAILIAN_GENERAL_REVIEW_APP_ID',
--   'DAILY_FORTUNE_LLM_PLATFORM', 'DAILY_FORTUNE_ACTION_BOT_ID', 'BAILIAN_DAILY_FORTUNE_APP_ID',
--   'WUXING_PROPORTION_LLM_PLATFORM', 'WUXING_PROPORTION_BOT_ID', 'BAILIAN_WUXING_PROPORTION_APP_ID',
--   'XISHEN_JISHEN_LLM_PLATFORM', 'XISHEN_JISHEN_BOT_ID', 'BAILIAN_XISHEN_JISHEN_APP_ID'
-- )
-- ORDER BY config_key;

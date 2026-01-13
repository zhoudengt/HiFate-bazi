-- ============================================
-- LLM 平台切换配置 SQL 脚本
-- ============================================
-- 说明：此脚本用于配置 LLM 平台切换功能
-- 执行前请根据实际情况修改配置值
-- ============================================

-- ============================================
-- 1. 全局 LLM 平台配置
-- ============================================
-- 设置默认平台为 Coze（默认值，可不配置）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('LLM_PLATFORM', 'coze', 'string', '默认 LLM 平台: coze 或 bailian', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 2. Coze 平台配置
-- ============================================
-- Coze Access Token（必需）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('COZE_ACCESS_TOKEN', 'pat_xxxxxxxxxxxxx', 'string', 'Coze 平台 Access Token', 'coze', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;

-- Coze 默认 Bot ID（必需）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('COZE_BOT_ID', 'bot_id_xxxxx', 'string', 'Coze 默认 Bot ID', 'coze', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;

-- 各场景的 Bot ID（可选，不配置则使用默认 Bot ID）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('MARRIAGE_ANALYSIS_BOT_ID', 'bot_id_xxxxx', 'string', '感情婚姻分析 Bot ID', 'coze', 1, 'production'),
  ('CAREER_WEALTH_BOT_ID', 'bot_id_xxxxx', 'string', '事业财富分析 Bot ID', 'coze', 1, 'production'),
  ('HEALTH_ANALYSIS_BOT_ID', 'bot_id_xxxxx', 'string', '身体健康分析 Bot ID', 'coze', 1, 'production'),
  ('CHILDREN_STUDY_BOT_ID', 'bot_id_xxxxx', 'string', '子女学习分析 Bot ID', 'coze', 1, 'production'),
  ('GENERAL_REVIEW_BOT_ID', 'bot_id_xxxxx', 'string', '总评分析 Bot ID', 'coze', 1, 'production'),
  ('DAILY_FORTUNE_ACTION_BOT_ID', 'bot_id_xxxxx', 'string', '每日运势行动建议 Bot ID', 'coze', 1, 'production'),
  ('WUXING_PROPORTION_BOT_ID', 'bot_id_xxxxx', 'string', '五行占比分析 Bot ID', 'coze', 1, 'production'),
  ('XISHEN_JISHEN_BOT_ID', 'bot_id_xxxxx', 'string', '喜神忌神分析 Bot ID', 'coze', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 3. 百炼平台配置
-- ============================================
-- 百炼 API Key（必需，如果使用百炼平台）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('BAILIAN_API_KEY', 'sk-xxxxxxxxxxxxx', 'string', '百炼平台 API Key (DashScope)', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;

-- 百炼各场景 App ID（必需，如果使用百炼平台）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('BAILIAN_MARRIAGE_APP_ID', '4bf72d82f83d439cb575856e5bcb8502', 'string', '百炼-感情婚姻 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_CAREER_WEALTH_APP_ID', '0f97307f05d041d2b643c967f98f4cbb', 'string', '百炼-事业财富 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_HEALTH_APP_ID', '1e9186468bf743a0be8748e0cddd5f44', 'string', '百炼-身体健康 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_CHILDREN_STUDY_APP_ID', 'a7d2174380be49508ecb5e014c54fc3a', 'string', '百炼-子女学习 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_GENERAL_REVIEW_APP_ID', '75d9a46f55374ea2be1ea28db10c8d03', 'string', '百炼-总评分析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_DAILY_FORTUNE_APP_ID', 'df11520293eb479a985916d977904a8a', 'string', '百炼-每日运势 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_WUXING_PROPORTION_APP_ID', 'd326e553a5764d9bac629e87019ac380', 'string', '百炼-五行解析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_XISHEN_JISHEN_APP_ID', 'b9188eacd5bc4e1d8b91bd66ef8671df', 'string', '百炼-喜神忌神 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 4. 场景级平台配置（可选）
-- ============================================
-- 如果不需要场景级配置，可以跳过此部分
-- 场景级配置优先级高于全局配置

-- 示例：让感情婚姻接口使用百炼
-- INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
-- VALUES ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '感情婚姻接口使用的 LLM 平台', 'llm', 1, 'production')
-- ON DUPLICATE KEY UPDATE 
--     config_value = VALUES(config_value),
--     updated_at = CURRENT_TIMESTAMP;

-- 示例：让事业财富接口使用百炼
-- INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
-- VALUES ('CAREER_WEALTH_LLM_PLATFORM', 'bailian', 'string', '事业财富接口使用的 LLM 平台', 'llm', 1, 'production')
-- ON DUPLICATE KEY UPDATE 
--     config_value = VALUES(config_value),
--     updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 5. 验证配置
-- ============================================
-- 执行以下 SQL 验证配置是否正确

-- 查看全局平台配置
-- SELECT config_key, config_value, description FROM service_configs WHERE config_key='LLM_PLATFORM';

-- 查看场景级平台配置
-- SELECT config_key, config_value, description FROM service_configs WHERE config_key LIKE '%_LLM_PLATFORM';

-- 查看 Coze 配置
-- SELECT config_key, config_value FROM service_configs WHERE category='coze' ORDER BY config_key;

-- 查看百炼配置
-- SELECT config_key, config_value FROM service_configs WHERE category='bailian' ORDER BY config_key;

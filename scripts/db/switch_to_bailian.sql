-- ============================================
-- 流式接口切换到百炼平台 - SQL 脚本
-- ============================================
-- 说明：执行此脚本后，所有流式接口将使用百炼平台
-- 只需修改配置表，无需修改代码
-- ============================================

-- ============================================
-- 1. 设置全局平台为百炼（一次性切换所有接口）
-- ============================================
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('LLM_PLATFORM', 'bailian', 'string', '默认 LLM 平台: coze 或 bailian', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = 'bailian',
    description = '默认 LLM 平台: coze 或 bailian',
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 2. 配置百炼 API Key（必需）
-- ============================================
-- ⚠️ 注意：这里使用的是 config.py 中的默认值，请根据实际情况修改
-- 如果已有配置，此语句不会覆盖现有值（使用 ON DUPLICATE KEY UPDATE）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('BAILIAN_API_KEY', 'sk-91ad3ec784b64fe78c4015827dfd982d', 'string', '百炼平台 API Key (DashScope)', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
    -- 如果已存在，不更新值，只更新描述和时间戳
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 3. 配置各场景的 App ID（可选，如果不配置会使用默认值）
-- ============================================
-- 注意：配置键命名规则：BAILIAN_{SCENE.upper()}_APP_ID
-- 例如：face_analysis -> BAILIAN_FACE_ANALYSIS_APP_ID

INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  -- 基础分析
  ('BAILIAN_WUXING_PROPORTION_APP_ID', 'd326e553a5764d9bac629e87019ac380', 'string', '百炼-五行解析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_XISHEN_JISHEN_APP_ID', 'b9188eacd5bc4e1d8b91bd66ef8671df', 'string', '百炼-喜神忌神 App ID', 'bailian', 1, 'production'),
  
  -- 专项分析
  ('BAILIAN_MARRIAGE_APP_ID', '4bf72d82f83d439cb575856e5bcb8502', 'string', '百炼-感情婚姻 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_CAREER_WEALTH_APP_ID', '0f97307f05d041d2b643c967f98f4cbb', 'string', '百炼-事业财富 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_HEALTH_APP_ID', '1e9186468bf743a0be8748e0cddd5f44', 'string', '百炼-身体健康 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_CHILDREN_STUDY_APP_ID', 'a7d2174380be49508ecb5e014c54fc3a', 'string', '百炼-子女学习 App ID', 'bailian', 1, 'production'),
  
  -- 综合分析
  ('BAILIAN_GENERAL_REVIEW_APP_ID', '75d9a46f55374ea2be1ea28db10c8d03', 'string', '百炼-总评分析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_DAILY_FORTUNE_APP_ID', 'df11520293eb479a985916d977904a8a', 'string', '百炼-每日运势 App ID', 'bailian', 1, 'production'),
  
  -- 面相和风水
  ('BAILIAN_FACE_ANALYSIS_APP_ID', '23f6ddd0ed1c4fb2aba2a21f238f1820', 'string', '百炼-面相分析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_DESK_FENGSHUI_APP_ID', '0a8d1685044d44a78628e427c98c901c', 'string', '百炼-办公桌风水 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 4. 场景级平台配置（可选，用于单独控制某个场景）
-- ============================================
-- 如果某个场景想单独使用 Coze，可以设置场景级配置
-- 例如：让感情婚姻接口使用 Coze，其他用百炼
-- INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
-- VALUES ('MARRIAGE_LLM_PLATFORM', 'coze', 'string', '感情婚姻接口使用的 LLM 平台', 'llm', 1, 'production')
-- ON DUPLICATE KEY UPDATE 
--     config_value = 'coze',
--     updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 5. 验证配置
-- ============================================
-- 执行以下 SQL 验证配置是否正确

-- 查看全局平台配置
SELECT config_key, config_value, description 
FROM service_configs 
WHERE config_key = 'LLM_PLATFORM';

-- 查看场景级平台配置
SELECT config_key, config_value, description 
FROM service_configs 
WHERE config_key LIKE '%_LLM_PLATFORM'
ORDER BY config_key;

-- 查看百炼 API Key
SELECT config_key, LEFT(config_value, 10) as api_key_prefix, description 
FROM service_configs 
WHERE config_key = 'BAILIAN_API_KEY';

-- 查看百炼各场景 App ID 配置
SELECT config_key, config_value, description 
FROM service_configs 
WHERE config_key LIKE 'BAILIAN_%_APP_ID'
ORDER BY config_key;

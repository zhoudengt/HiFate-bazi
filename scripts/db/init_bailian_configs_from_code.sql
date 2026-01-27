-- ============================================
-- 将代码中的百炼配置写入数据库
-- ============================================
-- 说明：此脚本将原来 SCENE_CONFIG_MAP 和 config.py 中的配置写入数据库
-- 执行后，所有百炼配置都从数据库读取，不再依赖代码中的硬编码
-- ============================================

-- ============================================
-- 1. 百炼 API Key（从 config.py 的默认值）
-- ============================================
-- ⚠️ 注意：这里使用的是 config.py 中的默认值，请根据实际情况修改
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('BAILIAN_API_KEY', 'sk-91ad3ec784b64fe78c4015827dfd982d', 'string', '百炼平台 API Key (DashScope)', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 2. 百炼各场景 App ID（从 SCENE_CONFIG_MAP 和 BAILIAN_APP_IDS）
-- ============================================
-- 这些是原来代码中硬编码的配置，现在写入数据库
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  -- 基础分析（从 BAILIAN_APP_IDS）
  ('BAILIAN_WUXING_PROPORTION_APP_ID', 'd326e553a5764d9bac629e87019ac380', 'string', '百炼-五行解析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_XISHEN_JISHEN_APP_ID', 'b9188eacd5bc4e1d8b91bd66ef8671df', 'string', '百炼-喜神忌神 App ID', 'bailian', 1, 'production'),
  
  -- 专项分析（从 SCENE_CONFIG_MAP 和 BAILIAN_APP_IDS）
  ('BAILIAN_MARRIAGE_APP_ID', '4bf72d82f83d439cb575856e5bcb8502', 'string', '百炼-感情婚姻 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_CAREER_WEALTH_APP_ID', '0f97307f05d041d2b643c967f98f4cbb', 'string', '百炼-事业财富 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_HEALTH_APP_ID', '1e9186468bf743a0be8748e0cddd5f44', 'string', '百炼-身体健康 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_CHILDREN_STUDY_APP_ID', 'a7d2174380be49508ecb5e014c54fc3a', 'string', '百炼-子女学习 App ID', 'bailian', 1, 'production'),
  
  -- 综合分析（从 SCENE_CONFIG_MAP 和 BAILIAN_APP_IDS）
  ('BAILIAN_GENERAL_REVIEW_APP_ID', '75d9a46f55374ea2be1ea28db10c8d03', 'string', '百炼-总评分析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_DAILY_FORTUNE_APP_ID', 'df11520293eb479a985916d977904a8a', 'string', '百炼-每日运势 App ID', 'bailian', 1, 'production'),
  
  -- 面相和风水（已有配置，这里确保写入）
  ('BAILIAN_FACE_ANALYSIS_APP_ID', '23f6ddd0ed1c4fb2aba2a21f238f1820', 'string', '百炼-面相分析 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_DESK_FENGSHUI_APP_ID', '0a8d1685044d44a78628e427c98c901c', 'string', '百炼-办公桌风水 App ID', 'bailian', 1, 'production'),
  
  -- QA 问答（从 BAILIAN_APP_IDS，虽然不是流式接口，但也写入以备后用）
  ('BAILIAN_QA_QUESTION_GENERATE_APP_ID', '835867a183cd4a0db861c61f632bbaa6', 'string', '百炼-QA问题生成 App ID', 'bailian', 1, 'production'),
  ('BAILIAN_QA_ANALYSIS_APP_ID', 'b9188eacd5bc4e1d8b91bd66ef8671df', 'string', '百炼-QA命理分析 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 3. 验证配置
-- ============================================
SELECT 
    '配置写入完成' as status,
    COUNT(*) as total_configs,
    COUNT(CASE WHEN config_key = 'BAILIAN_API_KEY' THEN 1 END) as has_api_key,
    COUNT(CASE WHEN config_key LIKE 'BAILIAN_%_APP_ID' THEN 1 END) as app_id_count
FROM service_configs
WHERE config_key = 'BAILIAN_API_KEY' 
   OR config_key LIKE 'BAILIAN_%_APP_ID';

-- 显示所有百炼配置
SELECT 
    config_key,
    LEFT(config_value, 20) as config_value_preview,
    description
FROM service_configs
WHERE config_key = 'BAILIAN_API_KEY' 
   OR config_key LIKE 'BAILIAN_%_APP_ID'
ORDER BY config_key;

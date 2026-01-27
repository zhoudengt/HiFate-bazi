-- ============================================
-- 快速更新 LLM_PLATFORM 为百炼
-- ============================================
-- 说明：执行此脚本后，所有流式接口将使用百炼平台
-- ============================================

USE hifate_bazi;

-- 设置全局平台为百炼（一次性切换所有接口）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('LLM_PLATFORM', 'bailian', 'string', '默认 LLM 平台: coze 或 bailian', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE 
    config_value = 'bailian',
    description = '默认 LLM 平台: coze 或 bailian',
    updated_at = CURRENT_TIMESTAMP;

-- 验证配置
SELECT config_key, config_value, description, updated_at
FROM service_configs
WHERE config_key = 'LLM_PLATFORM';

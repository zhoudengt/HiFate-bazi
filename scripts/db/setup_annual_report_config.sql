-- 年运报告功能数据库配置脚本
-- 支持 Coze 和百炼双平台切换

-- 1. 配置平台选择（bailian 或 coze）
INSERT INTO service_configs (config_key, config_value, description, config_type, category, is_active, created_at, updated_at)
VALUES ('ANNUAL_REPORT_LLM_PLATFORM', 'bailian', '年运报告使用的 LLM 平台: coze 或 bailian', 'string', 'llm', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = 'bailian',
    description = '年运报告使用的 LLM 平台: coze 或 bailian',
    updated_at = NOW();

-- 2. 配置百炼 App ID
INSERT INTO service_configs (config_key, config_value, description, config_type, category, is_active, created_at, updated_at)
VALUES ('BAILIAN_ANNUAL_REPORT_APP_ID', 'a2a45b93d4c04ee1b363bdaa8cd26d35', '年运报告百炼 App ID', 'string', 'bailian', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = 'a2a45b93d4c04ee1b363bdaa8cd26d35',
    description = '年运报告百炼 App ID',
    updated_at = NOW();

-- 3. 配置Coze Bot ID（可选，仅当使用 Coze 平台时需要）
INSERT INTO service_configs (config_key, config_value, description, is_active, created_at, updated_at)
VALUES ('ANNUAL_REPORT_BOT_ID', '7593296393016508450', '年运报告Coze Bot ID', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = '7593296393016508450',
    description = '年运报告Coze Bot ID',
    updated_at = NOW();

-- 4. 配置年份
INSERT INTO service_configs (config_key, config_value, description, is_active, created_at, updated_at)
VALUES ('ANNUAL_REPORT_YEAR', '2026', '年运报告年份', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = '2026',
    description = '年运报告年份',
    updated_at = NOW();

-- 5. 验证配置
SELECT config_key, config_value, description, is_active 
FROM service_configs 
WHERE config_key IN ('ANNUAL_REPORT_LLM_PLATFORM', 'BAILIAN_ANNUAL_REPORT_APP_ID', 'ANNUAL_REPORT_BOT_ID', 'ANNUAL_REPORT_YEAR')
ORDER BY config_key;

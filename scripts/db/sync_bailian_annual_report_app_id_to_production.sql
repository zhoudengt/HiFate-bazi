-- 仅同步 BAILIAN_ANNUAL_REPORT_APP_ID 到生产 service_configs
-- 执行方式见脚本内注释

INSERT INTO service_configs (config_key, config_value, description, config_type, category, is_active, created_at, updated_at)
VALUES ('BAILIAN_ANNUAL_REPORT_APP_ID', 'a2a45b93d4c04ee1b363bdaa8cd26d35', '年运报告百炼 App ID', 'string', 'bailian', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE
    config_value = 'a2a45b93d4c04ee1b363bdaa8cd26d35',
    description = '年运报告百炼 App ID',
    updated_at = NOW();

SELECT config_key, config_value, is_active FROM service_configs WHERE config_key = 'BAILIAN_ANNUAL_REPORT_APP_ID';

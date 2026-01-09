-- 年运报告功能数据库配置脚本
-- 执行前请确保已创建Coze Bot并获取Bot ID

-- 1. 配置Bot ID
INSERT INTO service_configs (config_key, config_value, description, is_active, created_at, updated_at)
VALUES ('ANNUAL_REPORT_BOT_ID', '7593296393016508450', '年运报告Coze Bot ID', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = '7593296393016508450',
    description = '年运报告Coze Bot ID',
    updated_at = NOW();

-- 2. 配置年份
INSERT INTO service_configs (config_key, config_value, description, is_active, created_at, updated_at)
VALUES ('ANNUAL_REPORT_YEAR', '2026', '年运报告年份', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = '2026',
    description = '年运报告年份',
    updated_at = NOW();

-- 3. 验证配置
SELECT config_key, config_value, description, is_active 
FROM service_configs 
WHERE config_key IN ('ANNUAL_REPORT_BOT_ID', 'ANNUAL_REPORT_YEAR');

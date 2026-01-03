-- 添加或更新每日运势行动建议 Bot ID 配置
-- Bot ID: 7584766797639958555

-- 使用 INSERT ... ON DUPLICATE KEY UPDATE 确保配置存在且为最新值
INSERT INTO `service_configs` (
    `config_key`,
    `config_value`,
    `config_type`,
    `category`,
    `description`,
    `environment`,
    `version`,
    `is_active`,
    `created_at`,
    `updated_at`
) VALUES (
    'DAILY_FORTUNE_ACTION_BOT_ID',
    '7584766797639958555',
    'string',
    'coze',
    '每日运势行动建议 Coze Bot ID',
    'production',
    1,
    1,
    NOW(),
    NOW()
)
ON DUPLICATE KEY UPDATE
    `config_value` = '7584766797639958555',
    `config_type` = 'string',
    `category` = 'coze',
    `description` = '每日运势行动建议 Coze Bot ID',
    `updated_at` = NOW(),
    `is_active` = 1;

-- 验证配置
SELECT 
    config_key,
    config_value,
    category,
    is_active,
    updated_at
FROM service_configs
WHERE config_key = 'DAILY_FORTUNE_ACTION_BOT_ID';


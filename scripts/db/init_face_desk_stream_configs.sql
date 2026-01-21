-- 面相分析和办公桌风水流式接口数据库配置
-- 执行此脚本以添加流式接口所需的配置项

-- 面相分析配置
INSERT INTO service_configs (config_key, config_value, description, created_at, updated_at) 
VALUES 
('FACE_ANALYSIS_BOT_ID', '7597406985550282787', '面相分析 Bot ID（用于日志记录）', NOW(), NOW()),
('FACE_ANALYSIS_LLM_PLATFORM', 'bailian', '面相分析使用的LLM平台（bailian/coze）', NOW(), NOW()),
('BAILIAN_FACE_ANALYSIS_APP_ID', '23f6ddd0ed1c4fb2aba2a21f238f1820', '面相分析百炼应用ID', NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = NOW();

-- 办公桌风水配置
INSERT INTO service_configs (config_key, config_value, description, created_at, updated_at) 
VALUES 
('DESK_FENGSHUI_BOT_ID', '7597409425955127336', '办公桌风水 Bot ID（用于日志记录）', NOW(), NOW()),
('DESK_FENGSHUI_LLM_PLATFORM', 'bailian', '办公桌风水使用的LLM平台（bailian/coze）', NOW(), NOW()),
('BAILIAN_DESK_FENGSHUI_APP_ID', '0a8d1685044d44a78628e427c98c901c', '办公桌风水百炼应用ID', NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = NOW();

-- 验证配置
SELECT config_key, config_value, description 
FROM service_configs 
WHERE config_key IN (
    'FACE_ANALYSIS_BOT_ID',
    'FACE_ANALYSIS_LLM_PLATFORM',
    'BAILIAN_FACE_ANALYSIS_APP_ID',
    'DESK_FENGSHUI_BOT_ID',
    'DESK_FENGSHUI_LLM_PLATFORM',
    'BAILIAN_DESK_FENGSHUI_APP_ID'
)
ORDER BY config_key;

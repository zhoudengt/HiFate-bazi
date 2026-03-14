-- 居家风水百炼智能体配置
-- 执行前请确认数据库名称正确

-- 插入/更新百炼智能体 App ID 配置
INSERT INTO `service_configs`
(`config_key`, `config_value`, `config_type`, `description`, `category`, `environment`, `version`, `is_active`)
VALUES
(
  'BAILIAN_HOME_FENGSHUI_VISION_APP_ID',
  '626cf5733b6b493e8e31ff9f6081a24f',
  'string',
  '居家风水视觉识别智能体 App ID（Qwen-VL-Plus，识别室内家具位置状态）',
  'bailian',
  'production',
  1,
  1
),
(
  'BAILIAN_HOME_FENGSHUI_REPORT_APP_ID',
  '2e12b83424eb4013a987c0c51d135092',
  'string',
  '居家风水报告生成智能体 App ID（百炼长文本模型，生成个性化风水分析报告）',
  'bailian',
  'production',
  1,
  1
)
ON DUPLICATE KEY UPDATE
  `config_value` = VALUES(`config_value`),
  `description` = VALUES(`description`),
  `updated_at` = CURRENT_TIMESTAMP;

-- 验证插入结果
SELECT config_key, config_value, description, is_active
FROM service_configs
WHERE config_key IN (
  'BAILIAN_HOME_FENGSHUI_VISION_APP_ID',
  'BAILIAN_HOME_FENGSHUI_REPORT_APP_ID'
);

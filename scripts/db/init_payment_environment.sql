-- ========================================
-- 统一支付环境配置初始化脚本
-- ========================================
-- 创建时间: 2026-01-20
-- 说明: 初始化统一支付环境配置，所有支付方式共享此配置

USE `hifate_bazi`;

-- ========================================
-- 插入统一支付环境配置
-- ========================================
-- 配置说明：
--   - provider: 'shared' (共享配置)
--   - config_key: 'payment_environment' (支付环境)
--   - config_value: 'production' | 'sandbox' | 'test' (环境值)
--   - environment: 'production' (配置本身的环境，固定为production)
--   - description: 配置描述

INSERT INTO payment_configs 
(provider, config_key, config_value, config_type, environment, description, is_active)
VALUES 
('shared', 'payment_environment', 'production', 'string', 'production', '统一支付环境配置（production/sandbox/test），所有支付方式共享此配置', 1)
ON DUPLICATE KEY UPDATE
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

-- ========================================
-- 验证配置
-- ========================================
SELECT 
    provider,
    config_key,
    config_value,
    environment,
    description,
    is_active,
    created_at,
    updated_at
FROM payment_configs
WHERE provider = 'shared' 
  AND config_key = 'payment_environment'
  AND environment = 'production';

-- ========================================
-- 使用说明
-- ========================================
-- 1. 查看当前环境：
--    SELECT config_value FROM payment_configs 
--    WHERE provider='shared' AND config_key='payment_environment';
--
-- 2. 切换到测试环境：
--    UPDATE payment_configs 
--    SET config_value='sandbox', updated_at=CURRENT_TIMESTAMP
--    WHERE provider='shared' AND config_key='payment_environment';
--
-- 3. 切换到生产环境：
--    UPDATE payment_configs 
--    SET config_value='production', updated_at=CURRENT_TIMESTAMP
--    WHERE provider='shared' AND config_key='payment_environment';
--
-- 4. 切换后需要清除缓存（通过热更新或重启服务）

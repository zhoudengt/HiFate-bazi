-- ========================================
-- 数据库同步脚本 - 新增表结构
-- 创建时间: 2026-01-21
-- 说明: 同步首页内容表和支付配置表
-- ========================================


-- ========================================
-- 来源: server/db/migrations/create_homepage_contents_table.sql
-- ========================================
-- ========================================
-- 首页内容表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-XX
-- 说明: 存储网站首页的图片与文字内容，支持排序和管理

USE `hifate_bazi`;

-- ========================================
-- 首页内容表
-- ========================================
CREATE TABLE IF NOT EXISTS `homepage_contents` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `title` VARCHAR(200) NOT NULL COMMENT '标题（如：AI守护神、八字命理等）',
    `tags` JSON COMMENT '标签列表（JSON数组，如：["科技", "精准"]）',
    `description` TEXT COMMENT '详细描述',
    `image_base64` LONGTEXT COMMENT '图片Base64编码（包含data:image前缀）',
    `sort_order` INT DEFAULT 0 COMMENT '排序字段（数字越小越靠前）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_sort_order` (`sort_order`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_enabled_sort` (`enabled`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='首页内容表';

-- ========================================
-- 表结构说明
-- ========================================
-- title: 内容标题，如"AI守护神"、"八字命理"等
-- tags: JSON数组格式的标签，如["科技", "精准"]、["古籍", "专业"]等
-- description: 详细描述文本，支持长文本
-- image_base64: 图片的Base64编码，包含完整的前缀（如：data:image/jpeg;base64,...）
-- sort_order: 排序字段，数字越小越靠前，用于控制显示顺序
-- enabled: 是否启用，软删除时设置为FALSE



-- ========================================
-- 来源: server/db/migrations/create_payment_configs_table.sql
-- ========================================
-- ========================================
-- 支付配置表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-02
-- 说明: 专门用于存储支付相关配置，支持多支付渠道、多环境、多商户

USE `hifate_bazi`;

-- ========================================
-- 支付配置表
-- ========================================
CREATE TABLE IF NOT EXISTS `payment_configs` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    `provider` VARCHAR(50) NOT NULL COMMENT '支付渠道：stripe/paypal/alipay/wechat/linepay/newebpay/shared',
    `config_key` VARCHAR(100) NOT NULL COMMENT '配置键（如：secret_key, client_id等）',
    `config_value` TEXT COMMENT '配置值（敏感信息建议加密存储）',
    `config_type` VARCHAR(20) DEFAULT 'string' COMMENT '配置类型：string/int/bool/json',
    `environment` VARCHAR(20) DEFAULT 'production' COMMENT '环境：production/sandbox/test',
    `merchant_id` VARCHAR(100) COMMENT '商户ID（可选，支持多商户，默认为NULL表示默认商户）',
    `description` TEXT COMMENT '配置描述',
    `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
    `is_encrypted` BOOLEAN DEFAULT 0 COMMENT '是否加密存储（预留字段，用于将来加密敏感信息）',
    `version` INT DEFAULT 1 COMMENT '版本号',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_provider_key_env_merchant` (`provider`, `config_key`, `environment`, `merchant_id`),
    INDEX `idx_provider` (`provider`),
    INDEX `idx_environment` (`environment`),
    INDEX `idx_active` (`is_active`),
    INDEX `idx_provider_env` (`provider`, `environment`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付配置表';

-- ========================================
-- 配置说明
-- ========================================
-- provider 支持的支付渠道：
--   - stripe: Stripe支付
--   - paypal: PayPal支付
--   - alipay: 支付宝国际版
--   - wechat: 微信支付
--   - linepay: Line Pay支付
--   - newebpay: 蓝新金流支付
--   - shared: 共享配置（如前端URL、API URL等）
--
-- environment 支持的环境：
--   - production: 生产环境
--   - sandbox: 沙箱/测试环境（Stripe, PayPal, Line Pay）
--   - test: 测试环境（NewebPay）
--
-- config_key 配置键示例：
--   Stripe: secret_key, public_key
--   PayPal: client_id, client_secret, mode
--   Alipay: app_id, private_key_path, public_key_path, gateway
--   WeChat: app_id, mch_id, api_key, cert_path, key_path
--   Line Pay: channel_id, channel_secret, mode, sandbox_url, production_url
--   NewebPay: merchant_id, hash_key, hash_iv, mode, test_url, production_url
--   Shared: frontend_base_url, api_base_url



-- ========================================
-- 来源: scripts/db/init_payment_environment.sql
-- ========================================
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



-- ========================================
-- 来源: scripts/db/init_face_desk_stream_configs.sql
-- ========================================
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



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
    `provider` VARCHAR(50) NOT NULL COMMENT '支付渠道：stripe/paypal/payssion/payermax/alipay/wechat/linepay/newebpay/shared',
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
--   - stripe: Stripe支付（全球信用卡）
--   - paypal: PayPal支付（全球电子钱包）
--   - payssion: Payssion支付聚合（LINE Pay 中转，香港公司适用）
--   - payermax: PayerMax支付聚合（全球600+支付方式）
--   - alipay: 支付宝国际版（中国用户）
--   - wechat: 微信支付（中国用户）
--   - linepay: Line Pay直接集成（台湾、日本、泰国）
--   - newebpay: 蓝新金流支付（台湾本地）
--   - shared: 共享配置（如前端URL、API URL等）
--
-- environment 支持的环境：
--   - production: 生产环境
--   - sandbox: 沙箱/测试环境（Stripe, PayPal, Line Pay, Payssion）
--   - test: 测试环境（PayerMax, NewebPay）
--
-- config_key 配置键示例：
--   Stripe: secret_key, public_key
--   PayPal: client_id, client_secret, mode
--   Payssion: api_key, secret, merchant_id
--   PayerMax: app_id, merchant_no, private_key_path, public_key_path
--   Alipay: app_id, private_key_path, public_key_path, gateway
--   WeChat: app_id, mch_id, api_key, cert_path, key_path
--   Line Pay: channel_id, channel_secret, mode, sandbox_url, production_url
--   NewebPay: merchant_id, hash_key, hash_iv, mode, test_url, production_url
--   Shared: frontend_base_url, api_base_url

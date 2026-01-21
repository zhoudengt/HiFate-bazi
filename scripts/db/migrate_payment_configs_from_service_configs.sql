-- ========================================
-- 支付配置迁移脚本
-- ========================================
-- 说明: 从 service_configs 表迁移支付配置到 payment_configs 表
-- 执行前请确保已创建 payment_configs 表

USE `hifate_bazi`;

-- ========================================
-- 配置键映射规则
-- ========================================
-- service_configs.config_key -> payment_configs (provider, config_key)
-- 
-- Stripe:
--   STRIPE_SECRET_KEY -> (stripe, secret_key)
--
-- PayPal:
--   PAYPAL_CLIENT_ID -> (paypal, client_id)
--   PAYPAL_CLIENT_SECRET -> (paypal, client_secret)
--   PAYPAL_MODE -> (paypal, mode)
--
-- Alipay:
--   ALIPAY_APP_ID -> (alipay, app_id)
--   ALIPAY_PRIVATE_KEY_PATH -> (alipay, private_key_path)
--   ALIPAY_PUBLIC_KEY_PATH -> (alipay, public_key_path)
--   ALIPAY_GATEWAY -> (alipay, gateway)
--
-- WeChat:
--   WECHAT_APP_ID -> (wechat, app_id)
--   WECHAT_MCH_ID -> (wechat, mch_id)
--   WECHAT_API_KEY -> (wechat, api_key)
--   WECHAT_CERT_PATH -> (wechat, cert_path)
--   WECHAT_KEY_PATH -> (wechat, key_path)
--
-- Line Pay:
--   LINEPAY_CHANNEL_ID -> (linepay, channel_id)
--   LINEPAY_CHANNEL_SECRET -> (linepay, channel_secret)
--   LINEPAY_MODE -> (linepay, mode)
--   LINEPAY_SANDBOX_URL -> (linepay, sandbox_url)
--   LINEPAY_PRODUCTION_URL -> (linepay, production_url)
--
-- NewebPay:
--   NEWEBPAY_MERCHANT_ID -> (newebpay, merchant_id)
--   NEWEBPAY_HASH_KEY -> (newebpay, hash_key)
--   NEWEBPAY_HASH_IV -> (newebpay, hash_iv)
--   NEWEBPAY_MODE -> (newebpay, mode)
--   NEWEBPAY_TEST_URL -> (newebpay, test_url)
--   NEWEBPAY_PRODUCTION_URL -> (newebpay, production_url)
--
-- Shared:
--   FRONTEND_BASE_URL -> (shared, frontend_base_url)
--   API_BASE_URL -> (shared, api_base_url)

-- ========================================
-- 开始迁移
-- ========================================

-- Stripe 配置
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'stripe' as provider,
    'secret_key' as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('Stripe密钥 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key = 'STRIPE_SECRET_KEY'
  AND category = 'payment'
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'stripe' 
      AND config_key = 'secret_key' 
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- PayPal 配置
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'paypal' as provider,
    CASE 
        WHEN config_key = 'PAYPAL_CLIENT_ID' THEN 'client_id'
        WHEN config_key = 'PAYPAL_CLIENT_SECRET' THEN 'client_secret'
        WHEN config_key = 'PAYPAL_MODE' THEN 'mode'
    END as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('PayPal配置 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key IN ('PAYPAL_CLIENT_ID', 'PAYPAL_CLIENT_SECRET', 'PAYPAL_MODE')
  AND category = 'payment'
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'paypal' 
      AND config_key = CASE 
          WHEN service_configs.config_key = 'PAYPAL_CLIENT_ID' THEN 'client_id'
          WHEN service_configs.config_key = 'PAYPAL_CLIENT_SECRET' THEN 'client_secret'
          WHEN service_configs.config_key = 'PAYPAL_MODE' THEN 'mode'
      END
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- Alipay 配置
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'alipay' as provider,
    CASE 
        WHEN config_key = 'ALIPAY_APP_ID' THEN 'app_id'
        WHEN config_key = 'ALIPAY_PRIVATE_KEY_PATH' THEN 'private_key_path'
        WHEN config_key = 'ALIPAY_PUBLIC_KEY_PATH' THEN 'public_key_path'
        WHEN config_key = 'ALIPAY_GATEWAY' THEN 'gateway'
    END as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('支付宝配置 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key IN ('ALIPAY_APP_ID', 'ALIPAY_PRIVATE_KEY_PATH', 'ALIPAY_PUBLIC_KEY_PATH', 'ALIPAY_GATEWAY')
  AND category = 'payment'
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'alipay' 
      AND config_key = CASE 
          WHEN service_configs.config_key = 'ALIPAY_APP_ID' THEN 'app_id'
          WHEN service_configs.config_key = 'ALIPAY_PRIVATE_KEY_PATH' THEN 'private_key_path'
          WHEN service_configs.config_key = 'ALIPAY_PUBLIC_KEY_PATH' THEN 'public_key_path'
          WHEN service_configs.config_key = 'ALIPAY_GATEWAY' THEN 'gateway'
      END
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- WeChat 配置
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'wechat' as provider,
    CASE 
        WHEN config_key = 'WECHAT_APP_ID' THEN 'app_id'
        WHEN config_key = 'WECHAT_MCH_ID' THEN 'mch_id'
        WHEN config_key = 'WECHAT_API_KEY' THEN 'api_key'
        WHEN config_key = 'WECHAT_CERT_PATH' THEN 'cert_path'
        WHEN config_key = 'WECHAT_KEY_PATH' THEN 'key_path'
    END as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('微信支付配置 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key IN ('WECHAT_APP_ID', 'WECHAT_MCH_ID', 'WECHAT_API_KEY', 'WECHAT_CERT_PATH', 'WECHAT_KEY_PATH')
  AND category = 'payment'
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'wechat' 
      AND config_key = CASE 
          WHEN service_configs.config_key = 'WECHAT_APP_ID' THEN 'app_id'
          WHEN service_configs.config_key = 'WECHAT_MCH_ID' THEN 'mch_id'
          WHEN service_configs.config_key = 'WECHAT_API_KEY' THEN 'api_key'
          WHEN service_configs.config_key = 'WECHAT_CERT_PATH' THEN 'cert_path'
          WHEN service_configs.config_key = 'WECHAT_KEY_PATH' THEN 'key_path'
      END
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- Line Pay 配置
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'linepay' as provider,
    CASE 
        WHEN config_key = 'LINEPAY_CHANNEL_ID' THEN 'channel_id'
        WHEN config_key = 'LINEPAY_CHANNEL_SECRET' THEN 'channel_secret'
        WHEN config_key = 'LINEPAY_MODE' THEN 'mode'
        WHEN config_key = 'LINEPAY_SANDBOX_URL' THEN 'sandbox_url'
        WHEN config_key = 'LINEPAY_PRODUCTION_URL' THEN 'production_url'
    END as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('Line Pay配置 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key IN ('LINEPAY_CHANNEL_ID', 'LINEPAY_CHANNEL_SECRET', 'LINEPAY_MODE', 'LINEPAY_SANDBOX_URL', 'LINEPAY_PRODUCTION_URL')
  AND category = 'payment'
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'linepay' 
      AND config_key = CASE 
          WHEN service_configs.config_key = 'LINEPAY_CHANNEL_ID' THEN 'channel_id'
          WHEN service_configs.config_key = 'LINEPAY_CHANNEL_SECRET' THEN 'channel_secret'
          WHEN service_configs.config_key = 'LINEPAY_MODE' THEN 'mode'
          WHEN service_configs.config_key = 'LINEPAY_SANDBOX_URL' THEN 'sandbox_url'
          WHEN service_configs.config_key = 'LINEPAY_PRODUCTION_URL' THEN 'production_url'
      END
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- NewebPay 配置
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'newebpay' as provider,
    CASE 
        WHEN config_key = 'NEWEBPAY_MERCHANT_ID' THEN 'merchant_id'
        WHEN config_key = 'NEWEBPAY_HASH_KEY' THEN 'hash_key'
        WHEN config_key = 'NEWEBPAY_HASH_IV' THEN 'hash_iv'
        WHEN config_key = 'NEWEBPAY_MODE' THEN 'mode'
        WHEN config_key = 'NEWEBPAY_TEST_URL' THEN 'test_url'
        WHEN config_key = 'NEWEBPAY_PRODUCTION_URL' THEN 'production_url'
    END as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('蓝新金流配置 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key IN ('NEWEBPAY_MERCHANT_ID', 'NEWEBPAY_HASH_KEY', 'NEWEBPAY_HASH_IV', 'NEWEBPAY_MODE', 'NEWEBPAY_TEST_URL', 'NEWEBPAY_PRODUCTION_URL')
  AND category = 'payment'
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'newebpay' 
      AND config_key = CASE 
          WHEN service_configs.config_key = 'NEWEBPAY_MERCHANT_ID' THEN 'merchant_id'
          WHEN service_configs.config_key = 'NEWEBPAY_HASH_KEY' THEN 'hash_key'
          WHEN service_configs.config_key = 'NEWEBPAY_HASH_IV' THEN 'hash_iv'
          WHEN service_configs.config_key = 'NEWEBPAY_MODE' THEN 'mode'
          WHEN service_configs.config_key = 'NEWEBPAY_TEST_URL' THEN 'test_url'
          WHEN service_configs.config_key = 'NEWEBPAY_PRODUCTION_URL' THEN 'production_url'
      END
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- Shared 配置（前端URL、API URL等）
INSERT INTO payment_configs (provider, config_key, config_value, config_type, environment, description, is_active, version)
SELECT 
    'shared' as provider,
    CASE 
        WHEN config_key = 'FRONTEND_BASE_URL' THEN 'frontend_base_url'
        WHEN config_key = 'API_BASE_URL' THEN 'api_base_url'
    END as config_key,
    config_value,
    config_type,
    COALESCE(environment, 'production') as environment,
    CONCAT('共享配置 - ', description) as description,
    is_active,
    version
FROM service_configs
WHERE config_key IN ('FRONTEND_BASE_URL', 'API_BASE_URL')
  AND (category = 'payment' OR category IS NULL)
  AND NOT EXISTS (
    SELECT 1 FROM payment_configs 
    WHERE provider = 'shared' 
      AND config_key = CASE 
          WHEN service_configs.config_key = 'FRONTEND_BASE_URL' THEN 'frontend_base_url'
          WHEN service_configs.config_key = 'API_BASE_URL' THEN 'api_base_url'
      END
      AND environment = COALESCE(service_configs.environment, 'production')
  );

-- ========================================
-- 迁移完成提示
-- ========================================
SELECT 
    provider,
    COUNT(*) as config_count,
    GROUP_CONCAT(DISTINCT config_key ORDER BY config_key SEPARATOR ', ') as config_keys
FROM payment_configs
GROUP BY provider
ORDER BY provider;

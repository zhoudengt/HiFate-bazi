-- ========================================
-- 添加 Payssion 和 PayerMax 支付配置
-- ========================================
-- 创建时间: 2026-01-24
-- 说明: 为新的支付平台添加配置支持

USE `hifate_bazi`;

-- ========================================
-- Payssion 配置
-- ========================================
-- Payssion 生产环境配置
INSERT INTO `payment_configs` (`provider`, `config_key`, `config_value`, `environment`, `description`) VALUES
('payssion', 'api_key', '', 'production', 'Payssion API Key（生产环境）'),
('payssion', 'secret', '', 'production', 'Payssion Secret Key（生产环境）'),
('payssion', 'merchant_id', '', 'production', 'Payssion Merchant ID（生产环境）')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`), `description` = VALUES(`description`);

-- Payssion 沙箱环境配置
INSERT INTO `payment_configs` (`provider`, `config_key`, `config_value`, `environment`, `description`) VALUES
('payssion', 'api_key', '', 'sandbox', 'Payssion API Key（沙箱环境）'),
('payssion', 'secret', '', 'sandbox', 'Payssion Secret Key（沙箱环境）'),
('payssion', 'merchant_id', '', 'sandbox', 'Payssion Merchant ID（沙箱环境）')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`), `description` = VALUES(`description`);

-- ========================================
-- PayerMax 配置
-- ========================================
-- PayerMax 生产环境配置
INSERT INTO `payment_configs` (`provider`, `config_key`, `config_value`, `environment`, `description`) VALUES
('payermax', 'app_id', '', 'production', 'PayerMax App ID（生产环境）'),
('payermax', 'merchant_no', '', 'production', 'PayerMax Merchant No（生产环境）'),
('payermax', 'private_key_path', '/path/to/payermax/private_key.pem', 'production', 'PayerMax 私钥文件路径（生产环境）'),
('payermax', 'public_key_path', '/path/to/payermax/public_key.pem', 'production', 'PayerMax 公钥文件路径（生产环境）')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`), `description` = VALUES(`description`);

-- PayerMax 测试环境配置
INSERT INTO `payment_configs` (`provider`, `config_key`, `config_value`, `environment`, `test`, 'PayerMax App ID（测试环境）'),
('payermax', 'merchant_no', '', 'test', 'PayerMax Merchant No（测试环境）'),
('payermax', 'private_key_path', '/path/to/payermax/private_key_test.pem', 'test', 'PayerMax 私钥文件路径（测试环境）'),
('payermax', 'public_key_path', '/path/to/payermax/public_key_test.pem', 'test', 'PayerMax 公钥文件路径（测试环境）')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`), `description` = VALUES(`description`);

-- ========================================
-- 更新现有配置的描述
-- ========================================
UPDATE `payment_configs` SET `description` = 'Stripe Secret Key（生产环境）' WHERE `provider` = 'stripe' AND `config_key` = 'secret_key' AND `environment` = 'production';
UPDATE `payment_configs` SET `description` = 'PayPal Client ID（生产环境）' WHERE `provider` = 'paypal' AND `config_key` = 'client_id' AND `environment` = 'production';
UPDATE `payment_configs` SET `description` = '支付宝 App ID（生产环境）' WHERE `provider` = 'alipay' AND `config_key` = 'app_id' AND `environment` = 'production';
UPDATE `payment_configs` SET `description` = '微信支付 App ID（生产环境）' WHERE `provider` = 'wechat' AND `config_key` = 'app_id' AND `environment` = 'production';
UPDATE `payment_configs` SET `description` = 'Line Pay Channel ID（生产环境）' WHERE `provider` = 'linepay' AND `config_key` = 'channel_id' AND `environment` = 'production';

-- ========================================
-- 配置使用说明
-- ========================================
/*
Payssion 配置说明：
- api_key: 从 Payssion 商户后台获取
- secret: 从 Payssion 商户后台获取
- merchant_id: 从 Payssion 商户后台获取

PayerMax 配置说明：
- app_id: 从 PayerMax 开发者中心获取
- merchant_no: 从 PayerMax 商户后台获取
- private_key_path: RSA 私钥文件路径（需要提前生成和配置）
- public_key_path: RSA 公钥文件路径（用于验证响应签名）

配置步骤：
1. 注册相应支付平台的商户账号
2. 获取必要的 API 凭证
3. 使用数据库管理脚本设置配置值：
   python3 scripts/db/manage_payment_configs.py add payssion api_key YOUR_API_KEY --environment production
   python3 scripts/db/manage_payment_configs.py add payermax app_id YOUR_APP_ID --environment production
*/
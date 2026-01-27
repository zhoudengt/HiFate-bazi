-- 添加 PayerMax 配置到数据库
USE `hifate_bazi`;

-- 删除旧配置（如果存在）
DELETE FROM payment_configs 
WHERE provider = 'payermax' AND environment = 'production';

-- 插入 PayerMax 配置
INSERT INTO payment_configs (provider, config_key, config_value, environment, is_active, created_at, updated_at)
VALUES
  ('payermax', 'app_id', 'dbe50c5313384571a2f9aa36a5153576', 'production', 1, NOW(), NOW()),
  ('payermax', 'merchant_no', 'SDP01010117296213', 'production', 1, NOW(), NOW()),
  ('payermax', 'private_key_path', '/opt/secure/keys/payermax_private_key.pem', 'production', 1, NOW(), NOW()),
  ('payermax', 'public_key_path', '/opt/secure/keys/payermax_public_key.pem', 'production', 1, NOW(), NOW()),
  ('payermax', 'mode', 'sandbox', 'production', 1, NOW(), NOW());

-- 验证插入结果
SELECT provider, config_key, config_value, environment, is_active 
FROM payment_configs 
WHERE provider = 'payermax' AND environment = 'production'
ORDER BY config_key;

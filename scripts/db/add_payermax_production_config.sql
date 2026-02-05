-- ========================================
-- PayerMax 生产环境配置分离脚本
-- ========================================
-- 创建时间: 2026-02-05
-- 说明: 分离 sandbox 和 production 配置，支持环境切换
-- 执行前提: 
--   1. 已生成生产环境密钥对
--   2. 已在 PayerMax 平台上传商户公钥并下载平台公钥
--   3. 已将密钥文件部署到 /opt/secure/keys/ 目录

USE `hifate_bazi`;

-- ========================================
-- 步骤 1: 将现有配置标记为 sandbox 环境
-- ========================================
-- 现有配置的 environment 是 'production'，但 mode 是 'sandbox'
-- 将其改为真正的 sandbox 环境配置

UPDATE payment_configs 
SET environment = 'sandbox',
    is_active = 0,
    updated_at = NOW()
WHERE provider = 'payermax' 
  AND environment = 'production';

-- ========================================
-- 步骤 2: 插入生产环境配置
-- ========================================
-- 注意: 如果生产环境的 app_id 和 merchant_no 与沙箱不同，请修改下面的值

INSERT INTO payment_configs 
  (provider, config_key, config_value, config_type, environment, description, is_active, created_at, updated_at)
VALUES
  -- app_id (如果生产环境不同，请修改此值)
  ('payermax', 'app_id', 'dbe50c5313384571a2f9aa36a5153576', 'string', 'production', 'PayerMax 生产环境应用ID', 1, NOW(), NOW()),
  
  -- merchant_no (如果生产环境不同，请修改此值)
  ('payermax', 'merchant_no', 'SDP01010117296213', 'string', 'production', 'PayerMax 生产环境商户号', 1, NOW(), NOW()),
  
  -- 生产环境私钥路径 (商户私钥，用于签名请求)
  ('payermax', 'private_key_path', '/opt/secure/keys/payermax_private_key_prod.pem', 'string', 'production', 'PayerMax 生产环境商户私钥路径', 1, NOW(), NOW()),
  
  -- 生产环境公钥路径 (PayerMax 平台公钥，用于验证响应签名)
  ('payermax', 'public_key_path', '/opt/secure/keys/payermax_public_key_prod.pem', 'string', 'production', 'PayerMax 生产环境平台公钥路径', 1, NOW(), NOW()),
  
  -- mode 设置为 production (控制 API URL)
  ('payermax', 'mode', 'production', 'string', 'production', 'PayerMax 生产环境模式', 1, NOW(), NOW());

-- ========================================
-- 步骤 3: 验证配置结果
-- ========================================
SELECT 
  id,
  provider, 
  config_key, 
  config_value, 
  environment, 
  is_active,
  description
FROM payment_configs 
WHERE provider = 'payermax'
ORDER BY environment DESC, config_key;

-- ========================================
-- 环境切换 SQL（供日后使用）
-- ========================================

-- 切换到生产环境:
-- UPDATE payment_configs SET is_active = CASE WHEN environment = 'production' THEN 1 ELSE 0 END WHERE provider = 'payermax';

-- 切换到沙箱环境:
-- UPDATE payment_configs SET is_active = CASE WHEN environment = 'sandbox' THEN 1 ELSE 0 END WHERE provider = 'payermax';

-- 查看当前激活的配置:
-- SELECT * FROM payment_configs WHERE provider = 'payermax' AND is_active = 1;

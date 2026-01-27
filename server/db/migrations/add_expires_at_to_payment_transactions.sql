-- ========================================
-- 添加 expires_at 字段到 payment_transactions 表
-- ========================================
-- 创建时间: 2026-01-27
-- 说明: 为支付订单添加过期时间字段，用于30分钟倒计时和过期检查

USE `hifate_bazi`;

-- 添加 expires_at 字段
ALTER TABLE `payment_transactions` 
ADD COLUMN `expires_at` TIMESTAMP NULL COMMENT '订单过期时间（创建时间+30分钟）' AFTER `created_at`;

-- 添加索引用于快速查询过期订单
ALTER TABLE `payment_transactions` 
ADD INDEX `idx_expires_at` (`expires_at`);

-- 为现有 pending 状态的订单设置默认过期时间（如果为空）
-- 注意：这里只更新 created_at 不为空且 expires_at 为空的记录
UPDATE `payment_transactions` 
SET `expires_at` = DATE_ADD(`created_at`, INTERVAL 30 MINUTE)
WHERE `expires_at` IS NULL 
  AND `status` = 'pending' 
  AND `created_at` IS NOT NULL;

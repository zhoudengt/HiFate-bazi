-- ========================================
-- 转换费率历史表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-22
-- 说明: 存储历史转换费率数据，用于风控监控和趋势分析

USE `hifate_bazi`;

-- ========================================
-- 转换费率历史表
-- ========================================
CREATE TABLE IF NOT EXISTS `conversion_fee_history` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    `provider` VARCHAR(50) NOT NULL COMMENT '支付渠道：stripe/paypal',
    `from_currency` VARCHAR(10) NOT NULL COMMENT '源货币代码',
    `to_currency` VARCHAR(10) NOT NULL COMMENT '目标货币代码',
    `fee_rate` DECIMAL(10, 4) NOT NULL COMMENT '费率（如：0.03表示3%）',
    `fixed_fee` DECIMAL(20, 2) DEFAULT 0 COMMENT '固定费用（如有）',
    `transaction_id` BIGINT COMMENT '关联的交易ID（如有）',
    `recorded_at` TIMESTAMP(3) NOT NULL COMMENT '记录时间（精确到毫秒）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_provider` (`provider`),
    INDEX `idx_currency_pair` (`from_currency`, `to_currency`),
    INDEX `idx_recorded_at` (`recorded_at`),
    INDEX `idx_transaction_id` (`transaction_id`),
    INDEX `idx_provider_recorded` (`provider`, `recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='转换费率历史表';

-- ========================================
-- 汇率历史表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-22
-- 说明: 存储历史汇率数据，用于风控监控和趋势分析

USE `hifate_bazi`;

-- ========================================
-- 汇率历史表
-- ========================================
CREATE TABLE IF NOT EXISTS `fx_rate_history` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    `from_currency` VARCHAR(10) NOT NULL COMMENT '源货币代码（如：USD, TWD, THB）',
    `to_currency` VARCHAR(10) NOT NULL COMMENT '目标货币代码（默认：HKD）',
    `exchange_rate` DECIMAL(20, 8) NOT NULL COMMENT '汇率',
    `provider` VARCHAR(50) NOT NULL COMMENT '汇率来源：stripe/paypal',
    `source` VARCHAR(50) COMMENT '数据来源（如：api, transaction）',
    `transaction_id` BIGINT COMMENT '关联的交易ID（如有）',
    `recorded_at` TIMESTAMP(3) NOT NULL COMMENT '记录时间（精确到毫秒）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_currency_pair` (`from_currency`, `to_currency`),
    INDEX `idx_provider` (`provider`),
    INDEX `idx_recorded_at` (`recorded_at`),
    INDEX `idx_transaction_id` (`transaction_id`),
    INDEX `idx_currency_recorded` (`from_currency`, `to_currency`, `recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='汇率历史表';

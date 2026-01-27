-- ========================================
-- 支付交易记录表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-22
-- 说明: 记录所有支付交易，包括原始金额、转换后金额、转换费用、实际汇率等

USE `hifate_bazi`;

-- ========================================
-- 支付交易记录表
-- ========================================
CREATE TABLE IF NOT EXISTS `payment_transactions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '交易ID',
    `order_id` VARCHAR(100) NOT NULL COMMENT '订单号（业务订单号）',
    `provider` VARCHAR(50) NOT NULL COMMENT '支付渠道：stripe/paypal/alipay/wechat/linepay',
    `provider_payment_id` VARCHAR(200) COMMENT '支付渠道返回的支付ID（如：session_id, payment_id, transaction_id）',
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '支付状态：pending/success/failed/canceled',
    
    -- 原始金额和货币
    `original_amount` DECIMAL(20, 2) NOT NULL COMMENT '原始金额',
    `original_currency` VARCHAR(10) NOT NULL COMMENT '原始货币代码（如：USD, TWD, THB）',
    
    -- 转换后金额和货币
    `converted_amount` DECIMAL(20, 2) COMMENT '转换后金额（如果需要转换）',
    `converted_currency` VARCHAR(10) DEFAULT 'HKD' COMMENT '转换后货币代码（默认HKD）',
    `needs_conversion` BOOLEAN DEFAULT 0 COMMENT '是否需要货币转换',
    
    -- 费用信息
    `conversion_fee` DECIMAL(20, 2) DEFAULT 0 COMMENT '转换费用（商家承担）',
    `conversion_fee_rate` DECIMAL(10, 4) COMMENT '转换费率（如：0.03表示3%）',
    `fixed_fee` DECIMAL(20, 2) DEFAULT 0 COMMENT '固定费用（PayPal的TWD/HKD固定费用）',
    `total_fee` DECIMAL(20, 2) DEFAULT 0 COMMENT '总费用（转换费用+固定费用）',
    
    -- 汇率信息
    `exchange_rate` DECIMAL(20, 8) COMMENT '预期汇率（创建订单时的汇率）',
    `actual_exchange_rate` DECIMAL(20, 8) COMMENT '实际汇率（支付成功时的汇率）',
    `exchange_rate_source` VARCHAR(50) COMMENT '汇率来源（stripe/paypal）',
    
    -- 区域和白名单信息
    `user_region` VARCHAR(10) COMMENT '用户所在区域（如：HK, TW, CN, US）',
    `region_open` BOOLEAN DEFAULT 1 COMMENT '区域是否开放',
    `is_whitelisted` BOOLEAN DEFAULT 0 COMMENT '是否为白名单用户',
    
    -- 客户信息
    `customer_email` VARCHAR(255) COMMENT '客户邮箱',
    `customer_id` VARCHAR(100) COMMENT '客户ID（业务系统用户ID）',
    
    -- 产品信息
    `product_name` VARCHAR(500) COMMENT '产品名称',
    `product_description` TEXT COMMENT '产品描述',
    
    -- 元数据
    `metadata` JSON COMMENT '元数据（JSON格式，存储额外信息）',
    
    -- 时间戳
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `paid_at` TIMESTAMP NULL COMMENT '支付成功时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_order_id` (`order_id`),
    INDEX `idx_provider` (`provider`),
    INDEX `idx_provider_payment_id` (`provider_payment_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_customer_email` (`customer_email`),
    INDEX `idx_customer_id` (`customer_id`),
    INDEX `idx_user_region` (`user_region`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_paid_at` (`paid_at`),
    INDEX `idx_needs_conversion` (`needs_conversion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付交易记录表';

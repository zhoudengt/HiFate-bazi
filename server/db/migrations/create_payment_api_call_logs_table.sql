-- ========================================
-- 支付接口调用日志表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-22
-- 说明: 记录所有支付接口调用，包括接口名称、调用时间、成功/失败、响应时间、账单信息等

USE `hifate_bazi`;

-- ========================================
-- 支付接口调用日志表
-- ========================================
CREATE TABLE IF NOT EXISTS `payment_api_call_logs` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    `api_name` VARCHAR(200) NOT NULL COMMENT '接口名称（如：stripe.create_checkout_session, paypal.create_order）',
    `provider` VARCHAR(50) NOT NULL COMMENT '支付渠道：stripe/paypal/alipay/wechat/linepay',
    `transaction_id` BIGINT COMMENT '关联的交易ID（payment_transactions.id）',
    `order_id` VARCHAR(100) COMMENT '关联的订单号',
    
    -- 调用时间
    `start_time` TIMESTAMP(3) NOT NULL COMMENT '调用开始时间（精确到毫秒）',
    `end_time` TIMESTAMP(3) COMMENT '调用结束时间（精确到毫秒）',
    `duration_ms` INT COMMENT '响应时间（毫秒）',
    
    -- 调用结果
    `success` BOOLEAN NOT NULL COMMENT '是否成功：1=成功，0=失败',
    `error_code` VARCHAR(100) COMMENT '错误码（如有）',
    `error_message` TEXT COMMENT '错误信息（如有）',
    `http_status_code` INT COMMENT 'HTTP状态码',
    
    -- 请求参数
    `request_params` JSON COMMENT '请求参数（JSON格式，脱敏处理）',
    
    -- 响应结果
    `response_data` JSON COMMENT '响应结果（JSON格式，脱敏处理）',
    
    -- 账单信息
    `billing_amount` DECIMAL(20, 2) COMMENT '账单金额',
    `billing_currency` VARCHAR(10) COMMENT '账单货币',
    `billing_conversion_fee` DECIMAL(20, 2) COMMENT '转换费用',
    `billing_fixed_fee` DECIMAL(20, 2) COMMENT '固定费用',
    `billing_exchange_rate` DECIMAL(20, 8) COMMENT '汇率',
    
    -- 元数据
    `metadata` JSON COMMENT '元数据（JSON格式，存储额外信息）',
    
    -- 时间戳
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_api_name` (`api_name`),
    INDEX `idx_provider` (`provider`),
    INDEX `idx_transaction_id` (`transaction_id`),
    INDEX `idx_order_id` (`order_id`),
    INDEX `idx_success` (`success`),
    INDEX `idx_start_time` (`start_time`),
    INDEX `idx_provider_api` (`provider`, `api_name`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付接口调用日志表';

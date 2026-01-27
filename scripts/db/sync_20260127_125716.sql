-- 数据库同步脚本
-- 生成时间: 2026-01-27 12:57:16
-- 部署ID: 20260127_125716

START TRANSACTION;

-- ==================== 删除表（⚠️ 危险操作，需要手动确认）====================
-- ⚠️  警告：删除表会永久删除所有数据，请先备份数据！
-- ⚠️  建议：在执行删除前，先备份表数据：mysqldump -u root -p database_name table_name > backup_table_name.sql

-- 删除表: service_configs_260127 (包含 37 条数据)
-- DROP TABLE IF EXISTS `service_configs_260127`;

-- ==================== 新增表 ====================
-- 创建表: fx_rate_history
CREATE TABLE `fx_rate_history` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `from_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '源货币代码（如：USD, TWD, THB）',
  `to_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '目标货币代码（默认：HKD）',
  `exchange_rate` decimal(20,8) NOT NULL COMMENT '汇率',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '汇率来源：stripe/paypal',
  `source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '数据来源（如：api, transaction）',
  `transaction_id` bigint DEFAULT NULL COMMENT '关联的交易ID（如有）',
  `recorded_at` timestamp(3) NOT NULL COMMENT '记录时间（精确到毫秒）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_currency_pair` (`from_currency`,`to_currency`),
  KEY `idx_provider` (`provider`),
  KEY `idx_recorded_at` (`recorded_at`),
  KEY `idx_transaction_id` (`transaction_id`),
  KEY `idx_currency_recorded` (`from_currency`,`to_currency`,`recorded_at`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='汇率历史表';

-- 创建表: conversion_fee_history
CREATE TABLE `conversion_fee_history` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '支付渠道：stripe/paypal',
  `from_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '源货币代码',
  `to_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '目标货币代码',
  `fee_rate` decimal(10,4) NOT NULL COMMENT '费率（如：0.03表示3%）',
  `fixed_fee` decimal(20,2) DEFAULT '0.00' COMMENT '固定费用（如有）',
  `transaction_id` bigint DEFAULT NULL COMMENT '关联的交易ID（如有）',
  `recorded_at` timestamp(3) NOT NULL COMMENT '记录时间（精确到毫秒）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_provider` (`provider`),
  KEY `idx_currency_pair` (`from_currency`,`to_currency`),
  KEY `idx_recorded_at` (`recorded_at`),
  KEY `idx_transaction_id` (`transaction_id`),
  KEY `idx_provider_recorded` (`provider`,`recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='转换费率历史表';

-- 创建表: payment_whitelist
CREATE TABLE `payment_whitelist` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '白名单ID',
  `user_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户ID（可选）',
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户邮箱（可选）',
  `phone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户手机号（可选）',
  `identifier` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '其他标识符（如：IP地址等，可选）',
  `whitelist_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '白名单类型：user_id/email/phone/identifier',
  `blocked_region` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '被限制的区域（如：CN表示大陆用户）',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'active' COMMENT '状态：active/inactive',
  `notes` text COLLATE utf8mb4_unicode_ci COMMENT '备注说明',
  `created_by` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_email` (`email`),
  KEY `idx_phone` (`phone`),
  KEY `idx_identifier` (`identifier`),
  KEY `idx_whitelist_type` (`whitelist_type`),
  KEY `idx_blocked_region` (`blocked_region`),
  KEY `idx_status` (`status`),
  KEY `idx_user_id_status` (`user_id`,`status`),
  KEY `idx_email_status` (`email`,`status`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付白名单表';

-- 创建表: payment_region_config
CREATE TABLE `payment_region_config` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `region_code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '区域代码（如：HK, TW, CN, US, JP等）',
  `region_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '区域名称（如：香港, 台湾, 大陆, 美国, 日本）',
  `is_open` tinyint(1) DEFAULT '1' COMMENT '是否开放支付：1=开放，0=关闭',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '描述说明',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_region_code` (`region_code`),
  KEY `idx_is_open` (`is_open`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付区域配置表';

-- 创建表: payment_api_call_logs
CREATE TABLE `payment_api_call_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `api_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '接口名称（如：stripe.create_checkout_session, paypal.create_order）',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '支付渠道：stripe/paypal/alipay/wechat/linepay',
  `transaction_id` bigint DEFAULT NULL COMMENT '关联的交易ID（payment_transactions.id）',
  `order_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联的订单号',
  `start_time` timestamp(3) NOT NULL COMMENT '调用开始时间（精确到毫秒）',
  `end_time` timestamp(3) NULL DEFAULT NULL COMMENT '调用结束时间（精确到毫秒）',
  `duration_ms` int DEFAULT NULL COMMENT '响应时间（毫秒）',
  `success` tinyint(1) NOT NULL COMMENT '是否成功：1=成功，0=失败',
  `error_code` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '错误码（如有）',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '错误信息（如有）',
  `http_status_code` int DEFAULT NULL COMMENT 'HTTP状态码',
  `request_params` json DEFAULT NULL COMMENT '请求参数（JSON格式，脱敏处理）',
  `response_data` json DEFAULT NULL COMMENT '响应结果（JSON格式，脱敏处理）',
  `billing_amount` decimal(20,2) DEFAULT NULL COMMENT '账单金额',
  `billing_currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '账单货币',
  `billing_conversion_fee` decimal(20,2) DEFAULT NULL COMMENT '转换费用',
  `billing_fixed_fee` decimal(20,2) DEFAULT NULL COMMENT '固定费用',
  `billing_exchange_rate` decimal(20,8) DEFAULT NULL COMMENT '汇率',
  `metadata` json DEFAULT NULL COMMENT '元数据（JSON格式，存储额外信息）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_api_name` (`api_name`),
  KEY `idx_provider` (`provider`),
  KEY `idx_transaction_id` (`transaction_id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_success` (`success`),
  KEY `idx_start_time` (`start_time`),
  KEY `idx_provider_api` (`provider`,`api_name`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付接口调用日志表';

-- 创建表: payment_transactions
CREATE TABLE `payment_transactions` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '交易ID',
  `order_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '订单号（业务订单号）',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '支付渠道：stripe/paypal/alipay/wechat/linepay',
  `provider_payment_id` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '支付渠道返回的支付ID（如：session_id, payment_id, transaction_id）',
  `status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'pending' COMMENT '支付状态：pending/success/failed/canceled',
  `original_amount` decimal(20,2) NOT NULL COMMENT '原始金额',
  `original_currency` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始货币代码（如：USD, TWD, THB）',
  `converted_amount` decimal(20,2) DEFAULT NULL COMMENT '转换后金额（如果需要转换）',
  `converted_currency` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'HKD' COMMENT '转换后货币代码（默认HKD）',
  `needs_conversion` tinyint(1) DEFAULT '0' COMMENT '是否需要货币转换',
  `conversion_fee` decimal(20,2) DEFAULT '0.00' COMMENT '转换费用（商家承担）',
  `conversion_fee_rate` decimal(10,4) DEFAULT NULL COMMENT '转换费率（如：0.03表示3%）',
  `fixed_fee` decimal(20,2) DEFAULT '0.00' COMMENT '固定费用（PayPal的TWD/HKD固定费用）',
  `total_fee` decimal(20,2) DEFAULT '0.00' COMMENT '总费用（转换费用+固定费用）',
  `exchange_rate` decimal(20,8) DEFAULT NULL COMMENT '预期汇率（创建订单时的汇率）',
  `actual_exchange_rate` decimal(20,8) DEFAULT NULL COMMENT '实际汇率（支付成功时的汇率）',
  `exchange_rate_source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '汇率来源（stripe/paypal）',
  `user_region` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户所在区域（如：HK, TW, CN, US）',
  `region_open` tinyint(1) DEFAULT '1' COMMENT '区域是否开放',
  `is_whitelisted` tinyint(1) DEFAULT '0' COMMENT '是否为白名单用户',
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '客户邮箱',
  `customer_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '客户ID（业务系统用户ID）',
  `product_name` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '产品名称',
  `product_description` text COLLATE utf8mb4_unicode_ci COMMENT '产品描述',
  `metadata` json DEFAULT NULL COMMENT '元数据（JSON格式，存储额外信息）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `paid_at` timestamp NULL DEFAULT NULL COMMENT '支付成功时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_provider` (`provider`),
  KEY `idx_provider_payment_id` (`provider_payment_id`),
  KEY `idx_status` (`status`),
  KEY `idx_customer_email` (`customer_email`),
  KEY `idx_customer_id` (`customer_id`),
  KEY `idx_user_region` (`user_region`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_paid_at` (`paid_at`),
  KEY `idx_needs_conversion` (`needs_conversion`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付交易记录表';

-- ==================== 删除字段（⚠️ 危险操作，需要手动确认）====================
-- ⚠️  警告：删除字段会永久删除该字段的所有数据，请先确认是否有外键依赖！
-- ⚠️  建议：在执行删除前，检查是否有其他表的外键引用此字段

-- 删除表 ai_conversation_history 的字段 scenario_type
-- ALTER TABLE `ai_conversation_history` DROP COLUMN `scenario_type`;

-- ==================== 新增表的数据 ====================
-- 表 fx_rate_history 有 2 条数据需要同步
INSERT INTO `fx_rate_history` (`id`, `from_currency`, `to_currency`, `exchange_rate`, `provider`, `source`, `transaction_id`, `recorded_at`, `created_at`) VALUES (1, 'TWD', 'HKD', '0.25500000', 'stripe', 'test', NULL, '2026-01-23 18:35:15.813000', '2026-01-23 18:35:15');
INSERT INTO `fx_rate_history` (`id`, `from_currency`, `to_currency`, `exchange_rate`, `provider`, `source`, `transaction_id`, `recorded_at`, `created_at`) VALUES (2, 'TWD', 'HKD', '0.25500000', 'stripe', 'test', NULL, '2026-01-23 18:35:53.139000', '2026-01-23 18:35:53');

-- 表 payment_whitelist 有 2 条数据需要同步
INSERT INTO `payment_whitelist` (`id`, `user_id`, `email`, `phone`, `identifier`, `whitelist_type`, `blocked_region`, `status`, `notes`, `created_by`, `created_at`, `updated_at`) VALUES (1, NULL, 'test_whitelist_1769164472@example.com', NULL, NULL, 'email', 'CN', 'active', '测试用户', 'test_script', '2026-01-23 18:34:32', '2026-01-23 18:34:32');
INSERT INTO `payment_whitelist` (`id`, `user_id`, `email`, `phone`, `identifier`, `whitelist_type`, `blocked_region`, `status`, `notes`, `created_by`, `created_at`, `updated_at`) VALUES (3, NULL, 'test_1769164515@example.com', NULL, NULL, 'email', 'CN', 'active', NULL, 'test', '2026-01-23 18:35:15', '2026-01-23 18:35:15');

-- 表 payment_region_config 有 10 条数据需要同步
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (1, 'HK', '香港', 1, '香港特别行政区 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (2, 'TW', '台湾', 1, '台湾地区 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (3, 'CN', '大陆', 0, '中国大陆 - 关闭支付（白名单用户除外）', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (4, 'US', '美国', 1, '美国 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (5, 'JP', '日本', 1, '日本 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (6, 'SG', '新加坡', 1, '新加坡 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (7, 'TH', '泰国', 1, '泰国 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (8, 'MY', '马来西亚', 1, '马来西亚 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (9, 'PH', '菲律宾', 1, '菲律宾 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');
INSERT INTO `payment_region_config` (`id`, `region_code`, `region_name`, `is_open`, `description`, `created_at`, `updated_at`) VALUES (10, 'ID', '印尼', 1, '印尼 - 开放支付', '2026-01-23 18:20:44', '2026-01-23 18:20:44');

-- 表 payment_transactions 有 2 条数据需要同步
INSERT INTO `payment_transactions` (`id`, `order_id`, `provider`, `provider_payment_id`, `status`, `original_amount`, `original_currency`, `converted_amount`, `converted_currency`, `needs_conversion`, `conversion_fee`, `conversion_fee_rate`, `fixed_fee`, `total_fee`, `exchange_rate`, `actual_exchange_rate`, `exchange_rate_source`, `user_region`, `region_open`, `is_whitelisted`, `customer_email`, `customer_id`, `product_name`, `product_description`, `metadata`, `created_at`, `paid_at`, `updated_at`) VALUES (1, 'TEST_1769164515757', 'stripe', NULL, 'pending', '100.00', 'TWD', '25.50', 'HKD', 1, '3.50', '0.0350', NULL, '3.50', '0.25500000', NULL, NULL, 'TW', 1, 0, 'test@example.com', NULL, '测试产品', NULL, NULL, '2026-01-23 18:35:15', NULL, '2026-01-23 18:35:15');
INSERT INTO `payment_transactions` (`id`, `order_id`, `provider`, `provider_payment_id`, `status`, `original_amount`, `original_currency`, `converted_amount`, `converted_currency`, `needs_conversion`, `conversion_fee`, `conversion_fee_rate`, `fixed_fee`, `total_fee`, `exchange_rate`, `actual_exchange_rate`, `exchange_rate_source`, `user_region`, `region_open`, `is_whitelisted`, `customer_email`, `customer_id`, `product_name`, `product_description`, `metadata`, `created_at`, `paid_at`, `updated_at`) VALUES (2, 'TEST_1769164553127', 'stripe', NULL, 'success', '100.00', 'TWD', '25.50', 'HKD', 1, '3.50', '0.0350', NULL, '3.50', '0.25500000', '0.25600000', NULL, 'TW', 1, 0, 'test@example.com', NULL, '测试产品', NULL, NULL, '2026-01-23 18:35:53', NULL, '2026-01-23 18:35:53');

-- ==================== 表数据差异（需要同步的数据）====================
-- 表 payment_configs 有 4 条数据需要同步（本地有但生产没有）
INSERT IGNORE INTO `payment_configs` (`id`, `provider`, `config_key`, `config_value`, `config_type`, `environment`, `merchant_id`, `description`, `is_active`, `is_encrypted`, `version`, `created_at`, `updated_at`) VALUES (9, 'payermax', 'merchant_no', 'SDP01010117296213', 'string', 'production', NULL, NULL, 1, 0, 1, '2026-01-27 11:30:49', '2026-01-27 11:30:49');
INSERT IGNORE INTO `payment_configs` (`id`, `provider`, `config_key`, `config_value`, `config_type`, `environment`, `merchant_id`, `description`, `is_active`, `is_encrypted`, `version`, `created_at`, `updated_at`) VALUES (10, 'payermax', 'private_key_path', '/opt/secure/keys/payermax_private_key.pem', 'string', 'production', NULL, NULL, 1, 0, 1, '2026-01-27 11:30:49', '2026-01-27 11:30:49');
INSERT IGNORE INTO `payment_configs` (`id`, `provider`, `config_key`, `config_value`, `config_type`, `environment`, `merchant_id`, `description`, `is_active`, `is_encrypted`, `version`, `created_at`, `updated_at`) VALUES (11, 'payermax', 'public_key_path', '/opt/secure/keys/payermax_public_key.pem', 'string', 'production', NULL, NULL, 1, 0, 1, '2026-01-27 11:30:49', '2026-01-27 11:30:49');
INSERT IGNORE INTO `payment_configs` (`id`, `provider`, `config_key`, `config_value`, `config_type`, `environment`, `merchant_id`, `description`, `is_active`, `is_encrypted`, `version`, `created_at`, `updated_at`) VALUES (12, 'payermax', 'mode', 'sandbox', 'string', 'production', NULL, NULL, 1, 0, 1, '2026-01-27 11:30:49', '2026-01-27 11:30:49');

-- 表 homepage_contents 有 9 条数据需要同步（本地有但生产没有）
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (8, '测试', '["测试"]', '测试', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:23:32', '2026-01-22 18:23:32');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (9, '测试内容', '["测试"]', '测试描述', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:27:31', '2026-01-22 18:27:31');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (10, '测试', '["测试"]', '测试', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:27:54', '2026-01-22 18:27:54');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (11, '测试', '["测试"]', '测试', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:28:02', '2026-01-22 18:28:02');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (12, '更新后的标题', '["测试"]', '测试描述', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 5, 0, '2026-01-22 18:37:34', '2026-01-22 18:37:44');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (13, '最终测试', '["测试"]', '测试', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:38:08', '2026-01-22 18:38:08');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (14, '最终测试', '["测试"]', '测试', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:38:23', '2026-01-22 18:38:23');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (15, '最终验证', '["测试"]', '测试', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:39:57', '2026-01-22 18:39:57');
INSERT IGNORE INTO `homepage_contents` (`id`, `title`, `tags`, `description`, `image_base64`, `sort_order`, `enabled`, `created_at`, `updated_at`) VALUES (16, '测试内容', '["测试"]', '测试描述', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 1, 1, '2026-01-22 18:42:29', '2026-01-22 18:42:29');

COMMIT;

-- 同步完成
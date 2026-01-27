-- ========================================
-- 支付白名单表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-22
-- 说明: 存储白名单用户信息，用于不开放区域的用户

USE `hifate_bazi`;

-- ========================================
-- 支付白名单表
-- ========================================
CREATE TABLE IF NOT EXISTS `payment_whitelist` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '白名单ID',
    `user_id` VARCHAR(100) COMMENT '用户ID（可选）',
    `email` VARCHAR(255) COMMENT '用户邮箱（可选）',
    `phone` VARCHAR(50) COMMENT '用户手机号（可选）',
    `identifier` VARCHAR(255) COMMENT '其他标识符（如：IP地址等，可选）',
    `whitelist_type` VARCHAR(20) NOT NULL COMMENT '白名单类型：user_id/email/phone/identifier',
    `blocked_region` VARCHAR(10) COMMENT '被限制的区域（如：CN表示大陆用户）',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive',
    `notes` TEXT COMMENT '备注说明',
    `created_by` VARCHAR(100) COMMENT '创建人',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_email` (`email`),
    INDEX `idx_phone` (`phone`),
    INDEX `idx_identifier` (`identifier`),
    INDEX `idx_whitelist_type` (`whitelist_type`),
    INDEX `idx_blocked_region` (`blocked_region`),
    INDEX `idx_status` (`status`),
    INDEX `idx_user_id_status` (`user_id`, `status`),
    INDEX `idx_email_status` (`email`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付白名单表';

-- 神煞排序配置表
-- 用于存储神煞的排序顺序、白话文解析和古诀
-- 创建时间: 2026-01-14

USE `hifate_bazi`;

-- 创建神煞排序配置表
CREATE TABLE IF NOT EXISTS `shensha_sort_config` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `sort_order` INT NOT NULL COMMENT '排序顺序（从小到大，数字越小越靠前）',
    `name` VARCHAR(50) NOT NULL COMMENT '神煞名称',
    `plain_text_desc` TEXT COMMENT '白话文解析（暂存，后期使用）',
    `ancient_desc` TEXT COMMENT '古诀（暂存，后期使用）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_name` (`name`),
    INDEX `idx_sort_order` (`sort_order`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='神煞排序配置表';

-- 更新规则版本号（用于热更新检测）
UPDATE `rule_version` SET `content_version` = `content_version` + 1 WHERE `id` = 1;

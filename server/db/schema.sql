-- 八字规则引擎数据库表结构

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `hifate_bazi` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `hifate_bazi`;

-- 规则表
CREATE TABLE IF NOT EXISTS `bazi_rules` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    `rule_code` VARCHAR(50) UNIQUE NOT NULL COMMENT '规则代码',
    `rule_name` VARCHAR(200) NOT NULL COMMENT '规则名称',
    `rule_type` VARCHAR(50) NOT NULL COMMENT '规则类型',
    `priority` INT DEFAULT 100 COMMENT '优先级（数字越大优先级越高）',
    `conditions` JSON NOT NULL COMMENT '匹配条件（JSON格式）',
    `content` JSON NOT NULL COMMENT '规则内容（JSON格式）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `description` TEXT COMMENT '规则描述',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_rule_type` (`rule_type`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_rule_code` (`rule_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='八字规则表';

-- 规则匹配日志表（可选，用于统计分析）
CREATE TABLE IF NOT EXISTS `bazi_rule_matches` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    `rule_id` BIGINT NOT NULL COMMENT '规则ID',
    `rule_code` VARCHAR(50) NOT NULL COMMENT '规则代码',
    `solar_date` VARCHAR(20) NOT NULL COMMENT '阳历日期',
    `solar_time` VARCHAR(20) NOT NULL COMMENT '出生时间',
    `gender` VARCHAR(10) NOT NULL COMMENT '性别',
    `matched_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '匹配时间',
    INDEX `idx_rule_id` (`rule_id`),
    INDEX `idx_matched_at` (`matched_at`),
    INDEX `idx_solar_date` (`solar_date`),
    FOREIGN KEY (`rule_id`) REFERENCES `bazi_rules`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='规则匹配日志表';

-- 缓存统计表（可选，用于监控）
CREATE TABLE IF NOT EXISTS `cache_stats` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '统计ID',
    `cache_type` VARCHAR(20) NOT NULL COMMENT '缓存类型（L1/L2）',
    `hit_count` BIGINT DEFAULT 0 COMMENT '命中次数',
    `miss_count` BIGINT DEFAULT 0 COMMENT '未命中次数',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY `uk_type_date` (`cache_type`, `stat_date`),
    INDEX `idx_stat_date` (`stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='缓存统计表';

-- 日柱性别内容表（用于存储日柱性别匹配的具体内容）
CREATE TABLE IF NOT EXISTS `rizhu_gender_contents` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '内容ID',
    `rizhu` VARCHAR(10) NOT NULL COMMENT '日柱（如：甲子）',
    `gender` VARCHAR(10) NOT NULL COMMENT '性别（male/female）',
    `descriptions` JSON NOT NULL COMMENT '描述列表（JSON数组）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `version` INT DEFAULT 1 COMMENT '版本号（用于热加载）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_rizhu_gender` (`rizhu`, `gender`),
    INDEX `idx_rizhu` (`rizhu`),
    INDEX `idx_gender` (`gender`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日柱性别内容表';

-- 版本号表（用于热加载检测）
CREATE TABLE IF NOT EXISTS `rule_version` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '版本ID',
    `rule_version` INT DEFAULT 1 COMMENT '规则版本号',
    `content_version` INT DEFAULT 1 COMMENT '内容版本号',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='规则版本号表';

-- 初始化版本号表
INSERT INTO `rule_version` (`rule_version`, `content_version`) VALUES (1, 1)
ON DUPLICATE KEY UPDATE `rule_version` = `rule_version`;


-- 每日运势数据库表结构

USE `hifate_bazi`;

-- 六十甲子运势表
CREATE TABLE IF NOT EXISTS `daily_fortune_jiazi` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `jiazi_day` VARCHAR(10) NOT NULL COMMENT '甲子日（如：乙丑）',
    `content` TEXT NOT NULL COMMENT '每日运势显示内容',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_jiazi_day` (`jiazi_day`),
    INDEX `idx_jiazi_day` (`jiazi_day`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='六十甲子运势表';

-- 十神查询表（Sheet 1）
CREATE TABLE IF NOT EXISTS `daily_fortune_shishen_query` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_stem` VARCHAR(5) NOT NULL COMMENT '当日日干（如：甲）',
    `birth_stem` VARCHAR(5) NOT NULL COMMENT '命主日干（如：己）',
    `shishen` VARCHAR(20) NOT NULL COMMENT '十神（如：正官）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_birth_stem` (`day_stem`, `birth_stem`),
    INDEX `idx_day_stem` (`day_stem`),
    INDEX `idx_birth_stem` (`birth_stem`),
    INDEX `idx_shishen` (`shishen`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='十神查询表';

-- 十神象义表（Sheet 2）
CREATE TABLE IF NOT EXISTS `daily_fortune_shishen_meaning` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `shishen` VARCHAR(20) NOT NULL COMMENT '十神（如：正官）',
    `hint` TEXT NOT NULL COMMENT '十神提示',
    `hint_keywords` TEXT NOT NULL COMMENT '十神象义提示词',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_shishen` (`shishen`),
    INDEX `idx_shishen` (`shishen`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='十神象义表';

-- 生肖刑冲破害表
CREATE TABLE IF NOT EXISTS `daily_fortune_zodiac` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_branch` VARCHAR(5) NOT NULL COMMENT '日支（如：辰）',
    `relation_type` VARCHAR(10) NOT NULL COMMENT '关系类型（合/冲/刑/破/害）',
    `target_branch` VARCHAR(5) NOT NULL COMMENT '目标地支（如：戌）',
    `target_zodiac` VARCHAR(10) NOT NULL COMMENT '目标生肖（如：狗）',
    `content` TEXT NOT NULL COMMENT '内容',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_branch_relation` (`day_branch`, `relation_type`, `target_branch`),
    INDEX `idx_day_branch` (`day_branch`),
    INDEX `idx_relation_type` (`relation_type`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生肖刑冲破害表';

-- 建除十二神表
CREATE TABLE IF NOT EXISTS `daily_fortune_jianchu` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `jianchu` VARCHAR(10) NOT NULL COMMENT '建除十二神（如：定）',
    `content` TEXT NOT NULL COMMENT '能量小结显示内容',
    `score` INT DEFAULT NULL COMMENT '分数',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_jianchu` (`jianchu`),
    INDEX `idx_jianchu` (`jianchu`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='建除十二神表';

-- 幸运颜色-万年历方位表
CREATE TABLE IF NOT EXISTS `daily_fortune_lucky_color_wannianli` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `direction` VARCHAR(20) NOT NULL COMMENT '方位（如：西北）',
    `colors` VARCHAR(200) NOT NULL COMMENT '颜色（逗号分隔，如：白色、金色、银色）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_direction` (`direction`),
    INDEX `idx_direction` (`direction`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='幸运颜色-万年历方位表';

-- 幸运颜色-十神表
CREATE TABLE IF NOT EXISTS `daily_fortune_lucky_color_shishen` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `shishen` VARCHAR(20) NOT NULL COMMENT '十神名称（如：正财）',
    `color` VARCHAR(50) NOT NULL COMMENT '颜色（如：黄色）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_shishen` (`shishen`),
    INDEX `idx_shishen` (`shishen`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='幸运颜色-十神表';

-- 贵人之路-十神方位表
CREATE TABLE IF NOT EXISTS `daily_fortune_guiren_direction` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_stem` VARCHAR(5) NOT NULL COMMENT '日干（如：乙）',
    `directions` VARCHAR(200) NOT NULL COMMENT '方位（逗号分隔，如：正北、西南）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_stem` (`day_stem`),
    INDEX `idx_day_stem` (`day_stem`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='贵人之路-十神方位表';

-- 瘟神方位-地支方位表
CREATE TABLE IF NOT EXISTS `daily_fortune_wenshen_direction` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    `day_branch` VARCHAR(5) NOT NULL COMMENT '日支（如：巳）',
    `direction` VARCHAR(20) NOT NULL COMMENT '方位（如：东南）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_day_branch` (`day_branch`),
    INDEX `idx_day_branch` (`day_branch`),
    INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='瘟神方位-地支方位表';

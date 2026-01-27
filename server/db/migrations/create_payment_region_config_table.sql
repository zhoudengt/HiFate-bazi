-- ========================================
-- 支付区域配置表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-22
-- 说明: 配置哪些区域开放/关闭支付功能

USE `hifate_bazi`;

-- ========================================
-- 支付区域配置表
-- ========================================
CREATE TABLE IF NOT EXISTS `payment_region_config` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    `region_code` VARCHAR(10) NOT NULL COMMENT '区域代码（如：HK, TW, CN, US, JP等）',
    `region_name` VARCHAR(100) NOT NULL COMMENT '区域名称（如：香港, 台湾, 大陆, 美国, 日本）',
    `is_open` BOOLEAN DEFAULT 1 COMMENT '是否开放支付：1=开放，0=关闭',
    `description` TEXT COMMENT '描述说明',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 唯一索引
    UNIQUE KEY `uk_region_code` (`region_code`),
    INDEX `idx_is_open` (`is_open`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付区域配置表';

-- ========================================
-- 初始化区域配置数据
-- ========================================
INSERT INTO `payment_region_config` (`region_code`, `region_name`, `is_open`, `description`) VALUES
('HK', '香港', 1, '香港特别行政区 - 开放支付'),
('TW', '台湾', 1, '台湾地区 - 开放支付'),
('CN', '大陆', 0, '中国大陆 - 关闭支付（白名单用户除外）'),
('US', '美国', 1, '美国 - 开放支付'),
('JP', '日本', 1, '日本 - 开放支付'),
('SG', '新加坡', 1, '新加坡 - 开放支付'),
('TH', '泰国', 1, '泰国 - 开放支付'),
('MY', '马来西亚', 1, '马来西亚 - 开放支付'),
('PH', '菲律宾', 1, '菲律宾 - 开放支付'),
('ID', '印尼', 1, '印尼 - 开放支付')
ON DUPLICATE KEY UPDATE
    `region_name` = VALUES(`region_name`),
    `description` = VALUES(`description`);

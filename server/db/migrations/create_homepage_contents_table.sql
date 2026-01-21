-- ========================================
-- 首页内容表 - 数据库表结构
-- ========================================
-- 创建时间: 2026-01-XX
-- 说明: 存储网站首页的图片与文字内容，支持排序和管理

USE `hifate_bazi`;

-- ========================================
-- 首页内容表
-- ========================================
CREATE TABLE IF NOT EXISTS `homepage_contents` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `title` VARCHAR(200) NOT NULL COMMENT '标题（如：AI守护神、八字命理等）',
    `tags` JSON COMMENT '标签列表（JSON数组，如：["科技", "精准"]）',
    `description` TEXT COMMENT '详细描述',
    `image_base64` LONGTEXT COMMENT '图片Base64编码（包含data:image前缀）',
    `sort_order` INT DEFAULT 0 COMMENT '排序字段（数字越小越靠前）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_sort_order` (`sort_order`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_enabled_sort` (`enabled`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='首页内容表';

-- ========================================
-- 表结构说明
-- ========================================
-- title: 内容标题，如"AI守护神"、"八字命理"等
-- tags: JSON数组格式的标签，如["科技", "精准"]、["古籍", "专业"]等
-- description: 详细描述文本，支持长文本
-- image_base64: 图片的Base64编码，包含完整的前缀（如：data:image/jpeg;base64,...）
-- sort_order: 排序字段，数字越小越靠前，用于控制显示顺序
-- enabled: 是否启用，软删除时设置为FALSE

-- 创建五行行业映射表
-- 用于存储五行与行业的映射关系，支持动态配置

CREATE TABLE IF NOT EXISTS `wuxing_industries` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `element` VARCHAR(10) NOT NULL COMMENT '五行：木、火、土、金、水',
    `category` VARCHAR(50) NOT NULL COMMENT '行业类别（如"金融财务类"、"文化教育类"）',
    `industry_name` VARCHAR(100) NOT NULL COMMENT '行业名称（如"银行"、"教师"）',
    `description` TEXT COMMENT '类别描述（如"适合逻辑清晰、决断力强的人"）',
    `priority` INT DEFAULT 100 COMMENT '优先级（用于排序，数字越小优先级越高）',
    `enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用 1:启用 0:禁用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_element` (`element`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_element_enabled` (`element`, `enabled`),
    INDEX `idx_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='五行行业映射表';


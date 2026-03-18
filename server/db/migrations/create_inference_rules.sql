SET NAMES utf8mb4;

-- 八字流式接口推理规则表
-- 所有领域共用一张表，通过 domain 字段区分
-- 创建日期：2026-03-18

CREATE TABLE IF NOT EXISTS `bazi_stream_inference_rules` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `rule_code` VARCHAR(100) UNIQUE NOT NULL COMMENT '规则唯一标识，如 marriage_spouse_star_001',
    `domain` VARCHAR(50) NOT NULL COMMENT '领域：marriage/health/career/wealth/children/wuxing/overall/annual/xishen',
    `category` VARCHAR(50) NOT NULL COMMENT '领域内分类，如 spouse_star/marriage_palace/marriage_timing',
    `rule_name` VARCHAR(200) NOT NULL COMMENT '规则名称（中文）',
    `conditions` JSON NOT NULL COMMENT '匹配条件（JSON对象）',
    `conclusions` JSON NOT NULL COMMENT '推理结论模板（JSON对象）',
    `priority` INT DEFAULT 100 COMMENT '优先级（数字越大越优先）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `source` VARCHAR(200) DEFAULT NULL COMMENT '规则来源（如"子平真诠·论妻"、"滴天髓"）',
    `description` TEXT DEFAULT NULL COMMENT '规则说明',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_domain_category` (`domain`, `category`),
    INDEX `idx_domain_enabled` (`domain`, `enabled`),
    INDEX `idx_priority` (`priority` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='八字流式接口推理规则表';

-- ========================================
-- 配置数据库化 - 数据库表结构
-- ========================================
-- 创建时间: 2024
-- 说明: 支持services.env配置化和input_data格式配置化

USE `hifate_bazi`;

-- ========================================
-- 1. 服务配置表（需求3：services.env配置化）
-- ========================================
CREATE TABLE IF NOT EXISTS `service_configs` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键（如：BAZI_CORE_SERVICE_URL）',
    `config_value` TEXT COMMENT '配置值',
    `config_type` VARCHAR(20) DEFAULT 'string' COMMENT '配置类型：string/int/bool/json',
    `description` TEXT COMMENT '配置描述',
    `category` VARCHAR(50) COMMENT '配置分类：grpc/coze/payment/frontend等',
    `environment` VARCHAR(20) DEFAULT 'production' COMMENT '环境：production/development/staging',
    `version` INT DEFAULT 1 COMMENT '版本号',
    `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_key` (`config_key`),
    INDEX `idx_category` (`category`),
    INDEX `idx_env` (`environment`),
    INDEX `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='服务配置表';

-- ========================================
-- 2. LLM输入格式定义表（需求2：input_data格式配置化）
-- ========================================
CREATE TABLE IF NOT EXISTS `llm_input_formats` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '格式ID',
    `format_name` VARCHAR(100) NOT NULL UNIQUE COMMENT '格式名称（如：fortune_analysis_full）',
    `intent` VARCHAR(50) NOT NULL COMMENT '意图类型（如：wealth/health/career/marriage/general等）',
    `format_type` VARCHAR(50) DEFAULT 'full' COMMENT '格式类型：full/minimal/custom',
    `structure` JSON NOT NULL COMMENT '格式结构定义（JSON格式，定义需要哪些字段）',
    `description` TEXT COMMENT '格式描述',
    `version` VARCHAR(20) DEFAULT 'v1.0' COMMENT '版本号',
    `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_format_name` (`format_name`),
    INDEX `idx_intent` (`intent`),
    INDEX `idx_format_type` (`format_type`),
    INDEX `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM输入数据格式定义表';

-- ========================================
-- 示例数据说明
-- ========================================
-- structure字段JSON格式示例：
-- {
--   "fields": {
--     "intent": {
--       "source": "request_param",
--       "field": "intent"
--     },
--     "question": {
--       "source": "request_param",
--       "field": "question"
--     },
--     "bazi": {
--       "source": "redis",
--       "key_template": "bazi:{solar_date}:{solar_time}:{gender}",
--       "fields": ["pillars", "day_stem"]
--     },
--     "liunian": {
--       "source": "redis",
--       "key_template": "fortune:{solar_date}:{solar_time}:{gender}:liunian",
--       "fields": ["year", "stem", "branch", "stem_element", "branch_element", "stem_shishen", "branch_shishen", "balance_summary", "relation_summary"]
--     },
--     "dayun": {
--       "source": "redis",
--       "key_template": "fortune:{solar_date}:{solar_time}:{gender}:dayun",
--       "fields": ["stem", "branch"]
--     },
--     "xi_ji": {
--       "source": "redis",
--       "key_template": "fortune:{solar_date}:{solar_time}:{gender}:xi_ji",
--       "fields": ["xi_shen", "ji_shen"],
--       "transform": {
--         "xi_shen": "slice:0:5",
--         "ji_shen": "slice:0:5"
--       }
--     },
--     "wangshuai": {
--       "source": "redis",
--       "key_template": "fortune:{solar_date}:{solar_time}:{gender}:wangshuai"
--     },
--     "matched_rules": {
--       "source": "redis",
--       "key_template": "rules:{solar_date}:{solar_time}:{gender}:{intent}",
--       "fields": ["rules_by_intent", "rules_count"]
--     },
--     "language_style": {
--       "source": "static",
--       "value": "通俗易懂，避免专业术语，面向普通用户。用日常语言解释命理概念，如\"正官\"可以说成\"稳定的工作机会\"，\"七杀\"可以说成\"挑战和压力\"。"
--     },
--     "category": {
--       "source": "request_param",
--       "field": "category",
--       "optional": true
--     }
--   }
-- }


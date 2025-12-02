-- 意图识别训练数据表结构
-- 用于记录用户问题，支持模型微调和规则库扩展

USE `hifate_bazi`;

-- 用户问题记录表（核心表）
CREATE TABLE IF NOT EXISTS `intent_user_questions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    `question` TEXT NOT NULL COMMENT '用户问题（原始文本）',
    `user_id` VARCHAR(100) DEFAULT 'anonymous' COMMENT '用户ID',
    `session_id` VARCHAR(100) COMMENT '会话ID',
    `solar_date` VARCHAR(20) COMMENT '出生日期（用于上下文）',
    `solar_time` VARCHAR(20) COMMENT '出生时间（用于上下文）',
    `gender` VARCHAR(10) COMMENT '性别（用于上下文）',
    
    -- 意图识别结果
    `intents` JSON COMMENT '识别到的意图列表（JSON数组）',
    `confidence` DECIMAL(5,4) COMMENT '置信度（0-1）',
    `rule_types` JSON COMMENT '规则类型列表（JSON数组）',
    `time_intent` JSON COMMENT '时间意图（JSON对象）',
    `keywords` JSON COMMENT '提取的关键词（JSON数组）',
    `method` VARCHAR(50) COMMENT '识别方法（local_model/keyword_fallback/llm_fallback）',
    `response_time_ms` INT COMMENT '响应时间（毫秒）',
    
    -- 分类结果
    `is_fortune_related` BOOLEAN DEFAULT TRUE COMMENT '是否与命理相关',
    `is_ambiguous` BOOLEAN DEFAULT FALSE COMMENT '是否模糊',
    `reasoning` TEXT COMMENT '识别理由',
    
    -- 训练标记
    `is_labeled` BOOLEAN DEFAULT FALSE COMMENT '是否已标注（用于训练）',
    `correct_intent` JSON COMMENT '正确意图（人工标注，JSON数组）',
    `correct_time_intent` JSON COMMENT '正确时间意图（人工标注，JSON对象）',
    `labeler_id` VARCHAR(100) COMMENT '标注人ID',
    `labeled_at` TIMESTAMP NULL COMMENT '标注时间',
    
    -- 训练状态
    `training_status` VARCHAR(20) DEFAULT 'pending' COMMENT '训练状态（pending/used/skipped）',
    `training_batch_id` VARCHAR(100) COMMENT '训练批次ID',
    `training_model_version` VARCHAR(50) COMMENT '使用的模型版本',
    
    -- 元数据
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_is_labeled` (`is_labeled`),
    INDEX `idx_training_status` (`training_status`),
    INDEX `idx_method` (`method`),
    INDEX `idx_confidence` (`confidence`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户问题记录表（意图识别训练数据）';

-- 意图分类规则扩展表（基于用户问题自动扩展）
CREATE TABLE IF NOT EXISTS `intent_keyword_rules` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    `keyword` VARCHAR(100) NOT NULL COMMENT '关键词',
    `intent` VARCHAR(50) NOT NULL COMMENT '意图类型',
    `confidence_boost` DECIMAL(5,4) DEFAULT 0.05 COMMENT '置信度加成（0-1）',
    `source` VARCHAR(50) DEFAULT 'auto' COMMENT '来源（auto/manual）',
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    `success_count` INT DEFAULT 0 COMMENT '成功次数（用于评估）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    UNIQUE KEY `uk_keyword_intent` (`keyword`, `intent`),
    INDEX `idx_intent` (`intent`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_usage_count` (`usage_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='意图关键词规则扩展表';

-- 模型训练批次表
CREATE TABLE IF NOT EXISTS `intent_model_training_batches` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '批次ID',
    `batch_id` VARCHAR(100) UNIQUE NOT NULL COMMENT '批次编号',
    `model_version` VARCHAR(50) NOT NULL COMMENT '模型版本',
    `description` TEXT COMMENT '批次描述',
    `question_count` INT DEFAULT 0 COMMENT '问题数量',
    `labeled_count` INT DEFAULT 0 COMMENT '已标注数量',
    `training_status` VARCHAR(20) DEFAULT 'pending' COMMENT '训练状态（pending/training/completed/failed）',
    `training_start_time` TIMESTAMP NULL COMMENT '训练开始时间',
    `training_end_time` TIMESTAMP NULL COMMENT '训练结束时间',
    `training_duration_sec` INT COMMENT '训练耗时（秒）',
    `model_accuracy` DECIMAL(5,4) COMMENT '模型准确率（0-1）',
    `model_path` VARCHAR(500) COMMENT '模型保存路径',
    `training_log` TEXT COMMENT '训练日志',
    `error_message` TEXT COMMENT '错误信息',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_batch_id` (`batch_id`),
    INDEX `idx_training_status` (`training_status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型训练批次表';

-- 模型版本管理表
CREATE TABLE IF NOT EXISTS `intent_model_versions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '版本ID',
    `version` VARCHAR(50) UNIQUE NOT NULL COMMENT '版本号',
    `model_name` VARCHAR(200) NOT NULL COMMENT '模型名称',
    `model_path` VARCHAR(500) NOT NULL COMMENT '模型路径',
    `base_model` VARCHAR(200) COMMENT '基础模型',
    `training_batch_id` VARCHAR(100) COMMENT '训练批次ID',
    `question_count` INT DEFAULT 0 COMMENT '训练问题数量',
    `accuracy` DECIMAL(5,4) COMMENT '准确率',
    `is_active` BOOLEAN DEFAULT FALSE COMMENT '是否激活',
    `deployed_at` TIMESTAMP NULL COMMENT '部署时间',
    `description` TEXT COMMENT '版本描述',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_version` (`version`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型版本管理表';


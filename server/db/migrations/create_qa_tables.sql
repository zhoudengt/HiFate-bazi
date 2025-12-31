-- ============================================
-- QA 多轮对话系统数据库表
-- 创建时间: 2025-01-XX
-- 描述: 创建问答系统相关表
-- ============================================

USE `hifate_bazi`;

-- 问题模板表
CREATE TABLE IF NOT EXISTS `qa_question_templates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '问题ID',
    `category` VARCHAR(50) NOT NULL COMMENT '分类：initial/career_wealth/marriage/health/children/liunian/yearly_report',
    `question_text` TEXT NOT NULL COMMENT '问题文本',
    `question_type` VARCHAR(20) DEFAULT 'user_selectable' COMMENT '问题类型：user_selectable/generated',
    `priority` INT DEFAULT 100 COMMENT '优先级',
    `enabled` TINYINT DEFAULT 1 COMMENT '是否启用',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_category` (`category`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问题模板表';

-- 对话会话表
CREATE TABLE IF NOT EXISTS `qa_conversation_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '会话ID',
    `user_id` VARCHAR(100) COMMENT '用户ID',
    `session_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '会话ID（唯一标识）',
    `solar_date` VARCHAR(20) COMMENT '出生日期',
    `solar_time` VARCHAR(10) COMMENT '出生时间',
    `gender` VARCHAR(10) COMMENT '性别',
    `current_category` VARCHAR(50) COMMENT '当前分类',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

-- 对话历史表
CREATE TABLE IF NOT EXISTS `qa_conversation_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '历史记录ID',
    `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID',
    `turn_number` INT NOT NULL COMMENT '对话轮次（从1开始）',
    `question` TEXT NOT NULL COMMENT '用户问题',
    `answer` TEXT COMMENT 'Coze生成的答案',
    `generated_questions_before` JSON COMMENT '提问后生成的问题（JSON数组）',
    `generated_questions_after` JSON COMMENT '答案生成后生成的问题（JSON数组）',
    `intent_result` JSON COMMENT '意图识别结果（完整JSON）',
    `category` VARCHAR(50) COMMENT '问题分类',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_turn_number` (`session_id`, `turn_number`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`session_id`) REFERENCES `qa_conversation_sessions`(`session_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';


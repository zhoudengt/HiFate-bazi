-- ========================================
-- 消息评价表
-- ========================================
-- 创建时间: 2026-03-10
-- 说明: 记录用户对流式 AI 消息的赞/踩评价
-- 用途: 收集用户反馈，用于 LLM 微调训练数据

USE `hifate_bazi`;

CREATE TABLE IF NOT EXISTS `message_feedback` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    `request_id` VARCHAR(36) NOT NULL COMMENT '关联 stream_api_call_logs.request_id',
    `rating` VARCHAR(10) NOT NULL COMMENT '评价类型: up(赞) | down(踩)',
    `comment` TEXT COMMENT '用户补充说明（踩时可选填写原因）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    UNIQUE INDEX `uk_request_id` (`request_id`),
    INDEX `idx_rating` (`rating`),
    INDEX `idx_created_at` (`created_at`),
    CONSTRAINT `fk_feedback_request_id`
        FOREIGN KEY (`request_id`) REFERENCES `stream_api_call_logs` (`request_id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息评价表';

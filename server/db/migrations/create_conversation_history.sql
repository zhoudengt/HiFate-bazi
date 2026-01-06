-- AI问答对话历史表
-- 用于记录多轮对话历史，支持数据分析和审计

USE `hifate_bazi`;

-- 对话历史记录表
CREATE TABLE IF NOT EXISTS `ai_conversation_history` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    `user_id` VARCHAR(100) NOT NULL COMMENT '用户ID',
    `conversation_id` VARCHAR(100) COMMENT 'Coze对话ID',
    `session_id` VARCHAR(100) COMMENT '会话ID（同一次八字计算的会话）',
    `category` VARCHAR(50) COMMENT '分类（婚姻/事业财富/健康等）',
    `question` TEXT NOT NULL COMMENT '用户问题（原始文本）',
    `answer` MEDIUMTEXT COMMENT 'LLM回答（完整文本）',
    `intent` VARCHAR(50) COMMENT '识别的意图（marriage/wealth/health等）',
    `keywords` JSON COMMENT '提取的关键词（JSON数组，3-5个）',
    `summary` VARCHAR(500) COMMENT '问答摘要（压缩版，一句话<100字）',
    `bazi_summary` VARCHAR(200) COMMENT '八字摘要（如：己巳、丁丑、庚辰、壬午）',
    `round_number` INT DEFAULT 1 COMMENT '对话轮次（同一session内的第几轮）',
    `response_time_ms` INT COMMENT '响应时间（毫秒）',
    `token_count` INT COMMENT 'Token消耗数量（可选）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_user_session` (`user_id`, `session_id`),
    INDEX `idx_conversation_id` (`conversation_id`),
    INDEX `idx_category` (`category`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_round_number` (`round_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI问答对话历史表';

-- 添加注释说明数据流向
-- 数据来源：
--   1. 场景1（首次对话）：保存简短答复
--   2. 场景2（追问）：保存详细回答
-- 数据用途：
--   1. 构建历史上下文（最近5轮的keywords+summary）传递给LLM
--   2. 数据分析和用户行为追踪
--   3. 审计和问题排查


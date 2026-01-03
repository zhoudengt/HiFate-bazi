-- 用户交互数据存储系统 - MySQL表结构
-- 用于记录用户功能使用、输入输出、性能指标等数据

USE `hifate_bazi`;

-- 功能使用记录表（核心表）
CREATE TABLE IF NOT EXISTS `function_usage_records` (
  `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
  `record_id` VARCHAR(100) UNIQUE NOT NULL COMMENT '记录ID（UUID）',
  `user_id` VARCHAR(100) DEFAULT 'anonymous' COMMENT '用户ID',
  `session_id` VARCHAR(100) COMMENT '会话ID（多轮对话）',
  `function_type` VARCHAR(50) NOT NULL COMMENT '功能类型：marriage/wealth/children/health/general/chat',
  `function_name` VARCHAR(100) COMMENT '功能名称：八字命理-感情婚姻/事业财富/子女学习/身体健康/总评分析/AI问答',
  `frontend_api` VARCHAR(200) NOT NULL COMMENT '前端调用的接口（如 /api/v1/bazi/marriage-analysis/stream）',
  `llm_api` VARCHAR(200) COMMENT '给大模型数据的接口（如 Coze API endpoint）',
  `round_number` INT DEFAULT 1 COMMENT '轮次（多轮对话时递增）',
  
  -- 输入输出摘要（用于快速查询）
  `frontend_input_summary` TEXT COMMENT '前端功能输入摘要（前500字符）',
  `input_data_summary` TEXT COMMENT 'input_data摘要（前500字符）',
  `llm_output_summary` TEXT COMMENT '大模型输出摘要（前500字符）',
  
  -- MongoDB关联
  `mongo_doc_id` VARCHAR(100) COMMENT 'MongoDB文档ID（关联详细数据）',
  
  -- 性能指标
  `api_response_time_ms` INT COMMENT '接口总响应时间（毫秒）',
  `llm_first_token_time_ms` INT COMMENT '大模型第一个token响应时间（毫秒）',
  `llm_total_time_ms` INT COMMENT '大模型总响应时间（毫秒）',
  `token_count` INT COMMENT 'Token使用量',
  
  -- 模型信息
  `model_name` VARCHAR(100) COMMENT '使用的模型名称',
  `model_version` VARCHAR(50) COMMENT '模型版本',
  `bot_id` VARCHAR(100) COMMENT 'Coze Bot ID',
  
  -- 状态
  `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态：success/failed/partial',
  `error_message` TEXT COMMENT '错误信息（如果有）',
  
  -- 时间戳
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  -- 索引
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_function_type` (`function_type`),
  INDEX `idx_session_id` (`session_id`),
  INDEX `idx_created_at` (`created_at`),
  INDEX `idx_record_id` (`record_id`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='功能使用记录表';


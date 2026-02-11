-- ========================================
-- 流式接口调用记录表
-- ========================================
-- 创建时间: 2026-02-11
-- 说明: 记录所有流式接口调用，包括用户入参、给大模型的参数、大模型返回内容、各阶段耗时
-- 用途: 数据分析、问题争端追溯

USE `hifate_bazi`;

CREATE TABLE IF NOT EXISTS `stream_api_call_logs` (
    -- 标识与路由
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    `trace_id` VARCHAR(100) NOT NULL COMMENT '请求追踪 ID（UUID）',
    `function_type` VARCHAR(50) NOT NULL COMMENT '场景类型：marriage/wealth/children/health/general/desk_fengshui/face 等',
    `frontend_api` VARCHAR(200) NOT NULL COMMENT '前端调用的端点路径',
    `bot_id` VARCHAR(100) COMMENT '使用的大模型 Bot ID',
    `llm_platform` VARCHAR(50) COMMENT '大模型平台：coze / bailian',

    -- 数据内容（核心 3 字段）
    `frontend_input` JSON COMMENT '用户入参：solar_date、solar_time、gender、calendar_type、location 等',
    `input_data` MEDIUMTEXT COMMENT '给大模型的结构化八字数据（基于生辰计算的结果，JSON 字符串）',
    `llm_output` MEDIUMTEXT COMMENT '大模型完整返回内容（用于争端追溯）',

    -- 耗时（4 字段，单位：毫秒）
    `api_total_ms` INT COMMENT '接口总耗时（从请求开始到 SSE 推送完成）',
    `input_data_gen_ms` INT COMMENT '数据编排 + 格式化耗时',
    `llm_first_token_ms` INT COMMENT '大模型首 token 耗时（从发起调用到收到第一个 token）',
    `llm_total_ms` INT COMMENT '大模型总耗时（从发起调用到 complete 事件）',

    -- 状态与错误
    `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态：success / failed / cache_hit',
    `error_message` TEXT COMMENT '错误详情（失败时记录）',
    `cache_hit` TINYINT(1) DEFAULT 0 COMMENT '是否命中 LLM 缓存（1=命中，跳过大模型调用）',

    -- 元数据
    `input_data_size` INT COMMENT 'input_data 字节大小（用于分析）',
    `llm_output_size` INT COMMENT 'llm_output 字节大小（用于分析）',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    -- 索引
    UNIQUE INDEX `uk_trace_id` (`trace_id`),
    INDEX `idx_function_type` (`function_type`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_status` (`status`),
    INDEX `idx_bot_id` (`bot_id`),
    INDEX `idx_function_created` (`function_type`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流式接口调用记录表';

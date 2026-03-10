-- ========================================
-- stream_api_call_logs 增加 request_id 列
-- ========================================
-- 创建时间: 2026-03-10
-- 说明: 为流式消息评价功能增加 request_id，供前端评价引用
-- 用途: 关联 message_feedback 表

USE `hifate_bazi`;

ALTER TABLE `stream_api_call_logs`
  ADD COLUMN `request_id` VARCHAR(36) DEFAULT NULL COMMENT '请求唯一ID，供前端评价引用（UUID）';

CREATE UNIQUE INDEX `uk_request_id` ON `stream_api_call_logs` (`request_id`);

-- ========================================
-- message_feedback 增加 email、name 列
-- ========================================
-- 创建时间: 2026-03-10
-- 说明: 记录提交评价的用户身份（前端传入）
-- 用途: 关联用户反馈与身份，便于 LLM 微调数据筛选

USE `hifate_bazi`;

ALTER TABLE `message_feedback`
  ADD COLUMN `email` VARCHAR(100) DEFAULT NULL COMMENT '用户邮箱（前端传入）',
  ADD COLUMN `name`  VARCHAR(50)  DEFAULT NULL COMMENT '用户名称（前端传入）';

CREATE INDEX `idx_email` ON `message_feedback` (`email`);

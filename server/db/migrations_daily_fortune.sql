-- 每日运势数据库迁移脚本
-- 用于向后兼容，添加新列和新表

USE `hifate_bazi`;

-- 1. 为 daily_fortune_jianchu 表添加 score 列（如果不存在）
ALTER TABLE `daily_fortune_jianchu` 
ADD COLUMN IF NOT EXISTS `score` INT DEFAULT NULL COMMENT '分数' AFTER `content`;

-- 注意：MySQL 5.7 不支持 IF NOT EXISTS，如果报错请手动检查列是否存在
-- 如果列已存在，可以忽略错误


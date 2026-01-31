-- 性能优化：规则匹配与日柱内容查询的复合索引
-- 执行前请确认数据库为 hifate_bazi；若索引已存在会报错，可忽略或先 DROP INDEX 再执行

USE `hifate_bazi`;

-- 规则匹配查询（按类型、启用、优先级）高频场景
ALTER TABLE `bazi_rules`
ADD INDEX `idx_type_enabled_priority` (`rule_type`, `enabled`, `priority`);

-- 日柱性别内容查询（按日柱、性别、启用）
ALTER TABLE `rizhu_gender_contents`
ADD INDEX `idx_rizhu_gender_enabled` (`rizhu`, `gender`, `enabled`);

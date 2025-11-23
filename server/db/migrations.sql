-- 向后兼容的元数据列（若不存在则添加）
USE `hifate_bazi`;

-- 逐条添加列；若已存在将报错，调用方会忽略对应错误并继续
ALTER TABLE `bazi_rules` ADD COLUMN `confidence_prior` DECIMAL(5,4) NULL COMMENT '先验置信度(0-1)' AFTER `priority`;
ALTER TABLE `bazi_rules` ADD COLUMN `mutually_exclusive_group` VARCHAR(100) NULL COMMENT '互斥组' AFTER `confidence_prior`;
ALTER TABLE `bazi_rules` ADD COLUMN `contradicts` JSON NULL COMMENT '矛盾规则ID列表' AFTER `mutually_exclusive_group`;
ALTER TABLE `bazi_rules` ADD COLUMN `tags` JSON NULL COMMENT '主题标签列表' AFTER `contradicts`;
ALTER TABLE `bazi_rules` ADD COLUMN `segment_weights` JSON NULL COMMENT '人群分段权重' AFTER `tags`;
ALTER TABLE `bazi_rules` ADD COLUMN `biz_impact_weight` DECIMAL(6,3) NULL COMMENT '业务权重' AFTER `segment_weights`;
ALTER TABLE `bazi_rules` ADD COLUMN `history_score` DECIMAL(5,4) NULL COMMENT '历史效果分(0-1)' AFTER `biz_impact_weight`;
ALTER TABLE `bazi_rules` ADD COLUMN `nlg_template_ids` JSON NULL COMMENT '可用NLG模板ID' AFTER `history_score`;



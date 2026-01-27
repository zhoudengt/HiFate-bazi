-- 数据库回滚脚本
-- 生成时间: 2026-01-27 12:57:16
-- 部署ID: 20260127_125716

START TRANSACTION;

-- ==================== 恢复删除的字段 ====================
-- ⚠️  注意：此操作会重新添加被删除的字段，但数据无法恢复
-- 恢复表 ai_conversation_history 的字段 scenario_type
ALTER TABLE `ai_conversation_history` ADD COLUMN `scenario_type` varchar(20) NULL DEFAULT scenario2  COMMENT 'åœºæ™¯ç±»åž‹ï¼šscenario1=é€‰æ‹©é¡¹, scenario2=é—®ç­”';

-- ==================== 恢复删除的表 ====================
-- ⚠️  注意：此操作会重新创建被删除的表，但数据无法恢复（需要从备份恢复）
-- 恢复表: service_configs_260127
-- ⚠️  警告：表结构可以恢复，但数据需要从备份恢复
-- 如果之前有备份，请使用：mysql -u root -p database_name < backup_service_configs_260127.sql

-- ==================== 删除新增表 ====================
DROP TABLE IF EXISTS `payment_transactions`;

DROP TABLE IF EXISTS `payment_api_call_logs`;

DROP TABLE IF EXISTS `payment_region_config`;

DROP TABLE IF EXISTS `payment_whitelist`;

DROP TABLE IF EXISTS `conversion_fee_history`;

DROP TABLE IF EXISTS `fx_rate_history`;

COMMIT;

-- 回滚完成
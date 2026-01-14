-- 添加 scenario_type 字段到 ai_conversation_history 表
-- 用于区分场景1（选择项）和场景2（问答）的对话记录
-- 创建时间: 2026-01-14

USE `hifate_bazi`;

-- 添加 scenario_type 字段
ALTER TABLE ai_conversation_history 
ADD COLUMN IF NOT EXISTS scenario_type VARCHAR(20) DEFAULT 'scenario2' 
COMMENT '场景类型：scenario1=选择项, scenario2=问答' 
AFTER category;

-- 添加索引以便按场景类型查询
CREATE INDEX IF NOT EXISTS idx_scenario_type ON ai_conversation_history(scenario_type);

-- 验证字段是否添加成功
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'hifate_bazi' 
  AND TABLE_NAME = 'ai_conversation_history' 
  AND COLUMN_NAME = 'scenario_type';

-- 修复子女学习分析格式定义问题
-- 问题：格式定义产生的数据结构与硬编码函数不匹配，导致验证失败
-- 解决方案：禁用格式定义，让系统总是使用硬编码函数 build_children_study_input_data

-- 1. 禁用子女学习分析格式定义
UPDATE input_data_formats 
SET is_active = 0,
    updated_at = NOW()
WHERE format_name = 'children_study_analysis';

-- 2. 同时禁用 llm_input_formats 表中的记录（如果存在）
UPDATE llm_input_formats 
SET is_active = 0,
    updated_at = NOW()
WHERE format_name = 'children_study_analysis';

-- 验证修改结果
SELECT 'input_data_formats' as table_name, format_name, is_active, updated_at
FROM input_data_formats 
WHERE format_name = 'children_study_analysis'
UNION ALL
SELECT 'llm_input_formats' as table_name, format_name, is_active, updated_at
FROM llm_input_formats 
WHERE format_name = 'children_study_analysis';

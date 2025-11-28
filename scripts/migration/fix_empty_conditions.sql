USE hifate_bazi;

-- 修复conditions字段为空的问题
-- 给这些规则设置一个非空的conditions值

UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_20043';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_20047';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_20049';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_20050';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70007';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70008';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70009';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70010';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70011';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70012';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70013';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70014';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70015';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70016';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70017';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70018';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70019';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70020';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70021';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70032';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70033';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70034';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70035';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70036';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70037';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70038';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70039';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70040';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70041';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70042';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70043';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70044';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70045';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70046';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70047';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70048';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70049';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70050';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70051';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70052';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70053';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70054';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70055';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70056';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70057';
UPDATE bazi_rules SET conditions = '{"all": [{"always": true}]}', updated_at = NOW() WHERE rule_code = 'FORMULA_70058';

UPDATE rule_version SET rule_version = rule_version + 1, updated_at = NOW();

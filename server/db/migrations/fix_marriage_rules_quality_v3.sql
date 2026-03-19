SET NAMES utf8mb4;

-- ═══ 1. 删除空条件的 timing 规则（与代码 _infer_marriage_timing() 重复且质量更差）═══
DELETE FROM bazi_stream_inference_rules
WHERE rule_code IN ('marriage_tm_001','marriage_tm_002','marriage_tm_003','marriage_tm_004','marriage_tm_005','marriage_tm_006','marriage_tm_007');

-- ═══ 2. 修正 spouse_star_early 规则描述歧义 ═══
-- marriage_tg_004: "偏财在年月透出" → "配偶星在年柱或月柱出现"
UPDATE bazi_stream_inference_rules
SET rule_name = '男命财星早现——早恋倾向',
    conclusions = JSON_SET(
        conclusions,
        '$.causal_chain', '男命 + 配偶星（财星）在年柱或月柱出现 → 财星早现 → 早年情缘旺 → 易早恋'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE rule_code = 'marriage_tg_004';

-- marriage_tg_005: "官杀在年月" → "配偶星在年柱或月柱出现"
UPDATE bazi_stream_inference_rules
SET rule_name = '女命官杀早现——婚姻较早',
    conclusions = JSON_SET(
        conclusions,
        '$.causal_chain', '女命 + 配偶星（官杀）在年柱或月柱出现 → 夫星早现 → 婚缘来得早 → 宜把握'
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE rule_code = 'marriage_tg_005';

-- ═══ 3. 新增害关系规则 ═══
INSERT INTO bazi_stream_inference_rules (rule_code, domain, category, rule_name, conditions, conclusions, priority, source, description) VALUES
('marriage_mp_012', 'marriage', 'marriage_palace', '婚姻宫逢害——暗伤感情',
 '{"marriage_palace_hai": true}',
 '{"spouse_character":"婚姻中有隐性伤害，表面平静但内心积怨，容易因误会、猜忌导致感情裂痕","marriage_quality":"需注意","causal_chain":"婚姻宫被害 → 暗中受损 → 表面和谐实则暗流 → 需主动沟通化解","confidence":0.78}',
 200, '命理通则', '日支被其他柱地支所害，婚姻有暗伤'),

('marriage_bc_010', 'marriage', 'branch_combo', '酉戌相害——月令害婚宫',
 '{"branch_hai": "month_day"}',
 '{"conclusion":"月令（社会环境/事业）与婚姻宫相害，工作压力侵蚀家庭关系，事业越忙感情越疏","causal_chain":"月支酉害日支戌 → 事业环境克制婚姻宫 → 工作与家庭难两全 → 需刻意平衡","confidence":0.76}',
 180, '渊海子平·论害', '月支害日支，事业影响婚姻'),

('marriage_bc_011', 'marriage', 'branch_combo', '子未相害——年害婚宫',
 '{"branch_hai": "year_day"}',
 '{"conclusion":"年支与婚姻宫相害，家族长辈或原生家庭因素对婚姻有负面影响","causal_chain":"年支害日支 → 原生家庭干扰 → 长辈介入婚事 → 需独立抉择","confidence":0.74}',
 170, '渊海子平·论害', '年支害日支，原生家庭影响婚姻'),

('marriage_bc_012', 'marriage', 'branch_combo', '时支害婚宫——晚年孤寂',
 '{"branch_hai": "hour_day"}',
 '{"conclusion":"时支与婚姻宫相害，晚年夫妻感情可能渐行渐远，子女因素也可能影响婚姻和谐","causal_chain":"时支害日支 → 子女宫害婚姻宫 → 晚年感情消磨 → 宜早培养共同爱好","confidence":0.72}',
 160, '渊海子平·论害', '时支害日支，晚年婚姻受影响')

ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    conditions = VALUES(conditions),
    conclusions = VALUES(conclusions),
    priority = VALUES(priority),
    source = VALUES(source),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

SET NAMES utf8mb4;

-- fix_marriage_rules_quality_v4.sql
-- 修正 marriage_ss_015: 条件从 spouse_star_count_min 改为 piancai_count_min，精确匹配偏财数量

UPDATE bazi_stream_inference_rules
SET conditions = JSON_SET(
    JSON_REMOVE(conditions, '$.spouse_star_count_min'),
    '$.piancai_count_min', 3
),
conclusions = JSON_SET(
    conclusions,
    '$.causal_chain', '男命 + 偏财3个以上 → 偏财过旺 → 情缘分散 → 婚姻易生变'
)
WHERE rule_code = 'marriage_ss_015';

-- 新增: 男命正财过多规则（对称补充）
INSERT INTO bazi_stream_inference_rules
    (rule_code, domain, category, rule_name, conditions, conclusions, priority, source, description)
VALUES
    ('marriage_ss_016', 'marriage', 'spouse_star', '男命多正财——婚恋选择多',
     '{"gender":"male","spouse_star_type":"正财","zhengcai_count_min":3}',
     '{"conclusion":"正财过多，对婚恋对象选择面广，容易犹豫不决，适合晚婚以沉淀心性","marriage_quality":"需沉淀","causal_chain":"男命 + 正财3个以上 → 正财过旺 → 选择多犹豫 → 宜晚婚","confidence":0.72}',
     180, '子平真诠·论妻', '正财过多，选择犹豫')
ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    conditions = VALUES(conditions),
    conclusions = VALUES(conclusions),
    priority = VALUES(priority);

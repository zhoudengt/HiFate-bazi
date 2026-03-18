SET NAMES utf8mb4;

-- 婚姻领域推理规则种子数据
-- 来源：子平真诠、滴天髓、三命通会等公认命理经典
-- 创建日期：2026-03-18

INSERT INTO bazi_stream_inference_rules (rule_code, domain, category, rule_name, conditions, conclusions, priority, source, description) VALUES

-- ═══════════════════════════════════════════════
-- 配偶星规则 (spouse_star)
-- ═══════════════════════════════════════════════

('marriage_ss_001', 'marriage', 'spouse_star', '男命正财为喜且有力——妻贤家稳',
 '{"gender":"male","spouse_star_type":"正财","spouse_star_is_xi":true}',
 '{"spouse_character":"妻子务实能干、善于理财持家、性格稳重贤淑","marriage_quality":"稳定","causal_chain":"男命 + 正财为喜用神 → 妻子是命中贵助 → 婚姻根基稳固","confidence":0.85}',
 200, '子平真诠·论妻', '正财为喜用，主妻贤良助夫'),

('marriage_ss_002', 'marriage', 'spouse_star', '男命正财为忌——夫妻多磨合',
 '{"gender":"male","spouse_star_type":"正财","spouse_star_is_xi":false}',
 '{"spouse_character":"妻子性格保守、过于计较细节、有时让人感到压力","marriage_quality":"需磨合","causal_chain":"男命 + 正财为忌神 → 妻子带来一定压力 → 需要更多包容沟通","confidence":0.75}',
 180, '子平真诠·论妻', '正财为忌，主婚姻需磨合'),

('marriage_ss_003', 'marriage', 'spouse_star', '男命偏财为喜——妻子大方豪爽',
 '{"gender":"male","spouse_star_type":"偏财","spouse_star_is_xi":true}',
 '{"spouse_character":"妻子大方豪爽、社交能力强、性格开朗外向","marriage_quality":"活泼","causal_chain":"男命 + 偏财为喜用 → 妻子性格大方有魅力 → 婚姻生活丰富多彩","confidence":0.80}',
 180, '子平真诠·论妻', '偏财为喜，主妻子开朗大方'),

('marriage_ss_004', 'marriage', 'spouse_star', '男命偏财为忌——感情不够专注',
 '{"gender":"male","spouse_star_type":"偏财","spouse_star_is_xi":false}',
 '{"spouse_character":"花销较大、不够安定、感情上可能不够专一","marriage_quality":"需注意","causal_chain":"男命 + 偏财为忌 → 妻子或自身感情易分心 → 需专注经营","confidence":0.70}',
 160, '子平真诠·论妻', '偏财为忌，主感情波动'),

('marriage_ss_005', 'marriage', 'spouse_star', '女命正官为喜——夫君正派可靠',
 '{"gender":"female","spouse_star_type":"正官","spouse_star_is_xi":true}',
 '{"spouse_character":"丈夫正派可靠、有事业心、顾家负责，为人正直","marriage_quality":"稳固","causal_chain":"女命 + 正官为喜用 → 丈夫是命中贵人 → 婚姻美满安稳","confidence":0.85}',
 200, '子平真诠·论夫', '正官为喜，主夫贤良'),

('marriage_ss_006', 'marriage', 'spouse_star', '女命正官为忌——丈夫管束过多',
 '{"gender":"female","spouse_star_type":"正官","spouse_star_is_xi":false}',
 '{"spouse_character":"丈夫过于严肃、给人压力大、管束较多","marriage_quality":"有压力","causal_chain":"女命 + 正官为忌 → 丈夫带来约束压力 → 需学会表达自己需求","confidence":0.75}',
 180, '子平真诠·论夫', '正官为忌，主夫妻有压力'),

('marriage_ss_007', 'marriage', 'spouse_star', '女命七杀为喜——丈夫有魄力担当',
 '{"gender":"female","spouse_star_type":"七杀","spouse_star_is_xi":true}',
 '{"spouse_character":"丈夫有魄力担当、能力强、有保护欲，做事果断","marriage_quality":"有力量","causal_chain":"女命 + 七杀为喜用 → 丈夫能力强 → 虽有压力但终获助力","confidence":0.80}',
 180, '滴天髓·论官杀', '七杀为喜，主夫有魄力'),

('marriage_ss_008', 'marriage', 'spouse_star', '女命七杀为忌——感情波折多',
 '{"gender":"female","spouse_star_type":"七杀","spouse_star_is_xi":false}',
 '{"spouse_character":"丈夫脾气急躁、控制欲强，婚姻过程中多摩擦","marriage_quality":"波折","causal_chain":"女命 + 七杀为忌 → 丈夫带来较大压力 → 感情需经历考验","confidence":0.75}',
 160, '滴天髓·论官杀', '七杀为忌，主感情波折'),

('marriage_ss_009', 'marriage', 'spouse_star', '男命身强财旺为喜——能担财得贤妻',
 '{"gender":"male","wangshuai":"身强","spouse_star_is_xi":true}',
 '{"conclusion":"身强能担财，妻星为喜用神，主婚姻幸福、妻子能力强且与自己互补。有利于早婚或适婚年龄结婚","confidence":0.85}',
 190, '三命通会', '身强担财，主婚姻美满'),

('marriage_ss_010', 'marriage', 'spouse_star', '男命身弱财旺为忌——担不起财易婚变',
 '{"gender":"male","wangshuai":"身弱","spouse_star_is_xi":false}',
 '{"conclusion":"身弱不担财，妻星为忌反成负担。婚姻中容易因经济或能力差距产生矛盾，建议走印比大运再结婚更稳","confidence":0.80}',
 190, '三命通会', '身弱不担财，婚姻需时机'),

('marriage_ss_011', 'marriage', 'spouse_star', '女命身强官弱——需强势丈夫方匹配',
 '{"gender":"female","wangshuai":"身强","spouse_star_strength":"weak"}',
 '{"conclusion":"身强官弱，丈夫力量不足以制约自己，婚姻中容易居主导地位。需找能力与自己匹配或更强的配偶","confidence":0.75}',
 170, '子平真诠·论夫', '身强官弱，主女命强势'),

('marriage_ss_012', 'marriage', 'spouse_star', '女命身弱官旺——压力大但遇强夫',
 '{"gender":"female","wangshuai":"身弱","spouse_star_is_xi":false}',
 '{"conclusion":"身弱官杀旺，丈夫能力强但带来很大压力。需要印星化杀来转化压力为助力，在感情中学会借力而不是硬扛","confidence":0.80}',
 170, '滴天髓', '身弱官旺，需印星化杀'),

-- ═══════════════════════════════════════════════
-- 婚姻宫规则 (marriage_palace)
-- ═══════════════════════════════════════════════

('marriage_mp_001', 'marriage', 'marriage_palace', '婚姻宫逢桃花——配偶有魅力',
 '{"has_deity":"桃花"}',
 '{"conclusion":"日支或命局中带桃花，配偶外貌出众或气质吸引人，异性缘佳。婚前桃花多，婚后宜收心经营","confidence":0.75}',
 160, '三命通会·论桃花', '桃花入宫，主配偶有魅力'),

('marriage_mp_002', 'marriage', 'marriage_palace', '命带红鸾天喜——婚恋吉兆',
 '{"has_deity":"红鸾"}',
 '{"conclusion":"红鸾星动主婚恋喜庆，遇到红鸾或天喜流年时，缘分容易出现，是婚恋的黄金时段","confidence":0.75}',
 160, '三命通会·论神煞', '红鸾天喜，主婚恋吉兆'),

('marriage_mp_003', 'marriage', 'marriage_palace', '命带天喜——喜事临门',
 '{"has_deity":"天喜"}',
 '{"conclusion":"天喜星主喜庆之事，与感情相关时，利于恋爱结婚。流年逢天喜时机尤佳","confidence":0.70}',
 150, '三命通会·论神煞', '天喜星动，主喜事'),

('marriage_mp_004', 'marriage', 'marriage_palace', '命带孤辰——感情较孤独',
 '{"has_deity":"孤辰"}',
 '{"conclusion":"孤辰入命，性格中有独处倾向，感情上不太主动。建议多参加社交活动，主动创造缘分","confidence":0.65}',
 140, '三命通会·论神煞', '孤辰主孤独'),

('marriage_mp_005', 'marriage', 'marriage_palace', '命带寡宿——婚恋宜晚',
 '{"has_deity":"寡宿"}',
 '{"conclusion":"寡宿入命，内心世界丰富但不善表达感情。婚恋宜晚不宜早，成熟后更懂得经营关系","confidence":0.65}',
 140, '三命通会·论神煞', '寡宿主晚婚'),

('marriage_mp_006', 'marriage', 'marriage_palace', '命带华盖——配偶有内涵',
 '{"has_deity":"华盖"}',
 '{"conclusion":"华盖主聪明清高、有艺术或宗教气质。配偶可能是知性型，有独特的精神世界和追求","confidence":0.65}',
 140, '三命通会·论神煞', '华盖主配偶知性'),

('marriage_mp_007', 'marriage', 'marriage_palace', '命带天乙贵人——婚恋有贵人助',
 '{"has_deity":"天乙贵人"}',
 '{"conclusion":"天乙贵人入命，感情中容易遇到贵人牵线搭桥，逢凶化吉。相亲或他人介绍的缘分值得重视","confidence":0.70}',
 150, '三命通会·论神煞', '天乙贵人助婚恋'),

('marriage_mp_008', 'marriage', 'marriage_palace', '命带驿马——配偶来自远方',
 '{"has_deity":"驿马"}',
 '{"conclusion":"驿马主奔波变动，配偶可能来自外地或异乡。感情中动中求缘，出差、旅行、异地都是结缘机会","confidence":0.65}',
 140, '三命通会·论神煞', '驿马主远方缘分'),

-- ═══════════════════════════════════════════════
-- 配偶星与婚姻宫交互规则 (spouse_interaction)
-- ═══════════════════════════════════════════════

('marriage_si_001', 'marriage', 'spouse_interaction', '男命财星坐日支——妻星入宫最佳',
 '{"gender":"male","spouse_star_type":"正财","spouse_star_is_xi":true}',
 '{"conclusion":"正财坐婚姻宫，妻星归位，是最理想的婚姻配置。妻子贤良助夫，夫妻感情深厚","causal_chain":"男命 + 正财坐日支 + 为喜用 → 妻星归宫 → 婚姻上佳","confidence":0.90}',
 220, '子平真诠·论妻', '财星坐宫，妻贤良'),

('marriage_si_002', 'marriage', 'spouse_interaction', '女命官星坐日支——夫星入宫',
 '{"gender":"female","spouse_star_type":"正官","spouse_star_is_xi":true}',
 '{"conclusion":"正官坐婚姻宫，夫星归位，丈夫正派可靠，婚姻安稳幸福。是女命中较好的婚姻格局","causal_chain":"女命 + 正官坐日支 + 为喜用 → 夫星归宫 → 婚姻美满","confidence":0.90}',
 220, '子平真诠·论夫', '官星坐宫，夫贤良'),

-- ═══════════════════════════════════════════════
-- 婚恋时机规则 (marriage_timing)
-- ═══════════════════════════════════════════════

('marriage_mt_001', 'marriage', 'marriage_timing', '大运引动财星——男命婚恋应期',
 '{"gender":"male","spouse_star_is_xi":true}',
 '{"conclusion":"大运天干或地支引动财星（妻星），为男命婚恋应期。此运中遇合年或桃花年，极利婚恋","causal_chain":"男命 + 大运引动财星 + 财星为喜 → 妻星得力 → 婚恋应期","confidence":0.80}',
 180, '命理通则', '大运引动妻星为应期'),

('marriage_mt_002', 'marriage', 'marriage_timing', '大运引动官杀——女命婚恋应期',
 '{"gender":"female","spouse_star_is_xi":true}',
 '{"conclusion":"大运天干或地支引动官杀星（夫星），为女命婚恋应期。此运中遇合年或桃花年，极利婚恋","causal_chain":"女命 + 大运引动官杀 + 官杀为喜 → 夫星得力 → 婚恋应期","confidence":0.80}',
 180, '命理通则', '大运引动夫星为应期'),

('marriage_mt_003', 'marriage', 'marriage_timing', '流年天合地合——婚恋大吉年',
 '{}',
 '{"conclusion":"流年天干地支同时与命局或大运形成天合地合，为人生大和谐年份。极利婚恋嫁娶、感情升温","confidence":0.85}',
 200, '命理通则', '天合地合为大吉年'),

('marriage_mt_004', 'marriage', 'marriage_timing', '流年天克地冲——感情变动年',
 '{}',
 '{"conclusion":"流年天干地支同时与命局或大运形成天克地冲，变动最大。可能是分合、搬迁、重大决定年","confidence":0.80}',
 190, '命理通则', '天克地冲为变动年'),

('marriage_mt_005', 'marriage', 'marriage_timing', '岁运并临——人生关键年',
 '{}',
 '{"conclusion":"流年与大运干支相同（岁运并临），人生重大变化年。婚恋方面可能出现关键转折，好坏看喜忌","confidence":0.80}',
 190, '命理通则', '岁运并临为关键年')

ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    conditions = VALUES(conditions),
    conclusions = VALUES(conclusions),
    priority = VALUES(priority),
    source = VALUES(source),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

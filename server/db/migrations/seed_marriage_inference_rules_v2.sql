SET NAMES utf8mb4;

-- ═══════════════════════════════════════════════════════════════════
-- 婚姻领域推理规则种子数据 V2（全面扩充版）
-- 来源：子平真诠、滴天髓、三命通会、渊海子平等公认命理经典
-- 与 bazi_rules 表的区别：本表提供多因子组合推理 + 因果链 + 置信度
-- 创建日期：2026-03-18
-- ═══════════════════════════════════════════════════════════════════

-- 清空旧数据重新写入
TRUNCATE TABLE bazi_stream_inference_rules;

INSERT INTO bazi_stream_inference_rules (rule_code, domain, category, rule_name, conditions, conclusions, priority, source, description) VALUES

-- ═══════════════════════════════════════════════
-- 第一类：配偶星综合分析 (spouse_star) — 30条
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
 170, '子平真诠·论妻', '偏财为忌，主感情分散'),

('marriage_ss_005', 'marriage', 'spouse_star', '女命正官为喜且有力——夫星端正可靠',
 '{"gender":"female","spouse_star_type":"正官","spouse_star_is_xi":true}',
 '{"spouse_character":"丈夫正派可靠、有事业心、顾家负责","marriage_quality":"稳定","causal_chain":"女命 + 正官为喜用神 → 丈夫是命中正缘 → 婚姻基础牢固","confidence":0.85}',
 200, '子平真诠·论夫', '正官为喜用，主夫端正有为'),

('marriage_ss_006', 'marriage', 'spouse_star', '女命正官为忌——夫妻有压力',
 '{"gender":"female","spouse_star_type":"正官","spouse_star_is_xi":false}',
 '{"spouse_character":"丈夫过于严肃、给人压力大、管束过多","marriage_quality":"需磨合","causal_chain":"女命 + 正官为忌 → 丈夫管束过多 → 需要空间和理解","confidence":0.75}',
 180, '子平真诠·论夫', '正官为忌，主夫过于严肃'),

('marriage_ss_007', 'marriage', 'spouse_star', '女命七杀为喜——夫有魄力',
 '{"gender":"female","spouse_star_type":"七杀","spouse_star_is_xi":true}',
 '{"spouse_character":"丈夫有魄力担当、能力强、有保护欲","marriage_quality":"有活力","causal_chain":"女命 + 七杀为喜用 → 丈夫有开拓精神 → 婚姻有激情但需磨合","confidence":0.80}',
 180, '滴天髓·论官杀', '七杀为喜，主夫有魄力'),

('marriage_ss_008', 'marriage', 'spouse_star', '女命七杀为忌——感情波折',
 '{"gender":"female","spouse_star_type":"七杀","spouse_star_is_xi":false}',
 '{"spouse_character":"丈夫脾气急躁、控制欲强、容易有争吵","marriage_quality":"波折","causal_chain":"女命 + 七杀为忌 → 夫妻间冲突多 → 感情经历波折","confidence":0.70}',
 170, '滴天髓·论官杀', '七杀为忌，主感情波折'),

('marriage_ss_009', 'marriage', 'spouse_star', '男命财星混杂——正偏财同现',
 '{"gender":"male","spouse_star_type":"mixed_finance"}',
 '{"conclusion":"感情世界较复杂，易有多段情缘或对感情有犹豫，建议晚婚以利稳定","marriage_quality":"复杂","causal_chain":"男命 + 正偏财同现 → 财星混杂 → 感情选择多但不专一 → 建议晚婚","confidence":0.78}',
 190, '子平真诠·论妻', '正偏财同透或同藏，感情复杂'),

('marriage_ss_010', 'marriage', 'spouse_star', '女命官杀混杂——正官七杀同现',
 '{"gender":"female","spouse_star_type":"mixed_official"}',
 '{"conclusion":"感情历程多波折，容易遇到不同类型的异性，需以印星化杀来稳定","marriage_quality":"波折","causal_chain":"女命 + 官杀混杂 → 夫星不纯 → 感情压力大 → 需印星化解","confidence":0.78}',
 190, '滴天髓·论官杀', '官杀混杂，感情压力大'),

('marriage_ss_011', 'marriage', 'spouse_star', '男命无财星——异性缘薄',
 '{"gender":"male","spouse_star_strength":"absent"}',
 '{"conclusion":"一生与异性缘份薄，婚姻不易，婚后夫妻不常在一起或感情淡漠。建议加强社交主动出击","marriage_quality":"缘薄","causal_chain":"男命 + 无正偏财 → 异性缘分薄 → 感情被动 → 需主动经营","confidence":0.75}',
 180, '子平真诠·论妻', '无财星主妻缘薄'),

('marriage_ss_012', 'marriage', 'spouse_star', '女命无官杀——配偶缘薄',
 '{"gender":"female","spouse_star_strength":"absent"}',
 '{"conclusion":"一生与配偶缘份薄，婚姻推迟，可能两地分居或感情较淡。需主动把握缘分","marriage_quality":"缘薄","causal_chain":"女命 + 无正官七杀 → 夫星缺位 → 婚恋被动 → 建议主动争取","confidence":0.75}',
 180, '子平真诠·论夫', '无官杀主夫缘薄'),

('marriage_ss_013', 'marriage', 'spouse_star', '男命独一正财——感情专一',
 '{"gender":"male","spouse_star_type":"正财","spouse_star_count":1}',
 '{"conclusion":"对感情专一念旧，看重家庭责任，婚姻整体稳定性较强，离婚概率偏低","marriage_quality":"稳定","causal_chain":"男命 + 独一正财 → 妻星纯一 → 感情专一 → 婚姻稳固","confidence":0.82}',
 200, '子平真诠·论妻', '独一正财，感情专一'),

('marriage_ss_014', 'marriage', 'spouse_star', '女命独一正官——感情执着',
 '{"gender":"female","spouse_star_type":"正官","spouse_star_count":1}',
 '{"conclusion":"对感情专一执着，始终看重家庭，婚姻整体稳定性较强，是持家型","marriage_quality":"稳定","causal_chain":"女命 + 独一正官 → 夫星纯正 → 感情坚定 → 婚姻可靠","confidence":0.82}',
 200, '子平真诠·论夫', '独一正官，感情坚定'),

('marriage_ss_015', 'marriage', 'spouse_star', '男命多偏财——情缘复杂',
 '{"gender":"male","spouse_star_type":"偏财","spouse_star_count_min":3}',
 '{"conclusion":"多情外向，对异性好感强，婚姻稳定性偏弱，易有家庭矛盾","marriage_quality":"不稳定","causal_chain":"男命 + 偏财3个以上 → 财星过旺 → 情缘分散 → 婚姻易生变","confidence":0.78}',
 190, '子平真诠·论妻', '偏财过多，情缘复杂'),

('marriage_ss_016', 'marriage', 'spouse_star', '女命多七杀——感情多波折',
 '{"gender":"female","spouse_star_type":"七杀","spouse_star_count_min":3}',
 '{"conclusion":"多情外向，易因感情生风波，婚姻稳定性偏弱","marriage_quality":"不稳定","causal_chain":"女命 + 七杀3个以上 → 官杀过旺 → 异性缘复杂 → 婚姻多变","confidence":0.78}',
 190, '滴天髓·论官杀', '七杀过多，感情多波折'),

-- ═══════════════════════════════════════════════
-- 第二类：婚姻宫综合分析 (marriage_palace) — 20条
-- ═══════════════════════════════════════════════

('marriage_mp_001', 'marriage', 'marriage_palace', '日支坐比肩——夫妻竞争',
 '{"day_branch_star":"比肩"}',
 '{"conclusion":"配偶与自己性格相近，但容易争执。婚姻中需注意避免竞争","marriage_quality":"需注意","causal_chain":"日支坐比肩 → 配偶与己同类 → 容易争权 → 需互相退让","confidence":0.78}',
 180, '子平真诠·论夫妻宫', '比肩坐婚姻宫'),

('marriage_mp_002', 'marriage', 'marriage_palace', '日支坐劫财——竞争者干扰',
 '{"day_branch_star":"劫财"}',
 '{"conclusion":"容易遇到竞争者或第三方干扰，配偶个性强、可能有争财之象","marriage_quality":"波折","causal_chain":"日支坐劫财 → 婚姻宫有争夺之气 → 第三者易介入 → 需防范","confidence":0.75}',
 180, '子平真诠·论夫妻宫', '劫财坐婚姻宫'),

('marriage_mp_003', 'marriage', 'marriage_palace', '日支坐食神——夫妻融洽',
 '{"day_branch_star":"食神"}',
 '{"conclusion":"配偶温和体贴、生活情趣丰富，夫妻相处融洽","marriage_quality":"良好","causal_chain":"日支坐食神 → 婚姻宫带和气 → 配偶温柔 → 生活愉快","confidence":0.82}',
 190, '子平真诠·论夫妻宫', '食神坐婚姻宫'),

('marriage_mp_004', 'marriage', 'marriage_palace', '日支坐伤官——感情直接尖锐',
 '{"day_branch_star":"伤官"}',
 '{"conclusion":"感情表达直接甚至尖锐，配偶有才华但脾气大","marriage_quality":"波折","causal_chain":"日支坐伤官 → 婚姻宫带锐气 → 言辞易伤人 → 需修养脾气","confidence":0.75}',
 180, '子平真诠·论夫妻宫', '伤官坐婚姻宫'),

('marriage_mp_005', 'marriage', 'marriage_palace', '男命日支坐正财——妻贤持家',
 '{"gender":"male","day_branch_star":"正财"}',
 '{"conclusion":"妻星坐婚姻宫，婚姻基础好，妻子贤良持家","marriage_quality":"极好","causal_chain":"男命 + 正财坐日支 → 妻星归位 → 婚姻宫正气 → 夫妻和睦","confidence":0.88}',
 210, '子平真诠·论夫妻宫', '男命正财坐日支为上佳'),

('marriage_mp_006', 'marriage', 'marriage_palace', '女命日支坐正官——丈夫可靠',
 '{"gender":"female","day_branch_star":"正官"}',
 '{"conclusion":"夫星坐婚姻宫，丈夫正派可靠，婚姻稳固","marriage_quality":"极好","causal_chain":"女命 + 正官坐日支 → 夫星归位 → 婚姻宫正气 → 夫妻恩爱","confidence":0.88}',
 210, '子平真诠·论夫妻宫', '女命正官坐日支为上佳'),

('marriage_mp_007', 'marriage', 'marriage_palace', '日支坐正印——配偶包容',
 '{"day_branch_star":"正印"}',
 '{"conclusion":"配偶包容大度、有文化修养，能给自己精神支持","marriage_quality":"良好","causal_chain":"日支坐正印 → 婚姻宫有贵气 → 配偶文雅 → 精神依靠","confidence":0.80}',
 180, '子平真诠·论夫妻宫', '正印坐婚姻宫'),

('marriage_mp_008', 'marriage', 'marriage_palace', '日支坐偏印——配偶内向',
 '{"day_branch_star":"偏印"}',
 '{"conclusion":"配偶想法独特、内心丰富，但可能有情感压抑","marriage_quality":"需理解","causal_chain":"日支坐偏印 → 婚姻宫内敛 → 配偶不善表达 → 需用心沟通","confidence":0.72}',
 170, '子平真诠·论夫妻宫', '偏印坐婚姻宫'),

('marriage_mp_009', 'marriage', 'marriage_palace', '婚姻宫逢冲——感情动荡',
 '{"marriage_palace_chong":true}',
 '{"conclusion":"感情中容易有较大变动或冲突，婚姻宫不安稳，宜晚婚或多沟通化解","marriage_quality":"不稳定","causal_chain":"婚姻宫逢冲 → 家庭关系动荡 → 感情多变 → 宜晚婚","confidence":0.80}',
 190, '命理通则', '婚姻宫逢冲主动荡'),

('marriage_mp_010', 'marriage', 'marriage_palace', '婚姻宫逢合——缘分到来',
 '{"marriage_palace_he":true}',
 '{"conclusion":"婚姻宫被合动，利于婚恋缘分出现，配偶感情投入度高","marriage_quality":"利好","causal_chain":"婚姻宫逢合 → 缘分信号 → 配偶投入 → 利于婚恋","confidence":0.78}',
 180, '命理通则', '婚姻宫逢合利缘分'),

('marriage_mp_011', 'marriage', 'marriage_palace', '婚姻宫逢刑——相处困难',
 '{"marriage_palace_xing":true}',
 '{"conclusion":"夫妻相处有隐性矛盾，表面平静内心不满，久之积怨影响感情","marriage_quality":"暗伤","causal_chain":"婚姻宫逢刑 → 暗伤累积 → 表面平和内心不满 → 需定期沟通","confidence":0.76}',
 180, '命理通则', '婚姻宫逢刑主暗伤'),

('marriage_mp_012', 'marriage', 'marriage_palace', '男命日支坐偏财——感情多波动',
 '{"gender":"male","day_branch_star":"偏财"}',
 '{"conclusion":"偏财坐婚姻宫，配偶大方活泼，但感情多波动","marriage_quality":"波折","causal_chain":"男命 + 偏财坐日支 → 妻星偏位 → 配偶不安定 → 感情多变","confidence":0.72}',
 170, '子平真诠·论夫妻宫', '偏财坐日支，感情多变'),

('marriage_mp_013', 'marriage', 'marriage_palace', '女命日支坐七杀——夫强势',
 '{"gender":"female","day_branch_star":"七杀"}',
 '{"conclusion":"偏夫坐婚姻宫，丈夫有魄力但性格强势，婚姻需磨合","marriage_quality":"需磨合","causal_chain":"女命 + 七杀坐日支 → 夫星偏刚 → 性格冲突 → 需互相退让","confidence":0.72}',
 170, '滴天髓·论官杀', '七杀坐日支，夫强势'),

-- ═══════════════════════════════════════════════
-- 第三类：十神组合断语 (ten_gods_combo) — 25条
-- ═══════════════════════════════════════════════

('marriage_tg_001', 'marriage', 'ten_gods_combo', '男命比劫坐日支——克妻',
 '{"gender":"male","day_branch_stars":["比肩","劫财"]}',
 '{"conclusion":"婚姻不顺，夫妻两个容易有口角、吵架，或者配偶身体不好","marriage_quality":"不顺","causal_chain":"男命 + 比劫坐日支 → 争夺妻星之力 → 婚姻宫受伤 → 需忍让","confidence":0.78}',
 190, '子平真诠·论妻', '比劫坐日支主克妻'),

('marriage_tg_002', 'marriage', 'ten_gods_combo', '女命食伤坐日支——克夫',
 '{"gender":"female","day_branch_stars":["食神","伤官"]}',
 '{"conclusion":"婚姻不顺，夫妻两个容易有口角、吵架，或者配偶身体不好","marriage_quality":"不顺","causal_chain":"女命 + 食伤坐日支 → 泄夫星之气 → 夫妻失衡 → 需修口德","confidence":0.78}',
 190, '子平真诠·论夫', '食伤坐日支主克夫'),

('marriage_tg_003', 'marriage', 'ten_gods_combo', '女命伤官见官——婚姻大忌',
 '{"gender":"female","has_shishen":["伤官","正官"]}',
 '{"conclusion":"伤官见官为女命大忌，感情波折多，婚姻不稳定，建议以印化解","marriage_quality":"大凶","causal_chain":"女命 + 伤官见官 → 夫星被克 → 感情根基受损 → 需印星化解","confidence":0.82}',
 200, '滴天髓·伤官见官', '女命伤官见官为大忌'),

('marriage_tg_004', 'marriage', 'ten_gods_combo', '男命偏财年月透出——早恋倾向',
 '{"gender":"male","spouse_star_early":true}',
 '{"conclusion":"情感开窍较早，易有早恋、早婚倾向，学生时期便可能萌生爱慕之情","marriage_quality":"早恋","causal_chain":"男命 + 偏财在年月透出 → 财星早现 → 早年情缘旺 → 易早恋","confidence":0.75}',
 170, '子平真诠·论妻', '偏财年月透出主早恋'),

('marriage_tg_005', 'marriage', 'ten_gods_combo', '女命官杀在年月——婚姻较早',
 '{"gender":"female","spouse_star_early":true}',
 '{"conclusion":"结婚时间比较早，易在年轻时遇到婚恋机会","marriage_quality":"早婚","causal_chain":"女命 + 官杀在年月 → 夫星早现 → 婚缘来得早 → 宜把握","confidence":0.75}',
 170, '子平真诠·论夫', '官杀年月出现主早婚'),

('marriage_tg_006', 'marriage', 'ten_gods_combo', '男命偏财两透——婚外情象',
 '{"gender":"male","spouse_star_type":"偏财","spouse_star_count":2}',
 '{"conclusion":"有婚姻不顺之象，实际中可能有正妻还有情人","marriage_quality":"不稳定","causal_chain":"男命 + 两偏财透出 → 偏财双现 → 正偏缘并存 → 婚外情象","confidence":0.76}',
 180, '子平真诠·论妻', '两偏财透出主二心'),

('marriage_tg_007', 'marriage', 'ten_gods_combo', '女命两偏官透出——感情分叉',
 '{"gender":"female","spouse_star_type":"七杀","spouse_star_count":2}',
 '{"conclusion":"易同时面对多段情缘，需留意情感边界，规避纠纷","marriage_quality":"不稳定","causal_chain":"女命 + 两七杀透出 → 杀星双现 → 夫缘多头 → 感情分叉","confidence":0.76}',
 180, '滴天髓·论官杀', '两七杀透出主感情分叉'),

('marriage_tg_008', 'marriage', 'ten_gods_combo', '女命伤官月柱——再婚之象',
 '{"gender":"female","has_shishen_in_month":"伤官"}',
 '{"conclusion":"伤官在月柱，性情直率但易伤人，婚姻中矛盾频发","marriage_quality":"不稳定","causal_chain":"女命 + 伤官在月柱 → 主气刚烈 → 夫妻冲突 → 再婚概率大","confidence":0.76}',
 180, '三命通会·论婚姻', '月柱伤官主再婚'),

('marriage_tg_009', 'marriage', 'ten_gods_combo', '男命伤官年时——刑妻克子',
 '{"gender":"male","has_shishen_year_hour":"伤官"}',
 '{"conclusion":"命带刑克之兆，刑妻克子恐难避免，需多慎之","marriage_quality":"凶","causal_chain":"男命 + 伤官占年时 → 首尾呼应 → 克力双重 → 刑妻克子","confidence":0.74}',
 180, '三命通会·论婚姻', '伤官年时双现主克'),

('marriage_tg_010', 'marriage', 'ten_gods_combo', '食神坐时支——初次婚姻不成',
 '{"has_shishen_in_hour":"食神"}',
 '{"conclusion":"一次婚姻谈不成，可能经历两段以上恋情才步入婚姻","marriage_quality":"曲折","causal_chain":"食神在时支 → 晚年花气 → 初婚不成 → 需耐心等待正缘","confidence":0.72}',
 170, '渊海子平·论婚姻', '食神时支主初婚不成'),

('marriage_tg_011', 'marriage', 'ten_gods_combo', '女命官杀先偏后正——先恋后婚',
 '{"gender":"female","spouse_star_pattern":"kill_early_official_late"}',
 '{"conclusion":"婚前方有情缘实至，先有经历后得正缘成婚","marriage_quality":"先波折后稳定","causal_chain":"女命 + 年月七杀日时正官 → 先遇偏缘 → 后得正缘 → 先恋后婚","confidence":0.76}',
 180, '三命通会·论婚姻', '七杀在前正官在后主先恋后婚'),

('marriage_tg_012', 'marriage', 'ten_gods_combo', '男命财星先偏后正——先恋后婚',
 '{"gender":"male","spouse_star_pattern":"casual_early_proper_late"}',
 '{"conclusion":"婚前有过情缘经历，先历偏缘后得正妻","marriage_quality":"先波折后稳定","causal_chain":"男命 + 年月偏财日时正财 → 先遇偏缘 → 后得正妻 → 先恋后婚","confidence":0.76}',
 180, '子平真诠·论妻', '偏财在前正财在后主先恋后婚'),

('marriage_tg_013', 'marriage', 'ten_gods_combo', '印星过多——婚缘薄弱',
 '{"has_shishen_count_min":{"正印":3}}',
 '{"conclusion":"孤辰寡宿之象，婚恋缘分浅薄，适合晚婚","marriage_quality":"缘薄","causal_chain":"正印3个以上 → 印星过旺 → 克制子嗣婚缘 → 适合晚婚","confidence":0.72}',
 170, '滴天髓·论印', '印星过旺主婚缘薄'),

('marriage_tg_014', 'marriage', 'ten_gods_combo', '劫财过旺——婚姻暴力倾向',
 '{"has_shishen_count_min":{"劫财":5}}',
 '{"conclusion":"命格中带有冲动戾气，易因情绪失控引发冲突","marriage_quality":"极需注意","causal_chain":"劫财5个以上 → 争夺之气极旺 → 冲动易怒 → 需修养心性","confidence":0.74}',
 180, '渊海子平·论比劫', '劫财过旺主冲动'),

-- ═══════════════════════════════════════════════
-- 第四类：神煞组合断语 (deity_combo) — 20条
-- ═══════════════════════════════════════════════

('marriage_dt_001', 'marriage', 'deity_combo', '日坐空亡——夫妻缘薄',
 '{"has_deity":"空亡","deity_pillar":"day"}',
 '{"conclusion":"夫妻之中有一方感情不真挚，或有早折之兆。需用心经营","marriage_quality":"缘薄","causal_chain":"日支空亡 → 婚姻宫虚空 → 配偶缘分薄 → 感情不实","confidence":0.76}',
 180, '渊海子平·论空亡', '日坐空亡主婚缘虚'),

('marriage_dt_002', 'marriage', 'deity_combo', '日坐羊刃(男)——妻性刚烈',
 '{"gender":"male","has_deity":"羊刃","deity_pillar":"day"}',
 '{"conclusion":"妻子性格暴躁、脾气刚烈，是强势型配偶","marriage_quality":"波折","causal_chain":"男命 + 日坐羊刃 → 婚姻宫戾气重 → 妻子性格刚烈 → 易争吵","confidence":0.78}',
 180, '渊海子平·论羊刃', '男命日坐羊刃主妻刚'),

('marriage_dt_003', 'marriage', 'deity_combo', '日坐羊刃(女)——克夫妨婚',
 '{"gender":"female","has_deity":"羊刃","deity_pillar":"day"}',
 '{"conclusion":"命带刚烈之气，妨克丈夫早离分","marriage_quality":"凶","causal_chain":"女命 + 日坐羊刃 → 婚姻宫煞气 → 刚性克夫 → 宜晚婚","confidence":0.76}',
 180, '渊海子平·论羊刃', '女命日坐羊刃主克夫'),

('marriage_dt_004', 'marriage', 'deity_combo', '羊刃两现——婚姻难美满',
 '{"has_deity_count":{"name":"羊刃","min":2}}',
 '{"conclusion":"婚姻难有美满，感情多波折","marriage_quality":"不好","causal_chain":"羊刃两现 → 刚烈之气双重 → 克性加重 → 婚姻多磨","confidence":0.76}',
 180, '渊海子平·论羊刃', '羊刃双现主婚不美'),

('marriage_dt_005', 'marriage', 'deity_combo', '日坐华盖(女)——孤独终老',
 '{"gender":"female","has_deity":"华盖","deity_pillar":"day"}',
 '{"conclusion":"性格清高孤傲，不易找到合适伴侣，婚姻较晚或无子","marriage_quality":"孤独","causal_chain":"女命 + 日坐华盖 → 清高自持 → 姻缘迟 → 宜修心养性","confidence":0.72}',
 170, '渊海子平·论华盖', '女命日坐华盖主孤'),

('marriage_dt_006', 'marriage', 'deity_combo', '日坐魁罡——夫妻争吵',
 '{"has_deity":"魁罡","deity_pillar":"day"}',
 '{"conclusion":"夫妻争吵打闹不分离，感情虽有波折但不会轻易放手","marriage_quality":"吵闹","causal_chain":"日坐魁罡 → 刚烈之气 → 夫妻争强 → 吵闹但不离","confidence":0.74}',
 170, '渊海子平·论魁罡', '魁罡坐日主争吵'),

('marriage_dt_007', 'marriage', 'deity_combo', '日坐驿马(女)——远嫁他乡',
 '{"gender":"female","has_deity":"驿马","deity_pillar":"day"}',
 '{"conclusion":"会找与自己出生家庭有距离的配偶，可能远嫁","marriage_quality":"远嫁","causal_chain":"女命 + 日坐驿马 → 婚姻宫有动 → 配偶远方来 → 远嫁","confidence":0.72}',
 170, '渊海子平·论驿马', '女命日坐驿马主远嫁'),

('marriage_dt_008', 'marriage', 'deity_combo', '男命日坐孤辰——克妻',
 '{"gender":"male","has_deity":"孤辰","deity_pillar":"day"}',
 '{"conclusion":"男命日坐孤辰，克妻之象明显","marriage_quality":"克妻","causal_chain":"男命 + 日坐孤辰 → 婚姻宫孤煞 → 克妻 → 宜晚婚","confidence":0.74}',
 180, '渊海子平·论孤辰', '男命日坐孤辰主克妻'),

('marriage_dt_009', 'marriage', 'deity_combo', '女命日坐寡宿——克夫',
 '{"gender":"female","has_deity":"寡宿","deity_pillar":"day"}',
 '{"conclusion":"女命日坐寡宿，克夫之象明显","marriage_quality":"克夫","causal_chain":"女命 + 日坐寡宿 → 婚姻宫孤煞 → 克夫 → 宜晚婚","confidence":0.74}',
 180, '渊海子平·论寡宿', '女命日坐寡宿主克夫'),

('marriage_dt_010', 'marriage', 'deity_combo', '日坐天乙贵人——配偶素质高',
 '{"has_deity":"天乙贵人","deity_pillar":"day"}',
 '{"conclusion":"配偶貌美素质高，人品出众","marriage_quality":"上佳","causal_chain":"日坐天乙贵人 → 婚姻宫贵气 → 配偶优秀 → 婚姻有福","confidence":0.80}',
 190, '渊海子平·论天乙', '日坐天乙主配偶优秀'),

('marriage_dt_011', 'marriage', 'deity_combo', '流年红鸾天喜——婚期将至',
 '{"liunian_deity":["红鸾","天喜"]}',
 '{"conclusion":"终身大事姻缘成，此年利于婚恋","marriage_quality":"大吉","causal_chain":"流年逢红鸾天喜 → 婚恋之星引动 → 缘分到来 → 宜把握","confidence":0.80}',
 190, '渊海子平·论桃花', '红鸾天喜主婚期'),

('marriage_dt_012', 'marriage', 'deity_combo', '亡神劫煞同现——妨克配偶',
 '{"has_deity_combo":["亡神","劫煞"]}',
 '{"conclusion":"妨克配偶祖业空，婚姻中易遇不幸","marriage_quality":"凶","causal_chain":"亡神劫煞同柱 → 凶煞叠加 → 克配偶 → 需化解","confidence":0.74}',
 180, '渊海子平·论凶煞', '亡神劫煞同现主克'),

('marriage_dt_013', 'marriage', 'deity_combo', '男命羊刃桃花同柱——桃花劫',
 '{"gender":"male","has_deity_combo_pillar":["羊刃","桃花"]}',
 '{"conclusion":"桃花劫会连带财运受损，可能因情感纠纷、应酬开销导致破财","marriage_quality":"劫财","causal_chain":"男命 + 羊刃桃花同柱 → 桃花劫 → 因情破财 → 需约束","confidence":0.76}',
 180, '渊海子平·论桃花', '羊刃桃花同柱主桃花劫'),

('marriage_dt_014', 'marriage', 'deity_combo', '男命日坐沐浴——妻美但波折',
 '{"gender":"male","has_star_fortune":"沐浴","fortune_pillar":"day"}',
 '{"conclusion":"妻子漂亮，但易感情起波浪","marriage_quality":"波折","causal_chain":"男命 + 日坐沐浴 → 桃花旺 → 妻美有魅力 → 但感情多变","confidence":0.74}',
 170, '渊海子平·论十二长生', '男命日坐沐浴主妻美波折'),

('marriage_dt_015', 'marriage', 'deity_combo', '男命日坐长生——妻善理财',
 '{"gender":"male","has_star_fortune":"长生","fortune_pillar":"day"}',
 '{"conclusion":"妻子必定善理财，持家有方","marriage_quality":"稳定","causal_chain":"男命 + 日坐长生 → 财星得生 → 妻子能干 → 家运兴旺","confidence":0.78}',
 180, '渊海子平·论十二长生', '男命日坐长生主妻善理财'),

-- ═══════════════════════════════════════════════
-- 第五类：地支组合断语 (branch_combo) — 20条
-- ═══════════════════════════════════════════════

('marriage_bc_001', 'marriage', 'branch_combo', '四库全——婚姻根基不稳',
 '{"branch_pattern":"si_ku_full"}',
 '{"conclusion":"主婚姻根基不稳，易有第三方介入或多番波折","marriage_quality":"不稳定","causal_chain":"辰戌丑未四库全 → 土气过重 → 克水(财/官) → 婚姻动荡","confidence":0.78}',
 190, '三命通会·论地支', '四库全主婚不稳'),

('marriage_bc_002', 'marriage', 'branch_combo', '日时地支合——婚宜迟',
 '{"branch_relation":"day_hour_liuhe"}',
 '{"conclusion":"婚姻宜迟不宜早，早婚则多变","marriage_quality":"宜晚婚","causal_chain":"日支与时支六合 → 婚姻宫被合走 → 早婚不稳 → 宜晚婚","confidence":0.76}',
 180, '渊海子平·论合', '日时合主宜晚婚'),

('marriage_bc_003', 'marriage', 'branch_combo', '月日天合地合——父母做主',
 '{"branch_relation":"month_day_liuhe"}',
 '{"conclusion":"婚姻可能由父母来做主或媒妁之言","marriage_quality":"传统","causal_chain":"月支与日支六合 → 父母宫合婚姻宫 → 长辈介入 → 婚姻由长辈定","confidence":0.72}',
 170, '渊海子平·论合', '月日合主父母做主'),

('marriage_bc_004', 'marriage', 'branch_combo', '日支被三方冲刑——婚姻不宁',
 '{"marriage_palace_multi_clash":true}',
 '{"conclusion":"婚姻不稳少安宁，不离则散","marriage_quality":"极不稳定","causal_chain":"日支被年月时多方冲刑 → 婚姻宫四面受敌 → 难以安宁 → 不离则散","confidence":0.80}',
 200, '三命通会·论冲刑', '日支多方冲刑主离散'),

('marriage_bc_005', 'marriage', 'branch_combo', '男命日支四正位——配偶端庄',
 '{"gender":"male","day_branch_type":"四正"}',
 '{"conclusion":"主配偶漂亮端庄或有能力","marriage_quality":"上佳","causal_chain":"男命 + 日支为子午卯酉 → 四正之气 → 配偶端正有能力","confidence":0.76}',
 180, '渊海子平·论日支', '男命日支四正主妻美'),

('marriage_bc_006', 'marriage', 'branch_combo', '男命日支四库位——配偶踏实',
 '{"gender":"male","day_branch_type":"四库"}',
 '{"conclusion":"配偶性情踏实稳重，待人真诚厚道，是能踏实过日子的类型","marriage_quality":"朴实","causal_chain":"男命 + 日支为辰戌丑未 → 四库之气 → 配偶踏实 → 品性可靠","confidence":0.76}',
 180, '渊海子平·论日支', '男命日支四库主妻朴实'),

('marriage_bc_007', 'marriage', 'branch_combo', '辰戌冲(男)——晚年孤独',
 '{"gender":"male","branch_pair":"辰戌"}',
 '{"conclusion":"多孤独，晚年孤独守空房","marriage_quality":"孤独","causal_chain":"男命 + 辰戌相冲 → 土气战争 → 婚姻宫不安 → 晚年孤寂","confidence":0.74}',
 170, '三命通会·论冲', '男命辰戌冲主晚年孤'),

('marriage_bc_008', 'marriage', 'branch_combo', '辰戌丑未全——克配偶',
 '{"branch_pattern":"chen_xu_chou_wei_full"}',
 '{"conclusion":"会克自己的配偶，婚姻动荡","marriage_quality":"极凶","causal_chain":"辰戌丑未全现 → 四库相冲战 → 克力极大 → 严重妨害配偶","confidence":0.80}',
 200, '三命通会·论地支', '四库全现主克偶'),

('marriage_bc_009', 'marriage', 'branch_combo', '地支纯一——婚姻不到头',
 '{"branch_unique_count":1}',
 '{"conclusion":"婚姻没有一个到头的，感情难长久","marriage_quality":"极不稳定","causal_chain":"四支同字 → 气场极端 → 单一之气 → 婚姻难维持","confidence":0.76}',
 180, '三命通会·论地支', '地支纯一主婚难到头'),

('marriage_bc_010', 'marriage', 'branch_combo', '日支火元素——配偶亮丽',
 '{"day_branch_element":"火"}',
 '{"conclusion":"配偶亮丽，面红润，性格热情","spouse_appearance":"面色红润、气质亮丽","causal_chain":"日支属火 → 配偶带火之性 → 外表亮丽 → 性格热情","confidence":0.72}',
 160, '渊海子平·论五行', '日支属火主配偶亮丽'),

('marriage_bc_011', 'marriage', 'branch_combo', '日支木元素——配偶高挑',
 '{"day_branch_element":"木"}',
 '{"conclusion":"配偶身材高挑，气质文雅","spouse_appearance":"身材高挑、头发秀丽","causal_chain":"日支属木 → 配偶带木之性 → 身材修长 → 气质文雅","confidence":0.72}',
 160, '渊海子平·论五行', '日支属木主配偶高挑'),

('marriage_bc_012', 'marriage', 'branch_combo', '日支金元素——配偶白皙',
 '{"day_branch_element":"金"}',
 '{"conclusion":"配偶长得白皙端庄","spouse_appearance":"肤白端庄","causal_chain":"日支属金 → 配偶带金之性 → 白皙端庄 → 有原则","confidence":0.72}',
 160, '渊海子平·论五行', '日支属金主配偶白皙'),

-- ═══════════════════════════════════════════════
-- 第六类：天干组合断语 (stem_combo) — 15条
-- ═══════════════════════════════════════════════

('marriage_sc_001', 'marriage', 'stem_combo', '戊癸合(男)——妻极端',
 '{"gender":"male","stem_combo":["戊","癸"]}',
 '{"conclusion":"妻子可能走极端，性格偏激","marriage_quality":"波折","causal_chain":"男命 + 戊癸天干合 → 合化为火 → 配偶性急 → 易走极端","confidence":0.74}',
 170, '三命通会·论合', '男命戊癸合主妻极端'),

('marriage_sc_002', 'marriage', 'stem_combo', '戊癸合(女)——晚年孤寂',
 '{"gender":"female","stem_combo":["戊","癸"]}',
 '{"conclusion":"孤星照拂，晚年身边少人陪伴，易陷孤寂","marriage_quality":"孤寂","causal_chain":"女命 + 戊癸天干合 → 合化为火 → 火旺木枯 → 晚年孤独","confidence":0.72}',
 170, '三命通会·论合', '女命戊癸合主晚年孤'),

('marriage_sc_003', 'marriage', 'stem_combo', '壬丙冲——婚姻冲动败家',
 '{"stem_combo":["壬","丙"]}',
 '{"conclusion":"婚姻冲动必败家","marriage_quality":"败","causal_chain":"壬丙天干冲 → 水火激战 → 冲动行事 → 因冲动败家","confidence":0.74}',
 180, '三命通会·论冲', '壬丙冲主冲动败家'),

('marriage_sc_004', 'marriage', 'stem_combo', '乙庚合(女)——貌美刑夫',
 '{"gender":"female","stem_combo":["乙","庚"]}',
 '{"conclusion":"长相貌美，但有刑夫克子之兆","marriage_quality":"波折","causal_chain":"女命 + 乙庚天干合 → 合化为金 → 金旺克木 → 貌美但克夫","confidence":0.74}',
 170, '三命通会·论合', '女命乙庚合主貌美克夫'),

('marriage_sc_005', 'marriage', 'stem_combo', '天干纯一——婚姻不安',
 '{"stem_unique_count":1}',
 '{"conclusion":"一生中婚姻都不得安宁","marriage_quality":"极不稳定","causal_chain":"四干同字 → 气场极端 → 刚性过强 → 婚姻难安","confidence":0.76}',
 180, '三命通会·论天干', '天干纯一主婚不安'),

('marriage_sc_006', 'marriage', 'stem_combo', '女命伤官无正官——必再嫁',
 '{"gender":"female","has_shishen":"伤官","no_shishen":"正官"}',
 '{"conclusion":"必定克夫再嫁","marriage_quality":"再婚","causal_chain":"女命 + 伤官透出 + 无正官 → 夫星被克尽 → 克夫 → 必再嫁","confidence":0.76}',
 190, '滴天髓·论官杀', '女命伤官无官主再嫁'),

('marriage_sc_007', 'marriage', 'stem_combo', '男命无正财有偏财——偏缘竞争',
 '{"gender":"male","no_shishen":"正财","has_shishen":"偏财"}',
 '{"conclusion":"婚姻中易出现第三者，偏缘竞争力强","marriage_quality":"不稳定","causal_chain":"男命 + 无正财有偏财 → 正妻缘薄 → 偏缘反强 → 第三者介入","confidence":0.74}',
 180, '子平真诠·论妻', '无正财有偏财主偏缘强'),

('marriage_sc_008', 'marriage', 'stem_combo', '女命无正财有偏财——婚姻不到头',
 '{"gender":"female","no_shishen_main":"正财","has_shishen_main":"偏财"}',
 '{"conclusion":"一次婚姻不到头","marriage_quality":"不稳定","causal_chain":"女命 + 天干无正财有偏财 → 偏缘旺正缘弱 → 初婚不稳 → 可能再婚","confidence":0.72}',
 170, '三命通会·论婚姻', '女命无正财有偏财主婚不到头'),

-- ═══════════════════════════════════════════════
-- 第七类：格局组合断语 (bazi_pattern) — 15条
-- ═══════════════════════════════════════════════

('marriage_bp_001', 'marriage', 'bazi_pattern', '日时天合地合(女)——二婚之象',
 '{"gender":"female","pillar_relation":"day_hour_tianhe_dihe"}',
 '{"conclusion":"即便步入婚姻，夫妻间矛盾多，二婚不止再嫁多","marriage_quality":"多婚","causal_chain":"女命 + 日时天合地合 → 婚姻宫被合走 → 姻缘不稳 → 多婚","confidence":0.76}',
 180, '三命通会·论合', '女命日时天合地合主多婚'),

('marriage_bp_002', 'marriage', 'bazi_pattern', '年日天合地合(男)——因妻发财或破',
 '{"gender":"male","pillar_relation":"year_day_tianhe_dihe"}',
 '{"conclusion":"因妻发财或财破，命运起伏大","marriage_quality":"大起大落","causal_chain":"男命 + 年日天合地合 → 财星与命格强联 → 因妻得财或破财","confidence":0.74}',
 170, '三命通会·论合', '男命年日天合地合主因妻财变'),

('marriage_bp_003', 'marriage', 'bazi_pattern', '月日天克地冲——妨克配偶',
 '{"pillar_relation":"month_day_tianke_dichong"}',
 '{"conclusion":"妨克配偶多验应，婚姻必变更","marriage_quality":"凶","causal_chain":"月日天克地冲 → 父母宫冲婚姻宫 → 家庭矛盾 → 婚姻不稳","confidence":0.78}',
 190, '三命通会·论冲克', '月日天克地冲主婚变'),

('marriage_bp_004', 'marriage', 'bazi_pattern', '年日地支同——相同之缘',
 '{"pillar_relation":"year_day_branch_equal"}',
 '{"conclusion":"易与同年出生者结缘，五行气场契合度较高","marriage_quality":"契合","causal_chain":"年支等于日支 → 出生年气场与婚姻宫同 → 易配同龄人","confidence":0.68}',
 160, '三命通会·论配偶', '年日支同主同龄配偶'),

('marriage_bp_005', 'marriage', 'bazi_pattern', '女命年日六合——不离娘家',
 '{"gender":"female","pillar_relation":"year_day_liuhe"}',
 '{"conclusion":"女招赘，女命不离娘家门","marriage_quality":"特殊","causal_chain":"女命 + 年支合日支 → 娘家宫合婚姻宫 → 不愿远嫁 → 招赘","confidence":0.72}',
 170, '渊海子平·论合', '女命年日合主招赘'),

('marriage_bp_006', 'marriage', 'bazi_pattern', '男命日时地支冲——中年克妻',
 '{"gender":"male","pillar_relation":"day_hour_branch_chong"}',
 '{"conclusion":"克妻格局明确，30岁左右对妻子运势冲击最强","marriage_quality":"克妻","causal_chain":"男命 + 日时地支冲 → 婚姻宫与子女宫冲 → 中年克妻","confidence":0.76}',
 180, '三命通会·论冲', '男命日时冲主克妻'),

('marriage_bp_007', 'marriage', 'bazi_pattern', '男命日时地支刑——多妻',
 '{"gender":"male","pillar_relation":"day_hour_branch_xing"}',
 '{"conclusion":"多妻之命，婚姻难白头","marriage_quality":"多婚","causal_chain":"男命 + 日时地支刑 → 婚姻宫受刑 → 克力持续 → 多婚","confidence":0.74}',
 180, '三命通会·论刑', '男命日时刑主多妻'),

('marriage_bp_008', 'marriage', 'bazi_pattern', '月日同支同时冲——夫妻分离',
 '{"pillar_relation":"day_hour_liuhe_day_month_chong"}',
 '{"conclusion":"夫妻分离各西东","marriage_quality":"分离","causal_chain":"日时合 + 日月冲 → 婚姻宫两面受力 → 分离之象","confidence":0.76}',
 180, '三命通会·论合冲', '合冲同见主分离'),

-- ═══════════════════════════════════════════════
-- 第八类：日柱特殊断语 (day_pillar_special) — 15条
-- ═══════════════════════════════════════════════

('marriage_dp_001', 'marriage', 'day_pillar_special', '日柱干支同气——吵闹一辈子',
 '{"day_pillar_type":"same_element"}',
 '{"conclusion":"容易和配偶吵吵闹闹一辈子，但也不会真正分开","marriage_quality":"吵闹","causal_chain":"日柱干支同气 → 比劫坐命 → 夫妻同性格 → 互不相让","confidence":0.74}',
 170, '渊海子平·论日柱', '干支同气主吵闹'),

('marriage_dp_002', 'marriage', 'day_pillar_special', '日柱干支相克——配偶约束',
 '{"day_pillar_type":"stem_ke_branch"}',
 '{"conclusion":"容易被配偶约束，配偶给自己压力大，挑剔我","marriage_quality":"受制","causal_chain":"日干克日支 → 我克婚姻宫 → 想管控配偶 → 反被反制","confidence":0.72}',
 170, '渊海子平·论日柱', '干克支主受配偶制'),

('marriage_dp_003', 'marriage', 'day_pillar_special', '日柱干支相生(干生支)——爱配偶',
 '{"day_pillar_type":"stem_sheng_branch"}',
 '{"conclusion":"自己主动爱配偶，愿意为对方付出","marriage_quality":"温馨","causal_chain":"日干生日支 → 我生婚姻宫 → 主动付出 → 爱配偶","confidence":0.76}',
 180, '渊海子平·论日柱', '干生支主爱配偶'),

('marriage_dp_004', 'marriage', 'day_pillar_special', '日柱干支相生(支生干)——配偶爱我',
 '{"day_pillar_type":"branch_sheng_stem"}',
 '{"conclusion":"配偶对自己好，主动付出、关心体贴","marriage_quality":"被爱","causal_chain":"日支生日干 → 婚姻宫生我 → 配偶主动 → 被爱","confidence":0.76}',
 180, '渊海子平·论日柱', '支生干主配偶爱我'),

('marriage_dp_005', 'marriage', 'day_pillar_special', '男命日支正财+驿马——妻贤能',
 '{"gender":"male","day_has":["正财","驿马"]}',
 '{"conclusion":"妻子贤能善持家，且行动力强","marriage_quality":"上佳","causal_chain":"男命 + 日支正财+驿马 → 妻星有力且活跃 → 贤能持家","confidence":0.80}',
 190, '渊海子平·论配偶', '正财驿马同日主妻贤能'),

-- ═══════════════════════════════════════════════
-- 第九类：旺衰与婚姻 (wangshuai_marriage) — 10条
-- ═══════════════════════════════════════════════

('marriage_ws_001', 'marriage', 'wangshuai_marriage', '极旺男命——妻难长守',
 '{"gender":"male","wangshuai":"极旺"}',
 '{"conclusion":"若娶美貌之妻或高才之女难以长相厮守，终必离婚。适合找性格温婉包容的配偶","marriage_quality":"不稳定","causal_chain":"男命极旺 → 身强克妻 → 妻星被压制 → 需找能承受之人","confidence":0.74}',
 170, '滴天髓·论旺衰', '极旺男命主克妻'),

('marriage_ws_002', 'marriage', 'wangshuai_marriage', '极弱男命——妻强夫弱',
 '{"gender":"male","wangshuai":"极弱"}',
 '{"conclusion":"妻子可能比较强势，婚姻中自己处于被动地位","marriage_quality":"需适应","causal_chain":"男命极弱 → 身弱财旺 → 妻星反克 → 妻强夫弱","confidence":0.72}',
 170, '滴天髓·论旺衰', '极弱男命主妻强'),

('marriage_ws_003', 'marriage', 'wangshuai_marriage', '极旺女命——夫难管束',
 '{"gender":"female","wangshuai":"极旺"}',
 '{"conclusion":"性格刚强，丈夫难以管束，婚姻中自己较主导","marriage_quality":"强势","causal_chain":"女命极旺 → 身强克官 → 夫星被压制 → 自己主导","confidence":0.74}',
 170, '滴天髓·论旺衰', '极旺女命主自己强势'),

('marriage_ws_004', 'marriage', 'wangshuai_marriage', '极弱女命——夫强妻弱',
 '{"gender":"female","wangshuai":"极弱"}',
 '{"conclusion":"丈夫比较强势，自己在婚姻中需多忍让","marriage_quality":"需忍让","causal_chain":"女命极弱 → 身弱官旺 → 夫星强势 → 需学会沟通","confidence":0.72}',
 170, '滴天髓·论旺衰', '极弱女命主夫强'),

('marriage_ws_005', 'marriage', 'wangshuai_marriage', '身旺财弱——需主动追求',
 '{"gender":"male","wangshuai_vs_spouse":"strong_vs_weak"}',
 '{"conclusion":"自身强而配偶星弱，需主动出击追求感情，否则姻缘迟来","marriage_quality":"需主动","causal_chain":"身旺财弱 → 自己强配偶缘弱 → 被动等无缘 → 需主动","confidence":0.72}',
 170, '滴天髓·论旺衰', '身旺财弱需主动'),

-- ═══════════════════════════════════════════════
-- 第十类：婚恋时机 (marriage_timing) — 10条
-- ═══════════════════════════════════════════════

('marriage_tm_001', 'marriage', 'marriage_timing', '大运引动配偶星五行——婚恋窗口',
 '{}',
 '{"conclusion":"大运天干引动配偶星五行，是婚恋缘分出现的重要窗口期","timing_type":"spouse_star_activated","causal_chain":"大运天干 → 引动配偶星五行 → 姻缘之门打开 → 宜把握","confidence":0.78}',
 180, '命理通则', '大运引动配偶星主婚缘'),

('marriage_tm_002', 'marriage', 'marriage_timing', '大运合动婚姻宫——缘分到来',
 '{}',
 '{"conclusion":"大运地支合动婚姻宫，缘分即将到来","timing_type":"palace_he","causal_chain":"大运地支 → 六合婚姻宫 → 缘分信号 → 利于结婚","confidence":0.80}',
 190, '命理通则', '大运合婚姻宫主缘至'),

('marriage_tm_003', 'marriage', 'marriage_timing', '大运冲动婚姻宫——感情变动',
 '{}',
 '{"conclusion":"大运地支冲动婚姻宫，感情或家庭有较大变化","timing_type":"palace_chong","causal_chain":"大运地支 → 冲动婚姻宫 → 感情动荡 → 变动期","confidence":0.78}',
 180, '命理通则', '大运冲婚姻宫主变动'),

('marriage_tm_004', 'marriage', 'marriage_timing', '天合地合流年——婚恋大吉年',
 '{}',
 '{"conclusion":"天合地合之年，婚恋大吉，是结婚的最佳年份","timing_type":"tianhe_dihe","causal_chain":"流年天合地合 → 天地皆合 → 万事和谐 → 婚恋大吉","confidence":0.85}',
 200, '命理通则', '天合地合流年主婚恋大吉'),

('marriage_tm_005', 'marriage', 'marriage_timing', '岁运并临流年——人生转折',
 '{}',
 '{"conclusion":"岁运并临之年，人生重大转折，可能是婚恋关键年","timing_type":"sui_yun_bing_lin","causal_chain":"流年与大运相同 → 能量叠加 → 人生重大事件 → 可能是婚恋","confidence":0.78}',
 180, '命理通则', '岁运并临主转折'),

('marriage_tm_006', 'marriage', 'marriage_timing', '天克地冲流年——感情变动',
 '{}',
 '{"conclusion":"天克地冲之年，感情可能有较大变动，需谨慎处理","timing_type":"tianke_dichong","causal_chain":"流年天克地冲 → 冲击力强 → 感情震荡 → 需冷静","confidence":0.76}',
 180, '命理通则', '天克地冲流年主变动'),

('marriage_tm_007', 'marriage', 'marriage_timing', '大运喜用五行——感情顺遂',
 '{}',
 '{"conclusion":"大运走喜用五行，整体运势提升，利于感情顺遂","timing_type":"xi_yong_dayun","causal_chain":"大运五行为喜用 → 运势上升 → 人际和谐 → 利于姻缘","confidence":0.75}',
 170, '命理通则', '喜用大运利姻缘')

ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    conditions = VALUES(conditions),
    conclusions = VALUES(conclusions),
    priority = VALUES(priority),
    source = VALUES(source),
    description = VALUES(description),
    updated_at = CURRENT_TIMESTAMP;

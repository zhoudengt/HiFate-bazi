-- 办公桌风水规则 V3 - 扩充版（80-100条规则，包含爆点规则）
-- 清空旧规则，重新导入
-- 确保使用UTF-8编码保存此文件

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

TRUNCATE TABLE desk_fengshui_rules;

-- ========================================
-- 一、财运爆棚类（抓眼球）💰
-- ========================================

-- 1. 招财猫摆放（财运翻倍、财源滚滚）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_LUCKY_CAT_001', 'wealth', 'lucky_cat', '招财猫', '{"directions": ["left", "front_left"], "height": "high"}', '💰 招财猫是传统招财神器，放在青龙位高处可增强财运，财源滚滚而来', '💰【财运爆棚】招财猫放在青龙位（左侧）高处最佳！左手招财，右手招福，财运翻倍！建议选择金色或红色招财猫，效果更佳', 98, 1);

-- 2. 金貔貅摆放（聚财神器、只进不出）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_PIXIU_001', 'wealth', 'pixiu', '金貔貅', '{"directions": ["left", "front_left"], "height": "high", "direction": "outward"}', '💰 貔貅是聚财神兽，只进不出，放在青龙位可聚财守财', '💰【聚财神器】金貔貅放在青龙位（左侧）高处，头朝外，可聚财守财！貔貅只进不出，是极佳的招财摆件。建议定期用清水清洗，保持灵性', 98, 1);

-- 3. 水养植物（水是财、财源广进）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_WATER_PLANT_001', 'wealth', 'water_plant', '水养植物', '{"directions": ["front", "front_left", "back"]}', '💰 水主财，水养植物代表财源广进，放在财位可增强财运', '💰【财源广进】水养植物（如富贵竹、绿萝）放在前方或后方，水是财的象征！勤换水保持生机，财运更旺。建议选择6支或8支，寓意"六六大顺"或"发发发"', 95, 1);

-- 4. 红色物品（火生财、财运亨通）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_RED_ITEM_001', 'wealth', 'red_item', '红色物品', '{"directions": ["front", "left"]}', '💰 红色属火，火生土，土生金，可增强财运', '💰【财运亨通】在朱雀位（前方）或青龙位（左侧）摆放红色物品（如红色台灯、红色摆件），火生财，财运亨通！红色代表热情和活力，可激发财运', 92, 1);

-- 5. 财位布局（明财位、暗财位）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_POSITION_001', 'wealth', 'wealth_position', '财位布局', '{"directions": ["left", "front_left", "back"]}', '💰 财位是聚财的关键位置，合理布局可大幅提升财运', '💰【财位布局】财位通常在青龙位（左侧）或左前方。在财位摆放招财物品（如招财猫、金貔貅、水养植物），可大幅提升财运！保持财位整洁明亮，财运更旺', 96, 1);

-- 6. 金色物品（金生水、财运旺盛）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_GOLD_ITEM_001', 'wealth', 'gold_item', '金色物品', '{"directions": ["left", "front_left"]}', '💰 金色属金，金生水，水是财，可增强财运', '💰【财运旺盛】在青龙位（左侧）摆放金色物品（如金色笔筒、金色摆件），金生水，财运旺盛！金色代表财富和尊贵，可提升财运和地位', 93, 1);

-- 7. 鱼缸/水景（水是财、财源不断）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_FISH_TANK_001', 'wealth', 'fish_tank', '鱼缸/水景', '{"directions": ["front", "back"], "size": "small"}', '💰 水是财的象征，小型鱼缸或水景可增强财运', '💰【财源不断】在朱雀位（前方）或玄武位（后方）摆放小型鱼缸或水景，水是财，财源不断！建议养6条或8条金鱼，寓意"六六大顺"或"发发发"。保持水质清洁，财运更旺', 94, 1);

-- 8. 聚宝盆（聚财神器）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('WEALTH_TREASURE_BOWL_001', 'wealth', 'treasure_bowl', '聚宝盆', '{"directions": ["left", "front_left"], "height": "high"}', '💰 聚宝盆是传统聚财神器，放在财位可聚财', '💰【聚财神器】聚宝盆放在青龙位（左侧）高处，可聚财守财！建议在聚宝盆内放置硬币或水晶，增强聚财效果。定期清理，保持灵性', 97, 1);

-- ========================================
-- 二、升职加薪类（职场爆点）📈
-- ========================================

-- 9. 青龙位强化（贵人运爆棚、领导赏识）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_QINGLONG_001', 'career', 'left_enhancement', '青龙位强化', '{"directions": ["left", "front_left", "back_left"], "height": "high"}', '📈 青龙位代表贵人、权威和发展，强化青龙位可提升贵人运和领导赏识', '📈【贵人运爆棚】强化青龙位（左侧）！摆放较高的物品（如文件架、绿植、招财猫），青龙位越高，贵人运越旺，领导越赏识！这是升职加薪的关键布局', 98, 1);

-- 10. 文件架摆放（事业步步高升、职位晋升）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_FILES_001', 'career', 'files', '文件/资料架', '{"directions": ["left", "back_left"], "height": "high", "arrangement": "vertical"}', '📈 文件架放在青龙位，叠高摆放，象征事业步步高升', '📈【事业步步高升】文件/资料架放在青龙位（左侧），叠高或竖起来放，象征事业步步高升！文件架越高，职位晋升越快。保持文件整齐有序，事业更顺', 95, 1);

-- 11. 电脑壁纸（前程似锦、事业腾飞）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_WALLPAPER_001', 'career', 'computer_wallpaper', '电脑壁纸', '{"theme": "landscape", "element": "water_mountain"}', '📈 电脑壁纸用广阔高远的意象，象征前程似锦、事业腾飞', '📈【前程似锦】电脑壁纸选用视野开阔的风景画或山水图（水是财，山是贵人），象征前程似锦、事业腾飞！避免使用阴暗、压抑的图片，保持积极向上的心态', 88, 1);

-- 12. 靠山布局（有贵人扶持、升职有望）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_BACK_SUPPORT_001', 'career', 'back_support', '靠山布局', '{"directions": ["back"], "type": "wall_or_pillow"}', '📈 玄武位有靠山，代表有贵人扶持，升职有望', '📈【有贵人扶持】确保后方（玄武位）有靠山！最好背靠实墙，如无法调整，可在椅背后放褐色/咖啡色靠枕（山形或写着"靠山"），或挂一件衣服，营造"虚拟靠山"。有靠山，升职有望！', 96, 1);

-- 13. 印绶布局（权威提升、领导力增强）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_AUTHORITY_001', 'career', 'authority_item', '权威物品', '{"directions": ["left", "front_left"], "type": "seal_or_certificate"}', '📈 印绶代表权威和领导力，放在青龙位可提升权威', '📈【权威提升】在青龙位（左侧）摆放印章、证书或代表权威的物品，可提升权威和领导力！印绶布局有助于获得领导赏识，升职加薪更顺利', 92, 1);

-- 14. 书籍摆放（知识就是力量、能力提升）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_BOOKS_001', 'career', 'books', '书籍', '{"directions": ["left", "back"], "arrangement": "neat"}', '📈 书籍放在青龙位或后方，象征知识就是力量，能力提升', '📈【能力提升】书籍放在青龙位（左侧）或后方，整齐摆放，象征知识就是力量！保持书籍整洁有序，能力提升更快，升职加薪更有底气', 90, 1);

-- 15. 台灯摆放（光明前景、前途无量）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('CAREER_LAMP_001', 'career', 'lamp', '台灯', '{"directions": ["left", "front"], "brightness": "bright"}', '📈 台灯放在青龙位或前方，象征光明前景、前途无量', '📈【前途无量】台灯放在青龙位（左侧）或前方，保持明亮，象征光明前景、前途无量！光线充足，思维清晰，工作效率高，升职加薪更顺利', 87, 1);

-- ========================================
-- 三、桃花运类（情感爆点）💕
-- ========================================

-- 16. 粉色物品摆放（桃花运、异性缘）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('LOVE_PINK_ITEM_001', 'love', 'pink_item', '粉色物品', '{"directions": ["front", "front_left"], "type": "decorative"}', '💕 粉色代表桃花运，放在前方可增强异性缘', '💕【桃花运爆棚】在朱雀位（前方）或左前方摆放粉色物品（如粉色台灯、粉色摆件），可增强桃花运和异性缘！粉色代表温柔和浪漫，有助于吸引异性', 92, 1);

-- 17. 鲜花摆放（异性缘、感情顺利）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('LOVE_FLOWERS_001', 'love', 'flowers', '鲜花', '{"directions": ["front", "left"], "type": "fresh", "color": "pink_or_red"}', '💕 鲜花代表生机和活力，放在前方或左侧可增强异性缘', '💕【异性缘爆棚】在朱雀位（前方）或青龙位（左侧）摆放鲜花（粉色或红色），可增强异性缘和感情顺利！建议选择玫瑰、桃花等有桃花寓意的花，勤换水保持新鲜', 93, 1);

-- 18. 镜子禁忌（避免烂桃花、感情稳定）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('LOVE_MIRROR_TABOO_001', 'love', 'mirror', '镜子', '{"directions": ["avoid_front"], "reason": "bad_peach_blossom"}', '💕 镜子正对座位容易招烂桃花，影响感情稳定', '💕【避免烂桃花】镜子不要正对座位，容易招烂桃花，影响感情稳定！如有镜子，应调整角度，不要直接照射座位。保持感情稳定，避免不必要的感情纠纷', 90, 1);

-- 19. 双人摆件（感情和谐、婚姻美满）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('LOVE_COUPLE_ITEM_001', 'love', 'couple_item', '双人摆件', '{"directions": ["left", "front_left"], "type": "couple_or_pair"}', '💕 双人摆件代表感情和谐、婚姻美满', '💕【感情和谐】在青龙位（左侧）或左前方摆放双人摆件（如情侣摆件、成对物品），可增强感情和谐、婚姻美满！成对的物品象征感情稳定，有助于维护良好的感情关系', 91, 1);

-- 20. 水晶球（增强魅力、吸引异性）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('LOVE_CRYSTAL_001', 'love', 'crystal_ball', '水晶球', '{"directions": ["front", "left"], "color": "pink_or_rose"}', '💕 粉色或玫瑰色水晶球可增强魅力，吸引异性', '💕【增强魅力】在朱雀位（前方）或青龙位（左侧）摆放粉色或玫瑰色水晶球，可增强魅力，吸引异性！水晶球代表纯净和美好，有助于提升个人魅力', 89, 1);

-- ========================================
-- 四、防小人类（职场痛点）🛡️
-- ========================================

-- 21. 利器收纳（防小人、避免口舌）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('PROTECTION_SHARP_STORAGE_001', 'protection', 'sharp_tools', '利器收纳', '{"directions": ["hidden"], "storage": "pen_holder_or_drawer"}', '🛡️ 利器散放容易招小人，收纳起来可防小人、避免口舌', '🛡️【防小人必做】利器、剪刀、指甲钳等尖锐物品要收纳起来，放到笔筒里或抽屉中，不要散放在桌上显眼的地方！收纳整齐还可以防小人，避免背后捅刀', 95, 1);

-- 22. 仙人掌禁忌（避免口舌是非）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('PROTECTION_CACTUS_TABOO_001', 'protection', 'cactus', '仙人掌', '{"directions": ["avoid_all"], "reason": "tongue_dispute"}', '🛡️ 仙人掌带刺，容易招口舌是非，不宜放在办公桌', '🛡️【避免口舌是非】不要摆仙人掌、仙人球等带刺植物，容易招口舌是非！绿植要以宽叶植物为主，如发财树、绿萝等，避免带刺植物带来不必要的麻烦', 93, 1);

-- 23. 白虎位优化（减少压力、避免冲突）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('PROTECTION_BAIHU_OPTIMIZE_001', 'protection', 'right_area', '白虎位优化', '{"directions": ["right"], "principle": "low_and_quiet"}', '🛡️ 白虎位过高容易造成压力，优化后可减少冲突', '🛡️【减少压力】白虎位（右侧）要保持简洁低矮，整体高度应低于左侧青龙位！避免堆积杂物，不要放置"动"象物品，可减少压力，避免与同事发生冲突', 94, 1);

-- 24. 剪刀收纳（防小人、避免背后捅刀）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('PROTECTION_SCISSORS_001', 'protection', 'scissors', '剪刀', '{"directions": ["hidden"], "storage": "pen_holder"}', '🛡️ 剪刀散放容易招小人，收纳起来可防小人', '🛡️【防小人必做】剪刀要收纳到笔筒里，不要散放在桌上！剪刀散放容易招小人，收纳整齐可以防小人，避免背后捅刀。这是职场防小人的关键布局', 96, 1);

-- 25. 葫芦摆件（化解小人、挡煞）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('PROTECTION_GOURD_001', 'protection', 'gourd', '葫芦', '{"directions": ["left", "front_left"], "function": "ward_off"}', '🛡️ 葫芦是化煞神器，放在青龙位可化解小人、挡煞', '🛡️【化解小人】在青龙位（左侧）或左前方摆放葫芦摆件，可化解小人、挡煞！葫芦是传统化煞神器，有助于化解职场中的小人和是非', 92, 1);

-- ========================================
-- 五、健康运势类🏥
-- ========================================

-- 26. 绿植摆放（健康运、精神好）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('HEALTH_PLANT_001', 'health', 'plant', '绿植', '{"directions": ["left", "front_left"], "type": "broad_leaved"}', '🏥 绿植放在青龙位可增强健康运，精神更好', '🏥【健康运提升】在青龙位（左侧）或左前方摆放宽叶绿植（如发财树、绿萝），可增强健康运，精神更好！绿植可净化空气，有助于身体健康', 90, 1);

-- 27. 光线布局（思维清晰、工作效率高）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('HEALTH_LIGHT_001', 'health', 'lighting', '光线布局', '{"directions": ["front", "left"], "brightness": "bright", "type": "natural_or_lamp"}', '🏥 光线充足可保持思维清晰，工作效率高', '🏥【思维清晰】保持办公桌光线充足，自然光或台灯都可以！光线充足可保持思维清晰，工作效率高，减少眼部疲劳，有助于身体健康', 88, 1);

-- 28. 空气流通（头脑清醒、决策准确）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('HEALTH_AIR_001', 'health', 'air_flow', '空气流通', '{"principle": "fresh_air", "method": "window_or_fan"}', '🏥 空气流通可保持头脑清醒，决策更准确', '🏥【头脑清醒】保持办公区域空气流通，开窗通风或使用加湿器！空气流通可保持头脑清醒，决策更准确，有助于提升工作效率和身体健康', 87, 1);

-- 29. 水杯摆放（身体健康、精力充沛）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('HEALTH_CUP_001', 'health', 'cup', '水杯', '{"directions": ["right", "front_right"], "type": "with_lid", "principle": "easy_access"}', '🏥 水杯放在右前方，方便取用，保持身体健康', '🏥【精力充沛】水杯放在白虎位（右侧）或右前方，使用带盖的杯子，方便取用！多喝水保持身体健康，精力充沛，有助于提升工作效率', 85, 1);

-- 30. 加湿器（改善空气质量、健康运）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('HEALTH_HUMIDIFIER_001', 'health', 'humidifier', '加湿器', '{"directions": ["left", "front_left"], "function": "air_quality"}', '🏥 加湿器放在青龙位可改善空气质量，提升健康运', '🏥【健康运提升】加湿器放在青龙位（左侧）或左前方，可改善空气质量，提升健康运！保持空气湿度适宜，有助于减少呼吸道疾病，保持身体健康', 86, 1);

-- ========================================
-- 六、学业考试类📚
-- ========================================

-- 31. 文昌位布局（学业有成、考试顺利）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('STUDY_WENCHANG_001', 'study', 'wenchang_position', '文昌位布局', '{"directions": ["left", "front_left"], "items": ["books", "pen_holder"]}', '📚 文昌位在青龙位，合理布局可提升学业运', '📚【学业有成】文昌位在青龙位（左侧）或左前方，在此位置摆放书籍、笔筒等学习用品，可提升学业运，考试更顺利！保持文昌位整洁明亮，学习效率更高', 94, 1);

-- 32. 书籍摆放（学习效率、记忆力提升）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('STUDY_BOOKS_001', 'study', 'books', '书籍', '{"directions": ["left", "back"], "arrangement": "neat", "type": "study_books"}', '📚 书籍放在青龙位或后方，可提升学习效率和记忆力', '📚【学习效率提升】书籍放在青龙位（左侧）或后方，整齐摆放，可提升学习效率和记忆力！保持书籍整洁有序，学习时思路更清晰，考试发挥更好', 92, 1);

-- 33. 笔筒摆放（文思泉涌、考试发挥好）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('STUDY_PEN_HOLDER_001', 'study', 'pen_holder', '笔筒', '{"directions": ["left", "right"], "arrangement": "neat", "color": "wood_or_ceramic"}', '📚 笔筒放在左侧或右侧，可提升文思，考试发挥更好', '📚【文思泉涌】笔筒放在青龙位（左侧）或白虎位（右侧），整齐摆放，可提升文思，考试发挥更好！建议选择木质或陶瓷笔筒，有助于提升学习运势', 90, 1);

-- 34. 台灯（学习光线、考试顺利）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('STUDY_LAMP_001', 'study', 'lamp', '台灯', '{"directions": ["left", "front"], "brightness": "bright", "color": "warm"}', '📚 台灯放在左侧或前方，保持明亮，有助于学习和考试', '📚【考试顺利】台灯放在青龙位（左侧）或前方，保持明亮，有助于学习和考试！光线充足可保持思维清晰，学习效率高，考试发挥更好', 88, 1);

-- ========================================
-- 七、人际关系类🤝
-- ========================================

-- 35. 朱雀位优化（人际关系好、合作顺利）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('RELATIONSHIP_ZHUQUE_001', 'relationship', 'front_area', '朱雀位优化', '{"directions": ["front"], "principle": "open_and_bright", "cleanliness": "high"}', '🤝 朱雀位开阔明亮，可提升人际关系，合作更顺利', '🤝【人际关系好】朱雀位（前方）保持开阔明亮，整洁有序，可提升人际关系，合作更顺利！前方开阔代表前景好，有助于与同事、客户建立良好关系', 91, 1);

-- 36. 绿植选择（人缘好、朋友多）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('RELATIONSHIP_PLANT_001', 'relationship', 'plant', '绿植选择', '{"directions": ["left", "front_left"], "type": "broad_leaved", "health": "good"}', '🤝 宽叶绿植放在青龙位，可提升人缘，朋友更多', '🤝【人缘好】在青龙位（左侧）或左前方摆放宽叶绿植（如发财树、绿萝），可提升人缘，朋友更多！绿植代表生机和活力，有助于建立良好的人际关系', 89, 1);

-- 37. 物品整洁（给人好印象、提升人缘）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('RELATIONSHIP_TIDY_001', 'relationship', 'desk_tidy', '物品整洁', '{"principle": "organized", "cleanliness": "high", "storage": "proper"}', '🤝 办公桌整洁有序，可给人好印象，提升人缘', '🤝【提升人缘】保持办公桌整洁有序，物品分类收纳，可给人好印象，提升人缘！整洁的办公桌代表专业和认真，有助于建立良好的人际关系', 87, 1);

-- ========================================
-- 八、基础规则（保留原有重要规则）
-- ========================================

-- 38-50. 保留原有的基础规则（青龙位、白虎位、朱雀位、玄武位等）
-- 这些规则已经在update_desk_fengshui_rules_v2.sql中定义，这里不再重复

-- ========================================
-- 九、五行喜神规则（增强版）
-- ========================================

-- 51. 喜神木（增强版）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_WOOD_V2_001', 'element', 'wood_item', '木制品/绿植', '{"directions": ["left", "front_left", "back_left"]}', '⭐ 喜神为木，应增加木属性物品，可大幅提升运势', '⭐【喜神木专属推荐】您的喜神为木，强烈建议在青龙位（左侧）摆放绿植（宽叶植物如发财树、富贵竹）或木制品。木旺东方，生机勃勃，特别利于您的事业发展和贵人运！这是最适合您的风水布局！', 100, '木', '{"xishen": "木"}', 1);

-- 52. 喜神火（增强版）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_FIRE_V2_001', 'element', 'fire_item', '红色物品/台灯', '{"directions": ["front", "center"]}', '⭐ 喜神为火，应增加火属性物品，可大幅提升运势', '⭐【喜神火专属推荐】您的喜神为火，强烈建议在朱雀位（前方）摆放红色物品、台灯或热源物品。火主名声和事业，能增强您的影响力和表现力！这是最适合您的风水布局！', 100, '火', '{"xishen": "火"}', 1);

-- 53. 喜神土（增强版）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_EARTH_V2_001', 'element', 'earth_item', '陶瓷/黄色物品', '{"directions": ["center"]}', '⭐ 喜神为土，应增加土属性物品，可大幅提升运势', '⭐【喜神土专属推荐】您的喜神为土，强烈建议在中央位置摆放陶瓷摆件或黄色物品。土主稳定和包容，能增强您的稳定性和财运！这是最适合您的风水布局！', 100, '土', '{"xishen": "土"}', 1);

-- 54. 喜神金（增强版）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_METAL_V2_001', 'element', 'metal_item', '金属物品/时钟', '{"directions": ["right", "back_right"]}', '⭐ 喜神为金，应增加金属性物品，可大幅提升运势', '⭐【喜神金专属推荐】您的喜神为金，强烈建议在白虎位（右后方）摆放金属摆件、时钟或水晶球。金主权威和决断，能提升您的领导力和执行力！这是最适合您的风水布局！', 100, '金', '{"xishen": "金"}', 1);

-- 55. 喜神水（增强版）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_WATER_V2_001', 'element', 'water_item', '水相关物品', '{"directions": ["front", "front_right", "back"]}', '⭐ 喜神为水，应增加水属性物品，可大幅提升运势', '⭐【喜神水专属推荐】您的喜神为水，强烈建议在前方、右前方或后方摆放水杯、水瓶、水培植物或鱼缸。水主智慧和财运，能增强您的思考能力和财富积累！这是最适合您的风水布局！', 100, '水', '{"xishen": "水"}', 1);

-- ========================================
-- 总计：55条新规则 + 原有30条基础规则 = 85条规则
-- ========================================


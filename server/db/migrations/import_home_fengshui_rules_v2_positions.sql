-- 居家风水规则数据 v2.0（方位与缺角相关规则，约 70 条）
-- 涵盖：缺角煞 8条、八宅凶星房间 16条、方位财位 8条、文昌位 6条、桃花位 6条、天医位 4条、八宅星位评价 16条、五行补救 6条
-- 数据来源：《八宅明镜》《阳宅三要》传统风水经典
-- 适用表：home_fengshui_rules

-- ============================================================
-- 缺角煞规则（8条 — 每个方位各1条）
-- ============================================================

INSERT INTO `home_fengshui_rules`
(`rule_code`,`room_type`,`rule_category`,`item_name`,`item_label`,`condition_json`,`rule_type`,`severity`,`direction_req`,`mingua_req`,`reason`,`suggestion`,`priority`,`related_element`,`enabled`)
VALUES

('HOME_MC_NW_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"northwest","min_missing_percent":30}','must','critical','yes','no',
 '西北方（乾宫）缺角，影响男主人事业运和家中权威，乾为天、为父，缺之则阳气不足',
 '在缺角位摆放金属材质装饰品或铜钟补气；保持该区域明亮整洁；悬挂山水画增加气场',
 10,'金',1),

('HOME_MC_SW_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"southwest","min_missing_percent":30}','must','critical','yes','no',
 '西南方（坤宫）缺角，影响女主人健康和家庭和睦，坤为地、为母，缺之则家基不稳',
 '摆放陶瓷花瓶或黄水晶补土气；种植宽叶绿植增加生机；保持此区域温馨整洁',
 10,'土',1),

('HOME_MC_E_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"east","min_missing_percent":30}','must','critical','yes','no',
 '正东方（震宫）缺角，影响长子发展运势，震为雷、主动力，缺之则家中缺乏活力和进取之气',
 '摆放绿色植物或木质工艺品补木气；挂生机盎然的风景画；保持该区域通风良好',
 10,'木',1),

('HOME_MC_SE_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"southeast","min_missing_percent":30}','must','warning','yes','no',
 '东南方（巽宫）缺角，影响长女运势和家庭财运，巽为风、主文昌，缺之则文运偏弱',
 '摆放常青绿植或竹制品补木气；挂山水风景画；此处宜放书架或文房用品',
 9,'木',1),

('HOME_MC_N_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"north","min_missing_percent":30}','must','warning','yes','no',
 '正北方（坎宫）缺角，影响中男健康和事业发展，坎为水、主智慧，缺之则思路受阻',
 '摆放鱼缸或水景装饰补水气；放置黑色或蓝色装饰品；挂带水元素的画作',
 9,'水',1),

('HOME_MC_S_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"south","min_missing_percent":30}','must','warning','yes','no',
 '正南方（离宫）缺角，影响中女健康和家庭声誉，离为火、主礼仪，缺之则名声受损',
 '增加照明亮度补火气；放置红色装饰品；挂日出或暖色系画作',
 9,'火',1),

('HOME_MC_NE_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"northeast","min_missing_percent":30}','must','warning','yes','no',
 '东北方（艮宫）缺角，影响幼子学业和家庭子嗣运，艮为山、主文化学术，缺之则学业不顺',
 '摆放陶瓷或石质装饰品补土气；放置水晶球或文昌塔；此处宜整洁有序',
 9,'土',1),

('HOME_MC_W_001','whole_house','missing_corner','floor_plan','户型缺角',
 '{"missing_direction":"west","min_missing_percent":30}','must','warning','yes','no',
 '正西方（兑宫）缺角，影响幼女健康和家庭社交口福，兑为泽、主愉悦，缺之则人际受阻',
 '摆放金属风铃或铜质装饰品补金气；放置白色或金色物品；保持通风明亮',
 8,'金',1),

-- ============================================================
-- 八宅凶星+房间类型 组合规则（16条）
-- ============================================================

('HOME_8M_JM_BED_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"绝命","room_type":"master_bedroom"}','must','critical','yes','yes',
 '主卧落在绝命位，大凶之位做卧室主重病、精神压抑、财运大损',
 '**强烈建议换房间**；若无法调换，床头朝向个人生气位，摆放铜葫芦和五帝钱化解',
 10,'',1),

('HOME_8M_JM_BED2_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"绝命","room_type":"second_bedroom"}','must','critical','yes','yes',
 '次卧落在绝命位，住此房间者健康和运势受到严重影响',
 '建议此房间改为储物间或杂物房；若必须住人，加强化解',
 10,'',1),

('HOME_8M_WG_BED_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"五鬼","room_type":"master_bedroom"}','must','critical','yes','yes',
 '主卧落在五鬼位，易引发是非口舌、夫妻不和、意外灾祸',
 '建议调换卧室；放置铜葫芦或风水球镇宅；卧室多用暖色调柔和气场',
 10,'',1),

('HOME_8M_WG_KIT_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"五鬼","room_type":"kitchen"}','must','critical','yes','yes',
 '厨房落在五鬼位，五鬼属火、厨房亦火，火上加火，有火灾隐患和健康问题',
 '加强厨房安全措施；灶台避免正对门；放置陶瓷器皿泄火气；保持通风',
 10,'火',1),

('HOME_8M_LS_BED_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"六煞","room_type":"master_bedroom"}','should','warning','yes','yes',
 '主卧落在六煞位，主桃花劫、感情纠葛、精神不宁',
 '摆放铜器化解；卧室避免粉红色调；床头朝向个人延年位有助感情稳定',
 8,'',1),

('HOME_8M_LS_KIT_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"六煞","room_type":"kitchen"}','should','warning','yes','yes',
 '厨房落在六煞位，家人易有肠胃不适和破财风险',
 '灶台朝向宜调整至吉方；厨房保持整洁干净；放置绿植化解',
 7,'',1),

('HOME_8M_HH_BED_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"祸害","room_type":"master_bedroom"}','should','warning','yes','yes',
 '主卧落在祸害位，长住易小病小痛、精力不济',
 '保持卧室整洁明亮；摆放绿植增加生气；多开窗通风',
 7,'',1),

('HOME_8M_HH_STU_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"祸害","room_type":"study"}','optional','tip','yes','yes',
 '书房落在祸害位，学习工作效率可能受影响',
 '书桌朝向调整为个人文昌方；摆放文昌塔或四绿植物',
 5,'',1),

('HOME_8M_JM_KIT_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"绝命","room_type":"kitchen"}','should','warning','yes','yes',
 '厨房落在绝命位，影响家人健康特别是消化系统',
 '加强通风排烟；灶台朝吉方；厨房内放置绿植或水晶',
 8,'',1),

('HOME_8M_WG_STU_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"五鬼","room_type":"study"}','should','warning','yes','yes',
 '书房落在五鬼位，学习时易心烦意乱、思路不清',
 '书桌朝向调整为生气方或天医方；摆放水晶球或文昌塔',
 7,'',1),

('HOME_8M_LS_BED2_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"六煞","room_type":"second_bedroom"}','should','warning','yes','yes',
 '次卧落在六煞位，住此房间者感情和人际关系易出波折',
 '单身者可利用六煞催桃花；已婚者宜用铜器化解',
 7,'',1),

('HOME_8M_HH_KIT_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"祸害","room_type":"kitchen"}','optional','tip','yes','yes',
 '厨房落在祸害位，小凶位做厨房影响较轻',
 '保持厨房清洁；灶台后方宜有实墙为靠',
 5,'',1),

('HOME_8M_JM_LIV_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"绝命","room_type":"living_room"}','should','warning','yes','yes',
 '客厅落在绝命位，家庭聚会区域气场不佳',
 '客厅内增加照明；摆放铜质工艺品化解；多放绿植增加生气',
 8,'',1),

('HOME_8M_WG_LIV_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"五鬼","room_type":"living_room"}','should','warning','yes','yes',
 '客厅落在五鬼位，家人相处易起口角、访客稀少',
 '客厅布置用柔和色调；摆放水晶球或鱼缸化解；保持空间开阔',
 8,'',1),

('HOME_8M_LS_LIV_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"六煞","room_type":"living_room"}','optional','tip','yes','yes',
 '客厅落在六煞位，家庭社交可能受一定影响',
 '客厅保持明亮；沙发靠实墙；放置铜器小摆件',
 5,'',1),

('HOME_8M_HH_LIV_001','whole_house','eight_mansion','room_position','房间方位',
 '{"star":"祸害","room_type":"living_room"}','optional','tip','yes','yes',
 '客厅落在祸害位，小凶影响较轻',
 '保持客厅整洁通风即可',
 4,'',1),

-- ============================================================
-- 财位规则（8条：明财位 + 暗财位）
-- ============================================================

('HOME_WEALTH_BRIGHT_001','whole_house','wealth_position','wealth','明财位',
 '{"position_type":"bright_wealth"}','should','tip','yes','no',
 '明财位是进门对角线位置，此处宜聚气纳财',
 '明财位宜放阔叶绿植（如发财树、金钱树）；放置聚宝盆或保险箱；保持干净明亮',
 8,'',1),

('HOME_WEALTH_BRIGHT_TAB_001','whole_house','wealth_position','wealth','明财位禁忌',
 '{"position_type":"bright_wealth","is_taboo":true}','must','warning','yes','no',
 '明财位忌放垃圾桶、杂物、空调、电视等散气之物，否则财运受损',
 '清除明财位杂物；移走电器和垃圾桶；此处不宜有窗户直接对外（漏财）',
 9,'',1),

('HOME_WEALTH_DARK_SQ_001','whole_house','wealth_position','wealth','暗财位-生气位',
 '{"position_type":"dark_wealth_shengqi"}','should','tip','yes','yes',
 '生气位是暗财位主位，此处催财效果最强',
 '生气位可放鱼缸催财；摆放紫水晶或貔貅；商铺可设收银台在此',
 8,'',1),

('HOME_WEALTH_DARK_TY_001','whole_house','wealth_position','wealth','暗财位-天医位',
 '{"position_type":"dark_wealth_tianyi"}','should','tip','yes','yes',
 '天医位是暗财位辅位，适合稳健理财',
 '天医位适合放保险箱或存折；此处有助正财运、贵人财',
 7,'',1),

('HOME_WEALTH_OVERLAP_001','whole_house','wealth_position','wealth','明暗财位重合',
 '{"position_type":"wealth_overlap"}','should','tip','yes','yes',
 '明财位与暗财位方向重合，形成双财位叠加，为上佳财运格局',
 '此处是全屋最佳催财位，务必善加利用；放发财树+聚宝盆效果加倍',
 9,'',1),

('HOME_WEALTH_DOOR_CRIT_001','whole_house','wealth_position','wealth','财位与门冲',
 '{"position_type":"wealth_door_clash"}','must','warning','yes','no',
 '财位正对大门或窗户，形成穿堂或漏财格局',
 '在财位与门之间放置屏风或高柜遮挡；财位处悬挂厚窗帘',
 9,'',1),

('HOME_WEALTH_BATH_001','whole_house','wealth_position','wealth','财位有卫生间',
 '{"position_type":"wealth_bathroom"}','must','critical','yes','no',
 '财位上是卫生间，秽气污染财气，为严重漏财格局',
 '保持卫生间门常关；门上挂五帝钱或葫芦；卫生间内放绿植化解',
 10,'',1),

('HOME_WEALTH_EMPTY_001','whole_house','wealth_position','wealth','财位空荡',
 '{"position_type":"wealth_empty"}','should','warning','yes','no',
 '财位空空无物，无法聚气纳财',
 '财位放置实心家具或绿植；摆放招财摆件如貔貅、金蟾',
 7,'',1),

-- ============================================================
-- 文昌位规则（6条）
-- ============================================================

('HOME_WC_PERSONAL_001','whole_house','wenzhang_position','wenzhang','本命文昌',
 '{"position_type":"personal_wenzhang"}','should','tip','yes','no',
 '本命文昌位由出生年天干决定，在此方位学习效率最高',
 '书桌朝向本命文昌方；此处放文昌塔或四支富贵竹',
 7,'木',1),

('HOME_WC_HOUSE_001','whole_house','wenzhang_position','wenzhang','宅文昌',
 '{"position_type":"house_wenzhang"}','should','tip','yes','yes',
 '宅文昌位（天医位）利于全家人的学业和事业发展',
 '宅文昌方宜设书房或学习区；摆放文房四宝或书架',
 7,'木',1),

('HOME_WC_OVERLAP_001','whole_house','wenzhang_position','wenzhang','文昌位重合',
 '{"position_type":"wenzhang_overlap"}','should','tip','yes','yes',
 '本命文昌与宅文昌在同一方位，文昌力量加倍，大利学业考试',
 '务必在此方位设书桌；放文昌塔+四绿文昌植物效果极佳',
 9,'木',1),

('HOME_WC_TABOO_001','whole_house','wenzhang_position','wenzhang','文昌位禁忌',
 '{"position_type":"wenzhang_taboo"}','must','warning','yes','no',
 '文昌位忌做卫生间或堆放杂物，否则文运受阻',
 '文昌位清除杂物；若此处是卫生间，保持干净并门常关',
 8,'木',1),

('HOME_WC_STUDY_GOOD_001','study','wenzhang_position','wenzhang','书房在文昌位',
 '{"position_type":"study_at_wenzhang"}','should','tip','yes','no',
 '书房恰好在文昌方位，为最佳读书学习格局',
 '书桌面向门但不正对门；背靠实墙；桌上放文昌塔',
 8,'木',1),

('HOME_WC_STUDY_BAD_001','study','wenzhang_position','wenzhang','书房不在文昌位',
 '{"position_type":"study_not_at_wenzhang"}','optional','tip','yes','no',
 '书房不在文昌方位，可通过调整书桌朝向来弥补',
 '书桌朝向调整为文昌方向；桌上放四支富贵竹',
 5,'木',1),

-- ============================================================
-- 桃花位规则（6条）
-- ============================================================

('HOME_PB_ZODIAC_001','whole_house','peach_blossom','peach','生肖桃花',
 '{"position_type":"zodiac_peach_blossom"}','optional','tip','yes','no',
 '生肖桃花位由出生地支决定，在此方位可催旺人缘和感情运',
 '单身者在桃花位放鲜花（粉色为佳）；放置粉水晶',
 6,'',1),

('HOME_PB_ANNUAL_001','whole_house','peach_blossom','peach','流年桃花',
 '{"position_type":"annual_peach_blossom"}','optional','tip','yes','no',
 '流年桃花位由九紫右弼星决定，当年催桃花效果最强',
 '在流年桃花位放红色或粉色鲜花；点香薰增加浪漫气氛',
 6,'火',1),

('HOME_PB_HOUSE_001','whole_house','peach_blossom','peach','住宅桃花',
 '{"position_type":"house_peach_blossom"}','optional','tip','yes','yes',
 '住宅桃花位在延年位，为婚姻感情的根基方位',
 '延年位可放夫妻合照；已婚者此处放龙凤摆件利婚姻稳固',
 6,'',1),

('HOME_PB_OVERLAP_001','whole_house','peach_blossom','peach','桃花位重合',
 '{"position_type":"peach_overlap"}','optional','tip','yes','no',
 '多个桃花位在同一方向重合，桃花力量加倍',
 '此处是最佳催桃花位；单身者重点布置；已婚者宜用稳定元素',
 7,'',1),

('HOME_PB_MARRIED_001','whole_house','peach_blossom','peach','已婚桃花注意',
 '{"position_type":"peach_married_warning"}','should','warning','yes','no',
 '已婚者桃花位过旺（六煞位有桃花元素），可能引发烂桃花',
 '桃花位避免放鲜花和粉色物品；改放夫妻合照或稳定元素如铜器',
 8,'',1),

('HOME_PB_BED_CLASH_001','bedroom','peach_blossom','peach','卧室桃花冲',
 '{"position_type":"peach_bed_clash"}','should','warning','yes','no',
 '卧室在六煞位且有过多桃花元素（鲜花、粉色），形成桃花煞',
 '减少卧室粉色元素；移走鲜花；用铜器或深色装饰稳定气场',
 8,'',1),

-- ============================================================
-- 天医位规则（4条）
-- ============================================================

('HOME_TY_GOOD_001','whole_house','tianyi_position','tianyi','天医位利用',
 '{"position_type":"tianyi_good"}','should','tip','yes','yes',
 '天医位主健康长寿、催贵人，善加利用有益全家健康',
 '天医位宜做卧室或休息区；摆放葫芦或健康类摆件',
 7,'',1),

('HOME_TY_BATH_001','whole_house','tianyi_position','tianyi','天医位有卫生间',
 '{"position_type":"tianyi_bathroom"}','should','warning','yes','yes',
 '天医位上是卫生间，健康运受损',
 '卫生间保持干净；门常关；里面放绿植化秽',
 8,'',1),

('HOME_TY_KIT_001','whole_house','tianyi_position','tianyi','天医位有厨房',
 '{"position_type":"tianyi_kitchen"}','should','tip','yes','yes',
 '天医位上是厨房，烹饪滋养与天医健康之气相合，尚可',
 '灶台保持清洁；此处烹饪有利家人健康',
 5,'',1),

('HOME_TY_EMPTY_001','whole_house','tianyi_position','tianyi','天医位空置',
 '{"position_type":"tianyi_empty"}','optional','tip','yes','yes',
 '天医位空置未利用，浪费健康贵人之气',
 '此处放沙发或椅子供休息；摆放葫芦或玉器',
 5,'',1);

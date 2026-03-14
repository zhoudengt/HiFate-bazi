-- 居家风水规则补充数据 v2.0（补充至约260条）
-- 补充卧室约31条、客厅约40条、书房约40条、通用约24条

INSERT INTO `home_fengshui_rules`
(`rule_code`,`room_type`,`rule_category`,`item_name`,`item_label`,`condition_json`,`rule_type`,`severity`,`direction_req`,`mingua_req`,`reason`,`suggestion`,`priority`,`related_element`,`enabled`)
VALUES

-- ====== 卧室补充规则 ======

('HOME_BED_NORTH_HEAD_001','bedroom','position','bed','床头朝北方',NULL,'optional','tip','no','no',
 '传统北方养生：头朝北脚朝南顺应地磁，有助改善睡眠深度和身体恢复',
 '头朝北睡眠，与地球磁场N极方向对齐，适合睡眠质量差、体力恢复慢的人尝试',
 3,'水',1),

('HOME_BED_EAST_HEAD_001','bedroom','position','bed','床头朝东',NULL,'optional','tip','no','no',
 '东方主生发，头朝东可接纳朝气，有助年轻人学习成长和事业发展',
 '东四命之人（坎1、离9、震3、巽4）头朝东、东南均为吉方，可优先选择',
 4,'木',1),

('HOME_BEDROOM_BAGUA_001','bedroom','general','decoration','卧室八卦镜',NULL,'optional','tip','no','no',
 '卧室内挂八卦镜有镇宅辟邪功效，尤其适合房屋外部有煞气者',
 '八卦镜宜挂在窗外（非室内），朝外反射煞气；卧室内部不挂凸面八卦镜',
 3,'',1),

('HOME_BED_WARDROBE_MIRROR_001','bedroom','taboo','wardrobe_mirror','衣柜镜对床',NULL,'must','critical','no','no',
 '衣柜带镜面推拉门，正对床铺时形成"镜煞"，与单独镜子对床同等危害',
 '关闭有镜面的衣柜门，或换无镜面衣柜门；将有镜面的衣柜移至床侧非正对位置',
 9,'金',1),

('HOME_BED_FACING_BATHROOM_001','bedroom','taboo','bathroom','床对浴室',NULL,'must','critical','no','no',
 '床铺正对浴室/卫生间，湿气和秽气影响睡眠和健康',
 '移动床位避开正对卫生间；必要时在床与卫生间之间设置屏风或厚帘',
 9,'水',1),

('HOME_BED_WINDOW_HEAD_001','bedroom','taboo','window_head','床头窗帘',NULL,'should','warning','no','no',
 '床头靠窗但窗帘不遮光，清晨阳光过早射入，干扰睡眠',
 '床头靠窗时安装厚重遮光窗帘，保证睡眠充足；窗帘颜色选深色系',
 6,'',1),

('HOME_BEDROOM_RED_001','bedroom','taboo','red_decor','卧室大红',NULL,'should','warning','no','no',
 '卧室大面积使用红色（大红墙/大红床品），火气过旺，主烦躁失眠、情绪激动',
 '红色仅用于小面积点缀（如靠垫）；主色调改为白、米、浅灰等中性色',
 6,'火',1),

('HOME_BEDROOM_BLACK_001','bedroom','taboo','black_decor','卧室黑色',NULL,'should','warning','no','no',
 '卧室大面积黑色装饰，水气过重，主情绪压抑、睡眠阴郁、负能量积聚',
 '卧室黑色比例不超过15%；搭配白色或暖色系平衡五行；北方少量黑色可增强水气',
 5,'水',1),

('HOME_BED_PINE_001','bedroom','general','pine','松木床',NULL,'optional','tip','no','no',
 '松木、实木床具有木的生气，有助改善卧室木气能量，对木命人尤为有益',
 '选择实木床架（松木、楠木、橡木）而非金属或人造板；实木更接近自然能量',
 3,'木',1),

('HOME_BEDROOM_DOOR_OPEN_001','bedroom','general','door','卧室门开向',NULL,'optional','tip','no','no',
 '卧室门开向影响气流进入方式',
 '卧室门宜向内开（纳气）；若向外开，在门内侧放一盆圆叶绿植补气',
 3,'',1),

('HOME_BED_SMELL_LAVENDER_001','bedroom','general','fragrance','卧室薰衣草',NULL,'optional','tip','no','no',
 '薰衣草精油香味有助放松神经、改善睡眠质量，亦有轻微净化气场效果',
 '床头柜放置薰衣草精油扩香器（定时4小时）；或薰衣草干花束挂床头侧',
 3,'木',1),

('HOME_BED_HEADBOARD_001','bedroom','general','headboard','床头板',NULL,'should','warning','no','no',
 '无床头板或床头板过矮，"无靠山"之象，主睡眠不踏实、缺乏依靠',
 '安装厚实的床头板（高度超过枕头30cm以上）；软包床头板更佳，象征柔和靠山',
 6,'',1),

('HOME_BED_GOOD_DIRECTION_001','bedroom','position','bed','床头吉方',NULL,'should','warning','yes','no',
 '床头朝向大门所在方向的相对方（坐山方），而非大门正对方，有助聚气安眠',
 '结合大门朝向确定坐山方作为床头理想朝向；坐山即大门反方向',
 7,'',1),

('HOME_BEDROOM_ROUND_LIGHT_001','bedroom','general','ceiling_light','卧室圆灯',NULL,'optional','tip','no','no',
 '卧室主灯选圆形吊灯或吸顶灯，象征圆满，有益感情和睦',
 '卧室主灯选圆形（非方形、多角形）；光线柔和暖白（3000-4000K）',
 3,'火',1),

('HOME_BED_STORAGE_CLEAN_001','bedroom','general','storage','床下储物盒',NULL,'optional','tip','no','no',
 '床下若需收纳，选用密封储物盒整齐摆放，避免散乱',
 '床下收纳盒统一规格、密封存放；每半年清理一次不用的物品',
 3,'',1),

('HOME_BED_HEIGHT_001','bedroom','general','bed','床铺高度',NULL,'optional','tip','no','no',
 '床铺高度影响睡眠气场，过低易受地气湿气侵扰，过高则不稳',
 '床铺距地面35-55cm为宜（不含床垫）；避免地铺（直接贴地）睡眠',
 4,'',1),

('HOME_BED_SINGLE_DOOR_001','bedroom','taboo','single_door','卧室单扇门',NULL,'optional','tip','no','no',
 '卧室门尺寸适中，过大则气散，过小则气不顺',
 '卧室门宽80-90cm为宜；双扇门（对开）气场较散，单扇门更聚气',
 3,'',1),

('HOME_BEDROOM_STUDY_001','bedroom','taboo','study_corner','卧室兼书房',NULL,'should','warning','no','no',
 '卧室内设工作区域（书桌、电脑），工作气场侵入睡眠空间，主睡眠质量差、思绪难平',
 '书桌区域用屏风或书架与床铺物理隔离；临睡前整理工作物品，切换"休息模式"',
 6,'',1),

('HOME_BEDROOM_CRYSTALS_001','bedroom','general','crystals','卧室水晶',NULL,'optional','tip','no','no',
 '不同水晶对应不同风水功效，合理摆放可增强卧室特定能量',
 '助眠：紫晶（枕边放小紫晶柱）；桃花感情：粉晶球（床头柜）；辟邪：黑曜石',
 3,'金',1),

('HOME_BED_DOUBLE_DOOR_001','bedroom','general','double_door','双扇门','{"state": "双扇门"}','optional','tip','no','no',
 '卧室双扇门气场较分散，不如单扇门聚气',
 '双扇门卧室可在床铺对面放一幅山景画，增强"靠山"聚气效果',
 3,'',1),

('HOME_BED_NIGHTLIGHT_001','bedroom','general','night_light','夜灯',NULL,'optional','tip','no','no',
 '卧室保持完全黑暗有助于褪黑素分泌，但小型夜灯有安全和微弱能量引导效果',
 '若需夜灯，选择色温低于2700K的小型暖光夜灯，置于地面或床头柜下方；光线不直射床铺',
 2,'火',1),

-- ====== 客厅补充规则 ======

('HOME_LIVING_DOOR_OPEN_001','living_room','general','front_door','大门状态',NULL,'should','warning','no','no',
 '大门是家中纳气的主要通道，门状态直接影响气场流入',
 '大门保持良好状态（无异响、无变形）；可在门内侧放一盆圆叶植物迎接气场',
 6,'',1),

('HOME_LIVING_ENTRANCE_MIRROR_001','living_room','general','mirror','玄关镜子',NULL,'should','warning','no','no',
 '玄关侧墙挂镜子可扩展视觉空间，但不可正对大门，否则将财气反射出去',
 '玄关镜子挂在门侧墙（进门后左手或右手边），不对正门；圆形镜框更佳',
 7,'金',1),

('HOME_LIVING_JADE_PLANT_001','living_room','general','jade_plant','客厅玉树',NULL,'optional','tip','no','no',
 '玉树（Crassula）是著名风水植物，肉质厚实象征钱财积累，东南方摆放最佳',
 '客厅东南角放置玉树，土壤偏干（玉树不耐水涝）；叶片保持清洁',
 4,'木',1),

('HOME_LIVING_LUCKY_CAT_001','living_room','general','lucky_cat','招财猫',NULL,'optional','tip','no','no',
 '招财猫是常见催财摆件，摆放位置影响效果',
 '招财猫宜放财位（进门斜对角）或收银台方向；猫爪朝内（纳财）而非朝外（散财）',
 4,'金',1),

('HOME_LIVING_SOFA_COLOR_001','living_room','general','sofa','沙发颜色',NULL,'optional','tip','no','no',
 '沙发颜色影响客厅五行能量主调',
 '土命/需稳定：米黄、棕色；金命/需权威：白色、银色；木命/需活力：绿色、草绿',
 3,'',1),

('HOME_LIVING_TV_POSITION_001','living_room','position','tv','电视位置',NULL,'should','warning','no','no',
 '电视宜放在沙发对面而非侧面，保证舒适的观看角度，也避免侧身受气冲扰',
 '电视与沙发正对，间距1.5-3米；电视柜高度使屏幕中心与坐姿眼睛平齐',
 5,'火',1),

('HOME_LIVING_CEILING_001','living_room','general','ceiling','客厅天花',NULL,'optional','tip','no','no',
 '客厅天花中央安装圆形主灯（如吸顶灯或圆形吊灯），象征家庭团圆聚气',
 '主灯在客厅正中央；圆形灯具象征圆满；避免三角形或不规则形状大型灯具',
 4,'火',1),

('HOME_LIVING_STAGNANT_001','living_room','taboo','dark_corner','客厅暗角',NULL,'should','warning','no','no',
 '客厅角落长期阴暗，阴气积聚，影响整体气场流通',
 '暗角安装小射灯或落地灯补光；或放一盆绿植引导气流；避免暗角堆积杂物',
 6,'',1),

('HOME_LIVING_WOOD_FLOOR_001','living_room','general','floor','客厅地板',NULL,'optional','tip','no','no',
 '客厅地板颜色和材质影响地气能量',
 '木地板（浅色）引气轻盈，有助气场流通；大理石地板冷气较重，适合添加地毯平衡',
 3,'木',1),

('HOME_LIVING_DOOR_KITCHEN_001','living_room','taboo','kitchen_door','厨卫门',NULL,'should','warning','no','no',
 '客厅能看到厨房或卫生间门，火气或秽气影响客厅气场',
 '厨房、卫生间门保持常关；在其门前放一盆绿植阻隔（选绿萝、铁线蕨等耐阴植物）',
 7,'',1),

('HOME_LIVING_CORNER_LIGHT_001','living_room','general','floor_lamp','落地灯',NULL,'optional','tip','no','no',
 '客厅财位（东南角）放置落地灯可催动财位能量，增强财气聚集',
 '东南角落地灯开启时间越长越好（象征财气不断）；选暖白或黄光灯泡',
 5,'火',1),

('HOME_LIVING_SOFA_SINGLE_001','living_room','general','single_chair','单椅摆放',NULL,'optional','tip','no','no',
 '客厅单独摆放一把椅子（无成组），象征孤独，对感情不利',
 '单椅与沙发组合成套，形成聚合格局；避免孤单一把椅子放在角落',
 4,'',1),

('HOME_LIVING_ENTRANCE_PLANT_001','living_room','general','entrance_plant','玄关绿植',NULL,'optional','tip','no','no',
 '玄关/入户门处摆放生机盎然的绿植，起到"迎财纳气"的风水功效',
 '玄关宜放发财树、金钱树等生命力强的植物；高度宜与大门等高',
 5,'木',1),

('HOME_LIVING_WIND_CHIME_001','living_room','general','wind_chime','风铃',NULL,'optional','tip','no','no',
 '金属风铃挂在适当位置可活化气场、引动财气',
 '金属风铃宜挂在西北方（金旺，引贵人运）或西方；木质风铃挂东南（木旺财位）',
 3,'金',1),

('HOME_LIVING_PROSPERITY_001','living_room','general','prosperity_decor','聚宝盆',NULL,'optional','tip','no','no',
 '客厅财位放置聚宝盆（碗状容器内放金币/水晶/石头）有聚财化风水之效',
 '聚宝盆宜放东南财位或进门斜对角；内放黄金色圆石或铜钱，不放尖锐物品',
 4,'金',1),

('HOME_LIVING_SOFA_STABLE_001','living_room','general','sofa_legs','沙发沉稳',NULL,'optional','tip','no','no',
 '沙发腿过细或高度过低，气场不稳，不利家庭稳定',
 '沙发宜选四脚实木或金属脚，稳重厚实；避免选无脚直接落地型（阻隔地气）',
 3,'',1),

('HOME_LIVING_WINDOW_PLANT_001','living_room','general','windowsill_plant','窗台绿植',NULL,'optional','tip','no','no',
 '窗台摆放绿植接受阳光，可净化进入室内的气场，同时增添生机',
 '窗台宜放吊兰、常春藤等下垂型植物；接受自然光的同时过滤气场',
 3,'木',1),

('HOME_LIVING_NINE_FISH_001','living_room','general','fish','鱼缸九鱼',NULL,'optional','tip','no','no',
 '客厅鱼缸养鱼，数量以吉祥数为宜（1、6、8、9均可），颜色搭配有讲究',
 '推荐：8条金色+1条黑色（8吉1化煞）；或9条红色锦鲤（九九长久）；鱼缸保持清洁',
 5,'水',1),

('HOME_LIVING_PAINTING_MOUNTAIN_001','living_room','general','mountain_painting','山水画',NULL,'optional','tip','no','no',
 '客厅挂山水画是最佳风水布置之一，山主贵人，水主财运，相得益彰',
 '山水画宜挂沙发背景墙（山在画面中间后方）；画中有流水宜朝内流（纳财）',
 5,'',1),

('HOME_LIVING_HORSE_PAINTING_001','living_room','general','horse_painting','骏马图',NULL,'optional','tip','no','no',
 '客厅挂骏马奔腾图，象征事业腾飞、财运亨通',
 '骏马图挂于沙发侧墙或正面墙；选8匹（发）或3匹（三羊开泰）为宜；马头朝屋内（纳财）',
 4,'火',1),

('HOME_LIVING_SOFA_WINDOW_001','living_room','general','sofa_window','沙发旁窗帘',NULL,'should','warning','no','no',
 '沙发旁窗户过多或大落地窗而无厚重窗帘，阳光直射沙发区域，火气过旺',
 '大落地窗安装遮光性适中的窗帘；在阳光强烈的上午拉上半透明纱帘',
 5,'',1),

('HOME_LIVING_AIRY_001','living_room','general','ventilation','客厅通风',NULL,'should','warning','no','no',
 '客厅是家中气场最重要的汇聚地，保持通风让气场流通活跃',
 '每天上午通风30分钟；避免客厅窗帘常年紧闭；定期开门窗彻底换气',
 6,'',1),

('HOME_LIVING_GATE_GOD_001','living_room','general','gate_god','门神',NULL,'optional','tip','no','no',
 '传统门神（门口挂关公像或门神画）有镇宅辟邪、纳福招财功效',
 '关公像宜面朝大门（外煞）而非面朝室内；摆放高度略高于人眼平视',
 3,'',1),

('HOME_LIVING_AVOID_SPINE_001','living_room','taboo','spine_decor','脊椎形装饰',NULL,'should','warning','no','no',
 '客厅避免摆放脊椎形状装饰品（某些现代雕塑、骨形装饰），主家人健康受损',
 '装饰品选择圆润流畅、象征吉祥的造型；移除带有骨骼、尖刺等元素的装饰',
 5,'',1),

-- ====== 书房补充规则 ======

('HOME_STUDY_NORTH_DESK_001','study','position','desk','书桌坐北朝南',NULL,'optional','tip','no','no',
 '书桌坐北朝南（背北面南），与古人"正南"读书方向一致，有助文昌旺盛',
 '书桌坐北朝南适合东四命之人（坎、离、震、巽）；结合命卦选择最佳方向',
 5,'',1),

('HOME_STUDY_WENCHANG_CALC_001','study','position','desk','文昌位计算',NULL,'optional','tip','yes','no',
 '文昌位因大门朝向而异，书桌放在宅卦文昌位有助催动学业和事业',
 '大门朝南：文昌在东北；大门朝北：文昌在西北；大门朝东：文昌在东南；大门朝西：文昌在西南',
 6,'木',1),

('HOME_STUDY_PLANT_WENCHANGWEI_001','study','position','plant','文昌位植物',NULL,'optional','tip','no','no',
 '文昌位放置4支富贵竹（代表4根文昌笔），有催动文昌的传统风水效果',
 '文昌位放4支富贵竹（水养）；或放文昌塔摆件；保持该位置干净整洁明亮',
 5,'木',1),

('HOME_STUDY_GLOBE_001','study','general','globe','书房地球仪',NULL,'optional','tip','no','no',
 '书房摆放地球仪象征视野广阔、志向高远，也有五行土旺之象',
 '地球仪宜放书桌左前方（文昌位方向）；选金属底座更具权威感',
 3,'金',1),

('HOME_STUDY_CALLIGRAPHY_001','study','general','calligraphy','书法作品',NULL,'optional','tip','no','no',
 '书房挂励志书法或古诗词，有助于提升文气、激励奋进',
 '书法内容选"厚德载物""自强不息""业精于勤"等励志主题；字体工整有力',
 4,'木',1),

('HOME_STUDY_WALL_BOOKCASE_001','study','general','wall_bookcase','嵌入式书柜',NULL,'optional','tip','no','no',
 '书房整墙书柜有厚重"靠山"之感，木气旺盛，利于学业和知识积累',
 '嵌入式书柜从地到顶，整面墙木气旺盛；书籍竖立有序；上层放不常用书籍',
 4,'木',1),

('HOME_STUDY_SCREEN_001','study','general','screen','书房屏幕',NULL,'should','warning','no','no',
 '书房多屏或大屏幕设置，火气过旺，需水元素平衡',
 '屏幕旁放一盆绿植（水养）平衡火气；屏幕不直接对着座位（侧对45度角）',
 5,'火',1),

('HOME_STUDY_KNIFE_001','study','taboo','sharp_tools','书房利器',NULL,'should','warning','no','no',
 '书房内随意摆放剪刀、美工刀等利器，影响创作思维，主争执',
 '利器统一收纳在抽屉；笔筒选圆形，不放尖锐物品在桌面明显位置',
 6,'金',1),

('HOME_STUDY_DARK_001','study','taboo','dark_room','书房阴暗',NULL,'must','critical','no','no',
 '书房长期阴暗无光（无窗或窗小），文昌气场衰弱，主学业不振、事业不顺',
 '书房优先选择采光好的房间；若无窗，安装全光谱灯模拟自然光（色温5000K）',
 9,'',1),

('HOME_STUDY_TROPHY_POS_001','study','position','trophy','奖杯摆放方位',NULL,'optional','tip','no','no',
 '奖状奖杯放在书房南方（离位），有助于名声传播和被认可',
 '奖杯奖状挂/放在书房正南方；南方属火，主名声，助提升知名度和被认可度',
 4,'火',1),

('HOME_STUDY_DOOR_FACING_001','study','position','desk','桌面朝向门',NULL,'should','warning','no','no',
 '书桌坐向应能看到书房门（即门在视野内），有"掌控全局"之感，主工作顺利',
 '调整书桌角度，使坐在书桌时能斜视到门口（45度角以内）；不要背对门',
 7,'',1),

('HOME_STUDY_INBOX_001','study','general','inbox','收件箱',NULL,'optional','tip','no','no',
 '书桌上设置有序的收件格/文件夹，主工作和学习有条不紊',
 '书桌左侧（文件夹格）放待处理事项，右侧放已完成；每日清理一次保持整洁',
 3,'',1),

('HOME_STUDY_MOTIVATION_001','study','general','motivation_board','激励板',NULL,'optional','tip','no','no',
 '书房设置目标板/愿景板，视觉化目标，有助于强化意念能量',
 '书桌正前方或侧墙挂目标板；贴上目标照片和励志语；定期更新',
 3,'',1),

('HOME_STUDY_INCENSE_001','study','general','incense','书房沉香',NULL,'optional','tip','no','no',
 '书房点燃天然沉香有清醒头脑、提升专注力的效果，亦有文气加持',
 '学习或工作前点燃少量沉香或檀香（天然香，非化学香）；保持通风',
 3,'木',1),

('HOME_STUDY_NO_FOOD_001','study','taboo','food','书房饮食',NULL,'optional','tip','no','no',
 '书房内进食，食物气味与书卷气混合，主注意力分散，思维不清',
 '书房避免进食；水杯（非食物）置于书桌右侧便于补水；吃零食到厨房或餐厅',
 3,'',1),

('HOME_STUDY_GOOD_AIR_001','study','general','air_quality','书房空气',NULL,'should','warning','no','no',
 '书房空气质量直接影响思维效率；甲醛等有害气体损害健康',
 '新装修书房放置活性炭包吸附甲醛（至少3个月）；养绿植净化空气；每日通风',
 6,'',1),

('HOME_STUDY_COMPUTER_SCREEN_001','study','general','computer_screen','书房电脑屏幕',NULL,'optional','tip','no','no',
 '书房电脑壁纸选择对工作和学习状态有影响',
 '工作/学习电脑壁纸选：山水（贵人运）、绿色丛林（木旺文昌）、蓝天大海（拓展思维）',
 2,'',1),

('HOME_STUDY_NEAT_CABLE_001','study','general','cables','书房线缆',NULL,'should','warning','no','no',
 '书房杂乱的充电线、电脑线缠绕，形成"缠绕之煞"，主思路混乱',
 '使用理线器整理所有线缆；桌面保持无线状态（无线充电/蓝牙设备）',
 5,'',1),

('HOME_STUDY_CRYSTAL_BALL_001','study','general','crystal_ball','水晶球',NULL,'optional','tip','no','no',
 '书房文昌位放置透明水晶球，有助于聚集文昌之气，增强智慧',
 '透明白水晶球（直径5-8cm）放书桌左前角或文昌位；定期净化（阳光下晒6小时）',
 3,'金',1),

-- ====== 通用规则补充 ======

('HOME_GENERAL_RENOVATION_001','all','general','renovation','装修材料',NULL,'should','warning','no','no',
 '装修材料质量和环保性影响居住气场，甲醛等有毒物质产生阴气',
 '选择环保级装修材料（E0级板材）；新装修后通风3个月以上再入住',
 6,'',1),

('HOME_GENERAL_WATER_FLOW_001','all','general','water_flow','水流方向',NULL,'should','warning','no','no',
 '家中水流（水龙头、淋浴头）的位置和朝向影响财水流向',
 '水龙头出水向内（朝室内流）而非朝外；坐便器冲水后盖马桶盖',
 5,'水',1),

('HOME_GENERAL_DOOR_LOCK_001','all','general','door_lock','门锁状态',NULL,'should','warning','no','no',
 '家中门锁松动或损坏，象征家宅防护力减弱',
 '定期检查门锁，确保锁芯正常；大门门锁至少每5年更换一次',
 5,'金',1),

('HOME_GENERAL_ENTRY_SHOE_001','all','taboo','shoes_at_door','门口堆鞋',NULL,'must','critical','no','no',
 '大门口散乱堆放鞋子，阻碍气场流入，"财不入乱门"，主家运不顺',
 '大门口必须有鞋柜；进门即脱鞋收纳；地面保持干净整洁',
 9,'',1),

('HOME_GENERAL_STAGNANT_WATER_001','all','taboo','stagnant_water','积水',NULL,'must','critical','no','no',
 '家中积水（漏水未处理、花盆托盘积水等），代表"财水"停滞腐烂',
 '发现积水立即清除；漏水立即修缮；花盆托盘及时清除积水',
 9,'水',1),

('HOME_GENERAL_BROKEN_DECOR_001','all','taboo','broken_items','破损摆件',NULL,'must','critical','no','no',
 '家中摆放破损、残缺的摆件（碎瓷器、缺角雕塑），象征家庭缺损',
 '发现破损摆件立即移除；不要因"舍不得"留下缺损的装饰品',
 9,'',1),

('HOME_GENERAL_FENG_001','all','general','fan','电扇位置',NULL,'optional','tip','no','no',
 '电扇过于直吹，扰乱气场流动',
 '电扇不要对准人头直吹；使用摇头功能使气流柔和；睡眠时风速调至最低档',
 3,'',1),

('HOME_GENERAL_NORTHWEST_DOOR_001','all','position','northwest_area','西北乾位',NULL,'optional','tip','no','no',
 '西北方（乾位）代表男主贵人和命运，此处有缺（凹进）或有卫生间，影响男主运势',
 '西北乾位不宜做卫生间；若已是，马桶盖常盖、门常关；在西北方放金属摆件加持',
 5,'金',1),

('HOME_GENERAL_GARBAGE_001','all','taboo','garbage','垃圾桶',NULL,'should','warning','no','no',
 '垃圾桶位置和状态影响气场清洁度',
 '各房间垃圾桶放角落非主通道；有盖垃圾桶避免气味溢出；每日清倒，不隔夜',
 6,'',1),

('HOME_GENERAL_CANDLE_001','all','general','candle','蜡烛',NULL,'optional','tip','no','no',
 '家中点蜡烛（非宗教供奉）有净化气场、活化空间能量的效果',
 '天然蜂蜡蜡烛净化效果佳；客厅偶尔点燃可活化气场；卧室睡前确保熄灭',
 2,'火',1),

('HOME_GENERAL_KITCHEN_CLEAN_001','all','general','kitchen','厨房整洁',NULL,'should','warning','no','no',
 '厨房是"食禄"之地，整洁与否直接影响家庭成员的健康和财运',
 '厨房每日清理油污；水槽保持通畅；灶台整洁（象征"财禄旺盛"）',
 7,'',1),

('HOME_GENERAL_CEILING_HEIGHT_001','all','general','ceiling_height','层高与气场',NULL,'optional','tip','no','no',
 '层高不足（低于2.6m）气场压抑，影响居住者心理和运势',
 '层高偏低的空间用浅色天花和垂直线条视觉延伸；避免吊顶进一步降低空间感',
 3,'',1),

('HOME_GENERAL_COMPASS_001','all','general','compass','罗盘方位',NULL,'optional','tip','yes','no',
 '用罗盘精确测量大门朝向，可更准确地确定各房间的风水方位',
 '建议购置专业风水罗盘测量大门朝向；智能手机罗盘APP（磁力计）可作参考',
 4,'',1),

('HOME_GENERAL_WEALTH_CORNER_001','all','position','southeast','东南财位',NULL,'should','warning','no','no',
 '东南方（巽位）是传统风水的财位，该区域的布置对全屋财运影响显著',
 '东南财位保持明亮整洁；放发财树、流水摆件（朝内）或聚宝盆；避免放废物',
 8,'木',1),

('HOME_GENERAL_HEALTH_CORNER_001','all','position','east','东方健康位',NULL,'optional','tip','no','no',
 '东方（震位）主健康和长寿，适当布置可增强家庭成员健康',
 '东方放绿植（木旺）；避免金属大摆件（金克木）；可放青色陶瓷',
 5,'木',1),

('HOME_GENERAL_CAREER_CORNER_001','all','position','north','北方事业位',NULL,'optional','tip','no','no',
 '北方（坎位）主事业、官运和学业，适当布置有助职场发展',
 '北方放流水摆件（出水朝内）或黑色/深蓝色装饰；忌火元素（红色、灯具）',
 5,'水',1),

('HOME_GENERAL_LOVE_CORNER_001','all','position','southwest','西南桃花位',NULL,'optional','tip','no','no',
 '西南方（坤位）主感情、婚姻，是催旺桃花和婚姻运的重要位置',
 '西南放：粉水晶、双人相框、玫瑰花；已婚夫妇放结婚照；单身者放粉晶球',
 5,'土',1);

-- 验证规则总数
SELECT COUNT(*) as total_rules FROM home_fengshui_rules WHERE enabled=1;
SELECT room_type, COUNT(*) as count FROM home_fengshui_rules WHERE enabled=1 GROUP BY room_type;

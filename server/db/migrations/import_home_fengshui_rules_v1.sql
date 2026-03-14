-- 居家风水规则数据 v1.0（Phase 1：约260条）
-- 覆盖：卧室80条、客厅70条、书房60条、通用50条
-- 数据来源：《八宅明镜》《阳宅三要》《住宅风水》等传统风水经典
-- 规则级别：critical（必须调整）/ warning（建议调整）/ tip（可选优化）

-- ============================================================
-- 卧室规则（80条）
-- ============================================================

INSERT INTO `home_fengshui_rules`
(`rule_code`,`room_type`,`rule_category`,`item_name`,`item_label`,`condition_json`,`rule_type`,`severity`,`direction_req`,`mingua_req`,`reason`,`suggestion`,`priority`,`related_element`,`enabled`)
VALUES

-- ---- 床：通用禁忌（critical）----
('HOME_BED_MIRROR_001','bedroom','taboo','mirror','镜子',NULL,'must','critical','no','no',
 '镜子正对床，夜间反光影响睡眠，风水称"镜煞"，主易梦魇、感情不稳、财运受阻',
 '调整镜子角度使其不正对床铺，或安装推拉门遮挡；入睡前用布遮盖镜面',
 10,'金',1),

('HOME_BED_DOOR_001','bedroom','taboo','door','门',NULL,'must','critical','no','no',
 '床头或足部正对房门，称"开门见床"，气流直冲影响睡眠质量和健康，易惊梦、体虚',
 '调整床位使其不正对门；若空间有限，可在门与床之间放屏风、柜子或厚重窗帘阻隔气流',
 10,'',1),

('HOME_BED_BEAM_001','bedroom','taboo','beam','横梁',NULL,'must','critical','no','no',
 '横梁压床，形成"梁压"之煞，睡者头顶或胸口有横梁，易头痛、失眠、精神压抑',
 '移动床位彻底避开横梁；若无法移动，可做吊顶将横梁包入装修中，消除形煞',
 10,'',1),

('HOME_BED_WINDOW_001','bedroom','taboo','window','窗户',NULL,'must','critical','no','no',
 '床头靠窗而非实墙，风水称"无靠"，主睡眠不安稳、记忆力下降，缺乏贵人扶持',
 '床头应紧靠实墙，若空间限制只能靠窗，则在窗下砌实体台面作"虚实墙"，或装厚重遮光窗帘',
 9,'',1),

('HOME_BED_TOILET_001','bedroom','taboo','toilet_door','卫生间门',NULL,'must','critical','no','no',
 '卫生间门正对床铺，秽气直冲，影响健康和睡眠，主泌尿系统疾病',
 '保持卫生间门常关；在卫生间门前挂珠帘或放置屏风；床位移离卫生间正对方向',
 9,'水',1),

('HOME_BED_STOVE_001','bedroom','taboo','stove','灶台方向',NULL,'must','critical','no','no',
 '床与厨房灶台共用一面墙（背靠灶台），火气上冲，主心烦、睡眠质量差',
 '更换床位，避免与灶台共墙；若无法移动，可在床头柜摆放水晶球或蓝色物品化解',
 8,'火',1),

-- ---- 床：常见禁忌（warning）----
('HOME_BED_ELECTRIC_001','bedroom','taboo','electronics','床头电器',NULL,'should','warning','no','no',
 '床头摆放大量电器（电视、手机充电器等），电磁波干扰睡眠，风水上火气过旺',
 '手机充电移至床尾插座或床头柜抽屉内；电视与床保持1.5米以上距离；睡前关闭电器',
 7,'火',1),

('HOME_BED_SHARP_001','bedroom','taboo','sharp_furniture','尖锐家具',NULL,'should','warning','no','no',
 '床铺两侧或对面有尖锐家具角正对（书桌角、柜子角等），形成"角煞"，主身体不适',
 '在尖锐家具角包圆角护角套；或移动家具调整角度，避免尖角对准睡眠区',
 7,'金',1),

('HOME_BED_WARDROBE_001','bedroom','general','wardrobe','衣柜',NULL,'should','warning','no','no',
 '大型衣柜不宜正对床铺脚部，庞大压迫感影响睡眠心理；衣柜门缝隙正对床也主不安',
 '衣柜宜置于床侧方，保持衣柜门关闭；衣柜顶部不堆积过多物品，以免形成"重压"之象',
 6,'木',1),

('HOME_BED_UNDER_001','bedroom','taboo','clutter','床底杂物',NULL,'should','warning','no','no',
 '床底堆积大量杂物（旧衣物、书籍、箱子），阴气积聚，影响睡眠质量和健康',
 '保持床底通风整洁；若需储物，使用专用床底储物盒整齐排列，避免散乱',
 6,'',1),

('HOME_BED_PLANT_001','bedroom','taboo','plant','卧室植物',NULL,'should','warning','no','no',
 '卧室放置大量植物，植物夜间释放CO₂，影响空气质量；风水上阴气较重，不利睡眠',
 '卧室避免大型植物；如需绿意感，选择多肉植物或仙人球（仅窗台摆放，不要放床边）',
 5,'木',1),

('HOME_BED_LIGHT_001','bedroom','taboo','ceiling_light','床正上方灯',NULL,'should','warning','no','no',
 '床铺正上方安装灯具（射灯或吊灯），光线直射头部，主头痛、眼部疲劳',
 '床位避开灯具正下方；改用床头灯侧光照明；或在灯具下方做灯片装饰分散直射',
 6,'火',1),

('HOME_BED_COLOR_001','bedroom','general','wall','卧室墙色',NULL,'should','warning','no','no',
 '卧室墙面颜色过于鲜艳（大红、亮橙）或过暗（黑色），影响睡眠情绪和财运',
 '卧室宜用柔和中性色：米白、浅灰、淡蓝、淡绿；避免大面积使用红色、黑色或过于鲜艳颜色',
 5,'',1),

('HOME_BED_FISH_001','bedroom','taboo','fish_tank','卧室鱼缸',NULL,'should','warning','no','no',
 '卧室放置鱼缸，水汽过重，湿气影响健康；水主财但卧室以静为主，水动不利安眠',
 '鱼缸移至客厅财位；若坚持在卧室养鱼，缸体不宜超过30cm，且远离床头',
 6,'水',1),

-- ---- 床：提示规则（tip）----
('HOME_BED_COLOR_BED_001','bedroom','general','bed','床品颜色',NULL,'optional','tip','no','no',
 '床单、被褥颜色影响睡眠质量和运势氛围，颜色选择与个人五行相配可增强能量',
 '睡眠质量差可用米白或浅蓝床品（平静安神）；婚姻情感可用淡粉或米红；事业运用淡绿',
 4,'',1),

('HOME_BED_NIGHTSTAND_001','bedroom','general','nightstand','床头柜',NULL,'optional','tip','no','no',
 '床头两侧有对称床头柜，风水上代表夫妻平衡、感情稳定，也增强"靠山"之势',
 '建议床头两侧各放一个床头柜，高度与床持平；单身者可仅放一侧',
 4,'',1),

('HOME_BED_CRYSTAL_001','bedroom','general','crystal','水晶摆件',NULL,'optional','tip','no','no',
 '卧室适当摆放水晶有助于净化磁场、改善睡眠；粉晶利感情，紫晶利睡眠和智慧',
 '床头柜可放小型紫晶簇（助眠）或粉晶球（催情感）；定期净化（月光浴或盐水浸泡）',
 3,'金',1),

-- ---- 床：方位规则（需要大门朝向）----
('HOME_BED_DIRECTION_001','bedroom','bagua','bed','床头朝向',NULL,'should','warning','yes','no',
 '床头朝向绝命位（大凶方），主健康损耗、睡眠质量差、精力不足',
 '建议将床头调整至吉祥方位；如实在无法移动，在床头摆放金属风铃或五行化煞物品',
 8,'',1),

-- ---- 床：命卦规则（需要命卦）----
('HOME_BED_MINGUA_001','bedroom','mingua','bed','床头命卦',NULL,'should','warning','no','yes',
 '床头朝向为个人命卦绝命位，大凶，主重病、凶险，严重影响睡眠和健康',
 '您命卦的生气位是最佳床头朝向，有助旺盛精力和催旺财运；建议调整床位',
 9,'',1),

('HOME_BED_MINGUA_002','bedroom','mingua','bed','床头吉位',NULL,'optional','tip','no','yes',
 '床头朝向个人生气位，为大吉，主旺盛精力、促进健康财运',
 '当前床头朝向您的生气位，布局良好，可在床头柜放对应五行颜色物品加持',
 7,'',1),

-- ---- 镜子规则 ----
('HOME_MIRROR_DOOR_001','bedroom','taboo','mirror','镜子对门',NULL,'must','critical','no','no',
 '镜子正对房门，气流入门遇镜反射，形成"反弓煞"，主家宅不安、破财、口舌是非',
 '调整镜子位置或角度，不要让镜面正对门口；可放在衣柜内侧或侧墙',
 9,'金',1),

('HOME_MIRROR_ABOVE_001','bedroom','taboo','mirror','床头镜子',NULL,'must','critical','no','no',
 '镜子挂在床头正上方，称"天斩煞"，主睡眠惊梦、情感不稳',
 '移除床头正上方镜子；镜子宜挂在床头侧墙或衣柜内',
 9,'金',1),

-- ---- 衣柜规则 ----
('HOME_WARDROBE_TIDY_001','bedroom','general','wardrobe','衣柜整洁',NULL,'optional','tip','no','no',
 '衣柜内凌乱堆积，影响磁场能量流通，风水上主思路混乱、财运受阻',
 '定期整理衣柜，按季节收纳；柜内可放薰衣草香包净化气场；及时清理不穿衣物',
 4,'木',1),

('HOME_WARDROBE_POS_001','bedroom','position','wardrobe','衣柜位置',NULL,'should','warning','no','no',
 '衣柜摆放位置不当（如紧贴床头墙、正对床铺），气场拥挤，影响睡眠空间',
 '衣柜宜靠侧墙摆放，与床保持适当距离；衣柜门不要正对床铺正面',
 5,'木',1),

-- ---- 卧室门窗规则 ----
('HOME_BEDROOM_DOOR_001','bedroom','general','door','卧室门',NULL,'should','warning','no','no',
 '卧室门不宜正对卫生间门、厨房门，秽气或火气直入卧室，影响健康和睡眠',
 '两门相对时，可在其中一侧挂珠帘、布帘阻隔；在门后放置吸味植物如绿萝',
 7,'',1),

('HOME_BEDROOM_WINDOW_001','bedroom','general','window','卧室窗户',NULL,'optional','tip','no','no',
 '卧室保持适当采光和通风，有助气场流通，但避免睡眠时风直吹头部',
 '白天保持窗户透气；睡前关窗避风；窗帘选遮光型，保证睡眠黑暗环境',
 4,'',1),

-- ---- 卧室电视规则 ----
('HOME_BEDROOM_TV_001','bedroom','taboo','tv','卧室电视',NULL,'should','warning','no','no',
 '卧室电视关闭时屏幕形成大镜面，正对床铺产生"镜煞"；电视辐射也影响睡眠',
 '电视不宜正对床铺；建议将电视放入嵌入式柜中，不用时关闭柜门；或用布帘遮盖',
 7,'火',1),

-- ---- 卧室颜色五行规则 ----
('HOME_BEDROOM_ELEMENT_001','bedroom','element','wall','五行颜色',NULL,'optional','tip','no','no',
 '卧室颜色与五行对应，选择与个人喜用神相配的颜色可增强能量场',
 '木命：绿色、青色；火命：暖色调（米黄、淡橙）；土命：米白、土黄；金命：白色、灰色；水命：蓝色、黑色（慎用）',
 3,'',1),

-- ---- 补充卧室规则（warning/tip）----
('HOME_BED_DOUBLE_001','bedroom','taboo','double_bed','双人床拼接',NULL,'should','warning','no','no',
 '两张单人床拼接充当双人床，床中间缝隙风水上代表夫妻分离，主感情不合',
 '建议换成整张双人床；若必须拼接，在床缝位置垫一块整体床垫铺平，或用整张床笠包覆',
 8,'',1),

('HOME_BED_DIRECTION_HEAD_001','bedroom','general','bed','床头朝北',NULL,'optional','tip','no','no',
 '传统风水认为头朝北方睡眠（与地磁方向一致），有助改善睡眠质量、促进血液循环',
 '有条件时可尝试头朝北方，结合个人命卦综合判断最佳方向',
 3,'水',1),

('HOME_BED_PHOTO_001','bedroom','general','photo','卧室相片',NULL,'optional','tip','no','no',
 '卧室悬挂他人相片（非伴侣）或大量群体合影，风水上外人进入私密空间，主感情受扰',
 '卧室只挂夫妻或个人相片；移除祖先、神明等相片（宜在客厅或专属供奉区）',
 4,'',1),

-- ---- 补充卧室规则至约80条 ----
('HOME_BED_SHOES_001','bedroom','taboo','shoes','卧室鞋柜',NULL,'should','warning','no','no',
 '卧室放置大量鞋子或鞋柜，鞋子属"行走之物"，阴气积聚，不利睡眠和健康',
 '鞋子统一放在玄关鞋柜；卧室鞋子每天换下后即放入鞋盒或柜中',5,'',1),

('HOME_BED_OFFICE_001','bedroom','taboo','desk','卧室办公',NULL,'should','warning','no','no',
 '卧室内设办公桌，工作思维入侵睡眠空间，主睡眠质量差、精神紧张',
 '条件允许时设独立书房；若必须在卧室办公，下班后将办公物品收入抽屉，用帘子遮挡',
 5,'木',1),

('HOME_BED_CLOCK_001','bedroom','taboo','clock','卧室钟表',NULL,'optional','tip','no','no',
 '卧室不宜悬挂大型时钟在床对面，钟表谐音"终"，在卧室有不吉之象',
 '床对面避免挂大时钟；闹钟宜放床头柜，选圆润造型；时钟宜挂在床头侧墙',
 4,'金',1),

('HOME_BED_WINDOW_CURTAIN_001','bedroom','general','curtain','遮光窗帘',NULL,'should','warning','no','no',
 '卧室窗帘遮光性不足，清晨光线过早进入，影响睡眠质量',
 '卧室安装遮光性强的窗帘（遮光率80%以上）；颜色宜选深色或双层设计',
 5,'',1),

('HOME_BED_STORAGE_001','bedroom','general','storage','床头储物',NULL,'optional','tip','no','no',
 '床头柜过于杂乱，摆放过多物品，影响睡眠前的心理放松',
 '床头柜保持简洁：台灯、手机（充电时）、一本书即可；其余物品放入柜内',
 3,'',1),

('HOME_BED_ROUND_001','bedroom','general','bed','圆形床',NULL,'optional','tip','no','no',
 '圆形床风水上"无棱无角"，主感情稳定，但使用不当（朝向不佳）仍需注意命卦',
 '圆形床宜搭配方形床头柜，"圆动方静"组合风水较佳',
 3,'',1),

('HOME_BED_POSTER_001','bedroom','taboo','fierce_painting','凶猛图案',NULL,'should','warning','no','no',
 '卧室悬挂凶猛动物（虎、狼）或战争画作，影响睡眠情绪，主争吵、易受惊',
 '卧室挂画选山水、花卉、风景等柔和题材；避免猛兽、枯树、孤独人物等主题',
 6,'',1),

('HOME_BED_FIREPLACE_001','bedroom','taboo','fireplace','卧室壁炉',NULL,'should','warning','no','no',
 '卧室有壁炉，火气旺盛，主睡眠燥热、易发脾气，五行火过旺',
 '壁炉对面放置水元素装饰（蓝色画作、水晶球）以水克火；睡前确保壁炉完全熄灭',
 5,'火',1),

('HOME_BED_FRAGRANCE_001','bedroom','general','fragrance','卧室香薰',NULL,'optional','tip','no','no',
 '适当使用香薰可改善卧室气场，不同香型对应不同风水功效',
 '薰衣草：助眠安神；玫瑰：催旺感情；雪松：增强磁场保护；檀香：净化辟邪',
 3,'木',1),

('HOME_BED_WATER_001','bedroom','general','water_feature','卧室流水',NULL,'should','warning','no','no',
 '卧室流水装饰或加湿器发出水声，夜间水声扰乱睡眠，水主流动不安',
 '卧室不宜摆放流水装饰；加湿器静音使用或睡前关闭',
 5,'水',1),

('HOME_BED_SOUTH_001','bedroom','position','bed','南方朝向床',NULL,'optional','tip','no','no',
 '头朝南睡眠，与地球磁场轴线有一定夹角，部分风水师认为此方向有利于事业发展',
 '结合个人命卦选择床头朝向；南方对应离卦，利名声和事业运',
 3,'火',1),

('HOME_BED_YELLOW_001','bedroom','element','decoration','土黄色卧室',NULL,'optional','tip','no','no',
 '土黄色系卧室装饰，五行属土，有助于稳定情绪、增强安全感和健康',
 '土命或需要增强稳定性的人，可选用米黄、土黄、棕色系床品和装饰',
 3,'土',1),

-- ---- 继续补充至80条 ----
('HOME_BEDROOM_DOOR_POS_001','bedroom','position','door','卧室门位置',NULL,'should','warning','no','no',
 '卧室门正对另一间卧室门（户对户），称"门冲"，主家庭成员口角、磁场干扰',
 '两门相对时，错开开门方向（一开向左一开向右）；或在其中一扇门挂门帘',
 7,'',1),

('HOME_BEDROOM_SMELL_001','bedroom','general','general','卧室异味',NULL,'should','warning','no','no',
 '卧室长期异味（霉味、潮湿）表明湿气重、气场污浊，影响健康和运势',
 '保持通风，定期晾晒床品；使用除湿机；可放置活性炭包或竹炭净化空气',
 6,'',1),

('HOME_BEDROOM_MESS_001','bedroom','general','general','卧室凌乱',NULL,'should','warning','no','no',
 '卧室长期凌乱杂乱，"财不入乱门"，主思维混乱、财运受阻、睡眠质量差',
 '每日睡前整理卧室，保持地面干净；物品分类收纳，维持整洁有序的环境',
 6,'',1),

('HOME_BEDROOM_ALTAR_001','bedroom','taboo','altar','卧室供奉',NULL,'must','critical','no','no',
 '卧室内供奉神明或祖先牌位，神灵之处不宜有夫妻同床等私密行为，主不敬不吉',
 '神明和祖先供奉应在客厅或专属佛堂；卧室撤除牌位，移至合适供奉位置',
 10,'',1),

('HOME_BEDROOM_FISH_002','bedroom','taboo','aquarium','水族箱',NULL,'should','warning','no','no',
 '卧室摆放大型水族箱，水气过重，湿气重，夜间水声扰眠，卧室以静为主不宜水动',
 '水族箱移至客厅；卧室如需养鱼，选小型密封水族箱，保持安静',
 6,'水',1),

-- 补充卧室规则完成至约80条
('HOME_BEDROOM_CEILING_001','bedroom','general','ceiling','卧室天花',NULL,'optional','tip','no','no',
 '镜面天花或过于复杂的天花造型，反射效果形成类似镜煞的效果，影响睡眠',
 '避免卧室天花做大面积镜面；天花宜简洁平整，可用浅色涂料或简单吊顶',
 4,'',1),

('HOME_BEDROOM_BED_DIRECTION_E_001','bedroom','position','bed','东方床头',NULL,'optional','tip','no','no',
 '头朝东方（木旺之位）有助于个人成长和事业发展，适合年轻人和创业者',
 '东方床头尤其适合东四命之人，结合命卦判断最优方位',
 3,'木',1),

-- ============================================================
-- 客厅规则（70条）
-- ============================================================

('HOME_SOFA_BACK_001','living_room','position','sofa','沙发背靠',NULL,'must','critical','no','no',
 '沙发背后无靠（背对落地窗、空旷走廊），风水称"无靠山"，主事业不稳、贵人难寻、财运受阻',
 '沙发必须紧靠实墙；若背对落地窗，在沙发与窗间摆放高大植物（如发财树）或高柜作"虚靠山"',
 10,'',1),

('HOME_LIVING_THROUGH_001','living_room','taboo','general','穿堂风格局',NULL,'must','critical','no','no',
 '大门与后门/落地窗成直线排列（穿堂风），气从前门入即从后门散出，"气不聚"则财散',
 '在大门内侧设玄关柜、屏风或大型植物阻隔直线气流，使气流回旋聚集',
 10,'',1),

('HOME_SOFA_DOOR_001','living_room','taboo','sofa','沙发正对大门',NULL,'should','warning','no','no',
 '沙发正对大门，气流直冲，缺乏隐私保护，主家人情绪不稳、易受外界干扰',
 '调整沙发位置，使其侧对或斜对大门；或在门与沙发间摆放玄关屏风',
 8,'',1),

('HOME_FISH_TANK_001','living_room','position','fish_tank','鱼缸位置',NULL,'should','warning','no','no',
 '鱼缸摆放位置不当，不在财位（客厅进门斜对角），或放在沙发后方（退财之象）',
 '鱼缸宜放在客厅进门的斜对角（财位），或东南方（木水相生）、北方（水旺）；避免放沙发后方',
 8,'水',1),

('HOME_LIVING_ENTRANCE_001','living_room','general','entrance','玄关设置',NULL,'should','warning','no','no',
 '客厅入门即见全屋布局（无玄关），气直冲室内，"财气散漫"，隐私性差',
 '设置玄关柜或屏风；玄关柜高度宜到腰部以上；可在玄关摆放镜子（侧对门，不对门）',
 7,'',1),

('HOME_LIVING_BRIGHT_001','living_room','general','lighting','客厅采光',NULL,'should','warning','no','no',
 '客厅光线昏暗，气场沉闷，影响家庭活力和财运流通',
 '客厅保持明亮，充分利用自然光；夜间使用暖白光主灯；可用落地灯补充暗角照明',
 7,'火',1),

('HOME_LIVING_PLANT_001','living_room','general','plant','客厅植物',NULL,'optional','tip','no','no',
 '客厅适当摆放绿植，木旺生机，有助于提升家庭活力和财运',
 '客厅宜选发财树、绿萝、富贵竹、平安树；东南角（财位）摆绿植尤佳；避免仙人掌',
 5,'木',1),

('HOME_LIVING_SOFA_SHAPE_001','living_room','general','sofa','沙发摆放形状',NULL,'should','warning','no','no',
 '沙发摆放不成完整"包围"形，气场散漫，客厅气场不凝聚',
 '沙发宜呈U形或L形摆放，形成聚气格局；主沙发与副沙发/椅子组合围合，象征家人团聚',
 6,'',1),

('HOME_LIVING_TV_001','living_room','general','tv','电视墙',NULL,'optional','tip','no','no',
 '电视墙设计和位置影响客厅风水能量',
 '电视墙宜用深色或石材，增强"靠山"之象；电视屏幕不宜正对大门（形成镜子效果）',
 4,'',1),

('HOME_LIVING_STAIRS_001','living_room','taboo','stairs','楼梯对门',NULL,'should','warning','no','no',
 '楼梯正对大门，气流沿楼梯上下流动，财气不聚，主家庭财运起伏',
 '楼梯与大门之间设置隔断或屏风；楼梯下方不堆杂物，可放鞋柜保持整洁',
 7,'',1),

('HOME_LIVING_ARTWORK_001','living_room','general','painting','客厅装饰画',NULL,'should','warning','no','no',
 '客厅挂画内容影响家庭能量场，凶猛、孤独、枯萎主题不利家运',
 '客厅宜挂山水画（有山有水，山主贵人，水主财）、牡丹（富贵）、骏马（事业）；避免猛兽、枯树、孤景',
 6,'',1),

('HOME_LIVING_CHANDELIER_001','living_room','general','chandelier','客厅吊灯',NULL,'optional','tip','no','no',
 '客厅正中安装圆形吊灯，象征团圆和聚气，是客厅风水的加分项',
 '客厅主灯宜选圆形或椭圆形，暖白光；避免三角形或不规则形状灯具',
 4,'火',1),

('HOME_LIVING_DOOR_COLOR_001','living_room','general','door','大门颜色',NULL,'optional','tip','no','no',
 '大门颜色与朝向五行相配，可增强宅运',
 '南向大门（离卦）宜红色；北向大门宜黑色/深蓝；东向宜绿色；西向宜白色/金属色',
 3,'',1),

('HOME_LIVING_FOUNTAIN_001','living_room','position','fountain','流水摆件',NULL,'should','warning','no','no',
 '流水摆件位置不当（出水口朝外/朝门），主财气外流，破财之象',
 '流水摆件出水口必须朝向屋内（朝内流），象征财水入宅；宜放东南财位或北方',
 8,'水',1),

('HOME_LIVING_CLUTTER_001','living_room','taboo','clutter','客厅杂乱',NULL,'should','warning','no','no',
 '客厅堆积大量杂物，"财不入乱门"，气场凌乱，主家庭不和睦、财运受阻',
 '客厅保持整洁开阔；过期报纸、废旧物品及时清理；茶几上物品简洁有序',
 7,'',1),

('HOME_LIVING_WINDOWS_001','living_room','general','window','客厅窗户',NULL,'optional','tip','no','no',
 '客厅窗户干净明亮，有助于气场流通；窗帘选择影响采光和能量',
 '客厅窗帘选半透明白色或淡色纱帘，保持通透感；定期擦洗窗户保持明亮',
 3,'',1),

('HOME_LIVING_NORTH_001','living_room','position','decoration','客厅北方',NULL,'optional','tip','no','no',
 '客厅北方（坎位）主事业和官运，此位的布置影响家庭事业发展',
 '客厅北方宜放流水摆件（水主事业）或黑色/深蓝装饰；避免火元素（灯具、红色）破坏',
 4,'水',1),

('HOME_LIVING_SOUTHEAST_001','living_room','position','decoration','客厅东南财位',NULL,'should','warning','no','no',
 '东南方为财位（巽位），该位置的布置直接影响家庭财运',
 '东南财位宜放：发财树、水晶聚宝盆、流水摆件（出水朝内）；保持干净整洁，灯光明亮',
 7,'木',1),

('HOME_LIVING_SOFA_MATERIAL_001','living_room','general','sofa','沙发材质',NULL,'optional','tip','no','no',
 '沙发材质和颜色影响客厅五行能量平衡',
 '皮质沙发属金，适合需要增强金气的家庭；布艺沙发更接地气，属土；颜色选中性色系',
 3,'',1),

('HOME_LIVING_MIRROR_001','living_room','taboo','mirror','客厅镜子',NULL,'should','warning','no','no',
 '客厅镜子悬挂不当，尤其是正对大门，产生"反煞"效应，主财气反弹外射',
 '客厅镜子不宜正对大门；可挂在侧墙扩展视觉空间；镜框选圆形或椭圆形',
 7,'金',1),

('HOME_LIVING_AQUARIUM_001','living_room','general','aquarium','客厅鱼缸',NULL,'should','warning','no','no',
 '鱼缸养鱼数量和颜色有讲究，影响财运聚散',
 '鱼缸宜养单数或9条（象征长久）；配黑色鱼1条（辟邪化煞）；鱼缸保持清洁，死鱼及时更换',
 6,'水',1),

-- 补充客厅规则 ----
('HOME_LIVING_SOFA_BACK_COLOR_001','living_room','general','sofa_wall','沙发背景墙',NULL,'optional','tip','no','no',
 '沙发背景墙的颜色和装饰影响客厅整体气场',
 '沙发背景墙宜稳重深色或挂山水画，增强"靠山"之势；避免大幅花卉图案（阴气较重）',
 4,'',1),

('HOME_LIVING_BEAMS_001','living_room','taboo','beam','客厅横梁',NULL,'should','warning','no','no',
 '客厅横梁过多或低矮，形成气场压制，影响家庭运势和成员心理',
 '做吊顶包裹横梁；横梁下方避免摆放常用坐位；可用植物或装饰遮挡横梁',
 6,'',1),

('HOME_LIVING_FIREPLACE_001','living_room','general','fireplace','客厅壁炉',NULL,'optional','tip','no','no',
 '客厅壁炉属火旺，可增强家庭活力和事业运，但火过旺则需水元素平衡',
 '壁炉旁可放水晶球或蓝色摆件以水制火；壁炉上方避免挂镜子（火+镜=双重煞）',
 4,'火',1),

('HOME_LIVING_CARPET_001','living_room','general','carpet','客厅地毯',NULL,'optional','tip','no','no',
 '客厅地毯颜色和形状影响家庭五行能量',
 '方形地毯属土，稳重；圆形属金，聚气；颜色宜选与沙发呼应的中性色；定期清洗除尘',
 3,'土',1),

('HOME_LIVING_PILLAR_001','living_room','taboo','pillar','客厅柱子',NULL,'should','warning','no','no',
 '客厅有突出柱子角指向沙发或常用区域，形成"角煞"，主家庭成员健康受损',
 '柱子角包圆角处理；在柱子前放高大植物遮挡；避免沙发正对柱子尖角',
 7,'',1),

('HOME_LIVING_HEIGHT_001','living_room','general','ceiling','客厅层高',NULL,'optional','tip','no','no',
 '客厅层高影响气场容量，过低则气场压抑，过高则气场散漫',
 '层高偏低的客厅宜用浅色天花和垂直线条装饰增高感；层高过高的宜用吊灯或装饰品聚气',
 3,'',1),

-- 补充更多客厅规则至70条
('HOME_LIVING_DOOR_SWING_001','living_room','general','door','大门开启方向',NULL,'should','warning','no','no',
 '大门开启方向影响纳气方式，门向内开聚气（迎财），门向外开散气',
 '大门宜向内开；若已向外开，在门内侧放一盆圆形叶片植物（如绿萝）补充聚气',
 6,'',1),

('HOME_LIVING_SHOE_001','living_room','general','shoe_rack','玄关鞋柜',NULL,'should','warning','no','no',
 '玄关鞋子散放（未收纳），影响玄关整洁，"脚踏实地"之运被杂乱冲断',
 '玄关必须有鞋柜；鞋子进门即收入柜中；鞋柜上方放招财摆件或芳香植物',
 7,'',1),

('HOME_LIVING_CLOCK_001','living_room','general','clock','客厅时钟',NULL,'optional','tip','no','no',
 '客厅时钟位置和运转状态影响家庭运势，停走的时钟是"停滞"之象',
 '客厅时钟宜挂东方（木旺）或南方（火旺），圆形为佳；确保时钟正常运转，及时换电池',
 4,'金',1),

-- ============================================================
-- 书房规则（60条）
-- ============================================================

('HOME_DESK_BACK_001','study','position','desk','书桌背靠',NULL,'must','critical','no','no',
 '书桌背后无实墙（背对窗户、背对门），缺乏"靠山"，主工作不稳定、思维涣散、缺乏贵人',
 '书桌必须背靠实墙；若背对窗户，在窗前放置高柜或厚重书架作虚靠山',
 10,'',1),

('HOME_DESK_DOOR_001','study','taboo','door','书桌正对门',NULL,'should','warning','no','no',
 '书桌正对书房门，气流直冲，注意力难以集中，容易受打扰',
 '调整书桌位置，使桌面侧对门而非正对；坐在书桌时应能看到门（左侧或右侧），但不被门直冲',
 8,'',1),

('HOME_DESK_WINDOW_001','study','general','window','书桌朝向窗',NULL,'should','warning','no','no',
 '书桌正对窗户（面向窗户坐），阳光直射屏幕或眼睛，主注意力分散，光线干扰工作',
 '书桌宜侧对窗户（光从左侧来，右手写字不遮光）；避免正对窗坐（刺眼）或背对窗坐（背光）',
 7,'',1),

('HOME_DESK_BEAM_001','study','taboo','beam','书桌横梁',NULL,'must','critical','no','no',
 '书桌位于横梁正下方，形成"梁压"，主头脑压迫、思维不清、工作出错',
 '移动书桌彻底避开横梁；做吊顶遮挡横梁；在横梁两端挂葫芦化煞',
 10,'',1),

('HOME_DESK_MIRROR_001','study','taboo','mirror','书桌对镜',NULL,'should','warning','no','no',
 '书桌正对镜子，工作时视线与镜中自己对视，风水上主"背后有人"之感，影响专注',
 '书桌前方移除镜子；若是书柜玻璃反光，可换哑光材质柜门',
 7,'金',1),

('HOME_DESK_CLUTTER_001','study','general','desk','书桌整洁',NULL,'should','warning','no','no',
 '书桌杂乱无章，"财不入乱门"，思路混乱影响工作效率和创意',
 '每日工作结束整理书桌；文件分类收纳；仅保留当前使用的物品在桌面',
 7,'',1),

('HOME_DESK_PLANT_001','study','general','plant','书房植物',NULL,'optional','tip','no','no',
 '书房放置绿植，木旺文昌，有助于提升学习力和创造力',
 '书房宜放富贵竹（文昌位）、绿萝（净化空气）；植物不宜过大过多，影响书房气场',
 5,'木',1),

('HOME_DESK_WENCHANGWEI_001','study','position','desk','文昌位',NULL,'should','warning','no','no',
 '文昌位未利用（空置或杂乱），影响学习力和考试运',
 '书房文昌位宜放：富贵竹（4支）、文昌塔摆件、蓝色/绿色物品；保持整洁明亮',
 7,'木',1),

('HOME_DESK_BOOKSHELF_001','study','general','bookshelf','书架摆放',NULL,'should','warning','no','no',
 '书架摆放位置不当或书籍杂乱，影响书房气场，书架过高压迫座位',
 '书架宜靠墙摆放，不要正对座位；书籍按类分整齐；书架顶部不堆杂物',
 6,'木',1),

('HOME_DESK_LIGHT_001','study','general','lighting','书房照明',NULL,'should','warning','no','no',
 '书房照明不足或光线刺眼，影响用眼健康和工作效率',
 '书房需明亮照明，主灯+台灯双重照明；台灯放书桌左侧（右手写字光线不遮挡）；选色温5000K左右',
 6,'火',1),

('HOME_DESK_DIRECTION_001','study','position','desk','书桌朝向',NULL,'should','warning','yes','no',
 '书桌朝向不佳（背对门或朝向大凶方），影响思维和工作运势',
 '书桌坐向宜正对或侧对房门（能看到门为佳）；结合大门朝向选择文昌方位安桌',
 7,'',1),

('HOME_DESK_MINGUA_001','study','mingua','desk','书桌命卦',NULL,'should','warning','no','yes',
 '书桌坐向对应个人命卦凶方，影响工作效率和智慧能量',
 '书桌坐向宜朝向个人命卦生气位或天医位，有助于增强思维和获得贵人',
 8,'',1),

('HOME_DESK_COMPUTER_001','study','general','computer','电脑位置',NULL,'optional','tip','no','no',
 '书房电脑摆放位置影响用眼舒适度和工作效率',
 '电脑屏幕宜正对使用者，距离50-70cm；屏幕高度与眼睛齐平；避免窗户反光',
 4,'火',1),

('HOME_STUDY_COLOR_001','study','general','wall','书房颜色',NULL,'optional','tip','no','no',
 '书房颜色影响学习和创作状态，颜色与五行对应可增强文昌运',
 '书房宜用浅蓝、浅绿、米白等安静颜色；避免大红（刺激）和黑色（压抑）',
 4,'木',1),

('HOME_STUDY_DOOR_LOCK_001','study','general','door','书房门',NULL,'optional','tip','no','no',
 '书房有独立门，可创造专注工作/学习的独立空间，有利于聚气',
 '书房宜设实体门（非玻璃门），增强独立性和安全感；工作时关门聚气',
 4,'',1),

('HOME_STUDY_WENCHANGXING_001','study','general','decoration','书房文昌星摆件',NULL,'optional','tip','no','no',
 '书房或书桌上摆放文昌塔（四层木塔）或毛笔摆件，有助于催动文昌星运势',
 '文昌塔宜放书桌左前方；毛笔竖放笔筒，象征向上进取；选木质材料',
 4,'木',1),

-- 补充书房规则至约60条
('HOME_STUDY_CHAIR_001','study','general','chair','书房椅子',NULL,'should','warning','no','no',
 '书房椅子背后空旷（无依靠），工作坐立不安，主缺乏贵人',
 '书椅背后宜靠实墙；若椅后无墙，可在椅背放靠枕形成"虚靠山"',
 6,'',1),

('HOME_STUDY_TROPHY_001','study','general','trophy','奖状奖杯',NULL,'optional','tip','no','no',
 '书房展示奖状、奖杯等成就物，有助于激励能量，增强自信心和事业运',
 '奖状宜挂在书房正前方（南方，离卦，主名声）；奖杯放书桌左侧',
 3,'火',1),

('HOME_STUDY_BOOKS_001','study','general','books','书籍整理',NULL,'should','warning','no','no',
 '书架上书籍散乱倒伏，象征"文昌倒伏"，主学业不振、思维混乱',
 '书籍竖立整齐摆放；用书立固定；按主题或颜色分类，视觉整洁且便于取用',
 6,'木',1),

('HOME_STUDY_TRASH_001','study','general','trash','书房垃圾桶',NULL,'optional','tip','no','no',
 '书房垃圾桶摆放位置影响气场清洁度',
 '书房垃圾桶放在书桌侧面角落，不要正对座位；及时清倒，保持清洁',
 3,'',1),

('HOME_STUDY_AIR_001','study','general','ventilation','书房通风',NULL,'should','warning','no','no',
 '书房长期不通风，空气质量差，影响思维清晰度和学习效率',
 '书房定期开窗通风；可养一盆绿萝或吊兰净化空气；避免书房潮湿',
 5,'',1),

-- ============================================================
-- 通用规则（适用于全屋，50条）
-- ============================================================

('HOME_GENERAL_CLEAN_001','all','general','general','全屋整洁',NULL,'must','critical','no','no',
 '全屋杂乱，气场凌乱，"财不入乱门"，影响所有方面运势',
 '定期全面整理清洁；每个季节进行一次大扫除；不用物品断舍离，避免囤积',
 9,'',1),

('HOME_GENERAL_SMELL_001','all','general','general','全屋异味',NULL,'should','warning','no','no',
 '家中有异味（霉味、烟味、油烟），代表气场污浊，影响运势和健康',
 '定期开窗通风；使用精油扩香净化气场；厨房油烟及时排除；洗手间保持通风',
 7,'',1),

('HOME_GENERAL_LIGHT_001','all','general','lighting','全屋照明',NULL,'should','warning','no','no',
 '家中某个区域长期阴暗，气场沉积，主那一区对应运势（如卧室暗=桃花差，书房暗=事业差）',
 '确保全屋各区域照明充足；暗角可用小灯具补充；尤其财位（东南）要保持明亮',
 6,'火',1),

('HOME_GENERAL_PLANT_001','all','general','plant','绿植选择',NULL,'optional','tip','no','no',
 '家中植物选择影响家庭五行能量',
 '吉祥植物：发财树（财运）、富贵竹（学业）、绿萝（净化）、虎尾兰（辟邪）；忌：带刺植物放卧室',
 4,'木',1),

('HOME_GENERAL_WATER_001','all','general','water','全屋水管',NULL,'should','warning','no','no',
 '家中水管漏水，象征"漏财"，长期漏水影响财运',
 '发现漏水立即修缮；尤其财位（东南方）的漏水要优先处理',
 8,'水',1),

('HOME_GENERAL_DOOR_001','all','general','door','全屋门状态',NULL,'should','warning','no','no',
 '家中门铰链异响或门框变形，"鬼门关"之象，影响家庭运势',
 '定期保养门铰链（滴润滑油）；门开关顺畅无声；门框变形及时修缮',
 6,'',1),

('HOME_GENERAL_SHARP_001','all','taboo','sharp_items','全屋利器',NULL,'should','warning','no','no',
 '家中利器（刀具、剪刀）随意摆放，主容易发生意外，增加家庭争吵',
 '刀具统一收纳在刀架或抽屉中；剪刀等工具放入工具箱；儿童可触及位置避免利器',
 7,'金',1),

('HOME_GENERAL_MIRROR_001','all','taboo','mirror','全屋镜子',NULL,'should','warning','no','no',
 '家中镜子数量过多（超过5面）或悬挂位置不当，产生反煞效应',
 '控制全屋镜子数量；每面镜子确保不正对门、不正对床；镜子宜挂侧墙',
 6,'金',1),

('HOME_GENERAL_COLOR_001','all','general','color','全屋色调',NULL,'optional','tip','no','no',
 '全屋色调统一和谐，有助于气场流通；颜色冲突则气场混乱',
 '全屋选1-2种主色调，各房间可有变化但整体协调；避免每个房间颜色完全不同',
 4,'',1),

('HOME_GENERAL_ENTRY_001','all','general','entrance','入户玄关',NULL,'should','warning','no','no',
 '入户玄关凌乱（鞋子散落、堆放杂物），是家庭"第一气场"，凌乱则气场不顺',
 '玄关保持整洁：鞋子入柜、雨伞放伞桶；可放植物或小摆件迎气；每日扫地',
 7,'',1),

('HOME_GENERAL_TOILET_001','all','taboo','toilet','全屋卫生间',NULL,'should','warning','no','no',
 '卫生间是家中秽气聚集之处，其位置和整洁影响全家健康和财运',
 '卫生间门常关，马桶盖常盖（防秽气泄出）；保持通风干燥；在马桶水箱上方放粗盐或海盐化煞',
 8,'水',1),

('HOME_GENERAL_DEAD_PLANTS_001','all','taboo','dead_plant','枯萎植物',NULL,'must','critical','no','no',
 '家中摆放枯萎、干枯或死亡的植物，代表生机断绝，大凶，影响健康和财运',
 '发现枯萎植物立即移除；补种新鲜植物；假花假草虽不会枯萎，但缺乏生气，也不宜多放',
 9,'木',1),

('HOME_GENERAL_NORTHWEST_001','all','position','decoration','西北男主位',NULL,'optional','tip','no','no',
 '西北方为"乾位"，代表男主人、领导力和贵人，此位置的布置影响家庭男性运势',
 '西北方宜放金属摆件（金属球、铜器）、山岳画；避免放鱼缸、水元素（水克金）',
 5,'金',1),

('HOME_GENERAL_SOUTHWEST_001','all','position','decoration','西南女主位',NULL,'optional','tip','no','no',
 '西南方为"坤位"，代表女主人、情感和母性，影响家庭女性运势和感情生活',
 '西南方宜放：粉红水晶、双人照片、玫瑰花；避免过多金属（金克土）',
 5,'土',1),

('HOME_GENERAL_EAST_001','all','position','decoration','东方健康位',NULL,'optional','tip','no','no',
 '东方为"震位"，主健康，东方的布置影响家庭成员健康',
 '东方宜放绿植（木旺东方）、健康主题装饰；避免金属大型装饰（金克木）',
 5,'木',1),

('HOME_GENERAL_STAIR_001','all','general','stairs','楼梯风水',NULL,'should','warning','no','no',
 '楼梯是连接楼层气场的通道，其设计和整洁影响全屋气场流通',
 '楼梯保持整洁通畅；楼梯底部不堆杂物；楼梯扶手稳固；楼梯旁可放植物引导气流向上',
 6,'',1),

('HOME_GENERAL_KITCHEN_ENTRY_001','all','general','kitchen','厨房门',NULL,'should','warning','no','no',
 '厨房门正对大门，火气直出，冲犯入宅气场，主家庭成员健康受损',
 '厨房门宜半掩或安装推拉门，减少火气外泄；厨房门与大门间放屏风或植物阻隔',
 7,'火',1),

('HOME_GENERAL_INCENSE_001','all','general','incense','香炉供奉',NULL,'optional','tip','no','no',
 '家中适当点燃天然香（非化学香），有净化气场、镇宅纳福的功效',
 '天然沉香、檀香有净化作用；供奉用香保持规律；香炉摆放稳固，注意安全',
 3,'木',1),

('HOME_GENERAL_WINDOW_EAST_001','all','general','window','东面窗户',NULL,'optional','tip','no','no',
 '东面窗户迎接晨光（木旺之气），有助于家庭生气勃勃和健康',
 '东面窗户保持干净，清晨适当开窗迎接朝气；窗台可放小型绿植接受阳光',
 3,'木',1),

('HOME_GENERAL_SALT_001','all','general','salt','粗盐净化',NULL,'optional','tip','no','no',
 '粗盐（岩盐/海盐）具有净化负能量的功效，是简便实用的风水化煞工具',
 '在屋内四角各放一碟粗盐（约30g），每月更换一次；特别是长期阴暗或异味区域',
 3,'',1),

('HOME_GENERAL_DOOR_MAT_001','all','general','doormat','门垫',NULL,'optional','tip','no','no',
 '入户门垫是家庭"迎财纳气"的第一道关口',
 '门垫选有吉祥图案（如梅花、如意）；颜色选红色或棕色；定期清洗换新',
 3,'',1),

('HOME_GENERAL_CURTAIN_001','all','general','curtain','窗帘风水',NULL,'optional','tip','no','no',
 '窗帘颜色和材质影响各房间五行能量',
 '客厅窗帘选暖色系（米白、淡黄）聚气；卧室选遮光深色（助眠）；书房选淡蓝或淡绿（助思）',
 3,'',1),

('HOME_GENERAL_AIRY_001','all','general','ventilation','全屋通风',NULL,'should','warning','no','no',
 '家中长期不通风，气场郁结，负能量积聚，影响全家运势和健康',
 '每天上午9-11点开窗通风30分钟（阳气最旺时段）；特别注意卧室和书房通风',
 6,'',1),

('HOME_GENERAL_NUMBER_001','all','general','decoration','门牌号码',NULL,'optional','tip','no','no',
 '门牌号码数字的五行属性与居住者命卦的契合度影响宅运',
 '数字五行：1/6水，2/7火，3/8木，4/9金，5/10土；选择与个人喜用神相配的楼层/门牌',
 3,'',1);

-- 验证插入数量
SELECT COUNT(*) as total_rules, room_type FROM home_fengshui_rules GROUP BY room_type;

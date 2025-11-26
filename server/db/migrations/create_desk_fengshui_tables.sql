-- 办公桌风水规则表
CREATE TABLE IF NOT EXISTS `desk_fengshui_rules` (
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  `rule_code` VARCHAR(50) UNIQUE NOT NULL COMMENT '规则编码，如 DESK_KETTLE_001',
  `rule_type` VARCHAR(30) NOT NULL COMMENT '规则类型：basic/element_based/career/taboo',
  `item_name` VARCHAR(50) NOT NULL COMMENT '物品英文名，如 kettle, plant',
  `item_label` VARCHAR(50) NOT NULL COMMENT '物品中文名，如 烧水壶, 绿植',
  `ideal_position` JSON COMMENT '理想位置 {"direction": "left", "bagua": "east"}',
  `reason` TEXT COMMENT '风水依据说明',
  `priority` INT DEFAULT 1 COMMENT '优先级 1-10，数字越大优先级越高',
  `related_element` VARCHAR(10) COMMENT '关联五行：木/火/土/金/水',
  `conditions` JSON COMMENT '匹配条件，如 {"gender": "male", "career": "leader"}',
  `suggestion` TEXT COMMENT '具体摆放建议',
  `enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用 1:启用 0:禁用',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_rule_type` (`rule_type`),
  INDEX `idx_item_name` (`item_name`),
  INDEX `idx_related_element` (`related_element`),
  INDEX `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='办公桌风水规则表';

-- 办公桌风水分析记录表
CREATE TABLE IF NOT EXISTS `desk_analysis_records` (
  `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  `user_id` VARCHAR(100) COMMENT '用户ID',
  `image_url` VARCHAR(500) COMMENT '照片存储URL',
  `image_hash` VARCHAR(64) COMMENT '图片MD5哈希值，用于去重',
  `detected_items` JSON COMMENT '检测到的物品列表',
  `bazi_info` JSON COMMENT '用户八字信息',
  `matched_rules` JSON COMMENT '匹配的规则列表',
  `suggestions` JSON COMMENT '建议列表（adjustments/additions/removals）',
  `score` INT COMMENT '综合评分 0-100',
  `summary` TEXT COMMENT '分析总结',
  `analysis_duration` INT COMMENT '分析耗时（毫秒）',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_image_hash` (`image_hash`),
  INDEX `idx_created_at` (`created_at`),
  INDEX `idx_score` (`score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='办公桌风水分析记录表';

-- 插入示例规则数据（基于传统风水理论）
INSERT INTO `desk_fengshui_rules` 
(`rule_code`, `rule_type`, `item_name`, `item_label`, `ideal_position`, `reason`, `priority`, `related_element`, `conditions`, `suggestion`, `enabled`) 
VALUES
-- 基础规则：烧水壶
('DESK_KETTLE_001', 'basic', 'kettle', '烧水壶', 
 '{"direction": "left", "bagua": "east"}', 
 '烧水壶五行属火，应放在青龙位（左侧），青龙位宜动，火属阳，利于事业发展和提升贵人运',
 8, '火', NULL, 
 '建议将烧水壶放在办公桌左侧（青龙位），远离右侧（白虎位），以免形成"白虎开口"之局', 1),

-- 基础规则：绿植
('DESK_PLANT_001', 'basic', 'plant', '绿植', 
 '{"direction": "left", "bagua": "east"}', 
 '绿植五行属木，木旺东方，宜放在左侧或东南侧，生机勃勃，利于健康和创意',
 7, '木', NULL, 
 '建议在办公桌左侧或靠窗位置摆放绿植，选择圆叶植物为佳，避免带刺植物', 1),

-- 基础规则：电脑
('DESK_LAPTOP_001', 'basic', 'laptop', '笔记本电脑', 
 '{"direction": "center", "bagua": "center"}', 
 '电脑为工作核心工具，宜放在办公桌中央或偏左位置，便于操作，保持明堂开阔',
 9, NULL, NULL, 
 '电脑屏幕应正对使用者，避免侧身工作，保证光线充足，减少反光', 1),

-- 基础规则：书籍文件
('DESK_BOOK_001', 'basic', 'book', '书籍文件', 
 '{"direction": "back", "bagua": "north"}', 
 '书籍文件五行属木，宜放在后方或左侧，形成"靠山"，利于工作稳定和贵人相助',
 6, '木', NULL, 
 '建议将常用书籍和文件整齐摆放在办公桌后方或左侧，保持办公桌前方开阔', 1),

-- 基础规则：水杯
('DESK_CUP_001', 'basic', 'cup', '水杯', 
 '{"direction": "right-front", "bagua": "west"}', 
 '水杯方便取用，宜放在右前方，但不宜正对电脑，避免泼洒损坏设备',
 5, '水', NULL, 
 '建议将水杯放在办公桌右前方，触手可及处，使用带盖的杯子更佳', 1),

-- 基础规则：鼠标键盘
('DESK_MOUSE_001', 'basic', 'mouse', '鼠标', 
 '{"direction": "right", "bagua": "west"}', 
 '鼠标宜放在电脑右侧（右手使用者），符合人体工学，提高工作效率',
 4, NULL, '{"handedness": "right"}', 
 '鼠标应与键盘在同一水平线上，距离适中，避免手臂悬空', 1),

-- 基础规则：手机
('DESK_PHONE_001', 'basic', 'cell phone', '手机', 
 '{"direction": "left-front", "bagua": "east"}', 
 '手机属于通讯工具，宜放在左前方，方便查看，但不宜正对电脑，避免分散注意力',
 5, NULL, NULL, 
 '建议将手机放在办公桌左前方或抽屉中，工作时建议静音或震动模式', 1),

-- 基础规则：时钟
('DESK_CLOCK_001', 'basic', 'clock', '时钟', 
 '{"direction": "front", "bagua": "south"}', 
 '时钟宜放在正前方可见位置，便于掌握时间，提升工作效率',
 4, NULL, NULL, 
 '时钟应放在视线可及处，但不宜正对座位，避免形成"时间压迫感"', 1),

-- 禁忌规则：仙人掌
('DESK_CACTUS_001', 'taboo', 'cactus', '仙人掌', 
 '{"direction": "avoid-front", "bagua": "avoid-south"}', 
 '仙人掌带刺，不宜放在前方（朱雀位），易招口舌是非，影响人际关系',
 9, NULL, NULL, 
 '如需摆放仙人掌，建议放在办公室角落或窗台，远离座位正前方', 1),

-- 禁忌规则：镜子
('DESK_MIRROR_001', 'taboo', 'mirror', '镜子', 
 '{"direction": "avoid-all", "bagua": "avoid-all"}', 
 '镜子不宜正对办公桌，容易形成反煞，影响精神集中和情绪稳定',
 8, NULL, NULL, 
 '办公桌附近避免摆放镜子，如有镜子应调整角度，不要直接照射座位', 1),

-- 五行规则：金属摆件（针对喜神为金的人）
('DESK_METAL_001', 'element_based', 'metal ornament', '金属摆件', 
 '{"direction": "right", "bagua": "west"}', 
 '金属摆件五行属金，金旺西方，宜放在右侧或西北侧，利于权威和领导力',
 7, '金', '{"xishen": "金"}', 
 '如您喜神为金，建议在办公桌右侧或西北方向放置金属笔筒、金属摆件等', 1),

-- 五行规则：水养植物（针对喜神为水的人）
('DESK_WATER_001', 'element_based', 'water feature', '水养植物', 
 '{"direction": "front-left", "bagua": "north"}', 
 '水养植物五行属水，水旺北方，利于财运和智慧，特别适合喜神为水的人',
 8, '水', '{"xishen": "水"}', 
 '如您喜神为水，建议在办公桌北侧或左前方放置水养植物、小鱼缸或蓝色物品', 1),

-- 五行规则：木质摆件（针对喜神为木的人）
('DESK_WOOD_001', 'element_based', 'wooden ornament', '木质摆件', 
 '{"direction": "left", "bagua": "east"}', 
 '木质摆件五行属木，木旺东方，利于成长和发展，特别适合喜神为木的人',
 7, '木', '{"xishen": "木"}', 
 '如您喜神为木，建议在办公桌东侧或左侧放置木质摆件、绿色植物', 1),

-- 五行规则：红色物品（针对喜神为火的人）
('DESK_FIRE_001', 'element_based', 'red item', '红色物品', 
 '{"direction": "front", "bagua": "south"}', 
 '红色物品五行属火，火旺南方，利于名声和事业，特别适合喜神为火的人',
 7, '火', '{"xishen": "火"}', 
 '如您喜神为火，建议在办公桌南侧或前方放置红色物品、暖色调装饰', 1),

-- 五行规则：陶瓷摆件（针对喜神为土的人）
('DESK_EARTH_001', 'element_based', 'ceramic ornament', '陶瓷摆件', 
 '{"direction": "center", "bagua": "center"}', 
 '陶瓷摆件五行属土，土主稳定和包容，特别适合喜神为土的人',
 7, '土', '{"xishen": "土"}', 
 '如您喜神为土，建议在办公桌中央或西南方向放置陶瓷摆件、黄色或棕色物品', 1);


-- 办公桌风水规则 - 严格基于文档内容
-- 清空旧规则，重新导入

TRUNCATE TABLE desk_fengshui_rules;

-- ========================================
-- 青龙位规则（左侧）
-- ========================================

-- 1. 青龙位基础规则：必须高于白虎位
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('QINGLONG_HEIGHT_001', 'position', 'left_items', '青龙位物品', '{"directions": ["left", "front_left", "back_left"]}', '青龙位必须起势高，象征贵人协助', '青龙位摆放的东西一定要比右手边更高一些，一切跟办公材料有关的东西，都是放左边最佳，可以叠起来或者竖起来放', 95, 1);

-- 2. 青龙位"动"象物品
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('QINGLONG_KETTLE_001', 'position', 'kettle', '养生壶/烧水壶', '{"directions": ["left", "front_left", "back_left"]}', '青龙位适合放具有"动"象的物品', '✅ 养生壶/烧水壶适合放在青龙位（左侧），符合"动"象原则，有助于提升贵人运', 90, 1),
('QINGLONG_HUMIDIFIER_001', 'position', 'humidifier', '加湿器', '{"directions": ["left", "front_left", "back_left"]}', '青龙位适合放具有"动"象的物品', '✅ 加湿器适合放在青龙位（左侧），符合"动"象原则', 90, 1),
('QINGLONG_FAN_001', 'position', 'fan', '风扇', '{"directions": ["left", "front_left", "back_left"]}', '青龙位适合放具有"动"象的物品', '✅ 风扇适合放在青龙位（左侧），符合"动"象原则', 90, 1),
('QINGLONG_PHONE_001', 'position', 'phone', '电话', '{"directions": ["left", "front_left", "back_left"]}', '青龙位适合放电话等物品', '✅ 电话适合放在青龙位（左侧）', 85, 1);

-- 3. 青龙位吉祥物
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('QINGLONG_LUCKY_001', 'position', 'lucky_cat', '招财猫', '{"directions": ["left", "front_left", "back_left"], "height": "high"}', '开运小摆件应放在高处或青龙位', '✅ 招财猫放在青龙位（左侧）或高处最佳，有助于开运', 88, 1),
('QINGLONG_TREE_001', 'position', 'plant', '发财树/绿植', '{"directions": ["left", "front_left", "back_left"]}', '青龙位适合摆放鲜花、绿植', '✅ 发财树/绿植适合放在青龙位（左侧），注意要宽叶植物，不要仙人掌、缠绕性藤类', 88, 1);

-- 4. 青龙位办公材料
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('QINGLONG_FILES_001', 'position', 'files', '文件/资料架', '{"directions": ["left", "front_left", "back_left"]}', '办公材料放左边最佳', '✅ 文件/资料架放在青龙位（左侧）很好，可以叠高或竖起来放', 85, 1);

-- ========================================
-- 白虎位规则（右侧）
-- ========================================

-- 5. 白虎位基础规则：低于青龙位、简洁
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('BAIHU_LOW_001', 'position', 'right_items', '白虎位物品', '{"directions": ["right", "front_right", "back_right"], "height": "low"}', '白虎位要低于青龙位，以简洁为主', '白虎位摆放的东西整体上比青龙位要低一些，以简单为主。所谓"宁叫青龙高万丈，不叫白虎抬起头"', 95, 1);

-- 6. 白虎位适合物品
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('BAIHU_MOUSE_001', 'position', 'mouse', '鼠标', '{"directions": ["right", "front_right"]}', '白虎位适合简单物品', '✅ 鼠标放在白虎位（右侧）很合适', 85, 1),
('BAIHU_CUP_001', 'position', 'cup', '水杯', '{"directions": ["right", "front_right", "back_right"]}', '白虎位可以放水杯', '✅ 水杯可以放在白虎位（右侧），但注意不要在右边烧水', 85, 1),
('BAIHU_PEN_001', 'position', 'pen_holder', '笔筒', '{"directions": ["right", "front_right", "back_right"]}', '白虎位可以放笔筒', '✅ 笔筒可以放在白虎位（右侧）', 80, 1),
('BAIHU_BOOK_001', 'position', 'book', '书籍', '{"directions": ["right", "front_right", "back_right"], "height": "low"}', '白虎位可以放书籍，但不宜太高', '✅ 书籍可以放在白虎位（右侧），但注意不宜太高，避免压过青龙位', 80, 1),
('BAIHU_CRYSTAL_001', 'position', 'crystal', '水晶球', '{"directions": ["right", "front_right", "back_right"]}', '白虎位可以放水晶球', '✅ 水晶球可以放在白虎位（右侧）', 80, 1);

-- 7. 白虎位禁忌物品（"动"象物品不宜放右侧）
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('BAIHU_KETTLE_TABOO', 'taboo', 'kettle', '烧水壶', '{"directions": ["left", "front_left", "back_left"]}', '白虎喜"静"，不要在右边烧水', '⚠️ 烧水壶在白虎位（右侧）不合适！建议移至青龙位（左侧），白虎喜静不喜动', 92, 1),
('BAIHU_PHONE_TABOO', 'taboo', 'phone', '手机/电话', '{"directions": ["left", "front_left", "back_left"]}', '白虎喜"静"，手机电话等不要放在右边', '⚠️ 手机/电话在白虎位（右侧）不合适！建议移至青龙位（左侧），白虎喜静不喜动', 92, 1),
('BAIHU_CLUTTER_TABOO', 'taboo', 'clutter', '杂物', NULL, '白虎位不要堆积太杂的东西', '⚠️ 白虎位（右侧）堆积太多杂物，会造成额外压力。建议精简，保持简洁', 88, 1);

-- ========================================
-- 朱雀位规则（前方）
-- ========================================

-- 8. 朱雀位基础规则：开阔明亮
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('ZHUQUE_OPEN_001', 'position', 'front_area', '朱雀位（前方明堂）', '{"directions": ["front", "center"]}', '朱雀位是前景位，越开阔、越亮越好', '朱雀位（前方）应保持开阔明亮，不要有太多遮挡之物。如果前方有同事，收拾得干干净净即可。电脑壁纸可以用广阔高远的意象', 95, 1);

-- 9. 朱雀位显示器规则
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('ZHUQUE_MONITOR_001', 'position', 'monitor', '显示器', '{"directions": ["front", "center"]}', '显示器放在前方是正常的', '✅ 显示器放在朱雀位（前方中央）符合日常使用习惯，保持屏幕整洁即可', 85, 1),
('ZHUQUE_LAPTOP_001', 'position', 'laptop', '笔记本电脑', '{"directions": ["front", "center"]}', '笔记本放在前方是正常的', '✅ 笔记本电脑放在朱雀位（前方）符合日常使用习惯', 85, 1);

-- 10. 朱雀位管理者规则
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, conditions, enabled) VALUES
('ZHUQUE_MANAGER_001', 'position', 'front_items', '朱雀位物品（管理者）', NULL, '管理者前方不能有任何摆设', '💡 如果您是管理者，前方（朱雀位）不能有任何摆设，绿植也不要放', 90, '{"role": "manager"}', 1);

-- ========================================
-- 玄武位规则（后方）
-- ========================================

-- 11. 玄武位基础规则：靠山
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('XUANWU_WALL_001', 'position', 'back_area', '玄武位（后方靠山）', '{"directions": ["back"]}', '玄武位代表稳固、靠山、贵人扶持', '💡 玄武位（后方）最好背靠实墙，不要背靠门或落地窗。如无法调整，可在椅背后放褐色/咖啡色靠枕（山形或写着"靠山"），或挂一件衣服，营造"虚拟靠山"', 95, 1);

-- ========================================
-- 其他风水建议
-- ========================================

-- 12. 形煞化解
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('GENERAL_COLUMN_001', 'taboo', 'column_angle', '柱子角冲', NULL, '柱子角对切座位形成形煞', '⚠️ 注意避开柱子角煞。化解方法：1）搭屏风隔开；2）放圆型物品如水晶球、葫芦挡煞；3）在柱子上挂"抬头见喜"字画；4）用高大绿植遮挡', 90, 1);

-- 13. 整洁规则
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('GENERAL_TIDY_001', 'general', 'desk', '办公桌整洁', NULL, '财不入乱门', '💡 办公桌可以东西多，但不可乱。财不入乱门，零碎小部件能收纳就收纳', 70, 1);

-- 14. 尖锐物品规则
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('GENERAL_SHARP_001', 'taboo', 'scissors', '剪刀/尖锐物', NULL, '尖锐物品散放易形成煞气', '⚠️ 利器、剪刀、指甲钳等尖锐物品要收纳起来，不要散放在桌上显眼的地方。放到笔筒里，还可以防小人', 85, 1);

-- 15. 五行规则 - 水晶
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, conditions, enabled) VALUES
('ELEMENT_CRYSTAL_001', 'element', 'crystal', '水晶', NULL, '根据五行喜忌摆放水晶', '💡 电脑属火，火太旺。如果您不喜火，可以摆水晶平衡磁场', 75, '{"dislike_element": "火"}', 1);

-- 16. 植物规则
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('GENERAL_FAKE_FLOWER_001', 'taboo', 'fake_flower', '假花', NULL, '假花不宜摆放', '⚠️ 不要在桌上摆放假花', 80, 1),
('GENERAL_CACTUS_001', 'taboo', 'cactus', '仙人掌/藤类植物', NULL, '仙人掌、缠绕性藤类不宜', '⚠️ 绿植要以宽叶植物为主，不要摆仙人掌、缠绕性的藤类植物', 82, 1),
('GENERAL_PLANT_WATER_001', 'general', 'plant', '绿植', '{"directions": ["left", "front_left", "back_left"]}', '鲜花和绿植要勤换水', '💡 鲜花和绿植要勤换水，保持新鲜。绿植要以宽叶植物为主', 72, 1);

-- 17. 电脑壁纸建议
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, enabled) VALUES
('GENERAL_WALLPAPER_001', 'general', 'computer', '电脑壁纸', NULL, '电脑壁纸影响心境', '💡 电脑屏幕壁纸可以选用视野开阔的风景画或山水图（水是财，山是贵人），有助于提升运势', 68, 1);

-- ========================================
-- 五行喜神规则
-- ========================================

-- 18. 喜神木
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_WOOD_001', 'element', 'plant', '绿植/木制品', '{"directions": ["left", "front_left", "back_left"]}', '喜神木应增加木属性物品', '⭐ 您的喜神为木，建议在青龙位（左侧）摆放绿植（宽叶植物如发财树、富贵竹）或木制品，增强运势', 100, '木', '{"xishen": "木"}', 1);

-- 19. 喜神火
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_FIRE_001', 'element', 'red_item', '红色物品', '{"directions": ["front", "center"]}', '喜神火应增加火属性物品', '⭐ 您的喜神为火，建议在朱雀位（前方）摆放红色物品、台灯或热源物品，增强运势', 100, '火', '{"xishen": "火"}', 1);

-- 20. 喜神土
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_EARTH_001', 'element', 'ceramic', '陶瓷/黄色物品', '{"directions": ["center"]}', '喜神土应增加土属性物品', '⭐ 您的喜神为土，建议在中央位置摆放陶瓷摆件或黄色物品，增强运势', 100, '土', '{"xishen": "土"}', 1);

-- 21. 喜神金
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_METAL_001', 'element', 'metal_item', '金属物品', '{"directions": ["right", "back_right"]}', '喜神金应增加金属性物品', '⭐ 您的喜神为金，建议在白虎位（右后方）摆放金属摆件、时钟或水晶球，增强运势', 100, '金', '{"xishen": "金"}', 1);

-- 22. 喜神水
INSERT INTO desk_fengshui_rules (rule_code, rule_type, item_name, item_label, ideal_position, reason, suggestion, priority, related_element, conditions, enabled) VALUES
('XISHEN_WATER_001', 'element', 'water_item', '水相关物品', '{"directions": ["front", "front_right"]}', '喜神水应增加水属性物品', '⭐ 您的喜神为水，建议在前方或右前方摆放水杯、水瓶、水培植物或鱼缸（如条件允许），增强财运', 100, '水', '{"xishen": "水"}', 1);



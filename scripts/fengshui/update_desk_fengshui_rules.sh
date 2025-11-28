#!/bin/bash
# 更新办公桌风水规则（补充详细规则）

set -e

echo "================================================"
echo "  更新办公桌风水规则"
echo "================================================"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "【步骤1】备份现有规则..."
mysql -h 127.0.0.1 -P 13306 -u root -proot123456 --default-character-set=utf8mb4 bazi_system \
  -e "SELECT COUNT(*) as '现有规则数' FROM desk_fengshui_rules;"

echo ""
echo "【步骤2】添加新规则..."
mysql -h 127.0.0.1 -P 13306 -u root -proot123456 --default-character-set=utf8mb4 bazi_system <<'EOF'

-- 插入补充规则（如果不存在）
INSERT IGNORE INTO desk_fengshui_rules 
(rule_code, rule_type, item_name, item_label, ideal_position, reason, priority, related_element, conditions, suggestion, enabled) 
VALUES

-- 青龙位专属规则
('DESK_QINGLONG_001', 'position', 'left_area', '青龙位（左侧）', 
 '{"direction": "left", "bagua": "east"}', 
 '青龙位五行属木，代表尊贵、威严、权利、贵人，是工位中最重要和最吉祥的位置。青龙位必须起势高，象征贵人协助',
 10, '木', NULL, 
 '青龙位应摆放高于右侧的物品，如文件架、书籍、绿植等。可放置具有"动"象的物品，如养生壶、加湿器、风扇。吉祥物如招财猫、发财树、金貔貅等应放在青龙位或高处', 1),

-- 白虎位专属规则
('DESK_BAIHU_001', 'position', 'right_area', '白虎位（右侧）', 
 '{"direction": "right", "bagua": "west"}', 
 '白虎位五行属金，代表收敛、压力。白虎喜"静"，宜简洁低矮。所谓"宁叫青龙高万丈，不叫白虎抬起头"',
 9, '金', NULL, 
 '白虎位应保持简洁，摆放低矮物品如鼠标、水杯、笔筒。避免堆积杂物，不要放置手机、电话、烧水壶等"动"象物品。整体高度应低于左侧青龙位', 1),

-- 朱雀位专属规则
('DESK_ZHUQUE_001', 'position', 'front_area', '朱雀位（前方明堂）', 
 '{"direction": "front", "bagua": "south"}', 
 '朱雀位为明堂，五行属火，代表光明、前景。朱雀是种鸟，喜欢光。前方应越开阔、越亮越好',
 9, '火', NULL, 
 '朱雀位应保持开阔明亮，不要有过多遮挡。如有同事在前方，保持整洁即可。格子工位可贴激励装饰，电脑壁纸用广阔高远的意象。管理者前方不能有任何摆设', 1),

-- 玄武位专属规则
('DESK_XUANWU_001', 'position', 'back_area', '玄武位（后方靠山）', 
 '{"direction": "back", "bagua": "north"}', 
 '玄武位五行属水，代表稳固、靠山、贵人扶持，是第二重要的位置。最好背靠实墙',
 10, '水', NULL, 
 '最佳是背靠实墙，不要背靠门或落地窗。如无法调整，可在椅背后放褐色或咖啡色靠枕（山形或写着"靠山"），或挂一件衣服，营造"虚拟靠山"', 1),

-- 形煞规则
('DESK_XINGSHA_001', 'taboo', 'column_angle', '柱子角冲', 
 '{"direction": "avoid-all", "bagua": "avoid-all"}', 
 '办公室最常见的形煞：柱子角对切座位，会导致各方面都不顺',
 10, NULL, NULL, 
 '避免选择被柱子角切到的座位。如已在此位置，可：1）搭屏风隔开；2）放圆型物品如水晶球、葫芦挡煞；3）在柱子上挂好寓意字画如"抬头见喜"；4）用高大绿植遮挡', 1),

-- 整洁规则
('DESK_CLEAN_001', 'basic', 'organization', '桌面整洁', 
 '{"direction": "all", "bagua": "all"}', 
 '整个办公桌可以东西多，但不可乱。财不入乱门，零碎小部件能收纳就收纳',
 8, NULL, NULL, 
 '保持桌面整洁有序，文件和物品分类收纳。避免杂乱堆积，以免影响财运和工作效率', 1),

-- 利器规则
('DESK_SHARP_001', 'taboo', 'sharp_tools', '利器剪刀', 
 '{"direction": "avoid-visible", "bagua": "avoid-visible"}', 
 '利器、剪刀、指甲钳等尖锐物品切忌散放在桌上显眼的地方，容易招小人',
 8, NULL, NULL, 
 '尖锐物品应收纳起来，可放到笔筒里或抽屉中。收纳整齐还可以防小人', 1),

-- 假花规则
('DESK_FAKE_FLOWER_001', 'taboo', 'fake_flower', '假花', 
 '{"direction": "avoid-all", "bagua": "avoid-all"}', 
 '不要在桌上摆放假花，缺乏生气，不利运势',
 7, NULL, NULL, 
 '应摆放真实的鲜花或绿植，并勤换水。选择宽叶植物为佳，不要摆仙人掌、缠绕性藤类植物', 1),

-- 电脑屏幕建议
('DESK_SCREEN_001', 'basic', 'computer_screen', '电脑屏幕壁纸', 
 '{"direction": "center", "bagua": "center"}', 
 '电脑属火，火太旺时可用适当元素平衡。屏幕壁纸可影响心理和运势',
 6, NULL, NULL, 
 '电脑屏幕可选用视野开阔的风景画或山水图（水是财，山是贵人）。如不喜火，可摆水晶平衡磁场', 1),

-- 绿植详细规则
('DESK_PLANT_DETAIL_001', 'basic', 'plant_detail', '绿植摆放', 
 '{"direction": "left", "bagua": "east"}', 
 '绿植五行属木，宜放东方或左侧。应选择宽叶植物，避免带刺植物',
 8, '木', NULL, 
 '绿植宜选：发财树、绿萝、富贵竹等宽叶植物。避免：仙人掌、仙人球等带刺植物。需勤换水保持生机', 1),

-- 吉祥物规则
('DESK_LUCKY_001', 'basic', 'lucky_ornament', '吉祥物摆件', 
 '{"direction": "left", "bagua": "east"}', 
 '开运的小摆件如招财猫、发财树、金貔貅等，应放在高处或青龙位',
 7, NULL, NULL, 
 '吉祥物应放在青龙位（左侧）或办公桌较高的位置，不可随意摆放', 1),

-- 资料架文件规则
('DESK_FILES_001', 'basic', 'file_rack', '文件资料架', 
 '{"direction": "left", "bagua": "east"}', 
 '文件资料架应放在左侧或后方，形成"靠山"和贵人助力',
 8, '木', NULL, 
 '一切办公材料相关的东西，都应放左边最佳，可叠起来或竖起来放。避免放在右侧白虎位造成压力', 1),

-- 电话手机规则
('DESK_PHONE_DETAIL_001', 'basic', 'phone_detail', '电话手机', 
 '{"direction": "left-front", "bagua": "east"}', 
 '电话手机属于通讯工具，具有"动"象，应放在青龙位（左侧）',
 7, NULL, NULL, 
 '电话、手机应放在左前方或左侧，避免放在右侧白虎位。白虎喜静，不宜放动象物品', 1),

-- 水杯详细规则
('DESK_CUP_DETAIL_001', 'basic', 'cup_detail', '水杯摆放', 
 '{"direction": "right-front", "bagua": "west"}', 
 '水杯五行属水，可放在右前方方便取用，但不宜正对电脑',
 6, '水', NULL, 
 '水杯宜放右前方，触手可及处。建议使用带盖的杯子更佳。不要在右边烧水', 1);

EOF

echo ""
echo "【步骤3】验证更新结果..."
mysql -h 127.0.0.1 -P 13306 -u root -proot123456 --default-character-set=utf8mb4 bazi_system \
  -e "SELECT COUNT(*) as '更新后规则数' FROM desk_fengshui_rules; 
      SELECT rule_type, COUNT(*) as count FROM desk_fengshui_rules GROUP BY rule_type;"

echo ""
echo "【步骤4】清理Redis缓存..."
redis-cli -h 127.0.0.1 -p 16379 DEL "desk_fengshui:rules:*" 2>/dev/null || echo "   (Redis缓存已清理或无缓存)"

echo ""
echo "================================================"
echo "  ✅ 规则更新完成！"
echo "================================================"
echo ""
echo "新增规则类型："
echo "  - position: 四象方位规则（青龙、白虎、朱雀、玄武）"
echo "  - basic: 详细的基础规则"
echo "  - taboo: 禁忌和形煞规则"
echo ""
echo "建议重启服务以应用更新："
echo "  ./scripts/stop_desk_fengshui_service.sh"
echo "  ./scripts/start_desk_fengshui_service.sh"
echo ""


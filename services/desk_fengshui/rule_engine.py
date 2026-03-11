# -*- coding: utf-8 -*-
"""
办公桌风水规则引擎
匹配物品与风水规则，生成调整建议
"""

import sys
import os
import json
import logging
import hashlib
from typing import List, Dict, Optional

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger(__name__)

# 尝试导入Redis（可选依赖）
try:
    from shared.config.redis import get_redis_client
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    get_redis_client = None


class DeskFengshuiEngine:
    """办公桌风水规则引擎"""
    
    # 五行对应的物品类别
    ELEMENT_ITEMS = {
        '木': ['plant', 'wooden ornament', 'book'],
        '火': ['kettle', 'red item', 'laptop'],
        '土': ['ceramic ornament', 'yellow item'],
        '金': ['metal ornament', 'scissors', 'clock'],
        '水': ['cup', 'bottle', 'water feature', 'fish_tank']
    }
    
    # 物品详细风水配置（核心：物品级精准分析）
    ITEM_FENGSHUI_CONFIG = {
        'cup': {
            'label': '水杯',
            'element': '水',
            'ideal_positions': ['right', 'front_right', 'front'],
            'avoid_positions': [],
            'position_reasons': {
                'right': '水杯放在右侧（白虎位）符合静态原则，便于取用',
                'front_right': '右前方位置取用方便，不影响工作',
                'front': '前方放置便于取用，保持工作区整洁',
                'left': '左侧（青龙位）可以放置，但注意不要遮挡动态物品'
            },
            'fengshui_benefit': '水主财运和智慧，水杯保持有水状态可增强财运',
            'tips': '建议水杯常保有水，象征财源不断；选用圆润造型更佳'
        },
        'kettle': {
            'label': '烧水壶/养生壶',
            'element': '火',
            'ideal_positions': ['left', 'front_left', 'back_left'],
            'avoid_positions': ['right', 'front_right', 'back_right'],
            'position_reasons': {
                'left': '烧水壶属"动"象，放在青龙位（左侧）符合"左动右静"原则，有助提升贵人运',
                'front_left': '左前方位置方便取用，且保持动态在青龙位',
                'back_left': '左后方位置稍远但符合风水原则',
                'right': '⚠️ 白虎位忌动！烧水沸腾属动象，放右侧易惹是非口舌',
                'front_right': '⚠️ 右前方仍属白虎位，不宜放置烧水壶',
                'back_right': '⚠️ 右后方属白虎位，烧水壶在此位置不利'
            },
            'fengshui_benefit': '烧水壶代表活力和动力，正确摆放可提升事业运',
            'tips': '如果右侧有烧水壶，强烈建议移至左侧'
        },
        'laptop': {
            'label': '笔记本电脑',
            'element': '火',
            'ideal_positions': ['center', 'front'],
            'avoid_positions': [],
            'position_reasons': {
                'center': '电脑放在正中央便于工作，符合主位原则',
                'front': '电脑在前方（朱雀位）视野开阔，利于工作',
                'left': '偏左放置也可，不影响风水',
                'right': '偏右放置也可，不影响风水'
            },
            'fengshui_benefit': '电脑是现代办公核心，保持屏幕整洁可提升事业运',
            'tips': '电脑壁纸建议使用开阔风景或山水图，象征前程似锦'
        },
        'mouse': {
            'label': '鼠标',
            'element': '金',
            'ideal_positions': ['right', 'front_right'],
            'avoid_positions': [],
            'position_reasons': {
                'right': '鼠标放在右侧符合使用习惯（右手用户），也符合白虎位静态原则',
                'front_right': '右前方便于操作，位置合适',
                'left': '左手用户可放左侧，不影响风水'
            },
            'fengshui_benefit': '鼠标属于执行工具，正确摆放有助提升执行力',
            'tips': '保持鼠标垫整洁，避免杂乱'
        },
        'potted plant': {
            'label': '绿植/盆栽',
            'element': '木',
            'ideal_positions': ['left', 'front_left', 'back_left'],
            'avoid_positions': [],
            'position_reasons': {
                'left': '绿植放在青龙位（左侧）最佳，木旺东方，增强贵人运和生机',
                'front_left': '左前方也是青龙位范围，适合摆放绿植',
                'back_left': '左后方可以摆放较高的绿植，增强青龙位气势',
                'right': '右侧可以放小型绿植，但高度应低于左侧',
                'front': '前方可放小型绿植，但不要遮挡视线'
            },
            'fengshui_benefit': '绿植代表生机和贵人运，是办公桌必备风水物品',
            'tips': '选择宽叶植物如发财树、富贵竹，避免仙人掌等带刺植物'
        },
        'plant': {
            'label': '绿植',
            'element': '木',
            'ideal_positions': ['left', 'front_left', 'back_left'],
            'avoid_positions': [],
            'position_reasons': {
                'left': '绿植放在青龙位（左侧）最佳，木旺东方，增强贵人运和生机',
                'front_left': '左前方也是青龙位范围，适合摆放绿植',
                'back_left': '左后方可以摆放较高的绿植，增强青龙位气势'
            },
            'fengshui_benefit': '绿植代表生机和贵人运，是办公桌必备风水物品',
            'tips': '选择宽叶植物如发财树、富贵竹，避免仙人掌等带刺植物'
        },
        'cell phone': {
            'label': '手机',
            'element': '火',
            'ideal_positions': ['left', 'front_left'],
            'avoid_positions': ['right', 'front_right'],
            'position_reasons': {
                'left': '手机经常响铃，属"动"象，放在青龙位（左侧）符合风水原则',
                'front_left': '左前方便于查看和接听',
                'right': '⚠️ 手机在白虎位经常响动，易惹口舌是非',
                'front_right': '⚠️ 右前方仍属白虎位，不宜放手机'
            },
            'fengshui_benefit': '手机代表沟通和人脉，正确摆放有助人际关系',
            'tips': '手机建议放在左侧，工作时可静音减少干扰'
        },
        'book': {
            'label': '书籍',
            'element': '木',
            'ideal_positions': ['left', 'back_left', 'back'],
            'avoid_positions': [],
            'position_reasons': {
                'left': '书籍放在青龙位可增强学业运和贵人运',
                'back_left': '左后方适合摆放较多书籍，增强靠山',
                'back': '后方放书籍可形成"书山"，增强靠山运'
            },
            'fengshui_benefit': '书籍代表知识和智慧，也可作为靠山象征',
            'tips': '书籍可以竖起来或叠放在左侧，增强青龙位高度'
        },
        'scissors': {
            'label': '剪刀',
            'element': '金',
            'ideal_positions': ['drawer', 'pen_holder'],
            'avoid_positions': ['visible', 'desk_surface'],
            'position_reasons': {
                'drawer': '剪刀等利器应收纳在抽屉里，不宜外露',
                'pen_holder': '可以放在笔筒里，刀尖朝下，有防小人作用',
                'visible': '⚠️ 利器外露易招惹是非和小人'
            },
            'fengshui_benefit': '剪刀收纳得当可防小人，外露则招是非',
            'tips': '剪刀、指甲钳等利器一定要收纳起来，不要散放桌面'
        },
        'clock': {
            'label': '时钟',
            'element': '金',
            'ideal_positions': ['left', 'front'],
            'avoid_positions': ['back'],
            'position_reasons': {
                'left': '时钟放在青龙位可以，但不要太大',
                'front': '前方可以放时钟，便于查看时间',
                'back': '⚠️ 后方不宜放时钟，有"背后有人催"的寓意'
            },
            'fengshui_benefit': '时钟代表时间管理，正确摆放有助提升效率',
            'tips': '办公桌上的时钟不宜太大，以小巧为佳'
        },
        'bottle': {
            'label': '水瓶',
            'element': '水',
            'ideal_positions': ['right', 'front_right', 'front'],
            'avoid_positions': [],
            'position_reasons': {
                'right': '水瓶放在右侧便于取用，符合静态原则',
                'front_right': '右前方位置取用方便',
                'front': '前方放置也可以'
            },
            'fengshui_benefit': '水瓶保持有水可增强财运',
            'tips': '建议水瓶常保有水，选用透明或蓝色更佳'
        },
        'vase': {
            'label': '花瓶',
            'element': '水',
            'ideal_positions': ['left', 'front_left'],
            'avoid_positions': [],
            'position_reasons': {
                'left': '花瓶放在青龙位可增强贵人运，尤其是插鲜花时',
                'front_left': '左前方适合放小型花瓶'
            },
            'fengshui_benefit': '花瓶插鲜花可增强桃花运和人缘',
            'tips': '注意勤换水，不要让花枯萎；不建议放假花'
        },
        'teddy bear': {
            'label': '玩偶',
            'element': '土',
            'ideal_positions': ['left', 'front_left'],
            'avoid_positions': ['right'],
            'position_reasons': {
                'left': '玩偶放在青龙位可增添温馨感',
                'front_left': '左前方适合放小型玩偶',
                'right': '白虎位不宜放太多装饰品'
            },
            'fengshui_benefit': '适量玩偶可缓解工作压力',
            'tips': '玩偶不宜太多，1-2个即可，保持桌面整洁'
        },
        'tv': {
            'label': '显示器',
            'element': '火',
            'ideal_positions': ['front', 'center'],
            'avoid_positions': [],
            'position_reasons': {
                'front': '显示器放在正前方（朱雀位）最佳，视野开阔',
                'center': '居中放置符合工作需求'
            },
            'fengshui_benefit': '显示器保持整洁，壁纸选择开阔风景可提升运势',
            'tips': '屏幕壁纸建议用山水或开阔风景，象征前程远大'
        },
        'keyboard': {
            'label': '键盘',
            'element': '金',
            'ideal_positions': ['front', 'center'],
            'avoid_positions': [],
            'position_reasons': {
                'front': '键盘放在正前方便于打字',
                'center': '居中放置符合人体工学'
            },
            'fengshui_benefit': '键盘是输入工具，保持整洁有助思路清晰',
            'tips': '定期清洁键盘，保持整洁'
        }
    }
    
    # 五行-物品-建议映射（用于喜神忌神分析）
    WUXING_RECOMMENDATIONS = {
        '木': {
            'items': ['绿植', '木制品', '书籍', '文件架'],
            'colors': ['绿色', '青色'],
            'position': '左侧（青龙位/东方）',
            'benefit': '生机、贵人运、事业发展、学业进步',
            'specific_suggestions': [
                {'item': '发财树/富贵竹', 'position': '左侧', 'reason': '木旺东方，绿植增强贵人运'},
                {'item': '木质笔筒', 'position': '左前方', 'reason': '木制品增强木气'},
                {'item': '书籍/文件', 'position': '左侧叠放', 'reason': '增强青龙位高度'}
            ]
        },
        '火': {
            'items': ['红色物品', '台灯', '烧水壶'],
            'colors': ['红色', '紫色', '橙色'],
            'position': '南方或左侧',
            'benefit': '名声、事业、影响力、表现力',
            'specific_suggestions': [
                {'item': '红色台灯', 'position': '左侧', 'reason': '火主名声，增强影响力'},
                {'item': '红色装饰', 'position': '前方', 'reason': '朱雀属火，红色增强气场'}
            ]
        },
        '土': {
            'items': ['陶瓷摆件', '黄色物品', '水晶'],
            'colors': ['黄色', '棕色', '米色'],
            'position': '中央或西南方',
            'benefit': '稳定、包容、财运、人际关系',
            'specific_suggestions': [
                {'item': '陶瓷摆件', 'position': '桌面中央偏右', 'reason': '土主稳定，增强根基'},
                {'item': '黄水晶', 'position': '右前方', 'reason': '黄水晶招财，土生金'}
            ]
        },
        '金': {
            'items': ['金属笔筒', '白色物品', '金属摆件'],
            'colors': ['白色', '金色', '银色'],
            'position': '西方或右侧',
            'benefit': '权威、决断力、领导力、执行力',
            'specific_suggestions': [
                {'item': '金属笔筒', 'position': '右侧', 'reason': '金主权威，增强决断力'},
                {'item': '白色装饰', 'position': '右前方', 'reason': '白色属金，增强气场'}
            ]
        },
        '水': {
            'items': ['水杯', '鱼缸', '水培植物', '蓝色物品'],
            'colors': ['蓝色', '黑色', '深灰色'],
            'position': '北方或前方',
            'benefit': '智慧、财运、人脉、思考能力',
            'specific_suggestions': [
                {'item': '水杯（常保有水）', 'position': '右前方', 'reason': '水主财运，水满则财旺'},
                {'item': '小型鱼缸', 'position': '前方', 'reason': '活水招财，增强财运'},
                {'item': '水培绿萝', 'position': '左前方', 'reason': '水木相生，同时增强木和水'}
            ]
        }
    }
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        初始化规则引擎（支持Redis缓存）
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config or self._get_default_db_config()
        self.rules_cache = None  # 内存缓存
        self.redis_client = None  # Redis客户端（可选）
        
        # 尝试初始化Redis客户端
        if REDIS_AVAILABLE:
            try:
                self.redis_client = get_redis_client()
                if self.redis_client:
                    # 测试连接
                    self.redis_client.ping()
                    logger.info("✅ Redis缓存已启用，规则将缓存到Redis")
                else:
                    logger.warning("⚠️ Redis客户端不可用，将使用内存缓存")
            except Exception as e:
                logger.warning(f"⚠️ Redis连接失败，将使用内存缓存: {e}")
                self.redis_client = None
    
    def _get_default_db_config(self) -> Dict:
        """获取默认数据库配置"""
        try:
            from shared.config.database import MYSQL_CONFIG
            # 确保字符集配置正确
            config = MYSQL_CONFIG.copy()
            config['charset'] = 'utf8mb4'
            config['use_unicode'] = True
            return config
        except Exception:
            return {
                'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'user': os.getenv('MYSQL_USER', 'root'),
                'password': os.getenv('MYSQL_PASSWORD', '123456'),
                'database': os.getenv('MYSQL_DATABASE', 'hifate_bazi'),
                'charset': 'utf8mb4',
                'use_unicode': True
            }
    
    def _get_builtin_rules(self) -> List[Dict]:
        """获取内置风水规则（MySQL不可用时的fallback）- 严格基于文档"""
        return [
            # 青龙位规则
            {
                'rule_code': 'QINGLONG_HEIGHT_001',
                'rule_type': 'position',
                'item_name': 'left_items',
                'item_label': '青龙位物品',
                'ideal_position': {'directions': ['left', 'front_left', 'back_left']},
                'suggestion': '青龙位摆放的东西一定要比右手边更高一些，一切跟办公材料有关的东西，都是放左边最佳，可以叠起来或者竖起来放',
                'priority': 95
            },
            {
                'rule_code': 'QINGLONG_KETTLE_001',
                'rule_type': 'position',
                'item_name': 'kettle',
                'item_label': '养生壶/烧水壶',
                'ideal_position': {'directions': ['left', 'front_left', 'back_left']},
                'suggestion': '✅ 养生壶/烧水壶适合放在青龙位（左侧），符合"动"象原则，有助于提升贵人运',
                'priority': 90
            },
            {
                'rule_code': 'QINGLONG_PLANT_001',
                'rule_type': 'position',
                'item_name': 'plant',
                'item_label': '发财树/绿植',
                'ideal_position': {'directions': ['left', 'front_left', 'back_left']},
                'suggestion': '✅ 发财树/绿植适合放在青龙位（左侧），注意要宽叶植物，不要仙人掌、缠绕性藤类',
                'priority': 88
            },
            # 白虎位规则
            {
                'rule_code': 'BAIHU_LOW_001',
                'rule_type': 'position',
                'item_name': 'right_items',
                'item_label': '白虎位物品',
                'ideal_position': {'directions': ['right', 'front_right', 'back_right']},
                'suggestion': '白虎位摆放的东西整体上比青龙位要低一些，以简单为主。所谓"宁叫青龙高万丈，不叫白虎抬起头"',
                'priority': 95
            },
            {
                'rule_code': 'BAIHU_MOUSE_001',
                'rule_type': 'position',
                'item_name': 'mouse',
                'item_label': '鼠标',
                'ideal_position': {'directions': ['right', 'front_right']},
                'suggestion': '✅ 鼠标放在白虎位（右侧）很合适',
                'priority': 85
            },
            {
                'rule_code': 'BAIHU_CUP_001',
                'rule_type': 'position',
                'item_name': 'cup',
                'item_label': '水杯',
                'ideal_position': {'directions': ['right', 'front_right', 'back_right']},
                'suggestion': '✅ 水杯可以放在白虎位（右侧），但注意不要在右边烧水',
                'priority': 85
            },
            # 白虎位禁忌
            {
                'rule_code': 'BAIHU_KETTLE_TABOO',
                'rule_type': 'taboo',
                'item_name': 'kettle',
                'item_label': '烧水壶',
                'ideal_position': {'directions': ['left', 'front_left', 'back_left']},
                'suggestion': '⚠️ 烧水壶在白虎位（右侧）不合适！建议移至青龙位（左侧），白虎喜静不喜动',
                'priority': 92
            },
            {
                'rule_code': 'BAIHU_PHONE_TABOO',
                'rule_type': 'taboo',
                'item_name': 'phone',
                'item_label': '手机/电话',
                'ideal_position': {'directions': ['left', 'front_left', 'back_left']},
                'suggestion': '⚠️ 手机/电话在白虎位（右侧）不合适！建议移至青龙位（左侧），白虎喜静不喜动',
                'priority': 92
            },
            # 朱雀位规则
            {
                'rule_code': 'ZHUQUE_OPEN_001',
                'rule_type': 'position',
                'item_name': 'front_area',
                'item_label': '朱雀位（前方明堂）',
                'ideal_position': {'directions': ['front', 'center']},
                'suggestion': '朱雀位（前方）应保持开阔明亮，不要有太多遮挡之物。如果前方有同事，收拾得干干净净即可。电脑壁纸可以用广阔高远的意象',
                'priority': 95
            },
            {
                'rule_code': 'ZHUQUE_MONITOR_001',
                'rule_type': 'position',
                'item_name': 'monitor',
                'item_label': '显示器',
                'ideal_position': {'directions': ['front', 'center']},
                'suggestion': '✅ 显示器放在朱雀位（前方中央）符合日常使用习惯，保持屏幕整洁即可',
                'priority': 85
            },
            # 玄武位规则
            {
                'rule_code': 'XUANWU_WALL_001',
                'rule_type': 'position',
                'item_name': 'back_area',
                'item_label': '玄武位（后方靠山）',
                'ideal_position': {'directions': ['back']},
                'suggestion': '💡 玄武位（后方）最好背靠实墙，不要背靠门或落地窗。如无法调整，可在椅背后放褐色/咖啡色靠枕（山形或写着"靠山"），或挂一件衣服，营造"虚拟靠山"',
                'priority': 95
            },
            # 通用建议
            {
                'rule_code': 'GENERAL_TIDY_001',
                'rule_type': 'general',
                'item_name': 'desk',
                'item_label': '办公桌整洁',
                'suggestion': '💡 办公桌可以东西多，但不可乱。财不入乱门，零碎小部件能收纳就收纳',
                'priority': 70
            },
            {
                'rule_code': 'GENERAL_SHARP_001',
                'rule_type': 'taboo',
                'item_name': 'scissors',
                'item_label': '剪刀/尖锐物',
                'suggestion': '⚠️ 利器、剪刀、指甲钳等尖锐物品要收纳起来，不要散放在桌上显眼的地方。放到笔筒里，还可以防小人',
                'priority': 85
            },
            {
                'rule_code': 'GENERAL_CACTUS_001',
                'rule_type': 'taboo',
                'item_name': 'cactus',
                'item_label': '仙人掌/藤类植物',
                'suggestion': '⚠️ 绿植要以宽叶植物为主，不要摆仙人掌、缠绕性的藤类植物',
                'priority': 82
            },
            {
                'rule_code': 'GENERAL_WALLPAPER_001',
                'rule_type': 'general',
                'item_name': 'computer',
                'item_label': '电脑壁纸',
                'suggestion': '💡 电脑屏幕壁纸可以选用视野开阔的风景画或山水图（水是财，山是贵人），有助于提升运势',
                'priority': 68
            },
            # 五行喜神规则
            {
                'rule_code': 'XISHEN_WOOD_001',
                'rule_type': 'element',
                'item_name': 'plant',
                'item_label': '绿植/木制品',
                'related_element': '木',
                'ideal_position': {'directions': ['left', 'front_left', 'back_left']},
                'suggestion': '⭐ 您的喜神为木，建议在青龙位（左侧）摆放绿植（宽叶植物如发财树、富贵竹）或木制品，增强运势',
                'priority': 100,
                'conditions': {'xishen': '木'}
            },
            {
                'rule_code': 'XISHEN_WATER_001',
                'rule_type': 'element',
                'item_name': 'water_item',
                'item_label': '水相关物品',
                'related_element': '水',
                'ideal_position': {'directions': ['front', 'front_right']},
                'suggestion': '⭐ 您的喜神为水，建议在前方或右前方摆放水杯、水瓶、水培植物或鱼缸（如条件允许），增强财运',
                'priority': 100,
                'conditions': {'xishen': '水'}
            }
        ]
    
    def _get_cache_key(self) -> str:
        """生成缓存键"""
        return "desk_fengshui_rules:all"
    
    def _get_rules_from_cache(self) -> Optional[List[Dict]]:
        """从缓存获取规则"""
        cache_key = self._get_cache_key()
        
        # 1. 先检查内存缓存
        if self.rules_cache:
            return self.rules_cache
        
        # 2. 检查Redis缓存
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    rules = json.loads(cached_data)
                    # 回填内存缓存
                    self.rules_cache = rules
                    logger.info(f"✅ 从Redis缓存加载了 {len(rules)} 条规则")
                    return rules
            except Exception as e:
                logger.warning(f"⚠️ Redis缓存读取失败: {e}")
        
        return None
    
    def _save_rules_to_cache(self, rules: List[Dict], ttl: int = 3600):
        """保存规则到缓存"""
        cache_key = self._get_cache_key()
        
        # 1. 保存到内存缓存
        self.rules_cache = rules
        
        # 2. 保存到Redis缓存
        if self.redis_client:
            try:
                rules_json = json.dumps(rules, ensure_ascii=False)
                self.redis_client.setex(cache_key, ttl, rules_json)
                logger.info(f"✅ 规则已缓存到Redis（TTL: {ttl}秒）")
            except Exception as e:
                logger.warning(f"⚠️ Redis缓存写入失败: {e}")
    
    def load_rules(self, force_reload: bool = False) -> List[Dict]:
        """
        加载风水规则（支持Redis缓存）
        
        Args:
            force_reload: 是否强制重新加载
        
        Returns:
            规则列表
        """
        # 如果不强制重新加载，先尝试从缓存获取
        if not force_reload:
            cached_rules = self._get_rules_from_cache()
            if cached_rules:
                return cached_rules
        
        try:
            import pymysql
            
            # 使用连接池（必须）
            from shared.config.database import get_mysql_connection, return_mysql_connection
            conn = get_mysql_connection()
            use_pool = True
            
            # 设置连接字符集（双重保险）
            conn.set_charset('utf8mb4')
            # 执行SET NAMES确保会话级别字符集
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            # 🔴 关键修复：使用 CAST AS BINARY 获取原始字节，绕过 pymysql 的字符集转换
            # 这样可以获取数据库中实际存储的字节，然后手动 UTF-8 解码
            sql = """
                SELECT 
                    id, rule_code, rule_type, item_name, 
                    CAST(item_label AS BINARY) as item_label_bytes,
                    CAST(reason AS BINARY) as reason_bytes,
                    CAST(suggestion AS BINARY) as suggestion_bytes,
                    ideal_position, priority, related_element, 
                    conditions, enabled, created_at, updated_at
                FROM desk_fengshui_rules 
                WHERE enabled = 1 
                ORDER BY priority DESC, rule_code
            """
            
            cursor.execute(sql)
            rules_raw = cursor.fetchall()
            
            # 手动解码字节字段，处理双重编码问题
            rules = []
            for rule in rules_raw:
                # 解码字节字段
                item_label_bytes = rule.get('item_label_bytes')
                reason_bytes = rule.get('reason_bytes')
                suggestion_bytes = rule.get('suggestion_bytes')
                
                # 解码函数：处理双重编码问题
                def decode_text_field(byte_data):
                    """
                    修复双重编码问题
                    
                    问题：数据库中存储的文本可能是双重编码的：
                    1. 原始中文 -> UTF-8 编码 -> 字节1
                    2. 字节1 被当作 latin1 字符串 -> 再次 UTF-8 编码 -> 字节2
                    3. 字节2 存储在数据库中
                    
                    修复流程：
                    1. 字节2 -> UTF-8 解码 -> 得到 latin1 字符串（字节1的文本表示）
                    2. latin1 字符串 -> latin1 编码回字节 -> 得到字节1
                    3. 字节1 -> UTF-8 解码 -> 得到正确的中文
                    """
                    if not byte_data:
                        return ''
                    if isinstance(byte_data, bytes):
                        try:
                            # 第一步：UTF-8 解码（得到 latin1 字符串）
                            first_decode = byte_data.decode('utf-8')
                            
                            # 检查是否已经包含中文（说明不是双重编码）
                            if any('\u4e00' <= c <= '\u9fff' for c in first_decode):
                                return first_decode
                            
                            try:
                                re_encoded1 = DeskFengshuiEngine._encode_mysql_latin1(first_decode)
                                second_decode = re_encoded1.decode('utf-8')
                                if any('\u4e00' <= c <= '\u9fff' for c in second_decode):
                                    return second_decode
                                try:
                                    re_encoded2 = DeskFengshuiEngine._encode_mysql_latin1(second_decode)
                                    third_decode = re_encoded2.decode('utf-8')
                                    if any('\u4e00' <= c <= '\u9fff' for c in third_decode):
                                        return third_decode
                                except (UnicodeEncodeError, UnicodeDecodeError):
                                    pass
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                pass
                            
                            # 如果修复失败，返回第一次解码的结果
                            return first_decode
                        except UnicodeDecodeError:
                            # UTF-8 解码失败，尝试 latin1
                            try:
                                return byte_data.decode('latin1')
                            except Exception:
                                return byte_data.decode('utf-8', errors='ignore')
                    else:
                        # 如果不是字节，直接使用 _safe_decode
                        return self._safe_decode(str(byte_data))
                
                # 解码各个字段
                rule['item_label'] = decode_text_field(item_label_bytes)
                rule['reason'] = decode_text_field(reason_bytes)
                rule['suggestion'] = decode_text_field(suggestion_bytes)
                
                # 移除临时字节字段
                rule.pop('item_label_bytes', None)
                rule.pop('reason_bytes', None)
                rule.pop('suggestion_bytes', None)
                
                rules.append(rule)
                
                if rule.get('ideal_position') and isinstance(rule['ideal_position'], str):
                    try:
                        rule['ideal_position'] = json.loads(rule['ideal_position'])
                    except Exception:
                        pass
                
                if rule.get('conditions') and isinstance(rule['conditions'], str):
                    try:
                        rule['conditions'] = json.loads(rule['conditions'])
                    except Exception:
                        pass
            
            cursor.close()
            
            # 返回连接到连接池
            return_mysql_connection(conn)
            
            # 保存到缓存
            self._save_rules_to_cache(rules, ttl=3600)  # 缓存1小时
            logger.info(f"加载了 {len(rules)} 条风水规则")
            
            return rules
            
        except Exception as e:
            logger.error(f"加载规则失败: {e}")
            logger.warning("⚠️ 使用内置规则作为fallback")
            # 使用内置规则作为fallback
            return self._get_builtin_rules()
    
    def analyze_item_fengshui(self, item: Dict, bazi_info: Optional[Dict] = None) -> Dict:
        """
        为单个物品进行详细的风水分析
        
        Args:
            item: 检测到的物品（含位置信息）
            bazi_info: 八字信息（含喜神忌神）
        
        Returns:
            物品的详细风水分析
        """
        if not item:
            return {
                'name': '',
                'label': '未知物品',
                'current_position': '',
                'is_position_ideal': True,
                'analysis': {},
                'suggestion': None
            }
        
        item_name = item.get('name', '') or ''
        item_label = item.get('label', item_name) or item_name
        current_position = item.get('position') or {}
        current_relative = current_position.get('relative', '') if current_position else ''
        current_direction = current_position.get('direction', '') if current_position else ''
        
        # 获取物品配置
        config = self.ITEM_FENGSHUI_CONFIG.get(item_name, {})
        
        if not config:
            # 未配置的物品，使用通用分析
            return {
                'name': item_name,
                'label': item_label,
                'current_position': current_position.get('relative_name', current_relative),
                'is_position_ideal': True,  # 未配置则认为位置可以
                'analysis': {
                    'current_assessment': f'{item_label}位于{current_position.get("relative_name", "当前位置")}',
                    'ideal_positions': [],
                    'avoid_positions': [],
                    'fengshui_element': '',
                    'bazi_relevance': ''
                },
                'suggestion': None
            }
        
        # 分析位置是否理想
        ideal_positions = config.get('ideal_positions', [])
        avoid_positions = config.get('avoid_positions', [])
        position_reasons = config.get('position_reasons', {})
        
        # 判断当前位置
        is_in_ideal = current_relative in ideal_positions or current_direction in ideal_positions
        is_in_avoid = current_relative in avoid_positions or current_direction in avoid_positions
        
        # 获取当前位置的评估
        current_assessment = position_reasons.get(current_relative, '')
        if not current_assessment:
            current_assessment = position_reasons.get(current_direction, '')
        if not current_assessment:
            if is_in_ideal:
                current_assessment = f'{item_label}位于{current_position.get("relative_name", current_relative)}，位置合适'
            elif is_in_avoid:
                current_assessment = f'⚠️ {item_label}位于{current_position.get("relative_name", current_relative)}，建议调整位置'
            else:
                current_assessment = f'{item_label}位于{current_position.get("relative_name", current_relative)}'
        
        # 八字相关性分析
        bazi_relevance = ''
        item_element = config.get('element', '')
        if bazi_info and item_element:
            xishen = bazi_info.get('xishen', '')
            jishen = bazi_info.get('jishen', '')
            
            if item_element == xishen:
                bazi_relevance = f'🌟 您的喜神为{xishen}，{item_label}属{item_element}，与您八字相合，有助增强运势'
            elif item_element == jishen:
                bazi_relevance = f'⚠️ 您的忌神为{jishen}，{item_label}属{item_element}，建议减少或调整位置'
        
        # 生成建议
        suggestion = None
        if is_in_avoid:
            ideal_pos_name = self._get_direction_name(ideal_positions[0]) if ideal_positions else '其他位置'
            suggestion = {
                'action': 'move',
                'from': current_position.get('relative_name', current_relative),
                'to': ideal_pos_name,
                'reason': current_assessment,
                'priority': 'high'
            }
        elif not is_in_ideal and ideal_positions:
            # 不在理想位置，但也不在禁忌位置
            ideal_pos_name = self._get_direction_name(ideal_positions[0])
            suggestion = {
                'action': 'optimize',
                'from': current_position.get('relative_name', current_relative),
                'to': ideal_pos_name,
                'reason': f'建议将{item_label}移至{ideal_pos_name}效果更佳',
                'priority': 'medium'
            }
        
        return {
            'name': item_name,
            'label': config.get('label', item_label),
            'current_position': current_position.get('relative_name', current_relative),
            'is_position_ideal': is_in_ideal and not is_in_avoid,
            'is_position_avoid': is_in_avoid,
            'analysis': {
                'current_assessment': current_assessment,
                'ideal_positions': [self._get_direction_name(p) for p in ideal_positions],
                'avoid_positions': [self._get_direction_name(p) for p in avoid_positions],
                'fengshui_element': item_element,
                'fengshui_benefit': config.get('fengshui_benefit', ''),
                'tips': config.get('tips', ''),
                'bazi_relevance': bazi_relevance
            },
            'suggestion': suggestion
        }
    
    def analyze_all_items(self, detected_items: List[Dict], bazi_info: Optional[Dict] = None) -> List[Dict]:
        """
        分析所有检测到的物品
        
        Args:
            detected_items: 检测到的物品列表
            bazi_info: 八字信息
        
        Returns:
            所有物品的详细分析列表
        """
        analyzed_items = []
        # 🔴 防御性检查：确保 detected_items 不为 None
        if not detected_items:
            detected_items = []
        
        for item in detected_items:
            if not item:
                continue
            analysis = self.analyze_item_fengshui(item, bazi_info)
            # 🔴 防御性检查：确保 analysis 不为 None 且是字典
            if analysis and isinstance(analysis, dict):
                analyzed_items.append(analysis)
            else:
                logger.warning(f"物品分析返回了无效结果，跳过: {type(analysis)}")
        return analyzed_items
    
    def generate_recommendations(self, detected_items: List[Dict], bazi_info: Optional[Dict] = None) -> Dict:
        """
        生成三级建议体系
        
        Args:
            detected_items: 检测到的物品列表
            bazi_info: 八字信息（含喜神忌神）
        
        Returns:
            三级建议结构：must_adjust, should_add, optional_optimize
        """
        recommendations = {
            'must_adjust': [],  # 必须调整（违反禁忌）
            'should_add': [],   # 建议添加（基于八字喜神）
            'optional_optimize': []  # 可选优化
        }
        
        # 确保 detected_items 不为 None
        if not detected_items:
            detected_items = []
        
        # 1. 分析每个物品，找出必须调整的（违反禁忌）
        for item in detected_items:
            if not item:
                continue
            analysis = self.analyze_item_fengshui(item, bazi_info)
            # 🔴 防御性检查：确保 analysis 不为 None 且是字典
            if not analysis or not isinstance(analysis, dict):
                logger.warning(f"物品分析返回了无效结果: {type(analysis)}")
                continue
            if analysis.get('is_position_avoid'):
                # 必须调整
                suggestion = analysis.get('suggestion') or {}
                # 🔴 防御性检查：确保 suggestion 是字典类型
                if suggestion and isinstance(suggestion, dict):
                    item_name = item.get('name', '') if item else ''
                    analysis_data = analysis.get('analysis') or {}
                    # 🔴 防御性检查：确保 analysis_data 是字典类型
                    if not isinstance(analysis_data, dict):
                        analysis_data = {}
                    recommendations['must_adjust'].append({
                        'item': analysis.get('label', item_name),
                        'action': suggestion.get('action', 'move'),
                        'from': suggestion.get('from', '当前位置'),
                        'to': suggestion.get('to', '其他位置'),
                        'reason': suggestion.get('reason', '违反风水禁忌'),
                        'priority': 'high',
                        'fengshui_element': analysis_data.get('fengshui_element', '')
                    })
            elif not analysis.get('is_position_ideal') and analysis.get('suggestion'):
                # 可选优化
                suggestion = analysis.get('suggestion') or {}
                # 🔴 防御性检查：确保 suggestion 是字典类型
                if suggestion and isinstance(suggestion, dict):
                    item_name = item.get('name', '') if item else ''
                    recommendations['optional_optimize'].append({
                        'item': analysis.get('label', item_name),
                        'action': suggestion.get('action', 'optimize'),
                        'from': suggestion.get('from', '当前位置'),
                        'to': suggestion.get('to', '更佳位置'),
                        'reason': suggestion.get('reason', '位置可优化'),
                        'priority': 'low'
                    })
        
        # 2. 基于四象布局检测缺失物品
        detected_item_names = [(item.get('name', '') or '').lower() for item in detected_items if item]
        detected_positions = {}
        for item in detected_items:
            if not item:
                continue
            pos = item.get('position') or {}
            relative = pos.get('relative', '') if pos else ''
            if relative not in detected_positions:
                detected_positions[relative] = []
            detected_positions[relative].append(item.get('name', '') or '')
        
        # 检查青龙位（左侧）是否有高物/绿植
        left_items = detected_positions.get('left', []) + detected_positions.get('front_left', []) + detected_positions.get('back_left', [])
        has_left_plant = any(item in ['plant', 'potted plant', 'vase'] for item in left_items)
        has_left_high_item = any(item in ['book', 'file', 'plant', 'potted plant'] for item in left_items)
        
        if not has_left_plant:
            recommendations['should_add'].append({
                'item': '绿植（发财树/富贵竹）',
                'position': '左侧（青龙位）',
                'reason': '青龙位宜高宜动，绿植可增强贵人运和生机',
                'priority': 'high',
                'fengshui_element': '木'
            })
        
        if not has_left_high_item and not has_left_plant:
            recommendations['optional_optimize'].append({
                'item': '书籍/文件架',
                'position': '左侧叠放',
                'reason': '增强青龙位高度，有助提升事业运',
                'priority': 'medium'
            })
        
        # 检查玄武位（后方）是否有靠山
        back_items = detected_positions.get('back', []) + detected_positions.get('back_left', []) + detected_positions.get('back_right', [])
        has_back_support = len(back_items) > 0
        
        if not has_back_support:
            recommendations['optional_optimize'].append({
                'item': '靠垫/背靠物品',
                'position': '后方（玄武位）',
                'reason': '增强靠山运，工作有依靠',
                'priority': 'medium'
            })
        
        # 3. 基于八字喜神推荐物品
        if bazi_info:
            xishen = bazi_info.get('xishen', '')
            jishen = bazi_info.get('jishen', '')
            
            if xishen and xishen in self.WUXING_RECOMMENDATIONS:
                wuxing_rec = self.WUXING_RECOMMENDATIONS.get(xishen, {})
                # 🔴 防御性检查：确保 wuxing_rec 不为 None 且是字典类型
                if not wuxing_rec or not isinstance(wuxing_rec, dict):
                    logger.warning(f"WUXING_RECOMMENDATIONS[{xishen}] 返回了无效值: {type(wuxing_rec)}")
                    wuxing_rec = {}
                
                # 检查是否已有喜神对应物品
                xishen_items = self.ELEMENT_ITEMS.get(xishen, [])
                has_xishen_item = any(item in detected_item_names for item in xishen_items)
                
                if not has_xishen_item:
                    # 推荐喜神物品
                    specific_suggestions = wuxing_rec.get('specific_suggestions', [])
                    # 🔴 防御性检查：确保 specific_suggestions 是列表
                    if not isinstance(specific_suggestions, list):
                        specific_suggestions = []
                    
                    for suggestion in specific_suggestions[:2]:
                        # 🔴 防御性检查：确保 suggestion 不为 None 且是字典类型
                        if not suggestion or not isinstance(suggestion, dict):
                            logger.warning(f"建议项不是字典类型: {type(suggestion)}")
                            continue
                        
                        recommendations['should_add'].append({
                            'item': suggestion.get('item', ''),
                            'position': suggestion.get('position', wuxing_rec.get('position', '')),
                            'reason': f"🌟 您的喜神为{xishen}，{suggestion.get('reason', '')}",
                            'priority': 'high',
                            'fengshui_element': xishen,
                            'bazi_based': True
                        })
            
            # 检查是否有忌神物品需要调整
            if jishen and jishen in self.ELEMENT_ITEMS:
                jishen_items = self.ELEMENT_ITEMS[jishen]
                for item in detected_items:
                    if not item:
                        continue
                    item_name = (item.get('name', '') or '').lower()
                    if item_name in jishen_items:
                        # 🔴 防御性检查：避免链式调用导致 None 错误
                        config = self.ITEM_FENGSHUI_CONFIG.get(item_name, {})
                        label = config.get('label', item_name) if config and isinstance(config, dict) else item_name
                        # 检查是否已在must_adjust中
                        already_in_must = any(adj.get('item') == label for adj in recommendations['must_adjust'])
                        if not already_in_must:
                            recommendations['optional_optimize'].append({
                                'item': label,
                                'action': 'reduce_or_move',
                                'reason': f"⚠️ 您的忌神为{jishen}，{label}属{jishen}，建议减少外露或收纳起来",
                                'priority': 'medium',
                                'fengshui_element': jishen,
                                'bazi_based': True
                            })
        
        # 4. 检查是否有利器外露
        sharp_items = ['scissors', 'knife', 'letter opener']
        for item in detected_items:
            if not item:
                continue
            item_name = (item.get('name', '') or '').lower()
            if item_name in sharp_items:
                pos = item.get('position') or {}
                relative = pos.get('relative', '') if pos else ''
                if relative not in ['drawer', 'pen_holder']:
                    # 🔴 防御性检查：避免链式调用导致 None 错误
                    config = self.ITEM_FENGSHUI_CONFIG.get(item_name, {})
                    item_label = config.get('label', item_name) if config and isinstance(config, dict) else item_name
                    
                    recommendations['must_adjust'].append({
                        'item': item_label,
                        'action': 'store',
                        'from': pos.get('relative_name', '桌面') if pos else '桌面',
                        'to': '抽屉或笔筒内',
                        'reason': '利器外露易招惹是非和小人，建议收纳',
                        'priority': 'high'
                    })
        
        # 5. 通用建议（如果没有其他建议）
        if not recommendations['should_add'] and not recommendations['must_adjust']:
            recommendations['optional_optimize'].append({
                'item': '水杯（常保有水）',
                'position': '右前方',
                'reason': '水主财运，水杯保持有水象征财源不断',
                'priority': 'low'
            })
        
        # 添加统计信息
        recommendations['statistics'] = {
            'must_adjust_count': len(recommendations['must_adjust']),
            'should_add_count': len(recommendations['should_add']),
            'optional_optimize_count': len(recommendations['optional_optimize']),
            'total_count': len(recommendations['must_adjust']) + len(recommendations['should_add']) + len(recommendations['optional_optimize'])
        }
        
        return recommendations
    
    def generate_bazi_analysis(self, detected_items: List[Dict], bazi_info: Optional[Dict] = None) -> Dict:
        """
        生成深度八字融合分析
        
        Args:
            detected_items: 检测到的物品列表
            bazi_info: 八字信息
        
        Returns:
            八字深度融合分析结果
        """
        if not bazi_info:
            return {
                'has_bazi': False,
                'message': '未提供八字信息，无法进行个性化分析'
            }
        
        xishen = bazi_info.get('xishen', '')
        jishen = bazi_info.get('jishen', '')
        
        analysis = {
            'has_bazi': True,
            'xishen': xishen,
            'jishen': jishen,
            'xishen_analysis': {},
            'jishen_analysis': {},
            'element_balance': {},
            'personalized_tips': [],
            'color_recommendations': [],
            'overall_compatibility': 0
        }
        
        # 统计桌面五行分布
        element_counts = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
        
        # 确保 detected_items 不为 None
        if not detected_items:
            detected_items = []
        
        for item in detected_items:
            if not item:
                continue
            item_name = (item.get('name', '') or '').lower()
            for element, items in self.ELEMENT_ITEMS.items():
                if item_name in items:
                    element_counts[element] += 1
                    break
            # 也从配置中查找
            config = self.ITEM_FENGSHUI_CONFIG.get(item_name, {})
            # 🔴 防御性检查：确保 config 不为 None 且是字典类型
            if config and isinstance(config, dict) and config.get('element'):
                element_counts[config['element']] += 1
        
        analysis['element_balance'] = element_counts
        
        # 喜神分析
        if xishen:
            xishen_count = element_counts.get(xishen, 0)
            xishen_rec = self.WUXING_RECOMMENDATIONS.get(xishen, {})
            
            # 🔴 防御性检查：确保 xishen_rec 不为 None 且是字典类型
            if not xishen_rec or not isinstance(xishen_rec, dict):
                logger.warning(f"WUXING_RECOMMENDATIONS[{xishen}] 返回了无效值: {type(xishen_rec)}")
                xishen_rec = {}
            
            if xishen_count >= 2:
                status = 'excellent'
                message = f'🌟 您的喜神为{xishen}，桌面{xishen}元素充足（{xishen_count}个），运势加成明显'
            elif xishen_count == 1:
                status = 'good'
                message = f'✅ 您的喜神为{xishen}，桌面有{xishen_count}个{xishen}元素，建议适当增加'
            else:
                status = 'weak'
                message = f'⚠️ 您的喜神为{xishen}，桌面缺少{xishen}元素，建议添加相关物品'
            
            analysis['xishen_analysis'] = {
                'element': xishen,
                'count': xishen_count,
                'status': status,
                'message': message,
                'benefit': xishen_rec.get('benefit', ''),
                'recommended_items': xishen_rec.get('items', []),
                'recommended_colors': xishen_rec.get('colors', []),
                'recommended_position': xishen_rec.get('position', '')
            }
            
            # 喜神对应的颜色推荐
            colors_list = xishen_rec.get('colors', [])
            # 🔴 防御性检查：确保 colors_list 是列表类型
            if not isinstance(colors_list, list):
                colors_list = []
            for color in colors_list:
                analysis['color_recommendations'].append({
                    'color': color,
                    'reason': f'{color}属{xishen}，与您的喜神相合',
                    'usage': f'可用于桌面装饰、文件夹、鼠标垫等',
                    'priority': 'high'
                })
        
        # 忌神分析
        if jishen:
            jishen_count = element_counts.get(jishen, 0)
            jishen_items_on_desk = []
            
            for item in detected_items:
                if not item:
                    continue
                item_name = (item.get('name', '') or '').lower()
                config = self.ITEM_FENGSHUI_CONFIG.get(item_name, {})
                # 🔴 防御性检查：确保 config 不为 None 且是字典类型
                if config and isinstance(config, dict) and config.get('element') == jishen:
                    jishen_items_on_desk.append(config.get('label', item_name))
            
            if jishen_count == 0:
                status = 'excellent'
                message = f'✅ 您的忌神为{jishen}，桌面没有{jishen}元素物品，很好'
            elif jishen_count == 1:
                status = 'caution'
                message = f'⚠️ 您的忌神为{jishen}，桌面有{jishen_count}个{jishen}元素物品（{", ".join(jishen_items_on_desk)}），建议减少外露'
            else:
                status = 'warning'
                message = f'❌ 您的忌神为{jishen}，桌面{jishen}元素过多（{jishen_count}个），建议收纳或移除部分物品'
            
            analysis['jishen_analysis'] = {
                'element': jishen,
                'count': jishen_count,
                'status': status,
                'message': message,
                'items_on_desk': jishen_items_on_desk,
                'suggestion': f'建议将{jishen}元素物品收纳起来或减少摆放' if jishen_count > 0 else ''
            }
        
        # 计算整体相容度
        compatibility_score = 50  # 基础分
        
        # 喜神加分
        xishen_count = element_counts.get(xishen, 0) if xishen else 0
        compatibility_score += min(xishen_count * 15, 30)  # 最多加30分
        
        # 忌神减分
        jishen_count = element_counts.get(jishen, 0) if jishen else 0
        compatibility_score -= min(jishen_count * 10, 20)  # 最多减20分
        
        # 五行平衡加分
        non_zero_elements = sum(1 for count in element_counts.values() if count > 0)
        if non_zero_elements >= 3:
            compatibility_score += 10
        
        analysis['overall_compatibility'] = max(0, min(100, compatibility_score))
        
        # 个性化建议
        if xishen:
            xishen_rec = self.WUXING_RECOMMENDATIONS.get(xishen, {})
            # 🔴 防御性检查：确保 xishen_rec 不为 None 且是字典类型
            if not xishen_rec or not isinstance(xishen_rec, dict):
                xishen_rec = {}
            
            items_list = xishen_rec.get('items', [])
            # 🔴 防御性检查：确保 items_list 是列表类型
            if not isinstance(items_list, list):
                items_list = []
            
            analysis['personalized_tips'].append({
                'type': 'xishen_enhance',
                'title': f'增强{xishen}元素',
                'tip': f"您的喜神为{xishen}，可增加{xishen_rec.get('position', '')}的相关物品：{', '.join(items_list[:3])}",
                'priority': 'high'
            })
        
        if jishen and element_counts.get(jishen, 0) > 0:
            analysis['personalized_tips'].append({
                'type': 'jishen_reduce',
                'title': f'减少{jishen}元素',
                'tip': f"您的忌神为{jishen}，建议减少或收纳桌面上的{jishen}元素物品",
                'priority': 'high'
            })
        
        # 五行相生建议
        wuxing_sheng = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
        if xishen:
            sheng_element = wuxing_sheng.get(xishen, '')
            if sheng_element:
                analysis['personalized_tips'].append({
                    'type': 'wuxing_sheng',
                    'title': f'五行相生：{xishen}生{sheng_element}',
                    'tip': f"{xishen}生{sheng_element}，可同时摆放{xishen}和{sheng_element}元素物品，形成相生局",
                    'priority': 'medium'
                })
        
        return analysis
    
    def match_rules(self, detected_items: List[Dict], bazi_info: Optional[Dict] = None) -> Dict:
        """
        匹配规则并生成建议
        
        Args:
            detected_items: 检测到的物品列表（含位置信息）
            bazi_info: 八字信息（含喜神忌神）
        
        Returns:
            匹配结果和建议
        """
        try:
            # 1. 加载规则
            rules = self.load_rules()
            
            # 2. 匹配基础规则
            adjustments = self._match_basic_rules(detected_items, rules)
            
            # 3. 匹配忌讳规则
            removals = self._match_taboo_rules(detected_items, rules)
            
            # 4. 基于喜神生成增加建议（即使没有八字信息也生成通用建议）
            additions = []
            additions = self._generate_additions(detected_items, bazi_info, rules)
            
            # 5. 计算评分
            score = self._calculate_score(detected_items, adjustments, additions, removals)
            
            # 6. 生成总结
            summary = self._generate_summary(detected_items, adjustments, additions, removals, score)
            
            # 按规则类型分类建议
            categorized_additions = self._categorize_suggestions(additions)
            
            return {
                'success': True,
                'adjustments': adjustments,
                'additions': additions,
                'removals': removals,
                'categorized_additions': categorized_additions,  # 新增：分类建议
                'score': score,
                'summary': summary,
                'statistics': {  # 新增：统计数据
                    'total_items': len(detected_items),
                    'adjustments_count': len(adjustments),
                    'additions_count': len(additions),
                    'removals_count': len(removals),
                    'categories_count': len(categorized_additions)
                }
            }
            
        except Exception as e:
            logger.error(f"规则匹配失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'adjustments': [],
                'additions': [],
                'removals': [],
                'score': 0,
                'summary': '规则匹配失败'
            }
    
    def _match_basic_rules(self, detected_items: List[Dict], rules: List[Dict]) -> List[Dict]:
        """匹配基础规则，检查物品位置是否合理"""
        adjustments = []
        
        for item in detected_items:
            item_name = item['name']
            item_label = item.get('label', item_name)
            current_position = item.get('position', {})
            current_relative = current_position.get('relative', '')
            current_direction = current_position.get('direction', '')
            
            # 查找该物品的规则（支持所有规则类型）
            for rule in rules:
                if rule['rule_type'] not in ['position', 'basic', 'taboo', 'wealth', 'career', 'love', 'protection', 'health', 'study', 'relationship', 'general']:
                    continue
                
                # 匹配物品名称
                rule_item_name = rule.get('item_name', '')
                if rule_item_name != item_name:
                    continue
                
                # 获取理想位置
                ideal_pos = rule.get('ideal_position', {})
                # 🔴 防御性检查：确保 ideal_pos 不为 None
                if not ideal_pos:
                    ideal_pos = {}
                if isinstance(ideal_pos, str):
                    try:
                        ideal_pos = json.loads(ideal_pos)
                    except Exception:
                        ideal_pos = {}
                if not isinstance(ideal_pos, dict):
                    continue
                
                ideal_directions = ideal_pos.get('directions', [])
                if isinstance(ideal_directions, str):
                    ideal_directions = [ideal_directions]
                
                # 检查当前位置是否在理想位置列表中
                is_in_ideal = False
                if current_relative in ideal_directions or current_direction in ideal_directions:
                    is_in_ideal = True
                
                # 如果是taboo规则且当前位置在禁止区域
                if rule['rule_type'] == 'taboo' and not is_in_ideal:
                    adjustments.append({
                        'item': item_label,
                        'item_label': item_label,
                        'current_position': current_position.get('relative_name', current_relative),
                        'ideal_position': self._get_direction_name(ideal_directions[0] if ideal_directions else 'left'),
                        'reason': self._safe_decode(rule.get('reason', '')),
                        'suggestion': self._safe_decode(rule.get('suggestion', '')),
                        'priority': 'high' if rule.get('priority', 5) >= 90 else 'medium',
                        'action': 'move',
                        'element': rule.get('related_element', '')
                    })
                    break
                # 如果是position规则或新规则类型且位置不匹配
                elif rule['rule_type'] in ['position', 'wealth', 'career', 'love', 'protection', 'health', 'study', 'relationship'] and not is_in_ideal and ideal_directions:
                    adjustments.append({
                        'item': item_label,
                        'item_label': item_label,
                        'current_position': current_position.get('relative_name', current_relative),
                        'ideal_position': self._get_direction_name(ideal_directions[0]),
                        'reason': self._safe_decode(rule.get('reason', '')),
                        'suggestion': self._safe_decode(rule.get('suggestion', '')),
                        'priority': 'high' if rule.get('priority', 5) >= 90 else 'medium',
                        'action': 'move',
                        'element': rule.get('related_element', '')
                    })
                    break
        
        return adjustments
    
    def _match_taboo_rules(self, detected_items: List[Dict], rules: List[Dict]) -> List[Dict]:
        """匹配忌讳规则，检查是否有不宜摆放的物品"""
        removals = []
        
        for item in detected_items:
            item_name = item['name']
            current_position = item.get('position', {})
            
            # 查找忌讳规则
            for rule in rules:
                if rule['rule_type'] != 'taboo':
                    continue
                
                if rule['item_name'] == item_name:
                    ideal_pos = rule.get('ideal_position', {})
                    # 🔴 防御性检查：确保 ideal_pos 不为 None
                    if not ideal_pos:
                        ideal_pos = {}
                    if isinstance(ideal_pos, str):
                        try:
                            ideal_pos = json.loads(ideal_pos)
                        except Exception:
                            ideal_pos = {}
                    avoid_direction = ideal_pos.get('direction', '') if isinstance(ideal_pos, dict) else ''
                    
                    # 检查是否在禁止区域
                    if 'avoid' in avoid_direction.lower():
                        removals.append({
                            'item': item['label'],
                            'item_label': item['label'],
                            'current_position': current_position.get('relative_name', ''),
                            'reason': rule.get('reason', ''),
                            'priority': 'high',
                            'action': 'remove',
                            'suggestion': rule.get('suggestion', '')
                        })
                        break
        
        return removals
    
    def _generate_additions(self, detected_items: List[Dict], bazi_info: Optional[Dict], rules: List[Dict]) -> List[Dict]:
        """基于规则和喜神生成增加建议"""
        additions = []
        xishen = bazi_info.get('xishen') if bazi_info else None
        
        # 检查已检测到的物品类型
        detected_item_names = {item['name'] for item in detected_items}
        # 🔴 防御性检查：避免链式调用导致 None 错误
        detected_left_items = []
        detected_right_items = []
        for item in detected_items:
            if not item:
                continue
            position = item.get('position') or {}
            if isinstance(position, dict):
                relative = position.get('relative', '')
                if relative in ['left', 'front_left', 'back_left']:
                    detected_left_items.append(item)
                elif relative in ['right', 'front_right', 'back_right']:
                    detected_right_items.append(item)
        
        # 1. 基于规则的增加建议（检查缺失的重要物品）
        for rule in rules:
            if rule['rule_type'] not in ['position', 'element', 'general', 'wealth', 'career', 'love', 'protection', 'health', 'study', 'relationship']:
                continue
            
            rule_item_name = rule.get('item_name', '')
            rule_item_label = self._safe_decode(rule.get('item_label', ''))
            
            # 跳过位置规则（不是物品）
            if rule_item_name in ['left_items', 'right_items', 'front_area', 'back_area', 'desk', 'computer']:
                continue
            
            # 检查是否已有该物品
            has_item = rule_item_name in detected_item_names
            
            # 如果是喜神相关规则，优先推荐（强制显示，即使已有类似物品）
            if xishen and rule.get('related_element') and rule.get('related_element') == xishen:
                ideal_pos = rule.get('ideal_position', {})
                # 🔴 防御性检查：确保 ideal_pos 不为 None
                if not ideal_pos:
                    ideal_pos = {}
                if isinstance(ideal_pos, str):
                    try:
                        ideal_pos = json.loads(ideal_pos)
                    except Exception:
                        ideal_pos = {}
                ideal_directions = ideal_pos.get('directions', []) if isinstance(ideal_pos, dict) else []
                if isinstance(ideal_directions, str):
                    ideal_directions = [ideal_directions]
                
                position_name = self._get_direction_name(ideal_directions[0]) if ideal_directions else '合适位置'
                suggestion = self._safe_decode(rule.get('suggestion', ''))
                
                # 强制添加⭐标记和强调
                if '⭐' not in suggestion and '🌟' not in suggestion:
                    suggestion = f"🌟【喜神{xishen}专属推荐】{suggestion}"
                elif '⭐' in suggestion:
                    suggestion = suggestion.replace('⭐', '🌟【喜神专属】')
                
                additions.append({
                    'item': rule_item_name,
                    'item_label': rule_item_label,
                    'position': position_name,
                    'reason': suggestion,
                    'suggestion': suggestion,
                    'priority': 'high',
                    'action': 'add',
                    'element': xishen,
                    'rule_type': rule.get('rule_type', 'element'),  # 添加规则类型
                    'is_xishen': True  # 标记为喜神建议
                })
                continue
            
            # 通用物品建议（基于规则）- 支持所有新规则类型
            if rule['rule_type'] in ['position', 'wealth', 'career', 'love', 'protection', 'health', 'study', 'relationship', 'general'] and not has_item:
                # 检查是否应该推荐（基于位置和规则优先级）
                ideal_pos = rule.get('ideal_position', {})
                # 🔴 防御性检查：确保 ideal_pos 不为 None
                if not ideal_pos:
                    ideal_pos = {}
                if isinstance(ideal_pos, str):
                    try:
                        ideal_pos = json.loads(ideal_pos)
                    except Exception:
                        ideal_pos = {}
                ideal_directions = ideal_pos.get('directions', []) if isinstance(ideal_pos, dict) else []
                if isinstance(ideal_directions, str):
                    ideal_directions = [ideal_directions]
                
                # 对于爆点规则（wealth, career, love等），优先推荐
                is_highlight_rule = rule['rule_type'] in ['wealth', 'career', 'love', 'protection']
                priority = 'high' if is_highlight_rule else 'medium'
                
                # 确定推荐位置
                if ideal_directions:
                    position_name = self._get_direction_name(ideal_directions[0])
                else:
                    # 根据规则类型默认位置
                    if rule['rule_type'] == 'wealth':
                        position_name = '左侧（青龙位）或前方'
                    elif rule['rule_type'] == 'career':
                        position_name = '左侧（青龙位）'
                    elif rule['rule_type'] == 'love':
                        position_name = '前方（朱雀位）'
                    else:
                        position_name = '合适位置'
                
                suggestion = self._safe_decode(rule.get('suggestion', ''))
                if not suggestion:
                    suggestion = self._safe_decode(rule.get('reason', ''))
                
                # 确保建议有表情符号前缀
                if not any(suggestion.startswith(emoji) for emoji in ['💰', '📈', '💕', '🛡️', '🏥', '📚', '🤝', '💡', '✅', '⭐', '🌟']):
                    emoji_map = {
                        'wealth': '💰',
                        'career': '📈',
                        'love': '💕',
                        'protection': '🛡️',
                        'health': '🏥',
                        'study': '📚',
                        'relationship': '🤝',
                        'general': '💡'
                    }
                    emoji = emoji_map.get(rule['rule_type'], '💡')
                    suggestion = f"{emoji} {suggestion}"
                
                # 对于爆点规则，无条件推荐（不限制位置条件）
                # 对于普通规则，根据位置条件推荐
                should_recommend = False
                if is_highlight_rule:
                    # 爆点规则无条件推荐
                    should_recommend = True
                elif ideal_directions:
                    # 检查位置条件
                    if 'left' in str(ideal_directions) and len(detected_left_items) < 3:
                        should_recommend = True
                    elif 'right' in str(ideal_directions) and len(detected_right_items) < 2:
                        should_recommend = True
                    elif 'front' in str(ideal_directions):
                        should_recommend = True
                    elif 'back' in str(ideal_directions):
                        should_recommend = True
                    else:
                        should_recommend = True  # 默认推荐
                else:
                    # 没有位置限制，推荐
                    should_recommend = True
                
                if should_recommend:
                    additions.append({
                        'item': rule_item_name,
                        'item_label': rule_item_label,
                        'position': position_name,
                        'ideal_position': position_name,
                        'reason': suggestion,
                        'suggestion': suggestion,
                        'priority': priority,
                        'action': 'add',
                        'element': rule.get('related_element'),
                        'rule_type': rule.get('rule_type', 'general')  # 添加规则类型
                    })
        
        # 2. 通用风水建议（基于四象布局）
        # 青龙位建议
        if len(detected_left_items) == 0:
            additions.append({
                'item': 'plant',
                'item_label': '绿植/文件架',
                'position': '左侧（青龙位）',
                'reason': '💡 青龙位（左侧）建议摆放绿植（宽叶植物如发财树、富贵竹）或文件架，提升贵人运。青龙位必须高于右侧',
                'suggestion': '💡 建议在左侧（青龙位）摆放绿植（宽叶植物如发财树、富贵竹）或文件架，提升贵人运',
                'priority': 'high',
                'action': 'add',
                'element': '木',
                'rule_type': 'career'  # 青龙位属于升职加薪类
            })
        
        # 玄武位建议
        additions.append({
            'item': 'back_support',
            'item_label': '靠山',
            'position': '后方（玄武位）',
            'reason': '💡 玄武位（后方）最好背靠实墙，不要背靠门或落地窗。如无法调整，可在椅背后放褐色/咖啡色靠枕（山形或写着"靠山"）',
            'suggestion': '💡 确保后方（玄武位）有靠山，可放褐色/咖啡色靠枕或挂衣服营造"虚拟靠山"',
            'priority': 'high',
            'action': 'add',
            'element': '水',
            'rule_type': 'career'  # 靠山属于升职加薪类
        })
        
        # 3. 按优先级排序：喜神建议优先，然后按priority排序
        def sort_key(x):
            priority_score = {'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'low'), 0)
            # 喜神建议额外加分
            if x.get('is_xishen'):
                priority_score += 10
            return priority_score
        
        additions.sort(key=sort_key, reverse=True)
        return additions[:10]  # 增加到10条，确保喜神建议显示
    
    def _calculate_score(self, detected_items: List[Dict], adjustments: List[Dict], 
                        additions: List[Dict], removals: List[Dict]) -> int:
        """
        计算综合评分
        
        评分规则：
        - 没有检测到物品：基础分50分（有优化空间）
        - 有物品基础分：60分
        - 每个正确摆放的物品：+5分
        - 每个需要调整的物品：-10分
        - 每个忌讳物品：-15分
        - 缺少推荐物品：-3分（而不是原来的-5分）
        """
        # 根据是否检测到物品设置基础分
        if len(detected_items) == 0:
            base_score = 50  # 空桌面，基础分50
        else:
            base_score = 60  # 有物品，基础分60
        
        # 正确摆放的物品加分
        correct_items = len(detected_items) - len(adjustments) - len(removals)
        score = base_score + correct_items * 5
        
        # 需要调整的物品扣分
        score -= len(adjustments) * 10
        
        # 忌讳物品扣分
        score -= len(removals) * 15
        
        # 缺少推荐物品轻微扣分（鼓励优化）
        score -= min(len(additions), 3) * 3  # 最多扣9分
        
        # 限制在0-100之间
        score = max(0, min(100, score))
        
        return score
    
    def _generate_summary(self, detected_items: List[Dict], adjustments: List[Dict], 
                         additions: List[Dict], removals: List[Dict], score: int) -> str:
        """生成分析总结"""
        total_items = len(detected_items)
        total_suggestions = len(adjustments) + len(additions) + len(removals)
        
        if score >= 90:
            level = "优秀"
            emoji = "🌟"
        elif score >= 75:
            level = "良好"
            emoji = "👍"
        elif score >= 60:
            level = "一般"
            emoji = "😊"
        elif score >= 50:
            level = "有待优化"
            emoji = "💡"
        else:
            level = "需要改进"
            emoji = "⚠️"
        
        # 没有检测到物品的情况
        if total_items == 0:
            summary = f"{emoji} 您的办公桌较为简洁（评分：{score}分）。根据风水原理，我们为您准备了{len(additions)}条优化建议，包括四象布局（青龙、白虎、朱雀、玄武）的完整规划。即使是简洁的办公桌，合理的布局也能为您带来更好的运势！"
        else:
            summary = f"{emoji} 您的办公桌共检测到{total_items}件物品，整体风水布局{level}（评分：{score}分）。"
            
            if adjustments:
                summary += f"有{len(adjustments)}处物品位置需要调整，"
            
            if additions:
                # 区分是否包含喜神建议
                has_xishen_suggestion = any('喜神' in item.get('reason', '') for item in additions)
                if has_xishen_suggestion:
                    summary += f"结合您的八字喜神，为您推荐{len(additions)}项个性化优化方案，"
                else:
                    summary += f"建议增加{len(additions)}类物品，"
            
            if removals:
                summary += f"有{len(removals)}件物品不宜摆放。"
            
            if total_suggestions == 0:
                # 即使位置都合理，也要给出优化建议
                summary = f"🎉 您的办公桌风水布局非常好！共检测到{total_items}件物品，所有物品摆放位置都很合理，评分{score}分。"
                # 添加通用优化建议
                if not additions:
                    summary += "\n\n💡 为进一步提升运势，建议：\n"
                    summary += "1. 青龙位（左侧）可增加绿植或文件架，提升贵人运\n"
                    summary += "2. 玄武位（后方）确保背靠实墙，增强靠山运\n"
                    summary += "3. 保持办公桌整洁有序，财不入乱门"
                else:
                    summary += "\n\n💡 优化建议："
                    for i, add in enumerate(additions[:3], 1):
                        summary += f"\n{i}. {add.get('suggestion', add.get('reason', ''))}"
        
        # 添加风水要点提示
        summary += "\n\n💡 风水要点：左青龙（高、动）、右白虎（低、静）、前朱雀（开阔）、后玄武（有靠）。"
        
        return summary
    
    def _get_general_suggestions(self, detected_items: List[Dict], xishen: Optional[str] = None) -> List[Dict]:
        """
        生成通用风水建议（即使没有检测到物品也返回建议）
        基于传统风水四象理论：左青龙、右白虎、前朱雀、后玄武
        """
        suggestions = []
        
        # 检查是否检测到各个方位的物品
        # 🔴 防御性检查：避免链式调用导致 None 错误
        has_left_items = False
        has_right_items = False
        has_front_items = False
        has_back_items = False
        
        for item in detected_items:
            if not item:
                continue
            position = item.get('position') or {}
            if isinstance(position, dict):
                relative = position.get('relative', '')
                vertical = position.get('vertical', '')
                if relative == 'left':
                    has_left_items = True
                elif relative == 'right':
                    has_right_items = True
                if vertical == 'front':
                    has_front_items = True
                elif vertical == 'back':
                    has_back_items = True
        
        # 青龙位建议（左侧）
        if not has_left_items or len(detected_items) < 3:
            suggestions.append({
                'item': 'general_left',
                'item_label': '青龙位布局',
                'position': '左侧（青龙位）',
                'reason': '青龙位代表贵人、权威和发展。建议在左侧摆放较高的物品（如资料架、文件夹、绿植），或具有"动"象的物品（如养生壶、加湿器）。青龙位必须高于右侧，象征"宁叫青龙高万丈，不叫白虎抬起头"',
                'priority': 'high',
                'action': 'add',
                'element': '木'
            })
        
        # 白虎位建议（右侧）
        if not has_right_items or len(detected_items) < 3:
            suggestions.append({
                'item': 'general_right',
                'item_label': '白虎位布局',
                'position': '右侧（白虎位）',
                'reason': '白虎位代表执行力，但宜静不宜动。建议保持简洁，只放鼠标、水杯等低矮物品。避免堆积杂物，避免放置电话、烧水壶等"动"象物品。整体高度应低于左侧青龙位',
                'priority': 'medium',
                'action': 'add',
                'element': '金'
            })
        
        # 朱雀位建议（前方）
        if has_front_items:
            suggestions.append({
                'item': 'general_front',
                'item_label': '朱雀位（前方明堂）',
                'position': '前方（朱雀位）',
                'reason': '朱雀位为明堂，代表前景和发展。应保持开阔明亮，避免堆积杂物。如果前方有遮挡，建议清理或在电脑壁纸使用开阔的风景图，象征视野开阔、前程似锦',
                'priority': 'medium',
                'action': 'adjust',
                'element': '火'
            })
        
        # 玄武位建议（后方）
        suggestions.append({
            'item': 'general_back',
            'item_label': '玄武位（靠山）',
            'position': '后方（玄武位）',
            'reason': '玄武位代表靠山和稳固。建议座位后有实墙，避免背靠门或落地窗。如无法调整座位，可在椅背放褐色或咖啡色靠枕，或挂一件衣服，营造"虚拟靠山"',
            'priority': 'high',
            'action': 'add',
            'element': '水'
            })
        
        # 根据喜神加强建议
        if xishen:
            xishen_suggestion = self._get_xishen_emphasis_suggestion(xishen, detected_items)
            if xishen_suggestion:
                suggestions.insert(0, xishen_suggestion)  # 放在最前面
        
        # 整体布局建议
        if len(detected_items) < 2:
            suggestions.append({
                'item': 'general_layout',
                'item_label': '整体布局优化',
                'position': '整体办公桌',
                'reason': '建议合理规划办公桌布局：1）避免柱子角对切座位（形煞）；2）保持桌面整洁有序，财不入乱门；3）利器剪刀等收纳起来，防小人；4）不摆假花，鲜花绿植勤换水；5）选择宽叶绿植，避免仙人掌等带刺植物',
                'priority': 'medium',
                'action': 'add',
                'element': ''
            })
        
        return suggestions
    
    def _get_xishen_emphasis_suggestion(self, xishen: str, detected_items: List[Dict]) -> Optional[Dict]:
        """根据喜神生成强调性建议"""
        xishen_items = {
            '木': ('绿植或木质摆件', '东方或左侧（青龙位）', '木旺东方，生机勃勃，特别利于您的事业发展和贵人运'),
            '火': ('红色装饰或台灯', '南方或前方（朱雀位）', '火主名声和事业，能增强您的影响力和表现力'),
            '土': ('陶瓷摆件或黄色物品', '中央或西南方', '土主稳定和包容，能增强您的稳定性和财运'),
            '金': ('金属笔筒或白色物品', '西方或右侧', '金主权威和决断，能提升您的领导力和执行力'),
            '水': ('水养植物或蓝色物品', '北方或后方', '水主智慧和财运，能增强您的思考能力和财富积累')
        }
        
        if xishen in xishen_items:
            item_name, position, benefit = xishen_items[xishen]
            
            # 检查是否已有相关物品
            has_xishen_item = False
            if xishen == '木':
                has_xishen_item = any('plant' in item.get('name', '').lower() for item in detected_items)
            elif xishen == '水':
                has_xishen_item = any(item.get('name', '') in ['cup', 'bottle', 'water feature'] for item in detected_items)
            
            if not has_xishen_item:
                return {
                    'item': f'xishen_{xishen}',
                    'item_label': f'⭐ 喜神{xishen}专属推荐',
                    'position': position,
                    'reason': f'🌟 根据您的八字，喜神为【{xishen}】，强烈建议在{position}摆放{item_name}。{benefit}。这是最适合您的风水布局！',
                    'priority': 'high',
                    'action': 'add',
                    'element': xishen
                }
        
        return None
    
    @staticmethod
    def _encode_mysql_latin1(text: str) -> bytes:
        """MySQL's latin1 = ISO-8859-1 for 0x80-0x9F control chars + cp1252 for printable chars."""
        result = bytearray()
        _cp1252_reverse = {}
        for b in range(256):
            try:
                c = bytes([b]).decode('cp1252')
                _cp1252_reverse[c] = b
            except Exception:
                pass
        for c in text:
            code = ord(c)
            if code <= 0xFF:
                result.append(code)
            elif c in _cp1252_reverse:
                result.append(_cp1252_reverse[c])
            else:
                result.append(0x3F)
        return bytes(result)

    @staticmethod
    def _safe_decode(text: str) -> str:
        """
        安全解码字符串，处理可能的编码问题
        增强版：支持多种编码修复策略，修复 pymysql latin1 错误编码问题
        
        🔴 核心问题：pymysql 在某些情况下会将 UTF-8 编码的中文字符以 latin1 方式读取，
        导致字符串中包含 0x80-0xFF 范围的字符，这些字符实际上是 UTF-8 字节被错误解释的结果。
        
        修复策略：
        1. 检测是否包含可疑字符（0x80-0xFF）
        2. 尝试将字符串按 latin1 编码回字节，再按 UTF-8 解码
        3. 验证修复后的文本是否包含中文字符
        """
        if not text:
            return text
        
        # 如果是bytes，先解码
        if isinstance(text, bytes):
            try:
                return text.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # 尝试latin1 -> utf-8的修复（pymysql常见问题）
                    fixed = text.decode('latin1').encode('latin1').decode('utf-8')
                    # 验证修复后的文本是否包含中文字符或常见标点
                    if any('\u4e00' <= c <= '\u9fff' or c in '，。！？；：' for c in fixed[:50]):
                        return fixed
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass
                try:
                    # 尝试gbk编码
                    fixed = text.decode('gbk')
                    if any('\u4e00' <= c <= '\u9fff' or c in '，。！？；：' for c in fixed[:50]):
                        return fixed
                except Exception:
                    pass
                return str(text, errors='ignore')
        
        # 如果是字符串，检查是否有乱码
        if isinstance(text, str):
            # 🔴 关键修复：检查是否包含 latin1 错误编码的中文字符
            # 特征：包含 0x80-0xFF 范围的字符，且这些字符组合起来可能是 UTF-8 编码的中文
            has_suspicious_chars = False
            suspicious_char_count = 0
            for c in text[:200]:  # 检查前200个字符
                if 0x80 <= ord(c) <= 0xFF:
                    has_suspicious_chars = True
                    suspicious_char_count += 1
                    if suspicious_char_count >= 3:  # 至少3个可疑字符才可能是中文乱码
                        break
            
            if has_suspicious_chars and suspicious_char_count >= 3:
                try:
                    fixed = self._encode_mysql_latin1(text).decode('utf-8')
                    chinese_count = sum(1 for c in fixed[:100] if '\u4e00' <= c <= '\u9fff')
                    chinese_punct_count = sum(1 for c in fixed[:100] if c in '，。！？；：')
                    if chinese_count >= 2 or chinese_punct_count >= 1:
                        return fixed
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            
            # 检查是否已经是正确的UTF-8（不包含可疑字符或修复失败）
            try:
                # 验证可以正常编码解码
                text.encode('utf-8').decode('utf-8')
                # 如果没有可疑字符，直接返回
                if not has_suspicious_chars:
                    return text
                # 如果有可疑字符但修复失败，可能是其他编码或非中文文本
                return text
            except UnicodeEncodeError:
                try:
                    fixed = self._encode_mysql_latin1(text).decode('utf-8')
                    if sum(1 for c in fixed[:100] if '\u4e00' <= c <= '\u9fff') >= 2:
                        return fixed
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
                return text
        
        return str(text)
    
    def _categorize_suggestions(self, additions: List[Dict]) -> Dict[str, Dict]:
        """
        按规则类型分类建议
        
        Args:
            additions: 增加建议列表
        
        Returns:
            分类后的建议字典
        """
        categories = {
            'wealth': {'name': '💰 财运爆棚', 'icon': '💰', 'color': '#ffd700', 'items': []},
            'career': {'name': '📈 升职加薪', 'icon': '📈', 'color': '#4caf50', 'items': []},
            'love': {'name': '💕 桃花运', 'icon': '💕', 'color': '#e91e63', 'items': []},
            'protection': {'name': '🛡️ 防小人', 'icon': '🛡️', 'color': '#9c27b0', 'items': []},
            'health': {'name': '🏥 健康运势', 'icon': '🏥', 'color': '#00bcd4', 'items': []},
            'study': {'name': '📚 学业考试', 'icon': '📚', 'color': '#3f51b5', 'items': []},
            'relationship': {'name': '🤝 人际关系', 'icon': '🤝', 'color': '#ff9800', 'items': []},
            'general': {'name': '💡 通用建议', 'icon': '💡', 'color': '#607d8b', 'items': []}
        }
        
        for addition in additions:
            # 根据规则类型或元素判断分类
            rule_type = addition.get('rule_type', 'general')
            element = addition.get('element', '')
            is_xishen = addition.get('is_xishen', False)
            
            # 喜神建议优先显示在对应分类
            if is_xishen and element:
                element_map = {'木': 'career', '火': 'career', '土': 'wealth', '金': 'career', '水': 'wealth'}
                category_key = element_map.get(element, 'general')
            elif rule_type in categories:
                category_key = rule_type
            elif element:
                element_map = {'木': 'career', '火': 'career', '土': 'wealth', '金': 'career', '水': 'wealth'}
                category_key = element_map.get(element, 'general')
            else:
                category_key = 'general'
            
            if category_key in categories:
                categories[category_key]['items'].append(addition)
        
        # 移除空分类
        return {k: v for k, v in categories.items() if v['items']}
    
    @staticmethod
    def _get_direction_name(direction: str) -> str:
        """获取方位中文名称"""
        direction_map = {
            'left': '左侧（青龙位）',
            'right': '右侧（白虎位）',
            'front': '前方（朱雀位）',
            'back': '后方（玄武位）',
            'center': '中央',
            'left-front': '左前方',
            'right-front': '右前方',
            'front_left': '左前方',
            'front_right': '右前方',
            'back_left': '左后方',
            'back_right': '右后方',
            'east': '东方',
            'west': '西方',
            'south': '南方',
            'north': '北方',
            'northeast': '东北方',
            'northwest': '西北方',
            'southeast': '东南方',
            'southwest': '西南方',
            'drawer': '抽屉内',
            'pen_holder': '笔筒内',
            'visible': '桌面可见处',
            'desk_surface': '桌面'
        }
        return direction_map.get(direction, direction)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    engine = DeskFengshuiEngine()
    
    # 模拟检测到的物品
    items = [
        {
            'name': 'laptop',
            'label': '笔记本电脑',
            'position': {'relative': 'center', 'relative_name': '中央'}
        },
        {
            'name': 'kettle',
            'label': '烧水壶',
            'position': {'relative': 'right', 'relative_name': '右侧（白虎位）'}
        }
    ]
    
    # 模拟八字信息
    bazi_info = {'xishen': '水', 'jishen': '火'}
    
    result = engine.match_rules(items, bazi_info)
    logger.info(json.dumps(result, ensure_ascii=False, indent=2))


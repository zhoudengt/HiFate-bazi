# -*- coding: utf-8 -*-
"""
办公桌风水规则引擎
匹配物品与风水规则，生成调整建议
"""

import sys
import os
import json
import logging
from typing import List, Dict, Optional

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger(__name__)


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
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        初始化规则引擎
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config or self._get_default_db_config()
        self.rules_cache = None
    
    def _get_default_db_config(self) -> Dict:
        """获取默认数据库配置"""
        try:
            from server.config.mysql_config import MYSQL_CONFIG
            return MYSQL_CONFIG
        except:
            return {
                'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'user': os.getenv('MYSQL_USER', 'root'),
                'password': os.getenv('MYSQL_PASSWORD', '123456'),
                'database': os.getenv('MYSQL_DATABASE', 'hifate_bazi'),
                'charset': 'utf8mb4'
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
    
    def load_rules(self, force_reload: bool = False) -> List[Dict]:
        """
        加载风水规则
        
        Args:
            force_reload: 是否强制重新加载
        
        Returns:
            规则列表
        """
        if self.rules_cache and not force_reload:
            return self.rules_cache
        
        try:
            import pymysql
            
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 查询启用的规则
            sql = """
                SELECT * FROM desk_fengshui_rules 
                WHERE enabled = 1 
                ORDER BY priority DESC, rule_code
            """
            
            cursor.execute(sql)
            rules = cursor.fetchall()
            
            # 解析JSON字段并修复编码
            for rule in rules:
                # 修复文本字段的编码
                if rule.get('reason'):
                    rule['reason'] = self._safe_decode(rule['reason'])
                if rule.get('suggestion'):
                    rule['suggestion'] = self._safe_decode(rule['suggestion'])
                if rule.get('item_label'):
                    rule['item_label'] = self._safe_decode(rule['item_label'])
                
                if rule.get('ideal_position') and isinstance(rule['ideal_position'], str):
                    try:
                        rule['ideal_position'] = json.loads(rule['ideal_position'])
                    except:
                        pass
                
                if rule.get('conditions') and isinstance(rule['conditions'], str):
                    try:
                        rule['conditions'] = json.loads(rule['conditions'])
                    except:
                        pass
            
            cursor.close()
            conn.close()
            
            self.rules_cache = rules
            logger.info(f"加载了 {len(rules)} 条风水规则")
            
            return rules
            
        except Exception as e:
            logger.error(f"加载规则失败: {e}")
            logger.warning("⚠️ 使用内置规则作为fallback")
            # 使用内置规则作为fallback
            return self._get_builtin_rules()
    
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
            
            # 4. 基于喜神生成增加建议
            additions = []
            if bazi_info and bazi_info.get('xishen'):
                additions = self._generate_additions(detected_items, bazi_info, rules)
            
            # 5. 计算评分
            score = self._calculate_score(detected_items, adjustments, additions, removals)
            
            # 6. 生成总结
            summary = self._generate_summary(detected_items, adjustments, additions, removals, score)
            
            return {
                'success': True,
                'adjustments': adjustments,
                'additions': additions,
                'removals': removals,
                'score': score,
                'summary': summary
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
            
            # 查找该物品的规则（支持position和basic类型）
            for rule in rules:
                if rule['rule_type'] not in ['position', 'basic', 'taboo']:
                    continue
                
                # 匹配物品名称
                rule_item_name = rule.get('item_name', '')
                if rule_item_name != item_name:
                    continue
                
                # 获取理想位置
                ideal_pos = rule.get('ideal_position', {})
                if not ideal_pos:
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
                # 如果是position规则且位置不匹配
                elif rule['rule_type'] == 'position' and not is_in_ideal and ideal_directions:
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
                    avoid_direction = ideal_pos.get('direction', '')
                    
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
    
    def _generate_additions(self, detected_items: List[Dict], bazi_info: Dict, rules: List[Dict]) -> List[Dict]:
        """基于规则和喜神生成增加建议"""
        additions = []
        xishen = bazi_info.get('xishen') if bazi_info else None
        
        # 检查已检测到的物品类型
        detected_item_names = {item['name'] for item in detected_items}
        detected_left_items = [item for item in detected_items if item.get('position', {}).get('relative') in ['left', 'front_left', 'back_left']]
        detected_right_items = [item for item in detected_items if item.get('position', {}).get('relative') in ['right', 'front_right', 'back_right']]
        
        # 1. 基于规则的增加建议（检查缺失的重要物品）
        for rule in rules:
            if rule['rule_type'] not in ['position', 'element', 'general']:
                continue
            
            rule_item_name = rule.get('item_name', '')
            rule_item_label = rule.get('item_label', '')
            
            # 跳过位置规则（不是物品）
            if rule_item_name in ['left_items', 'right_items', 'front_area', 'back_area', 'desk', 'computer']:
                continue
            
            # 检查是否已有该物品
            has_item = rule_item_name in detected_item_names
            
            # 如果是喜神相关规则，优先推荐
            if rule.get('related_element') == xishen and not has_item:
                ideal_pos = rule.get('ideal_position', {})
                ideal_directions = ideal_pos.get('directions', [])
                if isinstance(ideal_directions, str):
                    ideal_directions = [ideal_directions]
                
                position_name = self._get_direction_name(ideal_directions[0]) if ideal_directions else '合适位置'
                suggestion = rule.get('suggestion', '')
                if '⭐' not in suggestion:
                    suggestion = f"⭐ {suggestion}"
                
                additions.append({
                    'item': rule_item_name,
                    'item_label': rule_item_label,
                    'position': position_name,
                    'reason': suggestion,
                    'suggestion': suggestion,
                    'priority': 'high',
                    'action': 'add',
                    'element': xishen
                })
                continue
            
            # 通用物品建议（基于规则）
            if rule['rule_type'] == 'position' and not has_item:
                # 检查是否应该推荐（基于位置）
                ideal_pos = rule.get('ideal_position', {})
                ideal_directions = ideal_pos.get('directions', [])
                if isinstance(ideal_directions, str):
                    ideal_directions = [ideal_directions]
                
                # 如果理想位置在左侧，且左侧物品较少，推荐
                if 'left' in str(ideal_directions) and len(detected_left_items) < 2:
                    position_name = '左侧（青龙位）'
                    suggestion = rule.get('suggestion', '')
                    if not suggestion.startswith('✅') and not suggestion.startswith('💡'):
                        suggestion = f"💡 {suggestion}"
                    
                    additions.append({
                        'item': rule_item_name,
                        'item_label': rule_item_label,
                        'position': position_name,
                        'reason': suggestion,
                        'suggestion': suggestion,
                        'priority': 'medium',
                        'action': 'add',
                        'element': rule.get('related_element')
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
                'element': '木'
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
            'element': '水'
        })
        
        # 3. 按优先级排序，返回最多8条建议
        additions.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'low'), 0), reverse=True)
        return additions[:8]
    
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
        has_left_items = any(item.get('position', {}).get('relative') == 'left' for item in detected_items)
        has_right_items = any(item.get('position', {}).get('relative') == 'right' for item in detected_items)
        has_front_items = any(item.get('position', {}).get('vertical') == 'front' for item in detected_items)
        has_back_items = any(item.get('position', {}).get('vertical') == 'back' for item in detected_items)
        
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
    def _safe_decode(self, text: str) -> str:
        """安全解码字符串，处理可能的编码问题"""
        if not text:
            return text
        if isinstance(text, bytes):
            try:
                return text.decode('utf-8')
            except:
                try:
                    return text.decode('latin1').encode('latin1').decode('utf-8')
                except:
                    return str(text)
        if isinstance(text, str):
            # 检查是否有乱码（常见的中文乱码模式）
            try:
                # 尝试重新编码解码
                text.encode('utf-8').decode('utf-8')
                return text
            except:
                # 如果有问题，尝试修复
                try:
                    return text.encode('latin1').decode('utf-8')
                except:
                    return text
        return str(text)
    
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
            'east': '东方',
            'west': '西方',
            'south': '南方',
            'north': '北方',
            'northeast': '东北方',
            'northwest': '西北方'
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
    print(json.dumps(result, ensure_ascii=False, indent=2))


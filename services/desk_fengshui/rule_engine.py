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
                'port': int(os.getenv('MYSQL_PORT', 13306)),
                'user': os.getenv('MYSQL_USER', 'root'),
                'password': os.getenv('MYSQL_PASSWORD', 'root123456'),
                'database': os.getenv('MYSQL_DATABASE', 'bazi_system'),
                'charset': 'utf8mb4'
            }
    
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
            
            # 解析JSON字段
            for rule in rules:
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
            logger.error(f"加载规则失败: {e}", exc_info=True)
            return []
    
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
            current_position = item.get('position', {})
            current_relative = current_position.get('relative', '')
            
            # 查找该物品的规则
            for rule in rules:
                if rule['rule_type'] != 'basic':
                    continue
                
                if rule['item_name'] == item_name:
                    ideal_pos = rule.get('ideal_position', {})
                    ideal_direction = ideal_pos.get('direction', '')
                    
                    # 检查位置是否匹配
                    if ideal_direction and current_relative != ideal_direction:
                        adjustments.append({
                            'item': item['label'],
                            'item_label': item['label'],
                            'current_position': current_position.get('relative_name', current_relative),
                            'ideal_position': self._get_direction_name(ideal_direction),
                            'reason': rule.get('reason', ''),
                            'priority': 'high' if rule.get('priority', 5) >= 7 else 'medium',
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
        """基于喜神生成增加建议"""
        additions = []
        
        # 1. 基于喜神的个性化建议
        xishen = bazi_info.get('xishen') if bazi_info else None
        if xishen:
            # 查找喜神对应的物品规则
            for rule in rules:
                if rule['rule_type'] != 'element_based':
                    continue
                
                if rule.get('related_element') == xishen:
                    # 检查是否已经有相关物品
                    item_name = rule['item_name']
                    has_item = any(item['name'] == item_name for item in detected_items)
                    
                    if not has_item:
                        ideal_pos = rule.get('ideal_position', {})
                        ideal_direction = ideal_pos.get('direction', '')
                        
                        additions.append({
                            'item': item_name,
                            'item_label': rule['item_label'],
                            'position': self._get_direction_name(ideal_direction),
                            'reason': f"⭐ 重点推荐：{rule.get('reason', '')}（您的喜神为{xishen}，此物品特别适合您）",
                            'priority': 'high',  # 喜神建议提升优先级
                            'action': 'add',
                            'element': xishen
                        })
        
        # 2. 通用风水建议（无论是否检测到物品都给出）
        general_suggestions = self._get_general_suggestions(detected_items, xishen)
        additions.extend(general_suggestions)
        
        # 按优先级排序，返回最多6条建议
        additions.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x.get('priority', 'low'), 0), reverse=True)
        return additions[:6]
    
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
                summary = f"🎉 您的办公桌风水布局非常好！共检测到{total_items}件物品，所有物品摆放位置都很合理，评分{score}分。继续保持！"
        
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


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
        
        xishen = bazi_info.get('xishen')
        if not xishen:
            return additions
        
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
                        'reason': rule.get('reason', '') + f"（您的喜神为{xishen}）",
                        'priority': 'medium' if rule.get('priority', 5) >= 7 else 'low',
                        'action': 'add',
                        'element': xishen
                    })
        
        return additions[:3]  # 最多返回3条建议
    
    def _calculate_score(self, detected_items: List[Dict], adjustments: List[Dict], 
                        additions: List[Dict], removals: List[Dict]) -> int:
        """
        计算综合评分
        
        评分规则：
        - 基础分：60分
        - 每个正确摆放的物品：+5分
        - 每个需要调整的物品：-10分
        - 每个忌讳物品：-15分
        - 缺少喜神物品：-5分
        """
        base_score = 60
        
        # 正确摆放的物品加分
        correct_items = len(detected_items) - len(adjustments) - len(removals)
        score = base_score + correct_items * 5
        
        # 需要调整的物品扣分
        score -= len(adjustments) * 10
        
        # 忌讳物品扣分
        score -= len(removals) * 15
        
        # 缺少喜神物品扣分
        score -= len(additions) * 5
        
        # 限制在0-100之间
        score = max(0, min(100, score))
        
        return score
    
    def _generate_summary(self, detected_items: List[Dict], adjustments: List[Dict], 
                         additions: List[Dict], removals: List[Dict], score: int) -> str:
        """生成分析总结"""
        total_items = len(detected_items)
        total_suggestions = len(adjustments) + len(additions) + len(removals)
        
        if score >= 90:
            level = "非常好"
        elif score >= 75:
            level = "良好"
        elif score >= 60:
            level = "一般"
        else:
            level = "需要改进"
        
        summary = f"您的办公桌共检测到{total_items}件物品，整体风水布局{level}（评分：{score}分）。"
        
        if adjustments:
            summary += f"有{len(adjustments)}处物品位置需要调整，"
        
        if additions:
            summary += f"建议增加{len(additions)}类物品，"
        
        if removals:
            summary += f"有{len(removals)}件物品不宜摆放。"
        
        if total_suggestions == 0:
            summary = f"您的办公桌风水布局非常好！共检测到{total_items}件物品，所有物品摆放位置都很合理，评分{score}分。继续保持！"
        
        return summary
    
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


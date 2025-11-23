"""
算法公式规则匹配服务

⚠️ 已废弃：规则已迁移到数据库，统一使用RuleService
此服务保留仅用于向后兼容，新代码请使用RuleService

原规则来源: docs/2025.11.20算法公式.json (816条规则)
迁移状态: 已完成迁移到数据库 (rule_code: FORMULA_*)

规则类型:
- 财富: 基于十神（主星/副星）
- 婚配: 基于日柱
- 性格: 基于日柱
- 总评: 基于年柱+季节+时辰
- 身体: 基于地支关系/五行统计
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from server.services.bazi_service import BaziService
from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer


class FormulaRuleService:
    """算法公式规则匹配服务"""
    
    # 规则文件路径
    RULE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                             'docs', '2025.11.20算法公式.json')
    
    # 缓存规则数据
    _rules_cache = None
    
    @classmethod
    def load_rules(cls) -> Dict[str, Any]:
        """加载规则数据"""
        if cls._rules_cache is None:
            with open(cls.RULE_FILE, 'r', encoding='utf-8') as f:
                cls._rules_cache = json.load(f)
        return cls._rules_cache
    
    @classmethod
    def match_rules(cls, bazi_data: Dict[str, Any], rule_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        匹配规则
        
        Args:
            bazi_data: 八字数据
            rule_types: 要匹配的规则类型列表，None表示匹配所有
            
        Returns:
            {
                'matched_rules': {
                    'wealth': [matched_rule_ids],
                    'marriage': [matched_rule_ids],
                    'character': [matched_rule_ids],
                    'summary': [matched_rule_ids],
                    'health': [matched_rule_ids]
                },
                'rule_details': {rule_id: rule_data},
                'total_matched': int
            }
        """
        rules_data = cls.load_rules()
        
        # 默认匹配所有类型
        if rule_types is None:
            rule_types = ['财富', '婚配', '性格', '总评', '身体', '十神命格']
        
        matched_rules = {
            'wealth': [],      # 财富
            'marriage': [],    # 婚配
            'character': [],   # 性格
            'summary': [],     # 总评
            'health': [],      # 身体
            'shishen': []      # 十神命格
        }
        rule_details = {}
        
        type_mapping = {
            '财富': 'wealth',
            '婚配': 'marriage',
            '性格': 'character',
            '总评': 'summary',
            '身体': 'health',
            '十神命格': 'shishen'
        }
        
        # 遍历每个规则类型
        for sheet_name, sheet_data in rules_data.items():
            if sheet_name not in rule_types:
                continue
                
            english_type = type_mapping.get(sheet_name)
            if not english_type:
                continue
            
            # ✅ 十神命格特殊处理：按月柱副星顺序只返回第一个匹配的
            if sheet_name == '十神命格':
                matched_rule = cls._match_shishen_by_priority(bazi_data, sheet_data['rows'])
                if matched_rule:
                    rule_id = matched_rule['ID']
                    matched_rules[english_type].append(rule_id)
                    rule_details[rule_id] = {
                        'id': rule_id,
                        'type': sheet_name,
                        'type_en': english_type,
                        'gender': matched_rule.get('性别', '无论男女'),
                        'condition1': matched_rule.get('筛选条件1', ''),
                        'condition2': matched_rule.get('筛选条件2', ''),
                        'result': matched_rule.get('结果', '')
                    }
                continue  # 十神命格处理完毕，跳过常规匹配流程
            
            # 常规匹配流程（财富、婚配、性格等）
            for rule in sheet_data['rows']:
                if cls._match_single_rule(bazi_data, rule, sheet_name):
                    rule_id = rule['ID']
                    matched_rules[english_type].append(rule_id)
                    rule_details[rule_id] = {
                        'id': rule_id,
                        'type': sheet_name,
                        'type_en': english_type,
                        'gender': rule.get('性别', '无论男女'),
                        'condition1': rule.get('筛选条件1', ''),
                        'condition2': rule.get('筛选条件2', ''),
                        'result': rule.get('结果', '')
                    }
        
        total_matched = sum(len(rules) for rules in matched_rules.values())
        
        return {
            'matched_rules': matched_rules,
            'rule_details': rule_details,
            'total_matched': total_matched
        }
    
    @classmethod
    def _match_single_rule(cls, bazi_data: Dict[str, Any], rule: Dict[str, Any], rule_type: str) -> bool:
        """
        匹配单条规则
        
        Args:
            bazi_data: 八字数据
            rule: 规则数据
            rule_type: 规则类型（财富/婚配/性格/总评/身体）
            
        Returns:
            是否匹配
        """
        # 检查性别
        rule_gender = rule.get('性别', '无论男女')
        bazi_gender = bazi_data.get('basic_info', {}).get('gender', 'male')
        
        if rule_gender != '无论男女':
            if (rule_gender == '男' and bazi_gender != 'male') or \
               (rule_gender == '女' and bazi_gender != 'female'):
                return False
        
        # 根据规则类型调用不同的匹配方法
        condition1 = rule.get('筛选条件1', '')
        condition2 = rule.get('筛选条件2', '')
        
        if rule_type == '财富':
            return cls._match_wealth_rule(bazi_data, condition1, condition2)
        elif rule_type == '婚配':
            return cls._match_marriage_rule(bazi_data, condition1, condition2)
        elif rule_type == '性格':
            return cls._match_character_rule(bazi_data, condition1, condition2)
        elif rule_type == '总评':
            return cls._match_summary_rule(bazi_data, condition1, condition2)
        elif rule_type == '身体':
            return cls._match_health_rule(bazi_data, condition1, condition2)
        elif rule_type == '十神命格':
            return cls._match_shishen_rule(bazi_data, condition1, condition2)
        
        return False
    
    @classmethod
    def _match_wealth_rule(cls, bazi_data: Dict[str, Any], condition1: str, condition2: str) -> bool:
        """
        匹配财富规则
        
        条件示例:
        - 年柱主星是正财
        - 月柱主星是正财，月柱副星有食神或伤官
        - 年柱主星是正财，且年柱副星有正官，并且还是身旺或极旺
        """
        if condition1 != '十神':
            return False
        
        details = bazi_data.get('details', {})
        
        # 解析复合条件（用逗号和"且"、"并且"分割）
        sub_conditions = re.split(r'[，,]|且|并且', condition2)
        
        for sub_cond in sub_conditions:
            sub_cond = sub_cond.strip()
            if not sub_cond:
                continue
            
            # 匹配主星条件: "X柱主星是Y" 或 "X柱主星为Y"
            main_star_match = re.search(r'(年柱|月柱|日柱|时柱)主星(是|为)(.+)', sub_cond)
            if main_star_match:
                pillar_map = {'年柱': 'year', '月柱': 'month', '日柱': 'day', '时柱': 'hour'}
                pillar = pillar_map[main_star_match.group(1)]
                expected_star = main_star_match.group(3).strip()  # group(3)因为group(2)是"是|为"
                actual_star = details.get(pillar, {}).get('main_star', '')
                if actual_star != expected_star:
                    return False
                continue
            
            # 匹配副星条件: "X柱副星有Y" 或 "X柱副星有Y或Z"
            sub_star_match = re.search(r'(年柱|月柱|日柱|时柱|日支)副星(是|有)(.+)', sub_cond)
            if sub_star_match:
                pillar_map = {'年柱': 'year', '月柱': 'month', '日柱': 'day', '日支': 'day', '时柱': 'hour'}
                pillar = pillar_map[sub_star_match.group(1)]
                stars_text = sub_star_match.group(3).strip()
                
                # 处理"或"逻辑: "食神或伤官"
                if '或' in stars_text:
                    expected_stars = [s.strip() for s in stars_text.split('或')]
                else:
                    expected_stars = [stars_text]
                
                hidden_stars = details.get(pillar, {}).get('hidden_stars', [])
                # 满足其一即可
                if not any(star in hidden_stars for star in expected_stars):
                    return False
                continue
            
            # 匹配旺衰条件: "还是身旺或极旺" 或 "还是身旺命或极旺"
            if '身旺' in sub_cond or '极旺' in sub_cond:
                if not cls._check_wangshuai(bazi_data, ['身旺', '极旺']):
                    return False
                continue
            
            # 匹配"不受刑冲"
            if '不受刑冲' in sub_cond:
                if not cls._check_no_chong_xing(bazi_data):
                    return False
                continue
            
            # 匹配"禄"临官 - 暂时跳过，返回False
            if '禄' in sub_cond or '临官' in sub_cond:
                return False
            
            # 匹配"长生和库" - 暂时跳过，返回False
            if '长生' in sub_cond and '库' in sub_cond:
                return False
        
        return True
    
    @classmethod
    def _match_marriage_rule(cls, bazi_data: Dict[str, Any], condition1: str, condition2: str) -> bool:
        """
        匹配婚配规则
        
        条件示例: 甲子
        """
        if condition1 != '日柱':
            return False
        
        day_pillar = bazi_data.get('bazi_pillars', {}).get('day', {})
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        
        # 解析条件（如"甲子"）
        if len(condition2) == 2:
            expected_stem = condition2[0]
            expected_branch = condition2[1]
            return day_stem == expected_stem and day_branch == expected_branch
        
        return False
    
    @classmethod
    def _match_character_rule(cls, bazi_data: Dict[str, Any], condition1: str, condition2: str) -> bool:
        """
        匹配性格规则
        
        条件示例: 甲子
        """
        # 与婚配规则逻辑相同
        return cls._match_marriage_rule(bazi_data, condition1, condition2)
    
    @classmethod
    def _match_shishen_rule(cls, bazi_data: Dict[str, Any], condition1: str, condition2: str) -> bool:
        """
        匹配十神命格规则
        
        条件格式：
        优先级11：月柱主星是正官，且月柱副星有正官
        优先级21：月柱副星有正官，且年柱主星有正官或时柱主星有正官
        优先级31：月柱主星是正官，且年柱副星有正官或日柱副星有正官或时柱副星有正官
        
        主星 = 天干的十神 (main_star)
        副星 = 地支藏干的十神 (hidden_stars)
        """
        if condition1 != '月柱':
            return False
        
        # 解析条件中的十神名称（从条件2中提取）
        shishen_name = None
        for possible_shishen in ['正官', '七杀', '正印', '偏印', '正财', '偏财', '食神', '伤官']:
            if possible_shishen in condition2:
                shishen_name = possible_shishen
                break
        
        if not shishen_name:
            return False
        
        # 获取八字详细信息（使用与财富规则相同的数据结构）
        details = bazi_data.get('details', {})
        if not details:
            return False
        
        # 提取各柱的十神信息（主星 + 副星）
        year = details.get('year', {})
        month = details.get('month', {})
        day = details.get('day', {})
        hour = details.get('hour', {})
        
        # 主星（天干十神）
        year_main = year.get('main_star', '')
        month_main = month.get('main_star', '')
        day_main = day.get('main_star', '')
        hour_main = hour.get('main_star', '')
        
        # 副星（地支藏干十神）
        year_hidden = year.get('hidden_stars', [])
        month_hidden = month.get('hidden_stars', [])
        day_hidden = day.get('hidden_stars', [])
        hour_hidden = hour.get('hidden_stars', [])
        
        # 优先级1：月柱主星是XX，且月柱副星有XX
        if month_main == shishen_name and shishen_name in month_hidden:
            return True
        
        # 优先级2：月柱副星有XX，且（年柱主星有XX 或 时柱主星有XX）
        # 按年月日时顺序，先检查年柱，再检查时柱
        if shishen_name in month_hidden:
            # 先检查年柱主星
            if year_main == shishen_name:
                return True
            # 再检查时柱主星
            if hour_main == shishen_name:
                return True
        
        # 优先级3：月柱主星是XX，且（年/日/时柱副星有XX）
        if month_main == shishen_name:
            if (shishen_name in year_hidden or 
                shishen_name in day_hidden or 
                shishen_name in hour_hidden):
                return True
        
        return False
    
    @classmethod
    def _match_shishen_by_priority(cls, bazi_data: Dict[str, Any], shishen_rules: list) -> Optional[Dict[str, Any]]:
        """
        按优先级顺序匹配十神命格，只返回第一个匹配的规则
        
        匹配顺序：
        1. 优先级1（最高）：月柱主星是XX，且月柱副星有XX
        2. 优先级2（中等）：月柱副星有XX，且（年柱主星有XX 或 时柱主星有XX）
           ⚠️ 只有在优先级2中，才按月柱副星的出现顺序匹配
        3. 优先级3（最低）：月柱主星是XX，且（年/日/时柱副星有XX）
        
        Args:
            bazi_data: 八字数据
            shishen_rules: 十神命格规则列表
        
        Returns:
            匹配的规则（dict）或 None
        """
        # 获取八字详细信息
        details = bazi_data.get('details', {})
        if not details:
            return None
        
        month = details.get('month', {})
        month_main = month.get('main_star', '')
        month_hidden = month.get('hidden_stars', [])
        
        year_main = details.get('year', {}).get('main_star', '')
        hour_main = details.get('hour', {}).get('main_star', '')
        
        year_hidden = details.get('year', {}).get('hidden_stars', [])
        day_hidden = details.get('day', {}).get('hidden_stars', [])
        hour_hidden = details.get('hour', {}).get('hidden_stars', [])
        
        # 性别筛选辅助函数
        def check_gender(rule):
            rule_gender = rule.get('性别', '无论男女')
            bazi_gender = bazi_data.get('basic_info', {}).get('gender', 'male')
            if rule_gender != '无论男女':
                if (rule_gender == '男' and bazi_gender != 'male') or \
                   (rule_gender == '女' and bazi_gender != 'female'):
                    return False
            return True
        
        # 提取十神名称辅助函数
        def extract_shishen_name(condition2):
            for possible_shishen in ['正官', '七杀', '正印', '偏印', '正财', '偏财', '食神', '伤官']:
                if possible_shishen in condition2:
                    return possible_shishen
            return None
        
        # ============ 第一步：检查所有规则的优先级1 ============
        for rule in shishen_rules:
            if not check_gender(rule):
                continue
            
            condition1 = rule.get('筛选条件1', '')
            condition2 = rule.get('筛选条件2', '')
            
            if condition1 != '月柱':
                continue
            
            shishen_name = extract_shishen_name(condition2)
            if not shishen_name:
                continue
            
            # 优先级1：月柱主星是XX，且月柱副星有XX
            if month_main == shishen_name and shishen_name in month_hidden:
                return rule  # ✅ 找到优先级1匹配，立即返回
        
        # ============ 第二步：检查所有规则的优先级2（按月柱副星顺序） ============
        # 🔑 关键：只有在优先级2中才按副星出现顺序匹配
        for hidden_star in month_hidden:  # 按月柱副星顺序遍历
            for rule in shishen_rules:
                if not check_gender(rule):
                    continue
                
                condition1 = rule.get('筛选条件1', '')
                condition2 = rule.get('筛选条件2', '')
                
                if condition1 != '月柱':
                    continue
                
                shishen_name = extract_shishen_name(condition2)
                if not shishen_name:
                    continue
                
                # 如果当前规则的十神与当前副星匹配
                if shishen_name == hidden_star:
                    # 优先级2：月柱副星有XX，且（年柱主星有XX 或 时柱主星有XX）
                    if year_main == shishen_name or hour_main == shishen_name:
                        return rule  # ✅ 找到优先级2匹配，立即返回
        
        # ============ 第三步：检查所有规则的优先级3 ============
        for rule in shishen_rules:
            if not check_gender(rule):
                continue
            
            condition1 = rule.get('筛选条件1', '')
            condition2 = rule.get('筛选条件2', '')
            
            if condition1 != '月柱':
                continue
            
            shishen_name = extract_shishen_name(condition2)
            if not shishen_name:
                continue
            
            # 优先级3：月柱主星是XX，且（年/日/时柱副星有XX）
            if month_main == shishen_name:
                if (shishen_name in year_hidden or 
                    shishen_name in day_hidden or 
                    shishen_name in hour_hidden):
                    return rule  # ✅ 找到优先级3匹配，立即返回
        
        return None  # 没有任何规则匹配
    
    @classmethod
    def _match_summary_rule(cls, bazi_data: Dict[str, Any], condition1: str, condition2: str) -> bool:
        """
        匹配总评规则
        
        条件示例:
        - 甲子，且出生于春季，并且出生于卯时到申时
        - 甲子，且出生于农历六月
        """
        if condition1 != '年柱':
            return False
        
        year_pillar = bazi_data.get('bazi_pillars', {}).get('year', {})
        year_stem = year_pillar.get('stem', '')
        year_branch = year_pillar.get('branch', '')
        
        # 解析条件
        parts = re.split(r'[，,]|且|并且', condition2)
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            # 第一部分：年柱（如"甲子"）
            if i == 0 and len(part) == 2:
                expected_stem = part[0]
                expected_branch = part[1]
                if year_stem != expected_stem or year_branch != expected_branch:
                    return False
                continue
            
            # 匹配季节
            if '出生于春季' in part or '出生于夏季' in part or '出生于秋季' in part or '出生于冬季' in part:
                season_match = re.search(r'出生于(春季|夏季|秋季|冬季)', part)
                if season_match:
                    expected_season = season_match.group(1)
                    actual_season = cls._get_season_by_jieqi(bazi_data)
                    if actual_season != expected_season:
                        return False
                continue
            
            # 匹配时辰范围
            if '出生于' in part and '时到' in part and '时' in part:
                time_match = re.search(r'出生于(.{1})时到(.{1})时', part)
                if time_match:
                    start_hour = time_match.group(1)
                    end_hour = time_match.group(2)
                    
                    # 定义时辰顺序
                    hour_order = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
                    
                    # 获取时辰范围
                    start_idx = hour_order.index(start_hour)
                    end_idx = hour_order.index(end_hour)
                    
                    if start_idx <= end_idx:
                        # 不跨日: 卯时到申时 = ['卯','辰','巳','午','未','申']
                        hour_range = hour_order[start_idx:end_idx+1]
                    else:
                        # 跨日: 酉时到寅时 = ['酉','戌','亥','子','丑','寅']
                        hour_range = hour_order[start_idx:] + hour_order[:end_idx+1]
                    
                    hour_branch = bazi_data.get('bazi_pillars', {}).get('hour', {}).get('branch', '')
                    if hour_branch not in hour_range:
                        return False
                continue
            
            # 匹配农历月份
            if '出生于农历' in part:
                lunar_month_match = re.search(r'出生于农历(.+)月', part)
                if lunar_month_match:
                    # 暂时跳过农历月份判断
                    # TODO: 需要实现农历月份获取
                    return False
        
        return True
    
    @classmethod
    def _match_health_rule(cls, bazi_data: Dict[str, Any], condition1: str, condition2: str) -> bool:
        """
        匹配身体规则
        
        条件类型:
        - 地支: 子午冲、丑未冲等
        - 天干地支: 对应五行属性火低于1个（包含1个）
        - 日干: 甲、乙、丙等
        - 日支: 子、丑、寅等
        - 五行: 木、火、土、金、水
        """
        if condition1 == '地支':
            # 地支冲刑害
            return cls._check_branch_relation(bazi_data, condition2)
        
        elif condition1 == '天干地支':
            # 五行统计
            if '对应五行属性' in condition2 and '低于1个' in condition2:
                element_match = re.search(r'对应五行属性(.{1})低于1个', condition2)
                if element_match:
                    element = element_match.group(1)
                    element_counts = bazi_data.get('element_counts', {})
                    # 【防御性代码】确保 element_counts 是字典类型
                    if isinstance(element_counts, str):
                        try:
                            element_counts = json.loads(element_counts)
                        except:
                            element_counts = {}
                    if not isinstance(element_counts, dict):
                        element_counts = {}
                    return element_counts.get(element, 0) <= 1
        
        elif condition1 == '日干':
            # 日干匹配
            day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
            return day_stem == condition2
        
        elif condition1 == '日支':
            # 日支匹配
            day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
            return day_branch == condition2
        
        elif condition1 == '五行':
            # 日干五行匹配
            day_element = bazi_data.get('elements', {}).get('day', {}).get('stem_element', '')
            return day_element == condition2
        
        return False
    
    @classmethod
    def _check_wangshuai(cls, bazi_data: Dict[str, Any], expected_statuses: List[str]) -> bool:
        """
        检查旺衰状态
        
        Args:
            bazi_data: 八字数据
            expected_statuses: 期望的旺衰状态列表（如['身旺', '极旺']）
            
        Returns:
            是否满足条件
        """
        try:
            # 调用旺衰分析
            solar_date = bazi_data.get('basic_info', {}).get('solar_date', '')
            solar_time = bazi_data.get('basic_info', {}).get('solar_time', '')
            gender = bazi_data.get('basic_info', {}).get('gender', 'male')
            
            wangshuai_result = WangShuaiAnalyzer.analyze(solar_date, solar_time, gender)
            wangshuai_status = wangshuai_result.get('wangshuai', '')
            
            return wangshuai_status in expected_statuses
        except Exception as e:
            print(f"旺衰检查失败: {e}")
            return False
    
    @classmethod
    def _check_no_chong_xing(cls, bazi_data: Dict[str, Any]) -> bool:
        """
        检查是否不受刑冲
        
        Returns:
            True表示不受刑冲，False表示受刑冲
        """
        relationships = bazi_data.get('relationships', {})
        # 【防御性代码】确保 relationships 是字典类型
        if isinstance(relationships, str):
            try:
                relationships = json.loads(relationships)
            except:
                relationships = {}
        if not isinstance(relationships, dict):
            relationships = {}
        
        branch_relations = relationships.get('branch_relations', {})
        # 【防御性代码】确保 branch_relations 是字典类型
        if isinstance(branch_relations, str):
            try:
                branch_relations = json.loads(branch_relations)
            except:
                branch_relations = {}
        if not isinstance(branch_relations, dict):
            branch_relations = {}
        
        chong = branch_relations.get('chong', [])
        xing = branch_relations.get('xing', [])
        
        # 如果没有冲和刑，则不受刑冲
        return len(chong) == 0 and len(xing) == 0
    
    @classmethod
    def _check_branch_relation(cls, bazi_data: Dict[str, Any], condition: str) -> bool:
        """
        检查地支关系（冲刑害）
        
        条件示例: 子午冲、丑未冲、寅申冲等
        """
        relationships = bazi_data.get('relationships', {})
        # 【防御性代码】确保 relationships 是字典类型
        if isinstance(relationships, str):
            try:
                relationships = json.loads(relationships)
            except:
                relationships = {}
        if not isinstance(relationships, dict):
            relationships = {}
        
        branch_relations = relationships.get('branch_relations', {})
        # 【防御性代码】确保 branch_relations 是字典类型
        if isinstance(branch_relations, str):
            try:
                branch_relations = json.loads(branch_relations)
            except:
                branch_relations = {}
        if not isinstance(branch_relations, dict):
            branch_relations = {}
        
        # 解析条件
        if '冲' in condition:
            relation_type = 'chong'
            branches = condition.replace('冲', '')
        elif '刑' in condition:
            relation_type = 'xing'
            branches = condition.replace('刑', '')
        elif '害' in condition:
            relation_type = 'hai'
            branches = condition.replace('害', '')
        else:
            return False
        
        # 检查是否存在该地支关系
        relations = branch_relations.get(relation_type, [])
        for relation in relations:
            relation_branches = relation.get('branches', [])
            # 检查是否包含这两个地支
            if len(branches) == 2:
                if branches[0] in relation_branches and branches[1] in relation_branches:
                    return True
        
        return False
    
    @classmethod
    def _get_season_by_jieqi(cls, bazi_data: Dict[str, Any]) -> str:
        """
        根据节气获取季节
        
        Returns:
            春季、夏季、秋季、冬季
        """
        solar_date_str = bazi_data.get('basic_info', {}).get('solar_date', '')
        if not solar_date_str:
            return ''
        
        try:
            # 解析日期
            date_obj = datetime.strptime(solar_date_str, '%Y-%m-%d')
            month = date_obj.month
            day = date_obj.day
            
            # 根据节气定义季节
            # 春季: 立春(2/4左右) - 立夏(5/5左右)
            # 夏季: 立夏(5/5左右) - 立秋(8/7左右)
            # 秋季: 立秋(8/7左右) - 立冬(11/7左右)
            # 冬季: 立冬(11/7左右) - 立春(2/4左右)
            
            if (month == 2 and day >= 4) or month in [3, 4] or (month == 5 and day < 5):
                return '春季'
            elif (month == 5 and day >= 5) or month in [6, 7] or (month == 8 and day < 7):
                return '夏季'
            elif (month == 8 and day >= 7) or month in [9, 10] or (month == 11 and day < 7):
                return '秋季'
            else:
                return '冬季'
        except Exception as e:
            print(f"季节计算失败: {e}")
            return ''

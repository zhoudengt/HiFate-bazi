#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将FormulaRuleService的JSON规则迁移到数据库
将文本条件转换为RuleService的JSON条件格式
"""

import json
import os
import sys
import re
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class FormulaRuleConverter:
    """FormulaRuleService规则转换器"""
    
    # 规则类型映射
    TYPE_MAPPING = {
        '财富': 'wealth',
        '婚配': 'marriage',
        '性格': 'character',
        '总评': 'summary',
        '身体': 'health',
        '十神命格': 'shishen'
    }
    
    # 性别映射
    GENDER_MAPPING = {
        '无论男女': None,  # None表示不限制性别
        '男': 'male',
        '女': 'female'
    }
    
    @classmethod
    def convert_condition_to_json(cls, condition1: str, condition2: str, rule_type: str) -> Dict[str, Any]:
        """
        将FormulaRuleService的文本条件转换为RuleService的JSON条件格式
        
        Args:
            condition1: 筛选条件1（如"十神"、"日柱"）
            condition2: 筛选条件2（如"年柱主星是正财"）
            rule_type: 规则类型（财富/婚配/性格/总评/身体/十神命格）
            
        Returns:
            JSON格式的条件字典
        """
        conditions = {}
        
        if rule_type == '财富':
            return cls._convert_wealth_condition(condition1, condition2)
        elif rule_type == '婚配':
            return cls._convert_marriage_condition(condition1, condition2)
        elif rule_type == '性格':
            return cls._convert_character_condition(condition1, condition2)
        elif rule_type == '总评':
            return cls._convert_summary_condition(condition1, condition2)
        elif rule_type == '身体':
            return cls._convert_health_condition(condition1, condition2)
        elif rule_type == '十神命格':
            return cls._convert_shishen_condition(condition1, condition2)
        
        return conditions
    
    @classmethod
    def _convert_wealth_condition(cls, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        转换财富规则条件
        
        示例：
        - "年柱主星是正财" 
        - "月柱主星是正财，月柱副星有食神或伤官"
        - "年柱主星是正财，且年柱副星有正官，并且还是身旺或极旺"
        """
        all_conditions = []
        
        # 解析复合条件（用逗号和"且"、"并且"分割）
        sub_conditions = re.split(r'[，,]|且|并且', condition2)
        
        for sub_cond in sub_conditions:
            sub_cond = sub_cond.strip()
            if not sub_cond:
                continue
            
            # 匹配主星条件: "X柱主星是Y" 或 "X柱主星为Y"
            main_star_match = re.search(r'(年柱|月柱|日柱|时柱)主星(是|为)(.+)', sub_cond)
            if main_star_match:
                pillar_name = main_star_match.group(1)
                star_name = main_star_match.group(3).strip()
                pillar_key = cls._pillar_name_to_key(pillar_name)
                
                # 使用EnhancedRuleEngine支持的格式
                if pillar_key == 'year':
                    all_conditions.append({'main_star_in_year': star_name})
                elif pillar_key == 'day':
                    all_conditions.append({'main_star_in_day': star_name})
                else:
                    # 对于month和hour，使用main_star_in_pillar格式
                    all_conditions.append({
                        'main_star_in_pillar': {
                            'pillar': pillar_key,
                            'eq': star_name
                        }
                    })
                continue
            
            # 匹配副星条件: "X柱副星有Y" 或 "X柱副星有Y或Z"
            sub_star_match = re.search(r'(年柱|月柱|日柱|时柱|日支)副星(是|有)(.+)', sub_cond)
            if sub_star_match:
                pillar_name = sub_star_match.group(1)
                stars_text = sub_star_match.group(3).strip()
                pillar_key = cls._pillar_name_to_key(pillar_name)
                
                # 处理"或"逻辑: "食神或伤官"
                if '或' in stars_text:
                    expected_stars = [s.strip() for s in stars_text.split('或')]
                else:
                    expected_stars = [stars_text]
                
                # 使用hidden_stars_in_pillar格式（需要扩展EnhancedRuleEngine支持）
                # 暂时使用一个自定义格式，后续需要在EnhancedRuleEngine中添加支持
                all_conditions.append({
                    f'hidden_stars_in_{pillar_key}': expected_stars
                })
                continue
            
            # 匹配旺衰条件: "还是身旺或极旺" 或 "还是身旺命或极旺"
            if '身旺' in sub_cond or '极旺' in sub_cond:
                all_conditions.append({
                    'wangshuai': ['身旺', '极旺']
                })
                continue
            
            # 匹配"不受刑冲"
            if '不受刑冲' in sub_cond or '没有刑冲' in sub_cond:
                all_conditions.append({
                    'no_chong_xing': True
                })
                continue
            
            # 匹配"禄"临官 - 暂时跳过（需要更复杂的逻辑）
            if '禄' in sub_cond or '临官' in sub_cond:
                # TODO: 需要实现"禄"临官的判断逻辑
                pass
            
            # 匹配"长生和库" - 暂时跳过（需要更复杂的逻辑）
            if '长生' in sub_cond and '库' in sub_cond:
                # TODO: 需要实现"长生和库"的判断逻辑
                pass
        
        if len(all_conditions) == 1:
            return all_conditions[0]
        elif len(all_conditions) > 1:
            return {'all': all_conditions}
        else:
            return {}
    
    @classmethod
    def _convert_marriage_condition(cls, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        转换婚配规则条件
        
        示例: "甲子"
        """
        if condition1 != '日柱':
            return {}
        
        # 解析日柱（如"甲子"）
        if len(condition2) == 2:
            return {
                'day_pillar': condition2
            }
        
        return {}
    
    @classmethod
    def _convert_character_condition(cls, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        转换性格规则条件（与婚配规则相同）
        """
        return cls._convert_marriage_condition(condition1, condition2)
    
    @classmethod
    def _convert_summary_condition(cls, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        转换总评规则条件
        
        示例：
        - "甲子，且出生于春季，并且出生于卯时到申时"
        - "甲子，且出生于农历六月"
        """
        all_conditions = []
        
        if condition1 != '年柱':
            return {}
        
        # 解析复合条件
        parts = re.split(r'[，,]|且|并且', condition2)
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            # 第一部分：年柱（如"甲子"）
            if i == 0 and len(part) == 2:
                all_conditions.append({
                    'year_pillar': part
                })
                continue
            
            # 匹配季节
            season_match = re.search(r'出生于(春季|夏季|秋季|冬季)', part)
            if season_match:
                season = season_match.group(1)
                all_conditions.append({
                    'season': season
                })
                continue
            
            # 匹配时辰范围
            time_match = re.search(r'出生于(.{1})时到(.{1})时', part)
            if time_match:
                start_hour = time_match.group(1)
                end_hour = time_match.group(2)
                # 定义时辰顺序
                hour_order = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
                start_idx = hour_order.index(start_hour) if start_hour in hour_order else -1
                end_idx = hour_order.index(end_hour) if end_hour in hour_order else -1
                
                if start_idx >= 0 and end_idx >= 0:
                    if start_idx <= end_idx:
                        hour_range = hour_order[start_idx:end_idx+1]
                    else:
                        hour_range = hour_order[start_idx:] + hour_order[:end_idx+1]
                    all_conditions.append({
                        'hour_branch_range': hour_range
                    })
                continue
            
            # 匹配农历月份
            lunar_month_match = re.search(r'出生于农历(.+)月', part)
            if lunar_month_match:
                lunar_month = lunar_month_match.group(1)
                all_conditions.append({
                    'lunar_month': lunar_month
                })
                continue
        
        if len(all_conditions) == 1:
            return all_conditions[0]
        elif len(all_conditions) > 1:
            return {'all': all_conditions}
        else:
            return {}
    
    @classmethod
    def _convert_health_condition(cls, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        转换身体规则条件
        
        示例：
        - condition1="地支", condition2="子午冲" -> 地支冲关系
        - condition1="五行", condition2="木" -> 五行条件（日干五行）
        - condition1="日干", condition2="甲" -> 日干条件
        - condition1="天干地支", condition2="对应五行属性X低于1个" -> 五行统计条件
        """
        conditions = {}
        
        # 处理地支冲关系
        if condition1 == '地支':
            chong_match = re.search(r'(.{1})(.{1})冲', condition2)
            if chong_match:
                branch1 = chong_match.group(1)
                branch2 = chong_match.group(2)
                return {
                    'branch_chong': [branch1, branch2]
                }
        
        # 处理五行条件（日干五行）
        elif condition1 == '五行':
            # condition2是五行名称：木、火、土、金、水
            # 需要检查日干的五行属性
            element = condition2
            if element in ['木', '火', '土', '金', '水']:
                # 定义五行对应的天干
                element_to_stems = {
                    '木': ['甲', '乙'],
                    '火': ['丙', '丁'],
                    '土': ['戊', '己'],
                    '金': ['庚', '辛'],
                    '水': ['壬', '癸']
                }
                # 使用pillar_in条件检查日干是否属于该五行
                stems = element_to_stems.get(element, [])
                if stems:
                return {
                        'pillar_in': {
                            'pillar': 'day',
                            'part': 'stem',
                            'values': stems
                        }
                }
        
        # 处理日干条件
        elif condition1 == '日干':
            # condition2是天干：甲、乙、丙等
            if len(condition2) == 1 and condition2 in '甲乙丙丁戊己庚辛壬癸':
                return {
                    'pillar_in': {
                        'pillar': 'day',
                        'part': 'stem',
                        'values': [condition2]
                    }
                }
        
        # 处理日支条件
        elif condition1 == '日支':
            # condition2是地支：子、丑、寅等
            if len(condition2) == 1 and condition2 in '子丑寅卯辰巳午未申酉戌亥':
                return {
                    'pillar_in': {
                        'pillar': 'day',
                        'part': 'branch',
                        'values': [condition2]
                    }
                }
        
        # 处理天干地支五行统计条件
        elif condition1 == '天干地支':
            # condition2格式：对应五行属性X低于1个（包含1个）
            element_match = re.search(r'对应五行属性([木火土金水])低于(\d+)个', condition2)
            if element_match:
                element = element_match.group(1)
                max_count = int(element_match.group(2))
                # 使用elements_count条件
                return {
                    'elements_count': {
                        element: {'lte': max_count}
                    }
                }
        
        return conditions
    
    @classmethod
    def _convert_shishen_condition(cls, condition1: str, condition2: str) -> Dict[str, Any]:
        """
        转换十神命格规则条件
        
        示例：
        - "优先级11：月柱主星是正官，且月柱副星有正官"
        - "优先级21：月柱副星有正官，且年柱主星有正官或时柱主星有正官"
        """
        # 提取优先级（如果存在）
        priority_match = re.search(r'优先级(\d+)', condition2)
        priority = None
        if priority_match:
            priority = int(priority_match.group(1))
            # 移除优先级部分
            condition2 = re.sub(r'优先级\d+[：:]', '', condition2)
        
        # 使用与财富规则类似的转换逻辑
        return cls._convert_wealth_condition('十神', condition2)
    
    @staticmethod
    def _pillar_name_to_key(pillar_name: str) -> str:
        """将柱名称转换为key"""
        mapping = {
            '年柱': 'year',
            '月柱': 'month',
            '日柱': 'day',
            '日支': 'day',
            '时柱': 'hour'
        }
        return mapping.get(pillar_name, pillar_name)
    
    @classmethod
    def convert_rule(cls, rule: Dict[str, Any], rule_type: str) -> Dict[str, Any]:
        """
        转换单条规则
        
        Args:
            rule: JSON规则数据
            rule_type: 规则类型（财富/婚配/性格/总评/身体/十神命格）
            
        Returns:
            数据库规则格式
        """
        rule_id = rule.get('ID')
        condition1 = rule.get('筛选条件1', '')
        condition2 = rule.get('筛选条件2', '')
        gender = rule.get('性别', '无论男女')
        result = rule.get('结果', '')
        
        # 转换条件
        conditions = cls.convert_condition_to_json(condition1, condition2, rule_type)
        
        # 添加性别条件（如果有）
        if gender != '无论男女':
            gender_value = cls.GENDER_MAPPING.get(gender)
            if gender_value:
                if isinstance(conditions, dict) and 'all' in conditions:
                    conditions['all'].append({'gender': gender_value})
                elif isinstance(conditions, dict):
                    conditions = {'all': [conditions, {'gender': gender_value}]}
                else:
                    conditions = {'gender': gender_value}
        
        # 构建数据库规则
        db_rule = {
            'rule_code': f'FORMULA_{rule_id}',
            'rule_name': f'{rule_type}规则-{rule_id}',
            'rule_type': cls.TYPE_MAPPING.get(rule_type, rule_type.lower()),
            'priority': 100,  # 默认优先级，可以根据需要调整
            'conditions': conditions,
            'content': {
                'type': 'text',
                'text': result
            },
            'enabled': True,
            # ✅ 保存原始条件信息到description字段（JSON格式）
            'description': json.dumps({
                '筛选条件1': condition1,
                '筛选条件2': condition2,
                '性别': gender,
                '原始描述': f'从FormulaRuleService迁移的{rule_type}规则'
            }, ensure_ascii=False)
        }
        
        return db_rule


def migrate_rules(test_mode=False, test_count=10):
    """
    执行规则迁移
    
    Args:
        test_mode: 是否为测试模式（只转换少量规则）
        test_count: 测试模式下每个类型转换的规则数量
    """
    print("=" * 60)
    if test_mode:
        print(f"开始测试迁移FormulaRuleService规则到数据库（每个类型 {test_count} 条）")
    else:
        print("开始迁移FormulaRuleService规则到数据库")
    print("=" * 60)
    
    # 1. 加载JSON规则
    json_file = os.path.join(project_root, 'docs', '2025.11.20算法公式.json')
    if not os.path.exists(json_file):
        print(f"❌ 错误：找不到规则文件 {json_file}")
        return False
    
    with open(json_file, 'r', encoding='utf-8') as f:
        rules_data = json.load(f)
    
    print(f"✓ 加载JSON规则文件成功")
    
    # 2. 连接数据库
    try:
        from server.db.mysql_connector import get_db_connection
        db = get_db_connection()
        print(f"✓ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    # 3. 转换并导入规则
    converter = FormulaRuleConverter()
    total_count = 0
    success_count = 0
    error_count = 0
    
    for sheet_name, sheet_data in rules_data.items():
        if sheet_name == 'headers' or not isinstance(sheet_data, dict):
            continue
        
        rule_type = sheet_name
        rows = sheet_data.get('rows', [])
        
        # 测试模式：只处理前N条规则
        if test_mode:
            rows = rows[:test_count]
            print(f"\n处理规则类型: {rule_type} (测试模式: {len(rows)}/{sheet_data.get('count', len(rows))} 条)")
        else:
            print(f"\n处理规则类型: {rule_type} ({len(rows)} 条)")
        
        for rule in rows:
            total_count += 1
            try:
                # 转换规则
                db_rule = converter.convert_rule(rule, rule_type)
                
                # 插入数据库
                sql = """
                    INSERT INTO bazi_rules 
                    (rule_code, rule_name, rule_type, priority, conditions, content, enabled, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    rule_name = VALUES(rule_name),
                    rule_type = VALUES(rule_type),
                    priority = VALUES(priority),
                    conditions = VALUES(conditions),
                    content = VALUES(content),
                    description = VALUES(description)
                """
                
                db.execute_update(
                    sql,
                    (
                        db_rule['rule_code'],
                        db_rule['rule_name'],
                        db_rule['rule_type'],
                        db_rule['priority'],
                        json.dumps(db_rule['conditions'], ensure_ascii=False),
                        json.dumps(db_rule['content'], ensure_ascii=False),
                        db_rule['enabled'],
                        db_rule['description']
                    )
                )
                
                success_count += 1
                if success_count % 50 == 0:
                    print(f"  已处理 {success_count} 条规则...")
                    
            except Exception as e:
                error_count += 1
                rule_id = rule.get('ID', 'unknown')
                print(f"  ⚠ 规则 {rule_id} 转换失败: {e}")
                continue
    
    # 4. 更新版本号
    try:
        db.execute_update(
            "UPDATE rule_version SET rule_version = rule_version + 1 WHERE id = 1"
        )
        print(f"\n✓ 规则版本号已更新")
    except Exception as e:
        print(f"⚠ 更新版本号失败: {e}")
    
    # 5. 输出统计
    print("\n" + "=" * 60)
    print("迁移完成")
    print("=" * 60)
    print(f"总计: {total_count} 条规则")
    print(f"成功: {success_count} 条")
    print(f"失败: {error_count} 条")
    print("=" * 60)
    
    return error_count == 0


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='迁移FormulaRuleService规则到数据库')
    parser.add_argument('--test', action='store_true', help='测试模式（每个类型只转换10条规则）')
    parser.add_argument('--test-count', type=int, default=10, help='测试模式下每个类型转换的规则数量（默认10）')
    args = parser.parse_args()
    
    success = migrate_rules(test_mode=args.test, test_count=args.test_count)
    sys.exit(0 if success else 1)


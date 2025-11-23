#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的规则条件匹配器 - 支持复杂条件配置
支持：年柱、月柱、日柱、时柱、四柱神煞、组合条件等
"""

from collections import Counter
from typing import Dict, List, Any, Optional, Tuple

from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from src.data.relations import (
    STEM_HE,
    BRANCH_LIUHE,
    BRANCH_CHONG,
    BRANCH_XING,
    BRANCH_HAI,
    BRANCH_PO,
    BRANCH_SANHE_GROUPS,
    BRANCH_SANHUI_GROUPS,
)
PILLAR_NAMES = ["year", "month", "day", "hour"]
BRANCH_SEQUENCE = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
YANG_STEMS = {"甲", "丙", "戊", "庚", "壬"}
YIN_STEMS = {"乙", "丁", "己", "辛", "癸"}

ELEMENT_PRODUCES = {
    '木': '火',
    '火': '土',
    '土': '金',
    '金': '水',
    '水': '木'
}

ELEMENT_CONTROLS = {
    '木': '土',
    '火': '金',
    '土': '水',
    '金': '木',
    '水': '火'
}


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

class EnhancedRuleCondition:
    """增强的规则条件匹配器"""
    
    @staticmethod
    def match(condition: Dict, bazi_data: Dict) -> bool:
        """
        匹配增强条件
        
        支持的条件格式：
        1. 单柱条件：{"year_pillar": "甲子"}
        2. 四柱神煞：{"deities_in_any_pillar": ["天乙贵人"]}
        3. 特定柱神煞：{"deities_in_year": ["天乙贵人"]}
        4. 组合条件：{"all": [...], "any": [...]}
        
        Args:
            condition: 条件字典
            bazi_data: 八字数据字典
            
        Returns:
            bool: 是否匹配
        """
        if not condition:
            return True
        
        # 验证 bazi_data 的数据结构
        if not isinstance(bazi_data, dict):
            raise TypeError(f"bazi_data 必须是字典类型，但实际是: {type(bazi_data)}")
        
        # 确保关键字段是字典类型
        details = bazi_data.get('details', {})
        if not isinstance(details, dict):
            # 如果 details 不是字典，尝试修复或抛出错误
            raise TypeError(f"bazi_data['details'] 必须是字典类型，但实际是: {type(details)}, 值: {repr(details)[:100]}")
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        if not isinstance(bazi_pillars, dict):
            raise TypeError(f"bazi_data['bazi_pillars'] 必须是字典类型，但实际是: {type(bazi_pillars)}, 值: {repr(bazi_pillars)[:100]}")
        
        # 确保 details 中的每个柱也是字典类型
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_detail = details.get(pillar_type)
            if pillar_detail is not None and not isinstance(pillar_detail, dict):
                raise TypeError(f"bazi_data['details']['{pillar_type}'] 必须是字典类型，但实际是: {type(pillar_detail)}, 值: {repr(pillar_detail)[:100]}")
        
        for key, value in condition.items():
            if key == "all":
                # 所有条件都必须满足
                return all(EnhancedRuleCondition.match(c, bazi_data) for c in value)
            elif key == "any":
                # 任一条件满足即可
                return any(EnhancedRuleCondition.match(c, bazi_data) for c in value)
            elif key == "not":
                # 条件不满足
                return not EnhancedRuleCondition.match(value, bazi_data)
            
            # ========== 四柱条件 ==========
            elif key == "year_pillar":
                # 支持通配符 "*" 表示匹配任意值
                if value == "*":
                    return True
                year_stem = bazi_data.get('bazi_pillars', {}).get('year', {}).get('stem', '')
                year_branch = bazi_data.get('bazi_pillars', {}).get('year', {}).get('branch', '')
                year_pillar = f"{year_stem}{year_branch}"
                if isinstance(value, list):
                    return year_pillar in value
                return year_pillar == value
            
            elif key == "month_pillar":
                # 支持通配符 "*" 表示匹配任意值
                if value == "*":
                    return True
                month_stem = bazi_data.get('bazi_pillars', {}).get('month', {}).get('stem', '')
                month_branch = bazi_data.get('bazi_pillars', {}).get('month', {}).get('branch', '')
                month_pillar = f"{month_stem}{month_branch}"
                if isinstance(value, list):
                    return month_pillar in value
                return month_pillar == value
            
            elif key == "day_pillar" or key == "rizhu":
                # 支持通配符 "*" 表示匹配任意值
                if value == "*":
                    return True
                day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
                day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
                day_pillar = f"{day_stem}{day_branch}"
                if isinstance(value, list):
                    return day_pillar in value
                return day_pillar == value
            
            elif key == "hour_pillar":
                # 支持通配符 "*" 表示匹配任意值
                if value == "*":
                    return True
                hour_stem = bazi_data.get('bazi_pillars', {}).get('hour', {}).get('stem', '')
                hour_branch = bazi_data.get('bazi_pillars', {}).get('hour', {}).get('branch', '')
                hour_pillar = f"{hour_stem}{hour_branch}"
                if isinstance(value, list):
                    return hour_pillar in value
                return hour_pillar == value
            
            # ========== 四柱神煞条件 ==========
            elif key == "deities_in_any_pillar":
                """四柱中任意一柱存在指定神煞"""
                all_deities = []
                for pillar_type in ['year', 'month', 'day', 'hour']:
                    deities = bazi_data.get('details', {}).get(pillar_type, {}).get('deities', [])
                    if isinstance(deities, list):
                        all_deities.extend(deities)
                    elif deities:
                        all_deities.append(deities)
                if isinstance(value, list):
                    return any(d in all_deities for d in value)
                return value in all_deities
            
            elif key == "deities_in_all_pillars":
                """四柱中都存在指定神煞"""
                if isinstance(value, list):
                    return all(
                        any(d in bazi_data.get('details', {}).get(pillar_type, {}).get('deities', [])
                            for pillar_type in ['year', 'month', 'day', 'hour'])
                        for d in value
                    )
                return all(
                    value in bazi_data.get('details', {}).get(pillar_type, {}).get('deities', [])
                    for pillar_type in ['year', 'month', 'day', 'hour']
                )
            
            elif key == "deities_in_year":
                """年柱神煞"""
                year_deities = bazi_data.get('details', {}).get('year', {}).get('deities', [])
                if not isinstance(year_deities, list):
                    year_deities = [year_deities] if year_deities else []
                if isinstance(value, list):
                    return any(d in year_deities for d in value)
                return value in year_deities
            
            elif key == "deities_in_month":
                """月柱神煞"""
                month_deities = bazi_data.get('details', {}).get('month', {}).get('deities', [])
                if not isinstance(month_deities, list):
                    month_deities = [month_deities] if month_deities else []
                if isinstance(value, list):
                    return any(d in month_deities for d in value)
                return value in month_deities
            
            elif key == "deities_in_day":
                """日柱神煞"""
                day_deities = bazi_data.get('details', {}).get('day', {}).get('deities', [])
                if not isinstance(day_deities, list):
                    day_deities = [day_deities] if day_deities else []
                if isinstance(value, list):
                    return any(d in day_deities for d in value)
                return value in day_deities
            
            elif key == "deities_in_hour":
                """时柱神煞"""
                hour_deities = bazi_data.get('details', {}).get('hour', {}).get('deities', [])
                if not isinstance(hour_deities, list):
                    hour_deities = [hour_deities] if hour_deities else []
                if isinstance(value, list):
                    return any(d in hour_deities for d in value)
                return value in hour_deities
            
            # ========== 星运条件 ==========
            elif key == "star_fortune_in_year":
                star_fortune = bazi_data.get('details', {}).get('year', {}).get('star_fortune', '')
                if isinstance(value, list):
                    return star_fortune in value
                return star_fortune == value
            
            elif key == "star_fortune_in_month":
                star_fortune = bazi_data.get('details', {}).get('month', {}).get('star_fortune', '')
                if isinstance(value, list):
                    return star_fortune in value
                return star_fortune == value
            
            elif key == "star_fortune_in_day":
                star_fortune = bazi_data.get('details', {}).get('day', {}).get('star_fortune', '')
                if isinstance(value, list):
                    return star_fortune in value
                return star_fortune == value
            
            elif key == "star_fortune_in_hour":
                star_fortune = bazi_data.get('details', {}).get('hour', {}).get('star_fortune', '')
                if isinstance(value, list):
                    return star_fortune in value
                return star_fortune == value
            
            # ========== 主星条件 ==========
            elif key == "main_star_in_year":
                main_star = bazi_data.get('details', {}).get('year', {}).get('main_star', '')
                if isinstance(value, list):
                    return main_star in value
                return main_star == value
            
            elif key == "main_star_in_day":
                main_star = bazi_data.get('details', {}).get('day', {}).get('main_star', '')
                if isinstance(value, list):
                    return main_star in value
                return main_star == value

            elif key == "main_star_in_pillar":
                pillar = value.get('pillar') if isinstance(value, dict) else None
                if not pillar:
                    return False
                main_star = bazi_data.get('details', {}).get(pillar, {}).get('main_star', '')
                expected = value.get('in') or value.get('eq')
                if expected is None:
                    return False
                if isinstance(expected, list):
                    return main_star in expected
                return main_star == expected
            
            # ========== 副星（藏干十神）条件 ==========
            elif key.startswith("hidden_stars_in_"):
                # 支持 hidden_stars_in_year, hidden_stars_in_month, hidden_stars_in_day, hidden_stars_in_hour
                pillar = key.replace("hidden_stars_in_", "")
                if pillar not in ['year', 'month', 'day', 'hour']:
                    return False
                
                hidden_stars = bazi_data.get('details', {}).get(pillar, {}).get('hidden_stars', [])
                if not isinstance(hidden_stars, list):
                    hidden_stars = [hidden_stars] if hidden_stars else []
                
                if isinstance(value, list):
                    # 检查是否包含任一指定的十神
                    return any(star in hidden_stars for star in value)
                return value in hidden_stars
            
            # ========== 十神统计条件 ==========
            elif key in ["ten_gods_main", "ten_gods_sub", "ten_gods_total"]:
                stats_key_map = {
                    "ten_gods_main": "main",
                    "ten_gods_sub": "sub",
                    "ten_gods_total": "totals"
                }
                ten_gods_stats = bazi_data.get('ten_gods_stats', {})
                # 确保 ten_gods_stats 是字典类型，如果是字符串则反序列化
                if isinstance(ten_gods_stats, str):
                    try:
                        import json
                        ten_gods_stats = json.loads(ten_gods_stats)
                    except (json.JSONDecodeError, TypeError):
                        print(f"⚠️  ten_gods_stats 是字符串但无法解析为JSON: {repr(ten_gods_stats)[:100]}", flush=True)
                        ten_gods_stats = {}
                elif not isinstance(ten_gods_stats, dict):
                    print(f"⚠️  ten_gods_stats 不是字典类型: {type(ten_gods_stats)}, 值: {repr(ten_gods_stats)[:100]}", flush=True)
                    ten_gods_stats = {}
                
                stats = ten_gods_stats.get(stats_key_map[key], {})
                # 确保 stats 也是字典类型，如果是字符串则反序列化
                if isinstance(stats, str):
                    try:
                        import json
                        stats = json.loads(stats)
                    except (json.JSONDecodeError, TypeError):
                        print(f"⚠️  stats ({stats_key_map[key]}) 是字符串但无法解析为JSON: {repr(stats)[:100]}", flush=True)
                        stats = {}
                elif not isinstance(stats, dict):
                    print(f"⚠️  stats ({stats_key_map[key]}) 不是字典类型: {type(stats)}, 值: {repr(stats)[:100]}", flush=True)
                    stats = {}
                
                return EnhancedRuleCondition._match_ten_gods_stats(stats, value)

            elif key == "ten_gods_injured":
                return EnhancedRuleCondition._match_ten_gods_injured(bazi_data, value)

            # ========== 旺衰条件 ==========
            elif key == "wangshuai":
                """旺衰条件匹配"""
                try:
                    from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
                    
                    basic_info = bazi_data.get('basic_info', {})
                    solar_date = basic_info.get('solar_date', '')
                    solar_time = basic_info.get('solar_time', '')
                    gender = basic_info.get('gender', 'male')
                    
                    if not solar_date or not solar_time:
                        return False
                    
                    wangshuai_result = WangShuaiAnalyzer.analyze(solar_date, solar_time, gender)
                    wangshuai_status = wangshuai_result.get('wangshuai', '')
                    
                    if isinstance(value, list):
                        return wangshuai_status in value
                    return wangshuai_status == value
                except Exception as e:
                    print(f"⚠️  旺衰条件匹配失败: {e}", flush=True)
                    return False
            
            # ========== 季节条件 ==========
            elif key == "season":
                """季节条件匹配"""
                try:
                    from datetime import datetime
                    from lunar_python import Solar
                    
                    basic_info = bazi_data.get('basic_info', {})
                    solar_date = basic_info.get('solar_date', '')
                    
                    if not solar_date:
                        return False
                    
                    # 解析日期
                    try:
                        dt = datetime.strptime(solar_date, '%Y-%m-%d')
                        solar = Solar.fromYmd(dt.year, dt.month, dt.day)
                        lunar = solar.getLunar()
                        
                        # 获取当前节气
                        current_jieqi = lunar.getPrevJie()
                        jieqi_name = current_jieqi.getName()
                        
                        # 根据节气判断季节
                        spring_jieqi = ['立春', '雨水', '惊蛰', '春分', '清明', '谷雨']
                        summer_jieqi = ['立夏', '小满', '芒种', '夏至', '小暑', '大暑']
                        autumn_jieqi = ['立秋', '处暑', '白露', '秋分', '寒露', '霜降']
                        winter_jieqi = ['立冬', '小雪', '大雪', '冬至', '小寒', '大寒']
                        
                        if jieqi_name in spring_jieqi:
                            actual_season = '春季'
                        elif jieqi_name in summer_jieqi:
                            actual_season = '夏季'
                        elif jieqi_name in autumn_jieqi:
                            actual_season = '秋季'
                        elif jieqi_name in winter_jieqi:
                            actual_season = '冬季'
                        else:
                            actual_season = ''
                        
                        if isinstance(value, list):
                            return actual_season in value
                        return actual_season == value
                    except Exception as e:
                        print(f"⚠️  季节判断失败: {e}", flush=True)
                        return False
                except Exception as e:
                    print(f"⚠️  季节条件匹配失败: {e}", flush=True)
                    return False
            
            # ========== 时辰范围条件 ==========
            elif key == "hour_branch_range":
                """时辰范围条件匹配"""
                hour_branch = bazi_data.get('bazi_pillars', {}).get('hour', {}).get('branch', '')
                if isinstance(value, list):
                    return hour_branch in value
                return hour_branch == value
            
            # ========== 地支冲关系条件 ==========
            elif key == "branch_chong":
                """地支冲关系条件匹配"""
                if not isinstance(value, list) or len(value) != 2:
                    return False
                
                branch1, branch2 = value[0], value[1]
                
                # 检查四柱中是否存在这两个地支的冲关系
                relationships = bazi_data.get('relationships', {})
                if isinstance(relationships, str):
                    try:
                        import json
                        relationships = json.loads(relationships)
                    except:
                        relationships = {}
                
                branch_relations = relationships.get('branch_relations', {})
                if isinstance(branch_relations, str):
                    try:
                        import json
                        branch_relations = json.loads(branch_relations)
                    except:
                        branch_relations = {}
                
                # 检查是否有冲关系
                for pillar_type in ['year', 'month', 'day', 'hour']:
                    pillar_branch = bazi_data.get('bazi_pillars', {}).get(pillar_type, {}).get('branch', '')
                    if pillar_branch == branch1:
                        # 检查其他柱是否有branch2，且存在冲关系
                        for other_pillar in ['year', 'month', 'day', 'hour']:
                            if other_pillar == pillar_type:
                                continue
                            other_branch = bazi_data.get('bazi_pillars', {}).get(other_pillar, {}).get('branch', '')
                            if other_branch == branch2:
                                # 检查是否有冲关系
                                chong_key = f"{pillar_type}_{other_pillar}_chong"
                                if branch_relations.get(chong_key) or branch_relations.get(f"{other_pillar}_{pillar_type}_chong"):
                                    return True
                
                return False
            
            # ========== 不受刑冲条件 ==========
            elif key == "no_chong_xing":
                """不受刑冲条件匹配"""
                if not value:
                    return False
                
                relationships = bazi_data.get('relationships', {})
                if isinstance(relationships, str):
                    try:
                        import json
                        relationships = json.loads(relationships)
                    except:
                        relationships = {}
                
                branch_relations = relationships.get('branch_relations', {})
                if isinstance(branch_relations, str):
                    try:
                        import json
                        branch_relations = json.loads(branch_relations)
                    except:
                        branch_relations = {}
                
                # 检查是否有刑冲关系
                for key, val in branch_relations.items():
                    if 'chong' in key.lower() or 'xing' in key.lower():
                        if val:
                            return False  # 有刑冲，不满足条件
                
                return True  # 没有刑冲，满足条件
            
            # ========== 五行 / 地支条件 ==========
            elif key == "day_branch_in":
                day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
                if isinstance(value, list):
                    return day_branch in value
                return day_branch == value

            elif key == "day_branch_equals":
                day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
                targets = value if isinstance(value, list) else [value]
                for target in targets:
                    target_branch = bazi_data.get('bazi_pillars', {}).get(target, {}).get('branch', '')
                    if day_branch == target_branch:
                        return True
                return False

            elif key == "pillar_element":
                if not isinstance(value, dict):
                    return False
                pillar = value.get('pillar')
                part = value.get('part', 'branch')
                target_in = value.get('in')
                target_eq = value.get('eq')
                
                # 特殊处理纳音（nayin）部分
                if part == 'nayin':
                    # 从 details 中获取纳音，然后转换为纳音五行
                    details = bazi_data.get('details', {})
                    # 确保 details 是字典类型
                    if not isinstance(details, dict):
                        if isinstance(details, str):
                            try:
                                import json
                                details = json.loads(details)
                            except (json.JSONDecodeError, TypeError):
                                details = {}
                        else:
                            details = {}
                    
                    pillar_details = details.get(pillar, {})
                    # 确保 pillar_details 是字典类型
                    if not isinstance(pillar_details, dict):
                        if isinstance(pillar_details, str):
                            try:
                                import json
                                pillar_details = json.loads(pillar_details)
                            except (json.JSONDecodeError, TypeError):
                                pillar_details = {}
                        else:
                            pillar_details = {}
                    
                    nayin = pillar_details.get('nayin', '') if isinstance(pillar_details, dict) else ''
                    
                    # 纳音五行映射表
                    nayin_element_map = {
                        '海中金': '金', '炉中火': '火', '大林木': '木', '路旁土': '土', '剑锋金': '金',
                        '山头火': '火', '涧下水': '水', '城头土': '土', '白蜡金': '金', '杨柳木': '木',
                        '泉中水': '水', '屋上土': '土', '霹雳火': '火', '松柏木': '木', '长流水': '水',
                        '砂中金': '金', '山下火': '火', '平地木': '木', '壁上土': '土', '金箔金': '金',
                        '覆灯火': '火', '天河水': '水', '大驿土': '土', '钗钏金': '金', '桑柘木': '木',
                        '大溪水': '水', '沙中土': '土', '天上火': '火', '石榴木': '木', '大海水': '水'
                    }
                    element_val = nayin_element_map.get(nayin, '')
                else:
                    # 其他部分（stem_element, branch_element）从 elements 中获取
                    elements_map = bazi_data.get('elements', {})
                    if not isinstance(elements_map, dict):
                        # 如果 elements_map 是字符串，尝试反序列化
                        if isinstance(elements_map, str):
                            try:
                                import json
                                elements_map = json.loads(elements_map)
                            except (json.JSONDecodeError, TypeError):
                                elements_map = {}
                        else:
                            elements_map = {}
                    
                    pillar_info = elements_map.get(pillar, {})
                    # 确保 pillar_info 是字典类型
                    if not isinstance(pillar_info, dict):
                        if isinstance(pillar_info, str):
                            try:
                                import json
                                pillar_info = json.loads(pillar_info)
                            except (json.JSONDecodeError, TypeError):
                                pillar_info = {}
                        else:
                            pillar_info = {}
                    
                    element_key = f"{part}_element"
                    element_val = pillar_info.get(element_key) if isinstance(pillar_info, dict) else None
                
                if target_in is not None:
                    if not isinstance(target_in, list):
                        target_in = [target_in]
                    return element_val in target_in
                if target_eq is not None:
                    if isinstance(target_eq, list):
                        return element_val in target_eq
                    return element_val == target_eq
                return False

            elif key == "day_branch_element_in":
                elements_map = bazi_data.get('elements', {})
                # 确保 elements_map 是字典类型
                if not isinstance(elements_map, dict):
                    if isinstance(elements_map, str):
                        try:
                            import json
                            elements_map = json.loads(elements_map)
                        except (json.JSONDecodeError, TypeError):
                            elements_map = {}
                    else:
                        elements_map = {}
                
                day_info = elements_map.get('day', {})
                # 确保 day_info 是字典类型
                if not isinstance(day_info, dict):
                    if isinstance(day_info, str):
                        try:
                            import json
                            day_info = json.loads(day_info)
                        except (json.JSONDecodeError, TypeError):
                            day_info = {}
                    else:
                        day_info = {}
                
                day_element = day_info.get('branch_element') if isinstance(day_info, dict) else None
                values = value if isinstance(value, list) else [value]
                return day_element in values if day_element else False

            elif key == "pillar_in":
                pillar = value.get('pillar')
                part = value.get('part', 'branch')
                expected_values = ensure_list(value.get('values'))
                actual = EnhancedRuleCondition._get_pillar_part_value(bazi_data, pillar, part)
                if isinstance(actual, list):
                    return any(item in expected_values for item in actual)
                return actual in expected_values

            elif key == "pillar_equals":
                pillar = value.get('pillar')
                values = ensure_list(value.get('values'))
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                if not isinstance(bazi_pillars, dict):
                    return False
                pillar_info = bazi_pillars.get(pillar, {})
                # 确保 pillar_info 是字典类型
                if not isinstance(pillar_info, dict):
                    pillar_info = {}
                pillar_text = f"{pillar_info.get('stem', '')}{pillar_info.get('branch', '')}"
                return pillar_text in values

            elif key == "stems_count":
                stems = EnhancedRuleCondition._collect_stems(bazi_data)
                return EnhancedRuleCondition._match_collection_count(stems, value)

            elif key == "branches_count":
                branches = EnhancedRuleCondition._collect_branches(bazi_data)
                return EnhancedRuleCondition._match_collection_count(branches, value)

            elif key == "branch_group":
                return EnhancedRuleCondition._match_branch_group(bazi_data, value)
            elif key == "branch_offset":
                return EnhancedRuleCondition._match_branch_offset(bazi_data, value)
            elif key == "stems_parity":
                return EnhancedRuleCondition._match_stems_parity(bazi_data, value)
            elif key == "branch_adjacent":
                return EnhancedRuleCondition._match_branch_adjacent(bazi_data, value)
            elif key == "branches_unique":
                return EnhancedRuleCondition._match_branches_unique(bazi_data, value)
            elif key == "stems_unique":
                return EnhancedRuleCondition._match_stems_unique(bazi_data, value)

            elif key == "pillar_relation":
                return EnhancedRuleCondition._match_pillar_relation(bazi_data, value)
            elif key == "liunian_relation":
                return EnhancedRuleCondition._match_liunian_relation(bazi_data, value)
            
            elif key == "dayun_branch_equals":
                """大运地支与指定柱的地支相同"""
                fortune = bazi_data.get('fortune', {})
                current_dayun = fortune.get('current_dayun', {})
                dayun_branch = current_dayun.get('branch', '')
                
                if not dayun_branch:
                    return False
                
                target_pillar = value.get('target_pillar', 'day')
                target_part = value.get('target_part', 'branch')
                
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                target_pillar_data = bazi_pillars.get(target_pillar, {})
                target_value = target_pillar_data.get(target_part, '')
                
                return dayun_branch == target_value
            
            elif key == "liunian_combines_pillar":
                """流年与指定柱的天干合地支合"""
                liunian = EnhancedRuleCondition._get_current_liunian(bazi_data)
                if not liunian:
                    return False
                
                liunian_stem = liunian.get('stem', '')
                liunian_branch = liunian.get('branch', '')
                
                if not liunian_stem or not liunian_branch:
                    return False
                
                target_pillar = value.get('target_pillar', 'month')
                stem_relation = value.get('stem_relation', 'he')
                branch_relation = value.get('branch_relation', 'liuhe')
                
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                target_pillar_data = bazi_pillars.get(target_pillar, {})
                target_stem = target_pillar_data.get('stem', '')
                target_branch = target_pillar_data.get('branch', '')
                
                # 检查天干合
                stem_match = False
                if stem_relation == 'he':
                    stem_match = STEM_HE.get(liunian_stem) == target_stem or STEM_HE.get(target_stem) == liunian_stem
                
                # 检查地支合
                branch_match = False
                if branch_relation == 'liuhe':
                    branch_match = BRANCH_LIUHE.get(liunian_branch) == target_branch or BRANCH_LIUHE.get(target_branch) == liunian_branch
                
                return stem_match and branch_match
            
            elif key == "liunian_ganzhi_equals":
                """流年干支等于指定值"""
                liunian = EnhancedRuleCondition._get_current_liunian(bazi_data)
                if not liunian:
                    return False
                
                liunian_stem = liunian.get('stem', '')
                liunian_branch = liunian.get('branch', '')
                liunian_ganzhi = f"{liunian_stem}{liunian_branch}"
                
                # 支持直接传入字符串或字典
                if isinstance(value, str):
                    target_ganzhi = value
                elif isinstance(value, dict):
                    target_ganzhi = value.get('ganzhi', '')
                else:
                    target_ganzhi = str(value)
                
                return liunian_ganzhi == target_ganzhi
            
            elif key == "suiyun_binglin_kongwang":
                """岁运并临且是空亡"""
                fortune = bazi_data.get('fortune', {})
                current_dayun = fortune.get('current_dayun', {})
                current_liunian = fortune.get('current_liunian', {})
                
                if not current_dayun or not current_liunian:
                    return False
                
                # 检查岁运并临（大运和流年干支相同）
                dayun_stem = current_dayun.get('stem', '')
                dayun_branch = current_dayun.get('branch', '')
                liunian_stem = current_liunian.get('stem', '')
                liunian_branch = current_liunian.get('branch', '')
                
                if dayun_stem != liunian_stem or dayun_branch != liunian_branch:
                    return False
                
                # 检查是否是目标柱的空亡
                target_pillar = value.get('target_pillar', 'day') if isinstance(value, dict) else 'day'
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                target_pillar_data = bazi_pillars.get(target_pillar, {})
                target_stem = target_pillar_data.get('stem', '')
                target_branch = target_pillar_data.get('branch', '')
                target_ganzhi = f"{target_stem}{target_branch}"
                
                # 获取空亡地支
                details = bazi_data.get('details', {})
                target_details = details.get(target_pillar, {})
                kongwang = target_details.get('kongwang', '')
                
                # 检查并临的干支是否在空亡地支中
                if kongwang and (dayun_branch in kongwang or liunian_branch in kongwang):
                    return True
                
                return False
            
            elif key == "stems_chong":
                """天干四冲：甲庚、乙辛、丙壬、丁癸"""
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                stems = [
                    bazi_pillars.get('year', {}).get('stem', ''),
                    bazi_pillars.get('month', {}).get('stem', ''),
                    bazi_pillars.get('day', {}).get('stem', ''),
                    bazi_pillars.get('hour', {}).get('stem', '')
                ]
                
                # 天干四冲对：甲庚、乙辛、丙壬、丁癸
                chong_pairs = [
                    ('甲', '庚'), ('乙', '辛'), ('丙', '壬'), ('丁', '癸'),
                    ('庚', '甲'), ('辛', '乙'), ('壬', '丙'), ('癸', '丁')
                ]
                
                # 检查是否有任何一对相冲
                for pair in chong_pairs:
                    if pair[0] in stems and pair[1] in stems:
                        return True
                
                return False
            
            elif key == "stems_wuhe_pairs":
                """天干五合组数统计：甲己、乙庚、丙辛、丁壬、戊癸"""
                min_pairs = value.get('min_pairs', 1) if isinstance(value, dict) else 1
                
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                stems = [
                    bazi_pillars.get('year', {}).get('stem', ''),
                    bazi_pillars.get('month', {}).get('stem', ''),
                    bazi_pillars.get('day', {}).get('stem', ''),
                    bazi_pillars.get('hour', {}).get('stem', '')
                ]
                
                # 天干五合对：甲己、乙庚、丙辛、丁壬、戊癸
                wuhe_pairs = [
                    ('甲', '己'), ('乙', '庚'), ('丙', '辛'), ('丁', '壬'), ('戊', '癸'),
                    ('己', '甲'), ('庚', '乙'), ('辛', '丙'), ('壬', '丁'), ('癸', '戊')
                ]
                
                # 统计五合对的数量
                pair_count = 0
                for pair in wuhe_pairs:
                    if pair[0] in stems and pair[1] in stems:
                        pair_count += 1
                
                return pair_count >= min_pairs
            
            elif key == "ten_gods_main":
                """主星十神数量统计"""
                names = value.get('names', []) if isinstance(value, dict) else []
                eq = value.get('eq') if isinstance(value, dict) else None
                min_val = value.get('min') if isinstance(value, dict) else None
                max_val = value.get('max') if isinstance(value, dict) else None
                
                if not names:
                    return False
                
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                day_stem = bazi_pillars.get('day', {}).get('stem', '')
                
                if not day_stem:
                    return False
                
                from src.bazi_config.ten_gods_config import TenGodsCalculator
                calculator = TenGodsCalculator()
                
                # 统计主星十神数量（年、月、时柱的主星）
                counts = {}
                for pillar_name in ['year', 'month', 'hour']:
                    pillar_stem = bazi_pillars.get(pillar_name, {}).get('stem', '')
                    if pillar_stem:
                        main_star = calculator.get_stem_ten_god(day_stem, pillar_stem)
                        counts[main_star] = counts.get(main_star, 0) + 1
                
                # 检查每个指定的十神
                for ten_god in names:
                    count = counts.get(ten_god, 0)
                    if eq is not None and count != eq:
                        return False
                    if min_val is not None and count < min_val:
                        return False
                    if max_val is not None and count > max_val:
                        return False
                
                return True
            
            elif key == "branch_liuhe_sanhe_count":
                """六合与三合数量统计"""
                min_count = value.get('min', 0) if isinstance(value, dict) else 0
                
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                branches = [
                    bazi_pillars.get('year', {}).get('branch', ''),
                    bazi_pillars.get('month', {}).get('branch', ''),
                    bazi_pillars.get('day', {}).get('branch', ''),
                    bazi_pillars.get('hour', {}).get('branch', '')
                ]
                
                branch_set = set(branches)
                count = 0
                
                # 统计六合数量
                liuhe_pairs = [
                    ('子', '丑'), ('寅', '亥'), ('卯', '戌'), ('辰', '酉'),
                    ('巳', '申'), ('午', '未')
                ]
                for pair in liuhe_pairs:
                    if pair[0] in branch_set and pair[1] in branch_set:
                        count += 1
                
                # 统计三合数量
                for group in BRANCH_SANHE_GROUPS:
                    if branch_set.issuperset(group):
                        count += 1
                
                return count >= min_count
            
            elif key == "month_ten_gods_with_dayun_liunian":
                """月柱副星是特定十神，且大运或流年主星/副星也是这些十神"""
                ten_gods = value.get('ten_gods', []) if isinstance(value, dict) else []
                check_dayun = value.get('check_dayun', False) if isinstance(value, dict) else False
                check_liunian = value.get('check_liunian', False) if isinstance(value, dict) else False
                
                if not ten_gods:
                    return False
                
                # 检查月柱副星
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                day_stem = bazi_pillars.get('day', {}).get('stem', '')
                month_branch = bazi_pillars.get('month', {}).get('branch', '')
                
                # 获取月柱副星（地支藏干的十神）
                from src.bazi_config.ten_gods_config import TenGodsCalculator
                calculator = TenGodsCalculator()
                month_ten_gods = calculator.get_branch_ten_gods(day_stem, month_branch)
                
                # 检查月柱副星是否包含指定的十神
                month_has_ten_god = any(tg in month_ten_gods for tg in ten_gods)
                if not month_has_ten_god:
                    return False
                
                # 检查大运或流年
                fortune = bazi_data.get('fortune', {})
                
                if check_dayun:
                    current_dayun = fortune.get('current_dayun', {})
                    dayun_stem = current_dayun.get('stem', '')
                    dayun_branch = current_dayun.get('branch', '')
                    
                    if dayun_stem:
                        # 检查大运主星
                        dayun_main_star = calculator.get_stem_ten_god(day_stem, dayun_stem)
                        if dayun_main_star in ten_gods:
                            return True
                    
                    if dayun_branch:
                        # 检查大运副星
                        dayun_ten_gods = calculator.get_branch_ten_gods(day_stem, dayun_branch)
                        if any(tg in dayun_ten_gods for tg in ten_gods):
                            return True
                
                if check_liunian:
                    current_liunian = fortune.get('current_liunian', {})
                    liunian_stem = current_liunian.get('stem', '')
                    liunian_branch = current_liunian.get('branch', '')
                    
                    if liunian_stem:
                        # 检查流年主星
                        liunian_main_star = calculator.get_stem_ten_god(day_stem, liunian_stem)
                        if liunian_main_star in ten_gods:
                            return True
                    
                    if liunian_branch:
                        # 检查流年副星
                        liunian_ten_gods = calculator.get_branch_ten_gods(day_stem, liunian_branch)
                        if any(tg in liunian_ten_gods for tg in ten_gods):
                            return True
                
                return False
            elif key in ("liunian_deities", "liunian_deities_contains"):
                return EnhancedRuleCondition._match_liunian_deities(bazi_data, value)

            elif key == "element_total":
                counts = bazi_data.get('element_counts', {})
                return EnhancedRuleCondition._match_element_counts(counts, value)

            elif key == "element_relation":
                return EnhancedRuleCondition._match_element_relation(bazi_data, value)
            
            elif key == "ten_god_combines":
                return EnhancedRuleCondition._match_ten_god_combines(bazi_data, value)
            
            elif key == "lunar_month_in":
                """农历月份条件匹配"""
                basic_info = bazi_data.get('basic_info', {})
                lunar_date = basic_info.get('lunar_date', {})
                lunar_month = lunar_date.get('month', 0)
                
                # 处理闰月：负数表示闰月，需要转换为正数进行比较
                # 例如：-10 表示闰十月，应该匹配月份 10
                actual_month = abs(lunar_month)
                
                target_months = ensure_list(value.get('values', []))
                return actual_month in target_months
            
            elif key == "lunar_day_in":
                """农历日期条件匹配"""
                basic_info = bazi_data.get('basic_info', {})
                lunar_date = basic_info.get('lunar_date', {})
                lunar_day = lunar_date.get('day', 0)
                
                target_days = ensure_list(value.get('values', []))
                return lunar_day in target_days
            
            elif key in ("dayun_branch_in", "liunian_branch_in"):
                """大运/流年地支条件匹配"""
                fortune = bazi_data.get('fortune', {})
                
                if key == "dayun_branch_in":
                    # 大运地支
                    current_dayun = fortune.get('current_dayun', {})
                    dayun_branch = current_dayun.get('branch', '')
                    target_branches = ensure_list(value.get('values', []))
                    return dayun_branch in target_branches
                elif key == "liunian_branch_in":
                    # 流年地支
                    current_liunian = fortune.get('current_liunian', {})
                    liunian_branch = current_liunian.get('branch', '')
                    target_branches = ensure_list(value.get('values', []))
                    return liunian_branch in target_branches
                return False
            
            elif key == "nayin_count_in_pillars":
                """统计指定纳音在多个柱中出现的次数"""
                nayin_name = value.get('nayin_name', '')
                pillars = ensure_list(value.get('pillars', PILLAR_NAMES))
                min_count = value.get('min', 0)
                max_count = value.get('max')
                eq_count = value.get('eq')
                
                if not nayin_name:
                    return False
                
                # 统计纳音出现的次数
                count = 0
                details = bazi_data.get('details', {})
                
                for pillar in pillars:
                    pillar_details = details.get(pillar, {})
                    nayin = pillar_details.get('nayin', '')
                    if nayin == nayin_name:
                        count += 1
                
                # 检查数量条件
                if eq_count is not None:
                    return count == eq_count
                if max_count is not None and count > max_count:
                    return False
                if min_count is not None and count < min_count:
                    return False
                return True
            
            elif key == "deities_count":
                """统计神煞在四柱中出现的次数"""
                deity_name = value.get('name', '')
                min_count = value.get('min', 0)
                max_count = value.get('max')
                eq_count = value.get('eq')
                
                if not deity_name:
                    return False
                
                # 统计神煞出现的次数
                count = 0
                details = bazi_data.get('details', {})
                
                for pillar in PILLAR_NAMES:
                    pillar_details = details.get(pillar, {})
                    deities = pillar_details.get('deities', [])
                    if not isinstance(deities, list):
                        deities = [deities] if deities else []
                    if deity_name in deities:
                        count += 1
                
                # 检查数量条件
                if eq_count is not None:
                    return count == eq_count
                if max_count is not None and count > max_count:
                    return False
                if min_count is not None and count < min_count:
                    return False
                return True
            
            elif key == "branches_repeat_or_sanhui":
                """检查地支重复或三会局"""
                min_repeat = value.get('min_repeat', 3)
                check_sanhui = value.get('check_sanhui', False)
                
                bazi_pillars = bazi_data.get('bazi_pillars', {})
                branches = [
                    bazi_pillars.get('year', {}).get('branch', ''),
                    bazi_pillars.get('month', {}).get('branch', ''),
                    bazi_pillars.get('day', {}).get('branch', ''),
                    bazi_pillars.get('hour', {}).get('branch', '')
                ]
                
                # 检查是否有重复的地支
                from collections import Counter
                branch_counts = Counter(branches)
                max_repeat = max(branch_counts.values()) if branch_counts else 0
                if max_repeat >= min_repeat:
                    return True
                
                # 检查三会局
                if check_sanhui:
                    branch_set = set(branches)
                    for group in BRANCH_SANHUI_GROUPS:
                        if branch_set.issuperset(group):
                            return True
                
                return False
            
            # ========== 其他条件 ==========
            elif key == "gender":
                """性别条件，支持通配符 "*" 表示匹配任意值"""
                if value == "*" or value is None:
                    return True  # 不限制性别
                gender = bazi_data.get('basic_info', {}).get('gender', '')
                return gender == value or (gender == 'male' and value == '男') or (gender == 'female' and value == '女')
            
            # 可以继续扩展更多条件...
        
        return False

    @staticmethod
    def _match_ten_gods_stats(stats_map: Dict[str, Dict[str, Any]], spec: Dict[str, Any]) -> bool:
        """
        匹配十神统计条件
        spec 格式示例：
        {
            "names": ["正财", "偏财"],
            "min": 2,
            "max": 4,
            "eq": null,
            "pillars": ["year", "month"]
        }
        
        注意：stats_map 必须是字典类型，如果不是则返回 False
        """
        # 确保 stats_map 是字典类型
        if not isinstance(stats_map, dict):
            print(f"⚠️  _match_ten_gods_stats: stats_map 不是字典类型: {type(stats_map)}, 值: {repr(stats_map)[:100]}", flush=True)
            return False
        
        # 确保 spec 是字典类型
        if not isinstance(spec, dict):
            print(f"⚠️  _match_ten_gods_stats: spec 不是字典类型: {type(spec)}, 值: {repr(spec)[:100]}", flush=True)
            return False
        
        if spec is None:
            return True

        names = spec.get("names")
        if not names:
            # 未指定 names 时，以全部十神为对象
            names = list(stats_map.keys())

        pillars = spec.get("pillars")

        total_count = 0
        for name in names:
            entry = stats_map.get(name)
            # 如果 entry 是 None，说明这个十神不存在，跳过（不报错，因为这是正常的）
            if entry is None:
                continue
            # 确保 entry 是字典类型
            if not isinstance(entry, dict):
                # 如果是字符串，尝试反序列化
                if isinstance(entry, str):
                    try:
                        import json
                        entry = json.loads(entry)
                        # 更新 stats_map 中的值
                        stats_map[name] = entry
                    except (json.JSONDecodeError, TypeError):
                        print(f"⚠️  _match_ten_gods_stats: entry ({name}) 是字符串但无法解析为JSON: {repr(entry)[:100]}", flush=True)
                        continue
                else:
                    print(f"⚠️  _match_ten_gods_stats: entry ({name}) 不是字典类型: {type(entry)}, 值: {repr(entry)[:100]}", flush=True)
                    continue
            
            # 再次检查 entry 是否是字典（反序列化后）
            if not isinstance(entry, dict):
                continue

            if pillars:
                pillar_counts = entry.get("pillars", {})
                if not isinstance(pillar_counts, dict):
                    print(f"⚠️  _match_ten_gods_stats: pillar_counts 不是字典类型: {type(pillar_counts)}", flush=True)
                    pillar_counts = {}
                for pillar in pillars:
                    total_count += pillar_counts.get(pillar, 0)
            else:
                total_count += entry.get("count", 0)

        eq = spec.get("eq")
        if eq is not None:
            return total_count == eq

        min_value = spec.get("min")
        if min_value is not None and total_count < min_value:
            return False

        max_value = spec.get("max")
        if max_value is not None and total_count > max_value:
            return False

        return True

    @staticmethod
    def _match_ten_god_combines(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return False

        god = spec.get("god")
        if not god:
            return False

        source = spec.get("source", "main").lower()
        pillars = ensure_list(spec.get("pillars")) or ["year", "month", "day", "hour"]
        target_part = spec.get("target_part", "stem")
        relation = spec.get("relation")
        if not relation:
            relation = "he" if target_part == "stem" else "liuhe"

        target_pillars = ensure_list(spec.get("target_pillars"))
        if not target_pillars:
            target_pillar = spec.get("target_pillar", "day")
            if target_pillar:
                target_pillars = [target_pillar]
        if not target_pillars:
            return False

        details = bazi_data.get("details", {})
        bazi_pillars = bazi_data.get("bazi_pillars", {})

        for pillar in pillars:
            detail = details.get(pillar, {})
            candidate_stars: List[str] = []
            if source in {"main", "any"}:
                main_star = detail.get("main_star")
                if main_star:
                    candidate_stars.append(main_star)
            if source in {"sub", "any"}:
                sub_stars = detail.get("sub_stars") or detail.get("hidden_stars") or []
                candidate_stars.extend(sub_stars)

            if god not in candidate_stars:
                continue

            if target_part == "stem":
                source_value = bazi_pillars.get(pillar, {}).get("stem")
            elif target_part == "branch":
                source_value = bazi_pillars.get(pillar, {}).get("branch")
            else:
                source_value = EnhancedRuleCondition._get_pillar_part_value(bazi_data, pillar, target_part)

            if not source_value:
                continue

            for target_pillar in target_pillars:
                target_value = EnhancedRuleCondition._get_pillar_part_value(bazi_data, target_pillar, target_part)
                if not target_value:
                    continue
                if target_value == source_value and relation not in {"equal"}:
                    # 合、冲等需不同主体
                    if pillar == target_pillar:
                        continue

                if target_part == "stem":
                    if relation == "he" and STEM_HE.get(source_value) == target_value:
                        return True
                    if relation == "equal" and source_value == target_value:
                        return True
                elif target_part == "branch":
                    if relation == "liuhe" and BRANCH_LIUHE.get(source_value) == target_value:
                        return True
                    if relation == "chong" and BRANCH_CHONG.get(source_value) == target_value:
                        return True
                    if relation == "hai":
                        harm_targets = ensure_list(BRANCH_HAI.get(source_value))
                        reverse_harm = ensure_list(BRANCH_HAI.get(target_value))
                        if target_value in harm_targets or source_value in reverse_harm:
                            return True
                    if relation == "po" and BRANCH_PO.get(source_value) == target_value:
                        return True
                    if relation == "xing":
                        xings = ensure_list(BRANCH_XING.get(source_value))
                        reverse_xings = ensure_list(BRANCH_XING.get(target_value))
                        if target_value in xings or source_value in reverse_xings:
                            return True
                    if relation == "equal" and source_value == target_value:
                        return True
                else:
                    if relation == "equal" and source_value == target_value:
                        return True

        return False

    @staticmethod
    def _match_ten_gods_injured(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return False

        gods = ensure_list(spec.get("gods"))
        relations = ensure_list(spec.get("relations"))
        include_hidden = spec.get("include_hidden", False)

        if not gods or not relations:
            return False

        pillars = ["year", "month", "day", "hour"]
        details = bazi_data.get("details", {})
        branch_map = {
            pillar: bazi_data.get("bazi_pillars", {}).get(pillar, {}).get("branch")
            for pillar in pillars
        }

        for pillar in pillars:
            pillar_detail = details.get(pillar, {})
            stars = []
            main_star = pillar_detail.get("main_star")
            if main_star:
                stars.append(main_star)
            if include_hidden:
                stars.extend(pillar_detail.get("hidden_stars") or pillar_detail.get("hidden_stems") or [])

            if not any(star in gods for star in stars):
                continue

            branch_a = branch_map.get(pillar)
            if not branch_a:
                continue

            for other in pillars:
                if other == pillar:
                    continue
                branch_b = branch_map.get(other)
                if not branch_b:
                    continue
                if EnhancedRuleCondition._check_branch_relations(branch_a, branch_b, relations):
                    return True

        return False

    @staticmethod
    def _match_element_counts(counts: Dict[str, int], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True

        names = spec.get('names') or list(counts.keys())
        if not isinstance(names, list):
            names = [names]

        # 检查是否有 min/max/eq 要求，且 names 是五行名称列表
        # 如果有，应该分别检查每个五行，而不是使用总和逻辑
        has_quantity_spec = spec.get('min') is not None or spec.get('max') is not None or spec.get('eq') is not None
        all_are_elements = all(name in ['金', '木', '水', '火', '土'] for name in names)
        
        if has_quantity_spec and all_are_elements:
            # 有数量要求且 names 都是五行名称，分别检查每个五行
            min_value = spec.get('min')
            max_value = spec.get('max')
            eq = spec.get('eq')
            
            if eq is not None:
                # 等于：每个五行都要等于指定值
                for name in names:
                    if counts.get(name, 0) != eq:
                        return False
                return True
            
            if min_value is not None:
                # 最小值：每个五行都要 >= min_value
                for name in names:
                    if counts.get(name, 0) < min_value:
                        return False
            
            if max_value is not None:
                # 最大值：每个五行都要 <= max_value
                for name in names:
                    if counts.get(name, 0) > max_value:
                        return False
            
            # 如果执行到这里，说明所有五行都满足要求
            return True
        
        # 检查 names 是否是规则描述文本（如"有五个字属土"）
        # 如果是，需要解析为五行名称和数量
        import re
        element_requirements = []
        
        for name in names:
            # 尝试解析规则描述文本
            # 匹配模式：有(可选) + 数量(中文或数字) + 个字属 + 五行
            pattern = re.compile(r"(?:有)?([零〇一二三四五六七八九十两\d]+)(?:个)?字?属([木火土金水])")
            match = pattern.search(name)
            
            if match:
                # 解析成功，提取数量和五行
                num_text = match.group(1)
                element = match.group(2)
                
                # 解析中文数字
                count = EnhancedRuleCondition._parse_chinese_numeral(num_text)
                if count is not None:
                    element_requirements.append((element, count))
                    continue
            
            # 如果不是规则描述文本，直接作为五行名称使用
            if name in ['金', '木', '水', '火', '土']:
                element_requirements.append((name, None))
        
        # 如果有解析出的要求，逐个检查
        if element_requirements:
            for element, required_count in element_requirements:
                actual_count = counts.get(element, 0)
                if required_count is not None:
                    # 有具体数量要求
                    if actual_count != required_count:
                        return False
                else:
                    # 只要求存在（数量 > 0）
                    if actual_count == 0:
                        return False
            return True
        
        # 其他情况：使用总和逻辑（兼容旧规则）
        total = sum(counts.get(name, 0) for name in names)

        eq = spec.get('eq')
        if eq is not None:
            return total == eq

        min_value = spec.get('min')
        if min_value is not None and total < min_value:
            return False

        max_value = spec.get('max')
        if max_value is not None and total > max_value:
            return False

        return True
    
    @staticmethod
    def _parse_chinese_numeral(text: str) -> Optional[int]:
        """解析中文数字为整数"""
        if not text:
            return None
        
        import re
        clean = re.sub(r"[^零〇一二三四五六七八九十两\d]", "", text)
        if not clean:
            return None

        # 先尝试提取阿拉伯数字
        digits = re.findall(r"\d+", clean)
        if digits:
            return int(digits[0])

        # 中文数字映射
        CHINESE_NUMBER_MAP = {
            '零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '两': 2
        }
        
        if clean in CHINESE_NUMBER_MAP:
            return CHINESE_NUMBER_MAP[clean]

        # 处理"十"的情况（如"十五"、"二十"）
        if "十" in clean:
            parts = clean.split("十")
            if parts[0] == "":
                high = 1
            else:
                high = CHINESE_NUMBER_MAP.get(parts[0], 0)
            if parts[-1] == "":
                low = 0
            else:
                low = CHINESE_NUMBER_MAP.get(parts[-1], 0)
            return high * 10 + low

        return None

    @staticmethod
    def _match_element_relation(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True
        source = spec.get('source')
        target = spec.get('target')
        if not source or not target:
            return False
        elements_map = bazi_data.get('elements', {})
        relation = EnhancedRuleCondition._get_element_relation(elements_map, source, target)
        if relation == 'unknown':
            return False

        expected = spec.get('type')
        if expected is None:
            return relation != 'unknown'
        if isinstance(expected, list):
            return relation in expected
        return relation == expected

    @staticmethod
    def _get_element_relation(elements_map: Dict[str, Dict[str, Any]], source_ref: str, target_ref: str) -> str:
        source_element = EnhancedRuleCondition._resolve_element_ref(elements_map, source_ref)
        target_element = EnhancedRuleCondition._resolve_element_ref(elements_map, target_ref)
        if not source_element or not target_element:
            return 'unknown'
        if source_element == target_element:
            return 'same'
        if ELEMENT_PRODUCES.get(source_element) == target_element:
            return 'generate'
        if ELEMENT_PRODUCES.get(target_element) == source_element:
            return 'generated_by'
        if ELEMENT_CONTROLS.get(source_element) == target_element:
            return 'control'
        if ELEMENT_CONTROLS.get(target_element) == source_element:
            return 'controlled_by'
        return 'unknown'

    @staticmethod
    def _get_pillar_part_value(bazi_data: Dict[str, Any], pillar: Optional[str], part: str):
        if not pillar:
            return None
        
        # 安全地获取 bazi_pillars
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        if not isinstance(bazi_pillars, dict):
            raise TypeError(f"bazi_data['bazi_pillars'] 必须是字典类型，但实际是: {type(bazi_pillars)}")
        pillar_info = bazi_pillars.get(pillar, {})
        if not isinstance(pillar_info, dict):
            pillar_info = {}
        
        # 安全地获取 details
        details_dict = bazi_data.get('details', {})
        if not isinstance(details_dict, dict):
            raise TypeError(f"bazi_data['details'] 必须是字典类型，但实际是: {type(details_dict)}")
        details = details_dict.get(pillar, {})
        if not isinstance(details, dict):
            details = {}
        
        if part == 'stem':
            return pillar_info.get('stem')
        if part == 'branch':
            return pillar_info.get('branch')
        if part == 'nayin':
            return details.get('nayin')
        if part == 'kongwang':
            return details.get('kongwang')
        if part == 'pillar':
            return f"{pillar_info.get('stem', '')}{pillar_info.get('branch', '')}"
        return details.get(part)

    @staticmethod
    def _collect_stems(bazi_data: Dict[str, Any]) -> List[str]:
        result = []
        for pillar in ['year', 'month', 'day', 'hour']:
            stem = bazi_data.get('bazi_pillars', {}).get(pillar, {}).get('stem')
            if stem:
                result.append(stem)
        return result

    @staticmethod
    def _collect_branches(bazi_data: Dict[str, Any]) -> List[str]:
        result = []
        for pillar in ['year', 'month', 'day', 'hour']:
            branch = bazi_data.get('bazi_pillars', {}).get(pillar, {}).get('branch')
            if branch:
                result.append(branch)
        return result

    @staticmethod
    def _match_collection_count(items: List[str], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True

        counts = Counter(items)
        names = ensure_list(spec.get('names'))
        result = True

        if names:
            eq = spec.get('eq')
            min_value = spec.get('min')
            max_value = spec.get('max')
            
            # 如果有 eq 且 names 是多个，应该检查每个是否都满足要求
            # 例如：eq: 2, names: ["辰", "戌"] 应该检查：辰 ≥ 1 且 戌 ≥ 1
            if eq is not None and len(names) > 1:
                # 多个名称且有 eq 要求，检查每个是否都 ≥ 1（每个都要出现至少一次）
                for name in names:
                    if counts.get(name, 0) < 1:
                        return False
                return True
            
            # 单个名称或没有 eq 要求，使用总和逻辑
            total = sum(counts.get(name, 0) for name in names)
            if eq is not None:
                return total == eq
            if min_value is not None and total < min_value:
                return False
            if max_value is not None and total > max_value:
                return False
            result = total > 0

        any_eq = spec.get('any_eq')
        if any_eq is not None:
            if not counts:
                return False
            if not any(count == any_eq for count in counts.values()):
                return False
            result = True

        any_min = spec.get('any_min')
        if any_min is not None:
            if not counts:
                return False
            if max(counts.values()) < any_min:
                return False
            result = True

        any_max = spec.get('any_max')
        if any_max is not None:
            if not counts:
                return False
            if max(counts.values()) > any_max:
                return False
            result = True

        return result

    @staticmethod
    def _get_current_liunian(bazi_data: Dict[str, Any]) -> Dict[str, Any]:
        fortune = bazi_data.get('fortune') or {}
        liunian = fortune.get('current_liunian') or {}
        return liunian

    @staticmethod
    def _resolve_target_values(bazi_data: Dict[str, Any], spec: Dict[str, Any], part: str):
        part = 'stem' if part == 'stem' else 'branch'
        values = []
        if isinstance(spec, dict):
            if 'value' in spec:
                values.append(spec['value'])
            if 'values' in spec:
                values.extend(ensure_list(spec['values']))
            target = spec.get('target')
            if target:
                pillar = bazi_data.get('bazi_pillars', {}).get(target, {})
                target_value = pillar.get(part)
                if target_value:
                    values.append(target_value)
        return values

    @staticmethod
    def _match_liunian_relation(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec or not isinstance(spec, dict):
            return False
        liunian = EnhancedRuleCondition._get_current_liunian(bazi_data)
        if not liunian:
            return False

        part = spec.get('part', 'stem')
        relation = spec.get('relation', '').lower()

        liunian_value = liunian.get('stem' if part == 'stem' else 'branch')
        if not liunian_value or not relation:
            return False

        targets = EnhancedRuleCondition._resolve_target_values(bazi_data, spec, part)
        if not targets:
            return False

        if part == 'stem':
            if relation in ('he', 'combine'):
                return any(STEM_HE.get(liunian_value) == target for target in targets)
            if relation == 'equal':
                return any(liunian_value == target for target in targets)
        else:
            if relation in ('liuhe', 'he'):
                return any(BRANCH_LIUHE.get(liunian_value) == target for target in targets)
            if relation == 'equal':
                return any(liunian_value == target for target in targets)
            if relation == 'chong':
                return any(BRANCH_CHONG.get(liunian_value) == target for target in targets)
        return False

    @staticmethod
    def _match_liunian_deities(bazi_data: Dict[str, Any], spec: Any) -> bool:
        liunian = EnhancedRuleCondition._get_current_liunian(bazi_data)
        deities = liunian.get('deities')
        if not deities:
            deities = []
        if isinstance(deities, str):
            deities = [deities]

        if spec is None:
            return True

        if isinstance(spec, list):
            return any(item in deities for item in spec)

        if isinstance(spec, dict):
            any_list = ensure_list(spec.get('any'))
            all_list = ensure_list(spec.get('all'))
            if all_list:
                if not all(item in deities for item in all_list):
                    return False
            if any_list:
                if not any(item in deities for item in any_list):
                    return False
            return True

        return spec in deities

    @staticmethod
    def _match_pillar_relation(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True
        pillar_a = spec.get('pillar_a')
        pillar_b = spec.get('pillar_b')
        relation = spec.get('relation')
        part = spec.get('part', 'branch')
        if not pillar_a or not pillar_b or not relation:
            return False

        value_a = EnhancedRuleCondition._get_pillar_part_value(bazi_data, pillar_a, part)
        value_b = EnhancedRuleCondition._get_pillar_part_value(bazi_data, pillar_b, part)
        if not value_a or not value_b:
            return False

        relation = relation.lower()

        if part == 'pillar':
            if relation == 'equal':
                return value_a == value_b
            return False

        if part == 'branch':
            if relation == 'equal':
                return value_a == value_b
            if relation == 'liuhe' or relation == 'he':
                return BRANCH_LIUHE.get(value_a) == value_b
            if relation == 'chong':
                return BRANCH_CHONG.get(value_a) == value_b
            if relation == 'ke':
                element_a = BRANCH_ELEMENTS.get(value_a)
                element_b = BRANCH_ELEMENTS.get(value_b)
                if not element_a or not element_b:
                    return False
                return (ELEMENT_CONTROLS.get(element_a) == element_b or
                        ELEMENT_CONTROLS.get(element_b) == element_a)
            if relation == 'xing':
                targets = ensure_list(BRANCH_XING.get(value_a))
                reverse_targets = ensure_list(BRANCH_XING.get(value_b))
                return value_b in targets or value_a in reverse_targets
            if relation == 'hai':
                targets = ensure_list(BRANCH_HAI.get(value_a))
                reverse_targets = ensure_list(BRANCH_HAI.get(value_b))
                return value_b in targets or value_a in reverse_targets
            if relation == 'po':
                return BRANCH_PO.get(value_a) == value_b
            return False

        if part == 'stem':
            if relation == 'equal':
                return value_a == value_b
            if relation == 'he':
                return STEM_HE.get(value_a) == value_b
            if relation == 'ke':
                element_a = STEM_ELEMENTS.get(value_a)
                element_b = STEM_ELEMENTS.get(value_b)
                if not element_a or not element_b:
                    return False
                return (ELEMENT_CONTROLS.get(element_a) == element_b or
                        ELEMENT_CONTROLS.get(element_b) == element_a)
            return False

        if part == 'nayin':
            if relation == 'equal':
                return value_a == value_b
            return False

        return False

    @staticmethod
    def _match_branch_group(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True
        group_type = spec.get("type")
        if not group_type:
            return False
        branches = EnhancedRuleCondition._collect_branches(bazi_data)
        branch_set = set(branches)

        if group_type == "sanhe":
            groups = BRANCH_SANHE_GROUPS
        elif group_type == "sanhui":
            groups = BRANCH_SANHUI_GROUPS
        else:
            groups = [tuple(spec.get("group", []))]

        for group in groups:
            if branch_set.issuperset(group):
                return True
        return False

    @staticmethod
    def _match_branch_offset(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True
        source = spec.get("source")
        target = spec.get("target")
        offset = spec.get("offset", 0)
        if source not in PILLAR_NAMES or target not in PILLAR_NAMES:
            return False
        source_branch = bazi_data.get("bazi_pillars", {}).get(source, {}).get("branch")
        target_branch = bazi_data.get("bazi_pillars", {}).get(target, {}).get("branch")
        if not source_branch or not target_branch:
            return False
        try:
            source_index = BRANCH_SEQUENCE.index(source_branch)
        except ValueError:
            return False
        expected_index = (source_index + offset) % len(BRANCH_SEQUENCE)
        return BRANCH_SEQUENCE[expected_index] == target_branch

    @staticmethod
    def _match_stems_parity(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True
        parity = spec.get("type")
        stems = EnhancedRuleCondition._collect_stems(bazi_data)
        if not stems or len(stems) != 4:
            return False
        if parity == "yang":
            return all(stem in YANG_STEMS for stem in stems)
        if parity == "yin":
            return all(stem in YIN_STEMS for stem in stems)
        return False

    @staticmethod
    def _match_branch_adjacent(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        if not spec:
            return True
        pairs = spec.get("pairs") or []
        if not pairs:
            return False
        branches = EnhancedRuleCondition._collect_branches(bazi_data)
        for a, b in pairs:
            if a not in branches or b not in branches:
                continue
            indices_a = [idx for idx, value in enumerate(branches) if value == a]
            indices_b = [idx for idx, value in enumerate(branches) if value == b]
            for ia in indices_a:
                for ib in indices_b:
                    if abs(ia - ib) == 1:
                        return True
        return False

    @staticmethod
    def _check_branch_relations(branch_a: Optional[str], branch_b: Optional[str], relations: List[str]) -> bool:
        if not branch_a or not branch_b or not relations:
            return False
        for relation in relations:
            relation = relation.lower()
            if relation == "chong" and BRANCH_CHONG.get(branch_a) == branch_b:
                return True
            if relation == "liuhe" and BRANCH_LIUHE.get(branch_a) == branch_b:
                return True
            if relation == "xing":
                targets = ensure_list(BRANCH_XING.get(branch_a))
                reverse_targets = ensure_list(BRANCH_XING.get(branch_b))
                if branch_b in targets or branch_a in reverse_targets:
                    return True
            if relation == "hai":
                targets = ensure_list(BRANCH_HAI.get(branch_a))
                reverse_targets = ensure_list(BRANCH_HAI.get(branch_b))
                if branch_b in targets or branch_a in reverse_targets:
                    return True
            if relation == "po" and BRANCH_PO.get(branch_a) == branch_b:
                return True
        return False

    @staticmethod
    def _match_branches_unique(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        branches = EnhancedRuleCondition._collect_branches(bazi_data)
        unique_count = len(set(branches))
        eq = spec.get("eq")
        if eq is not None:
            return unique_count == eq
        min_val = spec.get("min")
        if min_val is not None and unique_count < min_val:
            return False
        max_val = spec.get("max")
        if max_val is not None and unique_count > max_val:
            return False
        return True

    @staticmethod
    def _match_stems_unique(bazi_data: Dict[str, Any], spec: Dict[str, Any]) -> bool:
        stems = EnhancedRuleCondition._collect_stems(bazi_data)
        unique_count = len(set(stems))
        eq = spec.get("eq")
        if eq is not None:
            return unique_count == eq
        min_val = spec.get("min")
        if min_val is not None and unique_count < min_val:
            return False
        max_val = spec.get("max")
        if max_val is not None and unique_count > max_val:
            return False
        return True

    @staticmethod
    def _resolve_element_ref(elements_map: Dict[str, Dict[str, Any]], ref: str) -> Optional[str]:
        if not ref or '_' not in ref:
            return None
        # 确保 elements_map 是字典类型
        if not isinstance(elements_map, dict):
            if isinstance(elements_map, str):
                try:
                    import json
                    elements_map = json.loads(elements_map)
                except (json.JSONDecodeError, TypeError):
                    return None
            else:
                return None
        
        pillar, part = ref.split('_', 1)
        pillar_info = elements_map.get(pillar, {})
        # 确保 pillar_info 是字典类型
        if not isinstance(pillar_info, dict):
            if isinstance(pillar_info, str):
                try:
                    import json
                    pillar_info = json.loads(pillar_info)
                except (json.JSONDecodeError, TypeError):
                    return None
            else:
                return None
        
        key = f"{part}_element"
        return pillar_info.get(key) if isinstance(pillar_info, dict) else None


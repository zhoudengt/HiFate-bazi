#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运流年工具函数 - 公共功能
用于优化 input_data 的流年大运结构
"""

import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def calculate_user_age(solar_date: str, current_time: Optional[datetime] = None) -> int:
    """
    计算用户年龄（虚岁，与排盘系统保持一致）
    
    Args:
        solar_date: 阳历日期，格式：YYYY-MM-DD
        current_time: 当前时间（可选，默认使用系统当前时间）
        
    Returns:
        int: 用户年龄（虚岁）
    """
    if current_time is None:
        current_time = datetime.now()
    
    birth_year = int(solar_date.split('-')[0])
    current_year = current_time.year
    
    # 虚岁计算：当前年份 - 出生年份 + 1
    current_age = current_year - birth_year + 1
    
    return current_age


def get_current_dayun(
    dayun_sequence: List[Dict[str, Any]], 
    current_age: int
) -> Optional[Dict[str, Any]]:
    """
    确定用户当前大运（与排盘系统保持一致）
    
    Args:
        dayun_sequence: 大运序列
        current_age: 当前年龄（虚岁）
        
    Returns:
        Optional[Dict[str, Any]]: 当前大运，如果未找到返回None
    """
    # 遍历大运序列，找到包含当前年龄的大运
    for dayun in dayun_sequence:
        # 跳过小运（使用 is_xiaoyun 标记，stem 为真实干支而非 '小运'）
        if dayun.get('is_xiaoyun', False):
            continue
        
        age_range = dayun.get('age_range', {})
        if age_range:
            age_start = age_range.get('start', 0)
            age_end = age_range.get('end', 0)
            if age_start <= current_age <= age_end:
                return dayun
        else:
            # 如果没有age_range，尝试从age_display解析
            age_display = dayun.get('age_display', '')
            if age_display:
                try:
                    # 处理 "31-40岁" 格式
                    if '-' in age_display:
                        parts = age_display.replace('岁', '').split('-')
                        if len(parts) == 2:
                            age_start = int(parts[0])
                            age_end = int(parts[1])
                            if age_start <= current_age <= age_end:
                                return dayun
                    # 处理 "31岁" 格式（大运只显示起始年龄）
                    elif age_display.endswith('岁'):
                        age_start = int(age_display.replace('岁', ''))
                        age_end = age_start + 9  # 大运通常10年
                        if age_start <= current_age <= age_end:
                            return dayun
                except:
                    pass
    
    # 如果没找到，返回第一个非小运的大运
    for dayun in dayun_sequence:
        if not dayun.get('is_xiaoyun', False):
            return dayun
    
    return None


def select_dayuns_with_priority(
    dayun_sequence: List[Dict[str, Any]],
    current_dayun: Dict[str, Any],
    count: int = 10
) -> List[Dict[str, Any]]:
    """
    选择10个大运，按优先级排序（当前大运优先级最高，距离越近优先级越高）
    
    优先级规则：
    - 优先级1：当前大运
    - 优先级2：下一个大运
    - 优先级3：前一个大运
    - 优先级4：再下一个大运
    - 优先级5：再前一个大运
    - ...以此类推
    
    Args:
        dayun_sequence: 完整的大运序列
        current_dayun: 当前大运
        count: 要选择的大运数量（默认10个）
        
    Returns:
        List[Dict[str, Any]]: 按优先级排序的大运列表，每个大运包含priority字段
    """
    if not current_dayun:
        # 如果没有当前大运，返回前count个大运
        result = []
        for idx, dayun in enumerate(dayun_sequence[:count]):
            if not dayun.get('is_xiaoyun', False):
                dayun_copy = dayun.copy()
                dayun_copy['priority'] = idx + 1
                result.append(dayun_copy)
        return result
    
    # 找到当前大运在序列中的位置
    current_step = current_dayun.get('step')
    current_index = None
    
    # 先尝试通过step查找
    if current_step is not None:
        for idx, dayun in enumerate(dayun_sequence):
            if dayun.get('step') == current_step:
                current_index = idx
                break
    
    # 如果没找到，通过对象比较查找
    if current_index is None:
        for idx, dayun in enumerate(dayun_sequence):
            if dayun == current_dayun:
                current_index = idx
                break
    
    if current_index is None:
        # 如果还是没找到，返回前count个大运
        result = []
        for idx, dayun in enumerate(dayun_sequence[:count]):
            if not dayun.get('is_xiaoyun', False):
                dayun_copy = dayun.copy()
                dayun_copy['priority'] = idx + 1
                result.append(dayun_copy)
        return result
    
    # 按优先级选择大运
    result = []
    priority = 1
    selected_indices = set()
    
    # 优先级1：当前大运
    current_dayun_copy = current_dayun.copy()
    current_dayun_copy['priority'] = priority
    result.append(current_dayun_copy)
    selected_indices.add(current_index)
    priority += 1
    
    # 按距离当前大运的远近选择（下一个、前一个、再下一个、再前一个...）
    forward_index = current_index + 1
    backward_index = current_index - 1
    
    while len(result) < count and (forward_index < len(dayun_sequence) or backward_index >= 0):
        # 先选择下一个大运
        if forward_index < len(dayun_sequence) and forward_index not in selected_indices:
            dayun = dayun_sequence[forward_index]
            if not dayun.get('is_xiaoyun', False):
                dayun_copy = dayun.copy()
                dayun_copy['priority'] = priority
                result.append(dayun_copy)
                selected_indices.add(forward_index)
                priority += 1
                if len(result) >= count:
                    break
            forward_index += 1
        
        # 再选择前一个大运
        if backward_index >= 0 and backward_index not in selected_indices:
            dayun = dayun_sequence[backward_index]
            if not dayun.get('is_xiaoyun', False):
                dayun_copy = dayun.copy()
                dayun_copy['priority'] = priority
                result.append(dayun_copy)
                selected_indices.add(backward_index)
                priority += 1
                if len(result) >= count:
                    break
            backward_index -= 1
        
        # 如果两个方向都没有更多大运，退出循环
        if forward_index >= len(dayun_sequence) and backward_index < 0:
            break
    
    return result


def add_life_stage_label(age: int) -> str:
    """
    添加人生阶段标签
    
    标准定义：
    - 童年：0-12岁
    - 青年：13-30岁
    - 中年：31-60岁
    - 老年：61岁及以上
    
    Args:
        age: 年龄
        
    Returns:
        str: 人生阶段标签
    """
    if age <= 12:
        return '童年'
    elif age <= 30:
        return '青年'
    elif age <= 60:
        return '中年'
    else:
        return '老年'


def add_dayun_metadata(dayun: Dict[str, Any], priority: int) -> Dict[str, Any]:
    """
    添加大运描述和备注信息
    
    Args:
        dayun: 大运数据
        priority: 优先级（1最高）
        
    Returns:
        Dict[str, Any]: 添加了描述和备注的大运数据
    """
    dayun_copy = dayun.copy()
    
    # 添加人生阶段标签
    age_range = dayun.get('age_range', {})
    if age_range:
        age_mid = (age_range.get('start', 0) + age_range.get('end', 0)) // 2
        dayun_copy['life_stage'] = add_life_stage_label(age_mid)
    else:
        # 如果没有age_range，尝试从age_display解析
        age_display = dayun.get('age_display', '')
        if age_display:
            try:
                # 处理 "31-40岁" 格式
                if '-' in age_display:
                    parts = age_display.replace('岁', '').split('-')
                    if len(parts) == 2:
                        age_mid = (int(parts[0]) + int(parts[1])) // 2
                        dayun_copy['life_stage'] = add_life_stage_label(age_mid)
                # 处理 "31岁" 格式（大运只显示起始年龄）
                elif age_display.endswith('岁'):
                    age_start = int(age_display.replace('岁', ''))
                    age_mid = age_start + 4  # 大运中间年龄
                    dayun_copy['life_stage'] = add_life_stage_label(age_mid)
                else:
                    dayun_copy['life_stage'] = ''
            except:
                dayun_copy['life_stage'] = ''
        else:
            dayun_copy['life_stage'] = ''
    
    # 添加描述信息
    if priority == 1:
        dayun_copy['description'] = '当前大运，重点关注'
        dayun_copy['note'] = '用户当前处于此大运，需要重点分析'
    elif priority <= 3:
        dayun_copy['description'] = '近期大运，需要关注'
        if priority == 2:
            dayun_copy['note'] = '用户即将进入此大运，需要关注'
        else:
            dayun_copy['note'] = '用户刚离开此大运，需要关注'
    elif priority <= 6:
        dayun_copy['description'] = '重要大运，值得参考'
        dayun_copy['note'] = '参考大运，可简要提及'
    else:
        dayun_copy['description'] = '参考大运'
        dayun_copy['note'] = '参考大运，可简要提及'
    
    return dayun_copy


def add_liunian_metadata(
    liunian: Dict[str, Any], 
    dayun_priority: int,
    liunian_type: str,
    birth_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    添加流年描述和备注信息
    
    Args:
        liunian: 流年数据
        dayun_priority: 所属大运的优先级
        liunian_type: 流年类型（tiankedi_chong/tianhedi_he/suiyun_binglin/other）
        birth_year: 出生年份（可选，用于计算年龄）
        
    Returns:
        Dict[str, Any]: 添加了描述和备注的流年数据
    """
    liunian_copy = liunian.copy()
    
    # ⚠️ 关键：确保保留 relations 字段（岁运并临、天克地冲、天合地合）
    # relations 字段必须从原始流年数据中保留，不能丢失
    if 'relations' not in liunian_copy:
        liunian_copy['relations'] = liunian.get('relations', [])
    
    # ⚠️ 关键：确保保留 dayun_step 和 dayun_ganzhi 字段（用于确定流年归属）
    if 'dayun_step' not in liunian_copy:
        liunian_copy['dayun_step'] = liunian.get('dayun_step')
    if 'dayun_ganzhi' not in liunian_copy:
        liunian_copy['dayun_ganzhi'] = liunian.get('dayun_ganzhi', '')
    
    # 添加人生阶段标签
    age = liunian.get('age')
    if age is None and birth_year is not None:
        # 从年份计算年龄（虚岁）
        liunian_year = liunian.get('year')
        if liunian_year:
            age = liunian_year - birth_year + 1  # 虚岁计算
            liunian_copy['age'] = age
    
    if age is not None:
        liunian_copy['life_stage'] = add_life_stage_label(age)
    else:
        liunian_copy['life_stage'] = ''
    
    # 流年类型显示
    type_display_map = {
        'tiankedi_chong': '天克地冲',
        'tianhedi_he': '天合地合',
        'suiyun_binglin': '岁运并临',
        'other': '其他特殊流年'
    }
    liunian_copy['type'] = liunian_type
    liunian_copy['type_display'] = type_display_map.get(liunian_type, '特殊流年')
    
    # 流年类型优先级（用于计算最终优先级）
    type_priority_map = {
        'tiankedi_chong': 1,
        'tianhedi_he': 2,
        'suiyun_binglin': 3,
        'other': 4
    }
    type_priority = type_priority_map.get(liunian_type, 4)
    
    # 最终优先级 = 大运优先级 * 100 + 流年类型优先级（确保大运优先级占主导）
    final_priority = dayun_priority * 100 + type_priority
    liunian_copy['priority'] = final_priority
    
    # 添加描述信息
    if liunian_type == 'tiankedi_chong':
        liunian_copy['description'] = '天克地冲流年，需重点关注'
        liunian_copy['note'] = '此流年与日柱天克地冲，对运势有重要影响'
    elif liunian_type == 'tianhedi_he':
        liunian_copy['description'] = '天合地合流年，需要关注'
        liunian_copy['note'] = '此流年与大运天合地合，对运势有积极影响'
    elif liunian_type == 'suiyun_binglin':
        liunian_copy['description'] = '岁运并临流年，值得注意'
        liunian_copy['note'] = '此流年与大运岁运并临，对运势有重要影响'
    else:
        liunian_copy['description'] = '特殊流年，可参考'
        liunian_copy['note'] = '此流年有特殊关系，可参考分析'
    
    return liunian_copy


def organize_liunians_by_dayun_with_priority(
    special_liunians: List[Dict[str, Any]],
    selected_dayuns: List[Dict[str, Any]],
    birth_year: Optional[int] = None
) -> Dict[int, List[Dict[str, Any]]]:
    """
    组织流年，确保归属正确，并按优先级排序
    
    Args:
        special_liunians: 特殊流年列表
        selected_dayuns: 已选择的大运列表（包含priority字段）
        birth_year: 出生年份（可选，用于计算流年年龄）
        
    Returns:
        Dict[int, List[Dict[str, Any]]]: {
            dayun_step: [流年列表（按优先级排序）]
        }
    """
    # 添加日志用于诊断
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[organize_liunians_by_dayun_with_priority] special_liunians 数量: {len(special_liunians) if special_liunians else 0}")
    logger.info(f"[organize_liunians_by_dayun_with_priority] selected_dayuns 数量: {len(selected_dayuns) if selected_dayuns else 0}")
    
    # 创建大运step到优先级的映射（统一转换为整数类型，确保类型一致性）
    dayun_priority_map = {}
    dayun_step_normalized_map = {}  # 用于类型标准化映射
    for dayun in selected_dayuns:
        step = dayun.get('step')
        priority = dayun.get('priority', 999)
        if step is not None:
            # 统一转换为整数类型
            try:
                step_int = int(step) if not isinstance(step, int) else step
                dayun_priority_map[step_int] = priority
                # 同时保留原始值的映射（处理字符串 "5" 和整数 5 的情况）
                if step != step_int:
                    dayun_step_normalized_map[step] = step_int
            except (ValueError, TypeError):
                # 如果无法转换为整数，使用原始值
                dayun_priority_map[step] = priority
    
    logger.debug(f"[organize_liunians_by_dayun_with_priority] dayun_priority_map keys: {list(dayun_priority_map.keys())}")
    if dayun_step_normalized_map:
        logger.debug(f"[organize_liunians_by_dayun_with_priority] dayun_step_normalized_map: {dayun_step_normalized_map}")
    
    # 按关系类型分类流年（使用统一的 KeyYearsProvider 数据层）
    from server.utils.key_years_provider import classify_special_liunians
    classified = classify_special_liunians(special_liunians)
    
    logger.info(f"[organize_liunians_by_dayun_with_priority] 分类结果: tiankedi_chong={len(classified['tiankedi_chong'])}, tianhedi_he={len(classified['tianhedi_he'])}, suiyun_binglin={len(classified['suiyun_binglin'])}, other={len(classified['other'])}")
    
    # 按大运分组，并添加元数据
    result = {}
    
    # 辅助函数：标准化 step 值（确保类型一致）
    def normalize_step(step_value):
        """标准化 step 值，统一转换为整数类型"""
        if step_value is None:
            return None
        try:
            # 先尝试转换为整数
            step_int = int(step_value) if not isinstance(step_value, int) else step_value
            # 检查标准化后的值是否在映射中
            if step_int in dayun_priority_map:
                return step_int
            # 如果不在，检查原始值是否在映射中
            if step_value in dayun_step_normalized_map:
                return dayun_step_normalized_map[step_value]
            # 如果原始值在映射中，使用原始值
            if step_value in dayun_priority_map:
                return step_value
            return None
        except (ValueError, TypeError):
            # 如果无法转换，检查原始值是否在映射中
            if step_value in dayun_priority_map:
                return step_value
            return None
    
    # 处理天克地冲
    for liunian in classified['tiankedi_chong']:
        step = normalize_step(liunian.get('dayun_step'))
        if step is not None and step in dayun_priority_map:
            dayun_priority = dayun_priority_map[step]
            liunian_with_metadata = add_liunian_metadata(liunian, dayun_priority, 'tiankedi_chong', birth_year)
            if step not in result:
                result[step] = []
            result[step].append(liunian_with_metadata)
    
    # 处理天合地合
    for liunian in classified['tianhedi_he']:
        step = normalize_step(liunian.get('dayun_step'))
        if step is not None and step in dayun_priority_map:
            dayun_priority = dayun_priority_map[step]
            liunian_with_metadata = add_liunian_metadata(liunian, dayun_priority, 'tianhedi_he', birth_year)
            if step not in result:
                result[step] = []
            result[step].append(liunian_with_metadata)
    
    # 处理岁运并临
    for liunian in classified['suiyun_binglin']:
        step = normalize_step(liunian.get('dayun_step'))
        if step is not None and step in dayun_priority_map:
            dayun_priority = dayun_priority_map[step]
            liunian_with_metadata = add_liunian_metadata(liunian, dayun_priority, 'suiyun_binglin', birth_year)
            if step not in result:
                result[step] = []
            result[step].append(liunian_with_metadata)
    
    # 处理其他
    for liunian in classified['other']:
        step = normalize_step(liunian.get('dayun_step'))
        if step is not None and step in dayun_priority_map:
            dayun_priority = dayun_priority_map[step]
            liunian_with_metadata = add_liunian_metadata(liunian, dayun_priority, 'other', birth_year)
            if step not in result:
                result[step] = []
            result[step].append(liunian_with_metadata)
    
    # 对每个大运下的流年按优先级排序
    for step in result:
        result[step].sort(key=lambda x: x.get('priority', 999999))
    
    return result


def build_enhanced_dayun_structure(
    dayun_sequence: List[Dict[str, Any]],
    special_liunians: List[Dict[str, Any]],
    current_age: int,
    current_dayun: Optional[Dict[str, Any]] = None,
    birth_year: Optional[int] = None,
    business_type: str = 'default',
    bazi_data: Optional[Dict[str, Any]] = None,
    gender: str = 'male'
) -> Dict[str, Any]:
    """
    构建增强的大运流年结构（包含优先级、描述、备注等）
    
    === 架构说明 ===
    - 数据层：special_liunians 必须来自 BaziDataOrchestrator（与 fortune/display 一致）
    - 业务层：通过 business_type 选择不同的关键大运筛选策略
    
    Args:
        dayun_sequence: 完整的大运序列
        special_liunians: 特殊流年列表（必须来自 orchestrator）
        current_age: 当前年龄
        current_dayun: 当前大运（可选，如果为None则自动查找）
        birth_year: 出生年份（可选，用于计算流年年龄）
        business_type: 业务类型（'default'/'health'/'marriage'/'career'/'children' 等）
            - 'default': 按距离当前大运的优先级选择（总评、年报）
            - 'health': 按五行病理冲突选择（健康分析）
            - 'marriage': 按感情星透出选择（婚姻分析）
            - 'career'/'career_wealth': 按官星/财星透出选择（事业财富）
            - 'children'/'children_study': 按食伤星透出选择（子女学习）
        bazi_data: 八字基础数据（业务筛选需要日主天干等）
        gender: 性别（婚姻分析需要）
        
    Returns:
        Dict[str, Any]: {
            'current_dayun': {...},       # 当前大运（优先级1）
            'key_dayuns': [...],          # 关键大运列表（按业务策略选择）
            'priority_description': {...},# 优先级说明
            'business_type': '...'        # 使用的业务策略
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 1. 如果没有提供当前大运，自动查找
    if current_dayun is None:
        current_dayun = get_current_dayun(dayun_sequence, current_age)
    
    # === 业务层：根据 business_type 选择关键大运 ===
    from server.utils.key_years_provider import BUSINESS_SELECTORS, _select_default_key_dayuns
    
    selector = BUSINESS_SELECTORS.get(business_type, _select_default_key_dayuns)
    business_key_dayuns = selector(
        dayun_sequence=dayun_sequence,
        current_dayun=current_dayun,
        current_age=current_age,
        bazi_data=bazi_data,
        gender=gender,
    )
    
    logger.info(
        f"[build_enhanced_dayun_structure] 业务策略={business_type}, "
        f"选中关键大运={len(business_key_dayuns)}"
    )
    
    # === 数据层：确保所有包含特殊流年的大运都被包含 ===
    special_dayun_steps = set()
    if special_liunians:
        for liunian in special_liunians:
            dayun_step = liunian.get('dayun_step')
            if dayun_step is not None:
                special_dayun_steps.add(int(dayun_step) if not isinstance(dayun_step, int) else dayun_step)
    
    # 2. 构建选中大运列表
    # 对于 default 策略，使用优先级排序（向后兼容）
    if business_type == 'default' or business_type in ('general_review', 'annual_report', 'smart_fortune'):
        # 默认策略：按距离优先级选择 + 包含特殊流年大运
        base_selected_dayuns = select_dayuns_with_priority(dayun_sequence, current_dayun, count=10)
        base_steps = {d.get('step') for d in base_selected_dayuns}
        
        additional_dayuns = []
        for dayun in dayun_sequence:
            step = dayun.get('step')
            if step in special_dayun_steps and step not in base_steps:
                dayun_copy = dayun.copy()
                dayun_copy['priority'] = 100 + len(additional_dayuns)
                additional_dayuns.append(dayun_copy)
        
        selected_dayuns = base_selected_dayuns + additional_dayuns
    else:
        # 业务策略：当前大运 + 所有含特殊流年的大运（必须与排盘一致）+ 业务标注
        # ⚠️ 原则：所有含特殊流年的大运都必须出现（与 fortune/display 一致），
        #          业务选择器只负责标注 business_reason，不负责筛选。
        selected_steps = set()
        selected_dayuns = []
        business_steps = {kd.get('step') for kd in business_key_dayuns}
        business_map = {kd.get('step'): kd for kd in business_key_dayuns}
        
        # 当前大运（优先级1）
        if current_dayun:
            cd = current_dayun.copy()
            cd['priority'] = 1
            # 如果当前大运也被业务选中，保留业务标注
            biz = business_map.get(current_dayun.get('step'))
            if biz:
                cd['relation_type'] = biz.get('relation_type', '')
                cd['business_reason'] = biz.get('business_reason', '')
            selected_dayuns.append(cd)
            selected_steps.add(current_dayun.get('step'))
        
        # 合并：业务选中的大运 + 含特殊流年的大运（取并集，统一分配优先级）
        # 先收集所有需要出现的大运 step
        must_include_steps = special_dayun_steps | business_steps
        
        priority = 2
        for dayun in dayun_sequence:
            step = dayun.get('step')
            if step in must_include_steps and step not in selected_steps:
                dayun_copy = dayun.copy()
                dayun_copy['priority'] = priority
                # 如果被业务选择器选中，标注 business_reason
                biz = business_map.get(step)
                if biz:
                    dayun_copy['relation_type'] = biz.get('relation_type', '')
                    dayun_copy['business_reason'] = biz.get('business_reason', '')
                selected_dayuns.append(dayun_copy)
                selected_steps.add(step)
                priority += 1
    
    # 3. 为每个大运添加元数据
    enhanced_dayuns = []
    for dayun in selected_dayuns:
        priority = dayun.get('priority', 999)
        enhanced_dayun = add_dayun_metadata(dayun, priority)
        # 保留业务层标注的 relation_type 和 business_reason
        if 'relation_type' in dayun:
            enhanced_dayun['relation_type'] = dayun['relation_type']
        if 'business_reason' in dayun:
            enhanced_dayun['business_reason'] = dayun['business_reason']
        enhanced_dayuns.append(enhanced_dayun)
    
    # 4. 组织流年（确保归属正确）
    logger.info(f"[build_enhanced_dayun_structure] special_liunians 数量: {len(special_liunians) if special_liunians else 0}")
    if special_liunians:
        for i, liunian in enumerate(special_liunians[:5]):
            dayun_step = liunian.get('dayun_step')
            logger.debug(f"[build_enhanced_dayun_structure] special_liunians[{i}] dayun_step={dayun_step} (type: {type(dayun_step)})")
    
    for i, dayun in enumerate(enhanced_dayuns[:5]):
        step = dayun.get('step')
        logger.debug(f"[build_enhanced_dayun_structure] enhanced_dayuns[{i}] step={step} (type: {type(step)})")
    
    liunians_by_dayun = organize_liunians_by_dayun_with_priority(
        special_liunians, 
        enhanced_dayuns,
        birth_year=birth_year
    )
    
    logger.info(f"[build_enhanced_dayun_structure] liunians_by_dayun keys: {list(liunians_by_dayun.keys())}")
    for step, liunians in liunians_by_dayun.items():
        logger.debug(f"[build_enhanced_dayun_structure] step={step} (type: {type(step)}), liunians 数量: {len(liunians)}")
    
    # 5. 分离当前大运和关键大运
    current_dayun_enhanced = None
    key_dayuns_enhanced = []
    
    for dayun in enhanced_dayuns:
        priority = dayun.get('priority', 999)
        step = dayun.get('step')
        
        try:
            step_normalized = int(step) if step is not None and not isinstance(step, int) else step
        except (ValueError, TypeError):
            step_normalized = step
        
        liunians = liunians_by_dayun.get(step_normalized, [])
        if not liunians and step_normalized != step:
            liunians = liunians_by_dayun.get(step, [])
        
        logger.debug(f"[build_enhanced_dayun_structure] dayun step={step} (normalized: {step_normalized}), 获取到 liunians 数量: {len(liunians)}")
        
        dayun['liunians'] = liunians
        
        if priority == 1:
            current_dayun_enhanced = dayun
        else:
            key_dayuns_enhanced.append(dayun)
    
    # 6. 构建结果
    result = {
        'current_dayun': current_dayun_enhanced,
        'key_dayuns': key_dayuns_enhanced,
        'priority_description': {
            'rule': '优先级1（当前大运）重点说，多说；优先级2-3次之；优先级4-6简要提及；优先级7-10提一下即可',
            'current_dayun_priority': 1,
            'total_dayuns': len(enhanced_dayuns)
        },
        'business_type': business_type
    }
    
    return result


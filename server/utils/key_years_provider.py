#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键年份统一提供者 (Key Years Provider)

=== 架构说明 ===

两层架构：
  1. 数据层（统一）：所有接口共享同一个 special_liunians 数据源
     - 数据源头：BaziDetailService.calculate_detail_full() → liunian_sequence.relations
     - 与 /api/v1/bazi/fortune/display（专业排盘）完全一致
     - 通过 BaziDataOrchestrator 的 special_liunians 模块统一获取
     - 禁止任何接口自行计算或获取特殊流年

  2. 业务层（差异化）：每个接口根据业务视角选择关键大运
     - 健康：五行病理冲突（水火交战、金木相战等）
     - 婚姻：感情星透出（正财/偏财 for 男、正官/七杀 for 女、桃花星）
     - 事业：官星/财星透出（正官/七杀/正财/偏财）
     - 子女：食伤星透出（食神/伤官）
     - 默认：按距离当前大运的优先级（总评、年运报告等）

=== 使用方法 ===

    from server.utils.key_years_provider import KeyYearsProvider

    # 在流式接口的 build_xxx_input_data() 中：
    result = KeyYearsProvider.build_key_years_structure(
        dayun_sequence=dayun_sequence,
        special_liunians=special_liunians,       # 必须来自 orchestrator
        current_age=current_age,
        business_type='health',                   # 业务类型
        bazi_data=bazi_data,                      # 业务筛选可能需要
        gender=gender,                            # 婚姻分析需要
    )

    current_dayun = result['current_dayun']
    key_dayuns = result['key_dayuns']

=== 新增业务类型 ===

    1. 在 BUSINESS_SELECTORS 注册新类型
    2. 实现对应的 _select_xxx_key_dayuns() 方法
    3. 在 modules_config.py 中添加配置
    4. 在流式接口的 build_xxx_input_data() 中调用

详见：standards/09_关键年份架构规范.md
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


# ============================================================================
# 数据层：统一数据处理（所有接口共享）
# ============================================================================

def classify_special_liunians(special_liunians: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    按关系类型分类特殊流年（数据层公共方法）
    
    优先级：天克地冲 > 天合地合 > 岁运并临 > 其他
    
    数据来源：BaziDataOrchestrator → SpecialLiunianService → liunian_sequence.relations
    与 /api/v1/bazi/fortune/display 完全一致
    
    Args:
        special_liunians: 特殊流年列表（必须来自 orchestrator 的 special_liunians.list）
        
    Returns:
        dict: {
            'tiankedi_chong': [...],   # 天克地冲
            'tianhedi_he': [...],      # 天合地合
            'suiyun_binglin': [...],   # 岁运并临
            'other': [...]             # 其他特殊关系
        }
    """
    classified = {
        'tiankedi_chong': [],
        'tianhedi_he': [],
        'suiyun_binglin': [],
        'other': []
    }
    
    if not special_liunians:
        return classified
    
    for liunian in special_liunians:
        relations = liunian.get('relations', [])
        relation_types = []
        for r in relations:
            if isinstance(r, dict):
                relation_types.append(r.get('type', ''))
            elif isinstance(r, str):
                relation_types.append(r)
        
        has_tiankedi = any('天克地冲' in rt for rt in relation_types)
        has_tianhedi = any('天合地合' in rt for rt in relation_types)
        has_suiyun = any('岁运并临' in rt for rt in relation_types)
        
        if has_tiankedi:
            classified['tiankedi_chong'].append(liunian)
        elif has_tianhedi:
            classified['tianhedi_he'].append(liunian)
        elif has_suiyun:
            classified['suiyun_binglin'].append(liunian)
        else:
            classified['other'].append(liunian)
    
    return classified


def organize_by_dayun(
    special_liunians: List[Dict[str, Any]], 
    dayun_sequence: List[Dict[str, Any]]
) -> Dict[Any, Dict[str, Any]]:
    """
    将特殊流年按大运分组（数据层公共方法）
    
    Args:
        special_liunians: 特殊流年列表（必须来自 orchestrator）
        dayun_sequence: 大运序列
    
    Returns:
        dict: {
            dayun_step: {
                'dayun_info': {...},
                'tiankedi_chong': [...],
                'tianhedi_he': [...],
                'suiyun_binglin': [...],
                'other': [...]
            }
        }
    """
    classified = classify_special_liunians(special_liunians)
    
    # 大运映射
    dayun_map = {}
    for dayun in dayun_sequence:
        step = dayun.get('step')
        if step is not None:
            dayun_map[step] = {
                'step': step,
                'stem': dayun.get('stem', ''),
                'branch': dayun.get('branch', ''),
                'age_display': dayun.get('age_display', ''),
                'year_start': dayun.get('year_start', 0),
                'year_end': dayun.get('year_end', 0)
            }
    
    result = {}
    
    def _add_to_result(liunian_list, category):
        for liunian in liunian_list:
            step = liunian.get('dayun_step')
            if step is not None:
                # 标准化 step 为 int
                try:
                    step = int(step) if not isinstance(step, int) else step
                except (ValueError, TypeError):
                    pass
                if step not in result:
                    result[step] = {
                        'dayun_info': dayun_map.get(step, {}),
                        'tiankedi_chong': [],
                        'tianhedi_he': [],
                        'suiyun_binglin': [],
                        'other': []
                    }
                result[step][category].append(liunian)
    
    _add_to_result(classified['tiankedi_chong'], 'tiankedi_chong')
    _add_to_result(classified['tianhedi_he'], 'tianhedi_he')
    _add_to_result(classified['suiyun_binglin'], 'suiyun_binglin')
    _add_to_result(classified['other'], 'other')
    
    return result


def get_current_dayun(
    dayun_sequence: List[Dict[str, Any]], 
    current_age: int
) -> Optional[Dict[str, Any]]:
    """
    确定当前大运（数据层公共方法）
    
    复用 dayun_liunian_helper.get_current_dayun 的逻辑
    """
    from server.utils.dayun_liunian_helper import get_current_dayun as _get_current_dayun
    return _get_current_dayun(dayun_sequence, current_age)


# ============================================================================
# 业务层：关键大运选择策略（各接口差异化）
# ============================================================================

def _get_stem_shishen(day_stem: str, target_stem: str) -> str:
    """
    计算天干十神（业务层工具方法）
    
    Args:
        day_stem: 日主天干
        target_stem: 目标天干（大运天干）
    
    Returns:
        str: 十神名称
    """
    HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    SHISHEN_MAP = {
        0: '比肩', 1: '劫财',
        2: '食神', 3: '伤官',
        4: '偏财', 5: '正财',
        6: '七杀', 7: '正官',
        8: '偏印', 9: '正印'
    }
    
    if day_stem not in HEAVENLY_STEMS or target_stem not in HEAVENLY_STEMS:
        return '未知'
    
    if day_stem == target_stem:
        return '比肩'
    
    day_index = HEAVENLY_STEMS.index(day_stem)
    target_index = HEAVENLY_STEMS.index(target_stem)
    relation_index = (target_index - day_index) % 10
    
    return SHISHEN_MAP.get(relation_index, '未知')


def _calculate_ganzhi_elements(stem: str, branch: str) -> Dict[str, int]:
    """计算干支五行统计（业务层工具方法）"""
    STEM_ELEMENTS = {
        '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
        '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'
    }
    BRANCH_ELEMENTS = {
        '子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土',
        '巳': '火', '午': '火', '未': '土', '申': '金', '酉': '金',
        '戌': '土', '亥': '水'
    }
    elements = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    if stem and stem in STEM_ELEMENTS:
        elements[STEM_ELEMENTS[stem]] += 1
    if branch and branch in BRANCH_ELEMENTS:
        elements[BRANCH_ELEMENTS[branch]] += 1
    return elements


# --- 默认策略：按距离当前大运的优先级 ---

def _select_default_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    current_dayun: Optional[Dict[str, Any]],
    current_age: int,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    默认关键大运选择：按距离当前大运的优先级
    
    用于：总评分析、年运报告、及未指定业务类型的接口
    """
    from server.utils.dayun_liunian_helper import select_dayuns_with_priority
    
    selected = select_dayuns_with_priority(dayun_sequence, current_dayun, count=10)
    
    # 排除当前大运（当前大运单独返回）
    current_step = current_dayun.get('step') if current_dayun else None
    key_dayuns = [d for d in selected if d.get('step') != current_step]
    
    return key_dayuns


# --- 健康策略：五行病理冲突 ---

def _analyze_dayun_health_relation(
    dayun: Dict[str, Any],
    bazi_elements: Dict[str, int]
) -> Optional[str]:
    """
    分析大运与原局的五行病理关系
    
    返回冲突类型（水土混战、水火交战、金木相战、木土相战、火金相战），
    如果没有特殊关系返回 None
    """
    dayun_stem = dayun.get('stem', '')
    dayun_branch = dayun.get('branch', '')
    dayun_elements = _calculate_ganzhi_elements(dayun_stem, dayun_branch)
    
    # 五行病理冲突检测（阈值：大运2 + 原局2）
    conflicts = [
        ('水', '土', '水土混战'),
        ('火', '水', '水火交战'),
        ('金', '木', '金木相战'),
        ('木', '土', '木土相战'),
        ('火', '金', '火金相战'),
    ]
    
    for elem_a, elem_b, conflict_name in conflicts:
        if (dayun_elements.get(elem_a, 0) >= 2 and bazi_elements.get(elem_b, 0) >= 2) or \
           (dayun_elements.get(elem_b, 0) >= 2 and bazi_elements.get(elem_a, 0) >= 2):
            return conflict_name
    
    return None


def _select_health_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    current_dayun: Optional[Dict[str, Any]],
    current_age: int,
    bazi_data: Dict[str, Any] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    健康分析关键大运选择：基于五行病理冲突
    
    选择与原局五行存在冲突的大运（水土混战、水火交战等），
    这些大运对应的年份是健康风险较高的时期。
    """
    element_counts = bazi_data.get('element_counts', {}) if bazi_data else {}
    
    key_dayuns = []
    for dayun in dayun_sequence:
        if dayun.get('is_xiaoyun', False):
            continue
        relation_type = _analyze_dayun_health_relation(dayun, element_counts)
        if relation_type:
            dayun_copy = dayun.copy()
            dayun_copy['relation_type'] = relation_type
            dayun_copy['business_reason'] = f'健康风险：{relation_type}'
            key_dayuns.append(dayun_copy)
    
    return key_dayuns


# --- 婚姻策略：感情星透出 ---

def _select_marriage_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    current_dayun: Optional[Dict[str, Any]],
    current_age: int,
    bazi_data: Dict[str, Any] = None,
    gender: str = 'male',
    **kwargs
) -> List[Dict[str, Any]]:
    """
    婚姻分析关键大运选择：基于感情星透出
    
    - 男命：关注正财（正妻）、偏财（情人/异性缘）
    - 女命：关注正官（正夫）、七杀（偏夫/异性缘）
    - 通用：桃花地支（子午卯酉）对应的大运
    """
    day_stem = ''
    if bazi_data:
        pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = pillars.get('day', {})
        day_stem = day_pillar.get('stem', '')
    
    if not day_stem:
        logger.warning("[婚姻策略] 无法获取日主天干，降级为默认策略")
        return _select_default_key_dayuns(dayun_sequence, current_dayun, current_age)
    
    # 感情星定义
    if gender == 'male':
        target_shishen = {'正财', '偏财'}
    else:
        target_shishen = {'正官', '七杀'}
    
    # 桃花地支
    TAOHUA_BRANCHES = {'子', '午', '卯', '酉'}
    
    key_dayuns = []
    current_step = current_dayun.get('step') if current_dayun else None
    
    for dayun in dayun_sequence:
        if dayun.get('is_xiaoyun', False):
            continue
        if dayun.get('step') == current_step:
            continue
        
        dayun_stem = dayun.get('stem', '')
        dayun_branch = dayun.get('branch', '')
        
        reasons = []
        
        # 检查天干十神
        if dayun_stem:
            shishen = _get_stem_shishen(day_stem, dayun_stem)
            if shishen in target_shishen:
                reasons.append(f'{shishen}透出')
        
        # 检查桃花
        if dayun_branch in TAOHUA_BRANCHES:
            reasons.append('桃花星')
        
        if reasons:
            dayun_copy = dayun.copy()
            dayun_copy['relation_type'] = '、'.join(reasons)
            dayun_copy['business_reason'] = f'感情关注：{"、".join(reasons)}'
            key_dayuns.append(dayun_copy)
    
    return key_dayuns


# --- 事业策略：官星/财星透出 ---

def _select_career_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    current_dayun: Optional[Dict[str, Any]],
    current_age: int,
    bazi_data: Dict[str, Any] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    事业财富分析关键大运选择：基于官星/财星/印星透出
    
    - 官星（正官/七杀）：仕途、领导力、权力
    - 财星（正财/偏财）：财运、投资、收入
    - 印星（正印/偏印）：贵人、学业、资源
    """
    day_stem = ''
    if bazi_data:
        pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = pillars.get('day', {})
        day_stem = day_pillar.get('stem', '')
    
    if not day_stem:
        logger.warning("[事业策略] 无法获取日主天干，降级为默认策略")
        return _select_default_key_dayuns(dayun_sequence, current_dayun, current_age)
    
    target_shishen = {'正官', '七杀', '正财', '偏财', '正印', '偏印'}
    
    key_dayuns = []
    current_step = current_dayun.get('step') if current_dayun else None
    
    for dayun in dayun_sequence:
        if dayun.get('is_xiaoyun', False):
            continue
        if dayun.get('step') == current_step:
            continue
        
        dayun_stem = dayun.get('stem', '')
        
        if dayun_stem:
            shishen = _get_stem_shishen(day_stem, dayun_stem)
            if shishen in target_shishen:
                dayun_copy = dayun.copy()
                dayun_copy['relation_type'] = f'{shishen}透出'
                dayun_copy['business_reason'] = f'事业关注：{shishen}透出'
                key_dayuns.append(dayun_copy)
    
    return key_dayuns


# --- 子女策略：食伤星透出 ---

def _select_children_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    current_dayun: Optional[Dict[str, Any]],
    current_age: int,
    bazi_data: Dict[str, Any] = None,
    gender: str = 'male',
    **kwargs
) -> List[Dict[str, Any]]:
    """
    子女学习分析关键大运选择：基于食伤星透出
    
    - 食神/伤官：子女星（男命以官杀为子女，女命以食伤为子女）
    - 但食伤同时代表才华、创造力、学习
    - 同时关注印星（学业）
    """
    day_stem = ''
    if bazi_data:
        pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = pillars.get('day', {})
        day_stem = day_pillar.get('stem', '')
    
    if not day_stem:
        logger.warning("[子女策略] 无法获取日主天干，降级为默认策略")
        return _select_default_key_dayuns(dayun_sequence, current_dayun, current_age)
    
    # 子女星：男命看官杀，女命看食伤
    if gender == 'male':
        target_shishen = {'正官', '七杀', '食神', '伤官'}
    else:
        target_shishen = {'食神', '伤官', '正官', '七杀'}
    
    key_dayuns = []
    current_step = current_dayun.get('step') if current_dayun else None
    
    for dayun in dayun_sequence:
        if dayun.get('is_xiaoyun', False):
            continue
        if dayun.get('step') == current_step:
            continue
        
        dayun_stem = dayun.get('stem', '')
        
        if dayun_stem:
            shishen = _get_stem_shishen(day_stem, dayun_stem)
            if shishen in target_shishen:
                dayun_copy = dayun.copy()
                dayun_copy['relation_type'] = f'{shishen}透出'
                dayun_copy['business_reason'] = f'子女关注：{shishen}透出'
                key_dayuns.append(dayun_copy)
    
    return key_dayuns


# ============================================================================
# 业务策略注册表
# ============================================================================

BUSINESS_SELECTORS: Dict[str, Callable] = {
    'default': _select_default_key_dayuns,
    'health': _select_health_key_dayuns,
    'marriage': _select_marriage_key_dayuns,
    'career': _select_career_key_dayuns,
    'career_wealth': _select_career_key_dayuns,     # 别名
    'children': _select_children_key_dayuns,
    'children_study': _select_children_key_dayuns,   # 别名
    'general_review': _select_default_key_dayuns,    # 总评用默认
    'annual_report': _select_default_key_dayuns,     # 年报用默认
    'smart_fortune': _select_default_key_dayuns,     # 智能运势用默认
}


# ============================================================================
# 统一入口：KeyYearsProvider
# ============================================================================

class KeyYearsProvider:
    """
    关键年份统一提供者
    
    两层架构：
    - 数据层：所有接口共享同一个 special_liunians 数据源
    - 业务层：每个接口根据业务视角选择关键大运
    
    数据来源必须以 /api/v1/bazi/fortune/display 为准，
    即 BaziDetailService.calculate_detail_full() → liunian_sequence.relations
    """
    
    # 数据层方法
    classify_liunians = staticmethod(classify_special_liunians)
    organize_by_dayun = staticmethod(organize_by_dayun)
    get_current_dayun = staticmethod(get_current_dayun)
    
    @staticmethod
    def build_key_years_structure(
        dayun_sequence: List[Dict[str, Any]],
        special_liunians: List[Dict[str, Any]],
        current_age: int,
        business_type: str = 'default',
        current_dayun: Optional[Dict[str, Any]] = None,
        bazi_data: Optional[Dict[str, Any]] = None,
        gender: str = 'male',
        birth_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        构建关键年份结构（统一入口）
        
        数据层：统一的 special_liunians 分类和按大运分组
        业务层：根据 business_type 选择不同的关键大运筛选策略
        
        Args:
            dayun_sequence: 大运序列（来自 orchestrator detail_data）
            special_liunians: 特殊流年列表（必须来自 orchestrator special_liunians.list）
            current_age: 当前年龄（虚岁）
            business_type: 业务类型，决定关键大运选择策略
                - 'default': 按距离优先级（总评、年报）
                - 'health': 五行病理冲突
                - 'marriage': 感情星透出
                - 'career' / 'career_wealth': 官星/财星透出
                - 'children' / 'children_study': 食伤星透出
                - 'general_review': 同 default
                - 'annual_report': 同 default
            current_dayun: 当前大运（可选，为 None 时自动查找）
            bazi_data: 八字基础数据（业务筛选需要日主天干等）
            gender: 性别（婚姻分析需要）
            birth_year: 出生年份（用于计算流年年龄）
            
        Returns:
            dict: {
                'current_dayun': {                 # 当前大运
                    ...dayun_fields,
                    'liunians': {
                        'tiankedi_chong': [...],
                        'tianhedi_he': [...],
                        'suiyun_binglin': [...],
                        'other': [...]
                    }
                },
                'key_dayuns': [                    # 关键大运列表
                    {
                        ...dayun_fields,
                        'relation_type': '...',    # 业务层标注的关系类型
                        'business_reason': '...',  # 业务层标注的原因
                        'liunians': {
                            'tiankedi_chong': [...],
                            'tianhedi_he': [...],
                            'suiyun_binglin': [...],
                            'other': [...]
                        }
                    }
                ],
                'business_type': '...',            # 使用的业务策略
                'data_source': 'orchestrator.special_liunians',
                'total_special_liunians': N
            }
        """
        if not dayun_sequence:
            logger.warning("[KeyYearsProvider] dayun_sequence 为空")
            return {
                'current_dayun': None,
                'key_dayuns': [],
                'business_type': business_type,
                'data_source': 'orchestrator.special_liunians',
                'total_special_liunians': 0
            }
        
        if special_liunians is None:
            special_liunians = []
        
        # === 数据层：统一处理 ===
        
        # 1. 确定当前大运
        if current_dayun is None:
            current_dayun = get_current_dayun(dayun_sequence, current_age)
        
        # 2. 按大运分组特殊流年（数据层统一逻辑）
        dayun_liunians = organize_by_dayun(special_liunians, dayun_sequence)
        
        logger.info(
            f"[KeyYearsProvider] 数据层: business_type={business_type}, "
            f"special_liunians={len(special_liunians)}, "
            f"dayun_liunians_groups={len(dayun_liunians)}"
        )
        
        # === 业务层：差异化选择关键大运（只标注，不筛选） ===
        
        selector = BUSINESS_SELECTORS.get(business_type, _select_default_key_dayuns)
        
        business_key_dayuns = selector(
            dayun_sequence=dayun_sequence,
            current_dayun=current_dayun,
            current_age=current_age,
            bazi_data=bazi_data,
            gender=gender,
        )
        
        # ⚠️ 关键修复：合并业务选中的大运与含特殊流年的大运（取并集）
        # 原则：所有含特殊流年的大运必须出现在 key_dayuns 中（与 fortune/display 一致），
        #        业务选择器只负责标注 business_reason，不负责筛选。
        business_map = {d.get('step'): d for d in business_key_dayuns}
        current_step = current_dayun.get('step') if current_dayun else None
        
        merged_key_dayuns = []
        merged_steps = set()
        
        # 先加入业务选中的大运（保留标注）
        for d in business_key_dayuns:
            step = d.get('step')
            if step != current_step and step not in merged_steps:
                merged_key_dayuns.append(d)
                merged_steps.add(step)
        
        # 再补充含特殊流年但未被业务选中的大运
        for step in dayun_liunians:
            if step not in merged_steps and step != current_step:
                # 从 dayun_sequence 中找到对应大运
                for dayun in dayun_sequence:
                    dayun_step = dayun.get('step')
                    try:
                        dayun_step_int = int(dayun_step) if dayun_step is not None and not isinstance(dayun_step, int) else dayun_step
                    except (ValueError, TypeError):
                        dayun_step_int = dayun_step
                    if dayun_step_int == step or dayun_step == step:
                        merged_key_dayuns.append(dayun.copy())
                        merged_steps.add(step)
                        break
        
        logger.info(
            f"[KeyYearsProvider] 业务层: strategy={business_type}, "
            f"business_selected={len(business_key_dayuns)}, "
            f"special_liunian_dayuns={len(dayun_liunians)}, "
            f"merged_key_dayuns={len(merged_key_dayuns)}"
        )
        
        # === 组装结果：为每个大运附加统一的流年数据 ===
        
        def _attach_liunians(dayun: Dict[str, Any]) -> Dict[str, Any]:
            """为大运附加其下的特殊流年（数据层统一逻辑）"""
            step = dayun.get('step')
            # 标准化 step
            try:
                step_int = int(step) if step is not None and not isinstance(step, int) else step
            except (ValueError, TypeError):
                step_int = step
            
            liunians_data = dayun_liunians.get(step_int, dayun_liunians.get(step, {}))
            
            dayun_result = dayun.copy()
            dayun_result['liunians'] = {
                'tiankedi_chong': liunians_data.get('tiankedi_chong', []),
                'tianhedi_he': liunians_data.get('tianhedi_he', []),
                'suiyun_binglin': liunians_data.get('suiyun_binglin', []),
                'other': liunians_data.get('other', [])
            }
            return dayun_result
        
        # 附加流年到当前大运
        current_dayun_result = _attach_liunians(current_dayun) if current_dayun else None
        
        # 附加流年到关键大运（使用合并后的列表）
        key_dayuns_result = [_attach_liunians(d) for d in merged_key_dayuns]
        
        return {
            'current_dayun': current_dayun_result,
            'key_dayuns': key_dayuns_result,
            'business_type': business_type,
            'data_source': 'orchestrator.special_liunians',
            'total_special_liunians': len(special_liunians)
        }
    
    @staticmethod
    def get_available_business_types() -> List[str]:
        """获取所有已注册的业务类型"""
        return list(BUSINESS_SELECTORS.keys())
    
    @staticmethod
    def register_business_selector(
        business_type: str, 
        selector: Callable
    ):
        """
        注册新的业务筛选策略
        
        用于扩展新的业务类型，无需修改此文件
        
        Args:
            business_type: 业务类型标识
            selector: 筛选函数，签名为：
                (dayun_sequence, current_dayun, current_age, 
                 bazi_data=None, gender='male', **kwargs) -> List[Dict]
        """
        BUSINESS_SELECTORS[business_type] = selector
        logger.info(f"[KeyYearsProvider] 注册业务策略: {business_type}")

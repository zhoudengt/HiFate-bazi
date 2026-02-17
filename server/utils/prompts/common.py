#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公共八字数据格式化工具"""

import json
import copy
from typing import Dict, Any, Optional

def _filter_empty_deities(data: Any) -> Any:
    """
    递归过滤数据结构中所有 deities 数组的空字符串
    
    Args:
        data: 要清理的数据（可以是 dict、list 或其他类型）
        
    Returns:
        清理后的数据
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if key == 'deities' and isinstance(value, list):
                # 过滤掉空字符串
                result[key] = [item for item in value if item != '']
            else:
                result[key] = _filter_empty_deities(value)
        return result
    elif isinstance(data, list):
        return [_filter_empty_deities(item) for item in data]
    else:
        return data


def _simplify_dayun(dayun: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    精简大运数据，只保留关键信息，减少数据量
    
    Args:
        dayun: 完整的大运数据
        
    Returns:
        精简后的大运数据
    """
    if not dayun:
        return None
    
    # ⚠️ 修复：正确获取大运干支（兼容不同的字段名）
    stem = dayun.get('stem', dayun.get('gan', ''))
    branch = dayun.get('branch', dayun.get('zhi', ''))
    ganzhi = dayun.get('ganzhi', f'{stem}{branch}')
    
    # 只保留关键字段
    simplified = {
        'step': dayun.get('step', ''),  # ⚠️ 新增：大运步数（用于确定流年归属）
        'ganzhi': ganzhi,
        'stem': stem,
        'branch': branch,
        'age_display': dayun.get('age_display', ''),  # ⚠️ 新增：年龄显示
        'start_age': dayun.get('start_age'),
        'end_age': dayun.get('end_age'),
        'wuxing': dayun.get('wuxing', ''),
        'shishen': dayun.get('shishen', ''),
        'analysis': dayun.get('analysis', '')[:200] if dayun.get('analysis') else '',  # 限制分析文本
    }
    
    # ⚠️ 修改：不再限制流年数量，所有特殊流年都要显示
    # 保留 relations 字段（岁运并临、天克地冲、天合地合）
    liunians = dayun.get('liunians', [])
    if liunians:
        simplified['key_liunians'] = [
            {
                'year': l.get('year'),
                'ganzhi': l.get('ganzhi', ''),
                'dayun_step': l.get('dayun_step'),  # 流年归属的大运步数
                'dayun_ganzhi': l.get('dayun_ganzhi', ''),  # 流年归属的大运干支
                'relations': l.get('relations', []),  # 特殊关系（岁运并临、天克地冲、天合地合）
                'type_display': l.get('type_display', ''),  # 关系类型显示
                'brief': l.get('analysis', '')[:100] if l.get('analysis') else ''
            }
            for l in liunians  # ⚠️ 不再限制数量，显示所有流年
        ]

    return simplified


# ==============================================================================
# 中文文本格式化工具函数（用于 LLM Prompt 优化）
# ==============================================================================

def format_bazi_pillars_text(bazi_pillars: Dict[str, Any]) -> str:
    """
    格式化四柱为简洁中文文本
    
    Args:
        bazi_pillars: 四柱数据 {'year': {'stem': '甲', 'branch': '子'}, ...}
        
    Returns:
        str: 格式化文本，如 "甲子年、乙丑月、丙寅日、丁卯时"
    """
    if not bazi_pillars:
        return ""
    
    pillar_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
    parts = []
    
    for pillar in ['year', 'month', 'day', 'hour']:
        pillar_data = bazi_pillars.get(pillar, {})
        stem = pillar_data.get('stem', '')
        branch = pillar_data.get('branch', '')
        if stem and branch:
            parts.append(f"{stem}{branch}{pillar_names[pillar]}")
    
    return '、'.join(parts)


def format_ten_gods_text(ten_gods: Dict[str, Any], include_hidden: bool = False) -> str:
    """
    格式化十神为简洁中文文本
    
    Args:
        ten_gods: 十神数据 {'year': {'main_star': '正官', 'hidden_stars': [...]}, ...}
        include_hidden: 是否包含藏干十神
        
    Returns:
        str: 格式化文本，如 "年正官、月劫财、日元男、时食神"
    """
    if not ten_gods:
        return ""
    
    pillar_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
    parts = []
    
    for pillar in ['year', 'month', 'day', 'hour']:
        pillar_data = ten_gods.get(pillar, {})
        main_star = pillar_data.get('main_star', '')
        if main_star:
            text = f"{pillar_names[pillar]}{main_star}"
            if include_hidden:
                hidden = pillar_data.get('hidden_stars', [])
                if hidden:
                    text += f"({'/'.join(hidden)})"
            parts.append(text)
    
    return '、'.join(parts)


def format_wuxing_distribution_text(element_counts: Dict[str, int]) -> str:
    """
    格式化五行分布为简洁中文文本
    
    Args:
        element_counts: 五行数量统计 {'木': 2, '火': 1, ...}
        
    Returns:
        str: 格式化文本，如 "金3、土2、木1、水1、火1"
    """
    if not element_counts:
        return ""
    
    # 按数量从高到低排序
    sorted_elements = sorted(
        element_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return '、'.join([f"{elem}{count}" for elem, count in sorted_elements])


def format_xi_ji_text(xi_ji: Dict[str, Any]) -> str:
    """
    格式化喜忌为简洁中文文本
    
    Args:
        xi_ji: 喜忌数据 {'xi_shen': '金土', 'ji_shen': '水木火', 'xi_ji_elements': {...}}
        
    Returns:
        str: 格式化文本，如 "喜金土，忌水木火"
    """
    if not xi_ji:
        return ""
    
    # 优先使用 xi_ji_elements 中的五行列表
    xi_elements = xi_ji.get('xi_ji_elements', {}).get('xi_shen', [])
    ji_elements = xi_ji.get('xi_ji_elements', {}).get('ji_shen', [])
    
    # 如果没有，使用字符串形式
    if not xi_elements:
        xi_str = xi_ji.get('xi_shen', '')
        xi_elements = list(xi_str) if isinstance(xi_str, str) else xi_str
    if not ji_elements:
        ji_str = xi_ji.get('ji_shen', '')
        ji_elements = list(ji_str) if isinstance(ji_str, str) else ji_str
    
    xi_text = ''.join(xi_elements) if xi_elements else '无'
    ji_text = ''.join(ji_elements) if ji_elements else '无'
    
    return f"喜{xi_text}，忌{ji_text}"


def format_deities_text(deities: Dict[str, Any]) -> str:
    """
    格式化神煞为简洁中文文本
    
    Args:
        deities: 神煞数据 {'year': ['天乙贵人', '桃花'], 'month': [...], ...}
        
    Returns:
        str: 格式化文本，如 "天乙贵人(年)、桃花(月)、红鸾(日)"
    """
    if not deities:
        return ""
    
    pillar_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
    all_deities = []
    
    for pillar in ['year', 'month', 'day', 'hour']:
        pillar_deities = deities.get(pillar, [])
        if pillar_deities:
            for deity in pillar_deities:
                if deity and deity.strip():  # 过滤空字符串
                    all_deities.append(f"{deity}({pillar_names[pillar]})")
    
    return '、'.join(all_deities) if all_deities else "无"


def _get_ganzhi(item: Dict[str, Any]) -> str:
    """公共辅助：从大运/流年数据中提取干支（兼容多种字段名）"""
    gz = item.get('ganzhi', '')
    if not gz:
        stem = item.get('stem', item.get('gan', ''))
        branch = item.get('branch', item.get('zhi', ''))
        gz = f"{stem}{branch}"
    return gz


def _normalize_life_stage(age_display: str, life_stage: str = '') -> str:
    """公共辅助：基于 age_display 标准化人生阶段"""
    # 提取起始年龄数字
    try:
        age_str = age_display.replace('岁', '').split('-')[0].strip()
        age = int(age_str)
    except (ValueError, IndexError):
        return life_stage or ''
    
    if age <= 15:
        return '少年'
    elif age <= 30:
        return '青年'
    elif age <= 55:
        return '中年'
    elif age <= 70:
        return '中晚年'
    else:
        return '晚年'


def format_key_dayuns_text(
    key_dayuns: list,
    current_dayun: Optional[Dict[str, Any]] = None,
    special_liunians: list = None
) -> list:
    """
    公共模块：格式化关键大运 + 关键流年（所有流式接口统一调用）
    
    规则：
    1. 按 step 升序排列（时间顺序）
    2. 特殊流年按 dayun_step 归属到对应大运下
    3. 人生阶段基于 age_display 标准化
    
    Args:
        key_dayuns: 关键大运列表
        current_dayun: 当前大运数据（可选，单独输出）
        special_liunians: 特殊流年列表（可选，按 dayun_step 分配到大运下）
        
    Returns:
        list: 格式化后的文本行列表（调用方 extend 到 lines 即可）
    """
    result_lines = []
    
    # --- 当前大运 ---
    current_step = None
    if current_dayun:
        ganzhi = _get_ganzhi(current_dayun)
        step = current_dayun.get('step', '')
        current_step = str(step)
        age_display = current_dayun.get('age_display', '')
        main_star = current_dayun.get('main_star', '')
        life_stage = _normalize_life_stage(age_display, current_dayun.get('life_stage', ''))
        
        cur_text = f"第{step}运{ganzhi}({age_display})"
        if main_star:
            cur_text += f"，{main_star}"
        if life_stage:
            cur_text += f"，{life_stage}"
        result_lines.append(f"【当前大运】{cur_text}")
        
        # 当前大运的流年：先取自身 liunians，再从 special_liunians 补充
        cur_liunians = _collect_liunians_for_step(current_dayun, current_step, special_liunians)
        if cur_liunians:
            liunian_text = format_liunian_text(cur_liunians)
            if liunian_text:
                result_lines.append(f"  流年：{liunian_text}")
    
    # --- 关键大运与流年 ---
    if not key_dayuns:
        return result_lines
    
    # 按 step 升序排列（时间顺序），只保留前10步大运（step <= 10）
    sorted_dayuns = sorted(key_dayuns, key=lambda d: int(d.get('step', 0) or 0))
    sorted_dayuns = [d for d in sorted_dayuns if int(d.get('step', 0) or 0) <= 10]
    
    dayun_lines = []
    for dayun in sorted_dayuns:
        step = str(dayun.get('step', ''))
        # 跳过当前大运（已单独输出）
        if step == current_step:
            continue
        
        ganzhi = _get_ganzhi(dayun)
        age_display = dayun.get('age_display', '')
        main_star = dayun.get('main_star', '')
        life_stage = _normalize_life_stage(age_display, dayun.get('life_stage', ''))
        business_reason = dayun.get('business_reason', '')
        
        text = f"第{step}运{ganzhi}({age_display})"
        if main_star:
            text += f"，{main_star}"
        if life_stage:
            text += f"，{life_stage}"
        if business_reason:
            text += f"[{business_reason}]"
        dayun_lines.append(text)
        
        # 该大运下的流年
        step_liunians = _collect_liunians_for_step(dayun, step, special_liunians)
        if step_liunians:
            liunian_text = format_liunian_text(step_liunians)
            if liunian_text:
                dayun_lines.append(f"  流年：{liunian_text}")
    
    if dayun_lines:
        result_lines.append(f"【关键大运与流年】")
        result_lines.extend(dayun_lines)
    
    return result_lines


def _collect_liunians_for_step(
    dayun: Dict[str, Any],
    step: str,
    special_liunians: list = None
) -> list:
    """
    公共辅助：收集某步大运下的所有流年
    1. 先从 dayun 自身的 liunians / key_liunians 取
    2. 再从 special_liunians 中按 dayun_step 匹配补充（去重）
    """
    # 自身流年
    own_liunians = dayun.get('liunians', dayun.get('key_liunians', []))
    if isinstance(own_liunians, dict):
        # 健康接口的 liunians 是 dict 格式 {type: [items]}
        flat = []
        for ltype, lyears in own_liunians.items():
            if lyears:
                for ly in lyears:
                    ly_copy = dict(ly)
                    ly_copy.setdefault('type_display', ltype)
                    flat.append(ly_copy)
        own_liunians = flat
    
    result = list(own_liunians) if own_liunians else []
    existing_years = {str(l.get('year', '')) for l in result}
    
    # 从 special_liunians 补充
    if special_liunians:
        for sl in special_liunians:
            sl_step = str(sl.get('dayun_step', ''))
            sl_year = str(sl.get('year', ''))
            if sl_step == str(step) and sl_year not in existing_years:
                result.append(sl)
                existing_years.add(sl_year)
    
    # 按年份排序
    result.sort(key=lambda x: int(x.get('year', 0) or 0))
    return result


def format_dayun_text(current_dayun: Optional[Dict[str, Any]], key_dayuns: list = None) -> str:
    """
    格式化大运为简洁中文文本（兼容旧调用，内部委托给 format_key_dayuns_text）
    """
    lines = format_key_dayuns_text(key_dayuns or [], current_dayun)
    return '\n'.join(lines)


def format_liunian_text(liunians: list, max_count: int = 0) -> str:
    """
    格式化流年为简洁中文文本（只显示特殊流年，不限制数量）
    
    Args:
        liunians: 流年列表
        max_count: 最大显示数量，0 表示不限制
        
    Returns:
        str: 格式化文本，如 "2026丙午(天克地冲)、2028戊申(天合地合)"
    """
    if not liunians:
        return ""
    
    parts = []
    
    for liunian in liunians:
        if max_count > 0 and len(parts) >= max_count:
            break
        
        year = liunian.get('year', '')
        ganzhi = liunian.get('ganzhi', '')
        relations = liunian.get('relations', [])
        type_display = liunian.get('type_display', '')
        
        if relations or type_display:
            # 有特殊关系的流年
            relation_text = type_display
            if not relation_text and relations:
                relation_types = [r.get('type', '') for r in relations if r.get('type')]
                relation_text = '/'.join(relation_types)
            
            if relation_text:
                parts.append(f"{year}{ganzhi}({relation_text})")
            else:
                parts.append(f"{year}{ganzhi}")
    
    return '、'.join(parts) if parts else ""


def format_judgments_text(judgments: list, max_count: int = 0) -> str:
    """
    格式化判词为简洁中文文本（保留完整判词，不截断）
    
    Args:
        judgments: 判词列表 [{'name': '规则名', 'text': '判词内容'}, ...]
        max_count: 最大显示数量，0 表示不限制
        
    Returns:
        str: 格式化文本，如 "正财坐长生，配偶贤良；日支逢冲，婚姻波折"
    """
    if not judgments:
        return ""
    
    items = judgments if max_count <= 0 else judgments[:max_count]
    texts = []
    for judgment in items:
        text = judgment.get('text', '')
        if text:
            texts.append(text)
    
    return '；'.join(texts) if texts else ""


def format_branch_relations_text(branch_relations: Dict[str, Any]) -> str:
    """
    格式化地支关系为简洁中文文本
    
    Args:
        branch_relations: 地支关系数据 {'chong': [...], 'xing': [...], 'po': [...], 'hai': [...]}
        
    Returns:
        str: 格式化文本，如 "冲:子午、刑:丑戌、合:寅亥"
    """
    if not branch_relations:
        return ""
    
    relation_names = {
        'chong': '冲',
        'xing': '刑',
        'po': '破',
        'hai': '害',
        'he': '合',
        'sanhe': '三合',
        'liuhe': '六合'
    }
    
    parts = []
    for key, name in relation_names.items():
        relations = branch_relations.get(key, [])
        if relations:
            if isinstance(relations[0], dict):
                # 字典格式
                items = [f"{r.get('branch1', '')}{r.get('branch2', '')}" for r in relations]
            else:
                # 字符串格式
                items = relations
            if items:
                parts.append(f"{name}:{'/'.join(items)}")
    
    return '，'.join(parts) if parts else "无"


# ==============================================================================
# 健康分析 Prompt 构建函数
# ==============================================================================


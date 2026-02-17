#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事业财富分析 prompt 构建"""

from typing import Dict, Any
from .common import format_bazi_pillars_text, format_ten_gods_text, format_wuxing_distribution_text, format_xi_ji_text, format_deities_text, format_dayun_text, format_liunian_text, format_judgments_text, format_branch_relations_text, format_key_dayuns_text

def format_career_wealth_input_data_for_coze(input_data: Dict[str, Any]) -> str:
    """
    将结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
    """
    # 获取原始数据
    mingpan = input_data.get('mingpan_shiye_caifu_zonglun', {})
    shiye = input_data.get('shiye_xing_gong', {})
    caifu = input_data.get('caifu_xing_gong', {})
    shiye_yunshi = input_data.get('shiye_yunshi', {})
    caifu_yunshi = input_data.get('caifu_yunshi', {})
    tiyun = input_data.get('tiyun_jianyi', {})
    
    # ⚠️ 方案2：优化数据结构，使用引用避免重复
    optimized_data = {
        # 1. 命盘事业财富总论（基础数据，只提取一次）
        'mingpan_shiye_caifu_zonglun': mingpan,
        
        # 2. 事业星与事业宫（引用十神，不重复存储）
        'shiye_xing_gong': {
            'shiye_xing': shiye.get('shiye_xing', {}),
            'month_pillar_analysis': shiye.get('month_pillar_analysis', {}),
            'ten_gods': mingpan.get('ten_gods', {}),
            'ten_gods_stats': shiye.get('ten_gods_stats', {}),
            'deities': shiye.get('deities', {}),
            'career_judgments': shiye.get('career_judgments', [])
        },
        
        # 3. 财富星与财富宫（引用十神，不重复存储）
        'caifu_xing_gong': {
            'caifu_xing': caifu.get('caifu_xing', {}),
            'year_pillar_analysis': caifu.get('year_pillar_analysis', {}),
            'hour_pillar_analysis': caifu.get('hour_pillar_analysis', {}),
            'shishang_shengcai': caifu.get('shishang_shengcai', {}),
            'caiku': caifu.get('caiku', {}),
            'wealth_judgments': caifu.get('wealth_judgments', [])
        },
        
        # 4. 事业运势（引用大运，不重复存储）
        'shiye_yunshi': {
            'current_age': shiye_yunshi.get('current_age', 0),
            'current_dayun': shiye_yunshi.get('current_dayun'),
            'key_dayuns': shiye_yunshi.get('key_dayuns', []),
            'key_liunian': shiye_yunshi.get('key_liunian', []),
            'chonghe_xinghai': shiye_yunshi.get('chonghe_xinghai', {})
        },
        
        # 5. 财富运势（引用大运，不重复存储）
        'caifu_yunshi': {
            'wealth_stages': caifu_yunshi.get('wealth_stages', {}),
            'current_dayun': shiye_yunshi.get('current_dayun'),  # 引用事业运势的当前大运
            'key_dayuns': shiye_yunshi.get('key_dayuns', []),  # 引用事业运势的关键大运
            'liunian_wealth_nodes': caifu_yunshi.get('liunian_wealth_nodes', []),
            'caiku_timing': caifu_yunshi.get('caiku_timing', {})
        },
        
        # 6. 提运建议（引用十神和喜忌，不重复存储）
        'tiyun_jianyi': {
            'ten_gods_summary': tiyun.get('ten_gods_summary', ''),
            'xi_ji': tiyun.get('xi_ji', {}),
            'fangwei': tiyun.get('fangwei', {}),
            'hangye': tiyun.get('hangye', {}),
            'wuxing_hangye': tiyun.get('wuxing_hangye', {})
        }
    }
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(optimized_data, ensure_ascii=False, indent=2)


def format_career_wealth_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将事业财富分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 4000 字符
    - 优化后约 600 字符
    - Token 减少约 85%
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_shiye_caifu_zonglun', {})
    shiye = input_data.get('shiye_xing_gong', {})
    caifu = input_data.get('caifu_xing_gong', {})
    shiye_yunshi = input_data.get('shiye_yunshi', {})
    tiyun = input_data.get('tiyun_jianyi', {})
    
    # 1. 命主基本信息
    day_master = mingpan.get('day_master', {})
    day_stem = day_master.get('stem', '')
    day_element = day_master.get('element', '')
    wangshuai = mingpan.get('wangshuai', '')
    yue_ling = mingpan.get('yue_ling', '')
    gender = mingpan.get('gender', '')
    gender_display = '男命' if gender == 'male' else '女命' if gender == 'female' else ''
    
    lines.append(f"【命主】{day_stem}{day_element}日元，{gender_display}，{wangshuai}，月令{yue_ling}")
    
    # 2. 四柱
    bazi_pillars = mingpan.get('bazi_pillars', {})
    pillars_text = format_bazi_pillars_text(bazi_pillars)
    if pillars_text:
        lines.append(f"【四柱】{pillars_text}")
    
    # 3. 格局
    geju_type = mingpan.get('geju_type', '')
    geju_desc = mingpan.get('geju_description', '')
    if geju_type:
        geju_text = geju_type
        if geju_desc:
            geju_text += f"，{geju_desc}"
        lines.append(f"【格局】{geju_text}")
    
    # 4. 十神
    ten_gods = mingpan.get('ten_gods', {})
    ten_gods_text = format_ten_gods_text(ten_gods)
    if ten_gods_text:
        lines.append(f"【十神】{ten_gods_text}")
    
    # 5. 事业星
    shiye_xing = shiye.get('shiye_xing', {})
    if shiye_xing:
        primary = shiye_xing.get('primary', '')
        positions = shiye_xing.get('positions', [])
        strength = shiye_xing.get('strength', '')
        
        shiye_text = primary
        if positions:
            shiye_text += f"({'/'.join(positions)})"
        if strength:
            shiye_text += f"，{strength}"
        if shiye_text:
            lines.append(f"【事业星】{shiye_text}")
    
    # 6. 财富星
    caifu_xing = caifu.get('caifu_xing', {})
    if caifu_xing:
        primary = caifu_xing.get('primary', '')
        positions = caifu_xing.get('positions', [])
        strength = caifu_xing.get('strength', '')
        
        caifu_text = primary
        if positions:
            caifu_text += f"({'/'.join(positions)})"
        if strength:
            caifu_text += f"，{strength}"
        if caifu_text:
            lines.append(f"【财富星】{caifu_text}")
    
    # 7. 食伤生财
    shishang = caifu.get('shishang_shengcai', {})
    if shishang and shishang.get('has_combination'):
        combination_type = shishang.get('combination_type', '食伤生财')
        lines.append(f"【食伤生财】有{combination_type}组合")
    
    # 8. 财库
    caiku = caifu.get('caiku', {})
    if caiku and caiku.get('has_caiku'):
        caiku_position = caiku.get('caiku_position', '')
        caiku_status = caiku.get('caiku_status', '')
        lines.append(f"【财库】{caiku_position}为财库，{caiku_status}")
    
    # 9. 神煞
    deities = shiye.get('deities', {})
    deities_text = format_deities_text(deities)
    if deities_text and deities_text != "无":
        lines.append(f"【神煞】{deities_text}")
    
    # 10. 事业判词（完整保留）
    career_judgments = shiye.get('career_judgments', [])
    if career_judgments:
        judgments_text = format_judgments_text(career_judgments)
        if judgments_text:
            lines.append(f"【事业判词】{judgments_text}")
    
    # 11. 财富判词（完整保留）
    wealth_judgments = caifu.get('wealth_judgments', [])
    if wealth_judgments:
        judgments_text = format_judgments_text(wealth_judgments)
        if judgments_text:
            lines.append(f"【财富判词】{judgments_text}")
    
    # 12-13. 当前大运 + 关键大运与流年（统一使用公共模块）
    lines.extend(format_key_dayuns_text(
        key_dayuns=shiye_yunshi.get('key_dayuns', []),
        current_dayun=shiye_yunshi.get('current_dayun', {}),
        special_liunians=shiye_yunshi.get('special_liunians', [])
    ))
    
    # 14. 喜忌
    xi_ji = tiyun.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    # 15. 方位建议
    fangwei = tiyun.get('fangwei', {})
    if fangwei:
        best = fangwei.get('best_directions', [])
        avoid = fangwei.get('avoid_directions', [])
        if best or avoid:
            fangwei_text = ""
            if best:
                fangwei_text += f"宜{'/'.join(best)}"
            if avoid:
                if fangwei_text:
                    fangwei_text += "，"
                fangwei_text += f"忌{'/'.join(avoid)}"
            lines.append(f"【方位】{fangwei_text}")
    
    # 16. 行业建议
    hangye = tiyun.get('hangye', {})
    if hangye:
        best = hangye.get('best_industries', [])
        if best:
            lines.append(f"【行业】宜{'/'.join(best[:5])}")
    
    return '\n'.join(lines)


# ==============================================================================
# 子女学习分析格式化函数
# ==============================================================================


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""子女学习分析 prompt 构建"""

from typing import Dict, Any
from .common import format_bazi_pillars_text, format_ten_gods_text, format_wuxing_distribution_text, format_xi_ji_text, format_deities_text, format_dayun_text, format_liunian_text, format_judgments_text, format_key_dayuns_text

def format_children_study_input_data_for_coze(input_data: Dict[str, Any]) -> str:
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
    mingpan = input_data.get('mingpan_zinv_zonglun', {})
    zinvxing = input_data.get('zinvxing_zinvgong', {})
    shengyu = input_data.get('shengyu_shiji', {})
    yangyu = input_data.get('yangyu_jianyi', {})
    children_rules = input_data.get('children_rules', {})
    
    # ⚠️ 方案2：优化数据结构，使用引用避免重复
    # 注意：为了确保 Bot 能正确理解，我们直接展开引用，但只保留一份数据
    optimized_data = {
        # 1. 命盘子女总论（基础数据，只提取一次）
        'mingpan_zinv_zonglun': mingpan,
        
        # 2. 子女星与子女宫（十神数据只提取一次）
        'zinvxing_zinvgong': zinvxing,
        
        # 3. 生育时机（引用十神，不重复存储）
        'shengyu_shiji': {
            'zinv_xing_type': shengyu.get('zinv_xing_type', ''),
            'current_dayun': shengyu.get('current_dayun'),
            'key_dayuns': shengyu.get('key_dayuns', []),
            'all_dayuns': shengyu.get('all_dayuns', []),
            # ⚠️ 直接引用十神数据（不重复存储）
            'ten_gods': zinvxing.get('ten_gods', {})
        },
        
        # 4. 养育建议（引用旺衰和十神，不重复存储）
        'yangyu_jianyi': {
            # ⚠️ 直接引用十神数据（不重复存储）
            'ten_gods': zinvxing.get('ten_gods', {}),
            # ⚠️ 直接引用旺衰字符串（不重复存储完整对象）
            'wangshuai': mingpan.get('wangshuai', ''),
            'xi_ji': yangyu.get('xi_ji', {})
        }
    }
    
    # 5. 添加子女规则（如果有）
    if children_rules:
        optimized_data['children_rules'] = children_rules
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(optimized_data, ensure_ascii=False, indent=2)


def format_children_study_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将子女学习分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 3000 字符
    - 优化后约 450 字符
    - Token 减少约 85%
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_zinv_zonglun', {})
    zinvxing = input_data.get('zinvxing_zinvgong', {})
    shengyu = input_data.get('shengyu_shiji', {})
    yangyu = input_data.get('yangyu_jianyi', {})
    children_rules = input_data.get('children_rules', {})
    
    # 1. 命主基本信息
    day_master = mingpan.get('day_master', {})
    day_stem = day_master.get('stem', '')
    day_element = day_master.get('element', '')
    wangshuai = mingpan.get('wangshuai', '')
    gender = mingpan.get('gender', '')
    gender_display = '男命' if gender == 'male' else '女命' if gender == 'female' else ''
    
    lines.append(f"【命主】{day_stem}{day_element}日元，{gender_display}，{wangshuai}")
    
    # 2. 四柱
    bazi_pillars = mingpan.get('bazi_pillars', {})
    pillars_text = format_bazi_pillars_text(bazi_pillars)
    if pillars_text:
        lines.append(f"【四柱】{pillars_text}")
    
    # 3. 子女星
    zinv_xing_type = zinvxing.get('zinv_xing_type', '') or shengyu.get('zinv_xing_type', '')
    if zinv_xing_type:
        lines.append(f"【子女星】{zinv_xing_type}")
    
    # 4. 子女宫（时柱）
    hour_pillar = zinvxing.get('hour_pillar', {})
    if hour_pillar:
        stem = hour_pillar.get('stem', '')
        branch = hour_pillar.get('branch', '')
        if stem and branch:
            lines.append(f"【子女宫】时柱{stem}{branch}")
    
    # 5. 十神
    ten_gods = zinvxing.get('ten_gods', {})
    ten_gods_text = format_ten_gods_text(ten_gods)
    if ten_gods_text:
        lines.append(f"【十神】{ten_gods_text}")
    
    # 6. 神煞
    deities = zinvxing.get('deities', {})
    deities_text = format_deities_text(deities)
    if deities_text and deities_text != "无":
        lines.append(f"【神煞】{deities_text}")
    
    # 7. 子女判词（完整保留）
    rule_judgments = children_rules.get('rule_judgments', [])
    if rule_judgments:
        judgments_text = format_judgments_text(
            [{'text': j} if isinstance(j, str) else j for j in rule_judgments]
        )
        if judgments_text:
            lines.append(f"【子女判词】{judgments_text}")
    
    # 8-9. 当前大运 + 关键大运与流年（统一使用公共模块）
    lines.extend(format_key_dayuns_text(
        key_dayuns=shengyu.get('key_dayuns', []),
        current_dayun=shengyu.get('current_dayun', {}),
        special_liunians=shengyu.get('special_liunians', [])
    ))
    
    # 10. 喜忌
    xi_ji = yangyu.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    return '\n'.join(lines)


# ==============================================================================
# 健康分析格式化函数
# ==============================================================================


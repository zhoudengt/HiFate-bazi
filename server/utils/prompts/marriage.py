#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""婚姻分析 prompt 构建"""

from typing import Dict, Any
from .common import format_bazi_pillars_text, format_ten_gods_text, format_wuxing_distribution_text, format_xi_ji_text, format_deities_text, format_dayun_text, format_liunian_text, format_judgments_text, format_branch_relations_text, format_key_dayuns_text

def format_marriage_input_data_for_coze(input_data: Dict[str, Any]) -> str:
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
    mingpan = input_data.get('mingpan_zonglun', {})
    peiou = input_data.get('peiou_tezheng', {})
    ganqing = input_data.get('ganqing_zoushi', {})
    shensha = input_data.get('shensha_dianjing', {})
    jianyi = input_data.get('jianyi_fangxiang', {})
    
    # ⚠️ 方案2：优化数据结构，使用引用避免重复
    optimized_data = {
        # 1. 命盘总论（基础数据，只提取一次）
        'mingpan_zonglun': mingpan,
        
        # 2. 配偶特征（引用十神，不重复存储）
        'peiou_tezheng': {
            'ten_gods': mingpan.get('ten_gods', {}),
            'deities': peiou.get('deities', {}),
            'marriage_judgments': peiou.get('marriage_judgments', []),
            'peach_blossom_judgments': peiou.get('peach_blossom_judgments', []),
            'matchmaking_judgments': peiou.get('matchmaking_judgments', []),
            'zhengyuan_judgments': peiou.get('zhengyuan_judgments', [])
        },
        
        # 3. 感情走势（引用十神和大运，不重复存储）
        'ganqing_zoushi': {
            'current_dayun': ganqing.get('current_dayun'),
            'key_dayuns': ganqing.get('key_dayuns', []),
            'ten_gods': mingpan.get('ten_gods', {})
        },
        
        # 4. 神煞点睛（引用神煞，不重复存储）
        'shensha_dianjing': {
            'deities': peiou.get('deities', {})
        },
        
        # 5. 建议方向（引用十神、喜忌和大运，不重复存储）
        'jianyi_fangxiang': {
            'ten_gods': mingpan.get('ten_gods', {}),
            'xi_ji': jianyi.get('xi_ji', {}),
            'current_dayun': ganqing.get('current_dayun'),
            'key_dayuns': ganqing.get('key_dayuns', [])
        }
    }
    
    # ⚠️ 新增：过滤掉所有 deities 数组中的空字符串
    cleaned_data = _filter_empty_deities(copy.deepcopy(optimized_data))
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(cleaned_data, ensure_ascii=False, indent=2)


def format_marriage_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将婚姻分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 3000 字符
    - 优化后约 500 字符
    - Token 减少约 83%
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_zonglun', {})
    peiou = input_data.get('peiou_tezheng', {})
    ganqing = input_data.get('ganqing_zoushi', {})
    jianyi = input_data.get('jianyi_fangxiang', {})
    
    # 1. 命主基本信息
    bazi_pillars = mingpan.get('bazi_pillars', {})
    day_pillar = mingpan.get('day_pillar', {})
    day_stem = day_pillar.get('stem', bazi_pillars.get('day', {}).get('stem', ''))
    day_branch = day_pillar.get('branch', bazi_pillars.get('day', {}).get('branch', ''))
    wangshuai = mingpan.get('wangshuai', '')
    
    # 从喜忌中判断身强身弱
    xi_ji = jianyi.get('xi_ji', {})
    
    lines.append(f"【命主】{day_stem}日元，配偶宫{day_branch}，{wangshuai}")
    
    # 2. 四柱
    pillars_text = format_bazi_pillars_text(bazi_pillars)
    if pillars_text:
        lines.append(f"【四柱】{pillars_text}")
    
    # 3. 十神
    ten_gods = mingpan.get('ten_gods', {})
    ten_gods_text = format_ten_gods_text(ten_gods)
    if ten_gods_text:
        lines.append(f"【十神】{ten_gods_text}")
    
    # 4. 地支关系
    branch_relations = mingpan.get('branch_relations', {})
    relations_text = format_branch_relations_text(branch_relations)
    if relations_text and relations_text != "无":
        lines.append(f"【地支关系】{relations_text}")
    
    # 5. 神煞
    deities = peiou.get('deities', {})
    deities_text = format_deities_text(deities)
    if deities_text and deities_text != "无":
        lines.append(f"【神煞】{deities_text}")
    
    # 6. 婚姻判词（完整保留，不截断）
    marriage_judgments = peiou.get('marriage_judgments', [])
    if marriage_judgments:
        judgments_text = format_judgments_text(marriage_judgments)
        if judgments_text:
            lines.append(f"【婚姻判词】{judgments_text}")
    
    # 7. 桃花判词（完整保留，不截断）
    peach_blossom_judgments = peiou.get('peach_blossom_judgments', [])
    if peach_blossom_judgments:
        judgments_text = format_judgments_text(peach_blossom_judgments)
        if judgments_text:
            lines.append(f"【桃花判词】{judgments_text}")
    
    # 8. 婚配判词（完整保留，不截断）
    matchmaking_judgments = peiou.get('matchmaking_judgments', [])
    if matchmaking_judgments:
        judgments_text = format_judgments_text(matchmaking_judgments)
        if judgments_text:
            lines.append(f"【婚配判词】{judgments_text}")
    
    # 9. 正缘判词（完整保留，不截断）
    zhengyuan_judgments = peiou.get('zhengyuan_judgments', [])
    if zhengyuan_judgments:
        judgments_text = format_judgments_text(zhengyuan_judgments)
        if judgments_text:
            lines.append(f"【正缘判词】{judgments_text}")
    
    # 10-11. 当前大运 + 关键大运与流年（统一使用公共模块）
    lines.extend(format_key_dayuns_text(
        key_dayuns=ganqing.get('key_dayuns', []),
        current_dayun=ganqing.get('current_dayun', {}),
        special_liunians=ganqing.get('special_liunians', [])
    ))
    
    # 12. 喜忌
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    return '\n'.join(lines)


# ==============================================================================
# 事业财富分析格式化函数
# ==============================================================================


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""总评分析 prompt 构建"""

from typing import Dict, Any, List, Optional
from .common import format_bazi_pillars_text, format_ten_gods_text, format_wuxing_distribution_text, format_xi_ji_text, format_deities_text, format_dayun_text, format_liunian_text, format_judgments_text, format_branch_relations_text, format_key_dayuns_text, _simplify_dayun

def format_general_review_input_data_for_coze(input_data: Dict[str, Any]) -> str:
    """
    将结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    ⚠️ 注意：此函数名虽然包含 "for_coze"，但实际上数据格式与平台无关
    相同的 formatted_data 可以同时给 Coze 和百炼使用，实现数据格式解耦
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
    """
    # 获取原始数据
    mingpan = input_data.get('mingpan_hexin_geju', {})
    xingge = input_data.get('xingge_tezhi', {})
    shiye_caiyun = input_data.get('shiye_caiyun', {})
    jiating = input_data.get('jiating_liuqin', {})
    jiankang = input_data.get('jiankang_yaodian', {})
    guanjian = input_data.get('guanjian_dayun', {})
    zhongsheng = input_data.get('zhongsheng_tidian', {})
    rizhu_xinming = input_data.get('rizhu_xinming_jiexi', {})  # 新增：日柱性命解析
    
    # ⚠️ 方案2：优化数据结构，使用引用避免重复
    optimized_data = {
        # 1. 命盘核心格局（基础数据，只提取一次）
        'mingpan_hexin_geju': mingpan,
        
        # 2. 性格特质（引用数据，不重复存储）
        'xingge_tezhi': {
            'day_master_personality': xingge.get('day_master_personality', []),
            'rizhu_algorithm': xingge.get('rizhu_algorithm', ''),
            'ten_gods_effect': xingge.get('ten_gods_effect', '')
        },
        
        # 3. 事业财运轨迹（引用数据，不重复存储）
        'shiye_caiyun': {
            'shiye_xing': shiye_caiyun.get('shiye_xing', {}),
            'caifu_xing': shiye_caiyun.get('caifu_xing', {}),
            'dayun_effect': shiye_caiyun.get('dayun_effect', {})
        },
        
        # 4. 家庭六亲关系（引用数据，不重复存储）
        'jiating_liuqin': {
            'year_pillar': jiating.get('year_pillar', {}),
            'month_pillar': jiating.get('month_pillar', {}),
            'day_pillar': jiating.get('day_pillar', {}),
            'hour_pillar': jiating.get('hour_pillar', {})
        },
        
        # 5. 健康要点（引用数据，不重复存储）
        'jiankang_yaodian': {
            'wuxing_balance': jiankang.get('wuxing_balance', {}),
            'zangfu_duiying': jiankang.get('zangfu_duiying', {}),
            'jiankang_ruodian': jiankang.get('jiankang_ruodian', {})
        },
        
        # 6. 关键大运与人生节点（引用数据，不重复存储）
        # ⚠️ 修改：不再限制大运数量，所有包含特殊流年的大运都要显示
        'guanjian_dayun': {
            'current_dayun': _simplify_dayun(guanjian.get('current_dayun')),
            'key_dayuns': [_simplify_dayun(d) for d in guanjian.get('key_dayuns', [])],  # 不限制数量，显示所有关键大运
            # dayun_sequence 太大（可能超过400KB），不传给 Coze Bot
            'chonghe_xinghai': guanjian.get('chonghe_xinghai', {})
        },
        
        # 7. 终生提点与建议（引用数据，不重复存储）
        'zhongsheng_tidian': {
            'xishen': zhongsheng.get('xishen', {}),
            'jishen': zhongsheng.get('jishen', {}),
            'xishen_wuxing': zhongsheng.get('xishen_wuxing', []),
            'jishen_wuxing': zhongsheng.get('jishen_wuxing', []),
            'fangwei_xuanze': zhongsheng.get('fangwei_xuanze', {}),
            'hangye_xuanze': zhongsheng.get('hangye_xuanze', {}),
            'xiushen_jianyi': zhongsheng.get('xiushen_jianyi', {}),
            'fengshui_tiaojie': zhongsheng.get('fengshui_tiaojie', {})
        },
        
        # 8. 日柱性命解析（新增：完整的日柱性格与命运分析数据）
        'rizhu_xinming_jiexi': {
            'rizhu': rizhu_xinming.get('rizhu', ''),
            'gender': rizhu_xinming.get('gender', ''),
            'gender_display': rizhu_xinming.get('gender_display', ''),
            'descriptions': rizhu_xinming.get('descriptions', []),  # 完整的31条数据
            'descriptions_count': rizhu_xinming.get('descriptions_count', 0),
            'summary': rizhu_xinming.get('summary', '')
        }
    }
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(optimized_data, ensure_ascii=False, indent=2)


def format_general_review_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将总评分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 5000 字符
    - 优化后约 700 字符
    - Token 减少约 86%
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_hexin_geju', {})
    xingge = input_data.get('xingge_tezhi', {})
    shiye_caiyun = input_data.get('shiye_caiyun', {})
    jiating = input_data.get('jiating_liuqin', {})
    jiankang = input_data.get('jiankang_yaodian', {})
    guanjian = input_data.get('guanjian_dayun', {})
    zhongsheng = input_data.get('zhongsheng_tidian', {})
    rizhu_xinming = input_data.get('rizhu_xinming_jiexi', {})
    
    # 1. 命主基本信息
    day_master = mingpan.get('day_master', {})
    day_stem = day_master.get('stem', '')
    day_element = day_master.get('element', '')
    wangshuai = mingpan.get('wangshuai', '')
    yue_ling = mingpan.get('yue_ling', '')
    
    lines.append(f"【命主】{day_stem}{day_element}日元，{wangshuai}，月令{yue_ling}")
    
    # 2. 四柱
    bazi_pillars = mingpan.get('bazi_pillars', {})
    pillars_text = format_bazi_pillars_text(bazi_pillars)
    if pillars_text:
        lines.append(f"【四柱】{pillars_text}")
    
    # 3. 格局
    geju_type = mingpan.get('geju_type', '')
    if geju_type:
        lines.append(f"【格局】{geju_type}")
    
    # 4. 十神
    ten_gods = mingpan.get('ten_gods', {})
    ten_gods_text = format_ten_gods_text(ten_gods)
    if ten_gods_text:
        lines.append(f"【十神】{ten_gods_text}")
    
    # 5. 性格特质（完整保留）
    day_master_personality = xingge.get('day_master_personality', [])
    if day_master_personality:
        personality_texts = []
        for p in day_master_personality:
            if isinstance(p, str):
                personality_texts.append(p)
            elif isinstance(p, dict):
                personality_texts.append(p.get('description', str(p)))
        if personality_texts:
            lines.append(f"【性格特质】{'；'.join(personality_texts)}")
    
    # 6. 事业星
    shiye_xing = shiye_caiyun.get('shiye_xing', {})
    if shiye_xing:
        primary = shiye_xing.get('primary', '')
        if primary:
            lines.append(f"【事业星】{primary}")
    
    # 7. 财富星
    caifu_xing = shiye_caiyun.get('caifu_xing', {})
    if caifu_xing:
        primary = caifu_xing.get('primary', '')
        if primary:
            lines.append(f"【财富星】{primary}")
    
    # 8. 家庭六亲
    liuqin_parts = []
    year_pillar = jiating.get('year_pillar', {})
    if year_pillar:
        main_star = year_pillar.get('main_star', '')
        if main_star:
            liuqin_parts.append(f"年柱{main_star}")
    month_pillar = jiating.get('month_pillar', {})
    if month_pillar:
        main_star = month_pillar.get('main_star', '')
        if main_star:
            liuqin_parts.append(f"月柱{main_star}")
    hour_pillar = jiating.get('hour_pillar', {})
    if hour_pillar:
        main_star = hour_pillar.get('main_star', '')
        if main_star:
            liuqin_parts.append(f"时柱{main_star}")
    if liuqin_parts:
        lines.append(f"【家庭六亲】{'、'.join(liuqin_parts)}")
    
    # 9. 健康要点（完整保留）
    wuxing_balance = jiankang.get('wuxing_balance', {})
    jiankang_ruodian = jiankang.get('jiankang_ruodian', {})
    health_parts = []
    if wuxing_balance:
        if isinstance(wuxing_balance, str):
            health_parts.append(f"五行平衡:{wuxing_balance}")
        elif isinstance(wuxing_balance, dict):
            health_parts.append(f"五行平衡:{str(wuxing_balance)}")
    if jiankang_ruodian:
        if isinstance(jiankang_ruodian, str):
            health_parts.append(f"弱点:{jiankang_ruodian}")
        elif isinstance(jiankang_ruodian, dict):
            for k, v in jiankang_ruodian.items():
                health_parts.append(f"{k}:{v}")
        elif isinstance(jiankang_ruodian, list):
            health_parts.append(f"弱点:{'、'.join(str(r) for r in jiankang_ruodian)}")
    if health_parts:
        lines.append(f"【健康要点】{'；'.join(health_parts)}")
    
    # 10. 辅助函数：从 dayun 数据中提取干支（兼容 ganzhi / stem+branch / gan+zhi）
    def _get_dayun_ganzhi(dayun_item: Dict[str, Any]) -> str:
        gz = dayun_item.get('ganzhi', '')
        if not gz:
            stem = dayun_item.get('stem', dayun_item.get('gan', ''))
            branch = dayun_item.get('branch', dayun_item.get('zhi', ''))
            gz = f"{stem}{branch}"
        return gz
    
    # 11. 完整大运序列（让 LLM 知道每步大运的干支和主星），只传前10个
    dayun_sequence = guanjian.get('dayun_sequence', [])
    if dayun_sequence:
        seq_parts = []
        for dayun in dayun_sequence[:10]:
            gz = _get_dayun_ganzhi(dayun)
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            main_star = dayun.get('main_star', '')
            star_text = f"，{main_star}" if main_star else ''
            seq_parts.append(f"第{step}运{gz}({age_display}{star_text})")
        if seq_parts:
            lines.append(f"【大运序列】{'；'.join(seq_parts)}")
    
    # 12-13. 当前大运 + 关键大运与流年（统一使用公共模块）
    lines.extend(format_key_dayuns_text(
        key_dayuns=guanjian.get('key_dayuns', []),
        current_dayun=guanjian.get('current_dayun', {}),
        special_liunians=guanjian.get('special_liunians', [])
    ))
    
    # 12. 喜忌
    xishen_wuxing = zhongsheng.get('xishen_wuxing', [])
    jishen_wuxing = zhongsheng.get('jishen_wuxing', [])
    if xishen_wuxing or jishen_wuxing:
        xi_text = ''.join(xishen_wuxing) if xishen_wuxing else '无'
        ji_text = ''.join(jishen_wuxing) if jishen_wuxing else '无'
        lines.append(f"【喜忌】喜{xi_text}，忌{ji_text}")
    
    # 13. 方位建议
    fangwei = zhongsheng.get('fangwei_xuanze', {})
    if fangwei:
        best = fangwei.get('best_directions', [])
        if best:
            lines.append(f"【方位】宜{'/'.join(best[:3])}")
    
    # 14. 行业建议
    hangye = zhongsheng.get('hangye_xuanze', {})
    if hangye:
        best = hangye.get('best_industries', [])
        if best:
            lines.append(f"【行业】宜{'/'.join(best[:5])}")
    
    # 15. 日柱解析（完整保留）
    rizhu = rizhu_xinming.get('rizhu', '')
    gender_display = rizhu_xinming.get('gender_display', '')
    if rizhu:
        descriptions = rizhu_xinming.get('descriptions', [])
        desc_text = ''
        if descriptions:
            desc_text = '；'.join([str(d) for d in descriptions])
        lines.append(f"【日柱解析】{rizhu}{gender_display}命，{desc_text}")
    
    return '\n'.join(lines)



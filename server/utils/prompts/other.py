#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能分析、年运、面相、风水 prompt 构建"""

import json
from typing import Dict, Any, Optional
from .common import format_bazi_pillars_text, format_ten_gods_text, format_wuxing_distribution_text, format_xi_ji_text, format_deities_text, format_dayun_text, format_liunian_text, format_judgments_text, format_branch_relations_text, format_key_dayuns_text, _simplify_dayun

def format_smart_fortune_for_llm(
    bazi_data: Dict[str, Any],
    fortune_context: Dict[str, Any],
    matched_rules: list,
    question: str,
    intent: str,
    category: Optional[str] = None,
    history_context: list = None
) -> str:
    """
    将智能运势分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 2500 字符
    - 优化后约 400 字符
    - Token 减少约 84%
    
    Args:
        bazi_data: 八字数据
        fortune_context: 流年大运上下文
        matched_rules: 匹配的规则
        question: 用户问题
        intent: 用户意图
        category: 分类（可选）
        history_context: 历史对话上下文（可选）
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 1. 提取八字数据
    bazi_pillars = (
        bazi_data.get('bazi_pillars') or 
        bazi_data.get('bazi', {}).get('bazi_pillars') or 
        {}
    )
    
    day_stem = (
        bazi_data.get('day_stem') or
        bazi_pillars.get('day', {}).get('stem', '')
    )
    
    basic_info = (
        bazi_data.get('basic_info') or
        bazi_data.get('bazi', {}).get('basic_info') or
        {}
    )
    
    gender = basic_info.get('gender', '')
    gender_display = '男命' if gender == 'male' else '女命' if gender == 'female' else ''
    
    # 2. 命主信息
    lines.append(f"【命主】{day_stem}日元，{gender_display}")
    
    # 3. 四柱
    pillars_text = format_bazi_pillars_text(bazi_pillars)
    if pillars_text:
        lines.append(f"【四柱】{pillars_text}")
    
    # 4. 十神
    ten_gods = (
        bazi_data.get('ten_gods') or
        bazi_data.get('bazi', {}).get('ten_gods') or
        {}
    )
    ten_gods_text = format_ten_gods_text(ten_gods)
    if ten_gods_text:
        lines.append(f"【十神】{ten_gods_text}")
    
    # 5. 五行分布
    element_counts = (
        bazi_data.get('element_counts') or
        bazi_data.get('bazi', {}).get('element_counts') or
        {}
    )
    if element_counts:
        wuxing_text = format_wuxing_distribution_text(element_counts)
        if wuxing_text:
            lines.append(f"【五行】{wuxing_text}")
    
    # 6. 喜忌
    wangshuai = bazi_data.get('wangshuai', {})
    if wangshuai:
        final_xi_ji = wangshuai.get('final_xi_ji', {})
        xi_elements = final_xi_ji.get('xi_shen_elements', [])
        ji_elements = final_xi_ji.get('ji_shen_elements', [])
        
        if xi_elements or ji_elements:
            xi_text = ''.join(xi_elements) if xi_elements else '无'
            ji_text = ''.join(ji_elements) if ji_elements else '无'
            lines.append(f"【喜忌】喜{xi_text}，忌{ji_text}")
    
    # 7. 大运流年（统一使用公共模块）
    if fortune_context:
        lines.extend(format_key_dayuns_text(
            key_dayuns=fortune_context.get('key_dayuns', []),
            current_dayun=fortune_context.get('current_dayun', {}),
            special_liunians=fortune_context.get('special_liunians', fortune_context.get('key_liunians', []))
        ))
    
    # 8. 匹配规则（保留完整判词，不只是规则名）
    if matched_rules:
        rule_texts = []
        for rule in matched_rules:
            rule_name = rule.get('rule_name', rule.get('name', ''))
            rule_text = rule.get('text', rule.get('judgment_text', ''))
            if rule_name and rule_text:
                rule_texts.append(f"{rule_name}:{rule_text}")
            elif rule_name:
                rule_texts.append(rule_name)
            elif rule_text:
                rule_texts.append(rule_text)
        if rule_texts:
            lines.append(f"【匹配规则】{'；'.join(rule_texts)}")
    
    # 9. 用户问题
    lines.append(f"【用户问题】{question}")
    
    # 10. 问题类型
    if category:
        lines.append(f"【问题类型】{category}")
    elif intent:
        lines.append(f"【意图】{intent}")
    
    # 11. 历史上下文（保留完整摘要）
    if history_context:
        history_parts = []
        for h in history_context:
            round_num = h.get('round', '')
            keywords = h.get('keywords', [])
            summary = h.get('summary', h.get('content', ''))
            if summary:
                history_parts.append(f"第{round_num}轮:{summary}")
            elif keywords:
                history_parts.append(f"第{round_num}轮:{'/'.join(keywords)}")
        if history_parts:
            lines.append(f"【历史上下文】{'；'.join(history_parts)}")
    
    # 12. 语言风格要求
    lines.append("【语言风格】通俗易懂，避免专业术语，用日常语言解释命理概念")
    
    return '\n'.join(lines)


def format_annual_report_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将年运报告分析数据格式化为中文文本（用于 LLM Prompt）
    
    ⚠️ 信息零丢失原则：保留所有关键信息，不截断不过滤
    包括：太岁完整描述、躲星时间、化解方法完整内容、
    12月流月完整影响、九宫飞星完整方位、立春建议、
    所有含特殊流年的大运等
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_analysis', {})
    monthly = input_data.get('monthly_analysis', {})
    taisui = input_data.get('taisui_info', {})
    fengshui = input_data.get('fengshui_info', {})
    dayun_liunian = input_data.get('dayun_liunian', {})
    
    # ⚠️ 年份锁定指令：防止百炼平台系统提示词中的年份覆盖后端计算的正确年份
    target_year = monthly.get('year', taisui.get('year', ''))
    if target_year:
        lines.append(f"【年份锁定指令 — 最高优先级】")
        lines.append(f"本报告仅针对{target_year}年。以下所有数据（太岁、九宫飞星、流月、犯太岁属相等）已由系统精确计算完成。")
        lines.append(f"你必须严格使用下方数据输出报告，禁止替换为其他年份信息。若你的知识与下方数据冲突，以下方数据为准。")
        lines.append("")

    # 命主画像数据（用户分层 + 命盘状态标记，指导报告主线和叙事策略）
    user_profile = input_data.get('user_profile', {})
    if user_profile:
        lines.append("【命主画像数据】")
        gender_str = "男" if user_profile.get("gender") == "male" else "女"
        age = user_profile.get("age", "")
        if age:
            lines.append(f"性别：{gender_str}，年龄：{age}岁（{user_profile.get('age_group', '')}）")
        else:
            lines.append(f"性别：{gender_str}")
        focus = user_profile.get("focus_priority", [])
        if focus:
            main_topics = "、".join(focus[:2]) if len(focus) >= 2 else focus[0]
            lines.append(f"报告主线（请重点展开）：{main_topics}；财运（常规输出）")
        bazi_states = user_profile.get("bazi_states", {})
        if bazi_states:
            state_parts = [f"{k}:{v}" for k, v in bazi_states.items() if v and k != "health_focus"]
            if state_parts:
                lines.append(f"命盘状态标记：{'，'.join(state_parts)}")
            health_focus = bazi_states.get("health_focus", [])
            if health_focus:
                lines.append(f"健康重点关注脏腑：{'、'.join(health_focus)}")
        user_tags = user_profile.get("user_tags", {})
        if user_tags:
            tag_parts = [f"{k}:{v}" for k, v in user_tags.items() if v]
            if tag_parts:
                lines.append(f"用户自报状态：{'，'.join(tag_parts)}")
        lines.append("")

    # 1. 命主基本信息
    bazi_pillars = mingpan.get('bazi_pillars', {})
    pillars_text = format_bazi_pillars_text(bazi_pillars)
    if pillars_text:
        lines.append(f"【四柱】{pillars_text}")
    
    # 2. 五行分布
    element_counts = mingpan.get('element_counts', {})
    if element_counts:
        wuxing_text = format_wuxing_distribution_text(element_counts)
        if wuxing_text:
            lines.append(f"【五行分布】{wuxing_text}")
    
    # 3. 旺衰
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        lines.append(f"【旺衰】{wangshuai}")
    
    # 4. 喜忌（完整保留）
    xi_ji = mingpan.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    # 5. 流年信息
    year = monthly.get('year', taisui.get('year', ''))
    if year:
        lines.append(f"【流年】{year}年")
    
    # 6. 太岁信息（完整保留描述，不截断）
    taisui_name = taisui.get('taisui_name', '')
    taisui_desc = taisui.get('taisui_description', '')
    if taisui_name:
        taisui_text = taisui_name
        if taisui_desc:
            taisui_text += f"，{taisui_desc}"
        lines.append(f"【太岁】{taisui_text}")
    
    # 7. 犯太岁
    fanshaisui = taisui.get('fanshaisui', {})
    if fanshaisui:
        fan_parts = [f"{k}{v}" for k, v in fanshaisui.items() if v]
        if fan_parts:
            lines.append(f"【犯太岁】{'、'.join(fan_parts)}")
    
    # 8. 躲星时间（旧版保留，新版曾丢失）
    duoxing_times = taisui.get('duoxing_times', {})
    if duoxing_times:
        if isinstance(duoxing_times, dict):
            duoxing_parts = [f"{k}:{v}" for k, v in duoxing_times.items() if v]
            if duoxing_parts:
                lines.append(f"【躲星时间】{'；'.join(duoxing_parts)}")
        elif isinstance(duoxing_times, str):
            lines.append(f"【躲星时间】{duoxing_times}")
    
    # 9. 化解方法（完整保留，不截断不限数量）
    resolution = taisui.get('resolution', {})
    if resolution:
        if isinstance(resolution, dict):
            resolution_parts = [f"{k}:{v}" for k, v in resolution.items() if v]
            if resolution_parts:
                lines.append(f"【化解方法】{'；'.join(resolution_parts)}")
        elif isinstance(resolution, list):
            if resolution:
                lines.append(f"【化解方法】{'；'.join(str(m) for m in resolution)}")
        elif isinstance(resolution, str):
            lines.append(f"【化解方法】{resolution}")
    
    # 10. 方神信息（旧版保留，新版曾丢失）
    fangshen = taisui.get('fangshen', {})
    if fangshen:
        if isinstance(fangshen, dict):
            fangshen_parts = [f"{k}:{v}" for k, v in fangshen.items() if v]
            if fangshen_parts:
                lines.append(f"【方神】{'；'.join(fangshen_parts)}")
        elif isinstance(fangshen, str):
            lines.append(f"【方神】{fangshen}")
    
    # 11. 流月运势（12月完整保留，不截断 yingxiang）
    months = monthly.get('months', [])
    if months:
        for m in months:
            month_num = m.get('month', '')
            ganzhi = m.get('ganzhi', '')
            jieqi = m.get('jieqi', '')
            yingxiang = m.get('yingxiang', '')
            wuxing_effect = m.get('wuxing_effect', '')
            
            month_text = f"{month_num}月{ganzhi}({jieqi})"
            if yingxiang:
                month_text += f":{yingxiang}"
            if wuxing_effect:
                month_text += f"，五行影响:{wuxing_effect}"
            lines.append(f"【流月{month_num}】{month_text}")
    
    # 12. 九宫飞星（完整方位信息）
    jiugong = fengshui.get('jiugong_feixing', {})
    wuhuang = fengshui.get('wuhuang', {})
    erhei = fengshui.get('erhei', {})
    
    if jiugong:
        # 输出所有星位
        jiugong_parts = []
        if isinstance(jiugong, dict):
            for star, info in jiugong.items():
                if isinstance(info, dict):
                    position = info.get('position', info.get('direction', ''))
                    meaning = info.get('meaning', info.get('description', ''))
                    jiugong_parts.append(f"{star}飞{position}" + (f"({meaning})" if meaning else ""))
                elif isinstance(info, str):
                    jiugong_parts.append(f"{star}:{info}")
        if jiugong_parts:
            lines.append(f"【九宫飞星】{'；'.join(jiugong_parts)}")
    
    fengshui_alert_parts = []
    if wuhuang:
        position = wuhuang.get('position', '')
        direction = wuhuang.get('direction', '')
        warning = wuhuang.get('warning', wuhuang.get('description', ''))
        wuhuang_text = f"五黄在{position or direction}"
        if warning:
            wuhuang_text += f"({warning})"
        fengshui_alert_parts.append(wuhuang_text)
    if erhei:
        position = erhei.get('position', '')
        direction = erhei.get('direction', '')
        warning = erhei.get('warning', erhei.get('description', ''))
        erhei_text = f"二黑在{position or direction}"
        if warning:
            erhei_text += f"({warning})"
        fengshui_alert_parts.append(erhei_text)
    if fengshui_alert_parts:
        lines.append(f"【凶星方位】{'，'.join(fengshui_alert_parts)}")
    
    # 13. 避煞时间（完整保留，不用硬编码）
    bixing_times = fengshui.get('bixing_times', {})
    if bixing_times:
        if isinstance(bixing_times, dict):
            bixing_parts = [f"{k}:{v}" for k, v in bixing_times.items() if v]
            if bixing_parts:
                lines.append(f"【避煞时间】{'；'.join(bixing_parts)}")
        elif isinstance(bixing_times, list):
            lines.append(f"【避煞时间】{'；'.join(str(b) for b in bixing_times)}")
        elif isinstance(bixing_times, str):
            lines.append(f"【避煞时间】{bixing_times}")
    
    # 14. 立春建议（旧版保留，新版曾丢失）
    lichun_suggestions = fengshui.get('lichun_suggestions', {})
    if lichun_suggestions:
        if isinstance(lichun_suggestions, dict):
            lichun_parts = [f"{k}:{v}" for k, v in lichun_suggestions.items() if v]
            if lichun_parts:
                lines.append(f"【立春建议】{'；'.join(lichun_parts)}")
        elif isinstance(lichun_suggestions, list):
            lines.append(f"【立春建议】{'；'.join(str(s) for s in lichun_suggestions)}")
        elif isinstance(lichun_suggestions, str):
            lines.append(f"【立春建议】{lichun_suggestions}")
    
    # 15. 大运流年数据（完整保留所有含特殊流年的大运）
    dayuns = dayun_liunian.get('dayuns', [])
    target_year_liunian = dayun_liunian.get('target_year_liunian', None)
    
    # 目标年份特殊流年（旧版保留，新版曾丢失）
    if target_year_liunian:
        year_ganzhi = target_year_liunian.get('ganzhi', '')
        type_display = target_year_liunian.get('type_display', '')
        relations = target_year_liunian.get('relations', [])
        relation_texts = []
        for r in relations:
            if isinstance(r, dict):
                relation_texts.append(r.get('type', ''))
            elif isinstance(r, str):
                relation_texts.append(r)
        relation_text = '/'.join(filter(None, relation_texts)) or type_display
        if relation_text:
            lines.append(f"【目标年份特殊关系】{year}{year_ganzhi}({relation_text})")
    
    if dayuns:
        # 找到包含目标年份的大运（当前大运）
        current_dayun = None
        for dayun in dayuns:
            liunians = dayun.get('liunians', [])
            for ln in liunians:
                if str(ln.get('year', '')) == str(year):
                    current_dayun = dayun
                    break
            if current_dayun:
                break
        
        # 使用公共模块格式化大运+流年（排序、流年归属、阶段标准化）
        lines.extend(format_key_dayuns_text(
            key_dayuns=dayuns,
            current_dayun=current_dayun,
            special_liunians=dayun_liunian.get('special_liunians', [])
        ))
    
    return '\n'.join(lines)


# 面相分析V2格式化函数

def format_face_analysis_input_data_for_coze(input_data: Dict[str, Any]) -> str:
    """
    将面相分析结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
    
    Args:
        input_data: 面相分析响应数据（包含 success 和 data 字段）
        
    Returns:
        str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
    """
    # 提取 data 字段
    data = input_data.get('data', {}) if isinstance(input_data, dict) else {}
    
    # 构建优化后的数据结构
    optimized_data = {
        'face_detected': data.get('face_detected', False),
        'landmarks': data.get('landmarks', {}),
        'santing_analysis': data.get('santing_analysis', {}),
        'wuyan_analysis': data.get('wuyan_analysis', {}),
        'gongwei_analysis': data.get('gongwei_analysis', []),
        'liuqin_analysis': data.get('liuqin_analysis', []),
        'shishen_analysis': data.get('shishen_analysis', []),
        'overall_summary': data.get('overall_summary', ''),
        'birth_info': data.get('birth_info')
    }
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(optimized_data, ensure_ascii=False, indent=2)


# 办公桌风水分析格式化函数

def format_desk_fengshui_input_data_for_coze(input_data: Dict[str, Any]) -> str:
    """
    将办公桌风水分析结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
    
    Args:
        input_data: 办公桌风水分析结果数据
        
    Returns:
        str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
    """
    # 如果输入数据包含 success 字段，提取 data
    if isinstance(input_data, dict) and 'success' in input_data:
        data = input_data.get('data', input_data)
    else:
        data = input_data
    
    # 构建优化后的数据结构
    optimized_data = {
        'success': data.get('success', True),
        'items': data.get('items', []),
        'item_analyses': data.get('item_analyses', []),
        'recommendations': data.get('recommendations', {}),
        'adjustments': data.get('adjustments', []),
        'additions': data.get('additions', []),
        'removals': data.get('removals', []),
        'score': data.get('score', 0),
        'summary': data.get('summary', '')
    }
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(optimized_data, ensure_ascii=False, indent=2)




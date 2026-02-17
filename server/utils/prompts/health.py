#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""健康分析 prompt 构建"""

from typing import Dict, Any
from .common import format_bazi_pillars_text, format_ten_gods_text, format_wuxing_distribution_text, format_xi_ji_text, format_deities_text, format_dayun_text, format_liunian_text, format_judgments_text, format_branch_relations_text, format_key_dayuns_text

def build_health_prompt(data: dict) -> str:
    """
    将JSON数据转换为自然语言格式的提示词（健康分析）
    
    Args:
        data: 分析所需的完整数据
        
    Returns:
        str: 自然语言格式的提示词
    """
    prompt_lines = []
    prompt_lines.append("请基于以下八字信息进行健康分析，分别从以下方面进行详细分析：")
    prompt_lines.append("")
    
    # 1. 命盘体质总论
    prompt_lines.append("【命盘体质总论】")
    section1 = data.get('mingpan_tizhi_zonglun', {})
    
    # ⚠️ 重要：输出完整的四柱信息
    bazi_pillars = section1.get('bazi_pillars', {})
    if bazi_pillars:
        year_pillar = bazi_pillars.get('year', {})
        month_pillar = bazi_pillars.get('month', {})
        day_pillar = bazi_pillars.get('day', {})
        hour_pillar = bazi_pillars.get('hour', {})
        
        # 构建四柱字符串
        pillars_list = []
        if year_pillar.get('stem') and year_pillar.get('branch'):
            pillars_list.append(f"{year_pillar.get('stem')}{year_pillar.get('branch')}")
        if month_pillar.get('stem') and month_pillar.get('branch'):
            pillars_list.append(f"{month_pillar.get('stem')}{month_pillar.get('branch')}")
        if day_pillar.get('stem') and day_pillar.get('branch'):
            pillars_list.append(f"{day_pillar.get('stem')}{day_pillar.get('branch')}")
        if hour_pillar.get('stem') and hour_pillar.get('branch'):
            pillars_list.append(f"{hour_pillar.get('stem')}{hour_pillar.get('branch')}")
        
        if pillars_list:
            prompt_lines.append(f"四柱：{' '.join(pillars_list)}")
    
    day_master = section1.get('day_master', {})
    if day_master.get('stem'):
        prompt_lines.append(f"日主：{day_master.get('stem')}{day_master.get('branch')}（{day_master.get('element', '')}）")
    if section1.get('wangshuai'):
        prompt_lines.append(f"旺衰：{section1.get('wangshuai')}")
    if section1.get('yue_ling'):
        prompt_lines.append(f"月令：{section1.get('yue_ling')}")
    if section1.get('wuxing_balance'):
        prompt_lines.append(f"五行平衡：{section1.get('wuxing_balance')}")
    
    elements = section1.get('elements', {})
    if elements:
        element_str = ', '.join([f"{k}: {v}" for k, v in elements.items() if v > 0])
        prompt_lines.append(f"五行分布：{element_str}")
    prompt_lines.append("")
    
    # 2. 五行病理推演
    prompt_lines.append("【五行病理推演】")
    section2 = data.get('wuxing_bingli', {})
    
    body_algorithm = section2.get('body_algorithm', {})
    if body_algorithm:
        organ_analysis = body_algorithm.get('organ_analysis', {})
        if organ_analysis:
            prompt_lines.append("五行五脏对应：")
            for organ, analysis in organ_analysis.items():
                element = analysis.get('element', '')
                strength = analysis.get('strength', '')
                health_status = analysis.get('health_status', '')
                prompt_lines.append(f"  {organ}（{element}）：{strength}，{health_status}")
    
    pathology_tendency = section2.get('pathology_tendency', {})
    if pathology_tendency:
        pathology_list = pathology_tendency.get('pathology_list', [])
        if pathology_list:
            prompt_lines.append("病理倾向：")
            for pathology in pathology_list:
                organ = pathology.get('organ', '')
                tendency = pathology.get('tendency', '')
                risk = pathology.get('risk', '')
                prompt_lines.append(f"  {organ}（{tendency}）：{risk}")
    prompt_lines.append("")
    
    # 3. 大运流年健康警示（按照新格式）
    section3 = data.get('dayun_jiankang', {})
    
    # 现行运
    current_dayun = section3.get('current_dayun')
    if current_dayun:
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        
        prompt_lines.append(f"**现行{step}运（{age_display}）：**")
        prompt_lines.append(f"- 大运：{stem}{branch}")
        prompt_lines.append("- [分析当前大运的五行特征对健康的影响]")
        
        # 列举关键流年（按优先级，数量灵活）
        liunians = current_dayun.get('liunians', {})
        if any(liunians.values()):
            prompt_lines.append("- [列举关键流年及健康风险]：")
            
            # 按优先级列出：天克地冲 > 天合地合 > 岁运并临 > 其他
            for liunian in liunians.get('tiankedi_chong', []):
                year = liunian.get('year', '')
                if year:
                    prompt_lines.append(f"  - {year}年：[分析该年的健康风险]")
            
            for liunian in liunians.get('tianhedi_he', []):
                year = liunian.get('year', '')
                if year:
                    prompt_lines.append(f"  - {year}年：[分析该年的健康风险]")
            
            for liunian in liunians.get('suiyun_binglin', []):
                year = liunian.get('year', '')
                if year:
                    prompt_lines.append(f"  - {year}年：[分析该年的健康风险]")
            
            for liunian in liunians.get('other', []):
                year = liunian.get('year', '')
                if year:
                    prompt_lines.append(f"  - {year}年：[分析该年的健康风险]")
        
        prompt_lines.append("")
    
    # 关键节点大运（只保留前10步，step <= 10）
    key_dayuns = section3.get('key_dayuns', [])
    if key_dayuns:
        # 获取完整的大运序列（用于格式化流年）
        all_dayuns = section3.get('all_dayuns', [])
        dayun_sequence_for_format = all_dayuns if all_dayuns else []
        for key_dayun in key_dayuns:
            step_num = int(key_dayun.get('step', 0) or 0)
            if step_num > 10:
                continue
            step = key_dayun.get('step', '')
            age_display = key_dayun.get('age_display', '')
            stem = key_dayun.get('stem', '')
            branch = key_dayun.get('branch', '')
            relation_type = key_dayun.get('relation_type', '')
            
            prompt_lines.append(f"**关键节点：{step}运（{age_display}）：**")
            prompt_lines.append(f"- 大运：{stem}{branch}")
            prompt_lines.append("- [分析该大运的五行特征，是否为调候用神出现]")
            if relation_type:
                prompt_lines.append(f"- [分析该运与原局的生克关系，如{relation_type}等]")
            prompt_lines.append("- 利好：[分析该运对健康的积极影响]")
            
            # 挑战：列出高风险流年（天克地冲 + 岁运并临）
            liunians = key_dayun.get('liunians', {})
            high_risk_liunians = liunians.get('tiankedi_chong', []) + liunians.get('suiyun_binglin', [])
            
            if high_risk_liunians:
                prompt_lines.append("- 挑战：[分析该运的健康风险，如")
                for liunian in high_risk_liunians:  # 不限制数量，保留所有流年
                    year = liunian.get('year', '')
                    relations = liunian.get('relations', [])
                    relation_type_str = ''
                    if relations and len(relations) > 0:
                        relation_type_str = relations[0].get('type', '')
                    if year:
                        if relation_type_str:
                            prompt_lines.append(f"  {year}年（{relation_type_str}），")
                        else:
                            prompt_lines.append(f"  {year}年，")
                prompt_lines.append("需重点防范XX]")
            
            prompt_lines.append("")
    
    # 4. 体质调理建议
    prompt_lines.append("【体质调理建议】")
    section4 = data.get('tizhi_tiaoli', {})
    
    xi_ji = section4.get('xi_ji', {})
    if xi_ji.get('xi_shen'):
        prompt_lines.append(f"喜神：{xi_ji.get('xi_shen')}")
    if xi_ji.get('ji_shen'):
        prompt_lines.append(f"忌神：{xi_ji.get('ji_shen')}")
    
    wuxing_tiaohe = section4.get('wuxing_tiaohe', {})
    if wuxing_tiaohe:
        tuning_suggestions = wuxing_tiaohe.get('tuning_suggestions', [])
        if tuning_suggestions:
            prompt_lines.append("五行调和方案：")
            for tuning in tuning_suggestions:
                organ = tuning.get('organ', '')
                direction = tuning.get('direction', '')
                reason = tuning.get('reason', '')
                prompt_lines.append(f"  {organ}（{direction}）：{reason}")
    
    zangfu_yanghu = section4.get('zangfu_yanghu', {})
    if zangfu_yanghu:
        care_suggestions = zangfu_yanghu.get('care_suggestions', [])
        if care_suggestions:
            prompt_lines.append("脏腑养护建议：")
            for care in care_suggestions:
                organ = care.get('organ', '')
                priority = care.get('priority', '')
                care_focus = care.get('care_focus', '')
                prompt_lines.append(f"  {organ}（优先级：{priority}，重点：{care_focus}）")
    prompt_lines.append("")
    
    # 5. 健康规则参考（NEW）
    prompt_lines.append("【健康规则参考】")
    health_rules = data.get('health_rules', {})
    matched_rules = health_rules.get('matched_rules', [])
    if matched_rules:
        prompt_lines.append(f"匹配到 {len(matched_rules)} 条健康规则：")
        for i, rule in enumerate(matched_rules[:20], 1):  # 最多显示20条
            rule_name = rule.get('name', f'规则{i}')
            rule_content = rule.get('content', {})
            if isinstance(rule_content, dict):
                rule_text = rule_content.get('text', '')
            else:
                rule_text = str(rule_content)
            if rule_text:
                prompt_lines.append(f"{i}. {rule_name}：{rule_text}")
            else:
                prompt_lines.append(f"{i}. {rule_name}：{rule.get('description', '')}")
    else:
        prompt_lines.append("（暂无匹配的健康规则）")
    prompt_lines.append("")
    
    prompt_lines.append("请基于以上信息，进行详细的健康分析，包括：")
    prompt_lines.append("1. 体质特征与健康基础")
    prompt_lines.append("2. 五行失衡与病理倾向")
    prompt_lines.append("3. 大运流年健康风险预警")
    prompt_lines.append("4. 针对性调理与养护建议")
    
    return '\n'.join(prompt_lines)


# ==============================================================================
# 婚姻分析格式化函数
# ==============================================================================


def format_health_input_data_for_coze(input_data: Dict[str, Any]) -> str:
    """
    将健康分析的结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        input_data: 结构化输入数据（健康分析格式）
        
    Returns:
        str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
    """
    # 获取健康分析的数据结构
    mingpan = input_data.get('mingpan_tizhi_zonglun', {})
    wuxing_bingli = input_data.get('wuxing_bingli', {})
    dayun_jiankang = input_data.get('dayun_jiankang', {})
    tizhi_tiaoli = input_data.get('tizhi_tiaoli', {})
    health_rules = input_data.get('health_rules', {})
    
    # ⚠️ 方案2：优化数据结构，使用引用避免重复
    optimized_data = {
        # 1. 命盘体质总论（基础数据，只提取一次）
        'mingpan_tizhi_zonglun': mingpan,
        
        # 2. 五行病理推演（完整数据）
        'wuxing_bingli': wuxing_bingli,
        
        # 3. 大运流年健康警示（完整数据）
        'dayun_jiankang': dayun_jiankang,
        
        # 4. 体质调理建议（完整数据）
        'tizhi_tiaoli': tizhi_tiaoli,
        
        # 5. 健康规则（如果有）
        'health_rules': health_rules
    }
    
    # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
    return json.dumps(optimized_data, ensure_ascii=False, indent=2)


def format_health_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将健康分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 3500 字符
    - 优化后约 500 字符
    - Token 减少约 86%
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_tizhi_zonglun', {})
    wuxing_bingli = input_data.get('wuxing_bingli', {})
    dayun_jiankang = input_data.get('dayun_jiankang', {})
    tizhi_tiaoli = input_data.get('tizhi_tiaoli', {})
    health_rules = input_data.get('health_rules', {})
    
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
    
    # 3. 五行分布
    elements = mingpan.get('elements', {})
    if elements:
        wuxing_text = format_wuxing_distribution_text(elements)
        if wuxing_text:
            lines.append(f"【五行分布】{wuxing_text}")
    
    # 4. 五行平衡
    wuxing_balance = mingpan.get('wuxing_balance', '')
    if wuxing_balance:
        lines.append(f"【五行平衡】{wuxing_balance}")
    
    # 5. 脏腑对应
    body_algorithm = wuxing_bingli.get('body_algorithm', {})
    organ_analysis = body_algorithm.get('organ_analysis', {})
    if organ_analysis:
        organ_parts = []
        for element, organs in organ_analysis.items():
            if organs:
                organ_parts.append(f"{element}主{'/'.join(organs) if isinstance(organs, list) else organs}")
        if organ_parts:
            lines.append(f"【脏腑对应】{'; '.join(organ_parts)}")
    
    # 6. 病理倾向（完整保留）
    pathology = wuxing_bingli.get('pathology_tendency', {})
    pathology_list = pathology.get('pathology_list', [])
    if pathology_list:
        pathology_texts = []
        for p in pathology_list:
            if isinstance(p, dict):
                pathology_texts.append(p.get('description', str(p)))
            else:
                pathology_texts.append(str(p))
        if pathology_texts:
            lines.append(f"【病理倾向】{'; '.join(pathology_texts)}")
    
    # 7. 健康判词（完整保留）
    rule_judgments = health_rules.get('rule_judgments', [])
    if rule_judgments:
        judgments_text = format_judgments_text(
            [{'text': j} if isinstance(j, str) else j for j in rule_judgments]
        )
        if judgments_text:
            lines.append(f"【健康判词】{judgments_text}")
    
    # 8-9. 当前大运 + 关键大运与流年（统一使用公共模块）
    lines.extend(format_key_dayuns_text(
        key_dayuns=dayun_jiankang.get('key_dayuns', []),
        current_dayun=dayun_jiankang.get('current_dayun', {}),
        special_liunians=dayun_jiankang.get('special_liunians', [])
    ))
    
    # 10. 喜忌
    xi_ji = tizhi_tiaoli.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    # 11. 调理建议（完整保留）
    wuxing_tiaohe = tizhi_tiaoli.get('wuxing_tiaohe', {})
    tuning_suggestions = wuxing_tiaohe.get('tuning_suggestions', [])
    if tuning_suggestions:
        suggestions = [s if isinstance(s, str) else str(s) for s in tuning_suggestions]
        if suggestions:
            lines.append(f"【调理建议】{'; '.join(suggestions)}")
    
    return '\n'.join(lines)


# ==============================================================================
# 总评分析格式化函数
# ==============================================================================


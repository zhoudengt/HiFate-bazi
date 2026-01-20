# -*- coding: utf-8 -*-
"""
Prompt 构建工具模块

此模块包含用于构建大模型 prompt 的函数，这些函数从各个分析 API 文件中提取。
只依赖标准库，不依赖 FastAPI 或其他服务器端依赖，可以在评测脚本中安全导入。

使用场景：
- 流式接口构建 prompt 传递给大模型
- 评测脚本构建相同的 prompt 确保一致性
"""

import json
import copy
from typing import Dict, Any, Optional


# ==============================================================================
# 通用辅助函数
# ==============================================================================

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
# 健康分析 Prompt 构建函数
# ==============================================================================

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
    
    # 关键节点大运
    key_dayuns = section3.get('key_dayuns', [])
    if key_dayuns:
        # 获取完整的大运序列（用于格式化流年）
        all_dayuns = section3.get('all_dayuns', [])
        dayun_sequence_for_format = all_dayuns if all_dayuns else []
        
        for key_dayun in key_dayuns:
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


# ==============================================================================
# 事业财富分析格式化函数
# ==============================================================================

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


# ==============================================================================
# 子女学习分析格式化函数
# ==============================================================================

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


# ==============================================================================
# 健康分析格式化函数
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


# ==============================================================================
# 总评分析格式化函数
# ==============================================================================

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


# ==============================================================================
# 向后兼容别名（保持原有API文件的兼容性）
# ==============================================================================

# 为原有函数名提供别名（原文件中的函数名）
format_input_data_for_coze = format_marriage_input_data_for_coze  # 默认指向婚姻分析（最早使用此名称）

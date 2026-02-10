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


def format_dayun_text(current_dayun: Optional[Dict[str, Any]], key_dayuns: list = None) -> str:
    """
    格式化大运为简洁中文文本
    
    Args:
        current_dayun: 当前大运数据
        key_dayuns: 关键大运列表（可选）
        
    Returns:
        str: 格式化文本
    """
    lines = []
    
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        ganzhi = current_dayun.get('ganzhi', f"{stem}{branch}")
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        main_star = current_dayun.get('main_star', '')
        
        current_text = f"第{step}运{ganzhi}({age_display})"
        if main_star:
            current_text += f"，{main_star}"
        lines.append(f"【当前大运】{current_text}")
    
    if key_dayuns:
        key_parts = []
        for dayun in key_dayuns[:5]:  # 最多显示5个关键大运
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            ganzhi = dayun.get('ganzhi', f"{stem}{branch}")
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            main_star = dayun.get('main_star', '')
            
            text = f"第{step}运{ganzhi}({age_display})"
            if main_star:
                text += f"-{main_star}"
            key_parts.append(text)
        
        if key_parts:
            lines.append(f"【关键大运】{'；'.join(key_parts)}")
    
    return '\n'.join(lines)


def format_liunian_text(liunians: list, max_count: int = 10) -> str:
    """
    格式化流年为简洁中文文本（只显示特殊流年）
    
    Args:
        liunians: 流年列表
        max_count: 最大显示数量
        
    Returns:
        str: 格式化文本，如 "2026丙午(天克地冲)、2028戊申(天合地合)"
    """
    if not liunians:
        return ""
    
    parts = []
    count = 0
    
    for liunian in liunians:
        if count >= max_count:
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
            count += 1
    
    return '、'.join(parts) if parts else ""


def format_judgments_text(judgments: list, max_count: int = 5) -> str:
    """
    格式化判词为简洁中文文本
    
    Args:
        judgments: 判词列表 [{'name': '规则名', 'text': '判词内容'}, ...]
        max_count: 最大显示数量
        
    Returns:
        str: 格式化文本，如 "正财坐长生，配偶贤良；日支逢冲，婚姻波折"
    """
    if not judgments:
        return ""
    
    texts = []
    for judgment in judgments[:max_count]:
        text = judgment.get('text', '')
        if text:
            # 截取前50个字符
            if len(text) > 50:
                text = text[:50] + "..."
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
    
    # 6. 婚姻判词
    marriage_judgments = peiou.get('marriage_judgments', [])
    if marriage_judgments:
        judgments_text = format_judgments_text(marriage_judgments, max_count=3)
        if judgments_text:
            lines.append(f"【婚姻判词】{judgments_text}")
    
    # 7. 桃花判词
    peach_blossom_judgments = peiou.get('peach_blossom_judgments', [])
    if peach_blossom_judgments:
        judgments_text = format_judgments_text(peach_blossom_judgments, max_count=2)
        if judgments_text:
            lines.append(f"【桃花判词】{judgments_text}")
    
    # 8. 婚配判词
    matchmaking_judgments = peiou.get('matchmaking_judgments', [])
    if matchmaking_judgments:
        judgments_text = format_judgments_text(matchmaking_judgments, max_count=2)
        if judgments_text:
            lines.append(f"【婚配判词】{judgments_text}")
    
    # 9. 正缘判词
    zhengyuan_judgments = peiou.get('zhengyuan_judgments', [])
    if zhengyuan_judgments:
        judgments_text = format_judgments_text(zhengyuan_judgments, max_count=2)
        if judgments_text:
            lines.append(f"【正缘判词】{judgments_text}")
    
    # 10. 当前大运
    current_dayun = ganqing.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        ganzhi = f"{stem}{branch}"
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        main_star = current_dayun.get('main_star', '')
        
        dayun_text = f"第{step}运{ganzhi}({age_display})"
        if main_star:
            dayun_text += f"，{main_star}"
        lines.append(f"【当前大运】{dayun_text}")
        
        # 当前大运的特殊流年
        liunians = current_dayun.get('liunians', [])
        if liunians:
            liunian_text = format_liunian_text(liunians, max_count=5)
            if liunian_text:
                lines.append(f"【当前大运流年】{liunian_text}")
    
    # 11. 关键大运
    key_dayuns = ganqing.get('key_dayuns', [])
    if key_dayuns:
        key_parts = []
        for dayun in key_dayuns[:3]:
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            ganzhi = f"{stem}{branch}"
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            main_star = dayun.get('main_star', '')
            
            text = f"第{step}运{ganzhi}({age_display})"
            if main_star:
                text += f"-{main_star}"
            key_parts.append(text)
            
            # 关键大运的特殊流年
            liunians = dayun.get('liunians', [])
            if liunians:
                liunian_text = format_liunian_text(liunians, max_count=3)
                if liunian_text:
                    key_parts.append(f"  流年:{liunian_text}")
        
        if key_parts:
            lines.append(f"【关键大运】{'；'.join(key_parts)}")
    
    # 12. 喜忌
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    return '\n'.join(lines)


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
            geju_text += f"，{geju_desc[:30]}"
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
    
    # 10. 事业判词
    career_judgments = shiye.get('career_judgments', [])
    if career_judgments:
        judgments_text = format_judgments_text(career_judgments, max_count=3)
        if judgments_text:
            lines.append(f"【事业判词】{judgments_text}")
    
    # 11. 财富判词
    wealth_judgments = caifu.get('wealth_judgments', [])
    if wealth_judgments:
        judgments_text = format_judgments_text(wealth_judgments, max_count=3)
        if judgments_text:
            lines.append(f"【财富判词】{judgments_text}")
    
    # 12. 当前大运
    current_dayun = shiye_yunshi.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        ganzhi = f"{stem}{branch}"
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        main_star = current_dayun.get('main_star', '')
        
        dayun_text = f"第{step}运{ganzhi}({age_display})"
        if main_star:
            dayun_text += f"，{main_star}"
        lines.append(f"【当前大运】{dayun_text}")
        
        # 当前大运的特殊流年
        liunians = current_dayun.get('liunians', [])
        if liunians:
            liunian_text = format_liunian_text(liunians, max_count=5)
            if liunian_text:
                lines.append(f"【当前大运流年】{liunian_text}")
    
    # 13. 关键大运
    key_dayuns = shiye_yunshi.get('key_dayuns', [])
    if key_dayuns:
        key_parts = []
        for dayun in key_dayuns[:3]:
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            ganzhi = f"{stem}{branch}"
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            main_star = dayun.get('main_star', '')
            
            text = f"第{step}运{ganzhi}({age_display})"
            if main_star:
                text += f"-{main_star}"
            key_parts.append(text)
        
        if key_parts:
            lines.append(f"【关键大运】{'；'.join(key_parts)}")
    
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
    
    # 7. 子女判词
    rule_judgments = children_rules.get('rule_judgments', [])
    if rule_judgments:
        judgments_text = format_judgments_text(
            [{'text': j} if isinstance(j, str) else j for j in rule_judgments],
            max_count=3
        )
        if judgments_text:
            lines.append(f"【子女判词】{judgments_text}")
    
    # 8. 当前大运
    current_dayun = shengyu.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        ganzhi = f"{stem}{branch}"
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        main_star = current_dayun.get('main_star', '')
        
        dayun_text = f"第{step}运{ganzhi}({age_display})"
        if main_star:
            dayun_text += f"，{main_star}"
        lines.append(f"【当前大运】{dayun_text}")
        
        # 特殊流年
        liunians = current_dayun.get('liunians', [])
        if liunians:
            liunian_text = format_liunian_text(liunians, max_count=5)
            if liunian_text:
                lines.append(f"【生育关注流年】{liunian_text}")
    
    # 9. 关键大运
    key_dayuns = shengyu.get('key_dayuns', [])
    if key_dayuns:
        key_parts = []
        for dayun in key_dayuns[:3]:
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            ganzhi = f"{stem}{branch}"
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            main_star = dayun.get('main_star', '')
            
            text = f"第{step}运{ganzhi}({age_display})"
            if main_star:
                text += f"-{main_star}"
            key_parts.append(text)
        
        if key_parts:
            lines.append(f"【关键大运】{'；'.join(key_parts)}")
    
    # 10. 喜忌
    xi_ji = yangyu.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    return '\n'.join(lines)


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
            lines.append(f"【脏腑对应】{'; '.join(organ_parts[:5])}")
    
    # 6. 病理倾向
    pathology = wuxing_bingli.get('pathology_tendency', {})
    pathology_list = pathology.get('pathology_list', [])
    if pathology_list:
        pathology_texts = []
        for p in pathology_list[:5]:
            if isinstance(p, dict):
                pathology_texts.append(p.get('description', str(p))[:30])
            else:
                pathology_texts.append(str(p)[:30])
        if pathology_texts:
            lines.append(f"【病理倾向】{'; '.join(pathology_texts)}")
    
    # 7. 健康判词
    rule_judgments = health_rules.get('rule_judgments', [])
    if rule_judgments:
        judgments_text = format_judgments_text(
            [{'text': j} if isinstance(j, str) else j for j in rule_judgments],
            max_count=3
        )
        if judgments_text:
            lines.append(f"【健康判词】{judgments_text}")
    
    # 8. 当前大运
    current_dayun = dayun_jiankang.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        ganzhi = f"{stem}{branch}"
        age_display = current_dayun.get('age_display', '')
        
        lines.append(f"【当前大运】{ganzhi}({age_display})")
        
        # 特殊流年
        liunians = current_dayun.get('liunians', {})
        special_years = []
        for ltype, lyears in liunians.items():
            if lyears and ltype != 'other':
                for ly in lyears[:2]:
                    year = ly.get('year', '')
                    ganzhi = ly.get('ganzhi', '')
                    special_years.append(f"{year}{ganzhi}({ltype})")
        if special_years:
            lines.append(f"【健康警示流年】{'; '.join(special_years[:5])}")
    
    # 9. 关键大运
    key_dayuns = dayun_jiankang.get('key_dayuns', [])
    if key_dayuns:
        key_parts = []
        for dayun in key_dayuns[:3]:
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            ganzhi = f"{stem}{branch}"
            age_display = dayun.get('age_display', '')
            relation_type = dayun.get('relation_type', '')
            
            text = f"{ganzhi}({age_display})"
            if relation_type:
                text += f"-{relation_type}"
            key_parts.append(text)
        
        if key_parts:
            lines.append(f"【关键大运】{'；'.join(key_parts)}")
    
    # 10. 喜忌
    xi_ji = tizhi_tiaoli.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    # 11. 调理建议
    wuxing_tiaohe = tizhi_tiaoli.get('wuxing_tiaohe', {})
    tuning_suggestions = wuxing_tiaohe.get('tuning_suggestions', [])
    if tuning_suggestions:
        suggestions = [s[:30] if isinstance(s, str) else str(s)[:30] for s in tuning_suggestions[:3]]
        if suggestions:
            lines.append(f"【调理建议】{'; '.join(suggestions)}")
    
    return '\n'.join(lines)


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
    
    # 5. 性格特质
    day_master_personality = xingge.get('day_master_personality', [])
    if day_master_personality:
        # 只取前3条性格描述
        personality_texts = []
        for p in day_master_personality[:3]:
            if isinstance(p, str):
                personality_texts.append(p[:30])
            elif isinstance(p, dict):
                personality_texts.append(p.get('description', str(p))[:30])
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
    
    # 9. 健康要点
    wuxing_balance = jiankang.get('wuxing_balance', {})
    jiankang_ruodian = jiankang.get('jiankang_ruodian', {})
    if wuxing_balance or jiankang_ruodian:
        health_text = ""
        if isinstance(wuxing_balance, str):
            health_text = wuxing_balance[:30]
        elif isinstance(jiankang_ruodian, str):
            health_text = jiankang_ruodian[:30]
        elif isinstance(jiankang_ruodian, dict):
            health_text = str(list(jiankang_ruodian.values())[:2])[:30]
        if health_text:
            lines.append(f"【健康要点】{health_text}")
    
    # 10. 当前大运
    current_dayun = guanjian.get('current_dayun', {})
    if current_dayun:
        ganzhi = current_dayun.get('ganzhi', '')
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        
        lines.append(f"【当前大运】第{step}运{ganzhi}({age_display})")
        
        # 特殊流年
        # ⚠️ 修复：兼容两种字段名（build_input_data 设 'liunians'，_simplify_dayun 设 'key_liunians'）
        key_liunians = current_dayun.get('liunians', current_dayun.get('key_liunians', []))
        if key_liunians:
            liunian_text = format_liunian_text(key_liunians, max_count=5)
            if liunian_text:
                lines.append(f"【关键流年】{liunian_text}")
    
    # 11. 关键大运
    key_dayuns = guanjian.get('key_dayuns', [])
    if key_dayuns:
        key_parts = []
        for dayun in key_dayuns[:5]:
            ganzhi = dayun.get('ganzhi', '')
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            
            text = f"第{step}运{ganzhi}({age_display})"
            key_parts.append(text)
        
        if key_parts:
            lines.append(f"【关键大运】{'；'.join(key_parts)}")
    
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
    
    # 15. 日柱解析
    rizhu = rizhu_xinming.get('rizhu', '')
    gender_display = rizhu_xinming.get('gender_display', '')
    if rizhu:
        descriptions = rizhu_xinming.get('descriptions', [])
        desc_text = ''
        if descriptions:
            desc_text = '；'.join([str(d)[:20] for d in descriptions[:2]])
        lines.append(f"【日柱解析】{rizhu}{gender_display}命，{desc_text}")
    
    return '\n'.join(lines)


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
    
    # 7. 大运流年
    if fortune_context:
        current_dayun = fortune_context.get('current_dayun', {})
        if current_dayun:
            ganzhi = current_dayun.get('ganzhi', '')
            age_display = current_dayun.get('age_display', '')
            if ganzhi:
                lines.append(f"【当前大运】{ganzhi}({age_display})")
        
        # 关键流年
        key_liunians = fortune_context.get('key_liunians', [])
        if key_liunians:
            liunian_text = format_liunian_text(key_liunians, max_count=5)
            if liunian_text:
                lines.append(f"【关键流年】{liunian_text}")
    
    # 8. 匹配规则
    if matched_rules:
        rule_texts = []
        for rule in matched_rules[:5]:
            rule_name = rule.get('rule_name', rule.get('name', ''))
            if rule_name:
                rule_texts.append(rule_name)
        if rule_texts:
            lines.append(f"【匹配规则】{'、'.join(rule_texts)}")
    
    # 9. 用户问题
    lines.append(f"【用户问题】{question}")
    
    # 10. 问题类型
    if category:
        lines.append(f"【问题类型】{category}")
    elif intent:
        lines.append(f"【意图】{intent}")
    
    # 11. 历史上下文
    if history_context:
        history_parts = []
        for h in history_context[-3:]:  # 只取最近3轮
            round_num = h.get('round', '')
            keywords = h.get('keywords', [])
            if keywords:
                history_parts.append(f"第{round_num}轮:{'/'.join(keywords[:3])}")
        if history_parts:
            lines.append(f"【历史上下文】{'，'.join(history_parts)}")
    
    # 12. 语言风格要求
    lines.append("【语言风格】通俗易懂，避免专业术语，用日常语言解释命理概念")
    
    return '\n'.join(lines)


def format_annual_report_for_llm(input_data: Dict[str, Any]) -> str:
    """
    将年运报告分析数据格式化为精简中文文本（用于 LLM Prompt 优化）
    
    优化效果：
    - 原 JSON 格式约 4500 字符
    - 优化后约 800 字符
    - Token 减少约 82%
    
    Args:
        input_data: 结构化输入数据
        
    Returns:
        str: 精简的中文文本格式
    """
    lines = []
    
    # 获取各部分数据
    mingpan = input_data.get('mingpan_analysis', {})
    monthly = input_data.get('monthly_analysis', {})
    taisui = input_data.get('taisui_info', {})
    fengshui = input_data.get('fengshui_info', {})
    dayun_liunian = input_data.get('dayun_liunian', {})
    
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
    
    # 4. 喜忌
    xi_ji = mingpan.get('xi_ji', {})
    xi_ji_text = format_xi_ji_text(xi_ji)
    if xi_ji_text:
        lines.append(f"【喜忌】{xi_ji_text}")
    
    # 5. 流年信息
    year = monthly.get('year', taisui.get('year', ''))
    if year:
        lines.append(f"【流年】{year}年")
    
    # 6. 太岁信息
    taisui_name = taisui.get('taisui_name', '')
    taisui_desc = taisui.get('taisui_description', '')
    if taisui_name:
        taisui_text = taisui_name
        if taisui_desc:
            taisui_text += f"，{taisui_desc[:30]}"
        lines.append(f"【太岁】{taisui_text}")
    
    # 7. 犯太岁
    fanshaisui = taisui.get('fanshaisui', {})
    if fanshaisui:
        fan_parts = [f"{k}{v}" for k, v in fanshaisui.items() if v]
        if fan_parts:
            lines.append(f"【犯太岁】{'、'.join(fan_parts)}")
    
    # 8. 流月运势（精简显示）
    months = monthly.get('months', [])
    if months:
        month_parts = []
        for m in months[:6]:  # 只显示上半年
            month_num = m.get('month', '')
            jieqi = m.get('jieqi', '')
            yingxiang = m.get('yingxiang', '')[:15] if m.get('yingxiang') else ''
            
            month_text = f"{month_num}月({jieqi})"
            if yingxiang:
                month_text += f":{yingxiang}"
            month_parts.append(month_text)
        
        if month_parts:
            lines.append(f"【上半年流月】{'；'.join(month_parts)}")
        
        # 下半年
        month_parts = []
        for m in months[6:]:  # 下半年
            month_num = m.get('month', '')
            jieqi = m.get('jieqi', '')
            yingxiang = m.get('yingxiang', '')[:15] if m.get('yingxiang') else ''
            
            month_text = f"{month_num}月({jieqi})"
            if yingxiang:
                month_text += f":{yingxiang}"
            month_parts.append(month_text)
        
        if month_parts:
            lines.append(f"【下半年流月】{'；'.join(month_parts)}")
    
    # 9. 九宫飞星
    jiugong = fengshui.get('jiugong_feixing', {})
    wuhuang = fengshui.get('wuhuang', {})
    erhei = fengshui.get('erhei', {})
    
    fengshui_parts = []
    if wuhuang:
        position = wuhuang.get('position', '')
        if position:
            fengshui_parts.append(f"五黄在{position}")
    if erhei:
        position = erhei.get('position', '')
        if position:
            fengshui_parts.append(f"二黑在{position}")
    
    if fengshui_parts:
        lines.append(f"【九宫飞星】{'，'.join(fengshui_parts)}")
    
    # 10. 避煞建议
    bixing_times = fengshui.get('bixing_times', {})
    if bixing_times:
        lines.append(f"【避煞建议】避动土方位，宜佩戴金属饰品")
    
    # 11. 化解方法
    resolution = taisui.get('resolution', {})
    if resolution:
        methods = []
        if isinstance(resolution, dict):
            methods = list(resolution.values())[:3]
        elif isinstance(resolution, list):
            methods = resolution[:3]
        if methods:
            lines.append(f"【化解方法】{'、'.join([str(m)[:15] for m in methods])}")
    
    # 12. 大运流年数据
    dayuns = dayun_liunian.get('dayuns', [])
    if dayuns:
        # 找到当前大运
        current_dayun = None
        for dayun in dayuns:
            liunians = dayun.get('liunians', [])
            for ln in liunians:
                if ln.get('year') == year:
                    current_dayun = dayun
                    break
            if current_dayun:
                break
        
        if current_dayun:
            ganzhi = current_dayun.get('ganzhi', '')
            age_display = current_dayun.get('age_display', '')
            lines.append(f"【当前大运】{ganzhi}({age_display})")
            
            # 特殊流年
            liunians = current_dayun.get('liunians', [])
            if liunians:
                liunian_text = format_liunian_text(liunians, max_count=5)
                if liunian_text:
                    lines.append(f"【特殊流年】{liunian_text}")
    
    return '\n'.join(lines)


# ==============================================================================
# 面相分析V2格式化函数
# ==============================================================================

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


# ==============================================================================
# 办公桌风水分析格式化函数
# ==============================================================================

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


# ==============================================================================
# 向后兼容别名（保持原有API文件的兼容性）
# ==============================================================================

# 为原有函数名提供别名（原文件中的函数名）
format_input_data_for_coze = format_marriage_input_data_for_coze  # 默认指向婚姻分析（最早使用此名称）

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-事业财富API
基于用户生辰数据，使用 Coze Bot 流式生成事业财富分析
"""

import logging
import os
import sys
from typing import Dict, Any, Optional, List
from fastapi import APIRouter
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_detail_service import BaziDetailService
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.industry_service import IndustryService
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import classify_special_liunians, organize_special_liunians_by_dayun
from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS

logger = logging.getLogger(__name__)

router = APIRouter()

# 天干五行对照
STEM_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

# 天干阴阳对照
STEM_YIN_YANG = {
    "甲": "阳", "乙": "阴",
    "丙": "阳", "丁": "阴",
    "戊": "阳", "己": "阴",
    "庚": "阳", "辛": "阴",
    "壬": "阳", "癸": "阴"
}

# 地支对应月令
BRANCH_MONTH = {
    "寅": "寅月", "卯": "卯月", "辰": "辰月",
    "巳": "巳月", "午": "午月", "未": "未月",
    "申": "申月", "酉": "酉月", "戌": "戌月",
    "亥": "亥月", "子": "子月", "丑": "丑月"
}

# 五行对应方位
ELEMENT_DIRECTION = {
    "木": "东",
    "火": "南",
    "土": "中",
    "金": "西",
    "水": "北"
}

# 五行行业对照已改为从数据库读取（使用 IndustryService）


def build_natural_language_prompt(data: dict) -> str:
    """
    将 JSON 数据转换为自然语言格式的提示词
    
    Args:
        data: 事业财富分析所需的完整数据
        
    Returns:
        str: 自然语言格式的提示词
    """
    prompt_lines = []
    prompt_lines.append("请基于以下八字信息进行事业财富分析：")
    prompt_lines.append("")
    
    # 1. 命盘事业财富总论
    prompt_lines.append("【命盘事业财富总论】")
    mingpan = data.get('mingpan_shiye_caifu_zonglun', {})
    
    # 日主信息
    day_master = mingpan.get('day_master', {})
    if day_master:
        stem = day_master.get('stem', '')
        branch = day_master.get('branch', '')
        element = day_master.get('element', '')
        yin_yang = day_master.get('yin_yang', '')
        prompt_lines.append(f"日主：{stem}{branch}（{yin_yang}{element}）")
    
    # 四柱排盘
    bazi_pillars = mingpan.get('bazi_pillars', {})
    if bazi_pillars:
        prompt_lines.append("四柱排盘：")
        for pillar_name, pillar_key in [('年柱', 'year'), ('月柱', 'month'), ('日柱', 'day'), ('时柱', 'hour')]:
            pillar = bazi_pillars.get(pillar_key, {})
            stem = pillar.get('stem', '')
            branch = pillar.get('branch', '')
            if stem and branch:
                prompt_lines.append(f"  {pillar_name}：{stem}{branch}")
    
    # 五行分布
    wuxing = mingpan.get('wuxing_distribution', {})
    if wuxing:
        wuxing_str = '、'.join([f"{k}{v}个" for k, v in wuxing.items() if v > 0])
        prompt_lines.append(f"五行分布：{wuxing_str}")
    
    # 旺衰
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        prompt_lines.append(f"身旺身弱：{wangshuai}")
    
    # 月令
    yue_ling = mingpan.get('yue_ling', '')
    if yue_ling:
        prompt_lines.append(f"月令：{yue_ling}")
    
    # 性别
    gender = mingpan.get('gender', '')
    gender_cn = '男' if gender == 'male' else '女' if gender == 'female' else ''
    if gender_cn:
        prompt_lines.append(f"性别：{gender_cn}")
    
    # 格局类型
    geju = mingpan.get('geju_type', '')
    if geju:
        prompt_lines.append(f"格局类型：{geju}")
    
    # 十神配置
    ten_gods = mingpan.get('ten_gods', {})
    if ten_gods:
        prompt_lines.append("十神配置：")
        for pillar_name, pillar_key in [('年柱', 'year'), ('月柱', 'month'), ('日柱', 'day'), ('时柱', 'hour')]:
            pillar_ten_gods = ten_gods.get(pillar_key, {})
            if pillar_ten_gods:
                main_star = pillar_ten_gods.get('main_star', '')
                hidden_stars = pillar_ten_gods.get('hidden_stars', [])
                hidden_str = '、'.join(hidden_stars) if hidden_stars else '无'
                prompt_lines.append(f"  {pillar_name}：主星{main_star}，副星{hidden_str}")
    
    prompt_lines.append("")
    
    # 2. 事业星与事业宫
    prompt_lines.append("【事业星与事业宫】")
    shiye = data.get('shiye_xing_gong', {})
    
    # 事业星
    shiye_xing = shiye.get('shiye_xing', {})
    if shiye_xing:
        primary = shiye_xing.get('primary', '')
        secondary = shiye_xing.get('secondary', '')
        positions = shiye_xing.get('positions', [])
        if primary:
            prompt_lines.append(f"主要事业星：{primary}")
        if secondary:
            prompt_lines.append(f"次要事业星：{secondary}")
        if positions:
            prompt_lines.append(f"事业星位置：{'、'.join(positions)}")
    
    # 月柱分析
    month_analysis = shiye.get('month_pillar_analysis', {})
    if month_analysis:
        stem = month_analysis.get('stem', '')
        branch = month_analysis.get('branch', '')
        stem_shishen = month_analysis.get('stem_shishen', '')
        if stem and branch:
            prompt_lines.append(f"月柱（事业宫）：{stem}{branch}，月干十神：{stem_shishen}")
    
    # 神煞分布
    deities = shiye.get('deities', {})
    if deities:
        prompt_lines.append("神煞分布：")
        for pillar_key, pillar_deities in deities.items():
            pillar_names_map = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
            pillar_name = pillar_names_map.get(pillar_key, pillar_key)
            if pillar_deities:
                deities_str = '、'.join(pillar_deities) if isinstance(pillar_deities, list) else str(pillar_deities)
                prompt_lines.append(f"  {pillar_name}：{deities_str}")
    
    # 事业判词
    career_judgments = shiye.get('career_judgments', [])
    if career_judgments:
        prompt_lines.append("事业判词：")
        for j in career_judgments[:5]:  # 最多显示5条
            name = j.get('name', '')
            text = j.get('text', '')
            if text:
                prompt_lines.append(f"  - {name}：{text}")
    
    prompt_lines.append("")
    
    # 3. 财富星与财富宫
    prompt_lines.append("【财富星与财富宫】")
    caifu = data.get('caifu_xing_gong', {})
    
    # 财富星
    caifu_xing = caifu.get('caifu_xing', {})
    if caifu_xing:
        primary = caifu_xing.get('primary', '')
        positions = caifu_xing.get('positions', [])
        if primary:
            prompt_lines.append(f"主要财星：{primary}")
        if positions:
            prompt_lines.append(f"财星位置：{'、'.join(positions)}")
    
    # 食伤生财
    shishang = caifu.get('shishang_shengcai', {})
    if shishang.get('has_combination'):
        prompt_lines.append(f"食伤生财：{shishang.get('combination_type', '')}")
    
    # 财库
    caiku = caifu.get('caiku', {})
    if caiku.get('has_caiku'):
        prompt_lines.append(f"财库：{caiku.get('caiku_position', '')}，状态：{caiku.get('caiku_status', '')}")
    
    # 财富判词
    wealth_judgments = caifu.get('wealth_judgments', [])
    if wealth_judgments:
        prompt_lines.append("财富判词：")
        for j in wealth_judgments[:5]:
            name = j.get('name', '')
            text = j.get('text', '')
            if text:
                prompt_lines.append(f"  - {name}：{text}")
    
    prompt_lines.append("")
    
    # 4. 事业运势
    prompt_lines.append("【事业运势】")
    yunshi = data.get('shiye_yunshi', {})
    
    # 当前年龄
    age = yunshi.get('current_age', 0)
    if age:
        prompt_lines.append(f"当前年龄：{age}岁")
    
    # 现行运（按照新格式）
    current_dayun = yunshi.get('current_dayun', {})
    if current_dayun:
        step = current_dayun.get('step', '')
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        main_star = current_dayun.get('main_star', '')
        age_display = current_dayun.get('age_display', '')
        if stem and branch:
            prompt_lines.append(f"**现行{step}运（{age_display}）：**")
            prompt_lines.append(f"- 大运：{stem}{branch}，主星：{main_star}")
            prompt_lines.append(f"- [分析当前大运的五行特征对事业的影响]")
            key_liunians = current_dayun.get('liunians', [])
            if key_liunians:
                prompt_lines.append(f"- [列举关键流年及事业风险]：")
                for liunian in key_liunians:
                    year = liunian.get('year', '')
                    liunian_type = liunian.get('type', '')
                    prompt_lines.append(f"  - {year}年（{liunian_type}）：[分析该年的事业风险，如XX年XX势过猛，需格外防范XX]")
            else:
                prompt_lines.append(f"- [列举关键流年及事业风险]：暂无特殊流年")
            prompt_lines.append("")
    
    # 关键节点大运（按照新格式）
    key_dayuns = yunshi.get('key_dayuns', [])
    if key_dayuns:
        for key_dayun in key_dayuns:
            step = key_dayun.get('step', '')
            stem = key_dayun.get('stem', '')
            branch = key_dayun.get('branch', '')
            main_star = key_dayun.get('main_star', '')
            age_display = key_dayun.get('age_display', '')
            relation_type = key_dayun.get('relation_type', '')
            if stem and branch:
                prompt_lines.append(f"**关键节点：{step}运（{age_display}）：**")
                prompt_lines.append(f"- 大运：{stem}{branch}，主星：{main_star}")
                prompt_lines.append(f"- [分析该大运的五行特征，是否为调候用神出现]")
                if relation_type:
                    prompt_lines.append(f"- [分析该运与原局的生克关系，如{relation_type}等]")
                prompt_lines.append(f"- 利好：[分析该运对事业的积极影响]")
                key_liunians = key_dayun.get('liunians', [])
                if key_liunians:
                    prompt_lines.append(f"- 挑战：[分析该运的事业风险，如XX年（岁运并临），XX势过猛冲击XX，需重点防范XX]：")
                    for liunian in key_liunians:
                        year = liunian.get('year', '')
                        liunian_type = liunian.get('type', '')
                        prompt_lines.append(f"  - {year}年（{liunian_type}）：[分析该年的事业风险]")
                else:
                    prompt_lines.append(f"- 挑战：[分析该运的事业风险]：暂无特殊流年")
                prompt_lines.append("")
    
    prompt_lines.append("")
    
    # 5. 财富运势
    prompt_lines.append("【财富运势】")
    caifu_yunshi = data.get('caifu_yunshi', {})
    
    # 财富积累阶段
    stages = caifu_yunshi.get('wealth_stages', {})
    if stages:
        early = stages.get('early', {})
        middle = stages.get('middle', {})
        late = stages.get('late', {})
        if early.get('stage_type'):
            prompt_lines.append(f"早年（{early.get('age_range', '1-30岁')}）：{early.get('stage_type', '')}")
        if middle.get('stage_type'):
            prompt_lines.append(f"中年（{middle.get('age_range', '30-50岁')}）：{middle.get('stage_type', '')}")
        if late.get('stage_type'):
            prompt_lines.append(f"晚年（{late.get('age_range', '50岁以后')}）：{late.get('stage_type', '')}")
    
    # 现行运（按照新格式）
    current_dayun = caifu_yunshi.get('current_dayun', {})
    if current_dayun:
        step = current_dayun.get('step', '')
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        main_star = current_dayun.get('main_star', '')
        age_display = current_dayun.get('age_display', '')
        if stem and branch:
            prompt_lines.append(f"**现行{step}运（{age_display}）：**")
            prompt_lines.append(f"- 大运：{stem}{branch}，主星：{main_star}")
            prompt_lines.append(f"- [分析当前大运的五行特征对财富的影响]")
            key_liunians = current_dayun.get('liunians', [])
            if key_liunians:
                prompt_lines.append(f"- [列举关键流年及财富风险]：")
                for liunian in key_liunians:
                    year = liunian.get('year', '')
                    liunian_type = liunian.get('type', '')
                    prompt_lines.append(f"  - {year}年（{liunian_type}）：[分析该年的财富风险，如XX年XX势过猛，需格外防范XX]")
            else:
                prompt_lines.append(f"- [列举关键流年及财富风险]：暂无特殊流年")
            prompt_lines.append("")
    
    # 关键节点大运（按照新格式）
    key_dayuns = caifu_yunshi.get('key_dayuns', [])
    if key_dayuns:
        for key_dayun in key_dayuns:
            step = key_dayun.get('step', '')
            stem = key_dayun.get('stem', '')
            branch = key_dayun.get('branch', '')
            main_star = key_dayun.get('main_star', '')
            age_display = key_dayun.get('age_display', '')
            relation_type = key_dayun.get('relation_type', '')
            if stem and branch:
                prompt_lines.append(f"**关键节点：{step}运（{age_display}）：**")
                prompt_lines.append(f"- 大运：{stem}{branch}，主星：{main_star}")
                prompt_lines.append(f"- [分析该大运的五行特征，是否为调候用神出现]")
                if relation_type:
                    prompt_lines.append(f"- [分析该运与原局的生克关系，如{relation_type}等]")
                prompt_lines.append(f"- 利好：[分析该运对财富的积极影响]")
                key_liunians = key_dayun.get('liunians', [])
                if key_liunians:
                    prompt_lines.append(f"- 挑战：[分析该运的财富风险，如XX年（岁运并临），XX势过猛冲击XX，需重点防范XX]：")
                    for liunian in key_liunians:
                        year = liunian.get('year', '')
                        liunian_type = liunian.get('type', '')
                        prompt_lines.append(f"  - {year}年（{liunian_type}）：[分析该年的财富风险]")
                else:
                    prompt_lines.append(f"- 挑战：[分析该运的财富风险]：暂无特殊流年")
                prompt_lines.append("")
    
    prompt_lines.append("")
    
    # 6. 提运建议
    prompt_lines.append("【提运建议】")
    jianyi = data.get('tiyun_jianyi', {})
    
    # 喜忌
    xi_ji = jianyi.get('xi_ji', {})
    if xi_ji:
        xi_shen = xi_ji.get('xi_shen', [])
        ji_shen = xi_ji.get('ji_shen', [])
        xi_shen_elements = xi_ji.get('xi_shen_elements', [])
        ji_shen_elements = xi_ji.get('ji_shen_elements', [])
        
        if xi_shen:
            prompt_lines.append(f"喜神：{'、'.join(xi_shen)}")
        if ji_shen:
            prompt_lines.append(f"忌神：{'、'.join(ji_shen)}")
        if xi_shen_elements:
            prompt_lines.append(f"喜用五行：{'、'.join(xi_shen_elements)}")
        if ji_shen_elements:
            prompt_lines.append(f"忌用五行：{'、'.join(ji_shen_elements)}")
    
    # 方位选择
    fangwei = jianyi.get('fangwei', {})
    if fangwei:
        best = fangwei.get('best_directions', [])
        avoid = fangwei.get('avoid_directions', [])
        if best:
            prompt_lines.append(f"最佳方位：{'、'.join(best)}")
        if avoid:
            prompt_lines.append(f"避开方位：{'、'.join(avoid)}")
    
    # 行业选择
    hangye = jianyi.get('hangye', {})
    if hangye:
        best = hangye.get('best_industries', [])
        avoid = hangye.get('avoid_industries', [])
        if best:
            prompt_lines.append(f"适合行业：{'、'.join(best[:5])}")
        if avoid:
            prompt_lines.append(f"谨慎行业：{'、'.join(avoid[:3])}")
    
    prompt_lines.append("")
    
    return '\n'.join(prompt_lines)


def _calculate_ganzhi_elements(stem: str, branch: str) -> Dict[str, int]:
    """
    计算干支的五行分布
    
    Args:
        stem: 天干
        branch: 地支
        
    Returns:
        dict: 五行统计，如 {'木': 1, '火': 1, '土': 0, '金': 0, '水': 0}
    """
    elements = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    
    # 天干五行
    if stem and stem in STEM_ELEMENTS:
        element = STEM_ELEMENTS[stem]
        elements[element] = elements.get(element, 0) + 1
    
    # 地支五行
    if branch and branch in BRANCH_ELEMENTS:
        element = BRANCH_ELEMENTS[branch]
        elements[element] = elements.get(element, 0) + 1
    
    return elements


def analyze_dayun_bazi_relation(
    dayun: Dict[str, Any],
    bazi_elements: Dict[str, int]
) -> Optional[str]:
    """
    分析大运与原局的生克关系
    
    Args:
        dayun: 大运信息（包含 stem, branch）
        bazi_elements: 原局五行统计
        
    Returns:
        关系类型字符串，如"水土混战"、"水火交战"等，如果没有特殊关系返回None
    """
    # 1. 计算大运的五行
    dayun_stem = dayun.get('stem', '')
    dayun_branch = dayun.get('branch', '')
    dayun_elements = _calculate_ganzhi_elements(dayun_stem, dayun_branch)
    
    # 2. 判断是否存在"混战"或"交战"关系
    # 水土混战：大运土多 + 原局水多，或大运水多 + 原局土多
    if (dayun_elements.get('土', 0) >= 2 and bazi_elements.get('水', 0) >= 2) or \
       (dayun_elements.get('水', 0) >= 2 and bazi_elements.get('土', 0) >= 2):
        return '水土混战'
    
    # 水火交战：大运火多 + 原局水多，或大运水多 + 原局火多
    if (dayun_elements.get('火', 0) >= 2 and bazi_elements.get('水', 0) >= 2) or \
       (dayun_elements.get('水', 0) >= 2 and bazi_elements.get('火', 0) >= 2):
        return '水火交战'
    
    # 金木相战：大运金多 + 原局木多，或大运木多 + 原局金多
    if (dayun_elements.get('金', 0) >= 2 and bazi_elements.get('木', 0) >= 2) or \
       (dayun_elements.get('木', 0) >= 2 and bazi_elements.get('金', 0) >= 2):
        return '金木相战'
    
    # 木土相战：大运木多 + 原局土多，或大运土多 + 原局木多
    if (dayun_elements.get('木', 0) >= 2 and bazi_elements.get('土', 0) >= 2) or \
       (dayun_elements.get('土', 0) >= 2 and bazi_elements.get('木', 0) >= 2):
        return '木土相战'
    
    # 火金相战：大运火多 + 原局金多，或大运金多 + 原局火多
    if (dayun_elements.get('火', 0) >= 2 and bazi_elements.get('金', 0) >= 2) or \
       (dayun_elements.get('金', 0) >= 2 and bazi_elements.get('火', 0) >= 2):
        return '火金相战'
    
    return None


def identify_key_dayuns(
    dayun_sequence: List[Dict[str, Any]],
    bazi_elements: Dict[str, int],
    current_age: int
) -> Dict[str, Any]:
    """
    识别现行运和关键节点大运
    
    Args:
        dayun_sequence: 大运序列
        bazi_elements: 原局五行统计
        current_age: 当前年龄
        
    Returns:
        {
            'current_dayun': {...},  # 现行运
            'key_dayuns': [...]       # 关键节点大运列表
        }
    """
    current_dayun = None
    key_dayuns = []
    
    # 1. 识别现行运（跳过"小运"）
    for dayun in dayun_sequence:
        step = dayun.get('step', '')
        if step == '小运':
            continue
        age_display = dayun.get('age_display', '')
        if age_display:
            try:
                parts = age_display.replace('岁', '').split('-')
                if len(parts) == 2:
                    start_age = int(parts[0])
                    end_age = int(parts[1])
                    if start_age <= current_age <= end_age:
                        current_dayun = dayun
                        break
            except:
                pass
    
    # 如果没找到，使用第一个非"小运"的大运
    if not current_dayun and dayun_sequence:
        for dayun in dayun_sequence:
            step = dayun.get('step', '')
            if step != '小运':
                current_dayun = dayun
                break
    
    # 2. 识别关键节点大运（与原局有特殊生克关系，跳过"小运"）
    for dayun in dayun_sequence:
        step = dayun.get('step', '')
        if step == '小运':
            continue
        relation_type = analyze_dayun_bazi_relation(dayun, bazi_elements)
        if relation_type:
            key_dayuns.append({
                **dayun,
                'relation_type': relation_type
            })
    
    return {
        'current_dayun': current_dayun,
        'key_dayuns': key_dayuns
    }


def validate_input_data(data: dict) -> tuple:
    """
    验证输入数据完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        (is_valid, error_message): 是否有效，错误信息（如果无效）
    """
    required_fields = {
        'mingpan_shiye_caifu_zonglun': {
            'bazi_pillars': '八字排盘',
            'day_master': '日主信息',
        },
        'shiye_xing_gong': {
            'ten_gods': '十神配置',
        },
        'tiyun_jianyi': {
            'xi_ji': '喜忌分析',
        },
    }
    
    missing_fields = []
    
    for section, fields in required_fields.items():
        if section not in data:
            missing_fields.append(f"{section}（整个部分缺失）")
            continue
            
        section_data = data[section]
        if not isinstance(section_data, dict):
            missing_fields.append(f"{section}（格式错误，应为字典）")
            continue
            
        for field, field_name in fields.items():
            if field not in section_data:
                missing_fields.append(f"{section}.{field}（{field_name}）")
            elif section_data[field] is None:
                missing_fields.append(f"{section}.{field}（{field_name}为None）")
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""


def extract_career_star(ten_gods_stats: dict) -> dict:
    """
    提取事业星信息
    事业星：正官、七杀（官杀代表事业）；正印、偏印（代表贵人、学识）
    """
    result = {
        'primary': '',
        'secondary': '',
        'positions': [],
        'strength': '',
        'description': ''
    }
    
    # 统计官杀印星数量
    zhengguan = ten_gods_stats.get('正官', 0)
    qisha = ten_gods_stats.get('七杀', 0)
    zhengyin = ten_gods_stats.get('正印', 0)
    pianyin = ten_gods_stats.get('偏印', 0)
    
    # 确定主要事业星
    if zhengguan > 0 or qisha > 0:
        if zhengguan >= qisha:
            result['primary'] = '正官'
            if qisha > 0:
                result['secondary'] = '七杀'
        else:
            result['primary'] = '七杀'
            if zhengguan > 0:
                result['secondary'] = '正官'
    elif zhengyin > 0 or pianyin > 0:
        if zhengyin >= pianyin:
            result['primary'] = '正印'
        else:
            result['primary'] = '偏印'
    
    return result


def extract_wealth_star(ten_gods_stats: dict) -> dict:
    """
    提取财富星信息
    财富星：正财、偏财
    """
    result = {
        'primary': '',
        'positions': [],
        'strength': '',
        'description': ''
    }
    
    zhengcai = ten_gods_stats.get('正财', 0)
    piancai = ten_gods_stats.get('偏财', 0)
    
    if zhengcai > 0 or piancai > 0:
        if zhengcai >= piancai:
            result['primary'] = '正财'
        else:
            result['primary'] = '偏财'
    
    return result


def check_shishang_shengcai(ten_gods_stats: dict, ten_gods_data: dict) -> dict:
    """
    检查食伤生财组合
    """
    result = {
        'has_combination': False,
        'shishen_positions': [],
        'shangguan_positions': [],
        'combination_type': '',
        'analysis': ''
    }
    
    shishen = ten_gods_stats.get('食神', 0)
    shangguan = ten_gods_stats.get('伤官', 0)
    zhengcai = ten_gods_stats.get('正财', 0)
    piancai = ten_gods_stats.get('偏财', 0)
    
    has_shishang = shishen > 0 or shangguan > 0
    has_cai = zhengcai > 0 or piancai > 0
    
    if has_shishang and has_cai:
        result['has_combination'] = True
        if shishen > 0 and shangguan > 0:
            result['combination_type'] = '食伤生财'
        elif shishen > 0:
            result['combination_type'] = '食神生财'
        else:
            result['combination_type'] = '伤官生财'
        result['analysis'] = '命局有食伤生财组合，利于才华变现、创业创收'
    
    return result


def calculate_age(birth_date: str) -> int:
    """计算当前年龄"""
    try:
        birth = datetime.strptime(birth_date, '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birth.year
        if today.month < birth.month or (today.month == birth.month and today.day < birth.day):
            age -= 1
        return max(0, age)
    except:
        return 0


def get_directions_from_elements(xi_elements: List[str], ji_elements: List[str]) -> dict:
    """根据喜忌五行获取方位建议"""
    result = {
        'best_directions': [],
        'avoid_directions': [],
        'analysis': ''
    }
    
    for element in xi_elements:
        direction = ELEMENT_DIRECTION.get(element)
        if direction and direction not in result['best_directions']:
            result['best_directions'].append(direction)
    
    for element in ji_elements:
        direction = ELEMENT_DIRECTION.get(element)
        if direction and direction not in result['avoid_directions']:
            result['avoid_directions'].append(direction)
    
    return result


def get_industries_from_elements(xi_elements: List[str], ji_elements: List[str]) -> dict:
    """
    根据喜忌五行获取行业建议（从数据库读取）
    
    Args:
        xi_elements: 喜神五行列表，如 ['金', '土']
        ji_elements: 忌神五行列表，如 ['木', '火']
    
    Returns:
        dict: {
            'best_industries': [...],      # 适合的行业列表
            'secondary_industries': [],    # 次要行业（预留）
            'avoid_industries': [...],     # 需要避免的行业列表
            'analysis': ''                 # 分析说明（预留）
        }
    """
    # 使用 IndustryService 从数据库查询行业数据
    return IndustryService.get_industries_by_elements(xi_elements, ji_elements)


class CareerWealthRequest(BaziBaseRequest):
    """事业财富分析请求模型"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量 CAREER_WEALTH_BOT_ID）")


class CareerWealthResponse(BaseModel):
    """事业财富分析响应模型"""
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/career-wealth/stream", summary="流式生成事业财富分析")
async def career_wealth_analysis_stream(request: CareerWealthRequest):
    """
    流式生成事业财富分析
    
    基于用户的八字数据，调用 Coze Bot 流式生成事业财富分析内容。
    """
    return StreamingResponse(
        career_wealth_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.bot_id
        ),
        media_type="text/event-stream"
    )


async def career_wealth_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """流式生成事业财富分析的生成器"""
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > CAREER_WEALTH_BOT_ID > COZE_BOT_ID）
        if not bot_id:
            bot_id = os.getenv("CAREER_WEALTH_BOT_ID")
            if not bot_id:
                bot_id = os.getenv("COZE_BOT_ID")
                if not bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失: 请设置环境变量 CAREER_WEALTH_BOT_ID 或 COZE_BOT_ID。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"事业财富分析请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={bot_id}")
        
        # 2. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            "solar",
            None, None, None
        )
        
        # 3. 使用统一接口获取所有数据（包括特殊流年）
        loop = asyncio.get_event_loop()
        executor = None
        
        try:
            # 使用 BaziDataOrchestrator 获取所有数据
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                final_solar_date, final_solar_time, gender,
                modules={
                    'bazi': True, 'wangshuai': True, 'detail': True,
                    'dayun': {'mode': 'count', 'count': 13},  # 获取所有大运
                    'special_liunians': {'dayun_config': {'mode': 'count', 'count': 13}, 'count': 200}  # 获取所有大运的特殊流年
                }
            )
            
            bazi_data = orchestrator_data['bazi']
            wangshuai_result = orchestrator_data['wangshuai']
            detail_result = orchestrator_data['detail']
            
            # 获取大运序列（统一接口返回的是列表）
            dayun_sequence = orchestrator_data.get('dayun', [])
            
            # 提取特殊流年（统一接口返回的是字典格式，包含 'list', 'by_dayun', 'formatted'）
            special_liunians_data = orchestrator_data.get('special_liunians', {})
            if isinstance(special_liunians_data, dict):
                special_liunians = special_liunians_data.get('list', [])
            elif isinstance(special_liunians_data, list):
                special_liunians = special_liunians_data
            else:
                special_liunians = []
            
            bazi_data = validate_bazi_data(bazi_data)
            
            # 处理旺衰数据
            if not wangshuai_result.get('success'):
                logger.warning(f"旺衰分析失败: {wangshuai_result.get('error')}")
                wangshuai_data = {}
            else:
                wangshuai_data = wangshuai_result.get('data', {})
                
        except Exception as e:
            import traceback
            error_msg = {'type': 'error', 'content': f"获取数据失败: {str(e)}"}
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 4. 获取规则匹配数据（事业、财富等）
        try:
            rule_data = {
                'basic_info': bazi_data.get('basic_info', {}),
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                'details': bazi_data.get('details', {}),
                'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
                'elements': bazi_data.get('elements', {}),
                'element_counts': bazi_data.get('element_counts', {}),
                'relationships': bazi_data.get('relationships', {})
            }
            
            # 一次查询匹配多种类型
            all_matched_rules = await loop.run_in_executor(
                executor,
                RuleService.match_rules,
                rule_data,
                ['career', 'wealth', 'summary'],
                True
            )
            
            # 按类型分类
            career_judgments = []
            wealth_judgments = []
            for rule in all_matched_rules:
                rule_type = rule.get('rule_type', '')
                rule_name = rule.get('rule_name', '')
                content = rule.get('content', {})
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                
                if rule_type == 'career':
                    career_judgments.append({'name': rule_name, 'text': text})
                elif rule_type == 'wealth':
                    wealth_judgments.append({'name': rule_name, 'text': text})
                    
        except Exception as e:
            logger.warning(f"规则匹配失败（不影响业务）: {e}")
            career_judgments = []
            wealth_judgments = []
        
        # 5. 提取大运流年数据（使用统一接口获取的数据）
        current_age = calculate_age(final_solar_date)
        
        # 计算原局五行统计
        element_counts = bazi_data.get('element_counts', {})
        bazi_elements = {
            '木': element_counts.get('木', 0),
            '火': element_counts.get('火', 0),
            '土': element_counts.get('土', 0),
            '金': element_counts.get('金', 0),
            '水': element_counts.get('水', 0)
        }
        
        # 识别现行运和关键节点大运
        dayun_analysis_result = identify_key_dayuns(dayun_sequence, bazi_elements, current_age)
        current_dayun_info = dayun_analysis_result.get('current_dayun')
        key_dayuns_list = dayun_analysis_result.get('key_dayuns', [])
        
        # 按大运分组特殊流年
        dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
        
        # 构建现行运数据（包含流年）
        current_dayun = {}
        if current_dayun_info:
            current_step = current_dayun_info.get('step')
            if current_step is None:
                for idx, dayun in enumerate(dayun_sequence):
                    if dayun == current_dayun_info:
                        current_step = idx
                        break
            dayun_liunian_data = dayun_liunians.get(current_step, {}) if current_step is not None else {}
            all_liunians = []
            if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
            if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
            if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
            if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
            current_dayun = {
                'step': str(current_step) if current_step is not None else '',
                'stem': current_dayun_info.get('stem', ''),
                'branch': current_dayun_info.get('branch', ''),
                'age_display': current_dayun_info.get('age_display', current_dayun_info.get('age_range', '')),
                'main_star': current_dayun_info.get('main_star', ''),
                'description': current_dayun_info.get('description', ''),
                'liunians': all_liunians
            }
        
        # 构建关键节点大运数据（包含流年）
        key_dayun_list = []
        for key_dayun_info in key_dayuns_list:
            key_step = key_dayun_info.get('step')
            if key_step is None:
                for idx, dayun in enumerate(dayun_sequence):
                    if dayun == key_dayun_info:
                        key_step = idx
                        break
            dayun_liunian_data = dayun_liunians.get(key_step, {}) if key_step is not None else {}
            all_liunians = []
            if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
            if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
            if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
            if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
            key_dayun_list.append({
                'step': str(key_step) if key_step is not None else '',
                'stem': key_dayun_info.get('stem', ''),
                'branch': key_dayun_info.get('branch', ''),
                'age_display': key_dayun_info.get('age_display', key_dayun_info.get('age_range', '')),
                'main_star': key_dayun_info.get('main_star', ''),
                'description': key_dayun_info.get('description', ''),
                'relation_type': key_dayun_info.get('relation_type', ''),
                'liunians': all_liunians
            })
        
        # 获取所有大运（用于参考）
        all_dayuns = []
        for dayun in dayun_sequence:
            step = dayun.get('step')
            if step == '小运':
                continue
            dayun_step = dayun.get('step')
            if dayun_step is None:
                for idx, d in enumerate(dayun_sequence):
                    if d == dayun:
                        dayun_step = idx
                        break
            dayun_liunian_data = dayun_liunians.get(dayun_step, {}) if dayun_step is not None else {}
            all_liunians = []
            if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
            if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
            if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
            if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
            all_dayuns.append({
                'step': str(dayun_step) if dayun_step is not None else '',
                'stem': dayun.get('stem', ''),
                'branch': dayun.get('branch', ''),
                'age_display': dayun.get('age_display', dayun.get('age_range', '')),
                'main_star': dayun.get('main_star', ''),
                'description': dayun.get('description', ''),
                'liunians': all_liunians
            })
        
        # 6. 提取神煞数据
        deities_data = {}
        try:
            details = bazi_data.get('details', {})
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_details = details.get(pillar_name, {})
                deities = pillar_details.get('deities', [])
                if deities:
                    deities_data[pillar_name] = deities
        except Exception as e:
            logger.warning(f"提取神煞数据失败（不影响业务）: {e}")
        
        # 7. 提取十神数据
        ten_gods_data = bazi_data.get('ten_gods_stats', {})
        ten_gods_by_pillar = {}
        try:
            details = bazi_data.get('details', {})
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_details = details.get(pillar_name, {})
                ten_gods_by_pillar[pillar_name] = {
                    'main_star': pillar_details.get('main_star', ''),
                    'hidden_stars': pillar_details.get('hidden_stars', [])
                }
        except Exception as e:
            logger.warning(f"提取十神数据失败（不影响业务）: {e}")
        
        # 8. 提取日柱和月柱数据
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        day_pillar = bazi_pillars.get('day', {})
        month_pillar = bazi_pillars.get('month', {})
        year_pillar = bazi_pillars.get('year', {})
        hour_pillar = bazi_pillars.get('hour', {})
        
        # 9. 提取喜忌数据
        xi_ji_data = {}
        try:
            if wangshuai_data:
                xi_ji_data = {
                    'xi_shen': wangshuai_data.get('xi_shen', []),
                    'ji_shen': wangshuai_data.get('ji_shen', []),
                    'xi_shen_elements': wangshuai_data.get('xi_shen_elements', []),
                    'ji_shen_elements': wangshuai_data.get('ji_shen_elements', []),
                    'analysis': ''
                }
        except Exception as e:
            logger.warning(f"提取喜忌数据失败（不影响业务）: {e}")
        
        # 10. 提取五行分布
        element_counts = bazi_data.get('element_counts', {})
        wuxing_distribution = {
            '木': element_counts.get('木', 0),
            '火': element_counts.get('火', 0),
            '土': element_counts.get('土', 0),
            '金': element_counts.get('金', 0),
            '水': element_counts.get('水', 0)
        }
        
        # 11. 提取事业星和财富星
        career_star = extract_career_star(ten_gods_data)
        wealth_star = extract_wealth_star(ten_gods_data)
        shishang_shengcai = check_shishang_shengcai(ten_gods_data, ten_gods_by_pillar)
        
        # 12. 获取方位和行业建议
        xi_elements = xi_ji_data.get('xi_shen_elements', [])
        ji_elements = xi_ji_data.get('ji_shen_elements', [])
        fangwei = get_directions_from_elements(xi_elements, ji_elements)
        hangye = get_industries_from_elements(xi_elements, ji_elements)
        
        # 13. 构建完整的输入数据
        input_data = {
            # 命盘事业财富总论
            'mingpan_shiye_caifu_zonglun': {
                'day_master': {
                    'stem': day_pillar.get('stem', ''),
                    'branch': day_pillar.get('branch', ''),
                    'element': STEM_ELEMENT.get(day_pillar.get('stem', ''), ''),
                    'yin_yang': STEM_YIN_YANG.get(day_pillar.get('stem', ''), '')
                },
                'bazi_pillars': {
                    'year': {'stem': year_pillar.get('stem', ''), 'branch': year_pillar.get('branch', '')},
                    'month': {'stem': month_pillar.get('stem', ''), 'branch': month_pillar.get('branch', '')},
                    'day': {'stem': day_pillar.get('stem', ''), 'branch': day_pillar.get('branch', '')},
                    'hour': {'stem': hour_pillar.get('stem', ''), 'branch': hour_pillar.get('branch', '')}
                },
                'wuxing_distribution': wuxing_distribution,
                'wangshuai': wangshuai_data.get('wangshuai', ''),
                'wangshuai_detail': wangshuai_data.get('detail', ''),
                'yue_ling': BRANCH_MONTH.get(month_pillar.get('branch', ''), ''),
                'gender': gender,
                'geju_type': wangshuai_data.get('geju_type', ''),
                'ten_gods': ten_gods_by_pillar
            },
            
            # 事业星与事业宫
            'shiye_xing_gong': {
                'shiye_xing': career_star,
                'month_pillar_analysis': {
                    'stem': month_pillar.get('stem', ''),
                    'branch': month_pillar.get('branch', ''),
                    'stem_shishen': ten_gods_by_pillar.get('month', {}).get('main_star', ''),
                    'branch_shishen': '',
                    'hidden_stems': ten_gods_by_pillar.get('month', {}).get('hidden_stars', []),
                    'analysis': ''
                },
                'ten_gods': ten_gods_by_pillar,
                'ten_gods_stats': ten_gods_data,
                'deities': deities_data,
                'career_judgments': career_judgments
            },
            
            # 财富星与财富宫
            'caifu_xing_gong': {
                'caifu_xing': wealth_star,
                'year_pillar_analysis': {
                    'stem': year_pillar.get('stem', ''),
                    'branch': year_pillar.get('branch', ''),
                    'stem_shishen': ten_gods_by_pillar.get('year', {}).get('main_star', ''),
                    'branch_shishen': '',
                    'analysis': ''
                },
                'hour_pillar_analysis': {
                    'stem': hour_pillar.get('stem', ''),
                    'branch': hour_pillar.get('branch', ''),
                    'stem_shishen': ten_gods_by_pillar.get('hour', {}).get('main_star', ''),
                    'branch_shishen': '',
                    'analysis': ''
                },
                'shishang_shengcai': shishang_shengcai,
                'caiku': {
                    'has_caiku': False,
                    'caiku_position': '',
                    'caiku_status': '',
                    'analysis': ''
                },
                'wealth_judgments': wealth_judgments
            },
            
            # 事业运势
            'shiye_yunshi': {
                'current_age': calculate_age(final_solar_date),
                'current_dayun': current_dayun,
                'key_dayuns': key_dayun_list,
                'all_dayuns': all_dayuns,
                'key_liunian': [],
                'chonghe_xinghai': {
                    'dayun_relations': [],
                    'liunian_relations': [],
                    'key_conflicts': []
                }
            },
            
            # 财富运势
            'caifu_yunshi': {
                'wealth_stages': {
                    'early': {'age_range': '1-30岁', 'stage_type': '', 'description': ''},
                    'middle': {'age_range': '30-50岁', 'stage_type': '', 'description': ''},
                    'late': {'age_range': '50岁以后', 'stage_type': '', 'description': ''}
                },
                'current_dayun': current_dayun,
                'key_dayuns': key_dayun_list,
                'all_dayuns': all_dayuns,
                'liunian_wealth_nodes': [],
                'caiku_timing': {
                    'has_timing': False,
                    'timing_years': [],
                    'timing_description': ''
                }
            },
            
            # 提运建议
            'tiyun_jianyi': {
                'ten_gods_summary': '',
                'xi_ji': xi_ji_data,
                'fangwei': fangwei,
                'hangye': hangye,
                'wuxing_hangye': IndustryService.get_industry_mapping()  # 从数据库读取
            }
        }
        
        # 14. 验证数据完整性
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            logger.error(f"数据完整性验证失败: {validation_error}")
            error_msg = {
                'type': 'error',
                'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        logger.info("✓ 数据完整性验证通过")
        
        # 15. 构建自然语言 prompt
        prompt = build_natural_language_prompt(input_data)
        logger.info(f"发送给 Coze Bot 的自然语言 prompt（前500字符）: {prompt[:500]}...")
        
        # 16. 创建Coze流式服务
        try:
            from server.services.coze_stream_service import CozeStreamService
            
            logger.info(f"使用 Bot ID: {bot_id}")
            coze_service = CozeStreamService(bot_id=bot_id)
            actual_bot_id = bot_id or coze_service.bot_id
            
        except ValueError as e:
            logger.error(f"Coze API 配置错误: {e}")
            error_msg = {
                'type': 'error',
                'content': f"Coze API 配置缺失: {str(e)}。请设置环境变量 COZE_ACCESS_TOKEN 和 CAREER_WEALTH_BOT_ID。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            logger.error(f"初始化 Coze 服务失败: {e}", exc_info=True)
            error_msg = {'type': 'error', 'content': f"初始化 Coze 服务失败: {str(e)}"}
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 17. 流式生成
        logger.info(f"开始流式生成，Bot ID: {actual_bot_id}, Prompt 长度: {len(prompt)}")
        
        try:
            chunk_count = 0
            has_content = False
            
            async for result in coze_service.stream_custom_analysis(prompt, actual_bot_id):
                chunk_count += 1
                
                if result.get('type') == 'progress':
                    content = result.get('content', '')
                    if '对不起' in content and '无法回答' in content:
                        logger.warning(f"检测到错误消息片段: {content[:100]}")
                        continue
                    else:
                        has_content = True
                        msg = {'type': 'progress', 'content': content}
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.05)
                elif result.get('type') == 'complete':
                    has_content = True
                    msg = {'type': 'complete', 'content': result.get('content', '')}
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    logger.info(f"流式生成完成，共 {chunk_count} 个chunk")
                    return
                elif result.get('type') == 'error':
                    error_content = result.get('content', '未知错误')
                    logger.error(f"Coze API 返回错误: {error_content}")
                    msg = {'type': 'error', 'content': error_content}
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    return
            
            if not has_content:
                logger.warning(f"未收到任何内容，chunk_count: {chunk_count}")
                error_msg = {'type': 'error', 'content': f'Coze Bot 未返回内容，请检查 Bot 配置'}
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            import traceback
            logger.error(f"流式生成异常: {e}\n{traceback.format_exc()}")
            error_msg = {'type': 'error', 'content': f"流式生成失败: {str(e)}"}
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
    except Exception as e:
        import traceback
        logger.error(f"事业财富分析失败: {e}\n{traceback.format_exc()}")
        error_msg = {'type': 'error', 'content': f"分析失败: {str(e)}"}
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


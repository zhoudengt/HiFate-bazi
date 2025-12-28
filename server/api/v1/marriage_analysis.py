#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-感情婚姻API
基于用户生辰数据，使用 Coze Bot 流式生成感情婚姻分析
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
import json
import asyncio

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
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun

logger = logging.getLogger(__name__)

router = APIRouter()


def build_natural_language_prompt(data: dict) -> str:
    """
    将 JSON 数据转换为自然语言格式的提示词
    参考 wuxing_proportion_service.py 的 build_llm_prompt 实现
    
    Args:
        data: 婚姻分析所需的完整数据
        
    Returns:
        str: 自然语言格式的提示词
    """
    prompt_lines = []
    prompt_lines.append("请基于以下八字信息进行感情婚姻分析，分别从命盘总论、配偶特征、感情走势、神煞点睛和建议方向五个方面进行详细分析：")
    prompt_lines.append("")
    
    # 1. 命盘总论
    prompt_lines.append("【命盘总论】")
    mingpan = data.get('mingpan_zonglun', {})
    
    # 八字排盘
    bazi_pillars = mingpan.get('bazi_pillars', {})
    if bazi_pillars:
        prompt_lines.append("四柱排盘：")
        for pillar_name, pillar_key in [('年柱', 'year'), ('月柱', 'month'), ('日柱', 'day'), ('时柱', 'hour')]:
            pillar = bazi_pillars.get(pillar_key, {})
            stem = pillar.get('stem', '')
            branch = pillar.get('branch', '')
            if stem and branch:
                prompt_lines.append(f"  {pillar_name}：{stem}{branch}")
    
    # 十神
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
    
    # 旺衰
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        prompt_lines.append(f"身旺身弱：{wangshuai}")
    
    # 日柱
    day_pillar = mingpan.get('day_pillar', {})
    if day_pillar:
        stem = day_pillar.get('stem', '')
        branch = day_pillar.get('branch', '')
        prompt_lines.append(f"日主：{stem}{branch}")
    
    prompt_lines.append("")
    
    # 2. 配偶特征
    prompt_lines.append("【配偶特征】")
    peiou = data.get('peiou_tezheng', {})
    
    # 神煞
    deities = peiou.get('deities', {})
    if deities:
        prompt_lines.append("神煞分布：")
        for pillar_key, pillar_deities in deities.items():
            pillar_names_map = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
            pillar_name = pillar_names_map.get(pillar_key, pillar_key)
            if pillar_deities:
                deities_str = '、'.join(pillar_deities) if isinstance(pillar_deities, list) else str(pillar_deities)
                prompt_lines.append(f"  {pillar_name}：{deities_str}")
    
    # 婚姻判词
    marriage_judgments = peiou.get('marriage_judgments', [])
    if marriage_judgments:
        prompt_lines.append("婚姻判词：")
        for j in marriage_judgments:
            name = j.get('name', '')
            text = j.get('text', '')
            if text:
                prompt_lines.append(f"  - {name}：{text}")
    
    # 桃花判词
    peach_blossom_judgments = peiou.get('peach_blossom_judgments', [])
    if peach_blossom_judgments:
        prompt_lines.append("桃花判词：")
        for j in peach_blossom_judgments:
            name = j.get('name', '')
            text = j.get('text', '')
            if text:
                prompt_lines.append(f"  - {name}：{text}")
    
    # 婚配判词
    matchmaking_judgments = peiou.get('matchmaking_judgments', [])
    if matchmaking_judgments:
        prompt_lines.append("婚配判词：")
        for j in matchmaking_judgments:
            name = j.get('name', '')
            text = j.get('text', '')
            if text:
                prompt_lines.append(f"  - {name}：{text}")
    
    # 正缘判词
    zhengyuan_judgments = peiou.get('zhengyuan_judgments', [])
    if zhengyuan_judgments:
        prompt_lines.append("正缘判词：")
        for j in zhengyuan_judgments:
            name = j.get('name', '')
            text = j.get('text', '')
            if text:
                prompt_lines.append(f"  - {name}：{text}")
    
    prompt_lines.append("")
    
    # 3. 感情走势
    prompt_lines.append("【感情走势】")
    ganqing = data.get('ganqing_zoushi', {})
    
    dayun_list = ganqing.get('dayun_list', [])
    if dayun_list:
        prompt_lines.append("大运分析（第2-4步大运）：")
        for dayun in dayun_list:
            step = dayun.get('step', '')
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            main_star = dayun.get('main_star', '')
            age_display = dayun.get('age_display', '')
            prompt_lines.append(f"  第{step}步大运：{stem}{branch}（{age_display}）主星{main_star}")
            # 输出该大运下的关键流年
            liunians = dayun.get('liunians', [])
            if liunians:
                prompt_lines.append(f"    关键流年：")
                for liunian in liunians:
                    year = liunian.get('year', '')
                    liunian_type = liunian.get('type', '')
                    prompt_lines.append(f"      - {year}年（{liunian_type}）：[分析该年的感情婚姻风险]")
            else:
                prompt_lines.append(f"    关键流年：暂无特殊流年")
    else:
        prompt_lines.append("  （大运数据待完善）")
    
    prompt_lines.append("")
    
    # 4. 神煞点睛
    prompt_lines.append("【神煞点睛】")
    shensha = data.get('shensha_dianjing', {})
    deities_all = shensha.get('deities', {})
    if deities_all:
        for pillar_key, pillar_deities in deities_all.items():
            pillar_names_map = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
            pillar_name = pillar_names_map.get(pillar_key, pillar_key)
            if pillar_deities:
                deities_str = '、'.join(pillar_deities) if isinstance(pillar_deities, list) else str(pillar_deities)
                prompt_lines.append(f"  {pillar_name}神煞：{deities_str}")
    else:
        prompt_lines.append("  （神煞数据待完善）")
    
    prompt_lines.append("")
    
    # 5. 建议方向
    prompt_lines.append("【建议方向】")
    jianyi = data.get('jianyi_fangxiang', {})
    
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
    
    prompt_lines.append("")
    prompt_lines.append("请根据以上信息，结合八字命理学知识，给出详细的感情婚姻分析。")
    
    return '\n'.join(prompt_lines)


def validate_input_data(data: dict) -> tuple[bool, str]:
    """
    验证输入数据完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        (is_valid, error_message): 是否有效，错误信息（如果无效）
    """
    required_fields = {
        'mingpan_zonglun': {
            'bazi_pillars': '八字排盘',
            'ten_gods': '十神',
            'wangshuai': '旺衰',
            'branch_relations': '地支刑冲破害',
            'day_pillar': '日柱'
        },
        'peiou_tezheng': {
            'ten_gods': '十神',
            'deities': '神煞',
            'marriage_judgments': '婚姻判词',
            'peach_blossom_judgments': '桃花判词',
            'matchmaking_judgments': '婚配判词',
            'zhengyuan_judgments': '正缘判词'
        },
        'ganqing_zoushi': {
            'dayun_list': '大运流年',
            'ten_gods': '十神'
        },
        'shensha_dianjing': {
            'deities': '神煞'
        },
        'jianyi_fangxiang': {
            'ten_gods': '十神',
            'xi_ji': '喜忌',
            'dayun_list': '大运流年'
        }
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
            elif isinstance(section_data[field], (list, dict)) and len(section_data[field]) == 0:
                # 对于列表和字典，允许为空（某些判词可能为空）
                pass
            elif isinstance(section_data[field], str) and not section_data[field].strip():
                # 对于字符串，允许为空（某些字段可能为空字符串）
                pass
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""


class MarriageAnalysisRequest(BaziBaseRequest):
    """感情婚姻分析请求模型"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID 环境变量）")


async def marriage_analysis_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    calendar_type: Optional[str] = "solar",
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    bot_id: Optional[str] = None
):
    """
    流式生成感情婚姻分析
    
    Args:
        solar_date: 阳历日期或农历日期
        solar_time: 出生时间
        gender: 性别
        calendar_type: 历法类型（solar/lunar），默认solar
        location: 出生地点（用于时区转换，优先级1）
        latitude: 纬度（用于时区转换，优先级2）
        longitude: 经度（用于时区转换和真太阳时计算，优先级2）
        bot_id: Coze Bot ID（可选，优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID 环境变量）
    """
    try:
        # 确定使用的 bot_id（优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID > COZE_BOT_ID）
        if not bot_id:
            bot_id = os.getenv("MARRIAGE_ANALYSIS_BOT_ID")
            if not bot_id:
                # 如果没有设置 MARRIAGE_ANALYSIS_BOT_ID，使用 COZE_BOT_ID 作为默认值
                bot_id = os.getenv("COZE_BOT_ID")
                if not bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失: 请设置环境变量 MARRIAGE_ANALYSIS_BOT_ID 或 COZE_BOT_ID 或在请求参数中提供 bot_id。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        # 1. 处理农历输入和时区转换（支持7个标准参数）
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            calendar_type or "solar",
            location,
            latitude,
            longitude
        )
        
        # 2. 并行获取基础数据
        loop = asyncio.get_event_loop()
        executor = None
        
        try:
            # 并行获取基础数据
            bazi_task = loop.run_in_executor(
                executor,
                lambda: BaziService.calculate_bazi_full(
                    final_solar_date,
                    final_solar_time,
                    gender
                )
            )
            wangshuai_task = loop.run_in_executor(
                executor,
                lambda: WangShuaiService.calculate_wangshuai(
                    final_solar_date,
                    final_solar_time,
                    gender
                )
            )
            
            bazi_result, wangshuai_result = await asyncio.gather(bazi_task, wangshuai_task)
            
            # 提取八字数据（BaziService.calculate_bazi_full 返回的结构是 {bazi: {...}, rizhu: {...}, matched_rules: [...]}）
            if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
                bazi_data = bazi_result['bazi']
            else:
                bazi_data = bazi_result
            
            # 验证数据类型
            bazi_data = validate_bazi_data(bazi_data)
            if not bazi_data:
                raise ValueError("八字计算失败，返回数据为空")
            
            # 处理旺衰数据
            if not wangshuai_result.get('success'):
                logger.warning(f"旺衰分析失败: {wangshuai_result.get('error')}")
                wangshuai_data = {}
            else:
                wangshuai_data = wangshuai_result.get('data', {})
            
            # ✅ 使用统一数据服务获取大运流年、特殊流年数据（确保数据一致性）
            from server.services.bazi_data_service import BaziDataService
            
            # 获取完整运势数据（包含大运序列、流年序列、特殊流年）
            fortune_data = await BaziDataService.get_fortune_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                calendar_type=calendar_type or "solar",
                location=location,
                latitude=latitude,
                longitude=longitude,
                include_dayun=True,
                include_liunian=True,
                include_special_liunian=True,
                dayun_mode=BaziDataService.DEFAULT_DAYUN_MODE,  # 统一的大运模式
                target_years=BaziDataService.DEFAULT_TARGET_YEARS,  # 统一的年份范围
                current_time=None
            )
            
            # 从统一数据服务获取大运序列和特殊流年
            dayun_sequence = []
            special_liunians = []
            
            # 转换为字典格式（兼容现有代码）
            for dayun in fortune_data.dayun_sequence:
                dayun_sequence.append({
                    'step': dayun.step,
                    'stem': dayun.stem,
                    'branch': dayun.branch,
                    'year_start': dayun.year_start,
                    'year_end': dayun.year_end,
                    'age_range': dayun.age_range,
                    'age_display': dayun.age_display,
                    'nayin': dayun.nayin,
                    'main_star': dayun.main_star,
                    'hidden_stems': dayun.hidden_stems or [],
                    'hidden_stars': dayun.hidden_stars or [],
                    'star_fortune': dayun.star_fortune,
                    'self_sitting': dayun.self_sitting,
                    'kongwang': dayun.kongwang,
                    'deities': dayun.deities or [],
                    'details': dayun.details or {}
                })
            
            # 转换为字典格式（兼容现有代码）
            for special_liunian in fortune_data.special_liunians:
                special_liunians.append({
                    'year': special_liunian.year,
                    'stem': special_liunian.stem,
                    'branch': special_liunian.branch,
                    'ganzhi': special_liunian.ganzhi,
                    'age': special_liunian.age,
                    'age_display': special_liunian.age_display,
                    'nayin': special_liunian.nayin,
                    'main_star': special_liunian.main_star,
                    'hidden_stems': special_liunian.hidden_stems or [],
                    'hidden_stars': special_liunian.hidden_stars or [],
                    'star_fortune': special_liunian.star_fortune,
                    'self_sitting': special_liunian.self_sitting,
                    'kongwang': special_liunian.kongwang,
                    'deities': special_liunian.deities or [],
                    'relations': special_liunian.relations or [],
                    'dayun_step': special_liunian.dayun_step,
                    'dayun_ganzhi': special_liunian.dayun_ganzhi,
                    'details': special_liunian.details or {}
                })
            
        except Exception as e:
            import traceback
            error_msg = {
                'type': 'error',
                'content': f"获取数据失败: {str(e)}\n{traceback.format_exc()}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 3. 获取规则匹配数据（婚姻、桃花等）- 恢复原来的方式
        marriage_judgments = []
        peach_blossom_judgments = []
        matchmaking_judgments = []
        zhengyuan_judgments = []
        
        try:
            matched_rules = await loop.run_in_executor(
                executor,
                RuleService.match_rules,
                bazi_data,
                ['marriage', 'peach_blossom', 'marriage_match', 'zhengyuan'],
                True  # use_cache
            )
            
            for rule in matched_rules:
                rule_type = rule.get('rule_type', '')
                content = rule.get('content', {})
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                rule_name = rule.get('rule_name', '')
                
                if 'marriage' in rule_type.lower() or '婚姻' in text:
                    if '婚配' in rule_name or '婚配' in text:
                        matchmaking_judgments.append({
                            'name': rule_name,
                            'text': text
                        })
                    elif '正缘' in rule_name or '正缘' in text:
                        zhengyuan_judgments.append({
                            'name': rule_name,
                            'text': text
                        })
                    else:
                        marriage_judgments.append({
                            'name': rule_name,
                            'text': text
                        })
                if 'peach' in rule_type.lower() or '桃花' in text:
                    peach_blossom_judgments.append({
                        'name': rule_name,
                        'text': text
                    })
        except Exception as e:
            logger.warning(f"规则匹配失败（不影响业务）: {e}")
        
        # 4. 提取大运流年数据（从 detail_result 获取，包含完整大运序列）
        # ⚠️ 只修改大运流年部分：添加特殊流年分组
        dayun_list = []
        try:
            # 按大运分组特殊流年（只修改这部分）
            dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
            
            # 跳过第0个"小运"，获取索引1、2、3的大运（第2-4步）
            for idx in [1, 2, 3]:
                if idx < len(dayun_sequence):
                    dayun = dayun_sequence[idx]
                    dayun_step = dayun.get('step')
                    if dayun_step is None:
                        dayun_step = idx
                    
                    # ⚠️ 只修改这部分：获取该大运下的特殊流年
                    dayun_liunian_data = dayun_liunians.get(dayun_step, {}) if dayun_step is not None else {}
                    all_liunians = []
                    if dayun_liunian_data.get('tiankedi_chong'): all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
                    if dayun_liunian_data.get('tianhedi_he'): all_liunians.extend(dayun_liunian_data['tianhedi_he'])
                    if dayun_liunian_data.get('suiyun_binglin'): all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
                    if dayun_liunian_data.get('other'): all_liunians.extend(dayun_liunian_data['other'])
                    
                    # 提取关键信息（包含流年）
                    dayun_info = {
                        'step': dayun.get('step', idx),
                        'stem': dayun.get('stem', ''),
                        'branch': dayun.get('branch', ''),
                        'main_star': dayun.get('main_star', ''),
                        'year_start': dayun.get('year_start', 0),
                        'year_end': dayun.get('year_end', 0),
                        'age_display': dayun.get('age_display', ''),
                        'liunians': all_liunians  # ⚠️ 只修改这部分：添加流年数据
                    }
                    dayun_list.append(dayun_info)
        except Exception as e:
            logger.warning(f"提取大运流年数据失败（不影响业务）: {e}")
        
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
        
        # 7. 提取十神数据（确保数据完整）
        ten_gods_data = bazi_data.get('ten_gods_stats', {})
        if not ten_gods_data:
            logger.warning("十神数据为空，可能影响分析结果")
        
        # 8. 提取地支刑冲破害数据
        branch_relations = {}
        try:
            relationships = bazi_data.get('relationships', {})
            branch_relations = relationships.get('branch_relations', {})
        except Exception as e:
            logger.warning(f"提取地支刑冲破害数据失败（不影响业务）: {e}")
        
        # 9. 提取日柱数据
        day_pillar = {}
        try:
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            day_pillar = bazi_pillars.get('day', {})
        except Exception as e:
            logger.warning(f"提取日柱数据失败（不影响业务）: {e}")
        
        # 10. 提取喜忌数据
        xi_ji_data = {}
        try:
            if wangshuai_data:
                xi_ji_data = {
                    'xi_shen': wangshuai_data.get('xi_shen', []),
                    'ji_shen': wangshuai_data.get('ji_shen', []),
                    'xi_shen_elements': wangshuai_data.get('xi_shen_elements', []),
                    'ji_shen_elements': wangshuai_data.get('ji_shen_elements', []),
                    'final_xi_ji': wangshuai_data.get('final_xi_ji', {})
                }
        except Exception as e:
            logger.warning(f"提取喜忌数据失败（不影响业务）: {e}")
        
        # 11. 构建完整的输入数据（JSON格式）
        # 确保包含所有必需的数据：八字排盘、十神、旺衰、地支刑冲破害、日柱、
        # 大运流年（第2、3、4个大运）、神煞、喜忌、婚姻判词、桃花判词、婚配判词、正缘判词
        input_data = {
            # 命盘总论数据（包含：八字排盘、十神、旺衰、地支刑冲破害、日柱）
            'mingpan_zonglun': {
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),  # 八字排盘（四柱完整数据）
                'ten_gods': ten_gods_data,  # 十神数据
                'wangshuai': wangshuai_data.get('wangshuai', ''),  # 旺衰分析结果
                'branch_relations': branch_relations,  # 地支刑冲破害关系
                'day_pillar': day_pillar  # 日柱详细信息
            },
            # 配偶特征数据（包含：十神、神煞、婚姻判词、桃花判词、婚配判词、正缘判词）
            'peiou_tezheng': {
                'ten_gods': ten_gods_data,  # 十神数据
                'deities': deities_data,  # 神煞数据
                'marriage_judgments': marriage_judgments,  # 婚姻判词
                'peach_blossom_judgments': peach_blossom_judgments,  # 桃花判词
                'matchmaking_judgments': matchmaking_judgments,  # 婚配判词
                'zhengyuan_judgments': zhengyuan_judgments  # 正缘判词
            },
            # 感情走势数据（包含：大运流年（第2、3、4个大运）、十神）
            'ganqing_zoushi': {
                'dayun_list': dayun_list,  # 大运流年（第2、3、4个大运，索引1、2、3）
                'ten_gods': ten_gods_data  # 十神数据
            },
            # 神煞点睛数据（包含：神煞）
            'shensha_dianjing': {
                'deities': deities_data  # 神煞数据（四柱神煞）
            },
            # 建议方向数据（包含：十神、喜忌、大运流年（第2、3、4个大运））
            'jianyi_fangxiang': {
                'ten_gods': ten_gods_data,  # 十神数据
                'xi_ji': xi_ji_data,  # 喜忌数据（喜神、忌神、喜忌五行）
                'dayun_list': dayun_list  # 大运流年（第2、3、4个大运）
            }
        }
        
        # 12. 验证数据完整性（确保所有必需数据都存在）
        logger.info(f"数据提取完成 - 八字排盘: {bool(bazi_data.get('bazi_pillars'))}, "
                   f"十神: {bool(ten_gods_data)}, 旺衰: {bool(wangshuai_data.get('wangshuai'))}, "
                   f"地支刑冲破害: {bool(branch_relations)}, 日柱: {bool(day_pillar)}, "
                   f"大运流年: {len(dayun_list)}, 神煞: {bool(deities_data)}, "
                   f"喜忌: {bool(xi_ji_data)}, 婚姻判词: {len(marriage_judgments)}, "
                   f"桃花判词: {len(peach_blossom_judgments)}, 婚配判词: {len(matchmaking_judgments)}, "
                   f"正缘判词: {len(zhengyuan_judgments)}")
        
        # 13. 验证输入数据完整性
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
        
        # 14. 输出完整的 input_data 日志（便于调试，仅输出关键字段摘要）
        logger.info(f"准备发送给 Coze Bot 的数据摘要:")
        logger.info(f"  - 命盘总论: 八字排盘={bool(input_data['mingpan_zonglun'].get('bazi_pillars'))}, "
                   f"十神={bool(input_data['mingpan_zonglun'].get('ten_gods'))}, "
                   f"旺衰={bool(input_data['mingpan_zonglun'].get('wangshuai'))}")
        logger.info(f"  - 配偶特征: 十神={bool(input_data['peiou_tezheng'].get('ten_gods'))}, "
                   f"神煞={bool(input_data['peiou_tezheng'].get('deities'))}, "
                   f"婚姻判词={len(input_data['peiou_tezheng'].get('marriage_judgments', []))}")
        logger.info(f"  - 感情走势: 大运流年={len(input_data['ganqing_zoushi'].get('dayun_list', []))}, "
                   f"十神={bool(input_data['ganqing_zoushi'].get('ten_gods'))}")
        logger.info(f"  - 神煞点睛: 神煞={bool(input_data['shensha_dianjing'].get('deities'))}")
        logger.info(f"  - 建议方向: 十神={bool(input_data['jianyi_fangxiang'].get('ten_gods'))}, "
                   f"喜忌={bool(input_data['jianyi_fangxiang'].get('xi_ji'))}, "
                   f"大运流年={len(input_data['jianyi_fangxiang'].get('dayun_list', []))}")
        
        # 15. 将输入数据转换为自然语言格式的 prompt（参考 wuxing_proportion_service.py）
        prompt = build_natural_language_prompt(input_data)
        logger.info(f"发送给 Coze Bot 的自然语言 prompt（前500字符）: {prompt[:500]}...")
        
        # 16. 创建Coze流式服务
        try:
            from server.services.coze_stream_service import CozeStreamService
            
            # 确保 bot_id 已设置
            if not bot_id:
                bot_id = os.getenv("MARRIAGE_ANALYSIS_BOT_ID") or os.getenv("COZE_BOT_ID")
            
            logger.info(f"使用 Bot ID: {bot_id}")
            
            # 创建服务（bot_id 作为参数传入，如果为None则从环境变量获取）
            coze_service = CozeStreamService(bot_id=bot_id)
            
            # 如果传入的 bot_id 与服务的 bot_id 不同，使用传入的
            actual_bot_id = bot_id or coze_service.bot_id
            logger.info(f"实际使用的 Bot ID: {actual_bot_id}")
            
        except ValueError as e:
            logger.error(f"Coze API 配置错误: {e}")
            error_msg = {
                'type': 'error',
                'content': f"Coze API 配置缺失: {str(e)}。请设置环境变量 COZE_ACCESS_TOKEN 和 MARRIAGE_ANALYSIS_BOT_ID（或 COZE_BOT_ID）。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            logger.error(f"初始化 Coze 服务失败: {e}", exc_info=True)
            error_msg = {
                'type': 'error',
                'content': f"初始化 Coze 服务失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 17. 流式生成（使用实际 bot_id）
        actual_bot_id = bot_id or coze_service.bot_id
        logger.info(f"开始流式生成，Bot ID: {actual_bot_id}, Prompt 长度: {len(prompt)}")
        
        try:
            chunk_count = 0
            has_content = False
            
            async for result in coze_service.stream_custom_analysis(prompt, actual_bot_id):
                chunk_count += 1
                
                # 转换为SSE格式
                if result.get('type') == 'progress':
                    content = result.get('content', '')
                    # 检测是否为错误消息
                    if '对不起' in content and '无法回答' in content:
                        logger.warning(f"检测到错误消息片段 (Bot ID: {actual_bot_id}): {content[:100]}")
                        # 跳过这个内容块，不显示给用户
                        continue
                    else:
                        has_content = True
                        msg = {
                            'type': 'progress',
                            'content': content
                        }
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.05)
                elif result.get('type') == 'complete':
                    has_content = True
                    msg = {
                        'type': 'complete',
                        'content': result.get('content', '')
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    logger.info(f"流式生成完成，共 {chunk_count} 个chunk")
                    return
                elif result.get('type') == 'error':
                    error_content = result.get('content', '未知错误')
                    logger.error(f"Coze API 返回错误 (Bot ID: {actual_bot_id}): {error_content}")
                    msg = {
                        'type': 'error',
                        'content': error_content
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    return
            
            # 如果没有收到任何内容，返回提示
            if not has_content:
                logger.warning(f"未收到任何内容，chunk_count: {chunk_count}, Bot ID: {actual_bot_id}")
                error_msg = {
                    'type': 'error',
                    'content': f'Coze Bot 未返回内容（Bot ID: {actual_bot_id}），请检查 Bot 配置和提示词'
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            import traceback
            logger.error(f"流式生成异常: {e}\n{traceback.format_exc()}")
            error_msg = {
                'type': 'error',
                'content': f"流式生成失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
    
    except Exception as e:
        import traceback
        logger.error(f"流式生成器异常: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"流式生成失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


async def extract_marriage_analysis_data(
    solar_date: str,
    solar_time: str,
    gender: str
) -> Dict[str, Any]:
    """
    提取婚姻分析所需的元数据（不调用 Coze API）
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        
    Returns:
        包含所有元数据的字典
    """
    try:
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            "solar",
            None,
            None,
            None
        )
        
        # 2. 并行获取八字排盘、旺衰数据和详细八字数据（包含大运数据）
        loop = asyncio.get_event_loop()
        bazi_task = loop.run_in_executor(
            None,
            lambda: BaziService.calculate_bazi_full(
                final_solar_date,
                final_solar_time,
                gender
            )
        )
        wangshuai_task = loop.run_in_executor(
            None,
            lambda: WangShuaiService.calculate_wangshuai(
                final_solar_date,
                final_solar_time,
                gender
            )
        )
        detail_task = loop.run_in_executor(
            None,
            lambda: BaziDetailService.calculate_detail_full(
                final_solar_date,
                final_solar_time,
                gender
            )
        )
        
        bazi_data, wangshuai_data, detail_result = await asyncio.gather(bazi_task, wangshuai_task, detail_task)
        
        # 验证八字数据
        bazi_data = validate_bazi_data(bazi_data)
        if not bazi_data:
            raise ValueError("八字计算失败，返回数据为空")
        
        # 3. 获取规则匹配数据
        marriage_judgments = []
        peach_blossom_judgments = []
        matchmaking_judgments = []
        zhengyuan_judgments = []
        
        try:
            matched_rules = RuleService.match_rules(
                bazi_data,
                rule_types=['marriage', 'peach_blossom', 'marriage_match', 'zhengyuan']
            )
            
            for rule in matched_rules:
                rule_type = rule.get('rule_type', '')
                content = rule.get('content', {})
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                
                if 'marriage' in rule_type.lower() or '婚姻' in text:
                    marriage_judgments.append(text)
                if 'peach' in rule_type.lower() or '桃花' in text:
                    peach_blossom_judgments.append(text)
                if 'match' in rule_type.lower() or '婚配' in text:
                    matchmaking_judgments.append(text)
                if 'zhengyuan' in rule_type.lower() or '正缘' in text:
                    zhengyuan_judgments.append(text)
        except Exception as e:
            logger.warning(f"规则匹配失败（不影响业务）: {e}")
        
        # 4. 提取大运流年数据（从 detail_result 获取，包含完整大运序列）
        dayun_list = []
        try:
            # 从 detail_result 获取大运序列（detail_result 包含完整的大运数据）
            dayun_sequence = detail_result.get('dayun_sequence', [])
            
            # 跳过第0个"小运"，获取索引1、2、3的大运（第2-4步）
            for idx in [1, 2, 3]:
                if idx < len(dayun_sequence):
                    dayun = dayun_sequence[idx]
                    dayun_info = {
                        'step': dayun.get('step', idx),
                        'stem': dayun.get('stem', ''),
                        'branch': dayun.get('branch', ''),
                        'main_star': dayun.get('main_star', ''),
                        'year_start': dayun.get('year_start', 0),
                        'year_end': dayun.get('year_end', 0),
                        'age_display': dayun.get('age_display', '')
                    }
                    dayun_list.append(dayun_info)
        except Exception as e:
            logger.warning(f"提取大运流年数据失败（不影响业务）: {e}")
        
        # 5. 提取神煞数据
        deities_data = {}
        try:
            deities_data = bazi_data.get('deities', {})
        except Exception as e:
            logger.warning(f"提取神煞数据失败（不影响业务）: {e}")
        
        # 6. 提取十神数据
        ten_gods_data = bazi_data.get('ten_gods_stats', {})
        if not ten_gods_data:
            logger.warning("十神数据为空，可能影响分析结果")
        
        # 7. 提取地支刑冲破害数据
        branch_relations = {}
        try:
            relationships = bazi_data.get('relationships', {})
            branch_relations = relationships.get('branch_relations', {})
        except Exception as e:
            logger.warning(f"提取地支刑冲破害数据失败（不影响业务）: {e}")
        
        # 8. 提取日柱数据
        day_pillar = {}
        try:
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            day_pillar = bazi_pillars.get('day', {})
        except Exception as e:
            logger.warning(f"提取日柱数据失败（不影响业务）: {e}")
        
        # 9. 提取喜忌数据
        xi_ji_data = {}
        try:
            if wangshuai_data:
                xi_ji_data = {
                    'xi_shen': wangshuai_data.get('xi_shen', []),
                    'ji_shen': wangshuai_data.get('ji_shen', []),
                    'xi_shen_elements': wangshuai_data.get('xi_shen_elements', []),
                    'ji_shen_elements': wangshuai_data.get('ji_shen_elements', []),
                    'final_xi_ji': wangshuai_data.get('final_xi_ji', {})
                }
        except Exception as e:
            logger.warning(f"提取喜忌数据失败（不影响业务）: {e}")
        
        # 10. 构建完整的输入数据
        input_data = {
            'mingpan_zonglun': {
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                'ten_gods': ten_gods_data,
                'wangshuai': wangshuai_data.get('wangshuai', ''),
                'branch_relations': branch_relations,
                'day_pillar': day_pillar
            },
            'peiou_tezheng': {
                'ten_gods': ten_gods_data,
                'deities': deities_data,
                'marriage_judgments': marriage_judgments,
                'peach_blossom_judgments': peach_blossom_judgments,
                'matchmaking_judgments': matchmaking_judgments,
                'zhengyuan_judgments': zhengyuan_judgments
            },
            'ganqing_zoushi': {
                'dayun_list': dayun_list,
                'ten_gods': ten_gods_data
            },
            'shensha_dianjing': {
                'deities': deities_data
            },
            'jianyi_fangxiang': {
                'ten_gods': ten_gods_data,
                'xi_ji': xi_ji_data,
                'dayun_list': dayun_list
            }
        }
        
        # 11. 验证数据完整性
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            raise ValueError(f"数据完整性验证失败: {validation_error}")
        
        return {
            'success': True,
            'data': input_data,
            'summary': {
                'bazi_pillars': bool(input_data['mingpan_zonglun'].get('bazi_pillars')),
                'ten_gods': bool(input_data['mingpan_zonglun'].get('ten_gods')),
                'wangshuai': bool(input_data['mingpan_zonglun'].get('wangshuai')),
                'branch_relations': bool(input_data['mingpan_zonglun'].get('branch_relations')),
                'day_pillar': bool(input_data['mingpan_zonglun'].get('day_pillar')),
                'deities': bool(input_data['peiou_tezheng'].get('deities')),
                'marriage_judgments': len(input_data['peiou_tezheng'].get('marriage_judgments', [])),
                'dayun_list': len(input_data['ganqing_zoushi'].get('dayun_list', [])),
                'xi_ji': bool(input_data['jianyi_fangxiang'].get('xi_ji'))
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"提取数据失败: {e}\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.post("/bazi/marriage-analysis/debug", summary="调试端点：返回婚姻分析元数据（不调用 Coze）")
async def marriage_analysis_debug(request: MarriageAnalysisRequest):
    """
    调试端点：返回婚姻分析所需的元数据（不调用 Coze API）
    
    用于验证数据提取是否正确，便于调试和验证 Coze Bot prompt 配置。
    
    **参数说明**：
    - **solar_date**: 阳历日期（必填）
    - **solar_time**: 出生时间（必填）
    - **gender**: 性别（必填）
    
    **返回格式**：
    JSON 响应，包含完整的 input_data 和摘要信息
    """
    try:
        result = await extract_marriage_analysis_data(
            request.solar_date,
            request.solar_time,
            request.gender
        )
        return result
    except Exception as e:
        import traceback
        logger.error(f"调试端点异常: {e}\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.post("/bazi/marriage-analysis/stream", summary="流式生成感情婚姻分析")
async def marriage_analysis_stream(request: MarriageAnalysisRequest):
    """
    流式生成感情婚姻分析
    
    使用Coze大模型基于用户生辰数据生成5个部分的分析内容：
    1. 命盘总论（八字排盘、十神、旺衰、地支刑冲破害、日柱）
    2. 配偶特征（十神、神煞、婚姻判词、桃花判词、婚配判词、正缘判词）
    3. 感情走势（大运流年和十神，第2、3、4个大运）
    4. 神煞点睛（神煞）
    5. 建议方向（十神、喜忌、大运流年第2、3、4个）
    
    **参数说明**：
    - **solar_date**: 阳历日期（必填）
    - **solar_time**: 出生时间（必填）
    - **gender**: 性别（必填）
    - **bot_id**: Coze Bot ID（可选，优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID 环境变量）
    
    **返回格式**：
    SSE流式响应，每行格式：`data: {"type": "progress|complete|error", "content": "..."}`
    """
    try:
        return StreamingResponse(
            marriage_analysis_stream_generator(
                request.solar_date,
                request.solar_time,
                request.gender,
                request.calendar_type,
                request.location,
                request.latitude,
                request.longitude,
                request.bot_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        import traceback
        logger.error(f"流式生成异常: {e}\n{traceback.format_exc()}")
        raise


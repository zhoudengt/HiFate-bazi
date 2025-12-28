#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-子女学习API
基于用户生辰数据，使用 Coze Bot 流式生成子女学习分析
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
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.coze_stream_service import CozeStreamService
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
from server.services.special_liunian_service import SpecialLiunianService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class ChildrenStudyRequest(BaziBaseRequest):
    """子女学习分析请求模型（继承 BaziBaseRequest，包含7个标准参数）"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量配置）")


@router.post("/children-study/stream", summary="流式生成子女学习分析")
async def children_study_analysis_stream(request: ChildrenStudyRequest):
    """
    流式生成子女学习分析
    
    Args:
        request: 子女学习分析请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    return StreamingResponse(
        children_study_analysis_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.calendar_type,
            request.location,
            request.latitude,
            request.longitude,
            request.bot_id
        ),
        media_type="text/event-stream"
    )


@router.post("/children-study/debug", summary="调试：查看子女学习分析数据")
async def children_study_analysis_debug(request: ChildrenStudyRequest):
    """
    调试接口：查看提取的数据和构建的 Prompt
    
    Args:
        request: 子女学习分析请求参数
        
    Returns:
        dict: 包含数据和 Prompt 的调试信息
    """
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, "solar", None, None, None
        )
        
        # 使用统一接口获取数据（包括特殊流年）
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True,
            'dayun': {
                'mode': 'count',
                'count': 13  # 获取所有大运
            },
            'special_liunians': {
                'dayun_config': {
                    'mode': 'count',
                    'count': 13  # 获取所有大运
                },
                'count': 200  # 获取足够多的特殊流年
            }
        }
        
        unified_data = await BaziDataOrchestrator.fetch_data(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            modules=modules,
            use_cache=True,
            parallel=True,
            calendar_type=request.calendar_type,
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # 从统一接口结果中提取数据
        bazi_result = unified_data.get('bazi', {})
        wangshuai_result = unified_data.get('wangshuai', {})
        detail_result = unified_data.get('detail', {})
        special_liunians = unified_data.get('special_liunians', {}).get('list', [])
        
        # 提取和验证数据
        if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
            bazi_data = bazi_result['bazi']
        else:
            bazi_data = bazi_result
        bazi_data = validate_bazi_data(bazi_data)
        
        # 获取大运序列（从detail_result，不是bazi_data）
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # 获取五行统计
        element_counts = bazi_data.get('element_counts', {})
        
        # 匹配子女类型规则
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': element_counts,
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 匹配子女类型规则
        loop = asyncio.get_event_loop()
        executor = None
        
        children_rules = await loop.run_in_executor(
            executor,
            RuleService.match_rules,
            rule_data,
            ['children'],
            True
        )
        
        # 构建input_data（传入特殊流年数据）
        input_data = build_children_study_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            request.gender,
            special_liunians=special_liunians
        )
        
        # 添加子女规则
        input_data['children_rules'] = {
            'matched_rules': children_rules,
            'rules_count': len(children_rules),
            'rule_judgments': [
                rule.get('content', {}).get('text', '') 
                for rule in children_rules 
                if isinstance(rule.get('content'), dict) and rule.get('content', {}).get('text')
            ]
        }
        
        # 验证数据完整性
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            return {
                "success": False,
                "error": f"数据完整性验证失败: {validation_error}"
            }
        
        # 构建Prompt
        prompt = build_natural_language_prompt(input_data)
        
        return {
            "success": True,
            "input_data": input_data,
            "prompt": prompt[:500],  # 只返回前500字符
            "prompt_length": len(prompt),
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_zinv_zonglun', {}).get('bazi_pillars', {}),
                "zinv_xing_type": input_data.get('zinvxing_zinvgong', {}).get('zinv_xing_type', ''),
                "dayun_count": len(input_data.get('shengyu_shiji', {}).get('all_dayuns', [])),
                "xi_ji": input_data.get('yangyu_jianyi', {}).get('xi_ji', {})
            }
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def children_study_analysis_stream_generator(
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
    流式生成子女学习分析
    
    Args:
        solar_date: 阳历日期或农历日期
        solar_time: 出生时间
        gender: 性别
        calendar_type: 历法类型（solar/lunar），默认solar
        location: 出生地点（用于时区转换，优先级1）
        latitude: 纬度（用于时区转换，优先级2）
        longitude: 经度（用于时区转换和真太阳时计算，优先级2）
        bot_id: Coze Bot ID（可选）
    """
    try:
        # 1. Bot ID 配置检查
        used_bot_id = bot_id
        if not used_bot_id:
            # 优先使用专用Bot ID
            used_bot_id = os.getenv("CHILDREN_STUDY_BOT_ID")
            if not used_bot_id:
                # 回退到通用Bot ID
                used_bot_id = os.getenv("COZE_BOT_ID")
                if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失，请设置 CHILDREN_STUDY_BOT_ID 或 COZE_BOT_ID 环境变量"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"使用 Bot ID: {used_bot_id}")
        
        # 2. 处理输入（农历转换等，支持7个标准参数）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type or "solar", location, latitude, longitude
        )
        
        # 3. 并行获取基础数据
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
            
            # 提取八字数据
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
            
            logger.info(f"[Children Study Stream] ✅ 统一数据服务数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[Children Study Stream] ❌ 数据获取失败: {error_msg}")
            error_response = {
                'type': 'error',
                'content': f"数据获取失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 4. 提取和验证数据
        
        # 获取五行统计
        element_counts = bazi_data.get('element_counts', {})
        
        # 5. 并行匹配子女类型规则（NEW）
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': element_counts,
            'relationships': bazi_data.get('relationships', {})
        }
        
        loop = asyncio.get_event_loop()
        executor = None
        
        children_rules = await loop.run_in_executor(
            executor,
            RuleService.match_rules,
            rule_data,
            ['children'],  # 匹配子女类型规则
            True
        )
        
        # 6. 构建input_data（传入特殊流年数据）
        input_data = build_children_study_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            gender,
            special_liunians=special_liunians  # ⚠️ 新增：传入特殊流年数据
        )
        
        # 7. 添加子女规则（NEW）
        input_data['children_rules'] = {
            'matched_rules': children_rules,
            'rules_count': len(children_rules),
            'rule_judgments': [
                rule.get('content', {}).get('text', '') 
                for rule in children_rules 
                if isinstance(rule.get('content'), dict) and rule.get('content', {}).get('text')
            ]
        }
        
        # 6. 验证数据完整性（阶段3：数据验证与完整性检查）
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            logger.error(f"数据完整性验证失败: {validation_error}")
            error_msg = {
                'type': 'error',
                'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 7. 构建自然语言Prompt（阶段4：Prompt构建）
        prompt = build_natural_language_prompt(input_data)
        logger.info(f"Prompt长度: {len(prompt)} 字符")
        logger.debug(f"Prompt前500字符: {prompt[:500]}")
        
        # 8. 调用Coze API（阶段5：Coze API调用）
        coze_service = CozeStreamService(bot_id=used_bot_id)
        
        # 9. 流式处理（阶段6：流式处理）
        async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=used_bot_id):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk.get('type') in ['complete', 'error']:
                break
                
    except ValueError as e:
        # 配置错误
        logger.error(f"Coze API 配置错误: {e}")
        error_msg = {
            'type': 'error',
            'content': f"Coze API 配置缺失: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
    except Exception as e:
        # 其他错误
        import traceback
        logger.error(f"子女学习分析失败: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"分析处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


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
    dayun_stem = dayun.get('gan', dayun.get('stem', ''))
    dayun_branch = dayun.get('zhi', dayun.get('branch', ''))
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
    
    # 1. 识别现行运（排除"小运"）
    for dayun in dayun_sequence:
        # 跳过"小运"
        if dayun.get('stem', '') == '小运' or dayun.get('gan', '') == '小运':
            continue
        
        age_display = dayun.get('age_display', dayun.get('age_range', ''))
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
            if dayun.get('stem', '') != '小运' and dayun.get('gan', '') != '小运':
                current_dayun = dayun
                break
    
    # 2. 识别关键节点大运（与原局有特殊生克关系，排除"小运"）
    for dayun in dayun_sequence:
        # 跳过"小运"
        if dayun.get('stem', '') == '小运' or dayun.get('gan', '') == '小运':
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


def build_children_study_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    gender: str,
    special_liunians: List[Dict[str, Any]] = None  # ⚠️ 新增：特殊流年数据
) -> Dict[str, Any]:
    """
    构建子女学习分析的输入数据
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        gender: 性别（male/female）
        
    Returns:
        dict: 子女学习分析的input_data
    """
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    ten_gods_data = detail_result.get('ten_gods', {})
    deities_data = detail_result.get('deities', {})
    
    # 提取日主信息
    day_pillar = bazi_pillars.get('day', {})
    day_stem = day_pillar.get('stem', '')
    day_branch = day_pillar.get('branch', '')
    
    # 提取时柱（子女宫）
    hour_pillar = bazi_pillars.get('hour', {})
    
    # 提取五行分布
    element_counts = bazi_data.get('element_counts', {})
    
    # 提取旺衰数据
    wangshuai = wangshuai_result.get('wangshuai', '')
    
    # 判断子女星类型（关键：男命看官杀，女命看食伤）
    zinv_xing_type = determine_children_star_type(ten_gods_data, gender)
    
    # ⚠️ 新增：识别现行运和关键节点大运
    # 计算当前年龄
    current_age = 0
    birth_date = bazi_data.get('basic_info', {}).get('solar_date', '')
    if birth_date:
        try:
            birth = datetime.strptime(birth_date, '%Y-%m-%d')
            today = datetime.now()
            current_age = today.year - birth.year - (1 if (today.month, today.day) < (birth.month, birth.day) else 0)
        except:
            pass
    
    # 识别关键大运
    key_dayuns_result = identify_key_dayuns(dayun_sequence, element_counts, current_age)
    current_dayun_info = key_dayuns_result.get('current_dayun')
    key_dayuns_list = key_dayuns_result.get('key_dayuns', [])
    
    # ⚠️ 新增：按大运分组特殊流年
    if special_liunians is None:
        special_liunians = []
    
    # 按大运分组特殊流年
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    
    # 构建现行运数据（包含流年）
    current_dayun_data = None
    if current_dayun_info:
        current_step = current_dayun_info.get('step')
        if current_step is None:
            # 如果没有step，尝试从索引推断
            for idx, dayun in enumerate(dayun_sequence):
                if dayun == current_dayun_info:
                    current_step = idx
                    break
        
        # ⚠️ 重要：dayun_liunians 的键是 int 类型，不是 str
        # 提取该大运下的所有流年（按优先级合并）
        dayun_liunian_data = dayun_liunians.get(current_step, {}) if current_step is not None else {}
        all_liunians = []
        # 按优先级顺序合并：天克地冲 > 天合地合 > 岁运并临 > 其他
        if dayun_liunian_data.get('tiankedi_chong'):
            all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
        if dayun_liunian_data.get('tianhedi_he'):
            all_liunians.extend(dayun_liunian_data['tianhedi_he'])
        if dayun_liunian_data.get('suiyun_binglin'):
            all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
        if dayun_liunian_data.get('other'):
            all_liunians.extend(dayun_liunian_data['other'])
        
        current_dayun_data = {
            'step': str(current_step) if current_step is not None else '',
            'stem': current_dayun_info.get('gan', current_dayun_info.get('stem', '')),
            'branch': current_dayun_info.get('zhi', current_dayun_info.get('branch', '')),
            'age_display': current_dayun_info.get('age_display', current_dayun_info.get('age_range', '')),
            'main_star': current_dayun_info.get('main_star', ''),
            'description': current_dayun_info.get('description', ''),
            'liunians': all_liunians  # ⚠️ 修改：使用合并后的所有流年（灵活，不限制数量）
        }
    
    # 构建关键节点大运数据（包含流年）
    key_dayuns_data = []
    for key_dayun in key_dayuns_list:
        step = key_dayun.get('step')
        if step is None:
            # 如果没有step，尝试从索引推断
            for idx, dayun in enumerate(dayun_sequence):
                if dayun == key_dayun:
                    step = idx
                    break
        
        # 提取该大运下的所有流年（按优先级合并）
        dayun_liunian_data = dayun_liunians.get(step, {}) if step is not None else {}
        all_liunians = []
        # 按优先级顺序合并：天克地冲 > 天合地合 > 岁运并临 > 其他
        if dayun_liunian_data.get('tiankedi_chong'):
            all_liunians.extend(dayun_liunian_data['tiankedi_chong'])
        if dayun_liunian_data.get('tianhedi_he'):
            all_liunians.extend(dayun_liunian_data['tianhedi_he'])
        if dayun_liunian_data.get('suiyun_binglin'):
            all_liunians.extend(dayun_liunian_data['suiyun_binglin'])
        if dayun_liunian_data.get('other'):
            all_liunians.extend(dayun_liunian_data['other'])
        
        key_dayuns_data.append({
            'step': str(step) if step is not None else '',
            'stem': key_dayun.get('gan', key_dayun.get('stem', '')),
            'branch': key_dayun.get('zhi', key_dayun.get('branch', '')),
            'age_display': key_dayun.get('age_display', key_dayun.get('age_range', '')),
            'main_star': key_dayun.get('main_star', ''),
            'description': key_dayun.get('description', ''),
            'relation_type': key_dayun.get('relation_type', ''),
            'liunians': all_liunians  # ⚠️ 修改：使用合并后的所有流年（灵活，不限制数量）
        })
    
    # 所有大运列表（用于参考）
    all_dayuns = []
    for idx, dayun in enumerate(dayun_sequence):
        all_dayuns.append({
            'step': str(idx),
            'stem': dayun.get('gan', dayun.get('stem', '')),
            'branch': dayun.get('zhi', dayun.get('branch', '')),
            'age_display': dayun.get('age_display', dayun.get('age_range', '')),
            'main_star': dayun.get('main_star', ''),
            'description': dayun.get('description', '')
        })
    
    # 提取喜忌数据（从旺衰分析）
    xi_ji_data = {
        'xi_shen': wangshuai_result.get('xi_shen', ''),
        'ji_shen': wangshuai_result.get('ji_shen', ''),
        'xi_ji_elements': wangshuai_result.get('xi_ji_elements', {})
    }
    
    # 构建input_data
    input_data = {
        # 1. 命盘子女总论
        'mingpan_zinv_zonglun': {
            'day_master': {
                'stem': day_stem,
                'branch': day_branch,
                'element': day_pillar.get('element', ''),
                'yin_yang': day_pillar.get('yin_yang', '')
            },
            'bazi_pillars': bazi_pillars,
            'elements': element_counts,
            'wangshuai': wangshuai,
            'gender': gender
        },
        
        # 2. 子女星与子女宫
        'zinvxing_zinvgong': {
            'zinv_xing_type': zinv_xing_type,
            'hour_pillar': hour_pillar,
            'ten_gods': ten_gods_data,
            'deities': deities_data
        },
        
        # 3. 生育时机
        'shengyu_shiji': {
            'zinv_xing_type': zinv_xing_type,
            'current_dayun': current_dayun_data,  # ⚠️ 修改：包含流年数据
            'key_dayuns': key_dayuns_data,  # ⚠️ 新增：关键节点大运列表
            'all_dayuns': all_dayuns,  # ⚠️ 新增：所有大运列表（用于参考）
            'ten_gods': ten_gods_data
        },
        
        # 4. 养育建议
        'yangyu_jianyi': {
            'ten_gods': ten_gods_data,
            'wangshuai': wangshuai_result,
            'xi_ji': xi_ji_data
        }
    }
    
    return input_data


def determine_children_star_type(ten_gods_data: Dict[str, Any], gender: str) -> str:
    """
    判断子女星类型
    
    男命：官杀（正官、七杀）为子女星
    女命：食伤（食神、伤官）为子女星
    
    Args:
        ten_gods_data: 十神数据
        gender: 性别（male/female）
        
    Returns:
        str: 子女星类型描述
    """
    if gender == 'male':
        # 男命看官杀
        guan_sha_count = 0
        guan_sha_types = []
        
        for pillar_name, pillar_data in ten_gods_data.items():
            if isinstance(pillar_data, dict):
                main_star = pillar_data.get('main_star', '')
                if main_star in ['正官', '七杀']:
                    guan_sha_count += 1
                    if main_star not in guan_sha_types:
                        guan_sha_types.append(main_star)
                
                hidden_stars = pillar_data.get('hidden_stars', [])
                for star in hidden_stars:
                    if star in ['正官', '七杀']:
                        if star not in guan_sha_types:
                            guan_sha_types.append(star)
        
        if guan_sha_types:
            return f"男命子女星：{'、'.join(guan_sha_types)}（官杀）"
        else:
            return "男命子女星：官杀（待完善）"
    else:
        # 女命看食伤
        shi_shang_count = 0
        shi_shang_types = []
        
        for pillar_name, pillar_data in ten_gods_data.items():
            if isinstance(pillar_data, dict):
                main_star = pillar_data.get('main_star', '')
                if main_star in ['食神', '伤官']:
                    shi_shang_count += 1
                    if main_star not in shi_shang_types:
                        shi_shang_types.append(main_star)
                
                hidden_stars = pillar_data.get('hidden_stars', [])
                for star in hidden_stars:
                    if star in ['食神', '伤官']:
                        if star not in shi_shang_types:
                            shi_shang_types.append(star)
        
        if shi_shang_types:
            return f"女命子女星：{'、'.join(shi_shang_types)}（食伤）"
        else:
            return "女命子女星：食伤（待完善）"


def validate_input_data(data: dict) -> tuple[bool, str]:
    """
    验证子女学习分析输入数据的完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = {
        'mingpan_zinv_zonglun': {
            'day_master': '日主信息',
            'bazi_pillars': '四柱排盘',
            'elements': '五行分布',
            'wangshuai': '旺衰分析',
            'gender': '性别'
        },
        'zinvxing_zinvgong': {
            'zinv_xing_type': '子女星类型',
            'hour_pillar': '时柱',
            'ten_gods': '十神配置',
            'deities': '神煞分布'
        },
        'shengyu_shiji': {
            'zinv_xing_type': '子女星类型',
            'current_dayun': '当前大运',
            'key_dayuns': '关键节点大运列表',
            'all_dayuns': '所有大运列表',
            'ten_gods': '十神配置'
        },
        'yangyu_jianyi': {
            'ten_gods': '十神配置',
            'wangshuai': '旺衰数据',
            'xi_ji': '喜忌数据'
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
                # 空列表/字典可能是正常的，不报错（如无大运数据）
                pass
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""


def build_natural_language_prompt(data: dict) -> str:
    """
    将JSON数据转换为自然语言格式的提示词
    
    Args:
        data: 子女学习分析的完整数据
        
    Returns:
        str: 自然语言格式的提示词
    """
    prompt_lines = []
    prompt_lines.append("请基于以下八字信息进行子女学习分析：")
    prompt_lines.append("")
    
    # 1. 命盘子女总论
    prompt_lines.append("【命盘子女总论】")
    mingpan = data.get('mingpan_zinv_zonglun', {})
    
    # 日主信息
    day_master = mingpan.get('day_master', {})
    if day_master:
        prompt_lines.append(f"日主：{day_master.get('stem', '')} {day_master.get('element', '')} {day_master.get('yin_yang', '')}")
    
    # 四柱排盘
    bazi_pillars = mingpan.get('bazi_pillars', {})
    if bazi_pillars:
        prompt_lines.append("四柱排盘：")
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_name, {})
            if pillar:
                pillar_cn = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_name, pillar_name)
                prompt_lines.append(f"  {pillar_cn}：{pillar.get('stem', '')}{pillar.get('branch', '')}")
    
    # 五行分布
    elements = mingpan.get('elements', {})
    if elements:
        prompt_lines.append("五行分布：" + "、".join([f"{k}{v}个" for k, v in elements.items() if v > 0]))
    
    # 旺衰分析
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        prompt_lines.append(f"旺衰分析：{wangshuai}")
    
    # 性别
    gender = mingpan.get('gender', '')
    gender_cn = '男' if gender == 'male' else '女'
    prompt_lines.append(f"性别：{gender_cn}")
    
    prompt_lines.append("")
    
    # 2. 子女星与子女宫
    prompt_lines.append("【子女星与子女宫】")
    zinvxing = data.get('zinvxing_zinvgong', {})
    
    # 子女星类型
    zinv_xing_type = zinvxing.get('zinv_xing_type', '')
    if zinv_xing_type:
        prompt_lines.append(f"子女星：{zinv_xing_type}")
    
    # 时柱（子女宫）
    hour_pillar = zinvxing.get('hour_pillar', {})
    if hour_pillar:
        prompt_lines.append(f"时柱（子女宫）：{hour_pillar.get('stem', '')}{hour_pillar.get('branch', '')}")
    
    # 十神配置
    ten_gods = zinvxing.get('ten_gods', {})
    if ten_gods:
        prompt_lines.append("十神配置：")
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar_ten_gods = ten_gods.get(pillar_name, {})
            if pillar_ten_gods:
                pillar_cn = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_name, pillar_name)
                main_star = pillar_ten_gods.get('main_star', '')
                hidden_stars = pillar_ten_gods.get('hidden_stars', [])
                stars_str = f"主星{main_star}"
                if hidden_stars:
                    stars_str += f"，副星{'、'.join(hidden_stars)}"
                prompt_lines.append(f"  {pillar_cn}：{stars_str}")
    
    # 神煞分布
    deities = zinvxing.get('deities', {})
    if deities:
        prompt_lines.append("神煞分布：")
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar_deities = deities.get(pillar_name, [])
            if pillar_deities:
                pillar_cn = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_name, pillar_name)
                prompt_lines.append(f"  {pillar_cn}：{'、'.join(pillar_deities)}")
    
    prompt_lines.append("")
    
    # 子女规则参考（NEW）
    children_rules = data.get('children_rules', {})
    matched_rules = children_rules.get('matched_rules', [])
    if matched_rules:
        prompt_lines.append("【子女规则参考】")
        prompt_lines.append(f"匹配到 {len(matched_rules)} 条子女规则：")
        for i, rule in enumerate(matched_rules[:20], 1):  # 最多显示20条
            rule_name = rule.get('rule_name', rule.get('name', f'规则{i}'))
            rule_content = rule.get('content', {})
            if isinstance(rule_content, dict):
                text = rule_content.get('text', '')
                if text:
                    prompt_lines.append(f"  {i}. {rule_name}：{text}")
            elif isinstance(rule_content, str):
                prompt_lines.append(f"  {i}. {rule_name}：{rule_content}")
        prompt_lines.append("")
    
    # 3. 生育时机（按照新格式：现行运和关键节点）
    shengyu = data.get('shengyu_shiji', {})
    
    # 现行运
    current_dayun = shengyu.get('current_dayun')
    if current_dayun:
        step = current_dayun.get('step', '')
        age_display = current_dayun.get('age_display', '')
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        main_star = current_dayun.get('main_star', '')
        liunians = current_dayun.get('liunians', [])
        
        prompt_lines.append(f"**现行{step}运（{age_display}）：**")
        prompt_lines.append(f"- 大运：{stem}{branch}，主星：{main_star}")
        prompt_lines.append(f"- [分析当前大运的五行特征对子女学习的影响]")
        
        # 列举关键流年及健康风险
        if liunians:
            prompt_lines.append(f"- [列举关键流年及学习风险]：")
            for liunian in liunians:
                year = liunian.get('year', '')
                liunian_type = liunian.get('type', '')
                if year:
                    prompt_lines.append(f"  - {year}年（{liunian_type}）：[分析该年的学习风险，如XX年XX势过猛，需格外防范XX]")
        else:
            prompt_lines.append(f"- [列举关键流年及学习风险]：暂无特殊流年")
        
        prompt_lines.append("")
    
    # 关键节点大运
    key_dayuns = shengyu.get('key_dayuns', [])
    if key_dayuns:
        for key_dayun in key_dayuns:
            step = key_dayun.get('step', '')
            age_display = key_dayun.get('age_display', '')
            stem = key_dayun.get('stem', '')
            branch = key_dayun.get('branch', '')
            main_star = key_dayun.get('main_star', '')
            relation_type = key_dayun.get('relation_type', '')
            liunians = key_dayun.get('liunians', [])
            
            prompt_lines.append(f"**关键节点：{step}运（{age_display}）：**")
            prompt_lines.append(f"- 大运：{stem}{branch}，主星：{main_star}")
            prompt_lines.append(f"- [分析该大运的五行特征，是否为调候用神出现]")
            
            if relation_type:
                prompt_lines.append(f"- [分析该运与原局的生克关系，如{relation_type}等]")
            
            prompt_lines.append(f"- 利好：[分析该运对子女学习的积极影响]")
            
            # 挑战：列举关键流年
            if liunians:
                challenge_parts = []
                for liunian in liunians:
                    year = liunian.get('year', '')
                    liunian_type = liunian.get('type', '')
                    if year:
                        challenge_parts.append(f"{year}年（{liunian_type}）")
                
                if challenge_parts:
                    prompt_lines.append(f"- 挑战：[分析该运的学习风险，如{', '.join(challenge_parts)}，XX势过猛冲击XX，需重点防范XX]")
                else:
                    prompt_lines.append(f"- 挑战：[分析该运的学习风险]")
            else:
                prompt_lines.append(f"- 挑战：[分析该运的学习风险]")
            
            prompt_lines.append("")
    
    # 4. 养育建议
    prompt_lines.append("【养育建议】")
    yangyu = data.get('yangyu_jianyi', {})
    
    # 喜忌数据
    xi_ji = yangyu.get('xi_ji', {})
    if xi_ji:
        xi_shen = xi_ji.get('xi_shen', '')
        ji_shen = xi_ji.get('ji_shen', '')
        if xi_shen:
            prompt_lines.append(f"喜神：{xi_shen}")
        if ji_shen:
            prompt_lines.append(f"忌神：{ji_shen}")
        
        xi_ji_elements = xi_ji.get('xi_ji_elements', {})
        if xi_ji_elements:
            xi_elements = xi_ji_elements.get('xi', [])
            ji_elements = xi_ji_elements.get('ji', [])
            if xi_elements:
                prompt_lines.append(f"喜用五行：{'、'.join(xi_elements)}")
            if ji_elements:
                prompt_lines.append(f"忌用五行：{'、'.join(ji_elements)}")
    
    prompt_lines.append("")
    
    return '\n'.join(prompt_lines)


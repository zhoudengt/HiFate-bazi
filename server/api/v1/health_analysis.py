#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-身体健康API
基于用户生辰数据，使用 Coze Bot 流式生成健康分析
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
from server.services.health_analysis_service import HealthAnalysisService
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.coze_stream_service import CozeStreamService
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
from server.services.special_liunian_service import SpecialLiunianService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from server.services.user_interaction_logger import get_user_interaction_logger
import time

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class HealthAnalysisRequest(BaziBaseRequest):
    """身体健康分析请求模型（继承 BaziBaseRequest，包含7个标准参数）"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量配置）")


@router.post("/health/stream", summary="流式生成健康分析")
async def health_analysis_stream(request: HealthAnalysisRequest):
    """
    流式生成健康分析
    
    Args:
        request: 健康分析请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    return StreamingResponse(
        health_analysis_stream_generator(
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


@router.post("/health/debug", summary="调试：查看健康分析数据")
async def health_analysis_debug(request: HealthAnalysisRequest):
    """
    调试接口：查看提取的数据和构建的 Prompt
    
    Args:
        request: 健康分析请求参数
        
    Returns:
        dict: 包含数据和 Prompt 的调试信息
    """
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, "solar", None, None, None
        )
        
        # 并行获取数据
        loop = asyncio.get_event_loop()
        executor = None
        
        bazi_result, wangshuai_result, detail_result = await asyncio.gather(
            loop.run_in_executor(executor, BaziService.calculate_bazi_full, final_solar_date, final_solar_time, request.gender),
            loop.run_in_executor(executor, WangShuaiService.calculate_wangshuai, final_solar_date, final_solar_time, request.gender),
            loop.run_in_executor(executor, BaziDetailService.calculate_detail_full, final_solar_date, final_solar_time, request.gender)
        )
        
        # 提取和验证数据
        if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
            bazi_data = bazi_result['bazi']
        else:
            bazi_data = bazi_result
        bazi_data = validate_bazi_data(bazi_data)
        
        # 获取大运序列（从detail_result）
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # 获取五行统计
        element_counts = bazi_data.get('element_counts', {})
        
        # 构建规则匹配数据
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': element_counts,
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 并行执行健康分析和规则匹配
        health_result, health_rules = await asyncio.gather(
            loop.run_in_executor(executor, HealthAnalysisService.analyze,
                                 bazi_data, element_counts, wangshuai_result,
                                 wangshuai_result.get('xi_ji_elements', {})),
            loop.run_in_executor(executor, RuleService.match_rules, rule_data, ['health'], True)
        )
        
        # 构建input_data
        input_data = build_health_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            health_result if health_result.get('success') else {},
            request.gender
        )
        
        # 添加健康规则
        input_data['health_rules'] = {
            'matched_rules': health_rules,
            'rules_count': len(health_rules),
            'rule_judgments': [rule.get('content', {}).get('text', '') for rule in health_rules if isinstance(rule.get('content'), dict)]
        }
        
        # 验证数据完整性
        is_valid, validation_error = validate_health_input_data(input_data)
        if not is_valid:
            return {
                "success": False,
                "error": f"数据完整性验证失败: {validation_error}"
            }
        
        # 构建Prompt
        prompt = build_health_prompt(input_data)
        
        return {
            "success": True,
            "input_data": input_data,
            "prompt": prompt[:500],  # 只返回前500字符
            "prompt_length": len(prompt),
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_tizhi_zonglun', {}).get('bazi_pillars', {}),
                "health_rules_count": len(input_data.get('health_rules', {}).get('matched_rules', [])),
                "dayun_count": len(input_data.get('dayun_jiankang', {}).get('dayun_list', [])),
                "wuxing_balance": input_data.get('mingpan_tizhi_zonglun', {}).get('wuxing_balance', '')
            }
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def health_analysis_stream_generator(
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
    流式生成健康分析
    
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
    # 记录开始时间和前端输入
    api_start_time = time.time()
    frontend_input = {
        'solar_date': solar_date,
        'solar_time': solar_time,
        'gender': gender,
        'calendar_type': calendar_type,
        'location': location,
        'latitude': latitude,
        'longitude': longitude
    }
    llm_first_token_time = None
    llm_output_chunks = []
    
    try:
        # 1. Bot ID 配置检查
        used_bot_id = bot_id
        if not used_bot_id:
            # 优先使用专用Bot ID
            used_bot_id = os.getenv("HEALTH_ANALYSIS_BOT_ID")
            if not used_bot_id:
                # 回退到通用Bot ID
                used_bot_id = os.getenv("COZE_BOT_ID")
                if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失，请设置 HEALTH_ANALYSIS_BOT_ID 或 COZE_BOT_ID 环境变量"
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
        
        # ⚠️ 初始化 detail_result，确保在所有代码路径中都有定义
        detail_result = None
        
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
            detail_task = loop.run_in_executor(
                executor,
                lambda: BaziDetailService.calculate_detail_full(
                    final_solar_date,
                    final_solar_time,
                    gender
                )
            )
            
            bazi_result, wangshuai_result, detail_result = await asyncio.gather(bazi_task, wangshuai_task, detail_task)
            
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
            
            logger.info(f"[Health Analysis Stream] ✅ 统一数据服务数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[Health Analysis Stream] ❌ 数据获取失败: {e}\n{error_msg}")
            error_response = {
                'type': 'error',
                'content': f"数据获取失败: {str(e)}。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 4. 提取和验证数据
        
        logger.info(f"[Health Analysis Stream] 获取到特殊流年数量: {len(special_liunians)}")
        
        # ⚠️ 防御性检查：确保 detail_result 不为 None
        # detail_result 包含 ten_gods 和 deities 数据，这些数据由 BaziDetailService.calculate_detail_full() 提供
        # 与 BaziDataService.get_fortune_data() 不同，detail_result 提供的是十神和神煞信息
        if detail_result is None:
            logger.error("[Health Analysis Stream] ❌ detail_result 为 None，无法继续分析")
            error_response = {
                'type': 'error',
                'content': "详细数据获取失败，无法继续分析。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 获取五行统计
        element_counts = bazi_data.get('element_counts', {})
        
        # 5. 构建规则匹配数据（用于健康规则匹配）
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': element_counts,
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 6. 并行执行健康分析和规则匹配
        loop = asyncio.get_event_loop()
        executor = None
        health_result, health_rules = await asyncio.gather(
            loop.run_in_executor(executor, HealthAnalysisService.analyze,
                                 bazi_data, element_counts, wangshuai_result, 
                                 wangshuai_result.get('xi_ji_elements', {})),
            loop.run_in_executor(executor, RuleService.match_rules, rule_data, ['health'], True)
        )
        
        # 7. 构建input_data（传递特殊流年数据）
        input_data = build_health_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            health_result if health_result.get('success') else {},
            gender,
            special_liunians=special_liunians  # ⚠️ 新增：传递特殊流年数据
        )
        
        # 8. 添加健康规则（NEW）
        input_data['health_rules'] = {
            'matched_rules': health_rules,
            'rules_count': len(health_rules),
            'rule_judgments': [
                rule.get('content', {}).get('text', '') 
                for rule in health_rules 
                if isinstance(rule.get('content'), dict) and rule.get('content', {}).get('text')
            ]
        }
        
        # 9. 验证数据完整性（阶段3：数据验证与完整性检查）
        is_valid, validation_error = validate_health_input_data(input_data)
        if not is_valid:
            logger.error(f"数据完整性验证失败: {validation_error}")
            error_msg = {
                'type': 'error',
                'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 10. 构建自然语言Prompt（阶段4：Prompt构建）
        prompt = build_health_prompt(input_data)
        logger.info(f"Prompt长度: {len(prompt)} 字符")
        logger.debug(f"Prompt前500字符: {prompt[:500]}")
        
        # 11. 调用Coze API（阶段5：Coze API调用）
        coze_service = CozeStreamService(bot_id=used_bot_id)
        
        # 12. 流式处理（阶段6：流式处理）
        llm_start_time = time.time()
        has_content = False
        
        async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=used_bot_id):
            # 记录第一个token时间
            if llm_first_token_time is None and chunk.get('type') == 'progress':
                llm_first_token_time = time.time()
            
            # 收集输出内容
            if chunk.get('type') == 'progress':
                llm_output_chunks.append(chunk.get('content', ''))
                has_content = True
            elif chunk.get('type') == 'complete':
                llm_output_chunks.append(chunk.get('content', ''))
                has_content = True
            
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk.get('type') in ['complete', 'error']:
                break
        
        # 记录交互数据（异步，不阻塞）
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
        llm_output = ''.join(llm_output_chunks)
        
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='health',
            function_name='八字命理-身体健康分析',
            frontend_api='/api/v1/bazi/health/stream',
            frontend_input=frontend_input,
            input_data=input_data if 'input_data' in locals() else {},
            llm_output=llm_output,
            llm_api='coze_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
            llm_total_time_ms=llm_total_time_ms,
            round_number=1,
            bot_id=used_bot_id,
            status='success' if has_content else 'failed',
            streaming=True
        )
                
    except ValueError as e:
        # 配置错误
        logger.error(f"Coze API 配置错误: {e}")
        error_msg = {
            'type': 'error',
            'content': f"Coze API 配置缺失: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='health',
            function_name='八字命理-身体健康分析',
            frontend_api='/api/v1/bazi/health/stream',
            frontend_input=frontend_input,
            input_data={},
            llm_output='',
            llm_api='coze_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=None,
            llm_total_time_ms=None,
            round_number=1,
            status='failed',
            error_message=str(e),
            streaming=True
        )
    except Exception as e:
        # 其他错误
        import traceback
        logger.error(f"健康分析失败: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"分析处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='health',
            function_name='八字命理-身体健康分析',
            frontend_api='/api/v1/bazi/health/stream',
            frontend_input=frontend_input,
            input_data={},
            llm_output='',
            llm_api='coze_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=None,
            llm_total_time_ms=None,
            round_number=1,
            status='failed',
            error_message=str(e),
            streaming=True
        )


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
    
    # 1. 识别现行运
    for dayun in dayun_sequence:
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
    
    if not current_dayun and dayun_sequence:
        current_dayun = dayun_sequence[0]
    
    # 2. 识别关键节点大运（与原局有特殊生克关系）
    for dayun in dayun_sequence:
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


def build_health_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    health_result: Dict[str, Any],
    gender: str,
    special_liunians: List[Dict[str, Any]] = None  # ⚠️ 新增：特殊流年数据
) -> Dict[str, Any]:
    """
    构建健康分析的输入数据
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        health_result: 健康分析结果
        gender: 性别（male/female）
        
    Returns:
        dict: 健康分析的input_data
    """
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    element_counts = bazi_data.get('element_counts', {})
    ten_gods_data = detail_result.get('ten_gods', {})
    
    # 提取日主信息
    day_pillar = bazi_pillars.get('day', {})
    day_stem = day_pillar.get('stem', '')
    day_branch = day_pillar.get('branch', '')
    
    # 提取旺衰数据
    wangshuai = wangshuai_result.get('wangshuai', '')
    
    # 提取月令
    month_pillar = bazi_pillars.get('month', {})
    month_branch = month_pillar.get('branch', '')
    yue_ling = f"{month_branch}月" if month_branch else ''
    
    # 提取喜忌数据
    xi_ji_data = {
        'xi_shen': wangshuai_result.get('xi_shen', ''),
        'ji_shen': wangshuai_result.get('ji_shen', ''),
        'xi_ji_elements': wangshuai_result.get('xi_ji_elements', {})
    }
    
    # 获取健康分析结果
    body_algorithm = health_result.get('body_algorithm', {})
    pathology_tendency = health_result.get('pathology_tendency', {})
    wuxing_tuning = health_result.get('wuxing_tuning', {})
    zangfu_care = health_result.get('zangfu_care', {})
    wuxing_balance = health_result.get('wuxing_balance', '')
    
    # ⚠️ 新增：识别现行运和关键节点大运
    # 计算当前年龄
    from datetime import datetime
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
    
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    
    # 构建现行运数据（包含流年）
    current_dayun_data = None
    if current_dayun_info:
        current_step = current_dayun_info.get('step')
        current_dayun_liunians = dayun_liunians.get(current_step, {})
        current_dayun_data = {
            'step': current_dayun_info.get('step'),
            'stem': current_dayun_info.get('stem', ''),
            'branch': current_dayun_info.get('branch', ''),
            'age_display': current_dayun_info.get('age_display', ''),
            'year_start': current_dayun_info.get('year_start', 0),
            'year_end': current_dayun_info.get('year_end', 0),
            'liunians': {
                'tiankedi_chong': current_dayun_liunians.get('tiankedi_chong', []),
                'tianhedi_he': current_dayun_liunians.get('tianhedi_he', []),
                'suiyun_binglin': current_dayun_liunians.get('suiyun_binglin', []),
                'other': current_dayun_liunians.get('other', [])
            }
        }
    
    # 构建关键节点大运数据（包含流年）
    key_dayuns_data = []
    for key_dayun in key_dayuns_list:
        key_step = key_dayun.get('step')
        key_dayun_liunians = dayun_liunians.get(key_step, {})
        key_dayuns_data.append({
            'step': key_dayun.get('step'),
            'stem': key_dayun.get('stem', ''),
            'branch': key_dayun.get('branch', ''),
            'age_display': key_dayun.get('age_display', ''),
            'year_start': key_dayun.get('year_start', 0),
            'year_end': key_dayun.get('year_end', 0),
            'relation_type': key_dayun.get('relation_type', ''),
            'liunians': {
                'tiankedi_chong': key_dayun_liunians.get('tiankedi_chong', []),
                'tianhedi_he': key_dayun_liunians.get('tianhedi_he', []),
                'suiyun_binglin': key_dayun_liunians.get('suiyun_binglin', []),
                'other': key_dayun_liunians.get('other', [])
            }
        })
    
    # 保留所有大运列表（用于参考）
    all_dayuns = []
    for dayun in dayun_sequence:
        all_dayuns.append({
            'step': dayun.get('step'),
            'stem': dayun.get('stem', ''),
            'branch': dayun.get('branch', ''),
            'age_display': dayun.get('age_display', ''),
            'year_start': dayun.get('year_start', 0),
            'year_end': dayun.get('year_end', 0)
        })
    
    # 五行生克关系（从health_result或计算）
    wuxing_shengke = pathology_tendency.get('wuxing_relations', {})
    
    # 构建input_data
    input_data = {
        # 1. 命盘体质总论
        'mingpan_tizhi_zonglun': {
            'day_master': {
                'stem': day_stem,
                'branch': day_branch,
                'element': day_pillar.get('element', ''),
                'yin_yang': day_pillar.get('yin_yang', '')
            },
            'bazi_pillars': bazi_pillars,
            'elements': element_counts,
            'wangshuai': wangshuai,
            'yue_ling': yue_ling,
            'wuxing_balance': wuxing_balance
        },
        
        # 2. 五行病理推演
        'wuxing_bingli': {
            'wuxing_shengke': wuxing_shengke,
            'body_algorithm': body_algorithm,
            'pathology_tendency': pathology_tendency
        },
        
        # 3. 大运流年健康警示
        'dayun_jiankang': {
            'current_dayun': current_dayun_data,  # ⚠️ 修改：包含流年数据
            'key_dayuns': key_dayuns_data,  # ⚠️ 新增：关键节点大运列表
            'all_dayuns': all_dayuns,  # ⚠️ 新增：所有大运列表（用于参考）
            'ten_gods': ten_gods_data
        },
        
        # 4. 体质调理建议
        'tizhi_tiaoli': {
            'xi_ji': xi_ji_data,
            'wuxing_tiaohe': wuxing_tuning,
            'zangfu_yanghu': zangfu_care
        }
    }
    
    return input_data


def validate_health_input_data(data: dict) -> tuple[bool, str]:
    """
    验证健康分析输入数据的完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = {
        'mingpan_tizhi_zonglun': {
            'day_master': '日主信息',
            'bazi_pillars': '四柱排盘',
            'elements': '五行分布',
            'wangshuai': '旺衰分析',
            'wuxing_balance': '五行平衡情况'
        },
        'wuxing_bingli': {
            'body_algorithm': '五行五脏对应',
            'pathology_tendency': '病理倾向'
        },
        'dayun_jiankang': {
            'current_dayun': '当前大运',
            'key_dayuns': '关键节点大运列表',
            'all_dayuns': '所有大运列表'
        },
        'tizhi_tiaoli': {
            'xi_ji': '喜忌数据',
            'wuxing_tiaohe': '五行调和方案',
            'zangfu_yanghu': '脏腑养护建议'
        },
        'health_rules': {
            'matched_rules': '健康规则列表'
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
                # 空列表/字典可能是正常的（如无匹配规则），不报错
                pass
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""


def build_health_prompt(data: dict) -> str:
    """
    将JSON数据转换为自然语言格式的提示词
    
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
                for liunian in high_risk_liunians[:3]:  # 最多列出3个
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


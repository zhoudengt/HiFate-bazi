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

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.special_liunian_service import SpecialLiunianService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from server.services.stream_call_logger import get_stream_call_logger
import time
from server.utils.dayun_liunian_helper import (
    calculate_user_age,
    get_current_dayun,
    build_enhanced_dayun_structure
)
from server.config.input_format_loader import build_input_data_from_result
from server.utils.prompt_builders import (
    format_children_study_input_data_for_coze as format_input_data_for_coze,
    format_children_study_for_llm
)
from server.utils.analysis_helpers import (
    _calculate_ganzhi_elements, analyze_dayun_bazi_relation, identify_key_dayuns,
)

# ✅ 性能优化：导入流式缓存工具
from server.utils.stream_cache_helper import (
    get_llm_cache, set_llm_cache,
    compute_input_data_hash, LLM_CACHE_TTL
)

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


@router.post("/children-study/test", summary="测试：查看格式化后的数据（方案2）")
async def children_study_analysis_test(request: ChildrenStudyRequest):
    """
    测试接口：查看格式化后的数据（用于方案2测试）
    
    返回格式化后的 JSON 数据，可以直接用于 Coze Bot 的 {{input}} 占位符
    
    Args:
        request: 子女学习分析请求参数
        
    Returns:
        dict: 包含格式化后的数据
    """
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, "solar", None, None, None
        )
        
        # 使用统一接口获取基础数据（与流式接口保持一致）
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True
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
            longitude=request.longitude,
            preprocessed=True
        )
        
        # 从统一接口结果中提取数据
        bazi_result = unified_data.get('bazi', {})
        wangshuai_result = unified_data.get('wangshuai', {})
        detail_result = unified_data.get('detail', {})
        
        # 提取和验证数据
        if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
            bazi_data = bazi_result['bazi']
        else:
            bazi_data = bazi_result
        bazi_data = validate_bazi_data(bazi_data)
        
        # ✅ 使用统一数据服务获取大运流年、特殊流年数据（与流式接口保持一致）
        from server.orchestrators.bazi_data_service import BaziDataService
        
        fortune_data = await BaziDataService.get_fortune_data(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            include_dayun=True,
            include_liunian=True,
            include_special_liunian=True,
            dayun_mode=BaziDataService.DEFAULT_DAYUN_MODE,
            target_years=BaziDataService.DEFAULT_TARGET_YEARS,
            current_time=None
        )
        
        # 转换为字典格式（与流式接口保持一致）
        dayun_sequence = []
        special_liunians = []
        
        for dayun in fortune_data.dayun_sequence:
            dayun_sequence.append({
                'step': dayun.step, 'stem': dayun.stem, 'branch': dayun.branch,
                'year_start': dayun.year_start, 'year_end': dayun.year_end,
                'age_range': dayun.age_range, 'age_display': dayun.age_display,
                'nayin': dayun.nayin, 'main_star': dayun.main_star,
                'hidden_stems': dayun.hidden_stems or [], 'hidden_stars': dayun.hidden_stars or [],
                'star_fortune': dayun.star_fortune, 'self_sitting': dayun.self_sitting,
                'kongwang': dayun.kongwang, 'deities': dayun.deities or [],
                'details': dayun.details or {}
            })
        
        for sl in fortune_data.special_liunians:
            special_liunians.append({
                'year': sl.year, 'stem': sl.stem, 'branch': sl.branch, 'ganzhi': sl.ganzhi,
                'age': sl.age, 'age_display': sl.age_display, 'nayin': sl.nayin,
                'main_star': sl.main_star, 'hidden_stems': sl.hidden_stems or [],
                'hidden_stars': sl.hidden_stars or [], 'star_fortune': sl.star_fortune,
                'self_sitting': sl.self_sitting, 'kongwang': sl.kongwang,
                'deities': sl.deities or [], 'relations': sl.relations or [],
                'dayun_step': sl.dayun_step, 'dayun_ganzhi': sl.dayun_ganzhi,
                'details': sl.details or {}
            })
        
        logger.info(f"[Children Study Test] ✅ 统一数据服务获取完成 - dayun: {len(dayun_sequence)}, special: {len(special_liunians)}")
        
        # 匹配子女类型规则
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
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
        
        # 构建input_data（优先使用数据库格式定义）
        use_hardcoded = False
        try:
            input_data = build_input_data_from_result(
                format_name='children_study_analysis',
                bazi_data=bazi_data,
                detail_result=detail_result,
                wangshuai_result=wangshuai_result,
                rule_result={'matched_rules': children_rules},
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians,
                gender=request.gender
            )
            # ✅ 检查格式定义构建的数据是否完整
            required_sections = ['mingpan_zinv_zonglun', 'zinvxing_zinvgong', 'shengyu_shiji', 'yangyu_jianyi']
            missing_sections = [s for s in required_sections if s not in input_data or not input_data[s]]
            if missing_sections:
                logger.warning(f"⚠️ 格式定义构建的数据不完整（缺少: {missing_sections}），降级到硬编码函数")
                use_hardcoded = True
            else:
                logger.info("✅ 使用数据库格式定义构建 input_data: children_study_analysis")
        except Exception as e:
            # 降级到硬编码函数
            logger.warning(f"⚠️ 格式定义构建失败，使用硬编码函数: {e}")
            use_hardcoded = True
        
        if use_hardcoded:
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
        
        # ⚠️ 方案2：格式化数据为 Coze Bot 输入格式
        formatted_data = format_input_data_for_coze(input_data)
        
        return {
            "success": True,
            "formatted_data": formatted_data,  # 格式化后的 JSON 数据（用于 Coze Bot 的 {{input}} 占位符）
            "formatted_data_length": len(formatted_data),  # 数据长度
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_zinv_zonglun', {}).get('bazi_pillars', {}),
                "zinv_xing_type": input_data.get('zinvxing_zinvgong', {}).get('zinv_xing_type', ''),
                "dayun_count": len(input_data.get('shengyu_shiji', {}).get('all_dayuns', [])),
                "current_dayun_liunians_count": len(input_data.get('shengyu_shiji', {}).get('current_dayun', {}).get('liunians', [])),
                "key_dayuns_count": len(input_data.get('shengyu_shiji', {}).get('key_dayuns', [])),
                "xi_ji": input_data.get('yangyu_jianyi', {}).get('xi_ji', {})
            },
            "usage": {
                "description": "此接口返回的数据可以直接用于 Coze Bot 的 {{input}} 占位符",
                "coze_bot_setup": "1. 登录 Coze 平台\n2. 找到'子女学习分析' Bot\n3. 进入 Bot 设置 → System Prompt\n4. 配置提示词并保存",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/children-study/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}", "calendar_type": "{request.calendar_type or "solar"}"}}\''
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"测试接口异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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
            longitude=request.longitude,
            preprocessed=True
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
        
        # 构建input_data（优先使用数据库格式定义）
        use_hardcoded = False
        try:
            input_data = build_input_data_from_result(
                format_name='children_study_analysis',
                bazi_data=bazi_data,
                detail_result=detail_result,
                wangshuai_result=wangshuai_result,
                rule_result={'matched_rules': children_rules},
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians,
                gender=request.gender
            )
            # ✅ 检查格式定义构建的数据是否完整
            required_sections = ['mingpan_zinv_zonglun', 'zinvxing_zinvgong', 'shengyu_shiji', 'yangyu_jianyi']
            missing_sections = [s for s in required_sections if s not in input_data or not input_data[s]]
            if missing_sections:
                logger.warning(f"⚠️ 格式定义构建的数据不完整（缺少: {missing_sections}），降级到硬编码函数")
                use_hardcoded = True
            else:
                logger.info("✅ 使用数据库格式定义构建 input_data: children_study_analysis")
        except Exception as e:
            # 降级到硬编码函数
            logger.warning(f"⚠️ 格式定义构建失败，使用硬编码函数: {e}")
            use_hardcoded = True
        
        if use_hardcoded:
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
        
        # ✅ 只返回 input_data，评测脚本使用相同的函数构建 formatted_data
        return {
            "success": True,
            "input_data": input_data,
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
        # ✅ 性能优化：立即返回首条消息，让用户感知到连接已建立
        # 这个优化将首次响应时间从 24秒 降低到 <1秒
        # ✅ 架构优化：移除无意义的进度消息，直接开始数据处理
        # 详见：standards/08_数据编排架构规范.md
        
        # 1. Bot ID 配置检查（优先级：参数 > 数据库配置 > 环境变量）
        used_bot_id = bot_id
        if not used_bot_id:
            # 优先级：数据库配置 > 环境变量
            used_bot_id = get_config_from_db_only("CHILDREN_STUDY_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失，请设置数据库配置 CHILDREN_STUDY_BOT_ID 或 COZE_BOT_ID，或环境变量"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"使用 Bot ID: {used_bot_id}")
        
        # 2. 处理输入（农历转换等，支持7个标准参数）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type or "solar", location, latitude, longitude
        )
        
        # 3. 通过 BaziDataOrchestrator 统一获取数据（主路径统一）
        try:
            from server.utils.analysis_stream_helpers import get_modules_config
            from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
            
            modules = get_modules_config('children')
            unified_data = await BaziDataOrchestrator.fetch_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                modules=modules,
                use_cache=True,
                parallel=True,
                calendar_type=calendar_type or "solar",
                location=location,
                latitude=latitude,
                longitude=longitude,
                preprocessed=True
            )
            
            # 提取八字数据
            bazi_module_data = unified_data.get('bazi', {})
            if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
                bazi_data = bazi_module_data.get('bazi', {})
            else:
                bazi_data = bazi_module_data
            bazi_data = validate_bazi_data(bazi_data)
            if not bazi_data:
                raise ValueError("八字计算失败，返回数据为空")
            
            wangshuai_result = unified_data.get('wangshuai', {})
            detail_result = unified_data.get('detail', {}) or {}
            dayun_sequence = detail_result.get('dayun_sequence', [])
            special_liunians_data = unified_data.get('special_liunians', {})
            special_liunians = special_liunians_data.get('list', []) if isinstance(special_liunians_data, dict) else []
            children_rules = unified_data.get('rules', [])
            
            logger.info(f"[Children Study Stream] ✅ BaziDataOrchestrator 数据获取完成")
            
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
        
        # ⚠️ 防御性检查：确保 detail_result 不为 None
        # detail_result 包含 ten_gods 和 deities 数据，这些数据由 BaziDetailService.calculate_detail_full() 提供
        # 与 BaziDataService.get_fortune_data() 不同，detail_result 提供的是十神和神煞信息
        if detail_result is None:
            logger.error("[Children Study Stream] ❌ detail_result 为 None，无法继续分析")
            error_response = {
                'type': 'error',
                'content': "详细数据获取失败，无法继续分析。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # ✅ 性能优化：规则已在前面并行获取（children_rules）
        
        # 5. 构建input_data（优先使用数据库格式定义）
        use_hardcoded = False
        try:
            input_data = build_input_data_from_result(
                format_name='children_study_analysis',
                bazi_data=bazi_data,
                detail_result=detail_result,
                wangshuai_result=wangshuai_result,
                rule_result={'matched_rules': children_rules},
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians,
                gender=gender
            )
            # ✅ 检查格式定义构建的数据是否完整
            required_sections = ['mingpan_zinv_zonglun', 'zinvxing_zinvgong', 'shengyu_shiji', 'yangyu_jianyi']
            missing_sections = [s for s in required_sections if s not in input_data or not input_data[s]]
            if missing_sections:
                logger.warning(f"⚠️ 格式定义构建的数据不完整（缺少: {missing_sections}），降级到硬编码函数")
                use_hardcoded = True
            else:
                logger.info("✅ 使用数据库格式定义构建 input_data: children_study_analysis")
        except Exception as e:
            # 降级到硬编码函数
            logger.warning(f"⚠️ 格式定义构建失败，使用硬编码函数: {e}")
            use_hardcoded = True
        
        if use_hardcoded:
            input_data = build_children_study_input_data(
                bazi_data,
                wangshuai_result,
                detail_result,
                dayun_sequence,
                gender,
                special_liunians=special_liunians
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
        
        # 8. 验证数据完整性（阶段3：数据验证与完整性检查）
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            logger.error(f"数据完整性验证失败: {validation_error}")
            error_msg = {
                'type': 'error',
                'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 9. ⚠️ 优化：使用精简中文文本格式（Token 减少 85%）
        formatted_data = format_children_study_for_llm(input_data)
        logger.info(f"格式化数据长度: {len(formatted_data)} 字符（优化后）")
        logger.debug(f"格式化数据:\n{formatted_data}")
        
        # ✅ 性能优化：检查 LLM 缓存
        input_data_hash = compute_input_data_hash(input_data)
        cached_llm_content = get_llm_cache("children_study", input_data_hash)
        
        if cached_llm_content:
            logger.info(f"✅ LLM 缓存命中: children_study")
            # 发送缓存的内容（模拟流式响应）
            complete_msg = {
                'type': 'complete',
                'content': cached_llm_content
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            total_duration = time.time() - api_start_time
            logger.info(f"✅ 从缓存返回完成: 耗时={total_duration:.2f}s")
            
            # 记录缓存命中日志
            try:
                stream_logger = get_stream_call_logger()
                stream_logger.log_async(
                    function_type='children',
                    frontend_api='/api/v1/bazi/children-study/stream',
                    frontend_input=frontend_input,
                    input_data=formatted_data if 'formatted_data' in locals() and formatted_data else '',
                    llm_output=cached_llm_content,
                    api_total_ms=int(total_duration * 1000),
                    bot_id=used_bot_id,
                    llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
                    status='cache_hit',
                    cache_hit=True,
                )
            except Exception as log_err:
                logger.warning(f"缓存命中日志记录失败: {log_err}")
            return
        
        logger.info(f"❌ LLM 缓存未命中: children_study")
        
        # 10. 调用 LLM API（阶段5：LLM API调用，支持 Coze 和百炼平台）
        # ⚠️ 方案2：直接发送格式化后的数据，Bot 会自动使用 System Prompt 中的模板
        from server.services.llm_service_factory import LLMServiceFactory
        from server.services.bailian_stream_service import BailianStreamService
        llm_service = LLMServiceFactory.get_service(scene="children_study", bot_id=used_bot_id)

        # 11. 流式处理（阶段6：流式处理）
        llm_start_time = time.time()
        has_content = False
        complete_content = ""
        
        async for chunk in llm_service.stream_analysis(formatted_data, bot_id=used_bot_id):
            # 记录第一个token时间
            if llm_first_token_time is None and chunk.get('type') == 'progress':
                llm_first_token_time = time.time()
            
            # 收集输出内容
            if chunk.get('type') == 'progress':
                llm_output_chunks.append(chunk.get('content', ''))
                has_content = True
            elif chunk.get('type') == 'complete':
                complete_content = chunk.get('content', '')
                llm_output_chunks.append(complete_content)
                has_content = True
                
                # ✅ 性能优化：缓存 LLM 生成结果
                if complete_content:
                    set_llm_cache("children_study", input_data_hash, complete_content, LLM_CACHE_TTL)
                    logger.info(f"✅ LLM 缓存已写入: children_study")
            
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk.get('type') in ['complete', 'error']:
                break
        
        # 记录交互数据（异步，不阻塞）
        api_end_time = time.time()
        api_total_ms = int((api_end_time - api_start_time) * 1000)
        llm_total_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
        llm_output = ''.join(llm_output_chunks)
        
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='children',
            frontend_api='/api/v1/bazi/children-study/stream',
            frontend_input=frontend_input,
            input_data=formatted_data if 'formatted_data' in locals() and formatted_data else '',
            llm_output=llm_output,
            llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
            api_total_ms=api_total_ms,
            llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
            llm_total_ms=llm_total_ms,
            bot_id=used_bot_id,
            status='success' if has_content else 'failed'
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
        api_total_ms = int((api_end_time - api_start_time) * 1000)
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='children',
            frontend_api='/api/v1/bazi/children-study/stream',
            frontend_input=frontend_input,
            input_data='',
            llm_output='',
            llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
            api_total_ms=api_total_ms,
            llm_first_token_ms=None,
            llm_total_ms=None,
            bot_id=used_bot_id,
            status='failed',
            error_message=str(e)
        )
    except Exception as e:
        # 其他错误
        import traceback
        logger.error(f"子女学习分析失败: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"分析处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        api_total_ms = int((api_end_time - api_start_time) * 1000)
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='children',
            frontend_api='/api/v1/bazi/children-study/stream',
            frontend_input=frontend_input,
            input_data='',
            llm_output='',
            llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
            api_total_ms=api_total_ms,
            llm_first_token_ms=None,
            llm_total_ms=None,
            bot_id=used_bot_id,
            status='failed',
            error_message=str(e)
        )




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
    # ⚠️ 数据提取辅助函数：从 wangshuai_result 中提取旺衰数据
    def extract_wangshuai_data(wangshuai_result: Dict[str, Any]) -> Dict[str, Any]:
        """从 wangshuai_result 中提取旺衰数据"""
        # wangshuai_result 可能是 {'success': True, 'data': {...}} 格式
        if isinstance(wangshuai_result, dict):
            if wangshuai_result.get('success') and 'data' in wangshuai_result:
                return wangshuai_result.get('data', {})
            # 如果直接是数据字典，直接返回
            if 'wangshuai' in wangshuai_result or 'xi_shen' in wangshuai_result:
                return wangshuai_result
        return {}
    
    # ⚠️ 数据提取辅助函数：从 detail_result 或 bazi_data 中提取十神数据
    def extract_ten_gods_data(detail_result: Dict[str, Any], bazi_data: Dict[str, Any]) -> Dict[str, Any]:
        """从 detail_result 或 bazi_data 中提取十神数据"""
        # 1. 先尝试从 detail_result 的顶层获取
        ten_gods = detail_result.get('ten_gods', {})
        if ten_gods and isinstance(ten_gods, dict) and len(ten_gods) > 0:
            return ten_gods
        
        # 2. 尝试从 detail_result 的 details 字段中提取
        details = detail_result.get('details', {})
        if details and isinstance(details, dict):
            ten_gods_from_details = {}
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_detail = details.get(pillar_name, {})
                if isinstance(pillar_detail, dict):
                    ten_gods_from_details[pillar_name] = {
                        'main_star': pillar_detail.get('main_star', ''),
                        'hidden_stars': pillar_detail.get('hidden_stars', [])
                    }
            if any(ten_gods_from_details.values()):
                return ten_gods_from_details
        
        # 3. 尝试从 bazi_data 的 details 字段中提取
        bazi_details = bazi_data.get('details', {})
        if bazi_details and isinstance(bazi_details, dict):
            ten_gods_from_bazi = {}
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_detail = bazi_details.get(pillar_name, {})
                if isinstance(pillar_detail, dict):
                    ten_gods_from_bazi[pillar_name] = {
                        'main_star': pillar_detail.get('main_star', ''),
                        'hidden_stars': pillar_detail.get('hidden_stars', [])
                    }
            if any(ten_gods_from_bazi.values()):
                return ten_gods_from_bazi
        
        # 4. 如果都没有，返回空字典
        return {}
    
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    
    # ⚠️ 修复：从 wangshuai_result 中正确提取旺衰数据
    wangshuai_data = extract_wangshuai_data(wangshuai_result)
    
    # ⚠️ 修复：从 detail_result 或 bazi_data 中提取十神数据
    ten_gods_data = extract_ten_gods_data(detail_result, bazi_data)
    
    # 从 bazi_data.details 中提取神煞数据（与婚姻、事业分析一致）
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
    
    # 提取日主信息
    day_pillar = bazi_pillars.get('day', {})
    day_stem = day_pillar.get('stem', '')
    day_branch = day_pillar.get('branch', '')
    
    # 提取时柱（子女宫）
    hour_pillar = bazi_pillars.get('hour', {})
    
    # 提取五行分布
    element_counts = bazi_data.get('element_counts', {})
    
    # ⚠️ 修复：从 wangshuai_data 中提取旺衰字符串
    wangshuai = wangshuai_data.get('wangshuai', '')
    
    # 判断子女星类型（关键：男命看官杀，女命看食伤）
    zinv_xing_type = determine_children_star_type(ten_gods_data, gender)
    
    # ⚠️ 优化：使用工具函数计算年龄和当前大运（与排盘系统一致）
    birth_date = bazi_data.get('basic_info', {}).get('solar_date', '')
    current_age = 0
    birth_year = None
    if birth_date:
        current_age = calculate_user_age(birth_date)
        try:
            birth_year = int(birth_date.split('-')[0])
        except Exception:
            pass
    
    # 获取当前大运（与排盘系统一致）
    current_dayun_info = get_current_dayun(dayun_sequence, current_age)
    
    # ⚠️ 优化：使用工具函数构建增强的大运流年结构（包含优先级、描述、备注等）
    if special_liunians is None:
        special_liunians = []
    
    enhanced_dayun_structure = build_enhanced_dayun_structure(
        dayun_sequence=dayun_sequence,
        special_liunians=special_liunians,
        current_age=current_age,
        current_dayun=current_dayun_info,
        birth_year=birth_year,
        business_type='children_study',
        bazi_data=bazi_data,
        gender=gender
    )
    
    # ⚠️ 优化：添加后处理函数（清理流月流日字段，限制流年数量）
    def clean_liunian_data(liunian: Dict[str, Any]) -> Dict[str, Any]:
        """清理流年数据：移除流月流日字段"""
        cleaned = liunian.copy()
        # 移除流月流日相关字段
        fields_to_remove = ['liuyue_sequence', 'liuri_sequence', 'liushi_sequence']
        for field in fields_to_remove:
            cleaned.pop(field, None)
        return cleaned
    
    # 注意：不再限制流年数量，只按优先级排序。优先级仅用于排序，不省略数据。
    
    # 提取当前大运数据（优先级1）
    current_dayun_enhanced = enhanced_dayun_structure.get('current_dayun')
    current_dayun_data = None
    if current_dayun_enhanced:
        # 获取流年数据并应用清理
        raw_liunians = current_dayun_enhanced.get('liunians', [])
        # 清理流月流日字段
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        # 按优先级排序，但不限制数量（保留所有流年）
        all_liunians = sorted(cleaned_liunians, key=lambda x: x.get('priority', 999999))
        
        # 格式化当前大运数据
        _stem = current_dayun_enhanced.get('gan', current_dayun_enhanced.get('stem', ''))
        _branch = current_dayun_enhanced.get('zhi', current_dayun_enhanced.get('branch', ''))
        current_dayun_data = {
            'step': str(current_dayun_enhanced.get('step', '')),
            'ganzhi': f"{_stem}{_branch}",  # ⚠️ 统一干支字段
            'stem': _stem,
            'branch': _branch,
            'age_display': current_dayun_enhanced.get('age_display', current_dayun_enhanced.get('age_range', '')),
            'main_star': current_dayun_enhanced.get('main_star', ''),
            'priority': current_dayun_enhanced.get('priority', 1),
            'life_stage': current_dayun_enhanced.get('life_stage', ''),
            'description': current_dayun_enhanced.get('description', ''),
            'note': current_dayun_enhanced.get('note', ''),
            'liunians': all_liunians  # 不限制数量，保留所有流年（含 relations 字段）
        }
    
    # 提取关键大运数据（优先级2-10）
    key_dayuns_enhanced = enhanced_dayun_structure.get('key_dayuns', [])
    key_dayuns_data = []
    for key_dayun in key_dayuns_enhanced:
        # 获取流年数据并应用清理
        raw_liunians = key_dayun.get('liunians', [])
        # 清理流月流日字段
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        # 按优先级排序，但不限制数量（保留所有流年）
        all_liunians_for_dayun = sorted(cleaned_liunians, key=lambda x: x.get('priority', 999999))
        
        _kd_stem = key_dayun.get('gan', key_dayun.get('stem', ''))
        _kd_branch = key_dayun.get('zhi', key_dayun.get('branch', ''))
        key_dayuns_data.append({
            'step': str(key_dayun.get('step', '')),
            'ganzhi': f"{_kd_stem}{_kd_branch}",  # ⚠️ 统一干支字段
            'stem': _kd_stem,
            'branch': _kd_branch,
            'age_display': key_dayun.get('age_display', key_dayun.get('age_range', '')),
            'main_star': key_dayun.get('main_star', ''),
            'priority': key_dayun.get('priority', 999),
            'life_stage': key_dayun.get('life_stage', ''),
            'description': key_dayun.get('description', ''),
            'note': key_dayun.get('note', ''),
            'business_reason': key_dayun.get('business_reason', ''),  # ⚠️ 保留业务标注
            'liunians': all_liunians_for_dayun  # 不限制数量，保留所有流年（含 relations 字段）
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
    
    # ⚠️ 修复：从 wangshuai_data 中提取喜忌数据（从旺衰分析）
    xi_ji_data = {
        'xi_shen': wangshuai_data.get('xi_shen', ''),
        'ji_shen': wangshuai_data.get('ji_shen', ''),
        'xi_ji_elements': wangshuai_data.get('xi_ji_elements', {})
    }
    
    # ⚠️ 如果 xi_ji_elements 为空，尝试从 final_xi_ji 中获取
    if not xi_ji_data.get('xi_ji_elements'):
        final_xi_ji = wangshuai_data.get('final_xi_ji', {})
        if final_xi_ji:
            xi_ji_data['xi_ji_elements'] = {
                'xi_shen': final_xi_ji.get('xi_shen_elements', []),
                'ji_shen': final_xi_ji.get('ji_shen_elements', [])
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
            'special_liunians': special_liunians,  # ⚠️ 特殊流年（供公共模块按 dayun_step 分配到各运）
            'all_dayuns': all_dayuns,  # ⚠️ 新增：所有大运列表（用于参考）
            'ten_gods': ten_gods_data
        },
        
        # 4. 养育建议
        'yangyu_jianyi': {
            'ten_gods': ten_gods_data,  # ⚠️ 方案2：使用引用，不重复
            'wangshuai': wangshuai,  # ⚠️ 方案2：只引用旺衰字符串，不重复完整对象
            'xi_ji': xi_ji_data
        }
    }
    
    return input_data

# ✅ format_input_data_for_coze 函数已移至 server/utils/prompt_builders.py
# 通过顶部 import 导入，确保评测脚本和流式接口使用相同的函数


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
            # ⚠️ 修复：即使找不到官杀，也不显示"待完善"，直接返回类型说明
            return "男命子女星：官杀"
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
            # ⚠️ 修复：即使找不到食伤，也不显示"待完善"，直接返回类型说明
            return "女命子女星：食伤"


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

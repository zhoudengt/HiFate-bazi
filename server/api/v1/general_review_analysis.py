#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-总评分析API
基于用户生辰数据，使用 Coze Bot 流式生成总评分析
"""

import logging
import os
import sys
import time
from typing import Dict, Any, Optional, List, Tuple
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
from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
from core.analyzers.fortune_relation_analyzer import FortuneRelationAnalyzer
from server.utils.data_validator import validate_bazi_data
from server.api.v1.xishen_jishen import get_xishen_jishen, XishenJishenRequest
from server.utils.bazi_input_processor import BaziInputProcessor

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from core.analyzers.fortune_relation_analyzer import FortuneRelationAnalyzer
from core.analyzers.wuxing_balance_analyzer import WuxingBalanceAnalyzer
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.industry_service import IndustryService
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.dayun_liunian_helper import (
    calculate_user_age,
    get_current_dayun,
    build_enhanced_dayun_structure
)

from server.config.input_format_loader import build_input_data_from_result
from server.utils.prompt_builders import (
    format_general_review_input_data_for_coze as format_input_data_for_coze,
    format_general_review_for_llm,
    _simplify_dayun
)
from server.services.user_interaction_logger import get_user_interaction_logger

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class GeneralReviewRequest(BaziBaseRequest):
    """总评分析请求模型（继承 BaziBaseRequest，包含7个标准参数）"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量配置）")


@router.post("/general-review/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def general_review_analysis_test(request: GeneralReviewRequest):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        request: 总评分析请求参数
        
    Returns:
        dict: 包含格式化后的数据
    """
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, request.calendar_type or "solar", 
            request.location, request.latitude, request.longitude
        )
        
        # 使用统一接口获取基础数据（与流式接口保持一致的 modules 配置）
        modules = {
            'bazi': True,
            'wangshuai': True,
            'xishen_jishen': True,
            'detail': True,
            'dayun': {
                'mode': 'count',
                'count': 13  # 获取所有大运（包含小运）
            },
            'liunian': True,
            'special_liunians': {
                'dayun_config': {
                    'mode': 'count',
                    'count': 8
                },
                'count': 100
            },
            'personality': True,
            'rizhu': True,
            'health': True,
            'rules': {
                'types': ['rizhu_gender', 'character', 'summary']
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
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            bazi_data = bazi_module_data.get('bazi', {})
            rizhu_from_bazi = bazi_module_data.get('rizhu', {})
        else:
            bazi_data = bazi_module_data
            rizhu_from_bazi = {}
        
        wangshuai_result = unified_data.get('wangshuai', {})
        detail_result = unified_data.get('detail', {})
        personality_result = unified_data.get('personality', {})
        rizhu_result = unified_data.get('rizhu', {}) or rizhu_from_bazi
        health_result = unified_data.get('health', {})
        
        # 提取和验证数据
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
        liunian_sequence = []
        special_liunians = []
        
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
        
        for liunian in fortune_data.liunian_sequence:
            liunian_sequence.append({
                'year': liunian.year,
                'stem': liunian.stem,
                'branch': liunian.branch,
                'ganzhi': liunian.ganzhi,
                'age': liunian.age,
                'age_display': liunian.age_display,
                'nayin': liunian.nayin,
                'main_star': liunian.main_star,
                'hidden_stems': liunian.hidden_stems or [],
                'hidden_stars': liunian.hidden_stars or [],
                'star_fortune': liunian.star_fortune,
                'self_sitting': liunian.self_sitting,
                'kongwang': liunian.kongwang,
                'deities': liunian.deities or [],
                'details': liunian.details or {}
            })
        
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
        
        logger.info(f"[General Review Test] ✅ 统一数据服务获取完成 - dayun: {len(dayun_sequence)}, liunian: {len(liunian_sequence)}, special: {len(special_liunians)}")
        
        # 获取喜忌数据（从 unified_data 获取，与流式接口一致）
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        if xishen_jishen_result and hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif xishen_jishen_result and hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        # 构建input_data（与流式接口保持一致）
        input_data = build_general_review_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            request.gender,
            final_solar_date,
            final_solar_time,
            personality_result,
            rizhu_result,
            health_result,
            liunian_sequence,  # 使用从 fortune_data 获取的流年序列
            special_liunians,
            xishen_jishen_result
        )
        logger.info("✅ [General Review Test] 使用与流式接口一致的数据构建 input_data")
        
        # 格式化数据
        formatted_data = format_input_data_for_coze(input_data)
        
        return {
            "success": True,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_hexin_geju', {}).get('bazi_pillars', {}),
                "dayun_count": len(input_data.get('guanjian_dayun', {}).get('key_dayuns', [])),
                "current_dayun_liunians_count": len(input_data.get('guanjian_dayun', {}).get('current_dayun', {}).get('liunians', []) if input_data.get('guanjian_dayun', {}).get('current_dayun') else []),
                "key_dayuns_count": len(input_data.get('guanjian_dayun', {}).get('key_dayuns', [])),
                "xishen": input_data.get('zhongsheng_tidian', {}).get('xishen', {}),
                "jishen": input_data.get('zhongsheng_tidian', {}).get('jishen', {})
            },
            "usage": {
                "description": "此接口返回的数据可以直接用于 Coze Bot 的 {{input}} 占位符",
                "coze_bot_setup": "1. 登录 Coze 平台\n2. 找到'八字命理总评分析' Bot\n3. 进入 Bot 设置 → System Prompt\n4. 配置提示词并保存",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/general-review/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}", "calendar_type": "{request.calendar_type or "solar"}"}}\''
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


@router.post("/general-review/stream", summary="流式生成总评分析")
async def general_review_analysis_stream(request: GeneralReviewRequest):
    """
    流式生成总评分析
    
    Args:
        request: 总评分析请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    logger.info(f"[General Review API] 收到请求: solar_date={request.solar_date}, solar_time={request.solar_time}")
    
    return StreamingResponse(
        general_review_analysis_stream_generator(
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


@router.post("/general-review/debug", summary="调试：查看总评分析数据")
async def general_review_analysis_debug(request: GeneralReviewRequest):
    """
    调试接口：查看提取的数据和构建的 Prompt
    
    Args:
        request: 总评分析请求参数
        
    Returns:
        dict: 包含数据和 Prompt 的调试信息
    """
    logger.debug(f"[DEBUG general_review_analysis_debug] 函数被调用，参数: solar_date={request.solar_date}, solar_time={request.solar_time}, gender={request.gender}")
    logger.info(f"[General Review Debug] ========== 函数开始执行 ==========")
    logger.info(f"[General Review Debug] 函数被调用，参数: solar_date={request.solar_date}, solar_time={request.solar_time}, gender={request.gender}")
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, "solar", None, None, None
        )
        
        # 使用统一接口获取数据
        try:
            # 构建统一接口的 modules 配置
            modules = {
                'bazi': True,
                'wangshuai': True,
                'xishen_jishen': True,
                'detail': True,
                'dayun': {
                    'mode': 'count',
                    'count': 13  # 获取所有大运（包含小运）
                },
                'liunian': True,
                'special_liunians': {
                    'dayun_config': {
                        'mode': 'count',
                        'count': 8
                    },
                    'count': 100
                },
                'personality': True,
                'rizhu': True,
                'health': True,
                'rules': {
                    'types': ['rizhu_gender', 'character', 'summary']
                }
            }
            
            logger.info(f"[General Review Debug] 开始调用统一接口获取数据")
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
            logger.info(f"[General Review Debug] ✅ 统一接口数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[General Review Debug] ❌ 统一接口调用失败: {e}\n{error_msg}")
            return {
                "success": False,
                "error": f"数据获取失败: {str(e)}",
                "error_trace": error_msg
            }
        
        # 从统一接口返回的数据中提取所需字段
        # 注意：BaziService.calculate_bazi_full 返回的结构是 {bazi: {...}, rizhu: {...}, matched_rules: [...]}
        # 所以实际八字数据在 unified_data['bazi']['bazi'] 中
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            # 嵌套结构：{bazi: {...实际数据...}, rizhu: {...}, matched_rules: [...]}
            bazi_data = bazi_module_data.get('bazi', {})
            # 同时可以从这里提取 rizhu 和 matched_rules
            rizhu_from_bazi = bazi_module_data.get('rizhu', {})
            matched_rules_from_bazi = bazi_module_data.get('matched_rules', [])
        else:
            # 扁平结构或空数据
            bazi_data = bazi_module_data
            rizhu_from_bazi = {}
            matched_rules_from_bazi = []
        
        # ⚠️ 修复：wangshuai_result 也是嵌套结构 {success: true, data: {...}}
        wangshuai_module_data = unified_data.get('wangshuai', {})
        if isinstance(wangshuai_module_data, dict) and 'data' in wangshuai_module_data:
            wangshuai_result = wangshuai_module_data.get('data', {})
        else:
            wangshuai_result = wangshuai_module_data
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        detail_data = unified_data.get('detail', {})
        personality_result = unified_data.get('personality', {})
        # 优先使用 personality 模块的 rizhu，如果没有则使用 bazi 模块返回的
        rizhu_result = unified_data.get('rizhu', {}) or rizhu_from_bazi
        health_result = unified_data.get('health', {})
        rules_data = unified_data.get('rules', [])
        
        # 处理 xishen_jishen_result（可能是 Pydantic 模型，需要转换为字典）
        if xishen_jishen_result and hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif xishen_jishen_result and hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        # 验证八字数据
        bazi_data = validate_bazi_data(bazi_data)
        
        # 提取大运序列和流年序列
        # 优先从 detail 模块中提取（与原有逻辑一致）
        if detail_data:
            details = detail_data.get('details', detail_data)
            dayun_sequence = details.get('dayun_sequence', [])
            liunian_sequence = details.get('liunian_sequence', [])
        else:
            # 降级方案：从 dayun 和 liunian 模块中提取
            dayun_sequence = unified_data.get('dayun', [])
            liunian_sequence = unified_data.get('liunian', [])
        
        logger.info(f"[General Review Debug] 获取到 dayun_sequence 数量: {len(dayun_sequence)}, liunian_sequence 数量: {len(liunian_sequence)}")
        
        # 提取特殊流年（统一接口返回的是字典格式，包含 'list', 'by_dayun', 'formatted'）
        special_liunians_data = unified_data.get('special_liunians', {})
        if isinstance(special_liunians_data, dict):
            special_liunians = special_liunians_data.get('list', [])
        elif isinstance(special_liunians_data, list):
            special_liunians = special_liunians_data
        else:
            special_liunians = []
        
        logger.info(f"[General Review Debug] 获取到特殊流年数量: {len(special_liunians)}")
        
        # 提取规则匹配结果（统一接口返回的是列表格式）
        rizhu_rules = []
        if isinstance(rules_data, list):
            rizhu_rules = rules_data
        elif isinstance(rules_data, dict):
            # 如果返回的是字典格式，合并所有规则类型
            rizhu_rules = rules_data.get('rizhu_gender', []) + \
                         rules_data.get('character', []) + \
                         rules_data.get('summary', [])
        
        # 构建 detail_result（用于 build_general_review_input_data）
        # 保持与原有格式一致
        detail_result = detail_data if detail_data else {
            'details': {
                'dayun_sequence': dayun_sequence,
                'liunian_sequence': liunian_sequence
            }
        }
        
        # 获取五行统计
        element_counts = bazi_data.get('element_counts', {})
        
        # 构建input_data（优先使用数据库格式定义）
        # 构建input_data（直接使用硬编码函数，确保数据完整性）
        input_data = build_general_review_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=request.gender,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            personality_result=personality_result,
            rizhu_result=rizhu_result,
            health_result=health_result,
            liunian_sequence=liunian_sequence,
            special_liunians=special_liunians,
            xishen_jishen_result=xishen_jishen_result
        )
        logger.info("✅ 使用硬编码函数构建 input_data: general_review_analysis")
        
        # ⚠️ DEBUG: 调用后检查变量
        logger.debug(f"[DEBUG] build_general_review_input_data 调用后，dayun_sequence 数量: {len(dayun_sequence)}, special_liunians 数量: {len(special_liunians)}")
        logger.info(f"[General Review Debug] build_general_review_input_data 调用后，dayun_sequence 数量: {len(dayun_sequence)}, special_liunians 数量: {len(special_liunians)}")
        
        # 添加日柱规则
        input_data['rizhu_rules'] = {
            'matched_rules': rizhu_rules,
            'rules_count': len(rizhu_rules),
            'rule_judgments': [
                rule.get('content', {}).get('text', '') 
                for rule in rizhu_rules 
                if isinstance(rule.get('content'), dict) and rule.get('content', {}).get('text')
            ]
        }
        
        # 验证数据完整性
        is_valid, validation_error = validate_general_review_input_data(input_data)
        if not is_valid:
            return {
                "success": False,
                "error": f"数据完整性验证失败: {validation_error}"
            }
        
        # ✅ 只返回 input_data，评测脚本使用相同的函数构建 formatted_data
        return {
            "success": True,
            "input_data": input_data,
            "summary": {
                "bazi_pillars": input_data.get('mingpan_hexin_geju', {}).get('bazi_pillars', {}),
                "dayun_count": len(input_data.get('guanjian_dayun', {}).get('key_dayuns', [])),
                "current_dayun_liunians_count": len(input_data.get('guanjian_dayun', {}).get('current_dayun', {}).get('liunians', []) if input_data.get('guanjian_dayun', {}).get('current_dayun') else []),
                "key_dayuns_count": len(input_data.get('guanjian_dayun', {}).get('key_dayuns', [])),
                "xishen": input_data.get('zhongsheng_tidian', {}).get('xishen', {}),
                "jishen": input_data.get('zhongsheng_tidian', {}).get('jishen', {})
            }
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"调试接口失败: {e}\n{error_trace}")
        
        return {
            "success": False,
            "error": str(e)
        }


async def general_review_analysis_stream_generator(
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
    流式生成总评分析的生成器
    
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
    
    # 调试：确认生成器被调用
    logger.debug(f"[General Review Stream DEBUG] 生成器开始执行: solar_date={solar_date}")
    
    try:
        # ✅ 性能优化：立即返回首条消息，让用户感知到连接已建立
        # 这个优化将首次响应时间从 24秒 降低到 <1秒
        # ✅ 架构优化：移除无意义的进度消息，直接开始数据处理
        # 详见：standards/08_数据编排架构规范.md
        
        # 1. 确定使用的 bot_id（优先级：参数 > 数据库配置 > 环境变量）
        used_bot_id = bot_id
        if not used_bot_id:
            # 只从数据库读取，不降级到环境变量
            used_bot_id = get_config_from_db_only("GENERAL_REVIEW_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                error_msg = {
                    'type': 'error',
                    'content': "数据库配置缺失: GENERAL_REVIEW_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置。"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
        
        logger.info(f"总评分析请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={used_bot_id}")
        
        # 2. 处理输入（农历转换等，支持7个标准参数）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, calendar_type or "solar", location, latitude, longitude
        )
        
        # 3. 使用统一接口获取数据（阶段2：数据获取与并行优化）
        # ✅ 性能优化：在数据获取开始时就 yield，减少客户端等待时间
        try:
            # 构建统一接口的 modules 配置
            modules = {
                'bazi': True,
                'wangshuai': True,
                'xishen_jishen': True,
                'detail': True,
                'dayun': {
                    'mode': 'count',
                    'count': 13  # 获取所有大运（包含小运）
                },
                'liunian': True,
                'special_liunians': {
                    'dayun_config': {
                        'mode': 'count',
                        'count': 8
                    },
                    'count': 100
                },
                'personality': True,
                'rizhu': True,  # ⚠️ 启用 rizhu 模块（调用 RizhuLiujiaziService 返回完整分析）
                'health': True,
                'rules': {
                    'types': ['rizhu_gender', 'character', 'summary']
                }
            }
            
            logger.info(f"[General Review Stream] 开始调用统一接口获取数据")
            
            unified_data = await BaziDataOrchestrator.fetch_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                modules=modules,
                use_cache=True,
                parallel=True
            )
            logger.info(f"[General Review Stream] ✅ 统一接口数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[General Review Stream] ❌ 统一接口调用失败: {e}\n{error_msg}")
            error_response = {
                'type': 'error',
                'content': f"数据获取失败: {str(e)}。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 4. 从统一接口返回的数据中提取所需字段
        # 注意：BaziService.calculate_bazi_full 返回的结构是 {bazi: {...}, rizhu: {...}, matched_rules: [...]}
        # 所以实际八字数据在 unified_data['bazi']['bazi'] 中
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            # 嵌套结构：{bazi: {...实际数据...}, rizhu: {...}, matched_rules: [...]}
            bazi_data = bazi_module_data.get('bazi', {})
            # 同时可以从这里提取 rizhu 和 matched_rules
            rizhu_from_bazi = bazi_module_data.get('rizhu', {})
            matched_rules_from_bazi = bazi_module_data.get('matched_rules', [])
        else:
            # 扁平结构或空数据
            bazi_data = bazi_module_data
            rizhu_from_bazi = {}
            matched_rules_from_bazi = []
        
        wangshuai_result = unified_data.get('wangshuai', {})
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        detail_data = unified_data.get('detail', {})
        personality_result = unified_data.get('personality', {})
        # 优先使用 personality 模块的 rizhu，如果没有则使用 bazi 模块返回的
        rizhu_result = unified_data.get('rizhu', {}) or rizhu_from_bazi
        health_result = unified_data.get('health', {})
        rules_data = unified_data.get('rules', [])
        
        # 处理 xishen_jishen_result（可能是 Pydantic 模型，需要转换为字典）
        if xishen_jishen_result and hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif xishen_jishen_result and hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        # 验证八字数据
        bazi_data = validate_bazi_data(bazi_data)
        
        # ✅ 使用统一数据服务获取大运流年、特殊流年数据（确保数据一致性）
        # ✅ 性能优化：复用 unified_data 中已获取的 detail_data，避免重复计算
        from server.orchestrators.bazi_data_service import BaziDataService
        
        # 获取完整运势数据（包含大运序列、流年序列、特殊流年）
        # 性能优化：传入已获取的 detail_data，避免重复调用 calculate_detail_full
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
            current_time=None,
            detail_result=detail_data  # ✅ 性能优化：复用已获取的 detail_data
        )
        
        # ✅ 性能优化：使用列表推导式批量转换，减少循环开销
        # 从统一数据服务获取大运序列和特殊流年
        # 转换为字典格式（兼容现有代码）- 使用列表推导式优化性能
        dayun_sequence = [
            {
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
            }
            for dayun in fortune_data.dayun_sequence
        ]
        
        # 转换为字典格式（兼容现有代码）- 使用列表推导式优化性能
        liunian_sequence = [
            {
                'year': liunian.year,
                'stem': liunian.stem,
                'branch': liunian.branch,
                'ganzhi': liunian.ganzhi,
                'age': liunian.age,
                'age_display': liunian.age_display,
                'nayin': liunian.nayin,
                'main_star': liunian.main_star,
                'hidden_stems': liunian.hidden_stems or [],
                'hidden_stars': liunian.hidden_stars or [],
                'star_fortune': liunian.star_fortune,
                'self_sitting': liunian.self_sitting,
                'kongwang': liunian.kongwang,
                'deities': liunian.deities or [],
                'details': liunian.details or {}
            }
            for liunian in fortune_data.liunian_sequence
        ]
        
        # 转换为字典格式（兼容现有代码）- 使用列表推导式优化性能
        special_liunians = [
            {
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
            }
            for special_liunian in fortune_data.special_liunians
        ]
        
        logger.info(f"[General Review Stream] ✅ 统一数据服务获取完成 - dayun_sequence 数量: {len(dayun_sequence)}, liunian_sequence 数量: {len(liunian_sequence)}, 特殊流年数量: {len(special_liunians)}")
        
        # 提取规则匹配结果（统一接口返回的是列表格式）
        rizhu_rules = []
        if isinstance(rules_data, list):
            rizhu_rules = rules_data
        elif isinstance(rules_data, dict):
            # 如果返回的是字典格式，合并所有规则类型
            rizhu_rules = rules_data.get('rizhu_gender', []) + \
                         rules_data.get('character', []) + \
                         rules_data.get('summary', [])
        
        # 构建 detail_result（用于 build_general_review_input_data）
        # 保持与原有格式一致
        detail_result = detail_data if detail_data else {
            'details': {
                'dayun_sequence': dayun_sequence,
                'liunian_sequence': liunian_sequence
            }
        }
        
        # 获取五行统计
        element_counts = bazi_data.get('element_counts', {})
        
        # ========== 阶段5：构建 input_data（直接使用硬编码函数，确保数据完整性） ==========
        logger.info(f"[阶段5-DEBUG] 准备构建 input_data，special_liunians 数量: {len(special_liunians)}")
        if special_liunians:
            special_liunian_strs = [f"{l.get('year', '')}年{l.get('ganzhi', '')}" for l in special_liunians[:3]]
            logger.info(f"[阶段5-DEBUG] special_liunians 内容: {special_liunian_strs}")
        
        input_data = build_general_review_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=gender,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            personality_result=personality_result,
            rizhu_result=rizhu_result,
            health_result=health_result,
            liunian_sequence=liunian_sequence,
            special_liunians=special_liunians,
            xishen_jishen_result=xishen_jishen_result
        )
        logger.info("✅ 使用硬编码函数构建 input_data: general_review_analysis")
        
        # 8. 添加日柱规则（NEW）
        input_data['rizhu_rules'] = {
            'matched_rules': rizhu_rules,
            'rules_count': len(rizhu_rules),
            'rule_judgments': [
                rule.get('content', {}).get('text', '') 
                for rule in rizhu_rules 
                if isinstance(rule.get('content'), dict) and rule.get('content', {}).get('text')
            ]
        }
        
        # 7. 验证数据完整性（阶段3：数据验证与完整性检查）
        is_valid, validation_error = validate_general_review_input_data(input_data)
        if not is_valid:
            logger.error(f"数据完整性验证失败: {validation_error}")
            error_msg = {
                'type': 'error',
                'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 8. ⚠️ 优化：使用精简中文文本格式（Token 减少 86%）
        formatted_data = format_general_review_for_llm(input_data)
        logger.info(f"[General Review Stream] 格式化数据长度: {len(formatted_data)} 字符（优化后）")
        logger.debug(f"[General Review Stream] 格式化数据:\n{formatted_data}")
        
        # 8.1 保存参数到文件（用于数据减枝分析）
        try:
            # 创建保存目录
            save_dir = os.path.join(project_root, "logs", "general_review_params")
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名（使用时间戳避免冲突）
            timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_date = final_solar_date.replace("-", "")
            safe_time = final_solar_time.replace(":", "-")
            filename = f"general_review_{safe_date}_{safe_time}_{gender}_{timestamp_str}.json"
            filepath = os.path.join(save_dir, filename)
            
            # 计算数据统计
            def calculate_module_size(module_data):
                """计算模块数据大小（JSON序列化后的字节数）"""
                try:
                    return len(json.dumps(module_data, ensure_ascii=False))
                except:
                    return 0
            
            modules_size = {}
            for key, value in input_data.items():
                if key != '_debug':  # 跳过调试信息
                    modules_size[key] = calculate_module_size(value)
            
            # 构建保存数据
            save_data = {
                "request_params": {
                    "solar_date": final_solar_date,
                    "solar_time": final_solar_time,
                    "gender": gender,
                    "calendar_type": calendar_type,
                    "location": location,
                    "latitude": latitude,
                    "longitude": longitude
                },
                "formatted_data": formatted_data,
                "statistics": {
                    "formatted_data_length": len(formatted_data),
                    "formatted_data_size_kb": round(len(formatted_data) / 1024, 2),
                    "input_data_keys": list(input_data.keys()),
                    "modules_size": modules_size,
                    "modules_size_total_kb": round(sum(modules_size.values()) / 1024, 2),
                    "dayun_count": len(dayun_sequence),
                    "liunian_count": len(liunian_sequence),
                    "special_liunian_count": len(special_liunians)
                },
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[General Review Stream] ✅ 参数已保存到: {filepath}")
            logger.info(f"[General Review Stream] 数据统计: 总大小 {save_data['statistics']['formatted_data_size_kb']} KB, "
                       f"模块总大小 {save_data['statistics']['modules_size_total_kb']} KB")
        except Exception as e:
            # 保存失败不影响主流程
            logger.warning(f"[General Review Stream] 保存参数文件失败: {e}", exc_info=True)
        
        # 9. 调用 LLM API（阶段5：LLM API调用，支持 Coze 和百炼平台）
        logger.info(f"🔍 [步骤5-LLM调用] 开始调用 LLM API，Bot ID: {used_bot_id}")
        from server.services.llm_service_factory import LLMServiceFactory
        llm_service = LLMServiceFactory.get_service(scene="general_review", bot_id=used_bot_id)

        # 10. 流式处理（阶段6：流式处理）
        llm_start_time = time.time()
        chunk_count = 0
        total_content_length = 0
        has_content = False
        
        async for chunk in llm_service.stream_analysis(formatted_data, bot_id=used_bot_id):
            chunk_type = chunk.get('type', 'unknown')
            
            # 记录第一个token时间
            if llm_first_token_time is None and chunk_type == 'progress':
                llm_first_token_time = time.time()
            
            if chunk_type == 'progress':
                chunk_count += 1
                content = chunk.get('content', '')
                llm_output_chunks.append(content)  # 收集输出内容
                total_content_length += len(content)
                has_content = True
                if chunk_count == 1:
                    logger.info(f"✅ [步骤5-Coze调用] 收到第一个响应块，类型: {chunk_type}")
            elif chunk_type == 'complete':
                complete_content = chunk.get('content', '')
                llm_output_chunks.append(complete_content)  # 收集完整内容
                logger.info(f"✅ [步骤5-Coze调用] 收到完成响应，总块数: {chunk_count}, 总内容长度: {total_content_length}")
                has_content = True
            elif chunk_type == 'error':
                logger.error(f"❌ [步骤5-Coze调用] 收到错误响应: {chunk.get('content', '')}")
            
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk_type in ['complete', 'error']:
                break
        
        # 记录交互数据（异步，不阻塞）
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
        llm_output = ''.join(llm_output_chunks)
        
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='general',
            function_name='八字命理-总评分析',
            frontend_api='/api/v1/bazi/general-review/stream',
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
            function_type='general',
            function_name='八字命理-总评分析',
            frontend_api='/api/v1/bazi/general-review/stream',
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
        # 其他错误（阶段7：错误处理）
        import traceback
        logger.error(f"总评分析失败: {e}\n{traceback.format_exc()}")
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
            function_type='general',
            function_name='八字命理-总评分析',
            frontend_api='/api/v1/bazi/general-review/stream',
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


def classify_special_liunians(special_liunians: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    按关系类型分类特殊流年（优先级排序）
    
    优先级：天克地冲 > 天合地合 > 岁运并临 > 其他
    
    Args:
        special_liunians: 特殊流年列表
        
    Returns:
        dict: 分类后的特殊流年
            - tiankedi_chong: 天克地冲的流年
            - tianhedi_he: 天合地合的流年
            - suiyun_binglin: 岁运并临的流年
            - other: 其他关系的流年
    """
    classified = {
        'tiankedi_chong': [],
        'tianhedi_he': [],
        'suiyun_binglin': [],
        'other': []
    }
    
    for liunian in special_liunians:
        relations = liunian.get('relations', [])
        relation_types = [r.get('type', '') for r in relations]
        
        # 检查是否包含优先关系（按优先级顺序）
        has_tiankedi = any('天克地冲' in rt for rt in relation_types)
        has_tianhedi = any('天合地合' in rt for rt in relation_types)
        has_suiyun = any('岁运并临' in rt for rt in relation_types)
        
        # 优先级：天克地冲 > 天合地合 > 岁运并临 > 其他
        if has_tiankedi:
            classified['tiankedi_chong'].append(liunian)
        elif has_tianhedi:
            classified['tianhedi_he'].append(liunian)
        elif has_suiyun:
            classified['suiyun_binglin'].append(liunian)
        else:
            classified['other'].append(liunian)
    
    return classified


def organize_special_liunians_by_dayun(
    special_liunians: List[Dict[str, Any]], 
    dayun_sequence: List[Dict[str, Any]]
) -> Dict[int, Dict[str, Any]]:
    """
    将特殊流年按大运分组，每个大运下的流年按优先级分类
    
    优先级：天克地冲 > 天合地合 > 岁运并临 > 其他
    
    Args:
        special_liunians: 特殊流年列表（包含 dayun_step 字段）
        dayun_sequence: 大运序列（用于获取大运信息）
    
    Returns:
        dict: {
            dayun_step: {
                'dayun_info': {...},  # 大运信息（step, stem, branch, age_display, year_start, year_end）
                'tiankedi_chong': [...],  # 天克地冲
                'tianhedi_he': [...],     # 天合地合
                'suiyun_binglin': [...],  # 岁运并临
                'other': [...]            # 其他
            }
        }
    """
    # 1. 先按关系类型分类（优先级排序）
    classified = classify_special_liunians(special_liunians)
    
    # 2. 创建大运映射
    dayun_map = {}
    for dayun in dayun_sequence:
        step = dayun.get('step')
        if step is not None:
            dayun_map[step] = {
                'step': dayun.get('step'),
                'stem': dayun.get('stem', ''),
                'branch': dayun.get('branch', ''),
                'age_display': dayun.get('age_display', ''),
                'year_start': dayun.get('year_start', 0),
                'year_end': dayun.get('year_end', 0)
            }
    
    # 3. 按大运分组
    result = {}
    
    # 处理天克地冲
    for liunian in classified['tiankedi_chong']:
        step = liunian.get('dayun_step')
        if step is not None:
            if step not in result:
                result[step] = {
                    'dayun_info': dayun_map.get(step, {}),
                    'tiankedi_chong': [],
                    'tianhedi_he': [],
                    'suiyun_binglin': [],
                    'other': []
                }
            result[step]['tiankedi_chong'].append(liunian)
    
    # 处理天合地合
    for liunian in classified['tianhedi_he']:
        step = liunian.get('dayun_step')
        if step is not None:
            if step not in result:
                result[step] = {
                    'dayun_info': dayun_map.get(step, {}),
                    'tiankedi_chong': [],
                    'tianhedi_he': [],
                    'suiyun_binglin': [],
                    'other': []
                }
            result[step]['tianhedi_he'].append(liunian)
    
    # 处理岁运并临
    for liunian in classified['suiyun_binglin']:
        step = liunian.get('dayun_step')
        if step is not None:
            if step not in result:
                result[step] = {
                    'dayun_info': dayun_map.get(step, {}),
                    'tiankedi_chong': [],
                    'tianhedi_he': [],
                    'suiyun_binglin': [],
                    'other': []
                }
            result[step]['suiyun_binglin'].append(liunian)
    
    # 处理其他
    for liunian in classified['other']:
        step = liunian.get('dayun_step')
        if step is not None:
            if step not in result:
                result[step] = {
                    'dayun_info': dayun_map.get(step, {}),
                    'tiankedi_chong': [],
                    'tianhedi_he': [],
                    'suiyun_binglin': [],
                    'other': []
                }
            result[step]['other'].append(liunian)
    
    return result


def _build_rizhu_xinming_node(
    day_pillar: Dict[str, Any],
    gender: str,
    personality_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    构建日柱性命解析节点
    
    包含完整的日柱性格与命运分析数据（31条或更多），不省略任何内容。
    数据来源：src/bazi_config/rizhu_gender_config.py -> RIZHU_GENDER_CONFIG
    
    Args:
        day_pillar: 日柱数据，包含 stem（天干）和 branch（地支）
        gender: 性别（male/female）
        personality_result: 日主性格分析结果，包含 descriptions 列表
    
    Returns:
        dict: 日柱性命解析节点
            {
                'rizhu': '甲子',              # 日柱（天干+地支）
                'gender': 'female',           # 性别
                'gender_display': '女',       # 性别显示
                'descriptions': [...],        # 完整的性格命运描述列表
                'descriptions_count': 31,     # 描述条目数量
                'summary': '日柱甲子女命分析'  # 摘要标题
            }
    """
    # 提取日柱
    day_stem = day_pillar.get('stem', '') if day_pillar else ''
    day_branch = day_pillar.get('branch', '') if day_pillar else ''
    rizhu = f"{day_stem}{day_branch}"
    
    # 转换性别显示
    gender_display = '男' if gender == 'male' else '女'
    
    # 提取完整的 descriptions 列表
    descriptions = []
    if personality_result and isinstance(personality_result, dict):
        descriptions = personality_result.get('descriptions', [])
    
    # 构建摘要
    summary = f"日柱{rizhu}{gender_display}命分析" if rizhu else f"{gender_display}命分析"
    
    # 记录日志
    logger.info(f"[rizhu_xinming_jiexi] 构建日柱节点: rizhu={rizhu}, gender={gender}, descriptions_count={len(descriptions)}")
    
    return {
        'rizhu': rizhu,
        'gender': gender,
        'gender_display': gender_display,
        'descriptions': descriptions,  # 完整的31条（或更多）数据
        'descriptions_count': len(descriptions),
        'summary': summary
    }


def build_general_review_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    gender: str,
    solar_date: str = None,  # ⚠️ 新增：原始阳历日期
    solar_time: str = None,  # ⚠️ 新增：原始阳历时间
    personality_result: Dict[str, Any] = None,
    rizhu_result: Dict[str, Any] = None,
    health_result: Dict[str, Any] = None,
    liunian_sequence: List[Dict[str, Any]] = None,
    special_liunians: List[Dict[str, Any]] = None,  # ⚠️ 新增：特殊流年（已筛选）
    xishen_jishen_result: Any = None  # ⚠️ 喜忌数据结果（XishenJishenResponse）
) -> Dict[str, Any]:
    """
    构建总评分析的输入数据
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        gender: 性别（male/female）
        solar_date: 原始阳历日期
        solar_time: 原始阳历时间
        personality_result: 日主性格分析结果
        rizhu_result: 日柱算法结果
        health_result: 健康分析结果
        liunian_sequence: 流年序列
        
    Returns:
        dict: 总评分析的input_data
    """
    # ⚠️ DEBUG: 记录参数信息到日志
    logger.info(f"[DEBUG build_general_review_input_data] solar_date={solar_date}, solar_time={solar_time}, gender={gender}")
    logger.info(f"[DEBUG build_general_review_input_data] dayun_sequence length={len(dayun_sequence)}")
    logger.info(f"[DEBUG build_general_review_input_data] bazi_data keys={list(bazi_data.keys())}")
    logger.info(f"[DEBUG build_general_review_input_data] bazi_data type={type(bazi_data)}")
    
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    logger.info(f"[DEBUG] bazi_pillars={bazi_pillars}")
    day_pillar = bazi_pillars.get('day', {})
    element_counts = bazi_data.get('element_counts', {})
    logger.info(f"[DEBUG] element_counts={element_counts}")
    ten_gods_data = bazi_data.get('ten_gods_stats', {})
    ten_gods_full = bazi_data.get('ten_gods', {})
    
    # 提取月令
    month_pillar = bazi_pillars.get('month', {})
    month_branch = month_pillar.get('branch', '')
    yue_ling = f"{month_branch}月" if month_branch else ''
    
    # 判断格局类型（基于月令和十神配置）
    geju_type = determine_geju_type(month_branch, ten_gods_full, wangshuai_result)
    
    # 分析五行流通情况
    wuxing_liutong = analyze_wuxing_liutong(element_counts, bazi_pillars)
    
    # 提取事业星和财富星
    shiye_xing = extract_career_star(ten_gods_data)
    caifu_xing = extract_wealth_star(ten_gods_data)
    
    # 分析大运对事业财运的影响
    dayun_effect = analyze_dayun_effect(dayun_sequence, shiye_xing, caifu_xing, ten_gods_data)
    
    # ⚠️ 数据提取辅助函数：从 wangshuai_result 中提取旺衰数据
    def extract_wangshuai_data(wangshuai_result: Dict[str, Any]) -> Dict[str, Any]:
        """从 wangshuai_result 中提取旺衰数据"""
        if isinstance(wangshuai_result, dict):
            if wangshuai_result.get('success') and 'data' in wangshuai_result:
                return wangshuai_result.get('data', {})
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
        
        return {}
    
    # ⚠️ 修复：从 wangshuai_result 中正确提取旺衰数据
    wangshuai_data = extract_wangshuai_data(wangshuai_result)
    wangshuai_str = wangshuai_data.get('wangshuai', '') if isinstance(wangshuai_data, dict) else str(wangshuai_data) if wangshuai_data else ''
    wangshuai_detail_str = wangshuai_data.get('wangshuai_detail', wangshuai_data.get('detail', '')) if isinstance(wangshuai_data, dict) else ''
    
    # ⚠️ 修复：从 detail_result 或 bazi_data 中提取十神数据
    ten_gods_extracted = extract_ten_gods_data(detail_result, bazi_data)
    # 如果提取的十神数据为空，使用原有的 ten_gods_full
    if not ten_gods_extracted:
        ten_gods_extracted = ten_gods_full
    
    # ⚠️ 优化：使用工具函数计算年龄和当前大运（与排盘系统一致）
    birth_date = bazi_data.get('basic_info', {}).get('solar_date', '') or solar_date
    current_age = 0
    birth_year = None
    if birth_date:
        current_age = calculate_user_age(birth_date)
        try:
            birth_year = int(birth_date.split('-')[0])
        except:
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
        birth_year=birth_year
    )
    
    # ⚠️ 优化：添加后处理函数（清理流月流日字段，限制流年数量）
    def clean_liunian_data(liunian: Dict[str, Any]) -> Dict[str, Any]:
        """清理流年数据：移除流月流日字段，保留 relations 和 dayun_step 字段"""
        cleaned = liunian.copy()
        fields_to_remove = ['liuyue_sequence', 'liuri_sequence', 'liushi_sequence']
        for field in fields_to_remove:
            cleaned.pop(field, None)
        # ⚠️ 关键：确保 relations 和 dayun_step 字段被保留
        if 'relations' not in cleaned:
            cleaned['relations'] = liunian.get('relations', [])
        if 'dayun_step' not in cleaned:
            cleaned['dayun_step'] = liunian.get('dayun_step')
        if 'dayun_ganzhi' not in cleaned:
            cleaned['dayun_ganzhi'] = liunian.get('dayun_ganzhi', '')
        return cleaned
    
    # ⚠️ 修改：不再限制流年数量，优先级只用于排序，所有特殊流年都要显示
    # 提取当前大运数据（优先级1）
    current_dayun_enhanced = enhanced_dayun_structure.get('current_dayun')
    current_dayun_data = None
    if current_dayun_enhanced:
        raw_liunians = current_dayun_enhanced.get('liunians', [])
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        # ⚠️ 不再限制数量，所有流年都显示，按优先级排序
        all_liunians = sorted(cleaned_liunians, key=lambda x: x.get('priority', 999999))
        
        current_dayun_data = {
            'step': str(current_dayun_enhanced.get('step', '')),
            'stem': current_dayun_enhanced.get('gan', current_dayun_enhanced.get('stem', '')),
            'branch': current_dayun_enhanced.get('zhi', current_dayun_enhanced.get('branch', '')),
            'age_display': current_dayun_enhanced.get('age_display', current_dayun_enhanced.get('age_range', '')),
            'main_star': current_dayun_enhanced.get('main_star', ''),
            'priority': current_dayun_enhanced.get('priority', 1),
            'life_stage': current_dayun_enhanced.get('life_stage', ''),
            'description': current_dayun_enhanced.get('description', ''),
            'note': current_dayun_enhanced.get('note', ''),
            'liunians': all_liunians  # ⚠️ 使用全部流年，不限制数量
        }
    
    # 提取关键大运数据（优先级2-10）
    key_dayuns_enhanced = enhanced_dayun_structure.get('key_dayuns', [])
    key_dayuns_data = []
    for key_dayun in key_dayuns_enhanced:
        raw_liunians = key_dayun.get('liunians', [])
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        # ⚠️ 不再限制数量，所有流年都显示，按优先级排序
        all_liunians_for_dayun = sorted(cleaned_liunians, key=lambda x: x.get('priority', 999999))
        
        key_dayuns_data.append({
            'step': str(key_dayun.get('step', '')),
            'stem': key_dayun.get('gan', key_dayun.get('stem', '')),
            'branch': key_dayun.get('zhi', key_dayun.get('branch', '')),
            'age_display': key_dayun.get('age_display', key_dayun.get('age_range', '')),
            'main_star': key_dayun.get('main_star', ''),
            'priority': key_dayun.get('priority', 999),
            'life_stage': key_dayun.get('life_stage', ''),
            'description': key_dayun.get('description', ''),
            'note': key_dayun.get('note', ''),
            'liunians': all_liunians_for_dayun  # ⚠️ 使用全部流年，不限制数量
        })
    
    # 分析大运流年冲合刑害
    chonghe_xinghai = analyze_chonghe_xinghai(bazi_pillars, dayun_sequence, detail_result)
    
    # ⚠️ 使用传入的特殊流年（已在外部通过 BaziDisplayService.get_fortune_display 获取并筛选）
    if special_liunians is None:
        special_liunians = []
    
    # ========== 阶段5：检查 special_liunians 是否正确传递到 build_general_review_input_data ==========
    logger.info(f"[阶段5] ✅ build_general_review_input_data 接收到的 special_liunians 数量: {len(special_liunians)}")
    logger.info(f"[阶段5] 接收到的特殊流年数量: {len(special_liunians)}")
    if special_liunians:
        special_liunian_strs = [f"{l.get('year', '')}年{l.get('ganzhi', '')}" for l in special_liunians[:5]]
        logger.info(f"[阶段5] special_liunians 内容: {special_liunian_strs}")
    else:
        logger.info(f"[阶段5] ⚠️ special_liunians 为空")
    
    # 提取十神对性格的影响
    ten_gods_effect = analyze_ten_gods_effect(ten_gods_data, ten_gods_full)
    
    # 提取健康相关数据
    wuxing_balance = health_result.get('wuxing_balance', {}) if health_result else {}
    zangfu_duiying = health_result.get('body_algorithm', {}) if health_result else {}
    jiankang_ruodian = health_result.get('pathology_tendency', {}) if health_result else {}
    
    # ⚠️ 提取喜忌数据（优先使用 xishen_jishen_result，如果没有则使用 wangshuai_result 作为降级）
    xi_ji_data = extract_xi_ji_data(xishen_jishen_result, wangshuai_result)
    
    # 构建方位选择、行业选择等建议
    # ⚠️ 使用新的喜忌结构
    xishen_wuxing = xi_ji_data.get('xishen_wuxing', [])
    jishen_wuxing = xi_ji_data.get('jishen_wuxing', [])
    fangwei_xuanze = get_directions_from_elements(xishen_wuxing, jishen_wuxing)
    hangye_xuanze = get_industries_from_elements(xishen_wuxing, jishen_wuxing)
    
    # 去掉调候信息（tiaohou）- 不修改底层函数，只在这里去掉
    xi_ji_xishen = xi_ji_data.get('xishen', {})
    xi_ji_jishen = xi_ji_data.get('jishen', {})
    xishen_without_tiaohou = {k: v for k, v in xi_ji_xishen.items() if k != 'tiaohou'}
    jishen_without_tiaohou = {k: v for k, v in xi_ji_jishen.items() if k != 'tiaohou'}
    
    # 构建完整的input_data
    input_data = {
        # 1. 命盘核心格局
        'mingpan_hexin_geju': {
            'day_master': day_pillar,
            'bazi_pillars': bazi_pillars,
            'ten_gods': ten_gods_extracted,  # ⚠️ 使用提取的十神数据
            'wangshuai': wangshuai_str,  # ⚠️ 使用提取的旺衰数据
            'wangshuai_detail': wangshuai_detail_str,  # ⚠️ 使用提取的旺衰详细数据
            'yue_ling': yue_ling,
            'geju_type': geju_type,
            'wuxing_liutong': wuxing_liutong
        },
        
        # 2. 性格特质
        'xingge_tezhi': {
            'day_master_personality': personality_result.get('descriptions', []) if personality_result else [],
            'rizhu_algorithm': rizhu_result.get('analysis', '') if rizhu_result else '',
            'ten_gods_effect': ten_gods_effect
        },
        
        # 3. 事业财运轨迹
        'shiye_caiyun': {
            'shiye_xing': shiye_xing,
            'caifu_xing': caifu_xing,
            'dayun_effect': dayun_effect
        },
        
        # 4. 家庭六亲关系
        'jiating_liuqin': {
            'year_pillar': bazi_pillars.get('year', {}),
            'month_pillar': bazi_pillars.get('month', {}),
            'day_pillar': bazi_pillars.get('day', {}),
            'hour_pillar': bazi_pillars.get('hour', {})
        },
        
        # 5. 健康要点
        'jiankang_yaodian': {
            'wuxing_balance': wuxing_balance,
            'zangfu_duiying': zangfu_duiying,
            'jiankang_ruodian': jiankang_ruodian
        },
        
        # 6. 关键大运与人生节点
        'guanjian_dayun': {
            'current_dayun': current_dayun_data,  # ⚠️ 使用增强的当前大运数据
            'key_dayuns': key_dayuns_data,  # ⚠️ 使用增强的关键大运数据（优先级2-10）
            'dayun_sequence': dayun_sequence,  # ⚠️ 完整的大运序列（保留用于兼容）
            'chonghe_xinghai': chonghe_xinghai
        },
        
        # 7. 终生提点与建议
        'zhongsheng_tidian': {
            'xishen': xishen_without_tiaohou,  # 去掉 tiaohou
            'jishen': jishen_without_tiaohou,  # 去掉 tiaohou（防御性）
            'xishen_wuxing': xi_ji_data.get('xishen_wuxing', []),
            'jishen_wuxing': xi_ji_data.get('jishen_wuxing', []),
            'fangwei_xuanze': fangwei_xuanze,
            'hangye_xuanze': hangye_xuanze,
            'xiushen_jianyi': {},  # 修身建议可以基于格局和性格生成
            'fengshui_tiaojie': {}  # 风水调节可以基于五行平衡生成
        },
        
        # 8. 日柱性命解析（新增：完整的日柱性格与命运分析数据）
        'rizhu_xinming_jiexi': _build_rizhu_xinming_node(day_pillar, gender, personality_result)
    }
    
    # ⚠️ DEBUG: 添加调试信息（用于排查特殊流年问题）
    input_data['_debug'] = {
        'solar_date': solar_date,
        'solar_time': solar_time,
        'gender': gender,
        'dayun_count': len(dayun_sequence),
        'special_liunian_count': len(special_liunians)
    }
    
    return input_data


def extract_xi_ji_data(xishen_jishen_result: Any, wangshuai_result: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    从 xishen_jishen_result 和 wangshuai_result 中提取喜忌数据，并转换为分离的标准格式
    
    ⚠️ 优先使用 xishen_jishen_result（五行）和 wangshuai_result（十神）的组合
    
    Args:
        xishen_jishen_result: get_xishen_jishen() 的返回结果（可能是 XishenJishenResponse 或字典）
        wangshuai_result: 旺衰分析结果（用于获取十神喜忌和调候信息）
    
    Returns:
        dict: 分离的喜忌数据结构
            {
                'xishen': {'shishen': [...], 'wuxing': [...], 'tiaohou': {...}},
                'jishen': {'shishen': [...], 'wuxing': [...]},
                'xishen_wuxing': [...],  # 独立字段
                'jishen_wuxing': [...]   # 独立字段
            }
    """
    # 初始化变量
    xi_shen = []
    ji_shen = []
    xi_shen_elements = []
    ji_shen_elements = []
    tiaohou_info = {}
    
    # 1. 处理 xishen_jishen_result（提取五行）
    if xishen_jishen_result:
        # 支持字典格式（统一接口返回）
        if isinstance(xishen_jishen_result, dict) and 'success' in xishen_jishen_result:
            if xishen_jishen_result.get('success') and xishen_jishen_result.get('data'):
                data = xishen_jishen_result['data']
                
                # 提取五行列表（从带ID的格式转换为纯名称列表）
                xi_shen_elements = [e['name'] for e in data.get('xi_shen_elements', []) if isinstance(e, dict) and 'name' in e]
                ji_shen_elements = [e['name'] for e in data.get('ji_shen_elements', []) if isinstance(e, dict) and 'name' in e]
                
                logger.info(f"✅ [喜忌数据] 从 xishen_jishen_result 提取五行: 喜神={xi_shen_elements}, 忌神={ji_shen_elements}")
        
        # 支持 Pydantic 对象格式
        elif hasattr(xishen_jishen_result, 'success') and xishen_jishen_result.success:
            if xishen_jishen_result.data:
                data = xishen_jishen_result.data
                
                # 提取五行列表
                xi_shen_elements = [e['name'] for e in data.get('xi_shen_elements', []) if isinstance(e, dict) and 'name' in e]
                ji_shen_elements = [e['name'] for e in data.get('ji_shen_elements', []) if isinstance(e, dict) and 'name' in e]
                
                logger.info(f"✅ [喜忌数据] 从 xishen_jishen_result（Pydantic）提取五行: 喜神={xi_shen_elements}, 忌神={ji_shen_elements}")
    
    # 2. 处理 wangshuai_result（提取十神和调候信息）
    if wangshuai_result:
        xi_shen = wangshuai_result.get('xi_shen', [])
        ji_shen = wangshuai_result.get('ji_shen', [])
        
        # 如果五行数据为空，从 wangshuai_result 获取
        if not xi_shen_elements:
            xi_shen_elements = wangshuai_result.get('xi_shen_elements', [])
        if not ji_shen_elements:
            ji_shen_elements = wangshuai_result.get('ji_shen_elements', [])
        
        # 提取调候信息
        final_xi_ji = wangshuai_result.get('final_xi_ji', {})
        if final_xi_ji:
            tiaohou_info = {
                'first_xishen': final_xi_ji.get('first_xi_shen', []) or final_xi_ji.get('first_xishen', []),
                'priority': final_xi_ji.get('tiaohou_priority', ''),
                'description': final_xi_ji.get('analysis', '') or final_xi_ji.get('description', ''),
                'recommendations': final_xi_ji.get('recommendations', [])
            }
        
        logger.info(f"✅ [喜忌数据] 从 wangshuai_result 提取十神: 喜神={xi_shen}, 忌神={ji_shen}")
    
    # 3. 返回分离的喜忌结构
    result = {
        'xishen': {
            'shishen': xi_shen,
            'wuxing': xi_shen_elements,
            'tiaohou': tiaohou_info
        },
        'jishen': {
            'shishen': ji_shen,
            'wuxing': ji_shen_elements
        },
        'xishen_wuxing': xi_shen_elements,  # 独立字段
        'jishen_wuxing': ji_shen_elements   # 独立字段
    }
    
    logger.info(f"✅ [喜忌数据] 返回分离结构: xishen.shishen={len(xi_shen)}, xishen.wuxing={len(xi_shen_elements)}, jishen.shishen={len(ji_shen)}, jishen.wuxing={len(ji_shen_elements)}")
    
    return result


def determine_geju_type(month_branch: str, ten_gods_full: dict, wangshuai_result: dict) -> str:
    """
    判断格局类型
    基于月令和十神配置判断格局类型（正官格、七杀格、正财格、偏财格、食神格、伤官格等）
    """
    try:
        # 从旺衰结果中获取格局类型
        geju = wangshuai_result.get('geju_type', '')
        if geju:
            return geju
        
        # 如果没有，基于月令和十神判断
        month_pillar_ten_gods = ten_gods_full.get('month', {})
        if month_pillar_ten_gods:
            main_star = month_pillar_ten_gods.get('main_star', '')
            if main_star:
                # 基于月柱主星判断格局
                geju_map = {
                    '正官': '正官格',
                    '七杀': '七杀格',
                    '偏官': '七杀格',
                    '正财': '正财格',
                    '偏财': '偏财格',
                    '食神': '食神格',
                    '伤官': '伤官格',
                    '正印': '正印格',
                    '偏印': '偏印格'
                }
                return geju_map.get(main_star, '')
        
        return ''
    except Exception as e:
        logger.warning(f"判断格局类型失败: {e}")
        return ''


def analyze_wuxing_liutong(element_counts: dict, bazi_pillars: dict) -> dict:
    """
    分析五行流通情况
    基于五行统计和生克关系分析五行流通
    """
    try:
        from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
        
        # 五行生克关系
        ELEMENT_RELATIONS = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }
        
        # 统计五行数量
        wuxing_count = {
            '木': element_counts.get('木', 0),
            '火': element_counts.get('火', 0),
            '土': element_counts.get('土', 0),
            '金': element_counts.get('金', 0),
            '水': element_counts.get('水', 0)
        }
        
        # 分析流通情况
        circulation_paths = []
        strong_elements = [e for e, count in wuxing_count.items() if count >= 2]
        weak_elements = [e for e, count in wuxing_count.items() if count == 0]
        
        # 分析主要流通路径
        for element in ['木', '火', '土', '金', '水']:
            if wuxing_count[element] > 0:
                produces = ELEMENT_RELATIONS[element]['produces']
                if wuxing_count[produces] > 0:
                    circulation_paths.append(f"{element}生{produces}")
        
        summary = ""
        if strong_elements:
            summary += f"强旺五行：{'、'.join(strong_elements)}；"
        if weak_elements:
            summary += f"缺失五行：{'、'.join(weak_elements)}；"
        if circulation_paths:
            summary += f"流通路径：{'、'.join(circulation_paths[:3])}"
        
        return {
            'wuxing_count': wuxing_count,
            'strong_elements': strong_elements,
            'weak_elements': weak_elements,
            'circulation_paths': circulation_paths,
            'summary': summary
        }
    except Exception as e:
        logger.warning(f"分析五行流通失败: {e}")
        return {}


def extract_career_star(ten_gods_stats: dict) -> dict:
    """
    提取事业星信息
    事业星：正官、七杀、正印、偏印
    """
    result = {
        'primary': '',
        'secondary': '',
        'positions': [],
        'strength': '',
        'description': ''
    }
    
    zhengguan = ten_gods_stats.get('正官', 0)
    qisha = ten_gods_stats.get('七杀', 0) + ten_gods_stats.get('偏官', 0)
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


def analyze_dayun_effect(dayun_sequence: List[dict], shiye_xing: dict, caifu_xing: dict, ten_gods_stats: dict) -> dict:
    """
    分析大运对事业财运的影响
    
    ⚠️ 包含所有大运阶段（至少前7步），确保不遗漏任何大运
    """
    try:
        result = {
            'career_effects': [],
            'wealth_effects': [],
            'all_dayuns': [],  # ⚠️ 新增：包含所有大运的完整信息
            'summary': ''
        }
        
        # ⚠️ 分析所有大运（至少前7步，确保不遗漏）
        max_steps = min(7, len(dayun_sequence))
        for idx in range(max_steps):
            if idx < len(dayun_sequence):
                dayun = dayun_sequence[idx]
                main_star = dayun.get('main_star', '')
                step = dayun.get('step', idx + 1)
                age_display = dayun.get('age_display', '')
                stem = dayun.get('stem', '')
                branch = dayun.get('branch', '')
                
                # ⚠️ 添加所有大运的完整信息
                dayun_info = {
                    'step': step,
                    'age_display': age_display,
                    'stem': stem,
                    'branch': branch,
                    'ganzhi': f"{stem}{branch}",
                    'main_star': main_star,
                    'year_start': dayun.get('year_start', 0),
                    'year_end': dayun.get('year_end', 0)
                }
                result['all_dayuns'].append(dayun_info)
                
                # 分析事业影响（所有大运都检查，不只是第2-4步）
                if main_star in ['正官', '七杀', '偏官', '正印', '偏印']:
                    result['career_effects'].append({
                        'step': step,
                        'age_display': age_display,
                        'main_star': main_star,
                        'ganzhi': f"{stem}{branch}",
                        'effect': f"第{step}步大运（{age_display}）主星为{main_star}，对事业有重要影响"
                    })
                
                # 分析财运影响（所有大运都检查，不只是第2-4步）
                if main_star in ['正财', '偏财', '食神', '伤官']:
                    result['wealth_effects'].append({
                        'step': step,
                        'age_display': age_display,
                        'main_star': main_star,
                        'ganzhi': f"{stem}{branch}",
                        'effect': f"第{step}步大运（{age_display}）主星为{main_star}，对财运有重要影响"
                    })
        
        # 生成摘要
        if result['career_effects']:
            result['summary'] += f"事业关键大运：{len(result['career_effects'])}步；"
        if result['wealth_effects']:
            result['summary'] += f"财运关键大运：{len(result['wealth_effects'])}步"
        
        logger.info(f"[大运分析] 共分析 {len(result['all_dayuns'])} 个大运阶段，事业影响 {len(result['career_effects'])} 步，财运影响 {len(result['wealth_effects'])} 步")
        
        return result
    except Exception as e:
        logger.warning(f"分析大运对事业财运的影响失败: {e}")
        return {}


def analyze_chonghe_xinghai(bazi_pillars: dict, dayun_sequence: List[dict], detail_result: dict) -> dict:
    """
    分析大运流年冲合刑害
    """
    try:
        result = {
            'bazi_internal_relations': {},
            'dayun_liunian_relations': [],
            'summary': ''
        }
        
        # 分析八字内部冲合刑害（使用静态方法）
        internal_relations = FortuneRelationAnalyzer._analyze_internal_relations(bazi_pillars)
        result['bazi_internal_relations'] = internal_relations
        
        # 分析大运与流年的关系（需要进一步实现）
        # 这里可以基于detail_result中的流年数据进行分析
        
        # 生成摘要
        if internal_relations.get('chong_details'):
            result['summary'] += f"冲：{len(internal_relations['chong_details'])}处；"
        if internal_relations.get('he_details'):
            result['summary'] += f"合：{len(internal_relations['he_details'])}处；"
        if internal_relations.get('xing_details'):
            result['summary'] += f"刑：{len(internal_relations['xing_details'])}处"
        
        return result
    except Exception as e:
        logger.warning(f"分析大运流年冲合刑害失败: {e}")
        return {}


def analyze_ten_gods_effect(ten_gods_stats: dict, ten_gods_full: dict) -> dict:
    """
    分析十神对性格的影响
    """
    try:
        result = {
            'effects': [],
            'summary': ''
        }
        
        # 基于十神配置分析性格特征
        dominant_gods = []
        for god, count in ten_gods_stats.items():
            if count >= 2:
                dominant_gods.append(god)
        
        # 十神性格特征映射
        personality_map = {
            '正官': '稳重、有责任感、遵守规则',
            '七杀': '果断、有魄力、勇于挑战',
            '正印': '温和、有爱心、乐于助人',
            '偏印': '独立思考、有创意、内向',
            '正财': '务实、节俭、重视物质',
            '偏财': '灵活、善于理财、敢于投资',
            '食神': '温和、有才华、喜欢享受',
            '伤官': '聪明、有才华、个性张扬',
            '比肩': '独立、自信、有主见',
            '劫财': '冲动、好胜、有竞争力'
        }
        
        effects = []
        for god in dominant_gods:
            if god in personality_map:
                effects.append(f"{god}：{personality_map[god]}")
        
        result['effects'] = effects
        if effects:
            result['summary'] = '、'.join(effects)
        
        return result
    except Exception as e:
        logger.warning(f"分析十神对性格的影响失败: {e}")
        return {}


def get_directions_from_elements(xi_elements: List[str], ji_elements: List[str]) -> dict:
    """根据喜忌五行获取方位建议"""
    ELEMENT_DIRECTION = {
        '木': '东方',
        '火': '南方',
        '土': '中央',
        '金': '西方',
        '水': '北方'
    }
    
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


def validate_general_review_input_data(data: dict) -> Tuple[bool, str]:
    """
    验证输入数据完整性（阶段3：数据验证与完整性检查）
    
    Args:
        data: 输入数据字典
        
    Returns:
        (is_valid, error_message): 是否有效，错误信息（如果无效）
    """
    required_fields = {
        'mingpan_hexin_geju': {
            'bazi_pillars': '八字排盘',
            'day_master': '日主信息',
            'ten_gods': '十神配置',
            'wangshuai': '旺衰分析'
        },
        'xingge_tezhi': {
            # 性格特质部分允许部分为空
        },
        'shiye_caiyun': {
            # 事业财运部分允许部分为空
        },
        'jiating_liuqin': {
            'year_pillar': '年柱',
            'month_pillar': '月柱',
            'day_pillar': '日柱',
            'hour_pillar': '时柱'
        },
        'jiankang_yaodian': {
            # 健康要点部分允许部分为空
        },
        'guanjian_dayun': {
            'key_dayuns': '关键大运列表'  # ⚠️ 已改为 key_dayuns（优先级2-10）
        },
        'zhongsheng_tidian': {
            'xishen': '喜神数据',
            'jishen': '忌神数据'
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

# ✅ _simplify_dayun 和 format_input_data_for_coze 函数已移至 server/utils/prompt_builders.py
# 通过顶部 import 导入，确保评测脚本和流式接口使用相同的函数

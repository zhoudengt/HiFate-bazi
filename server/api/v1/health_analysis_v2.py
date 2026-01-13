#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-身体健康分析API (V2)
基于用户生辰数据，使用 Coze Bot 流式生成健康分析
按照总评分析的统一接口、一级接口、二级接口架构开发
"""

import logging
import os
import sys
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
from server.services.health_analysis_service import HealthAnalysisService
from server.services.special_liunian_service import SpecialLiunianService
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.bazi_data_orchestrator import BaziDataOrchestrator

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
from server.api.v1.general_review_analysis import (
    classify_special_liunians,
    organize_special_liunians_by_dayun,
    extract_xi_ji_data
)
from server.utils.dayun_liunian_helper import (
    calculate_user_age,
    get_current_dayun,
    build_enhanced_dayun_structure
)

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class HealthAnalysisV2Request(BaseModel):
    """身体健康分析请求模型（V2）"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量配置）")


@router.post("/health-analysis-v2/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def health_analysis_v2_test(request: HealthAnalysisV2Request):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        request: 健康分析请求参数
        
    Returns:
        dict: 包含格式化后的数据
    """
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, "solar", None, None, None
        )
        
        # 使用统一接口获取数据
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True,
            'health': True,
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
            calendar_type="solar",
            location=None,
            latitude=None,
            longitude=None
        )
        
        # 从统一接口结果中提取数据
        bazi_data = unified_data.get('bazi', {})
        wangshuai_result = unified_data.get('wangshuai', {})
        detail_result = unified_data.get('detail', {})
        health_result = unified_data.get('health', {})
        special_liunians = unified_data.get('special_liunians', {}).get('list', [])
        
        # 提取和验证数据
        if isinstance(bazi_data, dict) and 'bazi' in bazi_data:
            bazi_data = bazi_data['bazi']
        bazi_data = validate_bazi_data(bazi_data)
        
        # 获取大运序列（从detail_result）
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # 构建input_data
        input_data = build_health_analysis_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            request.gender,
            final_solar_date,
            final_solar_time,
            health_result,
            special_liunians,
            None  # xishen_jishen_result
        )
        
        # 格式化数据
        formatted_data = format_input_data_for_coze(input_data)
        
        return {
            "success": True,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_tizhi_zonglun', {}).get('bazi_pillars', {}),
                "dayun_count": len(input_data.get('dayun_jiankang', {}).get('key_dayuns', [])),
                "current_dayun_liunians_count": len(input_data.get('dayun_jiankang', {}).get('current_dayun', {}).get('liunians', []) if input_data.get('dayun_jiankang', {}).get('current_dayun') else []),
                "key_dayuns_count": len(input_data.get('dayun_jiankang', {}).get('key_dayuns', [])),
                "xi_ji": input_data.get('tizhi_tiaoli', {}).get('xi_ji', {})
            },
            "usage": {
                "description": "此接口返回的数据可以直接用于 Coze Bot 的 {{input}} 占位符",
                "coze_bot_setup": "1. 登录 Coze 平台\n2. 找到'身体健康分析' Bot\n3. 进入 Bot 设置 → System Prompt\n4. 复制 docs/需求/Coze_Bot_System_Prompt_身体健康分析.md 中的提示词\n5. 粘贴到 System Prompt 中\n6. 保存设置",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/health-analysis-v2/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}"}}\''
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


@router.post("/health-analysis-v2/stream", summary="流式生成健康分析（V2）")
async def health_analysis_v2_stream(request: HealthAnalysisV2Request):
    """
    流式生成健康分析（V2版本）
    
    按照总评分析的架构：
    - 统一接口：BaziDataOrchestrator.fetch_data()
    - 一级接口：health_analysis_v2_stream_generator()
    - 二级接口：build_health_analysis_input_data()
    
    Args:
        request: 健康分析请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    return StreamingResponse(
        health_analysis_v2_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.bot_id
        ),
        media_type="text/event-stream"
    )


async def health_analysis_v2_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """流式生成健康分析的生成器（一级接口）"""
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > 数据库配置）
        used_bot_id = bot_id
        if not used_bot_id:
            # 只从数据库读取，不降级到环境变量
            used_bot_id = get_config_from_db_only("HEALTH_ANALYSIS_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "数据库配置缺失: HEALTH_ANALYSIS_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"健康分析请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={used_bot_id}")
        
        # 2. 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, "solar", None, None, None
        )
        
        # 3. 使用统一接口获取数据（阶段2：数据获取与并行优化）
        try:
            # 构建统一接口的 modules 配置
            modules = {
                'bazi': True,
                'wangshuai': True,
                'xishen_jishen': True,
                'detail': True,
                'dayun': {
                    'mode': 'indices',
                    'indices': [1, 2, 3]  # 第2-4步大运
                },
                'special_liunians': {
                    'dayun_config': {
                        'mode': 'indices',
                        'indices': [1, 2, 3]  # 与dayun一致
                    },
                    'count': 100
                },
                'health': True
            }
            
            logger.info(f"[Health Analysis V2 Stream] 开始调用统一接口获取数据")
            unified_data = await BaziDataOrchestrator.fetch_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                modules=modules,
                use_cache=True,
                parallel=True,
                calendar_type=request.calendar_type if hasattr(request, 'calendar_type') else "solar",
                location=request.location if hasattr(request, 'location') else None,
                latitude=request.latitude if hasattr(request, 'latitude') else None,
                longitude=request.longitude if hasattr(request, 'longitude') else None
            )
            logger.info(f"[Health Analysis V2 Stream] ✅ 统一接口数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[Health Analysis V2 Stream] ❌ 统一接口调用失败: {e}\n{error_msg}")
            error_response = {
                'type': 'error',
                'content': f"数据获取失败: {str(e)}。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 4. 从统一接口返回的数据中提取所需字段
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            bazi_data = bazi_module_data.get('bazi', {})
        else:
            bazi_data = bazi_module_data
        
        wangshuai_result = unified_data.get('wangshuai', {})
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        detail_data = unified_data.get('detail', {})
        health_result = unified_data.get('health', {})
        
        # 处理 xishen_jishen_result（可能是 Pydantic 模型，需要转换为字典）
        if xishen_jishen_result and hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif xishen_jishen_result and hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        # 验证八字数据
        bazi_data = validate_bazi_data(bazi_data)
        
        # 提取大运序列和流年序列
        if detail_data:
            details = detail_data.get('details', detail_data)
            dayun_sequence = details.get('dayun_sequence', [])
            liunian_sequence = details.get('liunian_sequence', [])
        else:
            dayun_sequence = unified_data.get('dayun', [])
            liunian_sequence = unified_data.get('liunian', [])
        
        logger.info(f"[Health Analysis V2 Stream] 获取到 dayun_sequence 数量: {len(dayun_sequence)}")
        
        # 提取特殊流年（统一接口返回的是字典格式，包含 'list', 'by_dayun', 'formatted'）
        special_liunians_data = unified_data.get('special_liunians', {})
        if isinstance(special_liunians_data, dict):
            special_liunians = special_liunians_data.get('list', [])
        elif isinstance(special_liunians_data, list):
            special_liunians = special_liunians_data
        else:
            special_liunians = []
        
        logger.info(f"[Health Analysis V2 Stream] 获取到特殊流年数量: {len(special_liunians)}")
        
        # 构建 detail_result（用于 build_health_analysis_input_data）
        detail_result = detail_data if detail_data else {
            'details': {
                'dayun_sequence': dayun_sequence,
                'liunian_sequence': liunian_sequence
            }
        }
        
        # 5. 调用二级接口构建输入数据（阶段3：数据验证与完整性检查）
        input_data = build_health_analysis_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=gender,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            health_result=health_result,
            special_liunians=special_liunians,
            xishen_jishen_result=xishen_jishen_result
        )
        
        # 6. 验证数据完整性（阶段3：数据验证与完整性检查）
        is_valid, validation_error = validate_health_analysis_input_data(input_data)
        if not is_valid:
            error_msg = {
                'type': 'error',
                'content': f"数据完整性验证失败: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 7. ⚠️ 方案2：格式化数据为 Coze Bot 输入格式
        formatted_data = format_input_data_for_coze(input_data)
        logger.info(f"[Health Analysis V2 Stream] 格式化数据长度: {len(formatted_data)} 字符")
        logger.debug(f"[Health Analysis V2 Stream] 格式化数据前500字符: {formatted_data[:500]}")
        
        # 8. 调用 LLM API（阶段5：LLM API调用，支持 Coze 和百炼平台）
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            llm_service = LLMServiceFactory.get_service(scene="health", bot_id=used_bot_id)
            async for chunk in llm_service.stream_analysis(formatted_data, bot_id=used_bot_id):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                if chunk.get('type') in ['complete', 'error']:
                    break
                    
        except ValueError as e:
            # 配置错误
            error_msg = {
                'type': 'error',
                'content': f"Coze API 配置缺失: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            # 其他错误
            import traceback
            error_msg = {
                'type': 'error',
                'content': f"Coze API 调用失败: {str(e)}"
            }
            logger.error(f"[Health Analysis V2 Stream] Coze API 调用失败: {e}\n{traceback.format_exc()}")
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"健康分析流式生成失败: {e}\n{error_trace}")
        error_msg = {
            'type': 'error',
            'content': f"处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


def build_health_analysis_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    gender: str,
    solar_date: str = None,
    solar_time: str = None,
    health_result: Dict[str, Any] = None,
    special_liunians: List[Dict[str, Any]] = None,
    xishen_jishen_result: Any = None
) -> Dict[str, Any]:
    """
    构建健康分析的输入数据（二级接口）
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        gender: 性别（male/female）
        solar_date: 原始阳历日期
        solar_time: 原始阳历时间
        health_result: 健康分析结果
        special_liunians: 特殊流年列表（已筛选）
        xishen_jishen_result: 喜忌数据结果（XishenJishenResponse）
        
    Returns:
        dict: 健康分析的input_data
    """
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
    
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    day_pillar = bazi_pillars.get('day', {})
    element_counts = bazi_data.get('element_counts', {})
    
    # ⚠️ 修复：从 wangshuai_result 中正确提取旺衰数据
    wangshuai_data_dict = extract_wangshuai_data(wangshuai_result)
    wangshuai_data = wangshuai_data_dict.get('wangshuai', '') if isinstance(wangshuai_data_dict, dict) else str(wangshuai_data_dict) if wangshuai_data_dict else ''
    
    # ⚠️ 修复：从 detail_result 或 bazi_data 中提取十神数据
    ten_gods_data = extract_ten_gods_data(detail_result, bazi_data)
    ten_gods_stats = bazi_data.get('ten_gods_stats', {})
    
    # 提取月令
    month_pillar = bazi_pillars.get('month', {})
    month_branch = month_pillar.get('branch', '')
    yue_ling = f"{month_branch}月" if month_branch else ''
    
    # 提取健康相关数据
    wuxing_balance = health_result.get('wuxing_balance', '') if health_result else ''
    body_algorithm = health_result.get('body_algorithm', {}) if health_result else {}
    pathology_tendency = health_result.get('pathology_tendency', {}) if health_result else {}
    wuxing_tuning = health_result.get('wuxing_tuning', {}) if health_result else {}
    zangfu_care = health_result.get('zangfu_care', {}) if health_result else {}
    
    # 提取五行生克关系
    wuxing_relations = pathology_tendency.get('wuxing_relations', {}) if pathology_tendency else {}
    
    # ⚠️ 修复：从 wangshuai_result 中提取喜忌数据
    xi_ji_data = extract_xi_ji_data(xishen_jishen_result, wangshuai_result)
    
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
        """清理流年数据：移除流月流日字段"""
        cleaned = liunian.copy()
        fields_to_remove = ['liuyue_sequence', 'liuri_sequence', 'liushi_sequence']
        for field in fields_to_remove:
            cleaned.pop(field, None)
        return cleaned
    
    def limit_liunians_by_priority(liunians: List[Dict[str, Any]], max_count: int = 3) -> List[Dict[str, Any]]:
        """限制流年数量：只保留优先级最高的N个（已按优先级排序）"""
        if not liunians:
            return []
        return liunians[:max_count]
    
    # 提取当前大运数据（优先级1）
    current_dayun_enhanced = enhanced_dayun_structure.get('current_dayun')
    current_dayun_data = None
    if current_dayun_enhanced:
        raw_liunians = current_dayun_enhanced.get('liunians', [])
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        limited_liunians = limit_liunians_by_priority(cleaned_liunians, max_count=3)
        
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
            'liunians': limited_liunians
        }
    
    # 提取关键大运数据（优先级2-10）
    key_dayuns_enhanced = enhanced_dayun_structure.get('key_dayuns', [])
    key_dayuns_data = []
    for key_dayun in key_dayuns_enhanced:
        raw_liunians = key_dayun.get('liunians', [])
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        limited_liunians = limit_liunians_by_priority(cleaned_liunians, max_count=3)
        
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
            'liunians': limited_liunians
        })
    
    # 构建完整的input_data
    input_data = {
        # 1. 命盘体质总论
        'mingpan_tizhi_zonglun': {
            'day_master': day_pillar,
            'bazi_pillars': bazi_pillars,
            'elements': element_counts,
            'wangshuai': wangshuai_data,
            'yue_ling': yue_ling,
            'wuxing_balance': wuxing_balance
        },
        
        # 2. 五行病理推演
        'wuxing_bingli': {
            'wuxing_shengke': wuxing_relations,
            'body_algorithm': body_algorithm,
            'pathology_tendency': pathology_tendency
        },
        
        # 3. 大运流年健康警示
        'dayun_jiankang': {
            'current_dayun': current_dayun_data,
            'key_dayuns': key_dayuns_data,  # 关键大运（优先级2-10）
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


def validate_health_analysis_input_data(data: dict) -> tuple[bool, str]:
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
            'dayun_list': '大运流年列表',
            'dayun_liunians': '按大运分组的流年'
        },
        'tizhi_tiaoli': {
            'xi_ji': '喜忌数据',
            'wuxing_tiaohe': '五行调和方案',
            'zangfu_yanghu': '脏腑养护建议'
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


def build_health_analysis_prompt(data: dict) -> str:
    """
    构建自然语言格式的提示词（阶段4：Prompt构建）
    将JSON数据转换为自然语言格式，确保 Coze Bot 能正确理解
    """
    prompt_lines = []
    # ⚠️ 注意：代码中只提供数据，不包含任何提示词或指令
    # 提示词必须在 Coze Bot 中配置
    
    # 1. 命盘体质总论
    prompt_lines.append("【命盘体质总论】")
    mingpan = data.get('mingpan_tizhi_zonglun', {})
    
    day_master = mingpan.get('day_master', {})
    if day_master:
        stem = day_master.get('stem', '')
        branch = day_master.get('branch', '')
        element = day_master.get('element', '')
        if stem and branch:
            prompt_lines.append(f"日主：{stem}{branch}（{element}）")
    
    bazi_pillars = mingpan.get('bazi_pillars', {})
    if bazi_pillars:
        prompt_lines.append("四柱排盘：")
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            stem = pillar.get('stem', '')
            branch = pillar.get('branch', '')
            if stem and branch:
                pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
                prompt_lines.append(f"  {pillar_name}：{stem}{branch}")
    
    elements = mingpan.get('elements', {})
    if elements:
        prompt_lines.append("五行分布：")
        for element, count in elements.items():
            if count > 0:
                prompt_lines.append(f"  {element}：{count}个")
    
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        prompt_lines.append(f"旺衰：{wangshuai}")
    
    yue_ling = mingpan.get('yue_ling', '')
    if yue_ling:
        prompt_lines.append(f"月令：{yue_ling}")
    
    wuxing_balance = mingpan.get('wuxing_balance', '')
    if wuxing_balance:
        prompt_lines.append(f"全局五行平衡：{wuxing_balance}")
    
    prompt_lines.append("")
    
    # 2. 五行病理推演
    prompt_lines.append("【五行病理推演】")
    wuxing_bingli = data.get('wuxing_bingli', {})
    
    wuxing_shengke = wuxing_bingli.get('wuxing_shengke', {})
    if wuxing_shengke:
        relations = wuxing_shengke.get('relations', [])
        if relations:
            prompt_lines.append("五行生克关系：")
            for relation in relations:
                organ = relation.get('organ', '')
                issue = relation.get('issue', '')
                risk = relation.get('risk', '')
                if organ and issue:
                    prompt_lines.append(f"  {organ}：{issue}，{risk}")
    
    body_algorithm = wuxing_bingli.get('body_algorithm', {})
    if body_algorithm:
        organ_analysis = body_algorithm.get('organ_analysis', {})
        if organ_analysis:
            prompt_lines.append("五脏对应：")
            for organ, analysis in organ_analysis.items():
                element = analysis.get('element', '')
                strength = analysis.get('strength', '')
                health_status = analysis.get('health_status', '')
                if element and strength:
                    prompt_lines.append(f"  {organ}（{element}）：{strength}，{health_status}")
    
    pathology_tendency = wuxing_bingli.get('pathology_tendency', {})
    if pathology_tendency:
        pathology_list = pathology_tendency.get('pathology_list', [])
        if pathology_list:
            prompt_lines.append("病理倾向：")
            for pathology in pathology_list:
                organ = pathology.get('organ', '')
                tendency = pathology.get('tendency', '')
                risk = pathology.get('risk', '')
                if organ and tendency:
                    prompt_lines.append(f"  {organ}：{tendency}，{risk}")
    
    prompt_lines.append("")
    
    # 3. 大运流年健康警示
    prompt_lines.append("【大运流年健康警示】")
    dayun_jiankang = data.get('dayun_jiankang', {})
    
    # 当前大运
    current_dayun = dayun_jiankang.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        age_display = current_dayun.get('age_display', '')
        if stem and branch:
            prompt_lines.append(f"当前大运：{stem}{branch}（{age_display}）")
    
    # 关键大运列表（第2-4步）
    dayun_list = dayun_jiankang.get('dayun_list', [])
    if dayun_list:
        prompt_lines.append("关键大运（第2-4步）：")
        for dayun in dayun_list:
            step = dayun.get('step', '')
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            age_display = dayun.get('age_display', '')
            if stem and branch:
                prompt_lines.append(f"  第{step}步大运：{stem}{branch}（{age_display}）")
    
    # 每个大运下的关键流年（最多2条，按优先级）
    dayun_liunians = dayun_jiankang.get('dayun_liunians', {})
    if dayun_liunians:
        prompt_lines.append("关键流年健康风险：")
        
        # 获取完整的大运序列（用于格式化）
        dayun_sequence_for_format = dayun_list if dayun_list else []
        
        # 按大运步骤排序
        sorted_dayun_steps = sorted([int(k) for k in dayun_liunians.keys() if isinstance(k, (int, str)) and str(k).isdigit()])
        
        for dayun_step in sorted_dayun_steps:
            dayun_data = dayun_liunians.get(dayun_step, {})
            if not dayun_data:
                continue
            
            dayun_info = dayun_data.get('dayun_info', {})
            key_liunians = dayun_data.get('key_liunian', [])
            
            if key_liunians:
                step = dayun_info.get('step', dayun_step)
                stem = dayun_info.get('stem', '')
                branch = dayun_info.get('branch', '')
                age_display = dayun_info.get('age_display', '')
                
                prompt_lines.append(f"第{step}步大运{stem}{branch}（{age_display}）关键流年：")
                
                # 使用 SpecialLiunianService.format_special_liunians_for_prompt 格式化
                formatted = SpecialLiunianService.format_special_liunians_for_prompt(
                    key_liunians, dayun_sequence_for_format
                )
                if formatted:
                    prompt_lines.append(formatted)
                else:
                    # 如果格式化失败，至少列出年份和干支
                    for liunian in key_liunians:
                        year = liunian.get('year', '')
                        ganzhi = liunian.get('ganzhi', '')
                        relations = liunian.get('relations', [])
                        if year and ganzhi:
                            relation_str = ''
                            if relations:
                                if isinstance(relations[0], dict):
                                    relation_str = '、'.join([r.get('type', '') for r in relations])
                                else:
                                    relation_str = '、'.join([str(r) for r in relations])
                            if relation_str:
                                prompt_lines.append(f"  - {year}年{ganzhi}（{relation_str}）")
                            else:
                                prompt_lines.append(f"  - {year}年{ganzhi}")
    
    # 十神配置
    ten_gods = dayun_jiankang.get('ten_gods', {})
    if ten_gods:
        prompt_lines.append("十神配置：")
        for shishen, count in ten_gods.items():
            if count > 0:
                prompt_lines.append(f"  {shishen}：{count}个")
    
    prompt_lines.append("")
    
    # 4. 体质调理建议
    prompt_lines.append("【体质调理建议】")
    tizhi_tiaoli = data.get('tizhi_tiaoli', {})
    
    xi_ji = tizhi_tiaoli.get('xi_ji', {})
    if xi_ji:
        xishen_wuxing = xi_ji.get('xishen_wuxing', [])
        jishen_wuxing = xi_ji.get('jishen_wuxing', [])
        
        if xishen_wuxing:
            prompt_lines.append(f"喜神五行：{'、'.join(xishen_wuxing)}")
        else:
            prompt_lines.append("喜神五行：无")
        
        if jishen_wuxing:
            prompt_lines.append(f"忌神五行：{'、'.join(jishen_wuxing)}")
        else:
            prompt_lines.append("忌神五行：无")
    
    wuxing_tiaohe = tizhi_tiaoli.get('wuxing_tiaohe', {})
    if wuxing_tiaohe:
        tuning_suggestions = wuxing_tiaohe.get('tuning_suggestions', [])
        if tuning_suggestions:
            prompt_lines.append("五行调和方案：")
            for tuning in tuning_suggestions:
                element = tuning.get('element', '')
                organ = tuning.get('organ', '')
                direction = tuning.get('direction', '')
                reason = tuning.get('reason', '')
                if element and organ:
                    prompt_lines.append(f"  {element}（{organ}）：{direction}，{reason}")
    
    zangfu_yanghu = tizhi_tiaoli.get('zangfu_yanghu', {})
    if zangfu_yanghu:
        care_suggestions = zangfu_yanghu.get('care_suggestions', [])
        if care_suggestions:
            prompt_lines.append("脏腑养护建议：")
            for care in care_suggestions:
                organ = care.get('organ', '')
                priority = care.get('priority', '')
                care_focus = care.get('care_focus', '')
                suggestions = care.get('suggestions', [])
                if organ:
                    prompt_lines.append(f"  {organ}（优先级：{priority}，重点：{care_focus}）：")
                    for suggestion in suggestions[:3]:  # 最多显示3条建议
                        prompt_lines.append(f"    - {suggestion}")
    
    return '\n'.join(prompt_lines)


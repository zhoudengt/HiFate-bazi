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

from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.bazi_service import BaziService
from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_detail_service import BaziDetailService
from server.services.rule_service import RuleService
from server.services.health_analysis_service import HealthAnalysisService
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.coze_stream_service import CozeStreamService

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
from server.utils.prompt_builders import (
    format_health_input_data_for_coze as format_input_data_for_coze,
    format_health_for_llm
)
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.services.stream_call_logger import get_stream_call_logger
import time

# ✅ 性能优化：导入流式缓存工具
from server.utils.stream_cache_helper import (
    get_llm_cache, set_llm_cache,
    compute_input_data_hash, LLM_CACHE_TTL
)

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
            request.solar_date, request.solar_time, request.calendar_type or "solar",
            request.location, request.latitude, request.longitude
        )
        
        # 通过 BaziDataOrchestrator 统一获取数据（主路径统一）
        from server.utils.analysis_stream_helpers import get_modules_config
        modules = get_modules_config('health')
        unified_data = await BaziDataOrchestrator.fetch_data(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            modules=modules,
            use_cache=True,
            parallel=True,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            preprocessed=True
        )
        
        # 提取数据
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            bazi_data = bazi_module_data.get('bazi', {})
        else:
            bazi_data = bazi_module_data
        bazi_data = validate_bazi_data(bazi_data)
        
        wangshuai_result = unified_data.get('wangshuai', {})
        if isinstance(wangshuai_result, dict) and wangshuai_result.get('success'):
            wangshuai_data = wangshuai_result.get('data', {})
        else:
            wangshuai_data = wangshuai_result if isinstance(wangshuai_result, dict) else {}
        
        detail_result = unified_data.get('detail', {})
        dayun_sequence = detail_result.get('dayun_sequence', [])
        special_liunians_data = unified_data.get('special_liunians', {})
        special_liunians = special_liunians_data.get('list', []) if isinstance(special_liunians_data, dict) else []
        health_rules = unified_data.get('rules', [])
        
        element_counts = bazi_data.get('element_counts', {})
        xi_ji_data_for_health_debug = {
            'xi_ji_elements': {
                'xi_shen': wangshuai_data.get('xi_shen_elements', []),
                'ji_shen': wangshuai_data.get('ji_shen_elements', [])
            }
        }
        
        loop = asyncio.get_event_loop()
        executor = None
        health_result = await loop.run_in_executor(
            executor,
            lambda: HealthAnalysisService.analyze(
                bazi_data, element_counts, wangshuai_data, xi_ji_data_for_health_debug
            )
        )
        
        # 构建input_data（直接使用硬编码函数，确保数据完整性）
        # ⚠️ 重要：使用 wangshuai_data（提取后的数据），而不是 wangshuai_result（原始结果）
        input_data = build_health_input_data(
            bazi_data,
            wangshuai_data,
            detail_result,
            dayun_sequence,
            health_result if health_result.get('success') else {},
            request.gender,
            special_liunians=special_liunians  # ✅ 添加特殊流年数据
        )
        logger.info("✅ 使用硬编码函数构建 input_data: health_analysis")
        
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
        
        # ✅ 只返回 input_data，评测脚本使用相同的函数构建 prompt
        return {
            "success": True,
            "input_data": input_data,
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_tizhi_zonglun', {}).get('bazi_pillars', {}),
                "health_rules_count": len(input_data.get('health_rules', {}).get('matched_rules', [])),
                "dayun_count": len(input_data.get('dayun_jiankang', {}).get('all_dayuns', [])),
                "current_dayun": input_data.get('dayun_jiankang', {}).get('current_dayun'),
                "key_dayuns_count": len(input_data.get('dayun_jiankang', {}).get('key_dayuns', [])),
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
        # ✅ 性能优化：立即返回首条消息，让用户感知到连接已建立
        # 这个优化将首次响应时间从 24秒 降低到 <1秒
        # ✅ 架构优化：移除无意义的进度消息，直接开始数据处理
        # 详见：standards/08_数据编排架构规范.md
        
        # 1. Bot ID 配置检查（优先级：参数 > 数据库配置 > 环境变量）
        used_bot_id = bot_id
        if not used_bot_id:
            # 优先级：数据库配置 > 环境变量
            used_bot_id = get_config_from_db_only("HEALTH_ANALYSIS_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "数据库配置缺失: HEALTH_ANALYSIS_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置"
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
            modules = get_modules_config('health')
            
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
            
            # 提取旺衰数据
            wangshuai_result = unified_data.get('wangshuai', {})
            if isinstance(wangshuai_result, dict) and wangshuai_result.get('success'):
                wangshuai_data = wangshuai_result.get('data', {})
            else:
                wangshuai_data = wangshuai_result if isinstance(wangshuai_result, dict) else {}
            
            if not wangshuai_result.get('success', True):
                logger.warning(f"旺衰分析失败: {wangshuai_result.get('error')}")
            
            # 提取 detail（BaziDetailService 返回的完整结构）
            detail_result = unified_data.get('detail', {})
            if not detail_result:
                raise ValueError("详细数据获取失败，无法继续分析")
            
            # 提取大运序列和特殊流年
            dayun_sequence = detail_result.get('dayun_sequence', [])
            special_liunians_data = unified_data.get('special_liunians', {})
            if isinstance(special_liunians_data, dict) and 'list' in special_liunians_data:
                special_liunians = special_liunians_data.get('list', [])
            else:
                special_liunians = []
            
            # 提取健康规则（由编排层 rules 模块返回）
            health_rules = unified_data.get('rules', [])
            
            logger.info(f"[Health Analysis Stream] ✅ BaziDataOrchestrator 数据获取完成")
            
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
        # ⚠️ 重要：使用 wangshuai_data（提取后的数据），而不是 wangshuai_result（原始结果）
        # ⚠️ 修复：构建正确的 xi_ji_data 结构
        # wangshuai_data 中的字段是 xi_shen_elements 和 ji_shen_elements（列表格式）
        # HealthAnalysisService.analyze() 期望的 xi_ji_data 结构是：
        # {'xi_ji_elements': {'xi_shen': [...], 'ji_shen': [...]}}
        xi_ji_data_for_health = {
            'xi_ji_elements': {
                'xi_shen': wangshuai_data.get('xi_shen_elements', []),
                'ji_shen': wangshuai_data.get('ji_shen_elements', [])
            }
        }
        logger.info(f"[Health Analysis] xi_ji_data_for_health 构建完成: xi_shen={xi_ji_data_for_health['xi_ji_elements']['xi_shen']}, ji_shen={xi_ji_data_for_health['xi_ji_elements']['ji_shen']}")
        
        # 6. 执行健康分析（HealthAnalysisService 需 bazi_data 等，编排层未封装此依赖，故在此调用）
        loop = asyncio.get_event_loop()
        executor = None
        health_result = await loop.run_in_executor(
            executor,
            lambda: HealthAnalysisService.analyze(
                bazi_data, element_counts, wangshuai_data, xi_ji_data_for_health
            )
        )
        
        # 7. 构建input_data
        # ⚠️ 重要：使用 wangshuai_data（提取后的数据），而不是 wangshuai_result（原始结果）
        input_data = build_health_input_data(
            bazi_data,
            wangshuai_data,
            detail_result,
            dayun_sequence,
            health_result if health_result.get('success') else {},
            gender,
            special_liunians=special_liunians
        )
        logger.info("✅ 使用硬编码函数构建 input_data: health_analysis")
        
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
        
        # ⚠️ DEBUG: 输出传给大模型的关键数据
        logger.info(f"[Health Analysis] 传给大模型的数据摘要:")
        logger.info(f"  - 特殊流年数量: {len(special_liunians)}")
        logger.info(f"  - 大运数量: {len(dayun_sequence)}")
        logger.info(f"  - 当前大运: {input_data.get('dayun_jiankang', {}).get('current_dayun')}")
        logger.info(f"  - 关键大运数量: {len(input_data.get('dayun_jiankang', {}).get('key_dayuns', []))}")
        logger.info(f"  - 健康规则数量: {len(health_rules)}")
        logger.info(f"  - 五行平衡: {input_data.get('mingpan_tizhi_zonglun', {}).get('wuxing_balance', '')}")
        logger.info(f"  - 病理倾向: {input_data.get('wuxing_bingli', {}).get('pathology_tendency', {})}")
        
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
        
        # 10. ⚠️ 优化：使用精简中文文本格式（Token 减少 86%）
        formatted_data = format_health_for_llm(input_data)
        logger.info(f"格式化数据长度: {len(formatted_data)} 字符（优化后）")
        logger.debug(f"格式化数据:\n{formatted_data}")
        
        # ✅ 性能优化：检查 LLM 缓存
        input_data_hash = compute_input_data_hash(input_data)
        cached_llm_content = get_llm_cache("health", input_data_hash)
        
        if cached_llm_content:
            logger.info(f"✅ LLM 缓存命中: health")
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
                    function_type='health',
                    frontend_api='/api/v1/bazi/health/stream',
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
        
        logger.info(f"❌ LLM 缓存未命中: health")
        
        # 11. 调用 LLM API（阶段5：LLM API调用，支持 Coze 和百炼平台）
        from server.services.llm_service_factory import LLMServiceFactory
        from server.services.bailian_stream_service import BailianStreamService
        llm_service = LLMServiceFactory.get_service(scene="health", bot_id=used_bot_id)

        # 12. 流式处理（阶段6：流式处理）
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
                    set_llm_cache("health", input_data_hash, complete_content, LLM_CACHE_TTL)
                    logger.info(f"✅ LLM 缓存已写入: health")
            
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
            function_type='health',
            frontend_api='/api/v1/bazi/health/stream',
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
            function_type='health',
            frontend_api='/api/v1/bazi/health/stream',
            frontend_input=frontend_input,
            input_data='',
            llm_output='',
            llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
            api_total_ms=api_total_ms,
            llm_first_token_ms=None,
            llm_total_ms=None,
            status='failed',
            error_message=str(e),
            bot_id=used_bot_id
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
        api_total_ms = int((api_end_time - api_start_time) * 1000)
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='health',
            frontend_api='/api/v1/bazi/health/stream',
            frontend_input=frontend_input,
            input_data='',
            llm_output='',
            llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
            api_total_ms=api_total_ms,
            llm_first_token_ms=None,
            llm_total_ms=None,
            status='failed',
            error_message=str(e),
            bot_id=used_bot_id
        )


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
    # ⚠️ 重要：从 wangshuai_result 中提取旺衰数据
    # 兼容两种情况：
    # 1. 传入的是 wangshuai_result（格式 {'success': True, 'data': {...}}），需要提取 data
    # 2. 传入的是 wangshuai_data（已经提取的数据，有 'wangshuai' 字段），直接使用
    if 'success' in wangshuai_result:
        # 情况1：传入的是 wangshuai_result
        if not wangshuai_result.get('success'):
            logger.warning(f"旺衰分析失败: {wangshuai_result.get('error')}")
            wangshuai_data = {}
        else:
            wangshuai_data = wangshuai_result.get('data', {})
    else:
        # 情况2：传入的是 wangshuai_data（已经提取的数据）
        wangshuai_data = wangshuai_result
    
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    element_counts = bazi_data.get('element_counts', {})
    ten_gods_data = detail_result.get('ten_gods', {})
    
    # 提取日主信息
    day_pillar = bazi_pillars.get('day', {})
    day_stem = day_pillar.get('stem', '')
    day_branch = day_pillar.get('branch', '')
    
    # ⚠️ 修复：从 wangshuai_data（提取后的数据）中获取旺衰数据
    wangshuai = wangshuai_data.get('wangshuai', '')
    
    # 提取月令
    month_pillar = bazi_pillars.get('month', {})
    month_branch = month_pillar.get('branch', '')
    yue_ling = f"{month_branch}月" if month_branch else ''
    
    # ⚠️ 修复：从 wangshuai_data（提取后的数据）中获取喜忌数据
    # wangshuai_data 中的字段是 xi_shen_elements 和 ji_shen_elements（列表格式）
    # 需要重新构建 xi_ji_elements 结构
    xi_ji_data = {
        'xi_shen': wangshuai_data.get('xi_shen', []),
        'ji_shen': wangshuai_data.get('ji_shen', []),
        'xi_shen_elements': wangshuai_data.get('xi_shen_elements', []),
        'ji_shen_elements': wangshuai_data.get('ji_shen_elements', []),
        # 兼容旧格式
        'xi_ji_elements': {
            'xi_shen': wangshuai_data.get('xi_shen_elements', []),
            'ji_shen': wangshuai_data.get('ji_shen_elements', [])
        }
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
    
    # ⚠️ 统一架构：使用 KeyYearsProvider 获取关键年份数据
    # 数据层：special_liunians 来自 orchestrator（与 fortune/display 一致）
    # 业务层：使用 'health' 策略（五行病理冲突选择关键大运）
    if special_liunians is None:
        special_liunians = []
    
    from server.utils.key_years_provider import KeyYearsProvider
    key_years_result = KeyYearsProvider.build_key_years_structure(
        dayun_sequence=dayun_sequence,
        special_liunians=special_liunians,
        current_age=current_age,
        business_type='health',
        bazi_data=bazi_data,
        gender=gender,
    )
    
    current_dayun_data = key_years_result.get('current_dayun')
    key_dayuns_data = key_years_result.get('key_dayuns', [])
    
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
            'special_liunians': special_liunians,  # ⚠️ 特殊流年（供公共模块按 dayun_step 分配到各运）
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

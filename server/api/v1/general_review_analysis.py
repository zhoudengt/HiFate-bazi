#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-总评分析API
基于用户生辰数据，使用 Coze Bot 流式生成总评分析
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
from server.services.rule_service import RuleService
from server.services.health_analysis_service import HealthAnalysisService
from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
from src.analyzers.fortune_relation_analyzer import FortuneRelationAnalyzer
from server.utils.data_validator import validate_bazi_data
from server.api.v1.xishen_jishen import get_xishen_jishen, XishenJishenRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.coze_stream_service import CozeStreamService
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from src.analyzers.fortune_relation_analyzer import FortuneRelationAnalyzer
from src.analyzers.wuxing_balance_analyzer import WuxingBalanceAnalyzer
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.industry_service import IndustryService

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class GeneralReviewRequest(BaseModel):
    """总评分析请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量配置）")


@router.post("/general-review/stream", summary="流式生成总评分析")
async def general_review_analysis_stream(request: GeneralReviewRequest):
    """
    流式生成总评分析
    
    Args:
        request: 总评分析请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    return StreamingResponse(
        general_review_analysis_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
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
    print(f"[DEBUG general_review_analysis_debug] 函数被调用，参数: solar_date={request.solar_date}, solar_time={request.solar_time}, gender={request.gender}")
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
                parallel=True
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
        
        # 构建input_data（⚠️ 明确使用关键字参数，避免参数对应错误）
        print(f"[DEBUG] 准备调用 build_general_review_input_data，dayun_sequence 数量: {len(dayun_sequence)}, special_liunians 数量: {len(special_liunians)}")
        logger.info(f"[General Review Debug] 准备调用 build_general_review_input_data，dayun_sequence 数量: {len(dayun_sequence)}, special_liunians 数量: {len(special_liunians)}")
        input_data = build_general_review_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=request.gender,
            solar_date=final_solar_date,  # ⚠️ 传递原始日期
            solar_time=final_solar_time,  # ⚠️ 传递原始时间
            personality_result=personality_result,
            rizhu_result=rizhu_result,
            health_result=health_result,
            liunian_sequence=liunian_sequence,  # ⚠️ 传递流年数据
            special_liunians=special_liunians,  # ⚠️ 传递特殊流年（已筛选）
            xishen_jishen_result=xishen_jishen_result  # ⚠️ 传递喜忌数据结果
        )
        
        # ⚠️ DEBUG: 调用后检查变量
        print(f"[DEBUG] build_general_review_input_data 调用后，dayun_sequence 数量: {len(dayun_sequence)}, special_liunians 数量: {len(special_liunians)}")
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
        
        # 简化返回，只返回 success 和 input_data
        return {
            "success": True,
            "input_data": input_data
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
    bot_id: Optional[str] = None
):
    """流式生成总评分析的生成器"""
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > GENERAL_REVIEW_BOT_ID > COZE_BOT_ID）
        used_bot_id = bot_id
        if not used_bot_id:
            used_bot_id = os.getenv("GENERAL_REVIEW_BOT_ID")
            if not used_bot_id:
                used_bot_id = os.getenv("COZE_BOT_ID")
                if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失: 请设置环境变量 GENERAL_REVIEW_BOT_ID 或 COZE_BOT_ID。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"总评分析请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={used_bot_id}")
        
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
        
        logger.info(f"[General Review Stream] 获取到 dayun_sequence 数量: {len(dayun_sequence)}, liunian_sequence 数量: {len(liunian_sequence)}")
        
        # 提取特殊流年（统一接口返回的是字典格式，包含 'list', 'by_dayun', 'formatted'）
        special_liunians_data = unified_data.get('special_liunians', {})
        if isinstance(special_liunians_data, dict):
            special_liunians = special_liunians_data.get('list', [])
        elif isinstance(special_liunians_data, list):
            special_liunians = special_liunians_data
        else:
            special_liunians = []
        
        logger.info(f"[General Review Stream] 获取到特殊流年数量: {len(special_liunians)}")
        
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
        
        # ========== 阶段5：检查 special_liunians 是否正确传递到 build_general_review_input_data ==========
        logger.info(f"[阶段5-DEBUG] 准备调用 build_general_review_input_data，special_liunians 数量: {len(special_liunians)}")
        if special_liunians:
            special_liunian_strs = [f"{l.get('year', '')}年{l.get('ganzhi', '')}" for l in special_liunians[:3]]
            logger.info(f"[阶段5-DEBUG] special_liunians 内容: {special_liunian_strs}")
        input_data = build_general_review_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=gender,
            solar_date=final_solar_date,  # ⚠️ 传递原始日期
            solar_time=final_solar_time,  # ⚠️ 传递原始时间
            personality_result=personality_result,
            rizhu_result=rizhu_result,
            health_result=health_result,
            liunian_sequence=liunian_sequence,  # ⚠️ 传递流年数据
            special_liunians=special_liunians,  # ⚠️ 传递特殊流年（已筛选）
            xishen_jishen_result=xishen_jishen_result  # ⚠️ 传递喜忌数据结果
        )
        
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
        
        # 8. 构建自然语言Prompt（阶段4：Prompt构建）
        prompt = build_general_review_prompt(input_data)
        logger.info(f"Prompt长度: {len(prompt)} 字符")
        logger.debug(f"Prompt前500字符: {prompt[:500]}")
        
        # 9. 调用Coze API（阶段5：Coze API调用）
        print(f"🔍 [步骤5-Coze调用] 开始调用 Coze API，Bot ID: {used_bot_id}")
        logger.info(f"[步骤5-Coze调用] 开始调用 Coze API，Bot ID: {used_bot_id}")
        coze_service = CozeStreamService(bot_id=used_bot_id)
        
        # 10. 流式处理（阶段6：流式处理）
        chunk_count = 0
        total_content_length = 0
        async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=used_bot_id):
            chunk_type = chunk.get('type', 'unknown')
            if chunk_type == 'progress':
                chunk_count += 1
                content = chunk.get('content', '')
                total_content_length += len(content)
                if chunk_count == 1:
                    print(f"✅ [步骤5-Coze调用] 收到第一个响应块，类型: {chunk_type}")
                    logger.info(f"[步骤5-Coze调用] 收到第一个响应块，类型: {chunk_type}")
            elif chunk_type == 'complete':
                print(f"✅ [步骤5-Coze调用] 收到完成响应，总块数: {chunk_count}, 总内容长度: {total_content_length}")
                logger.info(f"[步骤5-Coze调用] 收到完成响应，总块数: {chunk_count}, 总内容长度: {total_content_length}")
            elif chunk_type == 'error':
                print(f"❌ [步骤5-Coze调用] 收到错误响应: {chunk.get('content', '')}")
                logger.error(f"[步骤5-Coze调用] 收到错误响应: {chunk.get('content', '')}")
            
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk_type in ['complete', 'error']:
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
        # 其他错误（阶段7：错误处理）
        import traceback
        logger.error(f"总评分析失败: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"分析处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


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
    
    # 提取当前大运
    current_dayun = None
    if dayun_sequence:
        # 找到当前大运（通常是最接近或包含当前年龄的大运）
        from datetime import datetime
        birth_date = bazi_data.get('basic_info', {}).get('solar_date', '')
        if birth_date:
            try:
                birth = datetime.strptime(birth_date, '%Y-%m-%d')
                today = datetime.now()
                age = today.year - birth.year - (1 if (today.month, today.day) < (birth.month, birth.day) else 0)
                
                for dayun in dayun_sequence:
                    age_range = dayun.get('age_display', '')
                    if age_range:
                        # 解析年龄范围，如 "10-20岁"
                        try:
                            parts = age_range.replace('岁', '').split('-')
                            if len(parts) == 2:
                                start_age = int(parts[0])
                                end_age = int(parts[1])
                                if start_age <= age <= end_age:
                                    current_dayun = dayun
                                    break
                        except:
                            pass
                
                if not current_dayun and dayun_sequence:
                    # 如果没有找到，使用第一个大运
                    current_dayun = dayun_sequence[1] if len(dayun_sequence) > 1 else dayun_sequence[0]
            except:
                pass
    
    # 获取关键大运（第2-4步）
    key_dayun_list = []
    for idx in [1, 2, 3]:
        if idx < len(dayun_sequence):
            dayun = dayun_sequence[idx]
            key_dayun_list.append({
                'step': dayun.get('step', idx),
                'stem': dayun.get('stem', ''),
                'branch': dayun.get('branch', ''),
                'main_star': dayun.get('main_star', ''),
                'year_start': dayun.get('year_start', 0),
                'year_end': dayun.get('year_end', 0),
                'age_display': dayun.get('age_display', '')
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
            'ten_gods': ten_gods_full,
            'wangshuai': wangshuai_result.get('wangshuai', ''),
            'wangshuai_detail': wangshuai_result.get('wangshuai_detail', ''),
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
            'current_dayun': current_dayun,
            'dayun_list': key_dayun_list,
            'dayun_sequence': dayun_sequence,  # ⚠️ 完整的大运序列
            'dayun_liunians': organize_special_liunians_by_dayun(special_liunians, dayun_sequence),  # 按大运分组
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
        }
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
        from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
        
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
            'dayun_list': '大运列表'
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


def build_general_review_prompt(data: dict) -> str:
    """
    构建自然语言格式的提示词（阶段4：Prompt构建）
    将JSON数据转换为自然语言格式，确保 Coze Bot 能正确理解
    """
    prompt_lines = []
    # ⚠️ 注意：代码中只提供数据，不包含任何提示词或指令
    # 提示词必须在 Coze Bot 中配置
    
    # 1. 命盘核心格局
    prompt_lines.append("【命盘核心格局】")
    mingpan = data.get('mingpan_hexin_geju', {})
    
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
    
    # 旺衰
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        prompt_lines.append(f"身旺身弱：{wangshuai}")
    
    # 月令
    yue_ling = mingpan.get('yue_ling', '')
    if yue_ling:
        prompt_lines.append(f"月令：{yue_ling}")
    
    # 格局类型
    geju_type = mingpan.get('geju_type', '')
    if geju_type:
        prompt_lines.append(f"格局类型：{geju_type}")
    
    # 五行流通情况
    wuxing_liutong = mingpan.get('wuxing_liutong', {})
    if wuxing_liutong and wuxing_liutong.get('summary'):
        prompt_lines.append(f"五行流通：{wuxing_liutong['summary']}")
    
    prompt_lines.append("")
    
    # 2. 性格特质
    prompt_lines.append("【性格特质】")
    xingge = data.get('xingge_tezhi', {})
    
    # 日主性格
    personality = xingge.get('day_master_personality', [])
    if personality:
        prompt_lines.append("日主性格：")
        for desc in personality[:3]:  # 最多显示3条
            prompt_lines.append(f"  - {desc}")
    
    # 日柱算法
    rizhu_algorithm = xingge.get('rizhu_algorithm', '')
    if rizhu_algorithm:
        prompt_lines.append(f"日柱解析：{rizhu_algorithm[:200]}...")  # 截取前200字符
    
    # 十神对性格的影响
    ten_gods_effect = xingge.get('ten_gods_effect', {})
    if ten_gods_effect and ten_gods_effect.get('summary'):
        prompt_lines.append(f"十神影响：{ten_gods_effect['summary']}")
    
    prompt_lines.append("")
    
    # 日柱规则参考（NEW）
    rizhu_rules = data.get('rizhu_rules', {})
    matched_rules = rizhu_rules.get('matched_rules', [])
    if matched_rules:
        prompt_lines.append("【日柱规则参考】")
        prompt_lines.append(f"匹配到 {len(matched_rules)} 条日柱规则：")
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
    
    # 3. 事业财运轨迹
    prompt_lines.append("【事业财运轨迹】")
    shiye_caiyun = data.get('shiye_caiyun', {})
    
    # 事业星
    shiye_xing = shiye_caiyun.get('shiye_xing', {})
    if shiye_xing and shiye_xing.get('primary'):
        prompt_lines.append(f"事业星：{shiye_xing['primary']}")
    
    # 财富星
    caifu_xing = shiye_caiyun.get('caifu_xing', {})
    if caifu_xing and caifu_xing.get('primary'):
        prompt_lines.append(f"财富星：{caifu_xing['primary']}")
    
    # 大运阶段数据
    dayun_effect = shiye_caiyun.get('dayun_effect', {})
    all_dayuns = dayun_effect.get('all_dayuns', [])
    if all_dayuns:
        prompt_lines.append("大运阶段：")
        for dayun in all_dayuns:
            step = dayun.get('step', '')
            age_display = dayun.get('age_display', '')
            ganzhi = dayun.get('ganzhi', '')
            main_star = dayun.get('main_star', '')
            if step and age_display and ganzhi:
                prompt_lines.append(f"  第{step}步大运：{ganzhi}（{age_display}），主星：{main_star}")
    
    # 大运对事业财运的影响摘要
    if dayun_effect and dayun_effect.get('summary'):
        prompt_lines.append(f"大运影响摘要：{dayun_effect['summary']}")
    
    prompt_lines.append("")
    
    # 4. 家庭六亲关系
    prompt_lines.append("【家庭六亲关系】")
    jiating = data.get('jiating_liuqin', {})
    
    year_pillar = jiating.get('year_pillar', {})
    month_pillar = jiating.get('month_pillar', {})
    day_pillar = jiating.get('day_pillar', {})
    hour_pillar = jiating.get('hour_pillar', {})
    
    if year_pillar:
        stem = year_pillar.get('stem', '')
        branch = year_pillar.get('branch', '')
        if stem and branch:
            prompt_lines.append(f"年柱（父母）：{stem}{branch}")
    if month_pillar:
        stem = month_pillar.get('stem', '')
        branch = month_pillar.get('branch', '')
        if stem and branch:
            prompt_lines.append(f"月柱（兄弟）：{stem}{branch}")
    if day_pillar:
        stem = day_pillar.get('stem', '')
        branch = day_pillar.get('branch', '')
        if stem and branch:
            prompt_lines.append(f"日柱（配偶）：{stem}{branch}")
    if hour_pillar:
        stem = hour_pillar.get('stem', '')
        branch = hour_pillar.get('branch', '')
        if stem and branch:
            prompt_lines.append(f"时柱（子女）：{stem}{branch}")
    
    prompt_lines.append("")
    
    # 5. 健康要点
    prompt_lines.append("【健康要点】")
    jiankang = data.get('jiankang_yaodian', {})
    
    # 五行平衡
    wuxing_balance = jiankang.get('wuxing_balance', {})
    if wuxing_balance and isinstance(wuxing_balance, dict):
        summary = wuxing_balance.get('summary', '')
        if summary:
            prompt_lines.append(f"五行平衡：{summary}")
    
    # 脏腑对应
    zangfu_duiying = jiankang.get('zangfu_duiying', {})
    if zangfu_duiying and isinstance(zangfu_duiying, dict):
        organs = zangfu_duiying.get('organ_strength', {})
        if organs:
            strong_organs = [k for k, v in organs.items() if v > 2]
            weak_organs = [k for k, v in organs.items() if v < 1]
            if strong_organs:
                prompt_lines.append(f"强旺脏腑：{'、'.join(strong_organs)}")
            if weak_organs:
                prompt_lines.append(f"薄弱脏腑：{'、'.join(weak_organs)}")
    
    prompt_lines.append("")
    
    # 6. 关键大运与人生节点
    prompt_lines.append("【关键大运与人生节点】")
    guanjian = data.get('guanjian_dayun', {})
    
    # 当前大运
    current_dayun = guanjian.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        age_display = current_dayun.get('age_display', '')
        if stem and branch:
            prompt_lines.append(f"当前大运：{stem}{branch}（{age_display}）")
    
    # 大运序列数据
    dayun_sequence = guanjian.get('dayun_sequence', [])
    if dayun_sequence:
        prompt_lines.append("大运序列：")
        max_display = min(7, len(dayun_sequence))
        for idx in range(max_display):
            dayun = dayun_sequence[idx]
            step = dayun.get('step', idx + 1)
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            main_star = dayun.get('main_star', '')
            age_display = dayun.get('age_display', '')
            if stem and branch:
                prompt_lines.append(f"  第{step}步大运：{stem}{branch}（{age_display}），主星：{main_star}")
    
    # 关键大运列表
    dayun_list = guanjian.get('dayun_list', [])
    if dayun_list:
        prompt_lines.append("关键大运：")
        for dayun in dayun_list:
            step = dayun.get('step', '')
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            main_star = dayun.get('main_star', '')
            age_display = dayun.get('age_display', '')
            if stem and branch:
                prompt_lines.append(f"  第{step}步大运：{stem}{branch}（{age_display}），主星：{main_star}")
    
    # 冲合刑害
    chonghe_xinghai = guanjian.get('chonghe_xinghai', {})
    if chonghe_xinghai and chonghe_xinghai.get('summary'):
        prompt_lines.append(f"冲合刑害：{chonghe_xinghai['summary']}")
    
    # 特殊流年数据（按关系类型分类）
    # ⚠️ 修复：从 dayun_liunians 中提取并合并所有大运的特殊流年
    from server.services.special_liunian_service import SpecialLiunianService
    guanjian_dayun = data.get('guanjian_dayun', {})
    dayun_sequence_for_format = guanjian_dayun.get('dayun_sequence', guanjian_dayun.get('dayun_list', []))
    
    # 从 dayun_liunians 中提取并合并所有大运的特殊流年
    dayun_liunians = guanjian.get('dayun_liunians', {})
    tiankedi_chong = []
    tianhedi_he = []
    suiyun_binglin = []
    other_liunian = []
    
    # 遍历所有大运分组，合并特殊流年
    for dayun_step, dayun_data in dayun_liunians.items():
        if isinstance(dayun_data, dict):
            tiankedi_chong.extend(dayun_data.get('tiankedi_chong', []))
            tianhedi_he.extend(dayun_data.get('tianhedi_he', []))
            suiyun_binglin.extend(dayun_data.get('suiyun_binglin', []))
            other_liunian.extend(dayun_data.get('other', []))
    
    logger.info(f"[Prompt构建] 特殊流年统计: 天克地冲={len(tiankedi_chong)}, 天合地合={len(tianhedi_he)}, 岁运并临={len(suiyun_binglin)}, 其他={len(other_liunian)}")
    
    # 天克地冲（最高优先级）
    if tiankedi_chong:
        prompt_lines.append(f"特殊流年 - 天克地冲（共{len(tiankedi_chong)}个）：")
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(tiankedi_chong, dayun_sequence_for_format)
        if formatted:
            prompt_lines.append(formatted)
        else:
            # 如果格式化失败，至少列出年份和干支
            for liunian in tiankedi_chong[:10]:  # 最多显示10个
                year = liunian.get('year', '')
                ganzhi = liunian.get('ganzhi', '')
                if year and ganzhi:
                    prompt_lines.append(f"  - {year}年{ganzhi}")
    
    # 天合地合（高优先级）
    if tianhedi_he:
        prompt_lines.append(f"特殊流年 - 天合地合（共{len(tianhedi_he)}个）：")
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(tianhedi_he, dayun_sequence_for_format)
        if formatted:
            prompt_lines.append(formatted)
        else:
            # 如果格式化失败，至少列出年份和干支
            for liunian in tianhedi_he[:10]:  # 最多显示10个
                year = liunian.get('year', '')
                ganzhi = liunian.get('ganzhi', '')
                if year and ganzhi:
                    prompt_lines.append(f"  - {year}年{ganzhi}")
    
    # 岁运并临（高优先级）
    if suiyun_binglin:
        prompt_lines.append(f"特殊流年 - 岁运并临（共{len(suiyun_binglin)}个）：")
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(suiyun_binglin, dayun_sequence_for_format)
        if formatted:
            prompt_lines.append(formatted)
        else:
            # 如果格式化失败，至少列出年份和干支
            for liunian in suiyun_binglin[:10]:  # 最多显示10个
                year = liunian.get('year', '')
                ganzhi = liunian.get('ganzhi', '')
                if year and ganzhi:
                    prompt_lines.append(f"  - {year}年{ganzhi}")
    
    # 其他关系
    if other_liunian:
        prompt_lines.append(f"其他特殊流年（共{len(other_liunian)}个）：")
        # 其他流年也格式化显示
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(other_liunian[:20], dayun_sequence_for_format)  # 最多显示20个
        if formatted:
            prompt_lines.append(formatted)
        else:
            # 如果格式化失败，至少列出年份和干支
            for liunian in other_liunian[:10]:  # 最多显示10个
                year = liunian.get('year', '')
                ganzhi = liunian.get('ganzhi', '')
                if year and ganzhi:
                    prompt_lines.append(f"  - {year}年{ganzhi}")
    
    prompt_lines.append("")
    
    # 7. 终生提点与建议
    prompt_lines.append("【终生提点与建议】")
    zhongsheng = data.get('zhongsheng_tidian', {})
    
    # 喜神（独立）
    xishen = zhongsheng.get('xishen', {})
    xishen_shishen = []
    xishen_wuxing = []
    xishen_tiaohou = {}
    
    if xishen:
        xishen_shishen = xishen.get('shishen', [])
        xishen_wuxing = xishen.get('wuxing', [])
        xishen_tiaohou = xishen.get('tiaohou', {})
    
    # ⚠️ 修复：即使数据为空也明确标注，确保 Coze Bot 能看到完整信息
    if xishen_shishen:
        prompt_lines.append(f"喜用神（十神）：{'、'.join(xishen_shishen)}")
    else:
        prompt_lines.append("喜用神（十神）：无")
    
    if xishen_wuxing:
        prompt_lines.append(f"喜神五行：{'、'.join(xishen_wuxing)}")
    else:
        prompt_lines.append("喜神五行：无")
    
    if xishen_tiaohou and xishen_tiaohou.get('description'):
        prompt_lines.append(f"调候建议：{xishen_tiaohou.get('description', '')}")
    
    # 忌神（独立）
    jishen = zhongsheng.get('jishen', {})
    jishen_shishen = []
    jishen_wuxing = []
    
    if jishen:
        jishen_shishen = jishen.get('shishen', [])
        jishen_wuxing = jishen.get('wuxing', [])
    
    # ⚠️ 修复：即使数据为空也明确标注，确保 Coze Bot 能看到完整信息
    if jishen_shishen:
        prompt_lines.append(f"忌神（十神）：{'、'.join(jishen_shishen)}")
    else:
        prompt_lines.append("忌神（十神）：无")
    
    if jishen_wuxing:
        prompt_lines.append(f"忌神五行：{'、'.join(jishen_wuxing)}")
    else:
        prompt_lines.append("忌神五行：无")
    
    # ⚠️ 添加日志，便于调试
    logger.info(f"[Prompt构建] 喜忌数据: 喜神十神={len(xishen_shishen)}, 喜神五行={len(xishen_wuxing)}, 忌神十神={len(jishen_shishen)}, 忌神五行={len(jishen_wuxing)}")
    
    # 方位选择
    fangwei = zhongsheng.get('fangwei_xuanze', {})
    if fangwei:
        best = fangwei.get('best_directions', [])
        avoid = fangwei.get('avoid_directions', [])
        if best:
            prompt_lines.append(f"最佳方位：{'、'.join(best)}")
        if avoid:
            prompt_lines.append(f"避开方位：{'、'.join(avoid)}")
    
    # 行业选择
    hangye = zhongsheng.get('hangye_xuanze', {})
    if hangye:
        best = hangye.get('best_industries', [])
        avoid = hangye.get('avoid_industries', [])
        if best:
            prompt_lines.append(f"适合行业：{'、'.join(best[:5])}")
        if avoid:
            prompt_lines.append(f"谨慎行业：{'、'.join(avoid[:3])}")
    
    prompt_lines.append("")
    
    return '\n'.join(prompt_lines)


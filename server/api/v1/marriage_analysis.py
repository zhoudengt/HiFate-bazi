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
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor

logger = logging.getLogger(__name__)

router = APIRouter()


class MarriageAnalysisRequest(BaziBaseRequest):
    """感情婚姻分析请求模型"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID 环境变量）")


async def marriage_analysis_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """
    流式生成感情婚姻分析
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
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
        
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            "solar",  # 默认使用阳历
            None,  # location
            None,  # latitude
            None   # longitude
        )
        
        # 2. 获取八字排盘数据
        try:
            bazi_result = BaziService.calculate_bazi_full(final_solar_date, final_solar_time, gender)
            if not bazi_result:
                error_msg = {
                    'type': 'error',
                    'content': "八字排盘失败"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
            
            # 提取八字数据（可能包含 'bazi' 键）
            if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
                bazi_data = bazi_result['bazi']
            else:
                bazi_data = bazi_result
            
            # 验证数据类型
            bazi_data = validate_bazi_data(bazi_data)
            
        except Exception as e:
            import traceback
            error_msg = {
                'type': 'error',
                'content': f"获取八字排盘数据失败: {str(e)}\n{traceback.format_exc()}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 3. 获取旺衰数据
        try:
            wangshuai_result = WangShuaiService.calculate_wangshuai(final_solar_date, final_solar_time, gender)
            if not wangshuai_result.get('success'):
                logger.warning(f"旺衰分析失败: {wangshuai_result.get('error')}")
                wangshuai_data = {}
            else:
                wangshuai_data = wangshuai_result.get('data', {})
        except Exception as e:
            logger.warning(f"旺衰分析异常（不影响业务）: {e}")
            wangshuai_data = {}
        
        # 4. 获取规则匹配数据（婚姻、桃花等）
        try:
            # 构建规则匹配数据
            rule_data = {
                'basic_info': bazi_data.get('basic_info', {}),
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                'details': bazi_data.get('details', {}),
                'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
                'elements': bazi_data.get('elements', {}),
                'element_counts': bazi_data.get('element_counts', {}),
                'relationships': bazi_data.get('relationships', {})
            }
            
            # 匹配婚姻规则
            marriage_rules = RuleService.match_rules(rule_data, rule_types=['marriage'], use_cache=True)
            
            # 匹配桃花规则
            peach_blossom_rules = RuleService.match_rules(rule_data, rule_types=['peach_blossom'], use_cache=True)
            
            # 筛选婚配判词和正缘判词（从婚姻规则中筛选）
            marriage_judgments = []
            matchmaking_judgments = []
            zhengyuan_judgments = []
            
            for rule in marriage_rules:
                rule_name = rule.get('rule_name', '')
                content = rule.get('content', {})
                if isinstance(content, dict):
                    text = content.get('text', '')
                else:
                    text = str(content)
                
                # 根据规则名称或内容判断类型
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
            
            # 桃花判词
            peach_blossom_judgments = []
            for rule in peach_blossom_rules:
                rule_name = rule.get('rule_name', '')
                content = rule.get('content', {})
                if isinstance(content, dict):
                    text = content.get('text', '')
                else:
                    text = str(content)
                peach_blossom_judgments.append({
                    'name': rule_name,
                    'text': text
                })
                
        except Exception as e:
            logger.warning(f"规则匹配失败（不影响业务）: {e}")
            marriage_judgments = []
            peach_blossom_judgments = []
            matchmaking_judgments = []
            zhengyuan_judgments = []
        
        # 5. 提取大运流年数据（第2、3、4个大运，索引1、2、3）
        dayun_list = []
        try:
            details = bazi_data.get('details', {})
            dayun_sequence = details.get('dayun_sequence', [])
            
            # 跳过第0个"小运"，获取索引1、2、3的大运
            for idx in [1, 2, 3]:
                if idx < len(dayun_sequence):
                    dayun = dayun_sequence[idx]
                    # 提取关键信息
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
        input_data = {
            # 命盘总论数据
            'mingpan_zonglun': {
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                'ten_gods': ten_gods_data,
                'wangshuai': wangshuai_data.get('wangshuai', ''),
                'branch_relations': branch_relations,
                'day_pillar': day_pillar
            },
            # 配偶特征数据
            'peiou_tezheng': {
                'ten_gods': ten_gods_data,
                'deities': deities_data,
                'marriage_judgments': marriage_judgments,
                'peach_blossom_judgments': peach_blossom_judgments,
                'matchmaking_judgments': matchmaking_judgments,
                'zhengyuan_judgments': zhengyuan_judgments
            },
            # 感情走势数据
            'ganqing_zoushi': {
                'dayun_list': dayun_list,
                'ten_gods': ten_gods_data
            },
            # 神煞点睛数据
            'shensha_dianjing': {
                'deities': deities_data
            },
            # 建议方向数据
            'jianyi_fangxiang': {
                'ten_gods': ten_gods_data,
                'xi_ji': xi_ji_data,
                'dayun_list': dayun_list
            }
        }
        
        # 12. 将输入数据格式化为JSON字符串（作为prompt）
        prompt = json.dumps(input_data, ensure_ascii=False, indent=2)
        
        # 13. 创建Coze流式服务
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
        
        # 14. 流式生成（使用实际 bot_id）
        actual_bot_id = bot_id or coze_service.bot_id
        logger.info(f"开始流式生成，Bot ID: {actual_bot_id}, Prompt 长度: {len(prompt)}")
        
        try:
            chunk_count = 0
            has_content = False
            
            async for result in coze_service.stream_custom_analysis(prompt, actual_bot_id):
                chunk_count += 1
                
                # 转换为SSE格式
                if result.get('type') == 'progress':
                    has_content = True
                    msg = {
                        'type': 'progress',
                        'content': result.get('content', '')
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
                    logger.error(f"Coze API 返回错误: {error_content}")
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


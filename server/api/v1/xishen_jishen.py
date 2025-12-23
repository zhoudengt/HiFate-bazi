#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-喜神与忌神API
获取喜神五行、忌神五行和十神命格，并映射ID
"""

import logging
import os
import sys
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from fastapi.responses import StreamingResponse
import json
import asyncio
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_service import BaziService
from server.services.rule_service import RuleService
from server.services.config_service import ConfigService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor

logger = logging.getLogger(__name__)

router = APIRouter()


class XishenJishenRequest(BaziBaseRequest):
    """喜神忌神请求模型"""
    pass


class XishenJishenResponse(BaseModel):
    """喜神忌神响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/bazi/xishen-jishen", response_model=XishenJishenResponse, summary="获取喜神忌神和十神命格")
async def get_xishen_jishen(request: XishenJishenRequest):
    """
    获取喜神五行、忌神五行和十神命格
    
    根据用户的生辰（与基础八字排盘生辰同）：
    1. 从旺衰分析中获取喜神五行和忌神五行
    2. 从公式分析中获取十神命格
    3. 查询配置表获取对应的ID
    
    Returns:
        - xi_shen_elements: 喜神五行列表（包含名称和ID）
        - ji_shen_elements: 忌神五行列表（包含名称和ID）
        - shishen_mingge: 十神命格列表（包含名称和ID）
    """
    logger.info(f"📥 收到喜神忌神请求: {request.solar_date} {request.solar_time} {request.gender}")
    
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 1. 获取旺衰分析结果（包含喜神五行和忌神五行）
        wangshuai_result = WangShuaiService.calculate_wangshuai(
            final_solar_date,
            final_solar_time,
            request.gender
        )
        
        if not wangshuai_result.get('success'):
            error_msg = wangshuai_result.get('error', '旺衰计算失败')
            logger.error(f"❌ 旺衰计算失败: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        wangshuai_data = wangshuai_result.get('data', {})
        
        # 调试：打印完整的数据结构
        logger.info(f"   wangshuai_data keys: {list(wangshuai_data.keys())}")
        logger.info(f"   wangshuai_data.xi_shen_elements: {wangshuai_data.get('xi_shen_elements', 'NOT_FOUND')}")
        logger.info(f"   wangshuai_data.ji_shen_elements: {wangshuai_data.get('ji_shen_elements', 'NOT_FOUND')}")
        
        # 提取喜神五行和忌神五行（优先使用final_xi_ji中的综合结果，如果没有则使用原始结果）
        final_xi_ji = wangshuai_data.get('final_xi_ji', {})
        logger.info(f"   final_xi_ji存在: {bool(final_xi_ji)}, keys: {list(final_xi_ji.keys()) if final_xi_ji else []}")
        if final_xi_ji:
            logger.info(f"   final_xi_ji.xi_shen_elements: {final_xi_ji.get('xi_shen_elements', 'NOT_FOUND')}")
            logger.info(f"   final_xi_ji.ji_shen_elements: {final_xi_ji.get('ji_shen_elements', 'NOT_FOUND')}")
        
        if final_xi_ji and final_xi_ji.get('xi_shen_elements'):
            # 使用综合调候后的最终结果
            xi_shen_elements_raw = final_xi_ji.get('xi_shen_elements', [])
            ji_shen_elements_raw = final_xi_ji.get('ji_shen_elements', [])
            logger.info(f"   ✅ 使用final_xi_ji中的数据: 喜神={xi_shen_elements_raw}, 忌神={ji_shen_elements_raw}")
        else:
            # 使用原始旺衰结果
            xi_shen_elements_raw = wangshuai_data.get('xi_shen_elements', [])  # 如 ['金', '土']
            ji_shen_elements_raw = wangshuai_data.get('ji_shen_elements', [])  # 如 ['水', '木', '火']
            logger.info(f"   ⚠️  使用原始数据: 喜神={xi_shen_elements_raw}, 忌神={ji_shen_elements_raw}")
        
        logger.info(f"   最终提取 - 喜神五行: {xi_shen_elements_raw}, 忌神五行: {ji_shen_elements_raw}")
        
        # 2. 获取十神命格
        # ✅ 直接调用算法公式规则分析接口的逻辑，确保数据一致性
        from server.api.v1.formula_analysis import analyze_formula_rules, FormulaAnalysisRequest
        
        # 调用算法公式规则分析接口（只查询十神命格类型）
        formula_request = FormulaAnalysisRequest(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            rule_types=['shishen']  # 只查询十神命格
        )
        formula_result = await analyze_formula_rules(formula_request)
        
        if not formula_result.success:
            logger.warning(f"算法公式规则分析接口调用失败: {formula_result.error}")
            shishen_mingge_names = []
        else:
            # 从算法公式规则分析接口返回的数据中提取十神命格名称
            formula_data = formula_result.data
            matched_rules = formula_data.get('matched_rules', {})
            rule_details = formula_data.get('rule_details', {})
            
            # 获取十神命格规则的ID列表
            shishen_rule_ids = matched_rules.get('shishen', [])
            
            # 从所有命格名称列表中匹配
            all_mingge_names = list(ConfigService.get_all_mingge().keys())
            # 按长度降序排序，避免部分匹配问题
            all_mingge_names_sorted = sorted(all_mingge_names, key=len, reverse=True)
            
            shishen_mingge_names = []
            for rule_id in shishen_rule_ids:
                rule_detail = rule_details.get(rule_id, {})
                # 从规则的'结果'字段中提取命格名称
                rule_result = rule_detail.get('结果') or rule_detail.get('result') or ''
                
                if rule_result:
                    # 在结果文本中查找命格名称（按长度降序，避免部分匹配）
                    for mingge_name in all_mingge_names_sorted:
                        if mingge_name in rule_result:
                            if mingge_name not in shishen_mingge_names:
                                shishen_mingge_names.append(mingge_name)
                                logger.debug(f"从规则ID {rule_id} 的结果中提取到命格名称: {mingge_name}")
                                break  # 每个规则只取第一个匹配的命格名称
        
        logger.info(f"   十神命格: {shishen_mingge_names}")
        
        # 3. 映射ID
        xi_shen_elements = ConfigService.map_elements_to_ids(xi_shen_elements_raw)
        ji_shen_elements = ConfigService.map_elements_to_ids(ji_shen_elements_raw)
        shishen_mingge = ConfigService.map_mingge_to_ids(shishen_mingge_names)
        
        # 4. 构建响应数据
        response_data = {
            'solar_date': request.solar_date,
            'solar_time': request.solar_time,
            'gender': request.gender,
            'xi_shen_elements': xi_shen_elements,  # [{'name': '金', 'id': 4}, {'name': '土', 'id': 3}]
            'ji_shen_elements': ji_shen_elements,  # [{'name': '水', 'id': 5}, {'name': '木', 'id': 1}, {'name': '火', 'id': 2}]
            'shishen_mingge': shishen_mingge,  # [{'name': '正官格', 'id': 2001}, ...]
            'wangshuai': wangshuai_data.get('wangshuai'),  # 旺衰状态
            'total_score': wangshuai_data.get('total_score'),  # 总分
        }
        
        logger.info(f"✅ 喜神忌神获取成功")
        return XishenJishenResponse(success=True, data=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 喜神忌神API异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


async def xishen_jishen_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """
    流式生成喜神忌神大模型分析
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        bot_id: Coze Bot ID（可选，优先级：参数 > XISHEN_JISHEN_BOT_ID 环境变量）
    """
    try:
        # 确定使用的 bot_id（优先级：参数 > XISHEN_JISHEN_BOT_ID > COZE_BOT_ID）
        if not bot_id:
            bot_id = os.getenv("XISHEN_JISHEN_BOT_ID")
            if not bot_id:
                # 如果没有设置 XISHEN_JISHEN_BOT_ID，使用 COZE_BOT_ID 作为默认值
                bot_id = os.getenv("COZE_BOT_ID")
                if not bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失: 请设置环境变量 XISHEN_JISHEN_BOT_ID 或 COZE_BOT_ID 或在请求参数中提供 bot_id。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        # 1. 先获取基础数据
        try:
            request = XishenJishenRequest(
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender
            )
            base_result = await get_xishen_jishen(request)
            
            if not base_result.success or not base_result.data:
                error_msg = {
                    'type': 'error',
                    'content': f"获取基础数据失败: {base_result.error or '未知错误'}"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
            
            data = base_result.data
        except Exception as e:
            error_msg = {
                'type': 'error',
                'content': f"获取基础数据异常: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 2. 构建提示词
        xi_elements_text = '、'.join([e['name'] for e in data.get('xi_shen_elements', [])]) or '无'
        ji_elements_text = '、'.join([e['name'] for e in data.get('ji_shen_elements', [])]) or '无'
        mingge_text = '、'.join([m['name'] for m in data.get('shishen_mingge', [])]) or '无'
        
        prompt = f"""请根据以下八字命理信息，生成详细的喜神忌神分析：

十神命格：{mingge_text}
喜神五行：{xi_elements_text}
忌神五行：{ji_elements_text}
旺衰状态：{data.get('wangshuai', '未知')}
总分：{data.get('total_score', 0)}分

请基于这些信息，生成详细的命理分析内容。"""
        
        # 3. 创建Coze流式服务
        try:
            from server.services.coze_stream_service import CozeStreamService
            coze_service = CozeStreamService(bot_id=bot_id)
        except ValueError as e:
            error_msg = {
                'type': 'error',
                'content': f"Coze API 配置缺失: {str(e)}。请设置环境变量 COZE_ACCESS_TOKEN 和 COZE_BOT_ID。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            error_msg = {
                'type': 'error',
                'content': f"初始化 Coze 服务失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 4. 流式生成
        async for result in coze_service.stream_custom_analysis(prompt, bot_id):
            # 转换为SSE格式
            if result.get('type') == 'progress':
                msg = {
                    'type': 'progress',
                    'content': result.get('content', '')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)
            elif result.get('type') == 'complete':
                msg = {
                    'type': 'complete',
                    'content': result.get('content', '')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return
            elif result.get('type') == 'error':
                msg = {
                    'type': 'error',
                    'content': result.get('content', '生成失败')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return
                
    except Exception as e:
        import traceback
        error_msg = {
            'type': 'error',
            'content': f"流式生成失败: {str(e)}\n{traceback.format_exc()}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


class XishenJishenStreamRequest(BaseModel):
    """喜神忌神流式请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，优先级：参数 > XISHEN_JISHEN_BOT_ID 环境变量）")


@router.post("/bazi/xishen-jishen/stream", summary="流式生成喜神忌神分析")
async def xishen_jishen_stream(request: XishenJishenStreamRequest):
    """
    流式生成喜神忌神大模型分析
    
    使用Coze大模型基于十神命格、喜神五行、忌神五行生成详细分析，返回SSE流式响应。
    
    **参数说明**：
    - **solar_date**: 阳历日期（必填）
    - **solar_time**: 出生时间（必填）
    - **gender**: 性别（必填）
    - **bot_id**: Coze Bot ID（可选，优先级：参数 > XISHEN_JISHEN_BOT_ID 环境变量）
    
    **返回格式**：
    SSE流式响应，每行格式：`data: {"type": "progress|complete|error", "content": "..."}`
    """
    try:
        return StreamingResponse(
            xishen_jishen_stream_generator(
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
        logger.error(f"❌ 流式生成异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"流式生成失败: {str(e)}")


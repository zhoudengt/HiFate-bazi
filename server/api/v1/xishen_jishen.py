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
from fastapi import APIRouter, HTTPException, Request, Query
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
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.config_service import ConfigService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.config.config_loader import get_config_from_db_only
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)
from server.api.base.stream_handler import generate_request_id, _sse_request_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_xishen_jishen_for_llm(data: Dict[str, Any]) -> str:
    """
    将喜神忌神数据格式化为人类可读的中文描述（用于传给大模型）
    
    优化点：
    1. 去除冗长 JSON 和重复嵌套，只保留分析必需项
    2. 喜神/忌神/旺衰/十神命格/四柱/日主 等用简洁【标签】形式
    3. 可选：五行个数、十神简表，便于模型理解
    
    Args:
        data: 喜神忌神完整数据（含 xi_shen_elements, ji_shen_elements, bazi_pillars 等）
        
    Returns:
        str: 格式化后的中文描述（体量远小于原 JSON）
    """
    def _names(items: List[Any]) -> str:
        if not items:
            return '无'
        names = []
        for x in items:
            if isinstance(x, dict):
                names.append(x.get('name', str(x)))
            else:
                names.append(str(x))
        return '、'.join(names) if names else '无'
    
    lines = []
    
    logger.debug(f"[_format_xishen_jishen_for_llm] shishen_mingge={data.get('shishen_mingge', [])}")
    
    # 喜神五行
    xi = data.get('xi_shen_elements', [])
    lines.append(f"【喜神】{_names(xi)}")
    
    # 忌神五行
    ji = data.get('ji_shen_elements', [])
    lines.append(f"【忌神】{_names(ji)}")
    
    # 旺衰与总分
    wangshuai = data.get('wangshuai', '')
    total_score = data.get('total_score', 0)
    lines.append(f"【旺衰】{wangshuai}({total_score}分)")
    
    # 十神命格（取 name）
    mingge = data.get('shishen_mingge', [])
    lines.append(f"【十神命格】{_names(mingge)}")
    
    # 四柱：年乙丑 月己卯 日戊午 时丙辰
    pillars = data.get('bazi_pillars', {})
    if pillars:
        pillar_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
        parts = []
        for key in ['year', 'month', 'day', 'hour']:
            p = pillars.get(key, {})
            if isinstance(p, dict):
                s = p.get('stem', '') + p.get('branch', '')
            else:
                s = str(p)
            if s:
                parts.append(f"{pillar_names.get(key, key)}{s}")
        if parts:
            lines.append(f"【四柱】{' '.join(parts)}")
    
    # 日主
    day_stem = data.get('day_stem', '')
    if day_stem:
        lines.append(f"【日主】{day_stem}")
    
    # 可选：五行个数（只保留分析必需，简写）
    element_counts = data.get('element_counts', {})
    if element_counts and isinstance(element_counts, dict):
        parts = [f"{e}{c}" for e, c in element_counts.items() if c]
        if parts:
            lines.append(f"【五行个数】{' '.join(parts)}")
    
    # 可选：十神简表（四柱主星）
    ten_gods = data.get('ten_gods', {})
    if ten_gods and isinstance(ten_gods, dict):
        pillar_labels = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
        parts = []
        for key in ['year', 'month', 'day', 'hour']:
            tg = ten_gods.get(key, {})
            if isinstance(tg, dict):
                main = tg.get('main_star', '')
                if main:
                    parts.append(f"{pillar_labels.get(key, key)}{main}")
        if parts:
            lines.append(f"【十神】{'、'.join(parts)}")
    
    # 十神对照（从底层 detail_result.details 组装，不重算）
    try:
        from server.utils.prompts.common import format_ten_gods_reference_from_details, format_branch_relations_text, format_key_dayuns_text
        ten_gods_ref = format_ten_gods_reference_from_details(data.get('_details', {}), data.get('_bazi_pillars', {}))
        if ten_gods_ref:
            lines.append(f"【十神对照】{ten_gods_ref}")
        branch_relations = data.get('_branch_relations', {})
        if branch_relations:
            relations_text = format_branch_relations_text(branch_relations)
            if relations_text and relations_text != "无":
                lines.append(f"【地支关系】{relations_text}")
        key_dayuns = data.get('_key_dayuns', [])
        current_dayun = data.get('_current_dayun', {})
        special_liunians = data.get('_special_liunians', [])
        if current_dayun or key_dayuns:
            lines.extend(format_key_dayuns_text(
                key_dayuns=key_dayuns,
                current_dayun=current_dayun,
                special_liunians=special_liunians
            ))
    except Exception:
        pass
    
    return '\n'.join(lines)

# 双轨并行：编排层开关，默认关闭
USE_ORCHESTRATOR_XISHEN_JISHEN = os.environ.get("USE_ORCHESTRATOR_XISHEN_JISHEN", "false").lower() == "true"


class XishenJishenRequest(BaziBaseRequest):
    """喜神忌神请求模型"""
    pass


class XishenJishenResponse(BaseModel):
    """喜神忌神响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# --- 内部函数（供编排器调用，不注册为 HTTP 端点） ---
# [REMOVED] @router.post("/bazi/xishen-jishen", deprecated=True) 已下线

async def get_xishen_jishen(request: XishenJishenRequest):
    """
    获取喜神五行、忌神五行和十神命格
    
    ⚠️ **接口已标记为下线（deprecated）**
    
    此接口已标记为下线，建议使用流式接口：`POST /api/v1/bazi/xishen-jishen/stream`
    流式接口返回相同的基础数据（type: 'data'），并额外提供流式LLM分析。
    
    根据用户的生辰（与基础八字排盘生辰同）：
    1. 从旺衰分析中获取喜神五行和忌神五行
    2. 从公式分析中获取十神命格
    3. 查询配置表获取对应的ID
    
    Returns:
        - xi_shen_elements: 喜神五行列表（包含名称和ID）
        - ji_shen_elements: 忌神五行列表（包含名称和ID）
        - shishen_mingge: 十神命格列表（包含名称和ID）
    """
    logger.warning("⚠️ [DEPRECATED] 非流式接口 /bazi/xishen-jishen 已标记为下线，建议使用流式接口 /bazi/xishen-jishen/stream")
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
        
        # >>> 缓存检查（喜神忌神固定，不随时间变化）<<<
        cache_key = generate_cache_key("xishen", final_solar_date, final_solar_time, request.gender)
        cached = get_cached_result(cache_key, "xishen-jishen")
        if cached:
            logger.info(f"✅ 喜神忌神缓存命中")
            return XishenJishenResponse(success=True, data=cached)
        # >>> 缓存检查结束 <<<
        
        # 双轨并行：优先走编排层（USE_ORCHESTRATOR_XISHEN_JISHEN=true 时）
        if USE_ORCHESTRATOR_XISHEN_JISHEN:
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                final_solar_date,
                final_solar_time,
                request.gender,
                modules={"xishen_jishen": True},
                preprocessed=True,
                calendar_type=request.calendar_type or "solar",
                location=request.location,
                latitude=request.latitude,
                longitude=request.longitude,
            )
            xishen_result = orchestrator_data.get("xishen_jishen")
            if xishen_result is not None:
                if isinstance(xishen_result, dict):
                    return XishenJishenResponse(**xishen_result)
                if hasattr(xishen_result, "model_dump"):
                    return XishenJishenResponse(**xishen_result.model_dump())
                if hasattr(xishen_result, "dict"):
                    return XishenJishenResponse(**xishen_result.dict())
            # 降级到原有逻辑
            logger.warning("编排层喜神忌神数据为空，降级到原有逻辑")
        
        # 1. 获取旺衰分析结果（包含喜神五行和忌神五行）
        # ✅ 修复：改为异步执行，避免阻塞事件循环
        import time
        start_time = time.time()
        loop = asyncio.get_event_loop()
        from server.utils.async_executor import get_executor
        try:
            # 使用统一线程池执行，添加30秒超时保护
            wangshuai_result = await asyncio.wait_for(
                loop.run_in_executor(
                    get_executor(),
                    WangShuaiService.calculate_wangshuai,
                    final_solar_date,
                    final_solar_time,
                    request.gender
                ),
                timeout=30.0
            )
            elapsed_time = time.time() - start_time
            logger.info(f"⏱️ 旺衰计算耗时: {elapsed_time:.2f}秒")
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ 旺衰计算超时（>{30.0}秒），耗时: {elapsed_time:.2f}秒")
            raise HTTPException(status_code=500, detail="旺衰计算超时，请稍后重试")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ 旺衰计算异常（耗时: {elapsed_time:.2f}秒）: {e}", exc_info=True)
            raise
        
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
            
            logger.info(f"   开始提取命格名称，规则ID列表: {shishen_rule_ids}")
            logger.info(f"   rule_details 的键: {list(rule_details.keys())}")
            
            # ✅ 使用统一的命格提取器
            from server.services.mingge_extractor import extract_mingge_names_from_rules
            
            # 构建规则列表（从 rule_details 中提取）
            shishen_rules = []
            for rule_id in shishen_rule_ids:
                rule_detail = rule_details.get(str(rule_id), rule_details.get(rule_id, {}))
                logger.info(f"   规则 {rule_id}: rule_detail 存在 = {bool(rule_detail)}")
                if rule_detail:
                    logger.info(f"   规则 {rule_id}: 键 = {list(rule_detail.keys())}")
                    logger.info(f"   规则 {rule_id}: 结果字段 = {rule_detail.get('结果', rule_detail.get('result', '无'))[:80]}")
                    shishen_rules.append(rule_detail)
            
            logger.info(f"   ✅ 提取到 {len(shishen_rules)} 条规则详情")
            
            # 使用统一的提取器提取命格名称
            logger.info(f"   🔄 调用 extract_mingge_names_from_rules，输入规则数量: {len(shishen_rules)}")
            shishen_mingge_names = extract_mingge_names_from_rules(shishen_rules)
            
            logger.info(f"   🔚 extract_mingge_names_from_rules 返回: {shishen_mingge_names}")
        
        logger.info(f"   十神命格: {shishen_mingge_names}")
        
        # 与 data_assembler 保持一致：十神命格为空时使用默认「常格」
        if not shishen_mingge_names:
            shishen_mingge_names = ['常格']
        
        # 3. 映射ID
        xi_shen_elements = ConfigService.map_elements_to_ids(xi_shen_elements_raw)
        ji_shen_elements = ConfigService.map_elements_to_ids(ji_shen_elements_raw)
        shishen_mingge = ConfigService.map_mingge_to_ids(shishen_mingge_names)
        if not shishen_mingge and shishen_mingge_names:
            shishen_mingge = [{'name': '常格', 'id': None}]
        
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
        
        # >>> 缓存写入 <<<
        set_cached_result(cache_key, response_data, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        logger.info(f"✅ 喜神忌神获取成功")
        return XishenJishenResponse(success=True, data=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 喜神忌神API异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/bazi/xishen-jishen/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def xishen_jishen_test(request: XishenJishenRequest):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot）
    
    返回与流式接口相同格式的结构化数据（JSON），供评测脚本使用。
    确保 Coze 和百炼平台使用相同的输入数据。
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    
    **返回格式**：
    {
        "success": true,
        "input_data": {...},  # 结构化数据
        "formatted_data": "JSON字符串",  # 格式化后的JSON字符串
        "formatted_data_length": 1234
    }
    """
    try:
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 2. 使用统一数据服务获取数据（与流式接口一致）
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'xishen_jishen': True,
            'rules': {
                'types': ['shishen']
            }
        }
        
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
        
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        if hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        if not xishen_jishen_result or not xishen_jishen_result.get('success'):
            # orchestrator 内部异常被吞，回退直接调用以暴露真实错误
            import traceback as _tb
            try:
                direct_result = await get_xishen_jishen(request)
                if direct_result and direct_result.success:
                    xishen_jishen_result = direct_result.model_dump() if hasattr(direct_result, 'model_dump') else direct_result.dict()
                else:
                    return {"success": False, "error": "获取喜神忌神数据失败（直接调用也失败）"}
            except Exception as _fallback_err:
                return {
                    "success": False,
                    "error": f"获取喜神忌神数据失败: {_fallback_err}",
                    "traceback": _tb.format_exc()
                }
        
        data = xishen_jishen_result.get('data', xishen_jishen_result)
        
        # 3. 构建 input_data（结构化数据，与流式接口一致）
        input_data = {
            "shishen_mingge": data.get('shishen_mingge', []),
            "xi_shen_elements": data.get('xi_shen_elements', []),
            "ji_shen_elements": data.get('ji_shen_elements', []),
            "wangshuai": data.get('wangshuai', ''),
            "total_score": data.get('total_score', 0),
            "bazi_pillars": data.get('bazi_pillars', {}),
            "day_stem": data.get('day_stem', ''),
            "ten_gods": data.get('ten_gods', {}),
            "element_counts": data.get('element_counts', {}),
            "deities": data.get('deities', {}),
            "wangshuai_detail": data.get('wangshuai_detail', {})
        }
        
        # 4. 格式化数据：优化前=完整JSON，优化后=描述文（供优化效果测试用）
        formatted_data = json.dumps(input_data, ensure_ascii=False, indent=2)
        formatted_data_length = len(formatted_data)
        formatted_for_llm = _format_xishen_jishen_for_llm(data)
        formatted_data_length_optimized = len(formatted_for_llm)
        
        # 5. 返回格式化后的数据
        return {
            "success": True,
            "input_data": input_data,
            "formatted_data": formatted_data,
            "formatted_data_length": formatted_data_length,
            "formatted_data_llm": formatted_for_llm,
            "formatted_data_llm_length": formatted_data_length_optimized,
            "formatted_data_length_optimized": formatted_data_length_optimized,
            "usage": {
                "description": "此接口返回的结构化数据可以直接用于 Coze Bot 或百炼智能体的输入（使用 {{input}} 占位符）",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/bazi/xishen-jishen/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}", "calendar_type": "{request.calendar_type or "solar"}"}}\''
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"❌ 喜神忌神测试接口异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def xishen_jishen_stream_generator(
    request: XishenJishenRequest,
    bot_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """
    流式生成喜神忌神大模型分析
    
    先返回完整的喜神忌神数据，然后流式返回大模型分析
    
    Args:
        request: 喜神忌神请求（与普通接口相同）
        bot_id: Coze Bot ID（可选）
    """
    import traceback
    import time
    
    # 记录开始时间和前端输入
    api_start_time = time.time()
    frontend_input = {
        'solar_date': request.solar_date,
        'solar_time': request.solar_time,
        'gender': request.gender,
        'calendar_type': request.calendar_type,
        'location': request.location,
        'latitude': request.latitude,
        'longitude': request.longitude
    }
    llm_first_token_time = None
    llm_output_chunks = []
    llm_start_time = None
    request_id = request_id or generate_request_id()
    
    try:
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        # 3. 使用统一数据服务获取数据
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        
        modules = {
            'bazi': True,
            'wangshuai': True,
            'xishen_jishen': True,
            'detail': True,
            'special_liunians': True,
            'rules': {
                'types': ['shishen']
            }
        }
        
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
        
        # 4. 提取已组装好的数据
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        if hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        if not xishen_jishen_result or not xishen_jishen_result.get('success'):
            error_msg = {
                'type': 'error',
                'content': '获取喜神忌神数据失败'
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        data = xishen_jishen_result.get('data', xishen_jishen_result)
        
        # 4.1 十神命格 fallback：orchestrator 的规则匹配可能无法命中 shishen 规则，
        #     此时用与非流式接口相同的 analyze_formula_rules 补全
        if not data.get('shishen_mingge'):
            try:
                from server.api.v1.formula_analysis import analyze_formula_rules, FormulaAnalysisRequest
                from server.services.mingge_extractor import extract_mingge_names_from_rules
                from server.services.config_service import ConfigService
                
                formula_request = FormulaAnalysisRequest(
                    solar_date=final_solar_date,
                    solar_time=final_solar_time,
                    gender=request.gender,
                    calendar_type=request.calendar_type or "solar",
                    location=request.location,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    rule_types=['shishen']
                )
                formula_result = await analyze_formula_rules(formula_request)
                
                if formula_result.success:
                    formula_data = formula_result.data
                    matched_rules = formula_data.get('matched_rules', {})
                    rule_details = formula_data.get('rule_details', {})
                    shishen_rule_ids = matched_rules.get('shishen', [])
                    shishen_rules = []
                    for rule_id in shishen_rule_ids:
                        rule_detail = rule_details.get(str(rule_id), rule_details.get(rule_id, {}))
                        if rule_detail:
                            shishen_rules.append(rule_detail)
                    shishen_mingge_names = extract_mingge_names_from_rules(shishen_rules)
                    if shishen_mingge_names:
                        data['shishen_mingge'] = ConfigService.map_mingge_to_ids(shishen_mingge_names)
                        logger.info(f"[喜神忌神流式] 十神命格 fallback 成功: {shishen_mingge_names}")
            except Exception as e:
                logger.warning(f"[喜神忌神流式] 十神命格 fallback 失败: {e}")
        
        # 5. 构建响应数据（与普通接口一致，但可能包含扩展字段）
        # 只返回基础字段给前端，扩展字段用于LLM分析
        response_data_base = {
            'solar_date': data.get('solar_date', request.solar_date),
            'solar_time': data.get('solar_time', request.solar_time),
            'gender': data.get('gender', request.gender),
            'xi_shen_elements': data.get('xi_shen_elements', []),
            'ji_shen_elements': data.get('ji_shen_elements', []),
            'shishen_mingge': data.get('shishen_mingge', []),
            'wangshuai': data.get('wangshuai', ''),
            'total_score': data.get('total_score', 0)
        }
        
        response_data = {
            'success': True,
            'data': response_data_base
        }
        
        # 6. 先发送完整的喜神忌神数据（type: "data"）
        data_msg = {
            'type': 'data',
            'content': response_data
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        
        # 6.5 注入统一数据源的扩展字段（十神对照、地支关系、大运流年）
        try:
            bazi_module = unified_data.get('bazi', {})
            bazi_data_raw = bazi_module.get('bazi', bazi_module) if isinstance(bazi_module, dict) and 'bazi' in bazi_module else bazi_module
            detail_result = unified_data.get('detail', {}) or {}
            data['_details'] = detail_result.get('details', {})
            data['_bazi_pillars'] = data.get('bazi_pillars', {}) or bazi_data_raw.get('bazi_pillars', {})
            data['_branch_relations'] = bazi_data_raw.get('relationships', {}).get('branch_relations', {})
            dayun_sequence = detail_result.get('dayun_sequence') or (detail_result.get('details') or {}).get('dayun_sequence', [])
            special_liunians_data = unified_data.get('special_liunians', {})
            special_liunians = special_liunians_data.get('list', []) if isinstance(special_liunians_data, dict) else []
            from server.utils.dayun_liunian_helper import calculate_user_age, get_current_dayun, select_dayuns_with_priority
            birth_date = bazi_data_raw.get('basic_info', {}).get('solar_date', '')
            current_age = calculate_user_age(birth_date) if birth_date else 0
            current_dayun = get_current_dayun(dayun_sequence, current_age) or {}
            key_dayuns = select_dayuns_with_priority(dayun_sequence, current_dayun, count=5)
            data['_current_dayun'] = current_dayun
            data['_key_dayuns'] = key_dayuns
            data['_special_liunians'] = special_liunians
        except Exception as e:
            logger.warning(f"[喜神忌神] 提取扩展数据失败（不影响核心功能）: {e}")
        
        # 7. 格式化为简洁中文描述（与五行占比一致，减少 token、去冗余）
        formatted_data = _format_xishen_jishen_for_llm(data)
        input_data = {"formatted_text": formatted_data, "char_count": len(formatted_data)}
        
        # 8. LLM 分析结果缓存（相同八字描述 → 相同分析结果）
        import hashlib
        llm_cache_key = f"llm_xishen:{hashlib.md5(formatted_data.encode()).hexdigest()}"
        try:
            cached_llm_result = get_cached_result(llm_cache_key, "llm-xishen")
            if cached_llm_result:
                logger.info(f"[喜神忌神] LLM 缓存命中: {llm_cache_key[:30]}...")
                cached_content = cached_llm_result.get('content', '')
                if cached_content:
                    chunk_size = 50
                    for i in range(0, len(cached_content), chunk_size):
                        chunk = cached_content[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'progress', 'content': chunk}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.01)
                    yield f"data: {json.dumps({'type': 'complete', 'content': ''}, ensure_ascii=False)}\n\n"
                    return
        except Exception as e:
            logger.warning(f"[喜神忌神] LLM 缓存读取失败: {e}")
        
        # 9. 创建 LLM 流式服务（根据数据库配置选择平台：coze 或 bailian）
        # 配置方式：在 service_configs 表中设置 XISHEN_JISHEN_LLM_PLATFORM = "bailian" 使用千问模型
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            from server.services.bailian_stream_service import BailianStreamService
            llm_service = LLMServiceFactory.get_service(scene="xishen_jishen", bot_id=None)
        except ValueError as e:
            # 配置缺失，跳过大模型分析
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        
        # 11. 流式生成大模型分析（与五行占比一致，无心跳）
        llm_start_time = time.time()
        stream_kwargs = {}
        if hasattr(llm_service, 'bot_id') and llm_service.bot_id:
            actual_bot_id = bot_id or get_config_from_db_only("XISHEN_JISHEN_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if actual_bot_id:
                stream_kwargs['bot_id'] = actual_bot_id
        
        async for result in llm_service.stream_analysis(formatted_data, **stream_kwargs):
            if llm_first_token_time is None and result.get('type') == 'progress':
                llm_first_token_time = time.time()
            if result.get('type') == 'progress':
                content = result.get('content', '')
                if content:
                    llm_output_chunks.append(content)
                msg = {'type': 'progress', 'content': content}
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)
            elif result.get('type') == 'complete':
                complete_content = result.get('content', '')
                if complete_content:
                    llm_output_chunks.append(complete_content)
                llm_output = ''.join(llm_output_chunks)
                if llm_output:
                    try:
                        set_cached_result(llm_cache_key, {'content': llm_output}, L2_TTL * 24)
                        logger.info(f"[喜神忌神] LLM 结果已缓存: {llm_cache_key[:30]}..., 长度={len(llm_output)}")
                    except Exception as e:
                        logger.warning(f"[喜神忌神] LLM 缓存写入失败: {e}")
                
                api_end_time = time.time()
                api_response_time_ms = int((api_end_time - api_start_time) * 1000)
                llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
                has_content = len(llm_output_chunks) > 0
                try:
                    from server.services.stream_call_logger import get_stream_call_logger
                    stream_logger = get_stream_call_logger()
                    stream_logger.log_async(
                        function_type='xishen_jishen',
                        frontend_api='/api/v1/bazi/xishen-jishen/stream',
                        frontend_input=frontend_input,
                        input_data=formatted_data if 'formatted_data' in locals() and formatted_data else '',
                        llm_output=llm_output,
                        api_total_ms=api_response_time_ms,
                        llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
                        llm_total_ms=llm_total_time_ms,
                        bot_id=actual_bot_id if 'actual_bot_id' in locals() else None,
                        llm_platform='bailian' if isinstance(llm_service, BailianStreamService) else 'coze',
                        status='success' if has_content else 'failed',
                        request_id=request_id,
                    )
                except Exception as e:
                    logger.warning(f"[喜神忌神流式] 数据库记录失败: {e}", exc_info=True)
                
                msg = {'type': 'complete', 'content': complete_content}
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                break
            elif result.get('type') == 'error':
                msg = {'type': 'error', 'content': result.get('content', '生成失败')}
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                break
        else:
            msg = {'type': 'complete', 'content': ''}
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
    except Exception as e:
        error_msg = {
            'type': 'error',
            'content': f"流式生成喜神忌神分析失败: {str(e)}\n{traceback.format_exc()}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        try:
            api_end_time = time.time()
            api_response_time_ms = int((api_end_time - api_start_time) * 1000)
            from server.services.stream_call_logger import get_stream_call_logger
            stream_logger = get_stream_call_logger()
            stream_logger.log_async(
                function_type='xishen_jishen',
                frontend_api='/api/v1/bazi/xishen-jishen/stream',
                frontend_input=frontend_input,
                api_total_ms=api_response_time_ms,
                llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
                status='failed',
                error_message=str(e),
                request_id=request_id,
            )
        except Exception as log_error:
            logger.warning(f"[喜神忌神流式] 错误记录失败: {log_error}", exc_info=True)


async def _xishen_jishen_stream_handler(request: Request):
    """内部处理函数，供 GET 和 POST 路由共享"""
    """
    流式生成喜神忌神大模型分析
    
    支持 GET 和 POST 两种方式：
    - GET: 通过 URL 参数传递（用于 EventSource API）
    - POST: 通过请求体传递（向后兼容）
    
    与 /bazi/xishen-jishen 接口相同的输入，但以SSE流式方式返回数据：
    1. 首先返回完整的喜神忌神数据（type: "data"）
    2. 然后流式返回大模型分析（type: "progress"）
    3. 最后返回完成标记（type: "complete"）
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD（当calendar_type=lunar时，可为农历日期）
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    - **calendar_type**: 历法类型：solar(阳历) 或 lunar(农历)，默认solar
    - **location**: 出生地点（用于时区转换，优先级1）
    - **latitude**: 纬度（用于时区转换，优先级2）
    - **longitude**: 经度（用于时区转换和真太阳时计算，优先级2）
    
    **返回格式**：
    SSE流式响应，每行格式：`data: {"type": "data|progress|complete|error", "content": ...}`
    
    **示例**：
    ```
    data: {"type": "data", "content": {"success": true, "data": {...}}}
    data: {"type": "progress", "content": "喜神忌神分析："}
    data: {"type": "progress", "content": "您的命局..."}
    data: {"type": "complete", "content": "完整的大模型分析内容"}
    ```
    """
    try:
        # 根据请求方法处理参数
        if request.method == "POST":
            # POST 请求：从请求体读取 JSON
            try:
                body_data = await request.json()
                params = XishenJishenRequest(**body_data)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"POST 请求体解析失败: {str(e)}"
                )
        else:
            # GET 请求：从 URL 参数手动读取（避免 FastAPI Query 依赖注入问题）
            query_params = request.query_params
            solar_date = query_params.get("solar_date")
            solar_time = query_params.get("solar_time")
            gender = query_params.get("gender")
            calendar_type = query_params.get("calendar_type")
            location = query_params.get("location")
            latitude_str = query_params.get("latitude")
            longitude_str = query_params.get("longitude")
            
            if not solar_date or not solar_time or not gender:
                raise HTTPException(
                    status_code=400,
                    detail="缺少必需参数：solar_date, solar_time, gender"
                )
            
            # 转换可选参数
            latitude = float(latitude_str) if latitude_str else None
            longitude = float(longitude_str) if longitude_str else None
            
            params = XishenJishenRequest(
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender,
                calendar_type=calendar_type,
                location=location,
                latitude=latitude,
                longitude=longitude
            )
        
        return StreamingResponse(
            xishen_jishen_stream_generator(params),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Encoding": "identity"  # ⚠️ 关键：禁止 GZip 压缩 SSE 流
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 流式生成异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"流式查询喜神忌神异常: {str(e)}"
        )


# 注册 GET 和 POST 路由（都指向同一个处理函数）
@router.get("/bazi/xishen-jishen/stream", summary="流式生成喜神忌神分析（GET）")
async def xishen_jishen_stream_get(request: Request):
    """GET 方式流式生成喜神忌神分析（用于 EventSource API）"""
    return await _xishen_jishen_stream_handler(request)


@router.post("/bazi/xishen-jishen/stream", summary="流式生成喜神忌神分析（POST）")
async def xishen_jishen_stream_post(request: Request):
    """POST 方式流式生成喜神忌神分析（向后兼容）"""
    return await _xishen_jishen_stream_handler(request)


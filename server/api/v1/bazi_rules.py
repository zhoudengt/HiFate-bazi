#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字规则匹配API接口（新增，不影响现有接口）
"""

import sys
import os
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.rule_service import RuleService
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services import selector_service
from server.services import nlg_service
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.api_error_handler import api_error_handler
from server.utils.async_executor import get_executor

# 尝试导入限流器（可选功能）
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False
    Limiter = None
    get_remote_address = None
    RateLimitExceeded = None

router = APIRouter()

# 双轨并行：编排层开关，默认关闭
USE_ORCHESTRATOR_BAZI_RULES = os.environ.get("USE_ORCHESTRATOR_BAZI_RULES", "false").lower() == "true"

# 简单内存限流存储（如果 slowapi 不可用时的降级方案）
_rate_limit_storage = {}  # {key: [(timestamp, count), ...]}
_rate_limit_lock = __import__('threading').Lock()  # 线程锁

# 限流依赖函数（如果 slowapi 可用）
def check_rate_limit_dependency(http_request: Request):
    """限流检查依赖函数"""
    from slowapi.util import get_remote_address
    key = get_remote_address(http_request)
    limit_count = 60  # 每分钟60次
    limit_seconds = 60  # 60秒
    
    if RATE_LIMIT_AVAILABLE and hasattr(http_request.app.state, 'limiter'):
        # 使用 slowapi
        limiter = http_request.app.state.limiter
        try:
            # 创建一个包装函数并应用装饰器
            @limiter.limit(f"{limit_count}/minute", key_func=get_remote_address)
            def _check(req: Request):
                return True
            _check(http_request)
            return  # 成功检查，返回
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="请求过于频繁，每分钟最多60次，请稍后再试")
        except Exception as e:
            # slowapi 失败，降级到简单限流
            import logging
            logging.warning(f"slowapi 限流检查失败，使用降级方案: {e}")
    
    # 降级方案：简单的内存限流（线程安全）
    import time
    current_time = time.time()
    
    # 使用锁确保线程安全
    with _rate_limit_lock:
        # 清理过期记录
        if key in _rate_limit_storage:
            _rate_limit_storage[key] = [
                (ts, cnt) for ts, cnt in _rate_limit_storage[key]
                if current_time - ts < limit_seconds
            ]
        else:
            _rate_limit_storage[key] = []
        
        # 计算当前时间窗口内的请求数
        current_count = sum(cnt for _, cnt in _rate_limit_storage[key])
        
        # 调试信息（生产环境可移除）
        import logging
        logger = logging.getLogger(__name__)
        if current_count > 25:  # 接近限流时记录
            logger.info(f"限流检查: key={key}, count={current_count}/{limit_count}")
        
        if current_count >= limit_count:
            logger.warning(f"触发限流: key={key}, count={current_count}")
            raise HTTPException(status_code=429, detail="请求过于频繁，每分钟最多60次，请稍后再试")
        
        # 增加计数
        _rate_limit_storage[key].append((current_time, 1))


class BaziRulesRequest(BaziBaseRequest):
    """八字规则匹配请求模型"""
    rule_types: Optional[List[str]] = Field(None, description="要匹配的规则类型列表，不指定则匹配所有类型", example=["rizhu_gender", "deity"])
    include_bazi: Optional[bool] = Field(True, description="是否包含八字计算结果", example=True)


class BaziRulesResponse(BaseModel):
    """八字规则匹配响应模型"""
    success: bool
    bazi_data: Optional[dict] = None
    matched_rules: List[dict] = []
    rule_count: int = 0
    message: Optional[str] = None


@router.post("/bazi/rules/match", response_model=BaziRulesResponse, summary="匹配八字规则")
@api_error_handler
async def match_bazi_rules(request: BaziRulesRequest, http_request: Request):
    """
    匹配八字规则（新增接口，不影响现有功能）
    
    注意：此接口为后端评测脚本使用，不需要在 gRPC 网关中注册
    
    根据用户的生辰八字信息，匹配相应的规则并返回匹配结果。
    支持复杂的条件匹配，包括：
    - 年柱、月柱、日柱、时柱条件
    - 四柱神煞条件（任意柱/特定柱）
    - 星运条件
    - 组合条件（AND/OR/NOT）
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    - **rule_types**: 要匹配的规则类型列表（可选）
    - **include_bazi**: 是否包含八字计算结果（默认True）
    
    返回匹配的规则列表和八字数据
    """
    # 处理农历输入和时区转换
    final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
        request.solar_date,
        request.solar_time,
        request.calendar_type or "solar",
        request.location,
        request.latitude,
        request.longitude
    )

    # 双轨并行：优先走编排层（USE_ORCHESTRATOR_BAZI_RULES=true 时）
    if USE_ORCHESTRATOR_BAZI_RULES:
        orchestrator_data = await BaziDataOrchestrator.fetch_data(
            final_solar_date,
            final_solar_time,
            request.gender,
            modules={
                "bazi": True,
                "rules": {"types": request.rule_types or []},
            },
            preprocessed=True,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
        )
        matched_rules = orchestrator_data.get("rules") or []
        bazi_result = None
        if request.include_bazi:
            bazi_result = orchestrator_data.get("bazi")
            if bazi_result and isinstance(bazi_result, dict):
                bazi_result = validate_bazi_data(bazi_result.get("bazi", bazi_result))
        bazi_data = orchestrator_data.get("bazi") or {}
    else:
        loop = asyncio.get_event_loop()
        from core.calculators.BaziCalculator import BaziCalculator
        calculator = BaziCalculator(final_solar_date, final_solar_time, request.gender)
        bazi_data = await loop.run_in_executor(
            get_executor(),
            calculator.build_rule_input
        )
        bazi_data = validate_bazi_data(bazi_data)
        bazi_result = None
        if request.include_bazi:
            bazi_result = await loop.run_in_executor(
                executor,
                BaziService.calculate_bazi_full,
                request.solar_date,
                request.solar_time,
                request.gender
            )
            if bazi_result and isinstance(bazi_result, dict):
                bazi_result = validate_bazi_data(bazi_result.get('bazi', bazi_result))
        if not bazi_data:
            raise ValueError("八字计算失败，请检查输入参数")
        matched_rules = await loop.run_in_executor(
            get_executor(),
            RuleService.match_rules,
            bazi_data,
            request.rule_types,
            True
        )

    response_data = {
        'success': True,
        'bazi_data': bazi_result if request.include_bazi else None,
        'matched_rules': matched_rules,
        'rule_count': len(matched_rules)
    }

    if conversion_info.get('converted') or conversion_info.get('timezone_info'):
        response_data['conversion_info'] = conversion_info

    return BaziRulesResponse(**response_data)


class CuratedRequest(BaziRulesRequest):
    """精选规则请求，继承基础入参，新增可选参数"""
    k: Optional[int] = Field(8, description="返回条数上限，默认8")
    use_nlg: Optional[bool] = Field(False, description="是否返回NLG拼装文本")
    min_per_tag: Optional[dict] = Field(None, description="每个tag最少条数，如 {\"事业\":1,\"情感\":1}")
    max_per_tag: Optional[dict] = Field(None, description="每个tag最多条数，如 {\"事业\":3}")
    weights: Optional[dict] = Field(None, description="打分权重覆盖，如 {\"match\":0.4}")


@router.post("/bazi/rules/curated", summary="精选规则（去冲突+多样化，可选NLG）")
@api_error_handler
async def curated_bazi_rules(
    request: CuratedRequest, 
    http_request: Request
):
    """
    在不改变现有逻辑的前提下，基于已匹配规则做：
    - 安全评分（字段缺失回退）
    - 冲突消解（互斥组/contradicts）
    - 多样化（按 tags 配额）
    可选返回 NLG 拼装文本，便于直出用户端。
    
    **限流策略**: 每分钟60次/IP（如果 slowapi 可用）
    """
    # 限流检查（在函数开始处直接调用）
    check_rate_limit_dependency(http_request)

    loop = asyncio.get_event_loop()
    from core.calculators.BaziCalculator import BaziCalculator
    calculator = BaziCalculator(request.solar_date, request.solar_time, request.gender)
    bazi_data = await loop.run_in_executor(
        get_executor(),
        calculator.build_rule_input
    )
    bazi_data = validate_bazi_data(bazi_data)
    candidates = await loop.run_in_executor(
        get_executor(),
        RuleService.match_rules,
        bazi_data,
        request.rule_types,
        True
    )
    user_profile = {"gender": request.gender}
    curated = await loop.run_in_executor(
        get_executor(),
        selector_service.select_curated,
        candidates,
        user_profile,
        request.k or 8,
        request.min_per_tag,
        request.max_per_tag,
        request.weights
    )
    response = {
        "success": True,
        "rule_count": len(curated),
        "curated_rules": curated
    }
    if request.use_nlg:
        text = await loop.run_in_executor(
            get_executor(),
            nlg_service.render_curated_as_text,
            curated
        )
        response["nlg_text"] = text
    return response


@router.get("/bazi/rules/types", summary="获取规则类型列表")
async def get_rule_types():
    """
    获取所有可用的规则类型列表
    """
    try:
        engine = RuleService.get_engine()
        rule_types = set()
        for rule in engine.rules:
            rule_types.add(rule.get('rule_type', 'default'))
        
        return {
            "success": True,
            "rule_types": sorted(list(rule_types)),
            "count": len(rule_types)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规则类型失败: {str(e)}")


@router.get("/bazi/rules/stats", summary="获取规则统计信息")
async def get_rules_stats():
    """
    获取规则引擎统计信息
    """
    try:
        engine = RuleService.get_engine()
        cache = RuleService.get_cache()
        
        # 统计规则类型
        rule_type_count = {}
        for rule in engine.rules:
            rule_type = rule.get('rule_type', 'default')
            rule_type_count[rule_type] = rule_type_count.get(rule_type, 0) + 1
        
        return {
            "success": True,
            "total_rules": len(engine.rules),
            "enabled_rules": len([r for r in engine.rules if r.get('enabled', True)]),
            "rule_types": rule_type_count,
            "cache_stats": cache.stats() if cache else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/bazi/rules/query-rizhu-gender", summary="查询日柱性别规则内容")
@api_error_handler
async def query_rizhu_gender_rule(request: BaziRulesRequest):
    """
    专门查询日柱性别规则的内容（新增接口）
    
    根据用户的生辰八字信息，动态查询日柱性别对应的命理分析内容。
    使用 RizhuGenderAnalyzer 动态查询，不需要预先配置所有组合。
    
    - **solar_date**: 阳历日期 (YYYY-MM-DD)
    - **solar_time**: 出生时间 (HH:MM)
    - **gender**: 性别 (male/female)
    
    返回匹配的日柱性别规则内容
    """
    loop = asyncio.get_event_loop()
    bazi_result = await loop.run_in_executor(
        get_executor(),
        BaziService.calculate_bazi_full,
        request.solar_date,
        request.solar_time,
        request.gender
    )
    bazi_data = {
        'basic_info': bazi_result.get('bazi', {}).get('basic_info', {}),
        'bazi_pillars': bazi_result.get('bazi', {}).get('bazi_pillars', {}),
        'details': bazi_result.get('bazi', {}).get('details', {}),
        'ten_gods_stats': bazi_result.get('bazi', {}).get('ten_gods_stats', {}),
        'elements': bazi_result.get('bazi', {}).get('elements', {}),
        'element_counts': bazi_result.get('bazi', {}).get('element_counts', {}),
        'relationships': bazi_result.get('bazi', {}).get('relationships', {})
    }
    matched_rules = await loop.run_in_executor(
        get_executor(),
        RuleService.match_rules,
        bazi_data,
        ['rizhu_gender_dynamic'],
        True
    )
    day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '')
    day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
    rizhu = f"{day_stem}{day_branch}"
    gender = bazi_data.get('basic_info', {}).get('gender', 'male')
    return {
        "success": True,
        "rizhu": rizhu,
        "gender": gender,
        "matched_rules": matched_rules,
        "rule_count": len(matched_rules),
        "message": f"日柱{rizhu}{'男' if gender == 'male' else '女'}命分析"
    }


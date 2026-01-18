#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-感情婚姻API
基于用户生辰数据，使用 Coze Bot 流式生成感情婚姻分析

优化特性:
- 支持请求级别的 trace_id 追踪
- 支持重试机制（通过 CozeStreamService）
- 支持备用 Token 自动切换
"""

import logging
import os
import sys
import uuid
import copy
from typing import Dict, Any, Optional, List
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
from server.services.bazi_detail_service import BaziDetailService
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.user_interaction_logger import get_user_interaction_logger
import time

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import organize_special_liunians_by_dayun
from server.utils.dayun_liunian_helper import (
    calculate_user_age,
    get_current_dayun,
    build_enhanced_dayun_structure
)
from server.config.input_format_loader import get_format_loader, build_input_data_from_result
from server.utils.prompt_builders import (
    format_marriage_input_data_for_coze as format_input_data_for_coze,
    _filter_empty_deities
)

logger = logging.getLogger(__name__)

router = APIRouter()


def build_marriage_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    special_liunians: List[Dict[str, Any]],
    gender: str
) -> Dict[str, Any]:
    """
    构建感情婚姻分析的输入数据
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        special_liunians: 特殊流年列表
        gender: 性别（male/female）
        
    Returns:
        dict: 感情婚姻分析的input_data
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
    
    # ⚠️ 关键修复：提取 bazi_pillars，处理可能为空或格式不正确的情况
    bazi_pillars_raw = bazi_data.get('bazi_pillars', {})
    bazi_pillars = {}
    
    # 如果 bazi_pillars 为空或格式不正确，尝试从 details 中提取
    if not bazi_pillars_raw or not isinstance(bazi_pillars_raw, dict) or len(bazi_pillars_raw) == 0:
        logger.warning(f"⚠️ bazi_pillars 为空或格式不正确，尝试从 details 中提取")
        # 尝试从 details 中提取四柱信息
        details = bazi_data.get('details', {})
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar_detail = details.get(pillar_name, {})
            if isinstance(pillar_detail, dict):
                # 如果 details 中有完整信息，从中提取
                # 注意：details 中可能没有 stem 和 branch，需要从其他地方提取
                pass
    else:
        # 处理 bazi_pillars 可能是字符串格式的情况（如 {"year": "乙酉"}）
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar_value = bazi_pillars_raw.get(pillar_name)
            if isinstance(pillar_value, str) and len(pillar_value) == 2:
                # 字符串格式（如 "乙酉"），解析为字典格式
                stem = pillar_value[0]
                branch = pillar_value[1]
                bazi_pillars[pillar_name] = {'stem': stem, 'branch': branch}
            elif isinstance(pillar_value, dict) and 'stem' in pillar_value and 'branch' in pillar_value:
                # 字典格式，直接使用
                bazi_pillars[pillar_name] = pillar_value
            else:
                # 其他格式或为空，使用空字典
                bazi_pillars[pillar_name] = {}
    
    # 如果 bazi_pillars 仍然为空，尝试从 BaziService 重新计算
    if not bazi_pillars or all(not p.get('stem') or not p.get('branch') for p in bazi_pillars.values()):
        logger.warning(f"⚠️ bazi_pillars 提取失败，尝试重新计算")
        try:
            # 从 basic_info 中获取日期和时间，重新计算
            basic_info = bazi_data.get('basic_info', {})
            solar_date = basic_info.get('solar_date', '')
            solar_time = basic_info.get('solar_time', '')
            gender = basic_info.get('gender', 'male')
            
            if solar_date and solar_time:
                # 重新计算八字（仅在本地，避免递归调用）
                from core.calculators.BaziCalculator import BaziCalculator
                calculator = BaziCalculator(solar_date, solar_time, gender)
                recalc_result = calculator.calculate()
                if recalc_result and 'bazi_pillars' in recalc_result:
                    recalc_pillars = recalc_result['bazi_pillars']
                    if isinstance(recalc_pillars, dict) and len(recalc_pillars) > 0:
                        bazi_pillars = recalc_pillars
                        logger.info(f"✅ 重新计算 bazi_pillars 成功")
        except Exception as e:
            logger.error(f"❌ 重新计算 bazi_pillars 失败: {e}")
    
    # ⚠️ 修复：从 wangshuai_result 中正确提取旺衰数据
    wangshuai_data = extract_wangshuai_data(wangshuai_result)
    
    # ⚠️ 修复：从 detail_result 或 bazi_data 中提取十神数据
    ten_gods_data = extract_ten_gods_data(detail_result, bazi_data)
    
    # 提取神煞数据
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
    
    # 提取地支刑冲破害数据
    branch_relations = {}
    try:
        relationships = bazi_data.get('relationships', {})
        branch_relations = relationships.get('branch_relations', {})
    except Exception as e:
        logger.warning(f"提取地支刑冲破害数据失败（不影响业务）: {e}")
    
    # 提取日柱数据（确保格式正确）
    day_pillar_raw = bazi_pillars.get('day', {})
    if isinstance(day_pillar_raw, dict) and 'stem' in day_pillar_raw and 'branch' in day_pillar_raw:
        day_pillar = day_pillar_raw
    else:
        # 如果格式不正确，尝试从 bazi_data 的 details 中提取
        day_pillar = {}
        try:
            details = bazi_data.get('details', {})
            day_detail = details.get('day', {})
            # details 中没有 stem 和 branch，需要从 bazi_pillars 中获取
            # 如果 bazi_pillars 为空，使用空字典
            if day_pillar_raw and isinstance(day_pillar_raw, dict):
                day_pillar = day_pillar_raw
        except Exception as e:
            logger.warning(f"提取日柱数据失败（不影响业务）: {e}")
            day_pillar = {}
    
    # ⚠️ 修复：从 wangshuai_data 中提取旺衰字符串
    wangshuai = wangshuai_data.get('wangshuai', '')
    
    # ⚠️ 优化：使用工具函数计算年龄和当前大运（与排盘系统一致）
    birth_date = bazi_data.get('basic_info', {}).get('solar_date', '')
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
    
    # 注意：不再限制流年数量，只按优先级排序。优先级仅用于排序，不省略数据。
    
    # 提取当前大运数据（优先级1）
    current_dayun_enhanced = enhanced_dayun_structure.get('current_dayun')
    current_dayun_data = None
    if current_dayun_enhanced:
        raw_liunians = current_dayun_enhanced.get('liunians', [])
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        # 按优先级排序，但不限制数量（保留所有流年）
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
            'liunians': all_liunians  # 不限制数量，保留所有流年（含 relations 字段）
        }
    
    # 提取关键大运数据（优先级2-10）
    key_dayuns_enhanced = enhanced_dayun_structure.get('key_dayuns', [])
    key_dayuns_data = []
    for key_dayun in key_dayuns_enhanced:
        raw_liunians = key_dayun.get('liunians', [])
        cleaned_liunians = [clean_liunian_data(liunian) for liunian in raw_liunians]
        # 按优先级排序，但不限制数量（保留所有流年）
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
            'liunians': all_liunians_for_dayun  # 不限制数量，保留所有流年（含 relations 字段）
        })
    
    # ⚠️ 修复：从 wangshuai_data 中提取喜忌数据
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
        # 命盘总论数据（包含：八字排盘、十神、旺衰、地支刑冲破害、日柱）
        'mingpan_zonglun': {
            'bazi_pillars': bazi_pillars,
            'ten_gods': ten_gods_data,
            'wangshuai': wangshuai,
            'branch_relations': branch_relations,
            'day_pillar': day_pillar
        },
        # 配偶特征数据（包含：十神、神煞、婚姻判词、桃花判词、婚配判词、正缘判词）
        'peiou_tezheng': {
            'ten_gods': ten_gods_data,
            'deities': deities_data,
            'marriage_judgments': [],  # 将在调用处填充
            'peach_blossom_judgments': [],  # 将在调用处填充
            'matchmaking_judgments': [],  # 将在调用处填充
            'zhengyuan_judgments': []  # 将在调用处填充
        },
        # 感情走势数据（包含：大运流年、十神）
        'ganqing_zoushi': {
            'current_dayun': current_dayun_data,
            'key_dayuns': key_dayuns_data,
            'ten_gods': ten_gods_data
        },
        # 神煞点睛数据（包含：神煞）
        'shensha_dianjing': {
            'deities': deities_data
        },
        # 建议方向数据（包含：十神、喜忌、大运流年）
        'jianyi_fangxiang': {
            'ten_gods': ten_gods_data,
            'xi_ji': xi_ji_data,
            'current_dayun': current_dayun_data,
            'key_dayuns': key_dayuns_data
        }
    }
    
    return input_data

# ✅ _filter_empty_deities 和 format_input_data_for_coze 函数已移至 server/utils/prompt_builders.py
# 通过顶部 import 导入，确保评测脚本和流式接口使用相同的函数


def validate_input_data(data: dict) -> tuple[bool, str]:
    """
    验证输入数据完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        (is_valid, error_message): 是否有效，错误信息（如果无效）
    """
    required_fields = {
        'mingpan_zonglun': {
            'bazi_pillars': '八字排盘',
            'ten_gods': '十神',
            'wangshuai': '旺衰',
            'branch_relations': '地支刑冲破害',
            'day_pillar': '日柱'
        },
        'peiou_tezheng': {
            'ten_gods': '十神',
            'deities': '神煞',
            'marriage_judgments': '婚姻判词',
            'peach_blossom_judgments': '桃花判词',
            'matchmaking_judgments': '婚配判词',
            'zhengyuan_judgments': '正缘判词'
        },
        'ganqing_zoushi': {
            'current_dayun': '当前大运',
            'key_dayuns': '关键大运',
            'ten_gods': '十神'
        },
        'shensha_dianjing': {
            'deities': '神煞'
        },
        'jianyi_fangxiang': {
            'ten_gods': '十神',
            'xi_ji': '喜忌',
            'current_dayun': '当前大运',
            'key_dayuns': '关键大运'
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
                # 对于列表和字典，允许为空（某些判词可能为空）
                pass
            elif isinstance(section_data[field], str) and not section_data[field].strip():
                # 对于字符串，允许为空（某些字段可能为空字符串）
                pass
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""


class MarriageAnalysisRequest(BaziBaseRequest):
    """感情婚姻分析请求模型"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID 环境变量）")


async def marriage_analysis_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    calendar_type: Optional[str] = "solar",
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    bot_id: Optional[str] = None,
    trace_id: Optional[str] = None
):
    """
    流式生成感情婚姻分析
    
    Args:
        solar_date: 阳历日期或农历日期
        solar_time: 出生时间
        gender: 性别
        calendar_type: 历法类型（solar/lunar），默认solar
        location: 出生地点（用于时区转换，优先级1）
        latitude: 纬度（用于时区转换，优先级2）
        longitude: 经度（用于时区转换和真太阳时计算，优先级2）
        bot_id: Coze Bot ID（可选，优先级：参数 > MARRIAGE_ANALYSIS_BOT_ID 环境变量）
        trace_id: 请求追踪ID（可选，用于日志关联）
    """
    # 生成或使用 trace_id
    trace_id = trace_id or str(uuid.uuid4())[:8]
    
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
    
    logger.info(f"[{trace_id}] 🚀 开始婚姻分析: solar_date={solar_date}, solar_time={solar_time}, gender={gender}")
    
    try:
        # 确定使用的 bot_id（优先级：参数 > 数据库配置 > 环境变量）
        if not bot_id:
            # 只从数据库读取，不降级到环境变量
            bot_id = get_config_from_db_only("MARRIAGE_ANALYSIS_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "数据库配置缺失: MARRIAGE_ANALYSIS_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置，或在请求参数中提供 bot_id。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        # 1. 处理农历输入和时区转换（支持7个标准参数）
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            calendar_type or "solar",
            location,
            latitude,
            longitude
        )
        
        # 2. 并行获取基础数据（带容错处理）
        loop = asyncio.get_event_loop()
        executor = None
        data_start_time = time.time()
        
        try:
            # 并行获取基础数据，使用 return_exceptions=True 实现容错
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
            
            # 使用 return_exceptions=True，即使某个任务失败也不会影响其他任务
            results = await asyncio.gather(
                bazi_task, wangshuai_task, detail_task,
                return_exceptions=True
            )
            bazi_result, wangshuai_result, detail_result = results
            
            data_duration = time.time() - data_start_time
            logger.info(f"[{trace_id}] 📊 并行数据获取完成: 耗时={data_duration:.2f}s")
            
            # 处理八字数据（核心数据，必须成功）
            if isinstance(bazi_result, Exception):
                logger.error(f"[{trace_id}] ❌ 八字计算失败: {bazi_result}")
                raise ValueError(f"八字计算失败: {bazi_result}")
            
            # 提取八字数据（BaziService.calculate_bazi_full 返回的结构是 {bazi: {...}, rizhu: {...}, matched_rules: [...]}）
            if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
                bazi_data = bazi_result['bazi']
            else:
                bazi_data = bazi_result
            
            # 验证数据类型
            bazi_data = validate_bazi_data(bazi_data)
            if not bazi_data:
                raise ValueError("八字计算失败，返回数据为空")
            
            # 处理旺衰数据（非核心数据，失败时使用默认值）
            if isinstance(wangshuai_result, Exception):
                logger.warning(f"[{trace_id}] ⚠️ 旺衰分析异常（使用默认值）: {wangshuai_result}")
                wangshuai_data = {}
            elif not wangshuai_result.get('success'):
                logger.warning(f"[{trace_id}] ⚠️ 旺衰分析失败（使用默认值）: {wangshuai_result.get('error')}")
                wangshuai_data = {}
            else:
                wangshuai_data = wangshuai_result.get('data', {})
            
            # 处理详情数据（非核心数据，失败时使用默认值）
            if isinstance(detail_result, Exception):
                logger.warning(f"[{trace_id}] ⚠️ 详情计算异常（使用默认值）: {detail_result}")
                detail_result = {'success': False, 'data': {}}
            
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
            
        except Exception as e:
            import traceback
            error_msg = {
                'type': 'error',
                'content': f"获取数据失败: {str(e)}\n{traceback.format_exc()}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 3. 获取规则匹配数据（婚姻、桃花等）
        marriage_judgments = []
        peach_blossom_judgments = []
        matchmaking_judgments = []
        zhengyuan_judgments = []
        
        try:
            matched_rules = await loop.run_in_executor(
                executor,
                RuleService.match_rules,
                bazi_data,
                ['marriage', 'peach_blossom', 'marriage_match', 'zhengyuan'],
                True  # use_cache
            )
            
            for rule in matched_rules:
                rule_type = rule.get('rule_type', '')
                content = rule.get('content', {})
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                rule_name = rule.get('rule_name', '')
                
                if 'marriage' in rule_type.lower() or '婚姻' in text:
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
                if 'peach' in rule_type.lower() or '桃花' in text:
                    peach_blossom_judgments.append({
                        'name': rule_name,
                        'text': text
                    })
        except Exception as e:
            logger.warning(f"规则匹配失败（不影响业务）: {e}")
        
        # 4. 构建 input_data（优先使用数据库格式定义，验证失败则降级到硬编码函数）
        use_hardcoded = False
        try:
            input_data = build_input_data_from_result(
                format_name='marriage_analysis',
                bazi_data=bazi_data,
                detail_result=detail_result,
                wangshuai_result=wangshuai_result,
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians,
                gender=gender
            )
            # 验证格式定义构建的数据是否完整
            is_valid_temp, validation_error_temp = validate_input_data(input_data)
            if not is_valid_temp:
                logger.warning(f"⚠️ 格式定义构建的数据不完整，降级到硬编码函数: {validation_error_temp}")
                use_hardcoded = True
            else:
                logger.info("✅ 使用数据库格式定义构建 input_data: marriage_analysis")
        except Exception as e:
            # 格式定义构建失败，降级到硬编码函数
            logger.warning(f"⚠️ 格式定义构建失败，使用硬编码函数: {e}")
            use_hardcoded = True
        
        if use_hardcoded:
            input_data = build_marriage_input_data(
                bazi_data,
                wangshuai_result,
                detail_result,
                dayun_sequence,
                special_liunians,
                gender
            )
        
        # 5. 填充判词数据（如果使用格式定义，判词数据可能已经在Redis中，这里作为补充）
        if 'peiou_tezheng' in input_data:
            if not input_data['peiou_tezheng'].get('marriage_judgments'):
                input_data['peiou_tezheng']['marriage_judgments'] = marriage_judgments
            if not input_data['peiou_tezheng'].get('peach_blossom_judgments'):
                input_data['peiou_tezheng']['peach_blossom_judgments'] = peach_blossom_judgments
            if not input_data['peiou_tezheng'].get('matchmaking_judgments'):
                input_data['peiou_tezheng']['matchmaking_judgments'] = matchmaking_judgments
            if not input_data['peiou_tezheng'].get('zhengyuan_judgments'):
                input_data['peiou_tezheng']['zhengyuan_judgments'] = zhengyuan_judgments
        
        # 6. 验证输入数据完整性
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            logger.error(f"数据完整性验证失败: {validation_error}")
            error_msg = {
                'type': 'error',
                'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        logger.info("✓ 数据完整性验证通过")
        
        # 7. ⚠️ 方案2：格式化数据为 Coze Bot 输入格式
        formatted_data = format_input_data_for_coze(input_data)
        logger.info(f"格式化数据长度: {len(formatted_data)} 字符")
        logger.debug(f"格式化数据前500字符: {formatted_data[:500]}")
        
        # 8. 创建 LLM 流式服务（支持 Coze 和百炼平台）
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            
            # 确保 bot_id 已设置（优先级：参数 > 数据库配置）
            if not bot_id:
                bot_id = get_config_from_db_only("MARRIAGE_ANALYSIS_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            
            logger.info(f"使用 Bot ID: {bot_id}")
            
            # 使用工厂获取 LLM 服务（根据配置自动选择 Coze 或百炼）
            llm_service = LLMServiceFactory.get_service(scene="marriage", bot_id=bot_id)
            
            # 如果是 Coze 服务，获取实际的 bot_id
            if hasattr(llm_service, 'bot_id'):
                actual_bot_id = bot_id or llm_service.bot_id
                logger.info(f"实际使用的 Bot ID: {actual_bot_id}")
            else:
                actual_bot_id = bot_id
                logger.info(f"使用百炼平台，场景: marriage")

        except ValueError as e:
            logger.error(f"LLM 服务配置错误: {e}")
            error_msg = {
                'type': 'error',
                'content': f"LLM 服务配置缺失: {str(e)}。请检查数据库配置 COZE_ACCESS_TOKEN 和 MARRIAGE_ANALYSIS_BOT_ID（或 COZE_BOT_ID），或 BAILIAN_API_KEY 和 BAILIAN_MARRIAGE_APP_ID。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            logger.error(f"初始化 LLM 服务失败: {e}", exc_info=True)
            error_msg = {
                'type': 'error',
                'content': f"初始化 LLM 服务失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 9. ⚠️ 方案2：流式生成（直接发送格式化后的数据）
        if hasattr(llm_service, 'bot_id'):
            actual_bot_id = bot_id or llm_service.bot_id
        else:
            actual_bot_id = bot_id
        logger.info(f"开始流式生成，Bot ID: {actual_bot_id}, 数据长度: {len(formatted_data)}")
        
        try:
            chunk_count = 0
            has_content = False
            
            logger.info(f"[{trace_id}] 📤 开始调用 LLM API: bot_id={actual_bot_id}, data_length={len(formatted_data)}")

            async for result in llm_service.stream_analysis(formatted_data, trace_id=trace_id, bot_id=actual_bot_id):
                chunk_count += 1
                
                # 转换为SSE格式
                if result.get('type') == 'progress':
                    content = result.get('content', '')
                    # 检测是否为错误消息
                    if '对不起' in content and '无法回答' in content:
                        logger.warning(f"检测到错误消息片段 (Bot ID: {actual_bot_id}): {content[:100]}")
                        # 跳过这个内容块，不显示给用户
                        continue
                    else:
                        has_content = True
                        msg = {
                            'type': 'progress',
                            'content': content
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
                    total_duration = time.time() - api_start_time
                    logger.info(f"[{trace_id}] ✅ 流式生成完成: chunks={chunk_count}, 耗时={total_duration:.2f}s")
                    return
                elif result.get('type') == 'error':
                    error_content = result.get('content', '未知错误')
                    logger.error(f"[{trace_id}] ❌ Coze API 返回错误: {error_content}")
                    msg = {
                        'type': 'error',
                        'content': error_content
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    return
            
            # 如果收到内容但没有收到 complete 消息，说明流式响应异常结束
            # 在这种情况下，发送一个 complete 消息，确保前端能够正常处理
            if has_content:
                # 收到了 progress 消息，但循环已结束（没有收到 complete）
                # 这可能是因为流式响应超时或被中断，但至少收到了一些内容
                logger.warning(f"[{trace_id}] ⚠️ 流式响应异常结束: 收到 {chunk_count} 个 chunks，但未收到 complete 消息")
                # 发送一个空的 complete 消息，让前端知道可以处理已收到的内容
                complete_msg = {
                    'type': 'complete',
                    'content': ''
                }
                yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
                total_duration = time.time() - api_start_time
                logger.info(f"[{trace_id}] ⚠️ 流式生成异常完成: chunks={chunk_count}, 耗时={total_duration:.2f}s（未收到 complete 消息）")
            elif not has_content:
                # 完全没有收到任何内容
                logger.warning(f"[{trace_id}] ⚠️ 未收到任何内容: chunks={chunk_count}")
                error_msg = {
                    'type': 'error',
                    'content': f'Coze Bot 未返回内容（Bot ID: {actual_bot_id}），请检查 Bot 配置和提示词'
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            import traceback
            logger.error(f"[{trace_id}] ❌ 流式生成异常: {e}\n{traceback.format_exc()}")
            error_msg = {
                'type': 'error',
                'content': f"流式生成失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
            # 记录错误
            api_end_time = time.time()
            api_response_time_ms = int((api_end_time - api_start_time) * 1000)
            logger_instance = get_user_interaction_logger()
            logger_instance.log_function_usage_async(
                function_type='marriage',
                function_name='八字命理-感情婚姻',
                frontend_api='/api/v1/bazi/marriage-analysis/stream',
                frontend_input=frontend_input,
                input_data=input_data if 'input_data' in locals() else {},
                llm_output='',
                llm_api='coze_api',
                api_response_time_ms=api_response_time_ms,
                llm_first_token_time_ms=None,
                llm_total_time_ms=None,
                round_number=1,
                bot_id=actual_bot_id if 'actual_bot_id' in locals() else None,
                status='failed',
                error_message=str(e),
                streaming=True
            )
    
    except Exception as e:
        import traceback
        logger.error(f"[{trace_id}] ❌ 流式生成器异常: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"流式生成失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='marriage',
            function_name='八字命理-感情婚姻',
            frontend_api='/api/v1/bazi/marriage-analysis/stream',
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


async def extract_marriage_analysis_data(
    solar_date: str,
    solar_time: str,
    gender: str
) -> Dict[str, Any]:
    """
    提取婚姻分析所需的元数据（不调用 Coze API）
    
    Args:
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        
    Returns:
        包含所有元数据的字典
    """
    try:
        # 1. 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            "solar",
            None,
            None,
            None
        )
        
        # 2. 并行获取八字排盘、旺衰数据和详细八字数据（包含大运数据）
        loop = asyncio.get_event_loop()
        bazi_task = loop.run_in_executor(
            None,
            lambda: BaziService.calculate_bazi_full(
                final_solar_date,
                final_solar_time,
                gender
            )
        )
        wangshuai_task = loop.run_in_executor(
            None,
            lambda: WangShuaiService.calculate_wangshuai(
                final_solar_date,
                final_solar_time,
                gender
            )
        )
        detail_task = loop.run_in_executor(
            None,
            lambda: BaziDetailService.calculate_detail_full(
                final_solar_date,
                final_solar_time,
                gender
            )
        )
        
        bazi_result, wangshuai_result, detail_result = await asyncio.gather(bazi_task, wangshuai_task, detail_task)
        
        # ⚠️ 关键修复：提取八字数据（BaziService.calculate_bazi_full 返回的结构是 {bazi: {...}, rizhu: {...}, matched_rules: [...]}）
        if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
            bazi_data = bazi_result['bazi']
        else:
            bazi_data = bazi_result
        
        # 验证数据类型
        bazi_data = validate_bazi_data(bazi_data)
        if not bazi_data:
            raise ValueError("八字计算失败，返回数据为空")
        
        # ⚠️ 修复：从 wangshuai_result 中提取旺衰数据
        if isinstance(wangshuai_result, Exception):
            logger.warning(f"⚠️ 旺衰分析异常（使用默认值）: {wangshuai_result}")
            wangshuai_data = {}
        elif not wangshuai_result.get('success'):
            logger.warning(f"⚠️ 旺衰分析失败（使用默认值）: {wangshuai_result.get('error')}")
            wangshuai_data = {}
        else:
            wangshuai_data = wangshuai_result.get('data', {})
        
        # 3. 获取规则匹配数据
        marriage_judgments = []
        peach_blossom_judgments = []
        matchmaking_judgments = []
        zhengyuan_judgments = []
        
        try:
            matched_rules = RuleService.match_rules(
                bazi_data,
                rule_types=['marriage', 'peach_blossom', 'marriage_match', 'zhengyuan']
            )
            
            for rule in matched_rules:
                rule_type = rule.get('rule_type', '')
                content = rule.get('content', {})
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                rule_name = rule.get('rule_name', '')
                
                if 'marriage' in rule_type.lower() or '婚姻' in text:
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
                if 'peach' in rule_type.lower() or '桃花' in text:
                    peach_blossom_judgments.append({
                        'name': rule_name,
                        'text': text
                    })
        except Exception as e:
            logger.warning(f"规则匹配失败（不影响业务）: {e}")
        
        # 4. 提取大运流年数据（从 detail_result 获取，包含完整大运序列）
        dayun_list = []
        try:
            # 从 detail_result 获取大运序列（detail_result 包含完整的大运数据）
            dayun_sequence = detail_result.get('dayun_sequence', [])
            
            # 跳过第0个"小运"，获取索引1、2、3的大运（第2-4步）
            for idx in [1, 2, 3]:
                if idx < len(dayun_sequence):
                    dayun = dayun_sequence[idx]
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
        
        # 5. 提取神煞数据
        deities_data = {}
        try:
            deities_data = bazi_data.get('deities', {})
        except Exception as e:
            logger.warning(f"提取神煞数据失败（不影响业务）: {e}")
        
        # 6. 提取十神数据
        ten_gods_data = bazi_data.get('ten_gods_stats', {})
        if not ten_gods_data:
            logger.warning("十神数据为空，可能影响分析结果")
        
        # 7. 提取地支刑冲破害数据
        branch_relations = {}
        try:
            relationships = bazi_data.get('relationships', {})
            branch_relations = relationships.get('branch_relations', {})
        except Exception as e:
            logger.warning(f"提取地支刑冲破害数据失败（不影响业务）: {e}")
        
        # 8. 提取日柱数据
        day_pillar = {}
        try:
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            day_pillar = bazi_pillars.get('day', {})
        except Exception as e:
            logger.warning(f"提取日柱数据失败（不影响业务）: {e}")
        
        # 9. 提取喜忌数据
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
        
        # 10. ⚠️ 优化：使用新的 build_marriage_input_data 函数构建 input_data
        # 需要获取大运序列和特殊流年
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # ✅ 修复：从 BaziDataService 获取特殊流年数据（与 stream 接口保持一致）
        special_liunians = []
        try:
            from server.services.bazi_data_service import BaziDataService
            
            # 获取完整运势数据（包含大运序列、流年序列、特殊流年）
            # 注意：extract_marriage_analysis_data 函数只接受基本参数，使用默认值
            fortune_data = await BaziDataService.get_fortune_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                calendar_type="solar",  # 使用默认值，与 BaziInputProcessor.process_input 一致
                location=None,  # 使用默认值
                latitude=None,  # 使用默认值
                longitude=None,  # 使用默认值
                include_dayun=True,
                include_liunian=True,
                include_special_liunian=True,
                dayun_mode=BaziDataService.DEFAULT_DAYUN_MODE,
                target_years=BaziDataService.DEFAULT_TARGET_YEARS,
                current_time=None
            )
            
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
            
            logger.info(f"[extract_marriage_analysis_data] 获取到特殊流年数量: {len(special_liunians)}")
        except Exception as e:
            logger.warning(f"获取特殊流年数据失败（使用空列表）: {e}")
            special_liunians = []
        
        input_data = build_marriage_input_data(
            bazi_data,
            wangshuai_data,  # ✅ 修复：变量名应为 wangshuai_data
            detail_result,
            dayun_sequence,
            special_liunians,
            gender
        )
        
        # 填充判词数据
        input_data['peiou_tezheng']['marriage_judgments'] = marriage_judgments
        input_data['peiou_tezheng']['peach_blossom_judgments'] = peach_blossom_judgments
        input_data['peiou_tezheng']['matchmaking_judgments'] = matchmaking_judgments
        input_data['peiou_tezheng']['zhengyuan_judgments'] = zhengyuan_judgments
        
        # 11. 验证数据完整性
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            raise ValueError(f"数据完整性验证失败: {validation_error}")
        
        # ✅ 只返回 input_data，评测脚本使用相同的函数构建 formatted_data
        return {
            'success': True,
            'input_data': input_data,  # ✅ 统一字段名：input_data
            'summary': {
                'bazi_pillars': bool(input_data['mingpan_zonglun'].get('bazi_pillars')),
                'ten_gods': bool(input_data['mingpan_zonglun'].get('ten_gods')),
                'wangshuai': bool(input_data['mingpan_zonglun'].get('wangshuai')),
                'branch_relations': bool(input_data['mingpan_zonglun'].get('branch_relations')),
                'day_pillar': bool(input_data['mingpan_zonglun'].get('day_pillar')),
                'deities': bool(input_data['peiou_tezheng'].get('deities')),
                'marriage_judgments': len(input_data['peiou_tezheng'].get('marriage_judgments', [])),
                'current_dayun': bool(input_data['ganqing_zoushi'].get('current_dayun')),
                'key_dayuns': len(input_data['ganqing_zoushi'].get('key_dayuns', [])),
                'xi_ji': bool(input_data['jianyi_fangxiang'].get('xi_ji'))
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"提取数据失败: {e}\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.post("/bazi/marriage-analysis/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def marriage_analysis_test(request: MarriageAnalysisRequest):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        request: 感情婚姻分析请求参数
        
    Returns:
        dict: 包含格式化后的数据
    """
    try:
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, request.calendar_type or "solar", 
            request.location, request.latitude, request.longitude
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
            longitude=request.longitude
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
        from server.services.bazi_data_service import BaziDataService
        
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
        
        logger.info(f"[Marriage Test] ✅ 统一数据服务获取完成 - dayun: {len(dayun_sequence)}, special: {len(special_liunians)}")
        
        # 匹配规则
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        
        loop = asyncio.get_event_loop()
        executor = None
        
        matched_rules = await loop.run_in_executor(
            executor,
            RuleService.match_rules,
            rule_data,
            ['marriage', 'peach_blossom', 'marriage_match', 'zhengyuan'],
            True
        )
        
        # 构建input_data
        input_data = build_marriage_input_data(
            bazi_data,
            wangshuai_result,
            detail_result,
            dayun_sequence,
            special_liunians,
            request.gender
        )
        
        # 填充判词数据
        marriage_judgments = []
        peach_blossom_judgments = []
        matchmaking_judgments = []
        zhengyuan_judgments = []
        
        for rule in matched_rules:
            rule_type = rule.get('rule_type', '')
            content = rule.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            rule_name = rule.get('rule_name', '')
            
            if 'marriage' in rule_type.lower() or '婚姻' in text:
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
            if 'peach' in rule_type.lower() or '桃花' in text:
                peach_blossom_judgments.append({
                    'name': rule_name,
                    'text': text
                })
        
        input_data['peiou_tezheng']['marriage_judgments'] = marriage_judgments
        input_data['peiou_tezheng']['peach_blossom_judgments'] = peach_blossom_judgments
        input_data['peiou_tezheng']['matchmaking_judgments'] = matchmaking_judgments
        input_data['peiou_tezheng']['zhengyuan_judgments'] = zhengyuan_judgments
        
        # 格式化数据
        formatted_data = format_input_data_for_coze(input_data)
        
        return {
            "success": True,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_zonglun', {}).get('bazi_pillars', {}),
                "dayun_count": len(input_data.get('ganqing_zoushi', {}).get('key_dayuns', [])),
                "current_dayun_liunians_count": len(input_data.get('ganqing_zoushi', {}).get('current_dayun', {}).get('liunians', [])),
                "key_dayuns_count": len(input_data.get('ganqing_zoushi', {}).get('key_dayuns', [])),
                "xi_ji": input_data.get('jianyi_fangxiang', {}).get('xi_ji', {})
            },
            "usage": {
                "description": "此接口返回的数据可以直接用于 Coze Bot 的 {{input}} 占位符",
                "coze_bot_setup": "1. 登录 Coze 平台\n2. 找到'感情婚姻分析' Bot\n3. 进入 Bot 设置 → System Prompt\n4. 复制 docs/需求/Coze_Bot_System_Prompt_感情婚姻分析.md 中的提示词\n5. 粘贴到 System Prompt 中\n6. 保存设置",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/marriage-analysis/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}", "calendar_type": "{request.calendar_type or "solar"}"}}\''
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


@router.post("/bazi/marriage-analysis/debug", summary="调试端点：返回婚姻分析元数据（不调用 Coze）")
async def marriage_analysis_debug(request: MarriageAnalysisRequest):
    """
    调试端点：返回婚姻分析所需的元数据（不调用 Coze API）
    
    用于验证数据提取是否正确，便于调试和验证 Coze Bot prompt 配置。
    
    **参数说明**：
    - **solar_date**: 阳历日期（必填）
    - **solar_time**: 出生时间（必填）
    - **gender**: 性别（必填）
    
    **返回格式**：
    JSON 响应，包含完整的 input_data 和摘要信息
    """
    try:
        result = await extract_marriage_analysis_data(
            request.solar_date,
            request.solar_time,
            request.gender
        )
        return result
    except Exception as e:
        import traceback
        logger.error(f"调试端点异常: {e}\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


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
        # 生成 trace_id 用于请求追踪
        trace_id = str(uuid.uuid4())[:8]
        logger.info(f"[{trace_id}] 📥 收到婚姻分析请求: solar_date={request.solar_date}, gender={request.gender}")
        
        return StreamingResponse(
            marriage_analysis_stream_generator(
                request.solar_date,
                request.solar_time,
                request.gender,
                request.calendar_type,
                request.location,
                request.latitude,
                request.longitude,
                request.bot_id,
                trace_id=trace_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Trace-ID": trace_id  # 添加 trace_id 到响应头
            }
        )
    except Exception as e:
        import traceback
        logger.error(f"流式生成异常: {e}\n{traceback.format_exc()}")
        raise


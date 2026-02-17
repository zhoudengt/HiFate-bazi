#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-事业财富API
基于用户生辰数据，使用 Coze Bot 流式生成事业财富分析
"""

import logging
import os
import sys
import uuid
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
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.stream_call_logger import get_stream_call_logger
import time
from server.services.industry_service import IndustryService

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from server.utils.dayun_liunian_helper import (
    calculate_user_age,
    get_current_dayun,
    build_enhanced_dayun_structure
)
from server.config.input_format_loader import build_input_data_from_result
from server.utils.prompt_builders import (
    format_career_wealth_input_data_for_coze as format_input_data_for_coze,
    format_career_wealth_for_llm
)
from server.utils.analysis_helpers import (
    _calculate_ganzhi_elements, analyze_dayun_bazi_relation, identify_key_dayuns,
    extract_career_star, extract_wealth_star, check_shishang_shengcai,
    calculate_age, get_directions_from_elements, get_industries_from_elements,
    validate_analysis_input as _validate_base, ELEMENT_DIRECTION,
)

# ✅ 性能优化：导入流式缓存工具
from server.utils.stream_cache_helper import (
    get_llm_cache, set_llm_cache,
    compute_input_data_hash, LLM_CACHE_TTL
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 天干五行对照
STEM_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

# 天干阴阳对照
STEM_YIN_YANG = {
    "甲": "阳", "乙": "阴",
    "丙": "阳", "丁": "阴",
    "戊": "阳", "己": "阴",
    "庚": "阳", "辛": "阴",
    "壬": "阳", "癸": "阴"
}

# 地支对应月令
BRANCH_MONTH = {
    "寅": "寅月", "卯": "卯月", "辰": "辰月",
    "巳": "巳月", "午": "午月", "未": "未月",
    "申": "申月", "酉": "酉月", "戌": "戌月",
    "亥": "亥月", "子": "子月", "丑": "丑月"
}

# 五行对应方位
ELEMENT_DIRECTION = {
    "木": "东",
    "火": "南",
    "土": "中",
    "金": "西",
    "水": "北"
}

# 五行行业对照已改为从数据库读取（使用 IndustryService）


def build_career_wealth_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    special_liunians: List[Dict[str, Any]],
    gender: str
) -> Dict[str, Any]:
    """
    构建事业财富分析的输入数据
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        special_liunians: 特殊流年列表
        gender: 性别（male/female）
        
    Returns:
        dict: 事业财富分析的input_data
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
    
    # ⚠️ 修复：从 wangshuai_result 中正确提取旺衰数据
    wangshuai_data = extract_wangshuai_data(wangshuai_result)
    
    # ⚠️ 修复：从 detail_result 或 bazi_data 中提取十神数据
    ten_gods_data = extract_ten_gods_data(detail_result, bazi_data)
    
    # 提取十神统计（用于事业星和财富星分析）
    ten_gods_stats = bazi_data.get('ten_gods_stats', {})
    
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
    
    # 提取日柱、月柱、年柱、时柱
    day_pillar = bazi_pillars.get('day', {})
    month_pillar = bazi_pillars.get('month', {})
    year_pillar = bazi_pillars.get('year', {})
    hour_pillar = bazi_pillars.get('hour', {})
    
    # ⚠️ 修复：从 wangshuai_data 中提取旺衰字符串
    wangshuai = wangshuai_data.get('wangshuai', '')
    wangshuai_detail = wangshuai_data.get('detail', '')
    
    # 提取五行分布
    element_counts = bazi_data.get('element_counts', {})
    wuxing_distribution = {
        '木': element_counts.get('木', 0),
        '火': element_counts.get('火', 0),
        '土': element_counts.get('土', 0),
        '金': element_counts.get('金', 0),
        '水': element_counts.get('水', 0)
    }
    
    # 提取月令
    yue_ling = BRANCH_MONTH.get(month_pillar.get('branch', ''), '')
    
    # 提取格局类型
    geju_type = wangshuai_data.get('geju_type', '')
    
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
        birth_year=birth_year,
        business_type='career_wealth',
        bazi_data=bazi_data,
        gender=gender
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
        raw_liunians = key_dayun.get('liunians', [])
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
    
    # 提取事业星和财富星
    career_star = extract_career_star(ten_gods_stats)
    wealth_star = extract_wealth_star(ten_gods_stats)
    shishang_shengcai = check_shishang_shengcai(ten_gods_stats, ten_gods_data)
    
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
    
    # 获取方位和行业建议
    xi_elements = xi_ji_data.get('xi_ji_elements', {}).get('xi_shen', []) if isinstance(xi_ji_data.get('xi_ji_elements'), dict) else []
    ji_elements = xi_ji_data.get('xi_ji_elements', {}).get('ji_shen', []) if isinstance(xi_ji_data.get('xi_ji_elements'), dict) else []
    fangwei = get_directions_from_elements(xi_elements, ji_elements)
    hangye = get_industries_from_elements(xi_elements, ji_elements)
    
    # 构建input_data
    input_data = {
        # 命盘事业财富总论
        'mingpan_shiye_caifu_zonglun': {
            'day_master': {
                'stem': day_pillar.get('stem', ''),
                'branch': day_pillar.get('branch', ''),
                'element': STEM_ELEMENT.get(day_pillar.get('stem', ''), ''),
                'yin_yang': STEM_YIN_YANG.get(day_pillar.get('stem', ''), '')
            },
            'bazi_pillars': {
                'year': {'stem': year_pillar.get('stem', ''), 'branch': year_pillar.get('branch', '')},
                'month': {'stem': month_pillar.get('stem', ''), 'branch': month_pillar.get('branch', '')},
                'day': {'stem': day_pillar.get('stem', ''), 'branch': day_pillar.get('branch', '')},
                'hour': {'stem': hour_pillar.get('stem', ''), 'branch': hour_pillar.get('branch', '')}
            },
            'wuxing_distribution': wuxing_distribution,
            'wangshuai': wangshuai,
            'wangshuai_detail': wangshuai_detail,
            'yue_ling': yue_ling,
            'yue_ling_shishen': ten_gods_data.get('month', {}).get('main_star', ''),
            'gender': gender,
            'geju_type': geju_type,
            'geju_description': wangshuai_data.get('geju_description', ''),
            'ten_gods': ten_gods_data
        },
        # 事业星与事业宫
        'shiye_xing_gong': {
            'shiye_xing': career_star,
            'month_pillar_analysis': {
                'stem': month_pillar.get('stem', ''),
                'branch': month_pillar.get('branch', ''),
                'stem_shishen': ten_gods_data.get('month', {}).get('main_star', ''),
                'branch_shishen': '',
                'hidden_stems': ten_gods_data.get('month', {}).get('hidden_stars', []),
                'analysis': ''
            },
            'ten_gods': ten_gods_data,
            'ten_gods_stats': ten_gods_stats,
            'deities': deities_data,
            'career_judgments': []  # 将在调用处填充
        },
        # 财富星与财富宫
        'caifu_xing_gong': {
            'caifu_xing': wealth_star,
            'year_pillar_analysis': {
                'stem': year_pillar.get('stem', ''),
                'branch': year_pillar.get('branch', ''),
                'stem_shishen': ten_gods_data.get('year', {}).get('main_star', ''),
                'branch_shishen': '',
                'analysis': ''
            },
            'hour_pillar_analysis': {
                'stem': hour_pillar.get('stem', ''),
                'branch': hour_pillar.get('branch', ''),
                'stem_shishen': ten_gods_data.get('hour', {}).get('main_star', ''),
                'branch_shishen': '',
                'analysis': ''
            },
            'shishang_shengcai': shishang_shengcai,
            'caiku': {
                'has_caiku': False,
                'caiku_position': '',
                'caiku_status': '',
                'analysis': ''
            },
            'wealth_judgments': []  # 将在调用处填充
        },
        # 事业运势
        'shiye_yunshi': {
            'current_age': current_age,
            'current_dayun': current_dayun_data,
            'key_dayuns': key_dayuns_data,
            'special_liunians': special_liunians,  # ⚠️ 特殊流年（供公共模块按 dayun_step 分配到各运）
            'key_liunian': [],
            'chonghe_xinghai': {
                'dayun_relations': [],
                'liunian_relations': [],
                'key_conflicts': []
            }
        },
        # 财富运势
        'caifu_yunshi': {
            'wealth_stages': {
                'early': {'age_range': '1-30岁', 'stage_type': '', 'description': ''},
                'middle': {'age_range': '30-50岁', 'stage_type': '', 'description': ''},
                'late': {'age_range': '50岁以后', 'stage_type': '', 'description': ''}
            },
            'current_dayun': current_dayun_data,
            'key_dayuns': key_dayuns_data,
            'liunian_wealth_nodes': [],
            'caiku_timing': {
                'has_timing': False,
                'timing_years': [],
                'timing_description': ''
            }
        },
        # 提运建议
        'tiyun_jianyi': {
            'ten_gods_summary': '',
            'xi_ji': xi_ji_data,
            'fangwei': fangwei,
            'hangye': hangye,
            'wuxing_hangye': IndustryService.get_industry_mapping()
        }
    }
    
    return input_data

# ✅ format_input_data_for_coze 函数已移至 server/utils/prompt_builders.py
# 通过顶部 import 导入，确保评测脚本和流式接口使用相同的函数


def validate_input_data(data: dict) -> tuple:
    """
    验证输入数据完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        (is_valid, error_message): 是否有效，错误信息（如果无效）
    """
    required_fields = {
        'mingpan_shiye_caifu_zonglun': {
            'bazi_pillars': '八字排盘',
            'day_master': '日主信息',
            'ten_gods': '十神配置',
            'wangshuai': '旺衰分析',
        },
        'shiye_xing_gong': {
            'ten_gods': '十神配置',
            'shiye_xing': '事业星',
        },
        'caifu_xing_gong': {
            'caifu_xing': '财富星',
        },
        'shiye_yunshi': {
            'current_dayun': '当前大运',
            'key_dayuns': '关键大运',
        },
        'caifu_yunshi': {
            'current_dayun': '当前大运',
            'key_dayuns': '关键大运',
        },
        'tiyun_jianyi': {
            'xi_ji': '喜忌分析',
        },
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
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""




class CareerWealthRequest(BaziBaseRequest):
    """事业财富分析请求模型"""
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量 CAREER_WEALTH_BOT_ID）")


class CareerWealthResponse(BaseModel):
    """事业财富分析响应模型"""
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/career-wealth/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def career_wealth_analysis_test(request: CareerWealthRequest):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot 的 {{input}} 占位符）
    
    ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        request: 事业财富分析请求参数
        
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
        
        logger.info(f"[Career Wealth Test] ✅ 统一数据服务获取完成 - dayun: {len(dayun_sequence)}, special: {len(special_liunians)}")
        
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
            ['career', 'wealth', 'summary'],
            True
        )
        
        # 构建input_data（优先使用数据库格式定义）
        use_hardcoded = False
        try:
            input_data = build_input_data_from_result(
                format_name='career_wealth_analysis',
                bazi_data=bazi_data,
                detail_result=detail_result,
                wangshuai_result=wangshuai_result,
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians,
                gender=request.gender
            )
            # ✅ 检查格式定义构建的数据是否完整
            required_sections = ['mingpan_shiye_caifu_zonglun', 'shiye_xing_gong', 'caifu_xing_gong', 
                               'shiye_yunshi', 'caifu_yunshi', 'tiyun_jianyi']
            missing_sections = [s for s in required_sections if s not in input_data or not input_data[s]]
            if missing_sections:
                logger.warning(f"⚠️ 格式定义构建的数据不完整（缺少: {missing_sections}），降级到硬编码函数")
                use_hardcoded = True
            else:
                logger.info("✅ 使用数据库格式定义构建 input_data: career_wealth_analysis")
        except Exception as e:
            # 降级到硬编码函数
            logger.warning(f"⚠️ 格式定义构建失败，使用硬编码函数: {e}")
            use_hardcoded = True
        
        if use_hardcoded:
            input_data = build_career_wealth_input_data(
                bazi_data,
                wangshuai_result,
                detail_result,
                dayun_sequence,
                special_liunians,
                request.gender
            )
        
        # 填充判词数据
        career_judgments = []
        wealth_judgments = []
        for rule in matched_rules:
            rule_type = rule.get('rule_type', '')
            rule_name = rule.get('rule_name', '')
            content = rule.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            
            if rule_type == 'career':
                career_judgments.append({'name': rule_name, 'text': text})
            elif rule_type == 'wealth':
                wealth_judgments.append({'name': rule_name, 'text': text})
        
        # ⚠️ 安全访问：确保字段存在后再设置判词数据
        # 确保 input_data 是可修改的字典
        if not isinstance(input_data, dict):
            logger.warning(f"input_data 类型异常: {type(input_data)}, 转换为字典")
            input_data = dict(input_data) if hasattr(input_data, '__iter__') else {}
        
        # 使用 setdefault 确保字段存在
        input_data.setdefault('shiye_xing_gong', {})
        input_data.setdefault('caifu_xing_gong', {})
        
        # 确保子字段也是字典
        if not isinstance(input_data.get('shiye_xing_gong'), dict):
            input_data['shiye_xing_gong'] = {}
        if not isinstance(input_data.get('caifu_xing_gong'), dict):
            input_data['caifu_xing_gong'] = {}
        
        input_data['shiye_xing_gong']['career_judgments'] = career_judgments
        input_data['caifu_xing_gong']['wealth_judgments'] = wealth_judgments
        
        # ✅ 只返回 input_data，评测脚本使用相同的函数构建 formatted_data
        return {
            "success": True,
            "input_data": input_data,
            "data_summary": {
                "bazi_pillars": input_data.get('mingpan_shiye_caifu_zonglun', {}).get('bazi_pillars', {}),
                "dayun_count": len(input_data.get('shiye_yunshi', {}).get('key_dayuns', [])),
                "current_dayun_liunians_count": len(input_data.get('shiye_yunshi', {}).get('current_dayun', {}).get('liunians', [])),
                "key_dayuns_count": len(input_data.get('shiye_yunshi', {}).get('key_dayuns', [])),
                "xi_ji": input_data.get('tiyun_jianyi', {}).get('xi_ji', {})
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


@router.post("/career-wealth/debug", summary="调试：查看事业财富分析数据")
async def career_wealth_analysis_debug(request: CareerWealthRequest):
    """
    调试接口：返回 input_data（与流式接口使用相同的数据构建逻辑）
    
    ✅ 只返回 input_data，评测脚本使用相同的函数构建 formatted_data
    
    Args:
        request: 事业财富分析请求参数
        
    Returns:
        dict: 包含 input_data 的调试信息
    """
    try:
        # ✅ 直接调用 test 接口的逻辑（test 接口已返回 input_data）
        result = await career_wealth_analysis_test(request)
        
        # ✅ 只返回 input_data，不返回 formatted_data
        if result.get('success'):
            return {
                "success": True,
                "input_data": result.get('input_data', {}),
                "data_summary": result.get('data_summary', {})
            }
        return result
    except Exception as e:
        import traceback
        logger.error(f"调试接口失败: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/career-wealth/stream", summary="流式生成事业财富分析")
async def career_wealth_analysis_stream(request: CareerWealthRequest):
    """
    流式生成事业财富分析
    
    基于用户的八字数据，调用 Coze Bot 流式生成事业财富分析内容。
    """
    return StreamingResponse(
        career_wealth_stream_generator(
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


async def career_wealth_stream_generator(
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
    流式生成事业财富分析的生成器
    
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
    # 生成 trace_id 用于请求追踪
    trace_id = str(uuid.uuid4())[:8]
    
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
        
        # 1. 确定使用的 bot_id（优先级：参数 > 数据库配置 > 环境变量）
        if not bot_id:
            # 只从数据库读取，不降级到环境变量
            bot_id = get_config_from_db_only("CAREER_WEALTH_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "数据库配置缺失: CAREER_WEALTH_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"事业财富分析请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={bot_id}")
        
        # 2. 处理农历输入和时区转换（支持7个标准参数）
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            solar_date,
            solar_time,
            calendar_type or "solar",
            location,
            latitude,
            longitude
        )
        
        # 3. 通过 BaziDataOrchestrator 统一获取数据（主路径统一）
        try:
            from server.utils.analysis_stream_helpers import get_modules_config
            modules = get_modules_config('career_wealth')
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
            all_matched_rules = unified_data.get('rules', [])
        
        except Exception as e:
            import traceback
            error_msg = {'type': 'error', 'content': f"获取数据失败: {str(e)}"}
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 4. 处理规则匹配数据（已从 BaziDataOrchestrator 获取）
        career_judgments = []
        wealth_judgments = []
        for rule in all_matched_rules:
            rule_type = rule.get('rule_type', '')
            rule_name = rule.get('rule_name', '')
            content = rule.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            
            if rule_type == 'career':
                career_judgments.append({'name': rule_name, 'text': text})
            elif rule_type == 'wealth':
                wealth_judgments.append({'name': rule_name, 'text': text})
        
        # 5. 按规则类型分类判词
        career_judgments = []
        wealth_judgments = []
        for rule in all_matched_rules:
            rule_type = rule.get('rule_type', '')
            rule_name = rule.get('rule_name', '')
            content = rule.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            if rule_type == 'career':
                career_judgments.append({'name': rule_name, 'text': text})
            elif rule_type == 'wealth':
                wealth_judgments.append({'name': rule_name, 'text': text})
        
        # 6. 构建 input_data（优先使用数据库格式定义）
        use_hardcoded = False
        try:
            # 尝试从数据库格式定义构建
            input_data = build_input_data_from_result(
                format_name='career_wealth_analysis',
                bazi_data=bazi_data,
                detail_result=detail_result,
                wangshuai_result=wangshuai_result,
                rule_result={'matched_rules': all_matched_rules},
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians,
                gender=gender
            )
            # ✅ 检查格式定义构建的数据是否完整
            required_sections = ['mingpan_shiye_caifu_zonglun', 'shiye_xing_gong', 'caifu_xing_gong', 
                               'shiye_yunshi', 'caifu_yunshi', 'tiyun_jianyi']
            missing_sections = [s for s in required_sections if s not in input_data or not input_data[s]]
            if missing_sections:
                logger.warning(f"⚠️ 格式定义构建的数据不完整（缺少: {missing_sections}），降级到硬编码函数")
                use_hardcoded = True
            else:
                logger.info("✅ 使用数据库格式定义构建 input_data: career_wealth_analysis")
        except Exception as e:
            # 降级到硬编码函数
            logger.warning(f"⚠️ 格式定义构建失败，使用硬编码函数: {e}")
            use_hardcoded = True
        
        if use_hardcoded:
            input_data = build_career_wealth_input_data(
                bazi_data,
                wangshuai_result,
                detail_result,
                dayun_sequence,
                special_liunians,
                gender
            )
        
        # 6. 填充判词数据
        # ⚠️ 安全访问：确保字段存在后再设置判词数据
        if not isinstance(input_data, dict):
            logger.warning(f"input_data 类型异常: {type(input_data)}, 转换为字典")
            input_data = dict(input_data) if hasattr(input_data, '__iter__') else {}
        
        input_data.setdefault('shiye_xing_gong', {})
        input_data.setdefault('caifu_xing_gong', {})
        
        if not isinstance(input_data.get('shiye_xing_gong'), dict):
            input_data['shiye_xing_gong'] = {}
        if not isinstance(input_data.get('caifu_xing_gong'), dict):
            input_data['caifu_xing_gong'] = {}
        
        input_data['shiye_xing_gong']['career_judgments'] = career_judgments
        input_data['caifu_xing_gong']['wealth_judgments'] = wealth_judgments
        
        # 7. 验证数据完整性
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
        
        # 8. ⚠️ 优化：使用精简中文文本格式（Token 减少 85%）
        formatted_data = format_career_wealth_for_llm(input_data)
        logger.info(f"格式化数据长度: {len(formatted_data)} 字符（优化后）")
        logger.debug(f"格式化数据:\n{formatted_data}")
        
        # ✅ 性能优化：检查 LLM 缓存
        input_data_hash = compute_input_data_hash(input_data)
        cached_llm_content = get_llm_cache("career_wealth", input_data_hash)
        
        if cached_llm_content:
            logger.info(f"[{trace_id}] ✅ LLM 缓存命中: career_wealth")
            
            complete_msg = {
                'type': 'complete',
                'content': cached_llm_content
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            total_duration = time.time() - api_start_time
            logger.info(f"[{trace_id}] ✅ 从缓存返回完成: 耗时={total_duration:.2f}s")
            return
        
        logger.info(f"[{trace_id}] ❌ LLM 缓存未命中: career_wealth")
        
        # 9. 创建 LLM 流式服务（支持 Coze 和百炼平台）
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            from server.services.bailian_stream_service import BailianStreamService
            
            logger.info(f"使用 Bot ID: {bot_id}")
            llm_service = LLMServiceFactory.get_service(scene="career_wealth", bot_id=bot_id)
            if hasattr(llm_service, 'bot_id'):
                actual_bot_id = bot_id or llm_service.bot_id
            else:
                actual_bot_id = bot_id
            
        except ValueError as e:
            logger.error(f"LLM 服务配置错误: {e}")
            error_msg = {
                'type': 'error',
                'content': f"LLM 服务配置缺失: {str(e)}。请检查数据库配置 COZE_ACCESS_TOKEN 和 CAREER_WEALTH_BOT_ID（或 COZE_BOT_ID），或 BAILIAN_API_KEY 和 BAILIAN_CAREER_WEALTH_APP_ID。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            logger.error(f"初始化 LLM 服务失败: {e}", exc_info=True)
            error_msg = {'type': 'error', 'content': f"初始化 LLM 服务失败: {str(e)}"}
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 10. ⚠️ 方案2：流式生成（直接发送格式化后的数据）
        logger.info(f"开始流式生成，Bot ID: {actual_bot_id}, 数据长度: {len(formatted_data)}")
        
        try:
            chunk_count = 0
            has_content = False
            llm_start_time = time.time()
            
            async for result in llm_service.stream_analysis(formatted_data, bot_id=actual_bot_id):
                chunk_count += 1
                
                # 记录第一个token时间
                if llm_first_token_time is None and result.get('type') == 'progress':
                    llm_first_token_time = time.time()
                
                if result.get('type') == 'progress':
                    content = result.get('content', '')
                    llm_output_chunks.append(content)  # 收集输出内容
                    if '对不起' in content and '无法回答' in content:
                        logger.warning(f"检测到错误消息片段: {content[:100]}")
                        continue
                    else:
                        has_content = True
                        msg = {'type': 'progress', 'content': content}
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0)
                elif result.get('type') == 'complete':
                    has_content = True
                    complete_content = result.get('content', '')
                    llm_output_chunks.append(complete_content)  # 收集完整内容
                    msg = {'type': 'complete', 'content': complete_content}
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    
                    # ✅ 性能优化：缓存 LLM 生成结果
                    if complete_content:
                        set_llm_cache("career_wealth", input_data_hash, complete_content, LLM_CACHE_TTL)
                        logger.info(f"[{trace_id}] ✅ LLM 缓存已写入: career_wealth")
                    
                    logger.info(f"流式生成完成，共 {chunk_count} 个chunk")
                    break
                elif result.get('type') == 'error':
                    error_content = result.get('content', '未知错误')
                    logger.error(f"Coze API 返回错误: {error_content}")
                    msg = {'type': 'error', 'content': error_content}
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    break
            
            if not has_content:
                logger.warning(f"未收到任何内容，chunk_count: {chunk_count}")
                error_msg = {'type': 'error', 'content': f'Coze Bot 未返回内容，请检查 Bot 配置'}
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
            # 记录交互数据（异步，不阻塞）
            api_end_time = time.time()
            llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
            llm_output = ''.join(llm_output_chunks)
            
            stream_logger = get_stream_call_logger()
            stream_logger.log_async(
                function_type='wealth',
                frontend_api='/api/v1/bazi/career-wealth-analysis/stream',
                frontend_input=frontend_input,
                input_data=formatted_data if 'formatted_data' in locals() and formatted_data else '',
                llm_output=llm_output,
                api_total_ms=int((api_end_time - api_start_time) * 1000),
                llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
                llm_total_ms=llm_total_time_ms,
                bot_id=actual_bot_id,
                llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
                status='success' if has_content else 'failed'
            )
                
        except Exception as e:
            import traceback
            logger.error(f"流式生成异常: {e}\n{traceback.format_exc()}")
            error_msg = {'type': 'error', 'content': f"流式生成失败: {str(e)}"}
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
            # 记录错误
            api_end_time = time.time()
            stream_logger = get_stream_call_logger()
            stream_logger.log_async(
                function_type='wealth',
                frontend_api='/api/v1/bazi/career-wealth-analysis/stream',
                frontend_input=frontend_input,
                input_data=formatted_data if 'formatted_data' in locals() and formatted_data else '',
                llm_output='',
                api_total_ms=int((api_end_time - api_start_time) * 1000),
                llm_first_token_ms=None,
                llm_total_ms=None,
                bot_id=actual_bot_id if 'actual_bot_id' in locals() else None,
                llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
                status='failed',
                error_message=str(e)
            )
            
    except Exception as e:
        import traceback
        logger.error(f"事业财富分析失败: {e}\n{traceback.format_exc()}")
        error_msg = {'type': 'error', 'content': f"分析失败: {str(e)}"}
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='wealth',
            frontend_api='/api/v1/bazi/career-wealth-analysis/stream',
            frontend_input=frontend_input,
            input_data='',
            llm_output='',
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            llm_first_token_ms=None,
            llm_total_ms=None,
            llm_platform='bailian' if 'llm_service' in locals() and isinstance(llm_service, BailianStreamService) else 'coze',
            status='failed',
            error_message=str(e)
        )


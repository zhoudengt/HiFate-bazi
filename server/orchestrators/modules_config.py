#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一模块配置 - 所有接口的编排层模块配置集中管理

确保排盘接口、流式接口使用相同的数据结构和命名
所有接口必须通过 BaziDataOrchestrator.fetch_data() 获取数据

使用方法：
    from server.orchestrators.modules_config import get_modules_config
    
    modules = get_modules_config('pan_display')
    data = await BaziDataOrchestrator.fetch_data(..., modules=modules)
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 排盘展示接口配置
# ============================================================================

DISPLAY_MODULES = {
    # /api/v1/bazi/pan/display - 排盘展示
    'pan_display': {
        'bazi': True,               # 八字四柱、十神、五行
        'personality': True,        # 日柱性格分析（RizhuGenderAnalyzer）
        'rizhu': True,              # 日柱解析（RizhuLiujiaziService）
        'rules': {'types': None}    # 所有规则（内部筛选婚姻规则）
    },
    
    # /api/v1/bazi/interface - 基本信息（命宫、身宫、胎元等）
    'interface': {
        'bazi_interface': True,     # 完整界面数据（含命宫、身宫、胎元、命卦等）
        'shengong_minggong': True,  # 身宫命宫详细数据
    },
    
    # /api/v1/bazi/fortune/display - 大运流年流月（完整版，走统一编排）
    # 数据从编排层获取，格式化逻辑在 API 层的 _assemble_fortune_display_response()
    'fortune_display': {
        'bazi': True,               # 八字四柱（用于 pillars 格式化）
        # bazi_interface 不需要：前端 fortune/display 页面不使用 commander 字段，
        # 司令由 /bazi/pan/display 或 /bazi/shengong-minggong 提供。
        # 移除后 commander 默认为空字符串，响应结构不变。
        'detail': True,             # 大运流年流月完整数据
        'dayun': {                  # 大运筛选配置
            'mode': 'count',
            'count': 13             # 返回13个大运
        },
        'liunian': True,            # 流年
        'liuyue': True,             # 流月
        # 附加数据不请求（性能优化）
    },
    
    # /api/v1/bazi/shengong-minggong - 身宫命宫详细信息（完整版，走统一编排）
    # 数据从编排层获取，后处理逻辑在 API 层的 _assemble_shengong_minggong_response()
    'shengong_minggong': {
        'bazi': True,               # 八字四柱、日干（用于计算主星等）
        'bazi_interface': True,     # 获取身宫命宫胎元干支 + commander
        'detail': True,             # 大运流年流月（前端需要显示）
        'dayun': {
            'mode': 'count',
            'count': 13
        },
        'liunian': True,
        'liuyue': True,
    },
}


# ============================================================================
# 流式分析接口配置（从 analysis_stream_helpers.py 迁移）
# ============================================================================

STREAM_MODULES = {
    # 婚姻分析
    'marriage': {
        'bazi': True,
        'wangshuai': True,          # 含喜神、忌神
        'detail': True,
        'special_liunians': {
            'dayun_config': {'mode': 'count', 'count': 13},  # ⚠️ 统一为 count:13（与 fortune/display 一致）
            'target_years': [2025, 2026, 2027],
            'count': 200
        },
        'rules': {'types': ['marriage', 'peach_blossom', 'marriage_match', 'zhengyuan']}
    },
    
    # 健康分析
    'health': {
        'bazi': True,
        'wangshuai': True,
        'detail': True,
        'special_liunians': {
            'dayun_config': {'mode': 'count', 'count': 13},  # ⚠️ 统一为 count:13（与 fortune/display 一致）
            'target_years': [2025, 2026, 2027],
            'count': 200
        },
        'rules': {'types': ['health']}
    },
    
    # 子女分析
    'children': {
        'bazi': True,
        'wangshuai': True,
        'detail': True,
        'special_liunians': {
            'dayun_config': {'mode': 'count', 'count': 13},
            'target_years': [2025, 2026, 2027],
            'count': 200
        },
        'rules': {'types': ['children']}
    },
    
    # 事业财运分析
    'career_wealth': {
        'bazi': True,
        'wangshuai': True,
        'detail': True,
        'special_liunians': {
            'dayun_config': {'mode': 'count', 'count': 13},  # ⚠️ 统一为 count:13（与 fortune/display 一致）
            'target_years': [2025, 2026, 2027],
            'count': 200
        },
        'rules': {'types': ['career', 'wealth', 'summary']}
    },
    
    # 总评分析
    'general_review': {
        'bazi': True,
        'wangshuai': True,
        'detail': True,
        'special_liunians': {
            'dayun_config': {'mode': 'count', 'count': 13},  # ⚠️ 统一为 count:13（与 fortune/display 一致）
            'target_years': [2025, 2026, 2027],
            'count': 200
        },
        'rules': {'types': ['summary', 'shishen', 'career', 'wealth', 'marriage']}
    },
}


# ============================================================================
# 其他独立接口配置
# ============================================================================

OTHER_MODULES = {
    # /api/v1/bazi/xishen-jishen - 喜神忌神
    'xishen_jishen': {
        'bazi': True,
        'wangshuai': True,
        'xishen_jishen': True,
        'rules': {'types': ['shishen']}
    },
    
    # /api/v1/bazi/wuxing-proportion - 五行比例
    'wuxing_proportion': {
        'bazi': True,
        'wangshuai': True,
        'wuxing_proportion': True,
    },
    
    # /api/v1/bazi/daily-fortune-calendar - 日运日历
    'daily_fortune_calendar': {
        'bazi': True,
        'detail': True,
        'daily_fortune_calendar': True,
    },
}


def get_modules_config(scene: str, **kwargs) -> Dict[str, Any]:
    """
    获取场景的模块配置
    
    Args:
        scene: 场景名称，支持：
            - 排盘接口：pan_display, interface, fortune_display, shengong_minggong
            - 流式接口：marriage, health, children, career_wealth, general_review
            - 其他接口：xishen_jishen, wuxing_proportion, daily_fortune_calendar
        **kwargs: 可选参数，用于覆盖默认配置
            - dayun_count: 大运数量（默认13）
            - target_years: 目标年份列表
            - rule_types: 规则类型列表
        
    Returns:
        dict: 模块配置字典
        
    Raises:
        ValueError: 未知场景
        
    Example:
        >>> modules = get_modules_config('pan_display')
        >>> modules = get_modules_config('fortune_display', dayun_count=10)
        >>> modules = get_modules_config('marriage', target_years=[2024, 2025])
    """
    # 合并所有配置
    all_modules = {**DISPLAY_MODULES, **STREAM_MODULES, **OTHER_MODULES}
    
    if scene not in all_modules:
        raise ValueError(f"未知场景: {scene}，支持的场景: {list(all_modules.keys())}")
    
    # 复制配置，避免修改原始数据
    config = _deep_copy_dict(all_modules[scene])
    
    # 应用可选参数覆盖
    if 'dayun_count' in kwargs and 'dayun' in config:
        if isinstance(config['dayun'], dict):
            config['dayun']['count'] = kwargs['dayun_count']
    
    if 'target_years' in kwargs and 'special_liunians' in config:
        if isinstance(config['special_liunians'], dict):
            config['special_liunians']['target_years'] = kwargs['target_years']
    
    if 'rule_types' in kwargs and 'rules' in config:
        if isinstance(config['rules'], dict):
            config['rules']['types'] = kwargs['rule_types']
    
    return config


def _deep_copy_dict(d: Dict) -> Dict:
    """深度复制字典"""
    if not isinstance(d, dict):
        return d
    return {k: _deep_copy_dict(v) if isinstance(v, dict) else v for k, v in d.items()}


def get_all_scenes() -> Dict[str, list]:
    """获取所有支持的场景分类"""
    return {
        'display': list(DISPLAY_MODULES.keys()),
        'stream': list(STREAM_MODULES.keys()),
        'other': list(OTHER_MODULES.keys()),
    }


# ============================================================================
# 向后兼容：保留 analysis_stream_helpers.py 的接口
# ============================================================================

# 兼容旧接口命名
STREAM_ANALYSIS_MODULES = STREAM_MODULES


def get_stream_modules_config(scene: str) -> Dict[str, Any]:
    """
    获取流式分析场景的模块配置（向后兼容）
    
    等同于 get_modules_config(scene)，仅用于兼容旧代码
    """
    return get_modules_config(scene)

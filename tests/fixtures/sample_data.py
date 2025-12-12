#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据

提供标准化的测试数据，用于单元测试和集成测试
"""

from typing import List, Dict, Any

# ==================== 日期数据 ====================

# 有效日期列表
VALID_DATES: List[str] = [
    "2025-12-11",
    "2024-01-01",
    "2000-06-15",
    "1990-01-15",
    "1985-05-20",
]

# 无效日期列表
INVALID_DATES: List[str] = [
    "invalid",
    "not-a-date",
    "2025-13-01",  # 月份无效
    "2025-02-30",  # 日期无效
    "2025/12/11",  # 格式错误
]

# 边界日期
BOUNDARY_DATES: List[str] = [
    "1900-01-01",  # 最小日期
    "2100-12-31",  # 最大日期
    "2024-02-29",  # 闰年
    "2023-02-28",  # 非闰年
]

# ==================== 八字请求数据 ====================

BAZI_REQUESTS: List[Dict[str, Any]] = [
    {
        "solar_date": "1990-01-15",
        "solar_time": "12:00",
        "gender": "male",
        "expected": {
            "day_stem": "己",
            "day_branch": "巳"
        }
    },
    {
        "solar_date": "2000-06-15",
        "solar_time": "08:30",
        "gender": "female",
        "expected": {
            "year_ganzhi": "庚辰"
        }
    },
    {
        "solar_date": "1985-05-20",
        "solar_time": "23:30",  # 子时
        "gender": "male",
        "expected": {}
    },
]

# 无效八字请求
INVALID_BAZI_REQUESTS: List[Dict[str, Any]] = [
    {"solar_date": "invalid", "solar_time": "12:00", "gender": "male"},
    {"solar_date": "1990-01-15", "solar_time": "25:00", "gender": "male"},  # 时间无效
    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "invalid"},  # 性别无效
]

# ==================== 万年历期望数据 ====================

CALENDAR_EXPECTED: Dict[str, Dict[str, Any]] = {
    "2025-12-11": {
        "success": True,
        "lunar_date": "农历十月廿二",
        "shengxiao": "蛇",
        "xingzuo": "射手",
        "ganzhi": {
            "year": "乙巳",
            "month": "戊子",
            "day": "甲寅",
            "hour": "甲子"
        },
        "weekday": "星期四",
        "luck_level": "吉"
    },
    "2024-01-01": {
        "success": True,
        "lunar_date": "农历十一月二十",
        "shengxiao": "兔",
        "xingzuo": "摩羯"
    },
    "2000-06-15": {
        "success": True,
        "shengxiao": "龙"
    }
}

# ==================== 规则数据 ====================

SAMPLE_RULES: List[Dict[str, Any]] = [
    {
        "rule_code": "FORMULA_wealth_10001",
        "rule_type": "wealth",
        "rule_name": "财运规则1",
        "conditions": {
            "gender": "male",
            "wangshuai": ["身旺"]
        },
        "content": {"text": "财运测试"}
    },
    {
        "rule_code": "FORMULA_career_20001",
        "rule_type": "career",
        "rule_name": "事业规则1",
        "conditions": {
            "gender": "*"
        },
        "content": {"text": "事业测试"}
    }
]

# ==================== API 响应数据 ====================

SUCCESS_RESPONSE: Dict[str, Any] = {
    "success": True,
    "data": {},
    "error": None
}

ERROR_RESPONSE: Dict[str, Any] = {
    "success": False,
    "data": None,
    "error": "测试错误"
}

# ==================== 宜忌数据 ====================

SAMPLE_YI: List[str] = [
    "嫁娶", "祭祀", "开光", "出火", "出行",
    "拆卸", "修造", "动土", "解除", "开市"
]

SAMPLE_JI: List[str] = [
    "探病", "安葬", "入宅", "移徙"
]

# ==================== 神煞数据 ====================

SAMPLE_DEITIES: Dict[str, str] = {
    "xishen": "东北",
    "caishen": "东北",
    "fushen": "正北",
    "yanggui": "西南",
    "yingui": "东北"
}

# ==================== 吉神凶煞数据 ====================

SAMPLE_JISHEN: List[str] = [
    "月恩", "四相", "时德", "相日", "驿马",
    "天后", "天马", "天巫", "福德", "福生"
]

SAMPLE_XIONGSHA: List[str] = [
    "五虚", "八风", "归忌", "八专", "白虎"
]

# ==================== 规则类型映射 ====================

RULE_TYPE_MAPPING: Dict[str, str] = {
    "财富": "wealth",
    "婚姻": "marriage",
    "事业": "career",
    "子女": "children",
    "性格": "character",
    "总评": "summary",
    "身体": "health",
    "桃花": "peach_blossom",
    "十神命格": "shishen"
}

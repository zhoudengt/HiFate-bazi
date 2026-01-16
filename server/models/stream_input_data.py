#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口统一输入数据模型

设计原则：
1. 所有流式接口使用相同的数据结构
2. 数据来源统一：以 BaziDisplayService.get_fortune_display() 为准
3. 不做任何二次计算，直接透传排盘数据
4. 特殊年份、大运流年必须与排盘完全一致

使用方式：
    from server.models.stream_input_data import UnifiedBaziData, StreamInputData
    
    # 获取统一数据
    unified_data = await UnifiedBaziDataProvider.get_unified_data(...)
    
    # 组装为各接口所需的 input_data
    input_data = StreamDataAssembler.assemble_for_health(unified_data)
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from server.models.dayun import DayunModel
from server.models.liunian import LiunianModel
from server.models.special_liunian import SpecialLiunianModel


class BaziPillarsModel(BaseModel):
    """四柱数据模型（与排盘一致）"""
    year: Dict[str, Any] = Field(..., description="年柱")
    month: Dict[str, Any] = Field(..., description="月柱")
    day: Dict[str, Any] = Field(..., description="日柱")
    hour: Dict[str, Any] = Field(..., description="时柱")
    
    class Config:
        json_schema_extra = {
            "example": {
                "year": {"stem": "甲", "branch": "子", "nayin": "海中金"},
                "month": {"stem": "乙", "branch": "丑", "nayin": "海中金"},
                "day": {"stem": "丙", "branch": "寅", "nayin": "炉中火"},
                "hour": {"stem": "丁", "branch": "卯", "nayin": "炉中火"}
            }
        }


class WangShuaiModel(BaseModel):
    """
    旺衰数据模型（统一结构）
    
    注意：
    - xi_shen_elements 和 ji_shen_elements 是五行列表
    - xi_shen 和 ji_shen 是十神列表
    - 数据直接从 WangShuaiService 提取，不做转换
    """
    wangshuai: str = Field(..., description="旺衰判断", example="身旺")
    wangshuai_degree: Optional[int] = Field(None, description="旺衰程度(0-100)", example=65)
    total_score: Optional[int] = Field(None, description="总分", example=45)
    
    # 十神列表
    xi_shen: List[str] = Field(default_factory=list, description="喜神（十神）", example=["正财", "偏财", "正官"])
    ji_shen: List[str] = Field(default_factory=list, description="忌神（十神）", example=["比肩", "劫财", "印绶"])
    
    # 五行列表（关键！各服务使用这个）
    xi_shen_elements: List[str] = Field(default_factory=list, description="喜神（五行）", example=["木", "火"])
    ji_shen_elements: List[str] = Field(default_factory=list, description="忌神（五行）", example=["水", "金"])
    
    # 调候信息
    tiaohou: Optional[Dict[str, Any]] = Field(None, description="调候信息")
    final_xi_ji: Optional[Dict[str, Any]] = Field(None, description="最终喜忌（综合调候）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wangshuai": "身旺",
                "wangshuai_degree": 65,
                "total_score": 45,
                "xi_shen": ["正财", "偏财"],
                "ji_shen": ["比肩", "劫财"],
                "xi_shen_elements": ["木", "火"],
                "ji_shen_elements": ["水", "金"]
            }
        }


class BasicInfoModel(BaseModel):
    """基本信息模型"""
    solar_date: str = Field(..., description="阳历日期", example="1985-11-21")
    solar_time: str = Field(..., description="出生时间", example="06:30")
    gender: str = Field(..., description="性别", example="female")
    lunar_date: Optional[str] = Field(None, description="农历日期")
    lunar_time: Optional[str] = Field(None, description="农历时间")
    location: Optional[str] = Field(None, description="出生地点")
    
    class Config:
        json_schema_extra = {
            "example": {
                "solar_date": "1985-11-21",
                "solar_time": "06:30",
                "gender": "female"
            }
        }


class UnifiedBaziData(BaseModel):
    """
    统一八字数据模型
    
    这是所有流式接口的数据源，包含完整的八字信息。
    数据来源：BaziDisplayService.get_fortune_display()
    
    设计原则：
    1. 直接透传排盘数据，不做任何转换
    2. 特殊年份的 relations 字段必须与排盘完全一致
    3. 大运流年序列必须与排盘完全一致
    """
    
    # === 基础信息（所有接口必需）===
    basic_info: BasicInfoModel = Field(..., description="基本信息")
    bazi_pillars: BaziPillarsModel = Field(..., description="四柱")
    element_counts: Dict[str, int] = Field(default_factory=dict, description="五行统计")
    
    # === 旺衰喜忌（所有接口必需）===
    wangshuai: WangShuaiModel = Field(..., description="旺衰数据")
    
    # === 大运序列（完整列表，与排盘一致）===
    dayun_sequence: List[DayunModel] = Field(default_factory=list, description="大运序列")
    current_dayun: Optional[DayunModel] = Field(None, description="当前大运")
    
    # === 特殊流年（关键！必须与排盘完全一致）===
    special_liunians: List[SpecialLiunianModel] = Field(default_factory=list, description="特殊流年列表")
    
    # === 十神统计 ===
    ten_gods_stats: Optional[Dict[str, int]] = Field(None, description="十神统计")
    
    # === 详细数据（用于规则匹配等）===
    details: Optional[Dict[str, Any]] = Field(None, description="详细数据")
    
    # === 原始排盘数据（备用，不序列化）===
    # 注意：使用 exclude=True 使其不参与序列化
    raw_display_result: Optional[Dict[str, Any]] = Field(None, description="原始排盘数据（内部使用）", exclude=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "basic_info": {
                    "solar_date": "1985-11-21",
                    "solar_time": "06:30",
                    "gender": "female"
                },
                "bazi_pillars": {
                    "year": {"stem": "乙", "branch": "丑"},
                    "month": {"stem": "丁", "branch": "亥"},
                    "day": {"stem": "庚", "branch": "午"},
                    "hour": {"stem": "己", "branch": "卯"}
                },
                "element_counts": {"金": 2, "木": 1, "水": 2, "火": 2, "土": 1},
                "wangshuai": {
                    "wangshuai": "身旺",
                    "xi_shen_elements": ["木", "火"],
                    "ji_shen_elements": ["金", "水"]
                },
                "dayun_sequence": [],
                "special_liunians": []
            }
        }


class StreamInputData(BaseModel):
    """
    流式接口统一输入数据模型
    
    这是传给大模型的 input_data 结构。
    所有流式接口使用相同结构，按需填充不同字段。
    
    使用方式：
        # 从 UnifiedBaziData 组装
        input_data = StreamDataAssembler.assemble_for_health(unified_data)
    """
    
    # ==================== 第一层：命盘基础数据 ====================
    mingpan_tizhi_zonglun: Dict[str, Any] = Field(
        default_factory=dict, 
        description="命盘体质总论（日主、四柱、五行、旺衰）"
    )
    
    # ==================== 第二层：大运流年数据 ====================
    dayun_jiankang: Optional[Dict[str, Any]] = Field(
        None, 
        description="大运健康警示（当前大运、关键大运、特殊年份）"
    )
    
    # ==================== 第三层：五行病理数据（健康接口专用）====================
    wuxing_bingli: Optional[Dict[str, Any]] = Field(
        None, 
        description="五行病理推演"
    )
    
    # ==================== 第四层：调理建议（健康接口专用）====================
    tizhi_tiaoli: Optional[Dict[str, Any]] = Field(
        None, 
        description="体质调理建议（喜忌、脏腑养护）"
    )
    
    # ==================== 通用字段 ====================
    matched_rules: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="匹配的规则"
    )
    
    # ==================== 婚姻接口专用 ====================
    marriage_data: Optional[Dict[str, Any]] = Field(None, description="婚姻分析数据")
    
    # ==================== 事业财富接口专用 ====================
    career_wealth_data: Optional[Dict[str, Any]] = Field(None, description="事业财富分析数据")
    
    # ==================== 子女学业接口专用 ====================
    children_study_data: Optional[Dict[str, Any]] = Field(None, description="子女学业分析数据")
    
    # ==================== 总评接口专用 ====================
    general_review_data: Optional[Dict[str, Any]] = Field(None, description="总评分析数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mingpan_tizhi_zonglun": {
                    "bazi_pillars": {},
                    "day_master": {},
                    "elements": {},
                    "wangshuai": "身旺"
                },
                "dayun_jiankang": {
                    "current_dayun": {},
                    "key_dayuns": [],
                    "special_liunians_by_dayun": {}
                }
            }
        }

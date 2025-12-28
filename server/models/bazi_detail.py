#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整八字详细数据模型 - 统一的数据结构定义
包含大运序列、流年序列、特殊流年等
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from server.models.dayun import DayunModel
from server.models.liunian import LiunianModel
from server.models.special_liunian import SpecialLiunianModel


class BaziDetailModel(BaseModel):
    """完整八字详细数据模型"""
    # 基础八字数据
    basic_info: Optional[Dict[str, Any]] = Field(None, description="基本信息")
    bazi_pillars: Optional[Dict[str, Any]] = Field(None, description="四柱数据")
    ten_gods_stats: Optional[Dict[str, Any]] = Field(None, description="十神统计")
    elements: Optional[Dict[str, Any]] = Field(None, description="五行数据")
    element_counts: Optional[Dict[str, Any]] = Field(None, description="五行计数")
    relationships: Optional[Dict[str, Any]] = Field(None, description="关系数据")
    
    # 大运流年数据
    dayun_sequence: List[DayunModel] = Field(default_factory=list, description="大运序列")
    liunian_sequence: List[LiunianModel] = Field(default_factory=list, description="流年序列")
    special_liunians: List[SpecialLiunianModel] = Field(default_factory=list, description="特殊流年列表")
    
    # 当前大运流年信息
    current_dayun: Optional[DayunModel] = Field(None, description="当前大运")
    current_liunian: Optional[LiunianModel] = Field(None, description="当前流年")
    
    # 起运交运信息
    qiyun: Optional[Dict[str, Any]] = Field(None, description="起运信息")
    jiaoyun: Optional[Dict[str, Any]] = Field(None, description="交运信息")
    
    # 详细信息（原始数据）
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息（原始数据）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dayun_sequence": [],
                "liunian_sequence": [],
                "special_liunians": [],
                "current_dayun": None,
                "current_liunian": None,
                "qiyun": {},
                "jiaoyun": {}
            }
        }


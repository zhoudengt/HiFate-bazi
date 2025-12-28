#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年数据模型 - 统一的流年数据结构定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class LiunianModel(BaseModel):
    """流年数据模型"""
    year: int = Field(..., description="年份", example=2025)
    stem: str = Field(..., description="天干", example="乙")
    branch: str = Field(..., description="地支", example="巳")
    ganzhi: str = Field(..., description="干支", example="乙巳")
    age: Optional[int] = Field(None, description="年龄", example=35)
    age_display: Optional[str] = Field(None, description="年龄显示", example="35岁")
    nayin: Optional[str] = Field(None, description="纳音", example="覆灯火")
    main_star: Optional[str] = Field(None, description="主星", example="正财")
    hidden_stems: Optional[List[str]] = Field(None, description="藏干列表", example=["丙", "戊", "庚"])
    hidden_stars: Optional[List[str]] = Field(None, description="副星列表", example=["正财", "食神"])
    star_fortune: Optional[str] = Field(None, description="十二长生", example="沐浴")
    self_sitting: Optional[str] = Field(None, description="自坐", example="")
    kongwang: Optional[str] = Field(None, description="空亡", example="")
    deities: Optional[List[str]] = Field(None, description="神煞列表", example=["天乙贵人"])
    relations: Optional[List[Dict[str, Any]]] = Field(None, description="关系列表（冲合刑害等）", example=[{"type": "冲", "target": "日柱"}])
    liuyue_sequence: Optional[List[Dict[str, Any]]] = Field(None, description="流月序列（12个月）")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息（原始数据）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "year": 2025,
                "stem": "乙",
                "branch": "巳",
                "ganzhi": "乙巳",
                "age": 35,
                "age_display": "35岁",
                "nayin": "覆灯火",
                "main_star": "正财",
                "hidden_stems": ["丙", "戊", "庚"],
                "hidden_stars": ["正财", "食神"],
                "star_fortune": "沐浴",
                "self_sitting": "",
                "kongwang": "",
                "deities": ["天乙贵人"],
                "relations": [{"type": "冲", "target": "日柱"}]
            }
        }


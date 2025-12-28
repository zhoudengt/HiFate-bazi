#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大运数据模型 - 统一的大运数据结构定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class DayunModel(BaseModel):
    """大运数据模型"""
    step: int = Field(..., description="大运步骤（从0开始）", example=0)
    stem: str = Field(..., description="天干", example="甲")
    branch: str = Field(..., description="地支", example="子")
    ganzhi: str = Field(..., description="干支", example="甲子")
    year_start: Optional[int] = Field(None, description="起始年份", example=2025)
    year_end: Optional[int] = Field(None, description="结束年份", example=2034)
    age_range: Optional[Dict[str, int]] = Field(None, description="年龄范围", example={"start": 35, "end": 44})
    age_display: Optional[str] = Field(None, description="年龄显示", example="35-44岁")
    nayin: Optional[str] = Field(None, description="纳音", example="海中金")
    main_star: Optional[str] = Field(None, description="主星", example="正官")
    hidden_stems: Optional[List[str]] = Field(None, description="藏干列表", example=["癸"])
    hidden_stars: Optional[List[str]] = Field(None, description="副星列表", example=["正财"])
    star_fortune: Optional[str] = Field(None, description="十二长生", example="长生")
    self_sitting: Optional[str] = Field(None, description="自坐", example="")
    kongwang: Optional[str] = Field(None, description="空亡", example="")
    deities: Optional[List[str]] = Field(None, description="神煞列表", example=["天乙贵人"])
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息（原始数据）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "step": 0,
                "stem": "甲",
                "branch": "子",
                "ganzhi": "甲子",
                "year_start": 2025,
                "year_end": 2034,
                "age_range": {"start": 35, "end": 44},
                "age_display": "35-44岁",
                "nayin": "海中金",
                "main_star": "正官",
                "hidden_stems": ["癸"],
                "hidden_stars": ["正财"],
                "star_fortune": "长生",
                "self_sitting": "",
                "kongwang": "",
                "deities": ["天乙贵人"]
            }
        }


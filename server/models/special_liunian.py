#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特殊流年数据模型 - 统一的特殊流年数据结构定义
特殊流年：有关系的流年（冲合刑害、岁运并临等）
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from server.models.liunian import LiunianModel


class SpecialLiunianModel(LiunianModel):
    """特殊流年数据模型（继承流年模型，增加大运信息）"""
    dayun_step: Optional[int] = Field(None, description="所属大运步骤", example=0)
    dayun_ganzhi: Optional[str] = Field(None, description="所属大运干支", example="甲子")
    
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
                "relations": [{"type": "冲", "target": "日柱"}],
                "dayun_step": 0,
                "dayun_ganzhi": "甲子"
            }
        }


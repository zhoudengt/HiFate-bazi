#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字基础请求模型 - 包含所有公共字段和验证器
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional


class BaziBaseRequest(BaseModel):
    """八字基础请求模型 - 包含所有公共字段"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD（当calendar_type=lunar时，可为农历日期）", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    calendar_type: Optional[str] = Field("solar", description="历法类型：solar(阳历) 或 lunar(农历)，默认solar", example="solar")
    location: Optional[str] = Field(None, description="出生地点（用于时区转换，优先级1）", example="北京")
    latitude: Optional[float] = Field(None, description="纬度（用于时区转换，优先级2）", example=39.90)
    longitude: Optional[float] = Field(None, description="经度（用于时区转换和真太阳时计算，优先级2）", example=116.40)
    
    @field_validator('solar_date', mode='before')
    @classmethod
    def validate_date(cls, v):
        """验证日期格式 - 只检查非空，完全移除格式验证"""
        # 完全移除日期格式验证，允许任何格式（包括农历日期字符串）
        # 所有日期格式验证和转换都在 BaziInputProcessor.process_input() 中处理
        if not v:
            raise ValueError('日期不能为空')
        # 允许任何格式通过，包括农历日期字符串（如 "2024年正月初一"）
        return v
    
    @field_validator('solar_time')
    @classmethod
    def validate_time(cls, v):
        """验证时间格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        """验证性别"""
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v
    
    @field_validator('calendar_type')
    @classmethod
    def validate_calendar_type(cls, v):
        """验证历法类型"""
        if v and v not in ['solar', 'lunar']:
            raise ValueError('历法类型必须为 solar 或 lunar')
        return v or "solar"


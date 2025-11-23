#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字界面信息服务层
负责调用 bazi_interface_generator 生成界面信息
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.bazi_interface_generator import BaziInterfaceGenerator


class BaziInterfaceService:
    """八字界面信息服务类"""
    
    @staticmethod
    def generate_interface_full(solar_date: str, solar_time: str, gender: str, 
                                name: str = "", location: str = "未知地",
                                latitude: float = 39.00, longitude: float = 120.00) -> dict:
        """
        完整生成八字界面信息
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
            name: 姓名，可选
            location: 出生地点，可选
            latitude: 纬度，可选
            longitude: 经度，可选
        
        Returns:
            dict: 格式化的八字界面数据
        """
        # 转换性别格式
        if gender not in ["male", "female"]:
            if gender == "男":
                gender = "male"
            elif gender == "女":
                gender = "female"
        
        # 使用 BaziInterfaceGenerator 生成信息
        generator = BaziInterfaceGenerator()
        result = generator.generate_interface_info(
            name if name else "用户",
            gender,
            solar_date,
            solar_time,
            latitude,
            longitude,
            location
        )
        
        return result










































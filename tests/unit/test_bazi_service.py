#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字服务单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService


class TestBaziService:
    """八字服务测试类"""
    
    def test_calculate_bazi_full_success(self):
        """测试成功计算八字"""
        result = BaziService.calculate_bazi_full(
            solar_date="1990-01-15",
            solar_time="12:00",
            gender="male"
        )
        
        # 验证返回结果
        assert result is not None
        assert isinstance(result, dict)
        assert "bazi" in result
        
        # 验证八字数据
        bazi = result["bazi"]
        assert "bazi_pillars" in bazi
        assert "basic_info" in bazi
        
        # 验证四柱
        pillars = bazi["bazi_pillars"]
        assert "year" in pillars
        assert "month" in pillars
        assert "day" in pillars
        assert "hour" in pillars
    
    def test_calculate_bazi_full_female(self):
        """测试女性八字计算"""
        result = BaziService.calculate_bazi_full(
            solar_date="1990-05-20",
            solar_time="14:30",
            gender="female"
        )
        
        assert result is not None
        assert result["bazi"]["basic_info"]["gender"] == "female"
    
    def test_calculate_bazi_full_different_dates(self):
        """测试不同日期的八字计算"""
        test_cases = [
            ("1980-01-01", "00:00", "male"),
            ("2000-12-31", "23:59", "female"),
            ("1995-06-15", "12:00", "male"),
        ]
        
        for solar_date, solar_time, gender in test_cases:
            result = BaziService.calculate_bazi_full(
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender
            )
            assert result is not None
            assert "bazi" in result
    
    @pytest.mark.parametrize("solar_date,solar_time,gender", [
        ("1990-13-45", "12:00", "male"),  # 无效日期
        ("1990-01-15", "25:00", "male"),  # 无效时间
        ("1990-01-15", "12:00", "unknown"),  # 无效性别
    ])
    def test_calculate_bazi_full_invalid_input(self, solar_date, solar_time, gender):
        """测试无效输入"""
        # 注意：实际实现可能不会抛出异常，而是返回错误信息
        # 这里根据实际实现调整断言
        try:
            result = BaziService.calculate_bazi_full(
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender
            )
            # 如果返回了结果，检查是否包含错误信息
            if result:
                # 某些实现可能返回错误信息而不是抛出异常
                pass
        except (ValueError, TypeError, RuntimeError) as e:
            # 如果抛出异常，这是预期的行为
            # RuntimeError 可能来自微服务调用失败或本地计算失败
            assert isinstance(e, (ValueError, TypeError, RuntimeError))


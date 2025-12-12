#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万年历服务 单元测试

测试范围：
- CalendarAPIService 基本功能
- 日期转换
- 宜忌查询
- 神煞方位
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# 导入被测模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.services.calendar_api_service import CalendarAPIService


class TestCalendarAPIService:
    """CalendarAPIService 测试类"""
    
    # ==================== 测试前置 ====================
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.service = CalendarAPIService()
    
    # ==================== 正常流程测试 ====================
    
    def test_get_calendar_with_valid_date(self):
        """测试：有效日期查询"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert result["success"] == True
        assert result["lunar_date"] is not None
        assert "ganzhi" in result
        assert result["ganzhi"]["year"] == "乙巳"
        assert result["ganzhi"]["month"] == "戊子"
        assert result["ganzhi"]["day"] == "甲寅"
    
    def test_get_calendar_with_none_date(self):
        """测试：日期为空（使用今天）"""
        # When
        result = self.service.get_calendar(None)
        
        # Then
        assert result["success"] == True
        assert result["date"] is not None
    
    def test_get_calendar_returns_lunar_date(self):
        """测试：返回农历日期"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert result["lunar_date"] == "农历十月廿二"
    
    def test_get_calendar_returns_shengxiao(self):
        """测试：返回生肖"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert result["shengxiao"] == "蛇"
    
    def test_get_calendar_returns_xingzuo(self):
        """测试：返回星座"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert result["xingzuo"] == "射手"
    
    def test_get_calendar_returns_yi_list(self):
        """测试：返回宜列表"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "yi" in result
        assert isinstance(result["yi"], list)
        assert len(result["yi"]) > 0
    
    def test_get_calendar_returns_ji_list(self):
        """测试：返回忌列表"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "ji" in result
        assert isinstance(result["ji"], list)
    
    def test_get_calendar_returns_deities(self):
        """测试：返回神煞方位"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "deities" in result
        deities = result["deities"]
        assert "xishen" in deities  # 喜神
        assert "caishen" in deities  # 财神
        assert "fushen" in deities  # 福神
    
    def test_get_calendar_returns_chong_he_sha(self):
        """测试：返回冲合煞"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "chong_he_sha" in result
        chong_he_sha = result["chong_he_sha"]
        assert "chong" in chong_he_sha  # 冲
        assert "he" in chong_he_sha  # 合
        assert "sha" in chong_he_sha  # 煞
    
    # ==================== 边界条件测试 ====================
    
    def test_get_calendar_with_invalid_date_format(self):
        """测试：无效日期格式"""
        # Given
        invalid_date = "invalid-date"
        
        # When
        result = self.service.get_calendar(invalid_date)
        
        # Then
        assert result["success"] == False
        assert "error" in result
    
    def test_get_calendar_with_wrong_format(self):
        """测试：错误日期格式"""
        # Given
        wrong_format = "2025/12/11"  # 使用斜杠而不是连字符
        
        # When
        result = self.service.get_calendar(wrong_format)
        
        # Then
        assert result["success"] == False
    
    def test_get_calendar_with_leap_year(self):
        """测试：闰年日期"""
        # Given
        leap_year_date = "2024-02-29"
        
        # When
        result = self.service.get_calendar(leap_year_date)
        
        # Then
        assert result["success"] == True
    
    def test_get_calendar_with_year_boundary(self):
        """测试：年份边界"""
        # Given
        new_year = "2025-01-01"
        
        # When
        result = self.service.get_calendar(new_year)
        
        # Then
        assert result["success"] == True
    
    # ==================== 新增字段测试 ====================
    
    def test_get_calendar_returns_xingxiu(self):
        """测试：返回星宿信息"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "xingxiu" in result
        xingxiu = result["xingxiu"]
        assert "name" in xingxiu
        assert "luck" in xingxiu
    
    def test_get_calendar_returns_pengzu(self):
        """测试：返回彭祖百忌"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "pengzu" in result
        pengzu = result["pengzu"]
        assert "gan" in pengzu
        assert "zhi" in pengzu
    
    def test_get_calendar_returns_shensha(self):
        """测试：返回吉神凶煞"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "shensha" in result
        shensha = result["shensha"]
        assert "jishen" in shensha  # 吉神
        assert "xiongsha" in shensha  # 凶煞
    
    def test_get_calendar_returns_jiuxing(self):
        """测试：返回九星"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "jiuxing" in result
        jiuxing = result["jiuxing"]
        assert "year" in jiuxing
        assert "month" in jiuxing
        assert "day" in jiuxing
    
    def test_get_calendar_returns_other_info(self):
        """测试：返回其他信息"""
        # Given
        date = "2025-12-11"
        
        # When
        result = self.service.get_calendar(date)
        
        # Then
        assert "other" in result
        other = result["other"]
        assert "liuyao" in other  # 六曜
        assert "zhixing" in other  # 建除
        assert "yuexiang" in other  # 月相
    
    # ==================== 性能测试 ====================
    
    def test_get_calendar_performance(self):
        """测试：性能（响应时间）"""
        import time
        
        # Given
        date = "2025-12-11"
        
        # When
        start = time.time()
        result = self.service.get_calendar(date)
        elapsed = time.time() - start
        
        # Then
        assert result["success"] == True
        assert elapsed < 1.0  # 应在 1 秒内完成


class TestCalendarAPIServiceProvider:
    """测试提供商相关功能"""
    
    def setup_method(self):
        self.service = CalendarAPIService()
    
    def test_get_available_providers(self):
        """测试：获取可用提供商"""
        # When
        providers = self.service.get_available_providers()
        
        # Then
        assert isinstance(providers, list)
    
    def test_local_provider_always_available(self):
        """测试：本地提供商始终可用"""
        # When
        result = self.service.get_calendar("2025-12-11")
        
        # Then
        # 即使没有配置 API 密钥，也应该能使用本地计算
        assert result["success"] == True
        assert result["provider"] == "local"


# ==================== 参数化测试 ====================

class TestCalendarParameterized:
    """参数化测试"""
    
    def setup_method(self):
        self.service = CalendarAPIService()
    
    @pytest.mark.parametrize("date,expected_shengxiao", [
        ("2025-12-11", "蛇"),
        ("2024-01-01", "兔"),
        ("2000-06-15", "龙"),
    ])
    def test_get_shengxiao_for_different_years(self, date, expected_shengxiao):
        """测试：不同年份的生肖"""
        result = self.service.get_calendar(date)
        assert result["success"] == True
        assert result["shengxiao"] == expected_shengxiao
    
    @pytest.mark.parametrize("invalid_date", [
        "invalid",
        "2025-13-01",  # 月份无效
        "not-a-date",
    ])
    def test_invalid_dates(self, invalid_date):
        """测试：无效日期"""
        result = self.service.get_calendar(invalid_date)
        assert result["success"] == False

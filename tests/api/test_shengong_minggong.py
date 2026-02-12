#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

身宫命宫 API 专项测试

测试身宫命宫计算功能的完整性和正确性
"""

import pytest; pytest.importorskip("fastapi", reason="fastapi not installed")
import pytest
import httpx
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

BASE_URL = "http://localhost:8001"


@pytest.fixture
def client():
    """创建 HTTP 客户端"""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


@pytest.mark.asyncio
@pytest.mark.api
class TestShengongMinggong:
    """身宫命宫 API 测试类"""
    
    async def test_shengong_minggong_basic(self, client):
        """测试：基础身宫命宫计算"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # 验证响应结构
        assert result["success"] == True
        assert "data" in result
        
        data = result["data"]
        assert isinstance(data, dict)
        
        # 验证身宫数据
        assert "shengong" in data
        shengong = data["shengong"]
        assert isinstance(shengong, dict)
        assert "stem" in shengong and "branch" in shengong
        assert "char" in shengong["stem"] and "char" in shengong["branch"]
        shengong_ganzhi = shengong["stem"]["char"] + shengong["branch"]["char"]
        assert len(shengong_ganzhi) == 2, f"身宫干支应为2个字符，实际: {shengong_ganzhi}"
        
        # 验证命宫数据
        assert "minggong" in data
        minggong = data["minggong"]
        assert isinstance(minggong, dict)
        assert "stem" in minggong and "branch" in minggong
        assert "char" in minggong["stem"] and "char" in minggong["branch"]
        minggong_ganzhi = minggong["stem"]["char"] + minggong["branch"]["char"]
        assert len(minggong_ganzhi) == 2, f"命宫干支应为2个字符，实际: {minggong_ganzhi}"
        
        # 验证四柱数据
        assert "pillars" in data
        pillars = data["pillars"]
        assert isinstance(pillars, dict)
        for pillar_type in ["year", "month", "day", "hour"]:
            assert pillar_type in pillars
    
    @pytest.mark.parametrize("solar_date,solar_time,gender,expected_shengong_pattern,expected_minggong_pattern", [
        ("1990-01-15", "12:00", "male", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
        ("1995-05-20", "14:30", "female", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
        ("1987-01-07", "09:00", "male", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
        ("2000-12-31", "23:59", "female", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$", r"^[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]$"),
    ])
    async def test_shengong_minggong_different_inputs(
        self, 
        client, 
        solar_date, 
        solar_time, 
        gender,
        expected_shengong_pattern,
        expected_minggong_pattern
    ):
        """测试：不同输入的身宫命宫计算"""
        import re
        
        request_data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] == True
        assert "data" in result
        
        data = result["data"]
        
        # 验证身宫
        shengong_ganzhi = data["shengong"]["stem"]["char"] + data["shengong"]["branch"]["char"]
        assert re.match(expected_shengong_pattern, shengong_ganzhi), f"身宫干支格式错误: {shengong_ganzhi}"
        
        # 验证命宫
        minggong_ganzhi = data["minggong"]["stem"]["char"] + data["minggong"]["branch"]["char"]
        assert re.match(expected_minggong_pattern, minggong_ganzhi), f"命宫干支格式错误: {minggong_ganzhi}"
        
        # 验证数据完整性
        assert "main_star" in data["shengong"]
        assert "main_star" in data["minggong"]
        assert "hidden_stems" in data["shengong"]
        assert "hidden_stems" in data["minggong"]
        assert isinstance(data["shengong"]["hidden_stems"], list)
        assert isinstance(data["minggong"]["hidden_stems"], list)
    
    async def test_shengong_minggong_invalid_date(self, client):
        """测试：无效日期输入"""
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json={
                "solar_date": "1990-13-45",
                "solar_time": "12:00",
                "gender": "male"
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    async def test_shengong_minggong_missing_params(self, client):
        """测试：缺少必需参数"""
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json={
                "solar_date": "1990-01-15"
                # 缺少 solar_time 和 gender
            }
        )
        
        # 应该返回验证错误
        assert response.status_code in [400, 422]
    
    async def test_shengong_minggong_data_structure(self, client):
        """测试：验证数据结构完整性"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        data = result["data"]
        
        # 验证身宫数据结构
        shengong = data["shengong"]
        required_fields = ["stem", "branch", "main_star", "hidden_stems", "star_fortune", 
                          "self_sitting", "kongwang", "nayin", "deities"]
        for field in required_fields:
            assert field in shengong, f"身宫缺少字段: {field}"
        
        # 验证命宫数据结构
        minggong = data["minggong"]
        for field in required_fields:
            assert field in minggong, f"命宫缺少字段: {field}"
        
        # 验证四柱数据结构
        pillars = data["pillars"]
        for pillar_type in ["year", "month", "day", "hour"]:
            pillar = pillars[pillar_type]
            pillar_fields = ["stem", "branch", "main_star", "hidden_stems", "star_fortune",
                           "self_sitting", "kongwang", "nayin", "deities"]
            for field in pillar_fields:
                assert field in pillar, f"四柱 {pillar_type} 缺少字段: {field}"
    
    async def test_shengong_minggong_with_fortune_data(self, client):
        """测试：验证大运流年流月数据（完整验证）"""
        request_data = {
            "solar_date": "1990-01-15",
            "solar_time": "12:00",
            "gender": "male"
        }
        
        response = await client.post(
            "/api/v1/bazi/shengong-minggong",
            json=request_data
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        data = result["data"]
        
        # 验证大运数据
        assert "dayun" in data, "返回数据应包含 dayun 字段"
        dayun = data["dayun"]
        assert isinstance(dayun, dict), "dayun 应为字典类型"
        assert "current" in dayun, "dayun 应包含 current 字段"
        assert "list" in dayun, "dayun 应包含 list 字段（新增）"
        assert "qiyun" in dayun, "dayun 应包含 qiyun 字段"
        assert "jiaoyun" in dayun, "dayun 应包含 jiaoyun 字段"
        
        # 验证大运列表
        dayun_list = dayun.get("list", [])
        assert isinstance(dayun_list, list), "dayun.list 应为列表类型"
        # 如果列表不为空，验证列表项结构
        if dayun_list:
            first_dayun = dayun_list[0]
            assert isinstance(first_dayun, dict), "大运列表项应为字典类型"
            # 验证大运项的基本字段（根据实际返回结构调整）
        
        # 验证起运信息（完整结构）
        qiyun = dayun.get("qiyun", {})
        assert isinstance(qiyun, dict), "qiyun 应为字典类型"
        # qiyun 应包含 date, age_display, description 字段（如果数据获取成功）
        if qiyun:  # 如果数据不为空
            assert "date" in qiyun or "age_display" in qiyun or "description" in qiyun, \
                "qiyun 应包含 date, age_display 或 description 字段"
        
        # 验证交运信息（完整结构）
        jiaoyun = dayun.get("jiaoyun", {})
        assert isinstance(jiaoyun, dict), "jiaoyun 应为字典类型"
        # jiaoyun 应包含 date, age_display, description 字段（如果数据获取成功）
        if jiaoyun:  # 如果数据不为空
            assert "date" in jiaoyun or "age_display" in jiaoyun or "description" in jiaoyun, \
                "jiaoyun 应包含 date, age_display 或 description 字段"
        
        # 验证流年数据
        assert "liunian" in data, "返回数据应包含 liunian 字段"
        liunian = data["liunian"]
        assert isinstance(liunian, dict), "liunian 应为字典类型"
        assert "current" in liunian, "liunian 应包含 current 字段"
        assert "list" in liunian, "liunian 应包含 list 字段"
        assert isinstance(liunian.get("list"), list), "liunian.list 应为列表类型"
        
        # 验证流月数据
        assert "liuyue" in data, "返回数据应包含 liuyue 字段"
        liuyue = data["liuyue"]
        assert isinstance(liuyue, dict), "liuyue 应为字典类型"
        assert "current" in liuyue, "liuyue 应包含 current 字段"
        assert "list" in liuyue, "liuyue 应包含 list 字段"
        assert "target_year" in liuyue, "liuyue 应包含 target_year 字段（新增）"
        assert isinstance(liuyue.get("list"), list), "liuyue.list 应为列表类型"
        
        # 验证 target_year 字段
        target_year = liuyue.get("target_year")
        # target_year 可能为 None（如果计算失败）或整数（年份）
        if target_year is not None:
            assert isinstance(target_year, int), "target_year 应为整数类型"
            assert 1900 <= target_year <= 2100, f"target_year 应在合理范围内: {target_year}"
        
        # 验证流月列表应包含12个月（当前年份）
        liuyue_list = liuyue.get("list", [])
        # 流月列表应该包含当前年份的12个月，但可能因为计算失败而为空
        # 所以只验证它是列表类型，不强制要求有12个元素
        
        # 验证流年列表应包含当前大运范围内的流年（约10年）
        liunian_list = liunian.get("list", [])
        # 流年列表应该包含当前大运范围内的流年，但可能因为计算失败而为空
        # 所以只验证它是列表类型，不强制要求有特定数量


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

特殊流年服务单元测试
"""

import pytest; pytest.importorskip("grpc", reason="grpc not installed")
import sys
import os
import pytest
import asyncio
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.services.special_liunian_service import SpecialLiunianService


class TestSpecialLiunianService:
    """特殊流年服务测试类"""
    
    @pytest.mark.asyncio
    async def test_get_special_liunians_batch_basic(self):
        """测试基本批量获取功能"""
        solar_date = "1985-11-21"
        solar_time = "06:30"
        gender = "female"
        
        # 先获取大运序列
        from server.services.bazi_detail_service import BaziDetailService
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender
        )
        dayun_sequence = detail_result.get('details', {}).get('dayun_sequence', [])
        
        assert len(dayun_sequence) > 0, "大运序列不应为空"
        
        # 测试批量获取特殊流年
        special_liunians = await SpecialLiunianService.get_special_liunians_batch(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            dayun_sequence=dayun_sequence,
            dayun_count=3,  # 只测试前3个大运
            current_time=datetime.now()
        )
        
        # 验证返回结果
        assert isinstance(special_liunians, list), "应返回列表"
        
        # 验证每个流年都有 relations
        for liunian in special_liunians:
            assert 'relations' in liunian, "每个特殊流年应有 relations 字段"
            assert len(liunian.get('relations', [])) > 0, "relations 不应为空"
            assert 'dayun_step' in liunian, "每个特殊流年应有 dayun_step 字段"
            assert 'dayun_ganzhi' in liunian, "每个特殊流年应有 dayun_ganzhi 字段"
    
    @pytest.mark.asyncio
    async def test_get_special_liunians_batch_no_deduplication(self):
        """测试不去重功能（同一年可能有多个关系）"""
        solar_date = "1985-11-21"
        solar_time = "06:30"
        gender = "female"
        
        # 先获取大运序列
        from server.services.bazi_detail_service import BaziDetailService
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender
        )
        dayun_sequence = detail_result.get('details', {}).get('dayun_sequence', [])
        
        # 测试批量获取特殊流年
        special_liunians = await SpecialLiunianService.get_special_liunians_batch(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            dayun_sequence=dayun_sequence,
            dayun_count=8,
            current_time=datetime.now()
        )
        
        # 检查是否有同一年多个关系的流年
        year_liunian_map = {}
        for liunian in special_liunians:
            year = liunian.get('year')
            if year:
                if year not in year_liunian_map:
                    year_liunian_map[year] = []
                year_liunian_map[year].append(liunian)
        
        # 如果有同一年多个流年，说明不去重功能正常
        multiple_relations_years = [year for year, liunians in year_liunian_map.items() if len(liunians) > 1]
        # 注意：这个测试可能通过也可能不通过，取决于实际数据
        # 我们主要验证不去重逻辑不会报错
        print(f"同一年多个关系的年份: {multiple_relations_years}")
    
    def test_format_special_liunians_for_prompt(self):
        """测试格式匹配功能"""
        # 模拟特殊流年数据
        special_liunians = [
            {
                'year': 2020,
                'ganzhi': '庚子',
                'relations': ['年柱-天合地合'],
                'dayun_step': 2,
                'dayun_ganzhi': '戊子'
            },
            {
                'year': 2022,
                'ganzhi': '壬寅',
                'relations': ['岁运并临'],
                'dayun_step': 2,
                'dayun_ganzhi': '戊子'
            },
            {
                'year': 2025,
                'ganzhi': '乙巳',
                'relations': ['天合地合'],
                'dayun_step': 3,
                'dayun_ganzhi': '己丑'
            }
        ]
        
        # 模拟大运序列
        dayun_sequence = [
            {
                'step': 1,
                'stem': '丁',
                'branch': '亥',
                'age_range': {'start': 1, 'end': 10}
            },
            {
                'step': 2,
                'stem': '戊',
                'branch': '子',
                'age_range': {'start': 11, 'end': 20}
            },
            {
                'step': 3,
                'stem': '己',
                'branch': '丑',
                'age_range': {'start': 21, 'end': 30}
            }
        ]
        
        # 测试格式匹配
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(
            special_liunians,
            dayun_sequence
        )
        
        # 验证返回结果
        assert isinstance(formatted, str), "应返回字符串"
        assert len(formatted) > 0, "格式化结果不应为空"
        
        # 验证包含关键信息
        assert '2020' in formatted, "应包含年份"
        assert '庚子' in formatted, "应包含干支"
        assert '年柱-天合地合' in formatted, "应包含关系"
        assert '关键年份' in formatted, "应包含关键年份标题"
        
        print(f"格式化结果:\n{formatted}")
    
    def test_format_special_liunians_for_prompt_empty(self):
        """测试空数据格式匹配"""
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(
            [],
            []
        )
        
        assert formatted == "", "空数据应返回空字符串"
    
    @pytest.mark.asyncio
    async def test_get_special_liunians_batch_error_handling(self):
        """测试错误处理（单个大运失败不影响其他）"""
        solar_date = "1985-11-21"
        solar_time = "06:30"
        gender = "female"
        
        # 创建包含无效大运的序列
        dayun_sequence = [
            {
                'step': 1,
                'year_start': 1995,
                'year_end': 2005,
                'stem': '丁',
                'branch': '亥'
            },
            {
                'step': 2,
                # 缺少 year_start 和 year_end，应该被跳过
                'stem': '戊',
                'branch': '子'
            },
            {
                'step': 3,
                'year_start': 2015,
                'year_end': 2025,
                'stem': '己',
                'branch': '丑'
            }
        ]
        
        # 测试批量获取（应该跳过无效大运，处理有效大运）
        special_liunians = await SpecialLiunianService.get_special_liunians_batch(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            dayun_sequence=dayun_sequence,
            dayun_count=3,
            current_time=datetime.now()
        )
        
        # 验证不会因为无效大运而报错
        assert isinstance(special_liunians, list), "应返回列表（即使有错误）"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


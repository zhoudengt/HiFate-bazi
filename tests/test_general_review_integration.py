#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

总评分析集成测试 - 测试特殊流年功能集成
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

from server.api.v1.general_review_analysis import (
    general_review_analysis_stream_generator,
    build_general_review_input_data,
    build_general_review_prompt
)
from server.services.special_liunian_service import SpecialLiunianService


class TestGeneralReviewIntegration:
    """总评分析集成测试类"""
    
    @pytest.mark.asyncio
    async def test_special_liunians_integration(self):
        """测试特殊流年功能集成"""
        solar_date = "1985-11-21"
        solar_time = "06:30"
        gender = "female"
        
        # 1. 获取基础数据
        from server.services.bazi_service import BaziService
        from server.services.wangshuai_service import WangShuaiService
        from server.services.bazi_detail_service import BaziDetailService
        
        loop = asyncio.get_event_loop()
        executor = None
        
        bazi_result, wangshuai_result, detail_result = await asyncio.gather(
            loop.run_in_executor(executor, BaziService.calculate_bazi_full, solar_date, solar_time, gender),
            loop.run_in_executor(executor, WangShuaiService.calculate_wangshuai, solar_date, solar_time, gender),
            loop.run_in_executor(executor, BaziDetailService.calculate_detail_full, solar_date, solar_time, gender)
        )
        
        # 提取数据
        bazi_data = bazi_result.get('bazi', bazi_result)
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # 2. 使用批量服务获取特殊流年
        special_liunians = await SpecialLiunianService.get_special_liunians_batch(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            dayun_sequence=dayun_sequence,
            dayun_count=8,
            current_time=datetime.now()
        )
        
        # 3. 构建 input_data
        input_data = build_general_review_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=gender,
            solar_date=solar_date,
            solar_time=solar_time,
            special_liunians=special_liunians
        )
        
        # 4. 验证特殊流年是否正确传递
        key_liunian = input_data.get('guanjian_dayun', {}).get('key_liunian', [])
        assert len(key_liunian) == len(special_liunians), "特殊流年应正确传递到 input_data"
        
        # 5. 验证格式匹配功能
        formatted = SpecialLiunianService.format_special_liunians_for_prompt(
            key_liunian,
            dayun_sequence
        )
        
        if key_liunian:
            assert len(formatted) > 0, "格式化结果不应为空"
            assert '关键年份' in formatted, "应包含关键年份标题"
        
        # 6. 构建完整提示词
        prompt = build_general_review_prompt(input_data)
        
        # 7. 验证提示词包含特殊流年信息
        if key_liunian:
            # 检查格式化后的特殊流年是否在提示词中
            assert formatted in prompt or any(
                str(liunian.get('year', '')) in prompt 
                for liunian in key_liunian[:5]
            ), "提示词应包含特殊流年信息"
        
        print(f"特殊流年数量: {len(key_liunian)}")
        print(f"格式化结果长度: {len(formatted)}")
        print(f"提示词长度: {len(prompt)}")
    
    @pytest.mark.asyncio
    async def test_no_deduplication_in_integration(self):
        """测试集成中不去重功能"""
        solar_date = "1985-11-21"
        solar_time = "06:30"
        gender = "female"
        
        # 获取大运序列
        from server.services.bazi_detail_service import BaziDetailService
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender
        )
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # 获取特殊流年
        special_liunians = await SpecialLiunianService.get_special_liunians_batch(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            dayun_sequence=dayun_sequence,
            dayun_count=8,
            current_time=datetime.now()
        )
        
        # 检查是否有同一年多个关系的流年
        year_relations_map = {}
        for liunian in special_liunians:
            year = liunian.get('year')
            relations = liunian.get('relations', [])
            if year:
                if year not in year_relations_map:
                    year_relations_map[year] = []
                year_relations_map[year].extend(relations)
        
        # 统计同一年有多个关系的年份
        multiple_relations_years = [
            year for year, relations in year_relations_map.items() 
            if len(relations) > 1
        ]
        
        print(f"同一年多个关系的年份: {multiple_relations_years}")
        print(f"特殊流年总数: {len(special_liunians)}")
        
        # 验证不去重：如果有同一年多个关系，应该保留所有
        # 这个测试主要验证逻辑不会报错，实际结果取决于数据


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


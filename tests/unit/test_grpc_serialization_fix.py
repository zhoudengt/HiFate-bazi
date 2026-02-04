#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gRPC 序列化修复工具测试

测试 server/utils/grpc_serialization_fix.py 中的函数。
"""

import pytest
import json

# 导入被测试模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.utils.grpc_serialization_fix import (
    fix_dict_field,
    fix_ten_gods_stats,
    fix_element_counts,
    fix_all_grpc_fields
)


class TestFixDictField:
    """测试 fix_dict_field 函数"""
    
    @pytest.mark.unit
    def test_dict_input_returns_same(self):
        """字典输入应直接返回"""
        input_dict = {"key": "value", "count": 5}
        result = fix_dict_field(input_dict, "test_field")
        assert result == input_dict
    
    @pytest.mark.unit
    def test_none_input_returns_default(self):
        """None 输入应返回默认值"""
        result = fix_dict_field(None, "test_field")
        assert result == {}
        
        result = fix_dict_field(None, "test_field", default={"default": True})
        assert result == {"default": True}
    
    @pytest.mark.unit
    def test_empty_string_returns_default(self):
        """空字符串应返回默认值"""
        result = fix_dict_field("", "test_field")
        assert result == {}
    
    @pytest.mark.unit
    def test_json_string_parsed(self):
        """JSON 格式字符串应被正确解析"""
        input_str = '{"正官": 1, "偏财": 2}'
        result = fix_dict_field(input_str, "test_field")
        assert result == {"正官": 1, "偏财": 2}
    
    @pytest.mark.unit
    def test_python_literal_parsed(self):
        """Python 字面量格式字符串应被正确解析"""
        input_str = "{'正官': 1, '偏财': 2}"
        result = fix_dict_field(input_str, "test_field")
        assert result == {"正官": 1, "偏财": 2}
    
    @pytest.mark.unit
    def test_invalid_string_returns_default(self):
        """无效字符串应返回默认值"""
        result = fix_dict_field("not a dict", "test_field", log_errors=False)
        assert result == {}
    
    @pytest.mark.unit
    def test_other_types_return_default(self):
        """其他类型应返回默认值"""
        result = fix_dict_field(123, "test_field", log_errors=False)
        assert result == {}
        
        result = fix_dict_field([1, 2, 3], "test_field", log_errors=False)
        assert result == {}


class TestFixTenGodsStats:
    """测试 fix_ten_gods_stats 函数"""
    
    @pytest.mark.unit
    def test_normal_dict(self):
        """正常字典数据"""
        bazi_data = {
            "ten_gods_stats": {
                "totals": {"正官": 1, "偏财": 2}
            }
        }
        result = fix_ten_gods_stats(bazi_data)
        assert result == {"totals": {"正官": 1, "偏财": 2}}
    
    @pytest.mark.unit
    def test_extract_totals(self):
        """提取 totals 子字段"""
        bazi_data = {
            "ten_gods_stats": {
                "totals": {"正官": 1, "偏财": 2}
            }
        }
        result = fix_ten_gods_stats(bazi_data, extract_totals=True)
        assert result == {"正官": 1, "偏财": 2}
    
    @pytest.mark.unit
    def test_string_input(self):
        """字符串输入应被解析"""
        bazi_data = {
            "ten_gods_stats": '{"totals": {"正官": 1}}'
        }
        result = fix_ten_gods_stats(bazi_data)
        assert result == {"totals": {"正官": 1}}
    
    @pytest.mark.unit
    def test_missing_field(self):
        """缺少字段应返回空字典"""
        bazi_data = {}
        result = fix_ten_gods_stats(bazi_data)
        assert result == {}


class TestFixAllGrpcFields:
    """测试 fix_all_grpc_fields 函数"""
    
    @pytest.mark.unit
    def test_fixes_all_fields(self):
        """应修复所有已知字段"""
        bazi_data = {
            "ten_gods_stats": '{"正官": 1}',
            "element_counts": '{"金": 2}',
            "elements": '{"day": {"stem": "甲"}}',
            "relationships": '{"合": ["子丑合"]}'
        }
        result = fix_all_grpc_fields(bazi_data)
        
        assert result["ten_gods_stats"] == {"正官": 1}
        assert result["element_counts"] == {"金": 2}
        assert result["elements"] == {"day": {"stem": "甲"}}
        assert result["relationships"] == {"合": ["子丑合"]}
    
    @pytest.mark.unit
    def test_preserves_other_fields(self):
        """应保留其他字段不变"""
        bazi_data = {
            "basic_info": {"date": "1990-01-15"},
            "ten_gods_stats": {"正官": 1}
        }
        result = fix_all_grpc_fields(bazi_data)
        
        assert result["basic_info"] == {"date": "1990-01-15"}
        assert result["ten_gods_stats"] == {"正官": 1}

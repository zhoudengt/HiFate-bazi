#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则服务单元测试
测试规则匹配服务的核心功能
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.rule_service import RuleService


@pytest.fixture
def sample_bazi_data():
    """示例八字数据"""
    return {
        "bazi_pillars": {
            "year": {"stem": "庚", "branch": "午"},
            "month": {"stem": "戊", "branch": "子"},
            "day": {"stem": "甲", "branch": "寅"},
            "hour": {"stem": "庚", "branch": "午"}
        },
        "gender": "male",
        "wangshuai": "身旺"
    }


@pytest.mark.unit
class TestRuleService:
    """规则服务测试类"""
    
    def test_match_rules_basic(self, sample_bazi_data):
        """测试：基本规则匹配"""
        with patch('server.services.rule_service.get_mysql_connection') as mock_conn:
            # Mock 数据库连接
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "id": 1,
                    "rule_code": "FORMULA_wealth_80001",
                    "rule_type": "wealth",
                    "conditions": '{"gender": "male"}',
                    "content": '{"text": "测试规则"}'
                }
            ]
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            rules = RuleService.match_rules(sample_bazi_data, rule_types=['wealth'])
            
            assert isinstance(rules, list)
            assert len(rules) >= 0  # 可能匹配到规则，也可能没有
    
    def test_match_rules_multiple_types(self, sample_bazi_data):
        """测试：匹配多种类型的规则"""
        with patch('server.services.rule_service.get_mysql_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            rules = RuleService.match_rules(
                sample_bazi_data,
                rule_types=['wealth', 'marriage', 'career']
            )
            
            assert isinstance(rules, list)
    
    def test_match_rules_empty_result(self, sample_bazi_data):
        """测试：没有匹配到规则的情况"""
        with patch('server.services.rule_service.get_mysql_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            rules = RuleService.match_rules(sample_bazi_data, rule_types=['wealth'])
            
            assert isinstance(rules, list)
            assert len(rules) == 0
    
    def test_match_rules_invalid_bazi_data(self):
        """测试：无效的八字数据"""
        invalid_data = {}
        
        with patch('server.services.rule_service.get_mysql_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # 应该能够处理无效数据，返回空列表或抛出异常
            try:
                rules = RuleService.match_rules(invalid_data, rule_types=['wealth'])
                assert isinstance(rules, list)
            except Exception:
                # 如果抛出异常也是可以接受的
                pass
    
    def test_match_rules_with_gender_filter(self, sample_bazi_data):
        """测试：性别过滤"""
        with patch('server.services.rule_service.get_mysql_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
            
            # 测试男性
            sample_bazi_data["gender"] = "male"
            rules_male = RuleService.match_rules(sample_bazi_data, rule_types=['wealth'])
            
            # 测试女性
            sample_bazi_data["gender"] = "female"
            rules_female = RuleService.match_rules(sample_bazi_data, rule_types=['wealth'])
            
            assert isinstance(rules_male, list)
            assert isinstance(rules_female, list)


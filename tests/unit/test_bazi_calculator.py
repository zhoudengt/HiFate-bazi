#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WenZhenBazi 核心排盘单元测试"""

import pytest
from core.calculators.bazi_calculator import WenZhenBazi

CASES = [
    {"solar_date": "1987-01-07", "solar_time": "09:55", "gender": "male", "expected_day": ("丙", "辰")},
    {"solar_date": "1984-03-08", "solar_time": "09:15", "gender": "male", "expected_day": ("辛", "丑")},
    {"solar_date": "2008-09-08", "solar_time": "16:03", "gender": "female", "expected_day": ("辛", "亥")},
]


class TestInit:
    def test_basic_init(self):
        bazi = WenZhenBazi("2000-01-01", "12:00", "male")
        assert bazi.solar_date == "2000-01-01"
        assert bazi.gender == "male"
        assert bazi.bazi_pillars == {}
        assert bazi.last_result is None

    def test_default_gender(self):
        bazi = WenZhenBazi("2000-01-01", "12:00")
        assert bazi.gender == "male"


class TestCalculate:
    @pytest.mark.parametrize("case", CASES, ids=[c["solar_date"] for c in CASES])
    def test_result_has_all_keys(self, case):
        bazi = WenZhenBazi(case["solar_date"], case["solar_time"], case["gender"])
        result = bazi.calculate()
        for key in ("basic_info", "bazi_pillars", "details", "ten_gods_stats", "elements", "element_counts", "relationships"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.parametrize("case", CASES, ids=[c["solar_date"] for c in CASES])
    def test_day_pillar(self, case):
        bazi = WenZhenBazi(case["solar_date"], case["solar_time"], case["gender"])
        day = bazi.calculate()["bazi_pillars"]["day"]
        assert (day["stem"], day["branch"]) == case["expected_day"]

    def test_four_pillars_complete(self):
        result = WenZhenBazi("1987-01-07", "09:55", "male").calculate()
        for p in ("year", "month", "day", "hour"):
            assert "stem" in result["bazi_pillars"][p]
            assert "branch" in result["bazi_pillars"][p]

    def test_details_fields(self):
        result = WenZhenBazi("1987-01-07", "09:55", "male").calculate()
        for p in ("year", "month", "day", "hour"):
            d = result["details"][p]
            for field in ("main_star", "hidden_stars", "hidden_stems", "nayin", "deities"):
                assert field in d, f"Missing {field} in {p}"

    def test_zi_shi_adjustment(self):
        result = WenZhenBazi("2000-06-15", "23:30", "male").calculate()
        assert result["basic_info"]["is_zi_shi_adjusted"] is True

    def test_caches_result(self):
        bazi = WenZhenBazi("1987-01-07", "09:55", "male")
        r = bazi.calculate()
        assert bazi.last_result is r


class TestTenGods:
    def test_day_yuannan(self):
        r = WenZhenBazi("1987-01-07", "09:55", "male").calculate()
        assert r["details"]["day"]["main_star"] == "元男"

    def test_day_yuannv(self):
        r = WenZhenBazi("2008-09-08", "16:03", "female").calculate()
        assert r["details"]["day"]["main_star"] == "元女"

    def test_main_star_same(self):
        b = WenZhenBazi("2000-01-01", "12:00")
        assert b.get_main_star("甲", "甲", "year") == "比肩"
        assert b.get_main_star("甲", "乙", "year") == "劫财"

    def test_main_star_producing(self):
        b = WenZhenBazi("2000-01-01", "12:00")
        assert b.get_main_star("甲", "丙", "year") == "食神"
        assert b.get_main_star("甲", "丁", "year") == "伤官"

    def test_branch_ten_gods(self):
        b = WenZhenBazi("2000-01-01", "12:00")
        r = b.get_branch_ten_gods("甲", "子")
        assert isinstance(r, list) and len(r) > 0


class TestElements:
    def test_relation_same(self):
        b = WenZhenBazi("2000-01-01", "12:00")
        assert b._get_element_relation("木", "木") == "same"

    def test_relation_producing(self):
        b = WenZhenBazi("2000-01-01", "12:00")
        assert b._get_element_relation("木", "火") == "me_producing"

    def test_relation_controlling(self):
        b = WenZhenBazi("2000-01-01", "12:00")
        assert b._get_element_relation("木", "土") == "me_controlling"

    def test_element_counts_sum(self):
        bazi = WenZhenBazi("1987-01-07", "09:55", "male")
        bazi.calculate()
        elements = bazi._build_elements_info()
        counts = bazi._build_element_counts(elements)
        assert sum(counts.values()) == 8


class TestDataBuilders:
    @pytest.fixture
    def bazi(self):
        b = WenZhenBazi("1987-01-07", "09:55", "male")
        b.calculate()
        return b

    def test_ten_gods_stats(self, bazi):
        s = bazi._build_ten_gods_stats()
        assert all(k in s for k in ("main", "sub", "totals", "ten_gods_main"))

    def test_ganzhi_relationships(self, bazi):
        r = bazi._build_ganzhi_relationships()
        assert "stem_relations" in r and "branch_relations" in r

    def test_format_result(self, bazi):
        r = bazi._format_result()
        assert r["basic_info"]["gender"] == "male"


class TestConditionDebug:
    @pytest.fixture
    def bazi(self):
        b = WenZhenBazi("1987-01-07", "09:55", "male")
        b.calculate()
        return b

    def test_gender(self, bazi):
        r = bazi._collect_condition_values({"gender": "male"}, {"basic_info": {"gender": "male"}})
        assert any("gender=male" in v for v in r)

    def test_format_requirement(self, bazi):
        assert bazi._format_requirement(None) == ""
        assert "≥ 2" in bazi._format_requirement({"min": 2})

    def test_describe_element_sources(self, bazi):
        data = bazi._format_result()
        c = bazi._describe_element_sources(data)
        assert isinstance(c, dict) and len(c) > 0


class TestRuleInput:
    def test_structure(self):
        bazi = WenZhenBazi("1987-01-07", "09:55", "male")
        bazi.calculate()
        ri = bazi.build_rule_input()
        for k in ("basic_info", "bazi_pillars", "details", "ten_gods_stats", "elements", "fortune"):
            assert k in ri

    def test_rule_filters(self):
        assert WenZhenBazi._get_rule_filters("nonexistent") == {}

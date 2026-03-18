#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.inference.models import InferenceInput
from core.inference.marriage_engine import MarriageInferenceEngine
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
logging.basicConfig(level=logging.WARNING)

WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
STEM_YY = {"甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳", "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴"}

def make_pillars(year, month, day, hour):
    pillars = {}
    for name, gz in [("year", year), ("month", month), ("day", day), ("hour", hour)]:
        pillars[name] = {"stem": gz[0], "branch": gz[1]} if len(gz) >= 2 else {"stem": "", "branch": ""}
    return pillars

def calc_shishen(day_stem, other_stem):
    if not day_stem or not other_stem or day_stem == other_stem:
        return ""
    de, oe = STEM_ELEMENTS.get(day_stem, ""), STEM_ELEMENTS.get(other_stem, "")
    dy, oy = STEM_YY.get(day_stem, ""), STEM_YY.get(other_stem, "")
    if not de or not oe:
        return ""
    same_yy = (dy == oy)
    if de == oe: return "比肩" if same_yy else "劫财"
    if WUXING_SHENG.get(de) == oe: return "食神" if same_yy else "伤官"
    if WUXING_KE.get(de) == oe: return "偏财" if same_yy else "正财"
    if WUXING_SHENG.get(oe) == de: return "偏印" if same_yy else "正印"
    if WUXING_KE.get(oe) == de: return "七杀" if same_yy else "正官"
    return ""

def make_ten_gods(pillars, day_stem):
    ten_gods = {}
    for pname in ["year", "month", "day", "hour"]:
        stem = pillars[pname].get("stem", "")
        main_star = calc_shishen(day_stem, stem)
        ten_gods[pname] = {"main_star": main_star, "hidden_stars": []}
    return ten_gods

TEST_CASES = [
  {
    "name": "1988-09-16 男 壬午日柱",
    "year": "戊辰",
    "month": "辛酉",
    "day": "壬午",
    "hour": "癸卯",
    "gender": "male",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "1990-01-15 女 甲子日柱",
    "year": "己巳",
    "month": "丁丑",
    "day": "甲子",
    "hour": "庚午",
    "gender": "female",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "1985-06-20 男 丙申日柱",
    "year": "乙丑",
    "month": "壬午",
    "day": "丙申",
    "hour": "壬辰",
    "gender": "male",
    "expect_categories": [
      "spouse_star"
    ]
  },
  {
    "name": "1992-03-10 女 丁亥日柱",
    "year": "壬申",
    "month": "癸卯",
    "day": "丁亥",
    "hour": "辛亥",
    "gender": "female",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "大运力场测试 男",
    "year": "戊辰",
    "month": "辛酉",
    "day": "壬午",
    "hour": "癸卯",
    "gender": "male",
    "dayun_sequence": [
      {
        "ganzhi": "壬戌",
        "step": 1,
        "age_display": "3-12岁"
      },
      {
        "ganzhi": "癸亥",
        "step": 2,
        "age_display": "13-22岁"
      },
      {
        "ganzhi": "甲子",
        "step": 3,
        "age_display": "23-32岁"
      },
      {
        "ganzhi": "乙丑",
        "step": 4,
        "age_display": "33-42岁"
      },
      {
        "ganzhi": "丙寅",
        "step": 5,
        "age_display": "43-52岁"
      }
    ],
    "expect_categories": [
      "dynamic_balance",
      "marriage_timing"
    ]
  },
  {
    "name": "甲寅日柱男",
    "year": "甲子",
    "month": "丙寅",
    "day": "甲寅",
    "hour": "丙子",
    "gender": "male",
    "expect_categories": [
      "marriage_palace"
    ]
  },
  {
    "name": "丙午日柱女",
    "year": "庚申",
    "month": "戊子",
    "day": "丙午",
    "hour": "己丑",
    "gender": "female",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "庚辰日柱男",
    "year": "戊午",
    "month": "甲子",
    "day": "庚辰",
    "hour": "丁亥",
    "gender": "male",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "辰戌丑未四库全男",
    "year": "甲辰",
    "month": "丙戌",
    "day": "壬丑",
    "hour": "辛未",
    "gender": "male",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "多偏财男",
    "year": "乙亥",
    "month": "乙酉",
    "day": "戊午",
    "hour": "乙卯",
    "gender": "male",
    "expect_categories": [
      "spouse_star"
    ]
  },
  {
    "name": "bazi_rules匹配 男",
    "year": "庚午",
    "month": "辛巳",
    "day": "丙子",
    "hour": "丙申",
    "gender": "male",
    "matched_bazi_rules": [
      {
        "rule_type": "marriage_day_pillar",
        "rule_code": "MARR-10098",
        "rule_name": "丙子规则",
        "content": {
          "text": "配偶美貌，好奇之心强而超。"
        },
        "priority": 100
      },
      {
        "rule_type": "marriage_ten_gods",
        "rule_code": "MARR-10005",
        "rule_name": "无偏财",
        "content": {
          "text": "异性缘份薄。"
        },
        "priority": 85
      }
    ],
    "expect_categories": [
      "spouse_star",
      "day_pillar_judgment",
      "ten_gods_judgment"
    ]
  },
  {
    "name": "bazi_rules混合 女",
    "year": "乙丑",
    "month": "丁亥",
    "day": "辛巳",
    "hour": "壬辰",
    "gender": "female",
    "matched_bazi_rules": [
      {
        "rule_type": "marriage_branch_pattern",
        "rule_code": "MARR-10134",
        "rule_name": "巳亥冲",
        "content": {
          "text": "贞洁之气偏弱。"
        },
        "priority": 85
      }
    ],
    "expect_categories": [
      "spouse_star",
      "branch_pattern_judgment"
    ]
  },
  {
    "name": "大运合化 甲己合",
    "year": "甲子",
    "month": "丙寅",
    "day": "己巳",
    "hour": "甲子",
    "gender": "female",
    "dayun_sequence": [
      {
        "ganzhi": "甲午",
        "step": 3,
        "age_display": "23-32岁"
      }
    ],
    "expect_categories": [
      "dynamic_balance"
    ]
  },
  {
    "name": "大运冲散 子午冲",
    "year": "甲午",
    "month": "丙寅",
    "day": "壬子",
    "hour": "庚子",
    "gender": "male",
    "dayun_sequence": [
      {
        "ganzhi": "戊午",
        "step": 3,
        "age_display": "23-32岁"
      }
    ],
    "expect_categories": [
      "dynamic_balance"
    ]
  },
  {
    "name": "壬子日柱男 水旺",
    "year": "壬午",
    "month": "壬子",
    "day": "壬子",
    "hour": "壬子",
    "gender": "male",
    "expect_categories": [
      "spouse_star",
      "marriage_palace"
    ]
  },
  {
    "name": "女命降级",
    "year": "甲子",
    "month": "甲子",
    "day": "甲子",
    "hour": "甲子",
    "gender": "female",
    "expect_categories": [
      "marriage_palace"
    ]
  },
  {
    "name": "formula_marriage 男",
    "year": "甲子",
    "month": "丙寅",
    "day": "戊辰",
    "hour": "甲子",
    "gender": "male",
    "matched_bazi_rules": [
      {
        "rule_type": "formula_marriage",
        "rule_code": "F-10526",
        "rule_name": "极旺婚姻",
        "content": {
          "text": "终必离婚。"
        },
        "priority": 100
      }
    ],
    "expect_categories": [
      "formula_judgment"
    ]
  },
  {
    "name": "deity规则 女",
    "year": "甲子",
    "month": "丙寅",
    "day": "庚午",
    "hour": "丁亥",
    "gender": "female",
    "matched_bazi_rules": [
      {
        "rule_type": "marriage_deity",
        "rule_code": "MARR-70",
        "rule_name": "日坐寡宿",
        "content": {
          "text": "女命逢之克夫"
        },
        "priority": 85
      }
    ],
    "expect_categories": [
      "deity_judgment"
    ]
  },
  {
    "name": "多规则混合 男",
    "year": "壬申",
    "month": "壬寅",
    "day": "丙午",
    "hour": "己亥",
    "gender": "male",
    "matched_bazi_rules": [
      {
        "rule_type": "marriage_day_pillar",
        "rule_code": "M1",
        "rule_name": "丙午婚姻",
        "content": {
          "text": "吵闹一辈子"
        },
        "priority": 100
      },
      {
        "rule_type": "marriage_stem_pattern",
        "rule_code": "M2",
        "rule_name": "壬丙冲",
        "content": {
          "text": "冲动败家"
        },
        "priority": 100
      },
      {
        "rule_type": "marriage_branch_pattern",
        "rule_code": "M3",
        "rule_name": "申寅冲",
        "content": {
          "text": "配偶远方来"
        },
        "priority": 85
      }
    ],
    "expect_categories": [
      "spouse_star",
      "day_pillar_judgment",
      "stem_pattern_judgment",
      "branch_pattern_judgment"
    ]
  },
  {
    "name": "置信度分层",
    "year": "甲子",
    "month": "丙寅",
    "day": "壬午",
    "hour": "辛亥",
    "gender": "male",
    "matched_bazi_rules": [
      {
        "rule_type": "marriage_bazi_pattern",
        "rule_code": "TH",
        "rule_name": "高置信度",
        "content": {
          "text": "白头到老。"
        },
        "priority": 200,
        "confidence": 0.92
      },
      {
        "rule_type": "marriage_general",
        "rule_code": "TL",
        "rule_name": "低置信度",
        "content": {
          "text": "小波折。"
        },
        "priority": 50
      }
    ],
    "expect_categories": [
      "bazi_pattern_judgment",
      "general_judgment"
    ]
  }
]

def build_test_input(case):
    pillars = make_pillars(case['year'], case['month'], case['day'], case['hour'])
    day_stem = pillars['day']['stem']
    ten_gods = make_ten_gods(pillars, day_stem)
    wuxing_power = {e: 0.0 for e in ['木', '火', '土', '金', '水']}
    for pname in ['year', 'month', 'day', 'hour']:
        s = pillars[pname].get('stem', '')
        b = pillars[pname].get('branch', '')
        if s in STEM_ELEMENTS: wuxing_power[STEM_ELEMENTS[s]] += 1.5
        if b in BRANCH_ELEMENTS: wuxing_power[BRANCH_ELEMENTS[b]] += 1.5
    return InferenceInput(
        day_stem=day_stem, day_branch=pillars['day']['branch'], gender=case['gender'],
        bazi_pillars=pillars, wangshuai=case.get('wangshuai', ''), wuxing_power=wuxing_power,
        score_breakdown={}, ten_gods=ten_gods, branch_relations=case.get('branch_relations', {}),
        deities=case.get('deities', {}), xi_ji_elements=case.get('xi_ji_elements', {'xi_shen': [], 'ji_shen': []}),
        dayun_sequence=case.get('dayun_sequence', []), special_liunians=[],
        matched_bazi_rules=case.get('matched_bazi_rules', []),
    )

def run_tests():
    engine = MarriageInferenceEngine.get_instance()
    passed, failed, total = 0, 0, len(TEST_CASES)
    print(f"\n{'='*60}")
    print(f"  婚姻推理引擎测试集 - {total} 个用例")
    print(f"{'='*60}\n")
    for i, case in enumerate(TEST_CASES, 1):
        inp = build_test_input(case)
        result = engine.infer(inp)
        cats_hit = set(c.category for c in result.chains)
        expected = set(case.get('expect_categories', []))
        ok = len(cats_hit & expected) > 0
        if ok: passed += 1
        else: failed += 1
        status = '\u2705' if ok else '\u274c'
        print(f"[{i:2d}/{total}] {status} {case['name']}")
        print(f"        链条:{len(result.chains)} 命中:{sorted(cats_hit & expected)} 未中:{sorted(expected - cats_hit)}")
        for c in result.chains[:2]:
            print(f"          [{c.category}] {c.conclusion[:60]} ({c.confidence:.2f})")
        if len(result.chains) > 2: print(f"          ... +{len(result.chains)-2}条")
        print()
    rate = passed / total * 100 if total > 0 else 0
    print(f"{'='*60}")
    print(f"  结果: {passed}/{total} 通过  通过率: {rate:.1f}%")
    print(f"{'='*60}")
    return passed, failed

if __name__ == '__main__':
    p, f = run_tests()
    sys.exit(0 if f == 0 else 1)

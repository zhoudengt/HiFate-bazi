#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 2025.12.03算法公式.xlsx 规则到数据库

支持的规则类型:
- 总评: 十神坐格式等
- 婚姻: 十神相关
- 财富: 十神、喜忌、旺衰等
- 事业: 十神、旺衰、神煞等
- 性格: 十神相关
- 身体: 十神相关
- 父母: 十神相关（新增）
- 子女: 十神相关
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# 尝试导入 pandas
try:
    import pandas as pd
except ImportError:
    print("❌ 需要安装 pandas: pip install pandas openpyxl")
    sys.exit(1)

XLSX_FILE = os.path.join(PROJECT_ROOT, "docs", "2025.12.03算法公式.xlsx")

# 天干地支常量
STEMS = list("甲乙丙丁戊己庚辛壬癸")
BRANCHES = list("子丑寅卯辰巳午未申酉戌亥")

# 十神列表
TEN_GODS = ["比肩", "劫财", "食神", "伤官", "正财", "偏财", "正官", "偏官", "七杀", "正印", "偏印"]

# 规则类型映射
RULE_TYPE_MAP = {
    "总评": "summary",
    "婚姻": "marriage", 
    "桃花": "peach_blossom",
    "财富": "wealth",
    "事业": "career",
    "性格": "character",
    "身体": "health",
    "子女": "children",
    "父母": "parents",  # 新增
}

# 性别映射
GENDER_MAP = {
    "无论男女": None,
    "男": "male",
    "女": "female",
}


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    conditions: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


@dataclass
class RuleRecord:
    """规则记录"""
    rule_id: int
    rule_code: str
    rule_name: str
    rule_type: str
    rule_category: str
    priority: int
    conditions: Dict[str, Any]
    content: Dict[str, Any]
    description: str
    source: str


@dataclass
class SkippedRule:
    """跳过的规则"""
    rule_id: int
    reason: str
    source: str


class RuleParser:
    """规则解析器"""
    
    # 常见错别字修正映射
    TYPO_FIXES = {
        "丙成": "丙戌",
        "已卯": "己卯",
        "辛已": "辛巳",
        "戍": "戌",
        "己巳": "己巳",  # 保持不变
    }
    
    # 需要清理的引号字符 - 使用 Unicode 转义确保正确
    # U+201C: " (LEFT DOUBLE QUOTATION MARK)
    # U+201D: " (RIGHT DOUBLE QUOTATION MARK)
    # U+201E: „ (DOUBLE LOW-9 QUOTATION MARK)
    # U+201F: ‟ (DOUBLE HIGH-REVERSED-9 QUOTATION MARK)
    # U+0022: " (QUOTATION MARK)
    # U+0027: ' (APOSTROPHE)
    QUOTE_CHARS = [
        '\u201c', '\u201d', '\u201e', '\u201f',  # 中文双引号
        '\u2018', '\u2019',  # 中文单引号
        '"', "'", '`',  # ASCII 引号
    ]
    
    @classmethod
    def fix_typos(cls, text: str) -> str:
        """修正常见错别字"""
        for wrong, correct in cls.TYPO_FIXES.items():
            text = text.replace(wrong, correct)
        return text
    
    @classmethod
    def clean_quotes(cls, text: str) -> str:
        """清理所有引号字符"""
        for char in cls.QUOTE_CHARS:
            text = text.replace(char, '')
        return text
    
    @classmethod
    def parse(cls, row: Dict[str, Any], sheet_name: str) -> ParseResult:
        """解析规则条件"""
        cond1 = str(row.get("筛选条件1", "")).strip()
        cond2 = cls.fix_typos(str(row.get("筛选条件2", "")).strip())  # 修正错别字
        qty = str(row.get("数量", "")).strip() if pd.notna(row.get("数量")) else ""
        gender = str(row.get("性别", "无论男女")).strip()
        
        if not cond1 or not cond2:
            return ParseResult(False, reason="缺少筛选条件")
        
        # 构建条件
        conds: List[Dict[str, Any]] = []
        
        # 添加性别条件
        gender_value = GENDER_MAP.get(gender)
        if gender_value:
            conds.append({"gender": gender_value})
        
        # 根据条件类型解析
        result = cls._parse_by_type(cond1, cond2, qty, sheet_name)
        if not result.success:
            return result
        
        if result.conditions:
            if isinstance(result.conditions, list):
                conds.extend(result.conditions)
            else:
                conds.append(result.conditions)
        
        # 组合条件
        if not conds:
            return ParseResult(False, reason="未生成有效条件")
        
        if len(conds) == 1:
            return ParseResult(True, conditions=conds[0])
        
        return ParseResult(True, conditions={"all": conds})
    
    @classmethod
    def _parse_by_type(cls, cond1: str, cond2: str, qty: str, sheet_name: str) -> ParseResult:
        """根据条件类型解析"""
        
        # 神煞条件
        if cond1 == "神煞":
            return cls._parse_shensha(cond2)
        
        # 日柱条件
        if cond1 == "日柱":
            return cls._parse_day_pillar(cond2)
        
        # 月柱条件
        if cond1 == "月柱":
            return cls._parse_month_pillar(cond2)
        
        # 年柱条件
        if cond1 == "年柱":
            return cls._parse_year_pillar(cond2)
        
        # 时柱条件
        if cond1 == "时柱":
            return cls._parse_hour_pillar(cond2, qty)
        
        # 十神条件
        if cond1 == "十神":
            return cls._parse_ten_gods(cond2)
        
        # 天干地支条件
        if cond1 == "天干地支":
            return cls._parse_stem_branch(cond2)
        
        # 地支条件
        if cond1 == "地支":
            return cls._parse_branch(cond2)
        
        # 十二地支条件
        if cond1 == "十二地支":
            return cls._parse_branch(cond2)  # 暂时使用相同解析逻辑
        
        # 藏干副星条件
        if cond1 == "藏干副星":
            return cls._parse_zanggan_fuxing(cond2)
        
        # 日支条件
        if cond1 == "日支":
            return cls._parse_day_branch(cond2, qty)
        
        # 旺衰条件
        if cond1 == "旺衰":
            return cls._parse_wangshuai(cond2)
        
        # 命格条件
        if cond1 == "命格":
            return cls._parse_minggge(cond2)
        
        # 四柱条件
        if cond1 == "四柱":
            return cls._parse_four_pillars(cond2)
        
        # 十神命格条件
        if cond1 == "十神命格":
            return cls._parse_shishen_mingge(cond2)
        
        # 复合条件类型（用逗号分隔）
        if "，" in cond1 or "," in cond1:
            return cls._parse_composite(cond1, cond2, qty)
        
        return ParseResult(False, reason=f"未支持的条件类型: {cond1}")
    
    @classmethod
    def _parse_shensha(cls, cond2: str) -> ParseResult:
        """解析神煞条件"""
        conds = []
        
        # 四柱神煞有XXX
        if "四柱神煞有" in cond2:
            # 解析神煞名称
            text = cond2.replace("四柱神煞有", "")
            
            # 处理"且"、"又有"等连接词
            if "，且有" in text or "，又有" in text:
                parts = re.split(r"[，,]且有|[，,]又有", text)
                for part in parts:
                    shensha = part.strip()
                    if shensha:
                        conds.append({"deities_in_any_pillar": shensha})
                return ParseResult(True, conditions=conds)
            
            # 处理"或"
            if "或" in text:
                parts = text.split("或")
                any_conds = []
                for part in parts:
                    shensha = part.strip()
                    if shensha:
                        any_conds.append({"deities_in_any_pillar": shensha})
                return ParseResult(True, conditions={"any": any_conds})
            
            # 单个神煞
            shensha = text.strip()
            if shensha:
                return ParseResult(True, conditions={"deities_in_any_pillar": shensha})
        
        # X柱神煞有XXX
        pillar_match = re.match(r"(年柱|月柱|日柱|时柱)神煞有(.+)", cond2)
        if pillar_match:
            pillar_name = pillar_match.group(1)
            shensha_text = pillar_match.group(2)
            pillar_key = cls._pillar_to_key(pillar_name)
            
            # 处理"或"
            if "或" in shensha_text:
                parts = shensha_text.split("或")
                any_conds = []
                for part in parts:
                    shensha = part.strip()
                    if shensha:
                        any_conds.append({f"deities_in_{pillar_key}": shensha})
                return ParseResult(True, conditions={"any": any_conds})
            
            shensha = shensha_text.strip()
            return ParseResult(True, conditions={f"deities_in_{pillar_key}": shensha})
        
        # X柱有神煞XXX 且有YYY
        pillar_match = re.match(r"(年柱|月柱|日柱|时柱)有(.+)", cond2)
        if pillar_match:
            pillar_name = pillar_match.group(1)
            rest = pillar_match.group(2)
            pillar_key = cls._pillar_to_key(pillar_name)
            
            # 解析多个神煞
            parts = re.split(r"[，,]且有|[，,]又有", rest)
            for part in parts:
                shensha = part.strip()
                if shensha:
                    conds.append({f"deities_in_{pillar_key}": shensha})
            
            if conds:
                return ParseResult(True, conditions=conds)
        
        # 特殊情况：四柱神煞有X，又有Y，且八字有ZZ
        complex_match = re.match(r"四柱神煞有(.+)，又有(.+)，且八字有(.+)", cond2)
        if complex_match:
            shensha1 = complex_match.group(1).strip()
            shensha2 = complex_match.group(2).strip()
            branches = complex_match.group(3).strip()
            
            conds.append({"deities_in_any_pillar": shensha1})
            conds.append({"deities_in_any_pillar": shensha2})
            
            # 解析地支
            for branch in branches:
                if branch in BRANCHES:
                    conds.append({"branches_count": {"names": [branch], "min": 1}})
            
            return ParseResult(True, conditions=conds)
        
        # 柱中出现神煞XXX
        if "柱中出现神煞" in cond2 or "柱中出现" in cond2:
            shensha = cond2.replace("柱中出现神煞", "").replace("柱中出现", "").strip()
            return ParseResult(True, conditions={"deities_in_any_pillar": shensha})
        
        # 四柱中出现XXX
        if "四柱中出现" in cond2:
            shensha = cond2.replace("四柱中出现", "").strip()
            if "和" in shensha:
                parts = shensha.split("和")
                for part in parts:
                    conds.append({"deities_in_any_pillar": part.strip()})
                return ParseResult(True, conditions=conds)
            return ParseResult(True, conditions={"deities_in_any_pillar": shensha})
        
        # 四柱中有神煞XXX
        if "四柱中有神煞" in cond2:
            shensha = cond2.replace("四柱中有神煞", "").strip()
            return ParseResult(True, conditions={"deities_in_any_pillar": shensha})
        
        return ParseResult(False, reason=f"未识别的神煞条件: {cond2}")
    
    @classmethod
    def _parse_day_pillar(cls, cond2: str) -> ParseResult:
        """解析日柱条件"""
        # 清理引号用于匹配
        clean_cond = cls.clean_quotes(cond2)
        
        # 日柱是干支（如"甲子"）
        if len(clean_cond) == 2 and clean_cond[0] in STEMS and clean_cond[1] in BRANCHES:
            return ParseResult(True, conditions={
                "pillar_equals": {"pillar": "day", "values": [clean_cond]}
            })
        
        # 日柱有十神
        ten_god_match = re.match(r"日柱有(.+)", clean_cond)
        if ten_god_match:
            ten_god = ten_god_match.group(1).strip()
            if ten_god in TEN_GODS:
                # 日柱有某十神，可以是主星或副星
                return ParseResult(True, conditions={
                    "any": [
                        {"main_star_in_day": ten_god},
                        {"ten_gods_sub": {"names": [ten_god], "pillars": ["day"], "min": 1}}
                    ]
                })
        
        # 日柱上有X（天干）
        stem_match = re.match(r"日柱上有(.)", clean_cond)
        if stem_match:
            stem = stem_match.group(1)
            if stem in STEMS:
                return ParseResult(True, conditions={
                    "pillar_in": {"pillar": "day", "part": "stem", "values": [stem]}
                })
        
        # 日柱天干为X，且八字的四个地支中有Y字
        day_stem_branch_match = re.match(r'日柱天干为([甲乙丙丁戊己庚辛壬癸])[，,]且八字的四个地支中有([子丑寅卯辰巳午未申酉戌亥])字', clean_cond)
        if day_stem_branch_match:
            stem = day_stem_branch_match.group(1)
            branch = day_stem_branch_match.group(2)
            return ParseResult(True, conditions={
                "all": [
                    {"pillar_in": {"pillar": "day", "part": "stem", "values": [stem]}},
                    {"branches_count": {"names": [branch], "min": 1}}
                ]
            })
        
        # 日柱天干为X
        day_stem_match = re.match(r'日柱天干为([甲乙丙丁戊己庚辛壬癸])', clean_cond)
        if day_stem_match:
            stem = day_stem_match.group(1)
            return ParseResult(True, conditions={
                "pillar_in": {"pillar": "day", "part": "stem", "values": [stem]}
            })
        
        return ParseResult(False, reason=f"未识别的日柱条件: {cond2}")
    
    @classmethod
    def _parse_month_pillar(cls, cond2: str) -> ParseResult:
        """解析月柱条件"""
        # 月柱有十神
        ten_god_match = re.match(r"月柱有(.+)", cond2)
        if ten_god_match:
            ten_god = ten_god_match.group(1).strip()
            if ten_god in TEN_GODS:
                return ParseResult(True, conditions={
                    "any": [
                        {"main_star_in_pillar": {"pillar": "month", "eq": ten_god}},
                        {"ten_gods_sub": {"names": [ten_god], "pillars": ["month"], "min": 1}}
                    ]
                })
        
        # 月柱上有X
        stem_match = re.match(r"月柱上有(.)", cond2)
        if stem_match:
            stem = stem_match.group(1)
            if stem in STEMS:
                return ParseResult(True, conditions={
                    "pillar_in": {"pillar": "month", "part": "stem", "values": [stem]}
                })
        
        # 月柱副星有XXX
        sub_match = re.match(r"月柱副星有(.+)", cond2)
        if sub_match:
            ten_god = sub_match.group(1).strip()
            return ParseResult(True, conditions={
                "ten_gods_sub": {"names": [ten_god], "pillars": ["month"], "min": 1}
            })
        
        return ParseResult(False, reason=f"未识别的月柱条件: {cond2}")
    
    @classmethod
    def _parse_year_pillar(cls, cond2: str) -> ParseResult:
        """解析年柱条件"""
        # 年柱有十神
        ten_god_match = re.match(r"年柱有(.+)", cond2)
        if ten_god_match:
            ten_god = ten_god_match.group(1).strip()
            if ten_god in TEN_GODS:
                return ParseResult(True, conditions={
                    "any": [
                        {"main_star_in_year": ten_god},
                        {"ten_gods_sub": {"names": [ten_god], "pillars": ["year"], "min": 1}}
                    ]
                })
        
        # 年柱上有X
        stem_match = re.match(r"年柱上有(.)", cond2)
        if stem_match:
            stem = stem_match.group(1)
            if stem in STEMS:
                return ParseResult(True, conditions={
                    "pillar_in": {"pillar": "year", "part": "stem", "values": [stem]}
                })
        
        return ParseResult(False, reason=f"未识别的年柱条件: {cond2}")
    
    @classmethod
    def _parse_hour_pillar(cls, cond2: str, qty: str) -> ParseResult:
        """解析时柱条件"""
        # 时柱有十神
        ten_god_match = re.match(r"时柱有(.+)", cond2)
        if ten_god_match:
            ten_god = ten_god_match.group(1).strip()
            if ten_god in TEN_GODS:
                return ParseResult(True, conditions={
                    "any": [
                        {"main_star_in_pillar": {"pillar": "hour", "eq": ten_god}},
                        {"ten_gods_sub": {"names": [ten_god], "pillars": ["hour"], "min": 1}}
                    ]
                })
        
        # 时柱上有X
        stem_match = re.match(r"时柱上有(.)", cond2)
        if stem_match:
            stem = stem_match.group(1)
            if stem in STEMS:
                return ParseResult(True, conditions={
                    "pillar_in": {"pillar": "hour", "part": "stem", "values": [stem]}
                })
        
        # 时柱为干支
        if len(cond2) == 2 and cond2[0] in STEMS and cond2[1] in BRANCHES:
            return ParseResult(True, conditions={
                "pillar_equals": {"pillar": "hour", "values": [cond2]}
            })
        
        # 时柱地支列表（如"子、丑、寅、卯"）
        if "、" in cond2:
            branches = [b.strip() for b in cond2.split("、")]
            if all(b in BRANCHES for b in branches):
                if qty == "其中之一":
                    return ParseResult(True, conditions={
                        "pillar_in": {"pillar": "hour", "part": "branch", "values": branches}
                    })
        
        return ParseResult(False, reason=f"未识别的时柱条件: {cond2}")
    
    @classmethod
    def _parse_ten_gods(cls, cond2: str) -> ParseResult:
        """解析十神条件"""
        conds = []
        
        # X柱主星是Y，且...
        pillar_main_match = re.match(r"(年柱|月柱|日柱|时柱)主星是(.+?)([，,]且.+)?$", cond2)
        if pillar_main_match:
            pillar_name = pillar_main_match.group(1)
            ten_god = pillar_main_match.group(2).strip()
            extra = pillar_main_match.group(3)
            pillar_key = cls._pillar_to_key(pillar_name)
            
            if ten_god in TEN_GODS:
                if pillar_key == "day":
                    conds.append({"main_star_in_day": ten_god})
                elif pillar_key == "year":
                    conds.append({"main_star_in_year": ten_god})
                else:
                    conds.append({"main_star_in_pillar": {"pillar": pillar_key, "eq": ten_god}})
                
                # 处理额外条件
                if extra:
                    extra = extra.lstrip("，,且")
                    # X柱主星是Y
                    extra_pillar_match = re.match(r"(年柱|月柱|日柱|时柱)主星是(.+)", extra)
                    if extra_pillar_match:
                        extra_pillar = cls._pillar_to_key(extra_pillar_match.group(1))
                        extra_god = extra_pillar_match.group(2).strip()
                        if extra_god in TEN_GODS:
                            if extra_pillar == "day":
                                conds.append({"main_star_in_day": extra_god})
                            elif extra_pillar == "year":
                                conds.append({"main_star_in_year": extra_god})
                            else:
                                conds.append({"main_star_in_pillar": {"pillar": extra_pillar, "eq": extra_god}})
                    # 身强或极强
                    elif "身强" in extra or "极强" in extra:
                        conds.append({"wangshuai": ["身旺", "极旺"]})
                    # X柱有长生
                    elif "长生" in extra:
                        conds.append({"star_fortune_in_year": "长生"})
                
                return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        # X柱有十神
        pillar_match = re.match(r"(年柱|月柱|日柱|时柱)有(.+)", cond2)
        if pillar_match:
            pillar_name = pillar_match.group(1)
            ten_god = pillar_match.group(2).strip()
            pillar_key = cls._pillar_to_key(pillar_name)
            
            if ten_god in TEN_GODS:
                if pillar_key == "day":
                    return ParseResult(True, conditions={"main_star_in_day": ten_god})
                elif pillar_key == "year":
                    return ParseResult(True, conditions={"main_star_in_year": ten_god})
                else:
                    return ParseResult(True, conditions={
                        "main_star_in_pillar": {"pillar": pillar_key, "eq": ten_god}
                    })
        
        # 四柱主星出现多个十神
        if "四柱中主星出现" in cond2 or "四柱中出现" in cond2:
            # 匹配"正官，正印，偏印，正财中的2个及2个以上"
            match = re.search(r"([\u4e00-\u9fa5、，,]+)中的(\d+)个", cond2)
            if match:
                gods_text = match.group(1)
                count = int(match.group(2))
                gods = re.split(r"[、，,]", gods_text)
                gods = [g.strip() for g in gods if g.strip() in TEN_GODS]
                if gods:
                    return ParseResult(True, conditions={
                        "ten_gods_main": {"names": gods, "min": count}
                    })
        
        # 十神数量条件
        count_match = re.search(r"(\d+)个以上（包含\d+个）|(\d+)个或两个以上|(\d+)个以上", cond2)
        if count_match:
            count = int(count_match.group(1) or count_match.group(2) or count_match.group(3))
            # 提取十神名称
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={
                        "ten_gods_total": {"names": [god], "min": count}
                    })
        
        # 主星和副星数量
        if "主星和副星" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    count_match = re.search(r"(\d+)个", cond2)
                    if count_match:
                        count = int(count_match.group(1))
                        return ParseResult(True, conditions={
                            "ten_gods_total": {"names": [god], "min": count}
                        })
        
        # 日柱和月柱冲
        if "日柱和月柱形成相互冲的关系" in cond2:
            return ParseResult(True, conditions={
                "pillar_relation": {"pillar_a": "day", "pillar_b": "month", "relation": "chong"}
            })
        
        # 四柱天干主星出现XXX和YYY
        if "四柱的天干主星出现" in cond2 or "四柱天干主星出现" in cond2:
            # 提取十神
            gods = []
            for god in TEN_GODS:
                if god in cond2:
                    gods.append(god)
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_main": {"names": gods, "min": len(gods)}
                })
        
        # 四柱的天干出现正财和偏财
        if "四柱的天干出现" in cond2:
            gods = []
            for god in TEN_GODS:
                if god in cond2:
                    gods.append(god)
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_main": {"names": gods, "min": len(gods)}
                })
        
        # 食神、伤官多，能量强
        if "食神" in cond2 and "伤官" in cond2 and "能量强" in cond2:
            return ParseResult(True, conditions={
                "ten_gods_total": {"names": ["食神", "伤官"], "min": 3}
            })
        
        # 喜神有XXX
        if "喜神有" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={"xishen": god})
        
        # ========== 新增：十神坐格式 ==========
        # "食神坐偏财"：表示天干是食神，地支是偏财（同一柱）
        # 格式：X坐Y（X和Y都是十神）
        zuo_match = re.match(r"(.+)坐(.+)", cond2)
        if zuo_match:
            stem_god = zuo_match.group(1).strip()
            branch_god = zuo_match.group(2).strip()
            
            if stem_god in TEN_GODS and branch_god in TEN_GODS:
                # 检查任意柱的天干是stem_god，且该柱的地支藏干有branch_god
                # 使用any组合，检查年、月、日、时四柱
                pillar_conds = []
                for pillar in ["year", "month", "day", "hour"]:
                    if pillar == "day":
                        pillar_conds.append({
                            "all": [
                                {"main_star_in_day": stem_god},
                                {"ten_gods_sub": {"names": [branch_god], "pillars": [pillar], "min": 1}}
                            ]
                        })
                    elif pillar == "year":
                        pillar_conds.append({
                            "all": [
                                {"main_star_in_year": stem_god},
                                {"ten_gods_sub": {"names": [branch_god], "pillars": [pillar], "min": 1}}
                            ]
                        })
                    else:
                        pillar_conds.append({
                            "all": [
                                {"main_star_in_pillar": {"pillar": pillar, "eq": stem_god}},
                                {"ten_gods_sub": {"names": [branch_god], "pillars": [pillar], "min": 1}}
                            ]
                        })
                return ParseResult(True, conditions={"any": pillar_conds})
        
        # ========== 新增：命理学术语解析 ==========
        # "透"：天干出现（已有支持，通过main_star_in_pillar）
        # "得令"：月令当值（需要检查月柱）
        if "得令" in cond2 or "失令" in cond2:
            # 提取十神
            for god in TEN_GODS:
                if god in cond2:
                    # 检查月柱主星是该十神
                    return ParseResult(True, conditions={"main_star_in_pillar": {"pillar": "month", "eq": god}})
        
        # "克制"：五行相克关系（需要检查十神相克）
        # 暂时标记为待确认，需要更复杂的逻辑
        
        # "太旺"：旺衰极旺（已有支持）
        if "太旺" in cond2 or "极旺" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["极旺"]})
        
        # "衰弱"：力量弱
        # 结合旺衰判断，暂时标记为待确认（需要更复杂的逻辑）
        
        # "喜用"：喜用神（已有支持：xishen）
        if "喜用" in cond2 or "为喜用" in cond2 or "且是喜用" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={"xishen": god})
        
        # "忌神"：忌神（需要扩展：jishen）
        if "忌神" in cond2 or "为忌" in cond2 or "为忌神" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    # 使用jishen条件（如果规则引擎支持）
                    return ParseResult(True, conditions={"jishen": god})
        
        # "喜用"：喜用神（已有支持：xishen）
        if "喜用" in cond2 or "为喜用" in cond2 or "且是喜用" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={"xishen": god})
        
        # X干Y（如"年干偏官"、"月干正印"）
        gan_match = re.match(r"(年|月|日|时)干(.+)", cond2)
        if gan_match:
            pillar_name = gan_match.group(1) + "柱"
            ten_god = gan_match.group(2).strip()
            pillar_key = cls._pillar_to_key(pillar_name)
            
            if ten_god in TEN_GODS:
                if pillar_key == "day":
                    return ParseResult(True, conditions={"main_star_in_day": ten_god})
                elif pillar_key == "year":
                    return ParseResult(True, conditions={"main_star_in_year": ten_god})
                else:
                    return ParseResult(True, conditions={
                        "main_star_in_pillar": {"pillar": pillar_key, "eq": ten_god}
                    })
        
        # X支Y（如"日支偏官"）
        zhi_match = re.match(r"(年|月|日|时)支(.+)", cond2)
        if zhi_match:
            pillar_name = zhi_match.group(1) + "柱"
            ten_god = zhi_match.group(2).strip()
            pillar_key = cls._pillar_to_key(pillar_name)
            
            if ten_god in TEN_GODS:
                return ParseResult(True, conditions={
                    "ten_gods_sub": {"names": [ten_god], "pillars": [pillar_key], "min": 1}
                })
        
        # X柱透Y（如"月柱透比肩"）
        tou_match = re.match(r"(年|月|日|时)柱透(.+)", cond2)
        if tou_match:
            pillar_name = tou_match.group(1) + "柱"
            ten_god = tou_match.group(2).strip()
            pillar_key = cls._pillar_to_key(pillar_name)
            
            if ten_god in TEN_GODS:
                if pillar_key == "day":
                    return ParseResult(True, conditions={"main_star_in_day": ten_god})
                elif pillar_key == "year":
                    return ParseResult(True, conditions={"main_star_in_year": ten_god})
                else:
                    return ParseResult(True, conditions={
                        "main_star_in_pillar": {"pillar": pillar_key, "eq": ten_god}
                    })
        
        return ParseResult(False, reason=f"未识别的十神条件: {cond2}")
    
    @classmethod
    def _parse_stem_branch(cls, cond2: str) -> ParseResult:
        """解析天干地支五行条件"""
        conds = []
        
        # 五行数量条件
        # 格式: 对应五行属性X大于N个（包含N个）
        element_pattern = r"对应五行属性([木火土金水])([大小])于(\d+)个"
        
        # 处理"并且"分隔的多个条件
        parts = re.split(r"[，,]并且|并且", cond2)
        
        for part in parts:
            part = part.strip()
            
            # 五行数量
            element_match = re.search(element_pattern, part)
            if element_match:
                element = element_match.group(1)
                op = element_match.group(2)
                count = int(element_match.group(3))
                
                if op == "大":
                    conds.append({"element_total": {"names": [element], "min": count}})
                else:  # 小于
                    conds.append({"element_total": {"names": [element], "max": count}})
                continue
            
            # 天干数量: 八字中甲和乙数量3个以上
            stem_pattern = r"八字中([甲乙丙丁戊己庚辛壬癸])(?:和([甲乙丙丁戊己庚辛壬癸]))?数量(\d+)个([以上以下])"
            stem_match = re.search(stem_pattern, part)
            if stem_match:
                stem1 = stem_match.group(1)
                stem2 = stem_match.group(2)
                count = int(stem_match.group(3))
                op = stem_match.group(4)
                
                stems = [stem1]
                if stem2:
                    stems.append(stem2)
                
                if op == "以上":
                    conds.append({"stems_count": {"names": stems, "min": count}})
                else:
                    conds.append({"stems_count": {"names": stems, "max": count}})
                continue
        
        if conds:
            return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        return ParseResult(False, reason=f"未识别的天干地支条件: {cond2}")
    
    @classmethod
    def _parse_branch(cls, cond2: str) -> ParseResult:
        """解析地支条件"""
        # 地支内有X，并且有Y
        if "四柱地支内有" in cond2:
            branches = []
            for branch in BRANCHES:
                if branch in cond2:
                    branches.append(branch)
            if branches:
                conds = [{"branches_count": {"names": [b], "min": 1}} for b in branches]
                return ParseResult(True, conditions=conds)
        
        return ParseResult(False, reason=f"未识别的地支条件: {cond2}")
    
    @classmethod
    def _parse_zanggan_fuxing(cls, cond2: str) -> ParseResult:
        """解析藏干副星条件"""
        # 提取十神
        for god in TEN_GODS:
            if god in cond2:
                # 检查是否有柱位信息
                if "年" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year"], "min": 1}})
                elif "月" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["month"], "min": 1}})
                elif "日" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["day"], "min": 1}})
                elif "时" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["hour"], "min": 1}})
                else:
                    # 默认检查所有柱
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year", "month", "day", "hour"], "min": 1}})
        
        return ParseResult(False, reason=f"未识别的藏干副星条件: {cond2}")
    
    @classmethod
    def _parse_day_branch(cls, cond2: str, qty: str) -> ParseResult:
        """解析日支条件"""
        # 日支列表（如"辰、戌、丑、未"）
        if "、" in cond2:
            branches = [b.strip() for b in cond2.split("、")]
            if all(b in BRANCHES for b in branches):
                if qty == "其中之一":
                    return ParseResult(True, conditions={
                        "pillar_in": {"pillar": "day", "part": "branch", "values": branches}
                    })
        
        # 单个地支
        if len(cond2) == 1 and cond2 in BRANCHES:
            return ParseResult(True, conditions={
                "pillar_in": {"pillar": "day", "part": "branch", "values": [cond2]}
            })
        
        return ParseResult(False, reason=f"未识别的日支条件: {cond2}")
    
    @classmethod
    def _parse_zanggan_fuxing(cls, cond2: str) -> ParseResult:
        """解析藏干副星条件"""
        # 提取十神
        for god in TEN_GODS:
            if god in cond2:
                # 检查是否有柱位信息
                if "年" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year"], "min": 1}})
                elif "月" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["month"], "min": 1}})
                elif "日" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["day"], "min": 1}})
                elif "时" in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["hour"], "min": 1}})
                else:
                    # 默认检查所有柱
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year", "month", "day", "hour"], "min": 1}})
        
        return ParseResult(False, reason=f"未识别的藏干副星条件: {cond2}")
    
    @classmethod
    def _parse_wangshuai(cls, cond2: str) -> ParseResult:
        """解析旺衰条件"""
        if "身弱" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["身弱"]})
        if "身旺" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["身旺"]})
        if "极旺" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["极旺"]})
        
        return ParseResult(False, reason=f"未识别的旺衰条件: {cond2}")
    
    @classmethod
    def _parse_minggge(cls, cond2: str) -> ParseResult:
        """解析命格条件"""
        if "从格" in cond2:
            return ParseResult(True, conditions={"ming_ge": "从格"})
        
        return ParseResult(False, reason=f"未识别的命格条件: {cond2}")
    
    @classmethod
    def _parse_four_pillars(cls, cond2: str) -> ParseResult:
        """解析四柱条件"""
        # 四柱天干之间，地支之间有多个相冲关系
        if "多个相冲关系" in cond2:
            return ParseResult(True, conditions={"multi_chong": {"min": 2}})
        
        # 四柱有辰、戌、丑、未相关
        if "辰、戌、丑、未" in cond2 or "辰戌丑未" in cond2:
            # 四柱有辰、戌、丑、未
            if "但是没有辰戌或丑未" in cond2:
                # 有墓库但不相冲
                count_match = re.search(r"其中([两二三四])个", cond2)
                if count_match:
                    count_text = count_match.group(1)
                    count_map = {"两": 2, "二": 2, "三": 3, "四": 4}
                    count = count_map.get(count_text, 2)
                    return ParseResult(True, conditions={
                        "all": [
                            {"branches_count": {"names": ["辰", "戌", "丑", "未"], "min": count}},
                            {"no_chong_pair": [["辰", "戌"], ["丑", "未"]]}
                        ]
                    })
            elif "没有" in cond2:
                return ParseResult(True, conditions={
                    "branches_count": {"names": ["辰", "戌", "丑", "未"], "eq": 0}
                })
            else:
                return ParseResult(True, conditions={
                    "branches_count": {"names": ["辰", "戌", "丑", "未"], "min": 1}
                })
        
        # 四柱中同时出现干支
        if "同时出现" in cond2:
            # 提取干支
            pillars = []
            for stem in STEMS:
                for branch in BRANCHES:
                    ganzhi = stem + branch
                    if ganzhi in cond2:
                        pillars.append(ganzhi)
            
            if pillars:
                conds = []
                for p in pillars:
                    conds.append({
                        "any": [
                            {"pillar_equals": {"pillar": "year", "values": [p]}},
                            {"pillar_equals": {"pillar": "month", "values": [p]}},
                            {"pillar_equals": {"pillar": "day", "values": [p]}},
                            {"pillar_equals": {"pillar": "hour", "values": [p]}}
                        ]
                    })
                return ParseResult(True, conditions=conds)
        
        # 时柱为庚寅
        if "时柱为" in cond2:
            ganzhi = cond2.replace("时柱为", "").strip()
            if len(ganzhi) == 2:
                return ParseResult(True, conditions={
                    "pillar_equals": {"pillar": "hour", "values": [ganzhi]}
                })
        
        return ParseResult(False, reason=f"未识别的四柱条件: {cond2}")
    
    @classmethod
    def _parse_shishen_mingge(cls, cond2: str) -> ParseResult:
        """解析十神命格条件"""
        # 十神作为命格
        if cond2 in TEN_GODS:
            return ParseResult(True, conditions={"shishen_ming_ge": cond2})
        
        return ParseResult(False, reason=f"未识别的十神命格条件: {cond2}")
    
    @classmethod
    def _parse_composite(cls, cond1: str, cond2: str, qty: str) -> ParseResult:
        """解析复合条件"""
        conds = []
        
        # 四柱，十神：四柱的天干出现正财和偏财
        if "四柱" in cond1 and "十神" in cond1:
            if "天干出现" in cond2 or "天干主星出现" in cond2:
                gods = [g for g in TEN_GODS if g in cond2]
                if gods:
                    return ParseResult(True, conditions={
                        "ten_gods_main": {"names": gods, "min": len(gods)}
                    })
        
        # 天干，地支：年柱和日柱形成合的关系，日柱和时柱形成冲的关系
        if "天干" in cond1 and "地支" in cond1:
            # 年柱和日柱形成合的关系
            if "年柱和日柱形成合" in cond2:
                conds.append({"pillar_relation": {"pillar_a": "year", "pillar_b": "day", "relation": "he"}})
            # 日柱和时柱形成冲的关系
            if "日柱和时柱形成冲" in cond2:
                conds.append({"pillar_relation": {"pillar_a": "day", "pillar_b": "hour", "relation": "chong"}})
            # 日柱和时柱天干或地支相合
            if "日柱和时柱天干或地支相合" in cond2:
                conds.append({
                    "any": [
                        {"pillar_relation": {"pillar_a": "day", "pillar_b": "hour", "relation": "he", "part": "stem"}},
                        {"pillar_relation": {"pillar_a": "day", "pillar_b": "hour", "relation": "liuhe"}}
                    ]
                })
            # 年柱和月柱天干或地支相冲
            if "年柱和月柱天干或地支相冲" in cond2:
                conds.append({
                    "any": [
                        {"pillar_relation": {"pillar_a": "year", "pillar_b": "month", "relation": "chong", "part": "stem"}},
                        {"pillar_relation": {"pillar_a": "year", "pillar_b": "month", "relation": "chong"}}
                    ]
                })
            # 天干丙辛全，地支辰戌巳亥见
            if "天干丙辛全" in cond2 and "地支辰戌巳亥见" in cond2:
                conds.append({"stems_count": {"names": ["丙"], "min": 1}})
                conds.append({"stems_count": {"names": ["辛"], "min": 1}})
                conds.append({"branches_count": {"names": ["辰", "戌", "巳", "亥"], "min": 1}})
            
            # 特定天干地支组合（如"壬、癸、亥、子、丑、寅、申"）
            if "壬、癸、亥、子、丑、寅、申" in cond2:
                count = 3  # 默认3个以上
                if qty and "三个以上" in qty:
                    count = 3
                return ParseResult(True, conditions={
                    "stems_branches_count": {
                        "names": ["壬", "癸", "亥", "子", "丑", "寅", "申"],
                        "min": count
                    }
                })
            
            if conds:
                return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        # 天干，四柱：四柱中天干同时有甲，乙
        if "天干" in cond1 and "四柱" in cond1:
            if "天干同时有" in cond2:
                stems = [s for s in STEMS if s in cond2]
                if stems:
                    conds = [{"stems_count": {"names": [s], "min": 1}} for s in stems]
                    return ParseResult(True, conditions=conds)
        
        # 神煞，四柱：日柱和时柱有神煞华盖
        if "神煞" in cond1 and "四柱" in cond1:
            if "日柱和时柱有神煞" in cond2:
                shensha = cond2.replace("日柱和时柱有神煞", "").strip()
                return ParseResult(True, conditions={
                    "all": [
                        {"deities_in_day": shensha},
                        {"deities_in_hour": shensha}
                    ]
                })
        
        # 四柱，神煞：年柱和日柱互为空亡
        if "四柱" in cond1 and "神煞" in cond1:
            if "互为空亡" in cond2:
                return ParseResult(True, conditions={"mutual_kongwang": ["year", "day"]})
        
        # 地支，十神：子午卯酉四柱见三个，再有一个偏印
        if "地支" in cond1 and "十神" in cond1:
            if "子午卯酉" in cond2:
                match = re.search(r"见([三四])个", cond2)
                count = 3 if match and match.group(1) == "三" else 4
                conds = [{"branches_count": {"names": ["子", "午", "卯", "酉"], "min": count}}]
                for god in TEN_GODS:
                    if god in cond2:
                        conds.append({"ten_gods_total": {"names": [god], "min": 1}})
                        break
                return ParseResult(True, conditions=conds)
        
        # 十神，神煞相关
        if "十神" in cond1 and "神煞" in cond1:
            # 天干主星没有食神和伤官，地支神煞出现空亡
            if "天干主星没有" in cond2:
                conds.append({"ten_gods_main": {"names": ["食神", "伤官"], "eq": 0}})
            if "出现空亡" in cond2:
                conds.append({"deities_in_any_pillar": "空亡"})
            if conds:
                return ParseResult(True, conditions=conds)
        
        # 自坐，十二长生：日柱的十二长生自坐是墓库
        if "自坐" in cond1:
            if "墓库" in cond2:
                return ParseResult(True, conditions={"star_fortune_in_day": "墓"})
        
        # 十神命格相关
        if "十神命格" in cond1:
            for god in TEN_GODS:
                if god == cond2:
                    return ParseResult(True, conditions={"shishen_ming_ge": god})
        
        # ========== 新增：十神，喜忌 ==========
        if "十神" in cond1 and "喜忌" in cond1:
            # 解析十神部分
            ten_god_cond = None
            for god in TEN_GODS:
                if god in cond2:
                    # 检查是否有柱位信息
                    if "年" in cond2:
                        ten_god_cond = {"main_star_in_year": god}
                    elif "月" in cond2:
                        ten_god_cond = {"main_star_in_pillar": {"pillar": "month", "eq": god}}
                    elif "日" in cond2:
                        ten_god_cond = {"main_star_in_day": god}
                    elif "时" in cond2:
                        ten_god_cond = {"main_star_in_pillar": {"pillar": "hour", "eq": god}}
                    else:
                        # 默认检查四柱主星
                        ten_god_cond = {"ten_gods_main": {"names": [god], "min": 1}}
                    break
            
            # 解析喜忌部分
            xiji_cond = None
            if "喜用" in cond2 or "为喜用" in cond2 or "且是喜用" in cond2:
                for god in TEN_GODS:
                    if god in cond2:
                        xiji_cond = {"xishen": god}
                        break
            elif "忌神" in cond2 or "为忌" in cond2 or "为忌神" in cond2 or "且是忌神" in cond2:
                for god in TEN_GODS:
                    if god in cond2:
                        xiji_cond = {"jishen": god}
                        break
            
            if ten_god_cond and xiji_cond:
                return ParseResult(True, conditions={"all": [ten_god_cond, xiji_cond]})
            elif ten_god_cond:
                return ParseResult(True, conditions=ten_god_cond)
            elif xiji_cond:
                return ParseResult(True, conditions=xiji_cond)
        
        # ========== 新增：十神，神煞 ==========
        if "十神" in cond1 and "神煞" in cond1:
            ten_god_cond = None
            shensha_cond = None
            
            # 解析十神
            for god in TEN_GODS:
                if god in cond2:
                    if "年" in cond2:
                        ten_god_cond = {"main_star_in_year": god}
                    elif "月" in cond2:
                        ten_god_cond = {"main_star_in_pillar": {"pillar": "month", "eq": god}}
                    elif "日" in cond2:
                        ten_god_cond = {"main_star_in_day": god}
                    elif "时" in cond2:
                        ten_god_cond = {"main_star_in_pillar": {"pillar": "hour", "eq": god}}
                    break
            
            # 解析神煞
            if "空亡" in cond2:
                shensha_cond = {"deities_in_any_pillar": "空亡"}
            elif "华盖" in cond2:
                shensha_cond = {"deities_in_any_pillar": "华盖"}
            elif "天乙贵人" in cond2:
                shensha_cond = {"deities_in_any_pillar": "天乙贵人"}
            elif "驿马" in cond2:
                shensha_cond = {"deities_in_any_pillar": "驿马"}
            
            if ten_god_cond and shensha_cond:
                return ParseResult(True, conditions={"all": [ten_god_cond, shensha_cond]})
            elif ten_god_cond:
                return ParseResult(True, conditions=ten_god_cond)
            elif shensha_cond:
                return ParseResult(True, conditions=shensha_cond)
        
        # ========== 新增：十神，旺衰 ==========
        if "十神" in cond1 and "旺衰" in cond1:
            ten_god_cond = None
            wangshuai_cond = None
            
            # 解析十神
            for god in TEN_GODS:
                if god in cond2:
                    if "年" in cond2:
                        ten_god_cond = {"main_star_in_year": god}
                    elif "月" in cond2:
                        ten_god_cond = {"main_star_in_pillar": {"pillar": "month", "eq": god}}
                    elif "日" in cond2:
                        ten_god_cond = {"main_star_in_day": god}
                    elif "时" in cond2:
                        ten_god_cond = {"main_star_in_pillar": {"pillar": "hour", "eq": god}}
                    break
            
            # 解析旺衰
            if "身强" in cond2 or "身旺" in cond2:
                wangshuai_cond = {"wangshuai": ["身旺"]}
            elif "身弱" in cond2:
                wangshuai_cond = {"wangshuai": ["身弱"]}
            elif "极旺" in cond2 or "太旺" in cond2:
                wangshuai_cond = {"wangshuai": ["极旺"]}
            
            if ten_god_cond and wangshuai_cond:
                return ParseResult(True, conditions={"all": [ten_god_cond, wangshuai_cond]})
            elif ten_god_cond:
                return ParseResult(True, conditions=ten_god_cond)
            elif wangshuai_cond:
                return ParseResult(True, conditions=wangshuai_cond)
        
        # ========== 新增：十神，十二地支 ==========
        if "十神" in cond1 and "十二地支" in cond1:
            # 解析十神和地支的组合条件
            ten_god_cond = None
            branch_cond = None
            
            for god in TEN_GODS:
                if god in cond2:
                    ten_god_cond = {"ten_gods_total": {"names": [god], "min": 1}}
                    break
            
            # 解析地支
            for branch in BRANCHES:
                if branch in cond2:
                    branch_cond = {"branches_count": {"names": [branch], "min": 1}}
                    break
            
            if ten_god_cond and branch_cond:
                return ParseResult(True, conditions={"all": [ten_god_cond, branch_cond]})
            elif ten_god_cond:
                return ParseResult(True, conditions=ten_god_cond)
            elif branch_cond:
                return ParseResult(True, conditions=branch_cond)
        
        # ========== 新增：十神，十二长生 ==========
        if "十神" in cond1 and "十二长生" in cond1:
            ten_god_cond = None
            changsheng_cond = None
            
            for god in TEN_GODS:
                if god in cond2:
                    ten_god_cond = {"ten_gods_total": {"names": [god], "min": 1}}
                    break
            
            # 解析十二长生
            changsheng_list = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]
            for cs in changsheng_list:
                if cs in cond2:
                    if "日" in cond2:
                        changsheng_cond = {"star_fortune_in_day": cs}
                    elif "时" in cond2:
                        changsheng_cond = {"star_fortune_in_hour": cs}
                    elif "年" in cond2:
                        changsheng_cond = {"star_fortune_in_year": cs}
                    break
            
            if ten_god_cond and changsheng_cond:
                return ParseResult(True, conditions={"all": [ten_god_cond, changsheng_cond]})
            elif ten_god_cond:
                return ParseResult(True, conditions=ten_god_cond)
            elif changsheng_cond:
                return ParseResult(True, conditions=changsheng_cond)
        
        # ========== 新增：十神，流年 ==========
        if "十神" in cond1 and "流年" in cond1:
            # 流年条件需要特殊处理，暂时标记为待确认
            pass
        
        # ========== 新增：十神，副星 ==========
        if "十神" in cond1 and "副星" in cond1:
            for god in TEN_GODS:
                if god in cond2:
                    if "年" in cond2:
                        return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year"], "min": 1}})
                    elif "月" in cond2:
                        return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["month"], "min": 1}})
                    elif "日" in cond2:
                        return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["day"], "min": 1}})
                    elif "时" in cond2:
                        return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["hour"], "min": 1}})
                    else:
                        return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year", "month", "day", "hour"], "min": 1}})
        
        # ========== 新增：藏干副星，十神 ==========
        if "藏干副星" in cond1 and "十神" in cond1:
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={"ten_gods_sub": {"names": [god], "pillars": ["year", "month", "day", "hour"], "min": 1}})
        
        # ========== 新增：旺衰，十神，喜忌 ==========
        if "旺衰" in cond1 and "十神" in cond1 and "喜忌" in cond1:
            conds = []
            
            # 解析旺衰
            if "身强" in cond2 or "身旺" in cond2:
                conds.append({"wangshuai": ["身旺"]})
            elif "身弱" in cond2:
                conds.append({"wangshuai": ["身弱"]})
            
            # 解析十神
            for god in TEN_GODS:
                if god in cond2:
                    if "年" in cond2:
                        conds.append({"main_star_in_year": god})
                    elif "月" in cond2:
                        conds.append({"main_star_in_pillar": {"pillar": "month", "eq": god}})
                    elif "日" in cond2:
                        conds.append({"main_star_in_day": god})
                    elif "时" in cond2:
                        conds.append({"main_star_in_pillar": {"pillar": "hour", "eq": god}})
                    break
            
            # 解析喜忌
            if "喜用" in cond2 or "为喜用" in cond2:
                for god in TEN_GODS:
                    if god in cond2:
                        conds.append({"xishen": god})
                        break
            elif "忌神" in cond2 or "为忌" in cond2:
                for god in TEN_GODS:
                    if god in cond2:
                        conds.append({"jishen": god})
                        break
            
            if conds:
                return ParseResult(True, conditions={"all": conds})
        
        return ParseResult(False, reason=f"复合条件需人工确认: {cond1}")
    
    @staticmethod
    def _pillar_to_key(pillar_name: str) -> str:
        """柱名转key"""
        mapping = {
            "年柱": "year",
            "月柱": "month", 
            "日柱": "day",
            "时柱": "hour",
        }
        return mapping.get(pillar_name, pillar_name)


def load_excel_rules(xlsx_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """加载Excel规则"""
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"文件不存在: {xlsx_path}")
    
    rules_by_sheet = {}
    xls = pd.ExcelFile(xlsx_path)
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        rows = df.to_dict("records")
        rules_by_sheet[sheet_name] = rows
    
    return rules_by_sheet


def import_rules(
    xlsx_path: str,
    write_db: bool = True,
    append: bool = True,
) -> Tuple[List[RuleRecord], List[Dict[str, Any]], int, int]:
    """导入规则
    
    Returns:
        (parsed_rules, skipped_rules_details, inserted_count, updated_count)
        skipped_rules_details: 包含完整规则信息的字典列表
    """
    
    # 加载规则
    rules_by_sheet = load_excel_rules(xlsx_path)
    
    parsed_rules: List[RuleRecord] = []
    skipped_rules: List[Dict[str, Any]] = []
    
    for sheet_name, rows in rules_by_sheet.items():
        rule_type = RULE_TYPE_MAP.get(sheet_name, sheet_name.lower())
        
        for row in rows:
            rule_id = int(row.get("ID", 0))
            if not rule_id:
                continue
            
            # 解析规则
            result = RuleParser.parse(row, sheet_name)
            
            if not result.success:
                # 保存完整的规则信息
                skipped_rules.append({
                    "ID": rule_id,
                    "类型": sheet_name,
                    "性别": str(row.get("性别", "无论男女")),
                    "筛选条件1": str(row.get("筛选条件1", "")),
                    "筛选条件2": str(row.get("筛选条件2", "")),
                    "数量": str(row.get("数量", "")) if pd.notna(row.get("数量")) else "",
                    "结果": str(row.get("结果", "")),
                    "解析失败原因": result.reason or "解析失败",
                    "rule_code": f"FORMULA_{sheet_name.upper()}_{rule_id}"
                })
                continue
            
            # 构建规则记录
            rule_code = f"FORMULA_{sheet_name.upper()}_{rule_id}"
            rule_record = RuleRecord(
                rule_id=rule_id,
                rule_code=rule_code,
                rule_name=f"{sheet_name}规则-{rule_id}",
                rule_type=f"formula_{rule_type}",
                rule_category=sheet_name.lower(),
                priority=100,
                conditions=result.conditions,
                content={
                    "type": "text",
                    "text": str(row.get("结果", "")).strip()
                },
                description=json.dumps({
                    "筛选条件1": str(row.get("筛选条件1", "")),
                    "筛选条件2": str(row.get("筛选条件2", "")),
                    "性别": str(row.get("性别", "无论男女")),
                    "数量": str(row.get("数量", "")) if pd.notna(row.get("数量")) else "",
                }, ensure_ascii=False),
                source=sheet_name
            )
            parsed_rules.append(rule_record)
    
    # 写入数据库
    inserted_count = 0
    updated_count = 0
    
    if write_db and parsed_rules:
        from server.config.mysql_config import get_mysql_connection
        
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cur:
                # 获取已存在的规则
                existing_codes = set()
                if append:
                    cur.execute("SELECT rule_code FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%'")
                    existing_codes = {item["rule_code"] for item in cur.fetchall()}
                
                insert_sql = """
                    INSERT INTO bazi_rules 
                    (rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                update_sql = """
                    UPDATE bazi_rules
                    SET rule_name = %s, rule_type = %s, rule_category = %s, priority = %s,
                        conditions = %s, content = %s, description = %s, enabled = %s
                    WHERE rule_code = %s
                """
                
                for rule in parsed_rules:
                    if rule.rule_code in existing_codes:
                        # 更新
                        cur.execute(update_sql, (
                            rule.rule_name,
                            rule.rule_type,
                            rule.rule_category,
                            rule.priority,
                            json.dumps(rule.conditions, ensure_ascii=False),
                            json.dumps(rule.content, ensure_ascii=False),
                            rule.description,
                            True,
                            rule.rule_code
                        ))
                        updated_count += 1
                    else:
                        # 插入
                        cur.execute(insert_sql, (
                            rule.rule_code,
                            rule.rule_name,
                            rule.rule_type,
                            rule.rule_category,
                            rule.priority,
                            json.dumps(rule.conditions, ensure_ascii=False),
                            json.dumps(rule.content, ensure_ascii=False),
                            rule.description,
                            True
                        ))
                        inserted_count += 1
                        existing_codes.add(rule.rule_code)
                
                # 更新版本号
                cur.execute("UPDATE rule_version SET rule_version = rule_version + 1, content_version = content_version + 1")
                conn.commit()
                
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    return parsed_rules, skipped_rules, inserted_count, updated_count


def main():
    parser = argparse.ArgumentParser(description="导入 2025.12.03算法公式.xlsx 规则到数据库")
    parser.add_argument("--dry-run", action="store_true", help="仅解析并打印结果，不写入数据库")
    parser.add_argument("--xlsx", default=XLSX_FILE, help="Excel文件路径")
    args = parser.parse_args()
    
    print("=" * 60)
    print("导入 2025.12.03算法公式.xlsx 规则")
    print("=" * 60)
    
    try:
        parsed, skipped, inserted, updated = import_rules(
            xlsx_path=args.xlsx,
            write_db=not args.dry_run,
        )
        
        print(f"\n✅ 解析完成:")
        print(f"  - 成功解析: {len(parsed)} 条")
        print(f"  - 跳过/待确认: {len(skipped)} 条")
        
        if not args.dry_run:
            print(f"\n📦 数据库操作:")
            print(f"  - 新增: {inserted} 条")
            print(f"  - 更新: {updated} 条")
        
        if skipped:
            print(f"\n⚠️ 需确认的规则 ({len(skipped)} 条):")
            for item in skipped[:20]:  # 只显示前20条
                print(f"  - [{item.get('类型', '未知')}] ID {item.get('ID', '未知')}: {item.get('解析失败原因', '未知')}")
            if len(skipped) > 20:
                print(f"  ... 还有 {len(skipped) - 20} 条")
            
            # 保存未解析规则到JSON文件
            import json
            output_file = os.path.join(PROJECT_ROOT, "docs", "未解析规则_2025_12_03.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "统计": {
                        "总规则数": len(parsed) + len(skipped),
                        "成功解析": len(parsed),
                        "未解析": len(skipped),
                        "解析率": f"{len(parsed) / (len(parsed) + len(skipped)) * 100:.1f}%"
                    },
                    "未解析规则": skipped
                }, f, ensure_ascii=False, indent=2)
            print(f"\n📄 未解析规则详情已保存到: {output_file}")
        
        if args.dry_run and parsed:
            print(f"\n📋 示例规则预览 (前3条):")
            for rule in parsed[:3]:
                print(f"\n  rule_code: {rule.rule_code}")
                print(f"  conditions: {json.dumps(rule.conditions, ensure_ascii=False, indent=4)}")
                print(f"  content: {rule.content['text'][:100]}...")
                
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


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
        
        # 神煞十神条件（新增支持）
        if cond1 == "神煞十神":
            # 先尝试解析为十神条件
            result = cls._parse_ten_gods(cond2)
            if result.success:
                return result
            # 如果失败，尝试解析为复合条件
            return cls._parse_composite(cond1, cond2, qty)
        
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
        
        # ========== 新增：五行条件类型 ==========
        if cond1 == "五行":
            return cls._parse_wuxing(cond2)
        
        # ========== 新增：纳音条件类型 ==========
        if cond1 == "纳音":
            return cls._parse_nayin(cond2)
        
        # ========== 新增：天干条件类型 ==========
        if cond1 == "天干":
            return cls._parse_stem(cond2)
        
        # ========== 新增：日干条件类型 ==========
        if cond1 == "日干":
            return cls._parse_rigan(cond2)
        
        # ========== 新增：月令条件类型 ==========
        if cond1 == "月令":
            return cls._parse_yueling(cond2)
        
        # 复合条件类型（用逗号分隔）
        if "，" in cond1 or "," in cond1:
            return cls._parse_composite(cond1, cond2, qty)
        
        return ParseResult(False, reason=f"未支持的条件类型: {cond1}")
    
    @classmethod
    def _parse_shensha(cls, cond2: str) -> ParseResult:
        """解析神煞条件"""
        conds = []
        
        # "华盖数量3个及以上" - 神煞数量
        if "华盖数量" in cond2:
            count_match = re.search(r"华盖数量(\d+)个及以上", cond2)
            if count_match:
                count = int(count_match.group(1))
                return ParseResult(True, conditions={
                    "deities_count": {"name": "华盖", "min": count}
                })
        
        # "正印生沐浴" - 神煞特殊条件
        if "正印生沐浴" in cond2:
            return ParseResult(True, conditions={
                "all": [
                    {"ten_gods_total": {"names": ["正印"], "min": 1}},
                    {"deities_in_any_pillar": "沐浴"}
                ]
            })
        
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
        
        # ========== 新增：四柱神煞中有XXX（无"有"字） ==========
        if "四柱神煞中有" in cond2:
            shensha = cond2.replace("四柱神煞中有", "").strip()
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
        
        # ========== 新增：多个日柱选择（"XX、YY、ZZ其中之一"） ==========
        if "其中之一" in clean_cond:
            # 提取所有干支
            ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
            ganzhi_list = re.findall(ganzhi_pattern, clean_cond)
            if ganzhi_list:
                # 检查是否有附加条件（"并且"、"且"等）
                if "并且" in clean_cond or "且" in clean_cond:
                    # 有附加条件，需要组合处理
                    conds = [{
                        "pillar_equals": {"pillar": "day", "values": ganzhi_list}
                    }]
                    
                    # 解析副星条件（"副星有..."）
                    if "副星有" in clean_cond or "副星" in clean_cond:
                        # 提取十神名称
                        ten_gods_found = [tg for tg in TEN_GODS if tg in clean_cond]
                        if ten_gods_found:
                            # 检查是否有数量要求（"这4个"）
                            count_match = re.search(r'这(\d+)个', clean_cond)
                            if count_match:
                                required_count = int(count_match.group(1))
                                conds.append({
                                    "ten_gods_sub": {
                                        "names": ten_gods_found,
                                        "pillars": ["day"],
                                        "min": required_count
                                    }
                                })
                            else:
                                conds.append({
                                    "ten_gods_sub": {
                                        "names": ten_gods_found,
                                        "pillars": ["day"],
                                        "min": len(ten_gods_found)
                                    }
                                })
                    
                    # 解析神煞条件（"自坐禄神"）
                    if "自坐禄神" in clean_cond or "禄神" in clean_cond:
                        conds.append({"deities_in_day": "禄神"})
                    
                    if len(conds) > 1:
                        return ParseResult(True, conditions={"all": conds})
                    else:
                        return ParseResult(True, conditions=conds[0])
                else:
                    # 没有附加条件，直接返回多个日柱选择
                    return ParseResult(True, conditions={
                        "pillar_equals": {"pillar": "day", "values": ganzhi_list}
                    })
        
        # ========== 新增：特定日柱配合特定时柱 ==========
        if "特定日柱" in clean_cond and ("特定时柱" in clean_cond or "时柱" in clean_cond):
            # 提取日柱和时柱（从括号中，如"如乙丑、己巳"等）
            day_pillar_match = re.search(r'如([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])', clean_cond)
            if day_pillar_match:
                day_pillar = day_pillar_match.group(1)
                # 尝试提取多个日柱（如果有"等"）
                if "等" in clean_cond:
                    # 提取所有日柱
                    ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
                    day_pillars = re.findall(ganzhi_pattern, clean_cond.split("特定时柱")[0])
                    if not day_pillars:
                        day_pillars = [day_pillar]
                else:
                    day_pillars = [day_pillar]
                
                # 提取时柱（如果有具体时柱）
                hour_pillar_match = re.search(r'时柱[是]?([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])', clean_cond)
                if hour_pillar_match:
                    hour_pillar = hour_pillar_match.group(1)
                    return ParseResult(True, conditions={
                        "all": [
                            {"pillar_equals": {"pillar": "day", "values": day_pillars}},
                            {"pillar_equals": {"pillar": "hour", "values": [hour_pillar]}}
                        ]
                    })
                else:
                    # 没有具体时柱，只返回日柱条件（标记为需要时柱匹配）
                    return ParseResult(True, conditions={
                        "pillar_equals": {"pillar": "day", "values": day_pillars}
                    })
        
        # ========== 新增：特定日柱配合特定格局/神煞 ==========
        if "特定日柱" in clean_cond and ("格局" in clean_cond or "天医星" in clean_cond or "龙德贵人" in clean_cond):
            # 提取日柱
            ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
            day_pillars = re.findall(ganzhi_pattern, clean_cond.split("特定日柱")[1].split("配合")[0])
            
            conds = []
            if day_pillars:
                conds.append({"pillar_equals": {"pillar": "day", "values": day_pillars}})
            
            # 提取神煞
            if "天医星" in clean_cond:
                conds.append({"deities_in_any_pillar": "天医"})
            elif "龙德贵人" in clean_cond:
                conds.append({"deities_in_any_pillar": "龙德"})
            
            if len(conds) > 1:
                return ParseResult(True, conditions={"all": conds})
            elif conds:
                return ParseResult(True, conditions=conds[0])
        
        # ========== 新增：日柱配合神煞 ==========
        if "日柱配合" in clean_cond:
            # 提取神煞名称
            shensha_match = re.search(r'日柱配合(.+?)(?:，|$)', clean_cond)
            if shensha_match:
                shensha = shensha_match.group(1).strip()
                return ParseResult(True, conditions={
                    "deities_in_day": shensha
                })
        
        # ========== 新增：日柱 + 其他柱条件（"XX其中之一，年柱、月柱或时柱是YY"） ==========
        other_pillar_match = re.search(r'(年柱|月柱|时柱)[，,]?或(年柱|月柱|时柱)是([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])', clean_cond)
        if other_pillar_match and "其中之一" in clean_cond:
            # 先提取日柱列表
            ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
            day_pillars = re.findall(ganzhi_pattern, clean_cond.split("其中之一")[0])
            
            pillar_name = other_pillar_match.group(1)
            target_pillar = other_pillar_match.group(3)
            pillar_key = cls._pillar_to_key(pillar_name)
            
            conds = [{"pillar_equals": {"pillar": "day", "values": day_pillars}}]
            conds.append({
                "any": [
                    {"pillar_equals": {"pillar": "year", "values": [target_pillar]}},
                    {"pillar_equals": {"pillar": "month", "values": [target_pillar]}},
                    {"pillar_equals": {"pillar": "hour", "values": [target_pillar]}}
                ]
            })
            return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：日柱 + 地支条件（"XX其中之一，地支中有Y"） ==========
        if "其中之一" in clean_cond and "地支中有" in clean_cond:
            # 提取日柱列表
            ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
            day_pillars = re.findall(ganzhi_pattern, clean_cond.split("其中之一")[0])
            
            # 提取地支
            branch_match = re.search(r'地支中有([子丑寅卯辰巳午未申酉戌亥])', clean_cond)
            if day_pillars and branch_match:
                branch = branch_match.group(1)
                return ParseResult(True, conditions={
                    "all": [
                        {"pillar_equals": {"pillar": "day", "values": day_pillars}},
                        {"branches_count": {"names": [branch], "min": 1}}
                    ]
                })
        
        # ========== 新增：日柱神煞条件（"日柱神煞有XX"） ==========
        day_shensha_match = re.match(r'日柱神煞有(.+)', clean_cond)
        if day_shensha_match:
            shensha = day_shensha_match.group(1).strip()
            return ParseResult(True, conditions={"deities_in_day": shensha})
        
        # ========== 新增：大运流年触发的格局（先解析基础条件） ==========
        # "（甲子日主，年月时至少再有一个子，遇到大运流年巳火时，被触发成格）"
        if "日主" in clean_cond and "遇到大运流年" in clean_cond:
            # 提取日柱（如"甲子日主"）
            day_pillar_match = re.search(r'([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])日主', clean_cond)
            if day_pillar_match:
                day_pillar = day_pillar_match.group(1)
                conds = [{"pillar_equals": {"pillar": "day", "values": [day_pillar]}}]
                
                # 提取地支条件（"年月时至少再有一个子"）
                branch_match = re.search(r'至少再有一个([子丑寅卯辰巳午未申酉戌亥])', clean_cond)
                if branch_match:
                    branch = branch_match.group(1)
                    conds.append({
                        "all": [
                            {"branches_count": {"names": [branch], "min": 2}}  # 至少2个（日柱1个+其他柱至少1个）
                        ]
                    })
                
                # 标记需要大运流年触发（需要在规则引擎中支持）
                # 这里先返回基础条件，大运流年部分需要在规则引擎中实现
                if len(conds) > 1:
                    return ParseResult(True, conditions={"all": conds})
                else:
                    return ParseResult(True, conditions=conds[0])
        
        # ========== 新增：遥合格局（先解析基础条件） ==========
        # "辛丑、癸丑日通过丑土遥合巳中丙火（日主必须是辛丑日或者癸丑日，年月时的地支中必须至少再有一个丑土，等到大运流年遇到巳申时，被触发成格）"
        if "遥合" in clean_cond and "日主必须是" in clean_cond:
            # 提取日柱列表（从"日主必须是XX日或者XX日"）
            ganzhi_pattern = r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]'
            day_pillars = re.findall(ganzhi_pattern, clean_cond.split("日主必须是")[1].split("，")[0])
            
            if day_pillars:
                conds = [{"pillar_equals": {"pillar": "day", "values": day_pillars}}]
                
                # 提取地支条件（"年月时的地支中必须至少再有一个丑土"）
                branch_match = re.search(r'至少再有一个([子丑寅卯辰巳午未申酉戌亥])', clean_cond)
                if not branch_match:
                    branch_match = re.search(r'再有一个([子丑寅卯辰巳午未申酉戌亥])', clean_cond)
                if branch_match:
                    branch = branch_match.group(1)
                    conds.append({
                        "branches_count": {"names": [branch], "min": 2}  # 至少2个
                    })
                
                # 标记需要大运流年触发（需要在规则引擎中支持）
                if len(conds) > 1:
                    return ParseResult(True, conditions={"all": conds})
                else:
                    return ParseResult(True, conditions=conds[0])
        
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
        
        # ========== 新增：柱间关系条件解析（增强） ==========
        # "年柱与月柱天干克地支冲" - 天干相克且地支相冲
        pillar_ke_chong_match = re.search(r"(年柱|月柱|日柱|时柱)与(年柱|月柱|日柱|时柱)天干克地支冲", cond2)
        if pillar_ke_chong_match:
            pillar_a_name = pillar_ke_chong_match.group(1)
            pillar_b_name = pillar_ke_chong_match.group(2)
            pillar_a = cls._pillar_to_key(pillar_a_name)
            pillar_b = cls._pillar_to_key(pillar_b_name)
            return ParseResult(True, conditions={
                "all": [
                    {"pillar_relation": {"pillar_a": pillar_a, "pillar_b": pillar_b, "relation": "ke", "part": "stem"}},
                    {"pillar_relation": {"pillar_a": pillar_a, "pillar_b": pillar_b, "relation": "chong", "part": "branch"}}
                ]
            })
        
        # "四柱地支中有辰巳戌亥" - 地支组合条件
        if "四柱地支中有" in cond2:
            branches = [b for b in BRANCHES if b in cond2]
            if branches:
                return ParseResult(True, conditions={
                    "branches_count": {"names": branches, "min": len(branches)}
                })
        
        # "四柱中有寅，申，巳，亥" - 地支组合条件
        if "四柱中有" in cond2 and any(b in cond2 for b in ["寅", "申", "巳", "亥"]):
            branches = [b for b in ["寅", "申", "巳", "亥"] if b in cond2]
            if branches:
                return ParseResult(True, conditions={
                    "branches_count": {"names": branches, "min": 1}}
                )
        
        # "年月地支冲日时地支" - 年冲日或月冲时
        if "年月地支冲日时地支" in cond2:
            return ParseResult(True, conditions={
                "any": [
                    {"pillar_relation": {"pillar_a": "year", "pillar_b": "day", "relation": "chong", "part": "branch"}},
                    {"pillar_relation": {"pillar_a": "month", "pillar_b": "hour", "relation": "chong", "part": "branch"}}
                ]
            })
        
        # "年柱与月柱天干克地支冲，或日柱与时柱天干克地支冲，或月柱与日柱天干克地支冲"
        if "天干克地支冲" in cond2 and ("或" in cond2 or "，或" in cond2):
            # 解析多个"或"条件
            parts = re.split(r"[，,]或|或", cond2)
            any_conds = []
            for part in parts:
                part_match = re.search(r"(年柱|月柱|日柱|时柱)与(年柱|月柱|日柱|时柱)天干克地支冲", part)
                if part_match:
                    pillar_a_name = part_match.group(1)
                    pillar_b_name = part_match.group(2)
                    pillar_a = cls._pillar_to_key(pillar_a_name)
                    pillar_b = cls._pillar_to_key(pillar_b_name)
                    any_conds.append({
                        "all": [
                            {"pillar_relation": {"pillar_a": pillar_a, "pillar_b": pillar_b, "relation": "ke", "part": "stem"}},
                            {"pillar_relation": {"pillar_a": pillar_a, "pillar_b": pillar_b, "relation": "chong", "part": "branch"}}
                        ]
                    })
            if any_conds:
                return ParseResult(True, conditions={"any": any_conds})
        
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
        
        # ========== 新增：十神数量比较条件（增强） ==========
        # "四柱中正财数量多于偏财者" - 需要比较两个十神的数量
        more_than_match = re.search(r"(.+?)(?:数量|的数量)(?:多于|大于)(.+?)(?:者|，|$)", cond2)
        if more_than_match:
            god1 = more_than_match.group(1).strip()
            god2 = more_than_match.group(2).strip().rstrip("者").rstrip("，")
            # 清理可能的"四柱中"、"十神"等前缀
            god1 = re.sub(r"^(四柱中|十神|四柱)", "", god1).strip()
            god2 = re.sub(r"^(四柱中|十神|四柱)", "", god2).strip()
            if god1 in TEN_GODS and god2 in TEN_GODS:
                # 使用ten_gods_compare条件（需要在规则引擎中实现）
                return ParseResult(True, conditions={
                    "ten_gods_compare": {"god_a": god1, "god_b": god2, "relation": "more_than"}
                })
        
        # ========== 新增：多十神总数量限制（高优先级） ==========
        # "四柱中正官，七杀，正印，偏印数量少于3个" - 多个十神总数量限制
        multi_gods_less_match = re.search(r"(?:四柱中|四柱中十神)([\u4e00-\u9fa5，,、]+)(?:数量|的数量)(?:少于|少)(\d+)(?:个|三个)", cond2)
        if multi_gods_less_match:
            gods_text = multi_gods_less_match.group(1)
            count = int(multi_gods_less_match.group(2))
            # 提取十神名称
            gods = []
            for god in TEN_GODS:
                if god in gods_text:
                    gods.append(god)
            if len(gods) >= 2:  # 至少2个十神才使用总数量限制
                return ParseResult(True, conditions={
                    "ten_gods_total_group": {"names": gods, "max": count - 1}
                })
        
        # "X数量少于Y个" - 数量少于（单个十神）
        less_than_match = re.search(r"(.+?)(?:数量|的数量)少于(\d+)个", cond2)
        if less_than_match:
            god = less_than_match.group(1).strip()
            count = int(less_than_match.group(2))
            god = re.sub(r"^(四柱中|十神|四柱)", "", god).strip()
            if god in TEN_GODS:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": [god], "max": count - 1}
                })
        
        # "X比Y数量少" - 比较两个十神
        compare_less_match = re.search(r"(.+?)比(.+?)数量少", cond2)
        if compare_less_match:
            god1 = compare_less_match.group(1).strip()
            god2 = compare_less_match.group(2).strip()
            god1 = re.sub(r"^(四柱中|十神|四柱)", "", god1).strip()
            god2 = re.sub(r"^(四柱中|十神|四柱)", "", god2).strip()
            if god1 in TEN_GODS and god2 in TEN_GODS:
                return ParseResult(True, conditions={
                    "ten_gods_compare": {"god_a": god1, "god_b": god2, "relation": "less_than"}
                })
        
        # "四柱中X数量少于Y个" - 数量少于
        less_than_match = re.search(r"(.+)数量少于(\d+)个", cond2)
        if less_than_match:
            god = less_than_match.group(1).strip()
            count = int(less_than_match.group(2))
            if god in TEN_GODS:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": [god], "max": count - 1}
                })
        
        # "X数量为0" 或 "X数量为0-1"
        zero_match = re.search(r"(.+?)(?:数量|的数量)为0(?:-(\d+))?", cond2)
        if zero_match:
            god = zero_match.group(1).strip()
            max_count = int(zero_match.group(2)) if zero_match.group(2) else 0
            god = re.sub(r"^(四柱中|十神|四柱)", "", god).strip()
            if god in TEN_GODS:
                if max_count > 0:
                    return ParseResult(True, conditions={
                        "ten_gods_total": {"names": [god], "min": 0, "max": max_count}
                    })
                else:
                    return ParseResult(True, conditions={
                        "ten_gods_total": {"names": [god], "eq": 0}
                    })
        
        # "X或Y数量为0" - 多个十神数量为0
        zero_or_match = re.search(r"(.+?)或(.+?)数量为0", cond2)
        if zero_or_match:
            god1 = zero_or_match.group(1).strip()
            god2 = zero_or_match.group(2).strip()
            if god1 in TEN_GODS and god2 in TEN_GODS:
                return ParseResult(True, conditions={
                    "any": [
                        {"ten_gods_total": {"names": [god1], "eq": 0}},
                        {"ten_gods_total": {"names": [god2], "eq": 0}}
                    ]
                })
        
        # "十神X或Y数量为0" - 修复格式
        zero_or_ten_gods_match = re.search(r"十神(.+?)或(.+?)数量为0", cond2)
        if zero_or_ten_gods_match:
            god1 = zero_or_ten_gods_match.group(1).strip()
            god2 = zero_or_ten_gods_match.group(2).strip()
            if god1 in TEN_GODS and god2 in TEN_GODS:
                # 两个十神数量都为0
                return ParseResult(True, conditions={
                    "all": [
                        {"ten_gods_total": {"names": [god1], "eq": 0}},
                        {"ten_gods_total": {"names": [god2], "eq": 0}}
                    ]
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
        
        # ========== 新增：喜用神条件解析（增强） ==========
        # "日柱喜用神为X者" - 注意：这里可能是五行，需要检查
        xishen_pillar_match = re.search(r"(日柱|年柱|月柱|时柱)?喜用神(?:为|是)([木火土金水]|[\u4e00-\u9fa5]+)", cond2)
        if xishen_pillar_match:
            element_or_god = xishen_pillar_match.group(2).strip()
            # 如果是五行（木火土金水），需要转换为对应的十神或使用五行条件
            # 暂时先检查是否是十神
            if element_or_god in TEN_GODS:
                return ParseResult(True, conditions={"xishen": element_or_god})
            elif element_or_god in ["木", "火", "土", "金", "水"]:
                # 五行喜用神：需要检查八字中是否有该五行的十神
                # 五行到十神的映射（简化处理，实际需要根据日主判断）
                # 暂时使用element_total条件，表示该五行数量较多
                # 注意：这只是一个近似处理，真正的五行喜用神需要更复杂的逻辑
                return ParseResult(True, conditions={"element_total": {"names": [element_or_god], "min": 2}})
        
        # "喜用神为X" 或 "喜用神是X"
        xishen_simple_match = re.search(r"喜用神(?:为|是)([木火土金水]|[\u4e00-\u9fa5]+)", cond2)
        if xishen_simple_match:
            element_or_god = xishen_simple_match.group(1).strip()
            if element_or_god in TEN_GODS:
                return ParseResult(True, conditions={"xishen": element_or_god})
            elif element_or_god in ["木", "火", "土", "金", "水"]:
                return ParseResult(False, reason=f"五行喜用神暂不支持: {cond2}")
        
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
        
        # ========== 新增：旺相条件解析（在十神条件中） ==========
        # "且旺" 或 "并且旺相" - 在十神条件中出现的旺相判断
        if "且旺" in cond2 or "并且旺相" in cond2 or "旺相" in cond2:
            # 提取十神条件
            ten_god_conds = []
            for god in TEN_GODS:
                if god in cond2:
                    # 检查是否有数量条件
                    count_match = re.search(r"(\d+)个", cond2)
                    if count_match:
                        count = int(count_match.group(1))
                        ten_god_conds.append({"ten_gods_total": {"names": [god], "min": count}})
                    else:
                        ten_god_conds.append({"ten_gods_total": {"names": [god], "min": 1}})
            
            if ten_god_conds:
                # 组合十神条件和旺相条件
                wangshuai_cond = {"wangshuai": ["身旺", "极旺"]}
                if len(ten_god_conds) == 1:
                    return ParseResult(True, conditions={"all": [ten_god_conds[0], wangshuai_cond]})
                else:
                    return ParseResult(True, conditions={"all": ten_god_conds + [wangshuai_cond]})
        
        # "日主身旺"
        if "日主身旺" in cond2:
            # 提取十神条件
            for god in TEN_GODS:
                if god in cond2:
                    count_match = re.search(r"(\d+)个", cond2)
                    if count_match:
                        count = int(count_match.group(1))
                        return ParseResult(True, conditions={
                            "all": [
                                {"ten_gods_total": {"names": [god], "min": count}},
                                {"wangshuai": ["身旺"]}
                            ]
                        })
                    else:
                        return ParseResult(True, conditions={
                            "all": [
                                {"ten_gods_total": {"names": [god], "min": 1}},
                                {"wangshuai": ["身旺"]}
                            ]
                        })
        
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
        
        # ========== 新增：不被克判断 ==========
        # "且不被克" - 需要判断十神是否被其他十神克制
        if "且不被克" in cond2 or "不被克" in cond2:
            # 提取十神
            for god in TEN_GODS:
                if god in cond2:
                    # 移除"且不被克"部分，重新解析
                    clean_cond = cond2.replace("且不被克", "").replace("不被克", "").strip()
                    # 先解析其他条件
                    base_result = cls._parse_ten_gods(clean_cond)
                    if base_result.success:
                        # 添加不被克条件
                        if isinstance(base_result.conditions, dict):
                            base_result.conditions = {"all": [base_result.conditions, {"ten_gods_not_ke": god}]}
                        elif isinstance(base_result.conditions, list):
                            base_result.conditions.append({"ten_gods_not_ke": god})
                        return base_result
        
        # ========== 新增：同柱关系判断 ==========
        # "并且与寅申巳亥中任何一个字同柱" - 十神和地支同柱
        same_pillar_branch_match = re.search(r"与([子丑寅卯辰巳午未申酉戌亥、，,]+)中任何一个字同柱", cond2)
        if same_pillar_branch_match:
            branches_text = same_pillar_branch_match.group(1)
            branches = [b.strip() for b in re.split(r"[、，,]", branches_text) if b.strip() in BRANCHES]
            if branches:
                # 提取十神（支持"或"逻辑）
                gods = [g for g in TEN_GODS if g in cond2]
                if gods:
                    # 使用any组合：任一十神与任一地支同柱
                    return ParseResult(True, conditions={
                        "any": [
                            {"ten_gods_same_pillar_branch": {"ten_god": god, "branches": branches}}
                            for god in gods
                        ]
                    })
        
        # ========== 优化：同柱关系正则表达式（高优先级） ==========
        # "四柱出现X或者Y，并且与Z同柱" - 优化格式匹配，支持多种表达
        appear_and_same_patterns = [
            r"四柱出现(.+?)(?:或者|或)(.+?)，(?:并且|且)与([子丑寅卯辰巳午未申酉戌亥、，,]+)中任何一个字同柱",
            r"四柱出现(.+?)(?:或者|或)(.+?)，(?:并且|且)与([子丑寅卯辰巳午未申酉戌亥、，,]+)同柱",
            r"四柱出现(.+?)(?:或者|或)(.+?)，与([子丑寅卯辰巳午未申酉戌亥、，,]+)中任何一个字同柱",
        ]
        
        for pattern in appear_and_same_patterns:
            appear_and_same_match = re.search(pattern, cond2)
            if appear_and_same_match:
                god1 = appear_and_same_match.group(1).strip()
                god2 = appear_and_same_match.group(2).strip()
                branches_text = appear_and_same_match.group(3).strip()
                
                # 提取地支
                branches = [b.strip() for b in re.split(r"[、，,]", branches_text) if b.strip() in BRANCHES]
                
                # 提取十神（支持多个十神）
                gods = []
                for god in TEN_GODS:
                    if god in god1 or god in god2:
                        gods.append(god)
                
                if gods and branches:
                    # 使用any组合：任一十神与任一地支同柱
                    conds = []
                    for god in gods:
                        conds.append({"ten_gods_same_pillar_branch": {"ten_god": god, "branches": branches}})
                    return ParseResult(True, conditions={"any": conds})
        
        # "同一柱出现神煞X与Y" - 神煞同柱
        same_pillar_deity_match = re.search(r"同一柱出现神煞(.+?)与(.+)", cond2)
        if same_pillar_deity_match:
            deity1 = same_pillar_deity_match.group(1).strip()
            deity2 = same_pillar_deity_match.group(2).strip()
            # 提取十神
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={
                        "all": [
                            {"ten_gods_total": {"names": [god], "min": 1}},
                            {"deities_same_pillar": [deity1, deity2]}
                        ]
                    })
        
        # ========== 新增：连续出现判断 ==========
        # "四柱中连续出现X或Y" - 相邻柱连续出现
        consecutive_match = re.search(r"连续出现(.+?)或(.+?)(?:，|、|$)", cond2)
        if consecutive_match:
            ganzhi1 = consecutive_match.group(1).strip()
            ganzhi2 = consecutive_match.group(2).strip()
            # 提取干支（如"己亥"、"癸巳"）
            ganzhi_list = [g.strip() for g in re.split(r"[或、，,]", cond2.split("连续出现")[1].split("，")[0]) if len(g.strip()) == 2]
            if ganzhi_list:
                return ParseResult(True, conditions={
                    "pillars_consecutive": {"ganzhi_list": ganzhi_list}
                })
        
        # ========== 新增：占比计算 ==========
        # "数量占所有十神数量的三分之二以上" - 占比计算
        ratio_match = re.search(r"(.+?)数量占所有十神数量的(.+?)以上", cond2)
        if ratio_match:
            gods_text = ratio_match.group(1)
            ratio_text = ratio_match.group(2)
            # 提取十神（支持多个，用逗号分隔）
            gods = []
            for god in TEN_GODS:
                if god in gods_text:
                    gods.append(god)
            # 解析比例（三分之二 = 2/3）
            if "三分之二" in ratio_text or "2/3" in ratio_text:
                ratio = 2/3
            elif "一半" in ratio_text or "1/2" in ratio_text or "50%" in ratio_text:
                ratio = 0.5
            else:
                ratio = 0.5  # 默认
            
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_ratio": {"names": gods, "min_ratio": ratio}
                })
        
        # "数量占比十神总数的一半以上" - 修复格式
        ratio_half_match = re.search(r"(.+?)数量占比十神总数的一半以上", cond2)
        if ratio_half_match:
            gods_text = ratio_half_match.group(1)
            gods = [g for g in TEN_GODS if g in gods_text]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_ratio": {"names": gods, "min_ratio": 0.5}
                })
        
        # ========== 新增：命格判断 ==========
        # "伤官格" - 命格类型判断
        mingge_match = re.search(r"(.+?)格", cond2)
        if mingge_match:
            mingge_type = mingge_match.group(1).strip()
            if mingge_type in TEN_GODS:
                return ParseResult(True, conditions={
                    "mingge_type": mingge_type
                })
        
        # ========== 新增：五行相生关系 ==========
        # "十神X的五行与地支中的Y形成生的关系" - 五行相生
        element_sheng_match = re.search(r"(.+?)的五行与地支中的(.+?)形成生的关系", cond2)
        if element_sheng_match:
            god_text = element_sheng_match.group(1).strip()
            branches_text = element_sheng_match.group(2)
            branches = [b.strip() for b in re.split(r"[、，,]", branches_text) if b.strip() in BRANCHES]
            # 提取十神（支持多个，用逗号分隔）
            gods = [g for g in TEN_GODS if g in god_text]
            if gods and branches:
                # 使用any组合：任一十神与任一地支形成相生关系
                return ParseResult(True, conditions={
                    "any": [
                        {"ten_gods_element_sheng": {"ten_god": god, "branches": branches}}
                        for god in gods
                    ]
                })
        
        # ========== 新增：天干地支混合条件 ==========
        # "四柱中八字出现X，Y，Z，没有出现W" - 天干地支混合
        if "四柱中八字出现" in cond2 and "没有出现" in cond2:
            # 提取出现的天干地支
            appear_part = cond2.split("没有出现")[0].replace("四柱中八字出现", "").strip()
            not_appear_part = cond2.split("没有出现")[1].strip().replace("这个字", "").strip()
            
            appear_items = []
            for item in re.split(r"[，,]", appear_part):
                item = item.strip()
                if item in STEMS or item in BRANCHES:
                    appear_items.append(item)
            
            not_appear_items = []
            for item in re.split(r"[，,]", not_appear_part):
                item = item.strip()
                if item in STEMS or item in BRANCHES:
                    not_appear_items.append(item)
            
            if appear_items or not_appear_items:
                conds = []
                if appear_items:
                    # 使用stems_branches_count
                    conds.append({"stems_branches_count": {"names": appear_items, "min": len(appear_items)}})
                if not_appear_items:
                    # 使用not条件
                    for item in not_appear_items:
                        if item in STEMS:
                            conds.append({"not": {"stems_count": {"names": [item], "min": 1}}})
                        elif item in BRANCHES:
                            conds.append({"not": {"branches_count": {"names": [item], "min": 1}}})
                
                if conds:
                    return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        # "四柱中年干，月干或日出现两个X" - 天干重复出现
        two_stem_match = re.search(r"(年干|月干|日干|时干|年干，月干或日)(?:出现|有)两个(.+?)或者两个(.+?)", cond2)
        if two_stem_match:
            stem1 = two_stem_match.group(2).strip()
            stem2 = two_stem_match.group(3).strip()
            if stem1 in STEMS and stem2 in STEMS:
                return ParseResult(True, conditions={
                    "any": [
                        {"stems_count": {"names": [stem1], "min": 2}},
                        {"stems_count": {"names": [stem2], "min": 2}}
                    ]
                })
        
        # "四柱天干中有X，Y，Z，地支有A，B，C" - 天干地支组合
        if "四柱天干中有" in cond2 and "地支有" in cond2:
            stems_part = cond2.split("地支有")[0].replace("四柱天干中有", "").strip()
            branches_part = cond2.split("地支有")[1].strip().rstrip("者")
            
            stems = [s.strip() for s in re.split(r"[，,]", stems_part) if s.strip() in STEMS]
            branches = [b.strip() for b in re.split(r"[，,]", branches_part) if b.strip() in BRANCHES]
            
            if stems and branches:
                conds = [
                    {"stems_count": {"names": stems, "min": len(stems)}},
                    {"branches_count": {"names": branches, "min": len(branches)}}
                ]
                return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：地支本气 ==========
        # "正财出现在天干或地支本气" - 地支本气判断
        if "地支本气" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={
                        "any": [
                            {"ten_gods_main": {"names": [god], "min": 1}},
                            {"ten_gods_branch_benqi": {"names": [god], "min": 1}}
                        ]
                    })
        
        # ========== 新增：五合、三合、三会、六合统计 ==========
        # "四柱天干出现五合，地支出现三合，三会和六合总数数量3个以上"
        if "五合" in cond2 and "三合" in cond2 and ("三会" in cond2 or "六合" in cond2):
            count_match = re.search(r"总数数量(\d+)个以上", cond2)
            if count_match:
                min_count = int(count_match.group(1))
                return ParseResult(True, conditions={
                    "relations_count": {"min": min_count, "include": ["wuhe", "sanhe", "sanhui", "liuhe"]}
                })
        
        # ========== 新增：金神判断 ==========
        # "金神带正印偏印" - 金神判断
        if "金神" in cond2:
            for god in ["正印", "偏印"]:
                if god in cond2:
                    return ParseResult(True, conditions={
                        "all": [
                            {"jinshen": True},
                            {"ten_gods_total": {"names": [god], "min": 1}}
                        ]
                    })
        
        # ========== 新增：羊刃判断 ==========
        # "四柱中有七杀遇到神煞羊刃" - 羊刃判断
        if "羊刃" in cond2:
            for god in TEN_GODS:
                if god in cond2:
                    return ParseResult(True, conditions={
                        "all": [
                            {"ten_gods_total": {"names": [god], "min": 1}},
                            {"yangren": True}
                        ]
                    })
        
        # "羊刃持权" - 羊刃判断
        if "羊刃持权" in cond2:
            return ParseResult(True, conditions={"yangren": True})
        
        # ========== 新增：刑冲破害 ==========
        # "正财，偏财和正印，偏印都受到了刑冲破害" - 十神被破坏
        if "受到了刑冲破害" in cond2 or "被破坏" in cond2:
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_destroyed": {"names": gods}
                })
        
        # ========== 新增：其他复杂条件 ==========
        # "八字中X的数量有Y个及以上，Z的数量少于W个" - 五行数量混合
        if "八字中" in cond2 and "的数量" in cond2:
            # 提取五行
            element_pattern = r"([木火土金水])的数量有(\d+)个及以上"
            element_matches = re.findall(element_pattern, cond2)
            if element_matches:
                conds = []
                for element, count in element_matches:
                    conds.append({"element_total": {"names": [element], "min": int(count)}})
                
                # 提取"少于"条件
                less_pattern = r"([木火土金水])的数量少于(\d+)个"
                less_matches = re.findall(less_pattern, cond2)
                for element, count in less_matches:
                    conds.append({"element_total": {"names": [element], "max": int(count) - 1}})
                
                if conds:
                    return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        # "四柱中X或Y数量出现Z个及以上，且地支出现A，B，C，D" - 十神+地支组合
        if "数量出现" in cond2 and "且地支出现" in cond2:
            # 提取十神数量条件
            ten_god_count_match = re.search(r"(.+?)或(.+?)数量出现(\d+)个及以上", cond2)
            if ten_god_count_match:
                god1 = ten_god_count_match.group(1).strip()
                god2 = ten_god_count_match.group(2).strip()
                count = int(ten_god_count_match.group(3))
                
                # 提取地支
                branches_part = cond2.split("且地支出现")[1].strip()
                branches = [b.strip() for b in re.split(r"[，,]", branches_part) if b.strip() in BRANCHES]
                
                if (god1 in TEN_GODS or god2 in TEN_GODS) and branches:
                    conds = []
                    if god1 in TEN_GODS:
                        conds.append({"ten_gods_total": {"names": [god1], "min": count}})
                    if god2 in TEN_GODS:
                        conds.append({"ten_gods_total": {"names": [god2], "min": count}})
                    if len(conds) == 2:
                        conds = [{"any": conds}]
                    conds.append({"branches_count": {"names": branches, "min": len(branches)}})
                    return ParseResult(True, conditions={"all": conds})
        
        # "四柱中八字五行X数量达Y个及以上，地支中A，B，C，D数量Z个及以上" - 五行+地支组合
        if "八字五行" in cond2 and "地支中" in cond2:
            element_count_match = re.search(r"五行([木火土金水])数量达(\d+)个及以上", cond2)
            branch_count_match = re.search(r"地支中(.+?)数量(\d+)个及以上", cond2)
            
            if element_count_match and branch_count_match:
                element = element_count_match.group(1)
                element_count = int(element_count_match.group(2))
                branches_text = branch_count_match.group(1)
                branch_count = int(branch_count_match.group(2))
                
                branches = [b.strip() for b in re.split(r"[，,]", branches_text) if b.strip() in BRANCHES]
                
                conds = [
                    {"element_total": {"names": [element], "min": element_count}},
                    {"branches_count": {"names": branches, "min": branch_count}}
                ]
                return ParseResult(True, conditions={"all": conds})
        
        # "天干中出现X，Y，Z" - 天干出现（在十神条件中）
        if "天干中出现" in cond2:
            stems = [s for s in STEMS if s in cond2]
            if stems:
                return ParseResult(True, conditions={
                    "stems_count": {"names": stems, "min": len(stems)}
                })
        
        # "十神有X或Y，且地支出现A、B、C、D任何一个" - 十神+地支组合
        if "十神有" in cond2 and "且地支出现" in cond2:
            gods = [g for g in TEN_GODS if g in cond2.split("且地支出现")[0]]
            branches_part = cond2.split("且地支出现")[1].strip()
            branches = [b.strip() for b in re.split(r"[、，,]", branches_part.replace("任何一个", "")) if b.strip() in BRANCHES]
            
            if gods and branches:
                return ParseResult(True, conditions={
                    "all": [
                        {"ten_gods_total": {"names": gods, "min": 1}},
                        {"branches_count": {"names": branches, "min": 1}}
                    ]
                })
        
        # "天干十神出现X或者Y，且地支见A，B，C，D任何一个" - 天干十神+地支
        if "天干十神出现" in cond2 and "且地支见" in cond2:
            gods = [g for g in TEN_GODS if g in cond2.split("且地支见")[0]]
            branches_part = cond2.split("且地支见")[1].strip()
            branches = [b.strip() for b in re.split(r"[、，,]", branches_part.replace("任何一个", "")) if b.strip() in BRANCHES]
            
            if gods and branches:
                return ParseResult(True, conditions={
                    "all": [
                        {"ten_gods_main": {"names": gods, "min": 1}},
                        {"branches_count": {"names": branches, "min": 1}}
                    ]
                })
        
        # "四柱中天干十神有X和Y" - 天干十神组合
        if "四柱中天干十神有" in cond2:
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_main": {"names": gods, "min": len(gods)}
                })
        
        # "四柱中主星出现X和Y" - 主星组合
        if "四柱中主星出现" in cond2:
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_main": {"names": gods, "min": len(gods)}
                })
        
        # "四柱中有X和Y" - 十神组合
        if "四柱中有" in cond2 and any(g in cond2 for g in TEN_GODS):
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": gods, "min": len(gods)}
                })
        
        # "四柱地支X，Y，Z，W" - 地支组合（在十神条件中）
        if "四柱地支" in cond2:
            branches = [b for b in BRANCHES if b in cond2]
            if branches:
                return ParseResult(True, conditions={
                    "branches_count": {"names": branches, "min": len(branches)}
                })
        
        # ========== 新增：多十神组合比较（增强，支持反向比较） ==========
        # "伤官、偏财数量多于食神、正财数量" - 多十神组合比较（正向）
        if "数量多于" in cond2 and "，" in cond2:
            parts = cond2.split("数量多于")
            if len(parts) == 2:
                more_part = parts[0]
                less_part = parts[1]
                
                # 提取多个十神（支持顿号、逗号分隔）
                more_gods = []
                less_gods = []
                
                for god in TEN_GODS:
                    if god in more_part:
                        more_gods.append(god)
                    if god in less_part:
                        less_gods.append(god)
                
                if len(more_gods) >= 2 and len(less_gods) >= 2:
                    return ParseResult(True, conditions={
                        "ten_gods_compare_group": {"more": more_gods, "less": less_gods}
                    })
        
        # "食神，偏财比伤官，正财数量少" - 多十神组合比较（反向）
        if "比" in cond2 and "数量少" in cond2:
            # 提取"X，Y比Z，W数量少"格式
            compare_match = re.search(r"([\u4e00-\u9fa5，,、]+)比([\u4e00-\u9fa5，,、]+)数量少", cond2)
            if compare_match:
                less_part = compare_match.group(1)
                more_part = compare_match.group(2)
                
                # 提取十神
                less_gods = [g for g in TEN_GODS if g in less_part]
                more_gods = [g for g in TEN_GODS if g in more_part]
                
                if len(less_gods) >= 2 and len(more_gods) >= 2:
                    # 反向比较：less_gods 应该少于 more_gods
                    return ParseResult(True, conditions={
                        "ten_gods_compare_group": {"more": more_gods, "less": less_gods}
                    })
        
        # "女命八字，四柱中十神X，Y，Z的数量多于A，B的数量" - 性别+十神数量比较
        if "女命" in cond2 and "数量多于" in cond2:
            more_part = cond2.split("数量多于")[0]
            less_part = cond2.split("数量多于")[1]
            
            more_gods = [g for g in TEN_GODS if g in more_part]
            less_gods = [g for g in TEN_GODS if g in less_part]
            
            if more_gods and less_gods:
                return ParseResult(True, conditions={
                    "all": [
                        {"gender": "female"},
                        {"ten_gods_compare_group": {"more": more_gods, "less": less_gods}}
                    ]
                })
        
        # "四柱中十神X和Y的数量多" - 数量多（简化处理为至少2个）
        if "的数量多" in cond2:
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": gods, "min": 2}
                })
        
        # "四柱中十神X出现Y，Z" - 十神出现
        if "四柱中十神出现" in cond2:
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": gods, "min": len(gods)}
                })
        
        # "四柱中十神X，Y，Z数量有W个以上" - 十神数量
        count_above_match = re.search(r"四柱中十神(.+?)数量有(\d+)个以上", cond2)
        if count_above_match:
            gods_text = count_above_match.group(1)
            count = int(count_above_match.group(2))
            gods = [g for g in TEN_GODS if g in gods_text]
            if gods:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": gods, "min": count}
                })
        
        # "四柱中十神X数量为Y-Z" - 十神数量范围
        range_match = re.search(r"四柱中十神(.+?)数量为(\d+)-(\d+)", cond2)
        if range_match:
            god = range_match.group(1).strip()
            min_count = int(range_match.group(2))
            max_count = int(range_match.group(3))
            if god in TEN_GODS:
                return ParseResult(True, conditions={
                    "ten_gods_total": {"names": [god], "min": min_count, "max": max_count}
                })
        
        # "四柱中十神X数量为Y-Z，Y出现在Z或W" - 复杂组合
        if "数量为" in cond2 and "出现在" in cond2:
            # 先解析数量条件
            count_part = cond2.split("，")[0]
            appear_part = cond2.split("，")[1] if "，" in cond2 else ""
            
            count_match = re.search(r"(.+?)数量为(\d+)-(\d+)", count_part)
            if count_match:
                god = count_match.group(1).strip()
                min_count = int(count_match.group(2))
                max_count = int(count_match.group(3))
                
                if god in TEN_GODS:
                    conds = [{"ten_gods_total": {"names": [god], "min": min_count, "max": max_count}}]
                    
                    # 解析"出现在"条件
                    if "出现在" in appear_part:
                        if "天干" in appear_part:
                            conds.append({"ten_gods_main": {"names": [god], "min": 1}})
                        elif "地支本气" in appear_part:
                            conds.append({"ten_gods_branch_benqi": {"names": [god], "min": 1}})
                    
                    # 解析"多于"条件
                    if "多于" in appear_part:
                        more_gods = [g for g in TEN_GODS if g in appear_part.split("多于")[1]]
                        if more_gods:
                            conds.append({"ten_gods_compare_group": {"more": [god], "less": more_gods}})
                    
                    return ParseResult(True, conditions={"all": conds})
        
        # "四柱十神中X，Y数量有Z个及以上，A，B数量为0" - 多条件组合
        if "数量有" in cond2 and "数量为0" in cond2:
            # 解析"数量有"条件
            have_part = cond2.split("，且")[0] if "，且" in cond2 else cond2.split("数量为0")[0]
            zero_part = cond2.split("数量为0")[1] if "数量为0" in cond2 else ""
            
            have_match = re.search(r"(.+?)数量有(\d+)个及以上", have_part)
            if have_match:
                gods_text = have_match.group(1)
                count = int(have_match.group(2))
                gods = [g for g in TEN_GODS if g in gods_text]
                
                conds = []
                if gods:
                    conds.append({"ten_gods_total": {"names": gods, "min": count}})
                
                # 解析"数量为0"条件
                zero_gods = [g for g in TEN_GODS if g in zero_part]
                if zero_gods:
                    conds.append({"ten_gods_total": {"names": zero_gods, "eq": 0}})
                
                if conds:
                    return ParseResult(True, conditions={"all": conds})
        
        # "四柱天干出现五合" - 五合判断
        if "天干出现五合" in cond2:
            return ParseResult(True, conditions={
                "stem_wuhe_pairs": {"min": 1}
            })
        
        # "地支出现三合，三会和六合" - 三合三会六合判断
        if "地支出现三合" in cond2 or "三会" in cond2 or "六合" in cond2:
            return ParseResult(True, conditions={
                "branch_liuhe_sanhe_count": {"min": 1}
            })
        
        # ========== 新增：流年大运支持（低优先级） ==========
        # "军人身份流年大小运五行是金土" - 流年大运五行
        liunian_dayun_element_match = re.search(r"流年(?:大小运|大运)(?:五行是|五行为)([木火土金水、，,]+)", cond2)
        if liunian_dayun_element_match:
            elements_text = liunian_dayun_element_match.group(1)
            # 提取五行
            elements = [e.strip() for e in re.split(r"[、，,]", elements_text) if e.strip() in ["木", "火", "土", "金", "水"]]
            
            if elements:
                # 注意：军人身份条件暂时忽略，因为需要额外的用户信息
                return ParseResult(True, conditions={
                    "liunian_dayun_element": {"elements": elements}
                })
        
        # "流年大小运五行是X" - 简化格式
        if "流年大小运五行" in cond2 or "流年大运五行" in cond2:
            elements = [e for e in ["木", "火", "土", "金", "水"] if e in cond2]
            if elements:
                return ParseResult(True, conditions={
                    "liunian_dayun_element": {"elements": elements}
                })
        
        # "华盖数量3个及以上" - 神煞数量（在十神条件中）
        if "华盖数量" in cond2:
            count_match = re.search(r"华盖数量(\d+)个及以上", cond2)
            if count_match:
                count = int(count_match.group(1))
                return ParseResult(True, conditions={
                    "deities_count": {"name": "华盖", "min": count}
                })
        
        # ========== 优化：身旺+十神组合正则表达式（高优先级） ==========
        # "身旺，同时有七杀，正印，偏印" - 身旺+十神组合
        wangshuai_ten_gods_patterns = [
            r"身旺，同时有([\u4e00-\u9fa5，,、]+)",
            r"身强，同时有([\u4e00-\u9fa5，,、]+)",
            r"身旺，有([\u4e00-\u9fa5，,、]+)",
            r"身强，有([\u4e00-\u9fa5，,、]+)",
        ]
        
        for pattern in wangshuai_ten_gods_patterns:
            wangshuai_match = re.search(pattern, cond2)
            if wangshuai_match:
                gods_text = wangshuai_match.group(1)
                # 提取十神
                gods = [g for g in TEN_GODS if g in gods_text]
                if gods:
                    # 组合旺衰条件和十神存在条件
                    conds = [{"wangshuai": ["身旺"]}]
                    for god in gods:
                        conds.append({"ten_gods_total": {"names": [god], "min": 1}})
                    return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：十神能量量化功能（低优先级） ==========
        # "伤官食神强于正七官杀者" - 十神能量比较
        energy_compare_match = re.search(r"(.+?)(?:强于|能量强于|能量大于)(.+?)(?:者|，|$)", cond2)
        if energy_compare_match:
            group_a_text = energy_compare_match.group(1).strip()
            group_b_text = energy_compare_match.group(2).strip().rstrip("者").rstrip("，")
            
            # 提取十神（支持多个十神）
            group_a = [g for g in TEN_GODS if g in group_a_text]
            group_b = [g for g in TEN_GODS if g in group_b_text]
            
            if len(group_a) >= 1 and len(group_b) >= 1:
                return ParseResult(True, conditions={
                    "ten_gods_energy_compare": {"group_a": group_a, "group_b": group_b, "relation": "stronger"}
                })
        
        # ========== 新增：地支+五行组合条件（中优先级） ==========
        # "辰戌土旺为狱官" - 地支+五行组合
        branch_element_match = re.search(r"([子丑寅卯辰巳午未申酉戌亥、，,]+)([木火土金水])旺", cond2)
        if branch_element_match:
            branches_text = branch_element_match.group(1)
            element = branch_element_match.group(2)
            
            # 提取地支
            branches = [b.strip() for b in re.split(r"[、，,]", branches_text) if b.strip() in BRANCHES]
            
            if branches and element:
                return ParseResult(True, conditions={
                    "branch_element_combination": {"branches": branches, "element": element, "wang": True}
                })
        
        # "正印生沐浴" - 神煞特殊条件（在十神条件中）
        if "正印生沐浴" in cond2:
            return ParseResult(True, conditions={
                "all": [
                    {"ten_gods_total": {"names": ["正印"], "min": 1}},
                    {"deities_in_any_pillar": "沐浴"}
                ]
            })
        
        # ========== 新增：十神数量相当 + 旺衰条件 ==========
        if "数量相当" in cond2 or "数量相等" in cond2:
            # 提取十神名称
            ten_gods_found = [tg for tg in TEN_GODS if tg in cond2]
            if len(ten_gods_found) >= 2:
                conds = []
                # 添加十神数量相等条件（需要在规则引擎中实现）
                conds.append({
                    "ten_gods_equal": {
                        "names": ten_gods_found[:2]  # 取前两个
                    }
                })
                
                # 添加旺衰条件
                if "日主身强" in cond2 or "身强" in cond2:
                    conds.append({"wangshuai": ["身旺", "极旺"]})
                elif "日主身弱" in cond2 or "身弱" in cond2:
                    conds.append({"wangshuai": ["身弱"]})
                
                return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：旺衰 + 十神相邻条件 ==========
        if "相邻" in cond2:
            conds = []
            # 添加旺衰条件
            if "日主身强" in cond2 or "身强" in cond2:
                conds.append({"wangshuai": ["身旺", "极旺"]})
            
            # 提取十神名称
            ten_gods_found = [tg for tg in TEN_GODS if tg in cond2]
            if ten_gods_found:
                # 十神相邻条件（需要在规则引擎中实现）
                conds.append({
                    "ten_gods_adjacent": {
                        "names": ten_gods_found
                    }
                })
            
            if conds:
                return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：旺衰 + 十神顺次出现 ==========
        if "顺次出现" in cond2 or "顺生组合" in cond2:
            conds = []
            # 添加旺衰条件
            if "日主身强" in cond2 or "身强" in cond2:
                conds.append({"wangshuai": ["身旺", "极旺"]})
            
            # 提取十神名称（财星、官星、印星等）
            ten_gods_found = [tg for tg in TEN_GODS if tg in cond2 or ("财" in cond2 and tg in ["正财", "偏财"]) or ("官" in cond2 and tg in ["正官", "七杀"]) or ("印" in cond2 and tg in ["正印", "偏印"])]
            if ten_gods_found:
                # 十神顺序条件（需要在规则引擎中实现）
                conds.append({
                    "ten_gods_sequence": {
                        "names": ten_gods_found
                    }
                })
            
            if conds:
                return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：十神合的关系 ==========
        if "合" in cond2 and ("官星" in cond2 or "正官" in cond2 or "七杀" in cond2):
            # "命局（原局）、大运或流年的天干地支中，官星（正官/七杀）与其他干支发生了"合"的关系"
            conds = []
            # 添加十神条件（正官或七杀）
            if "正官" in cond2:
                conds.append({
                    "any": [
                        {"ten_gods_total": {"names": ["正官"], "min": 1}},
                        {"ten_gods_total": {"names": ["七杀"], "min": 1}}
                    ]
                })
            else:
                conds.append({
                    "ten_gods_total": {
                        "names": ["正官", "七杀"],
                        "min": 1
                    }
                })
            
            # 添加合的关系条件（需要在规则引擎中实现）
            conds.append({
                "ten_gods_he": {
                    "names": ["正官", "七杀"]
                }
            })
            
            return ParseResult(True, conditions={"all": conds})
        
        # ========== 新增：禄马星被冲克后又相合 ==========
        if "禄马星被冲克后又相合" in cond2 or "禄马星" in cond2:
            conds = []
            # 添加旺衰条件
            if "日主身强" in cond2:
                conds.append({"wangshuai": ["身旺", "极旺"]})
            
            # 添加十神条件（无财星或无官星）
            if "不见财星" in cond2 or "无财星" in cond2:
                conds.append({
                    "not": {
                        "ten_gods_total": {
                            "names": ["正财", "偏财"],
                            "min": 1
                        }
                    }
                })
            if "不见官星" in cond2 or "无官星" in cond2:
                conds.append({
                    "not": {
                        "ten_gods_total": {
                            "names": ["正官", "七杀"],
                            "min": 1
                        }
                    }
                })
            
            # 添加神煞条件（禄神、驿马）
            conds.append({
                "any": [
                    {"deities_in_any_pillar": "禄神"},
                    {"deities_in_any_pillar": "驿马"}
                ]
            })
            
            if conds:
                return ParseResult(True, conditions={"all": conds})
        
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
        # "四柱中有寅，申，巳，亥" - 地支出现
        if "四柱中有" in cond2:
            branches = [b for b in BRANCHES if b in cond2]
            if branches:
                return ParseResult(True, conditions={
                    "branches_count": {"names": branches, "min": len(branches)}
                })
        
        # 地支内有X，并且有Y
        if "四柱地支内有" in cond2:
            branches = []
            for branch in BRANCHES:
                if branch in cond2:
                    branches.append(branch)
            if branches:
                conds = [{"branches_count": {"names": [b], "min": 1}} for b in branches]
                return ParseResult(True, conditions=conds)
        
        # ========== 新增：地支顺次排列（"地支'甲戊庚'顺次排列"） ==========
        # 注意：这里"甲戊庚"是误写（实际是天干），但解析器尝试兼容
        if "顺次排列" in cond2:
            # 提取地支序列（从引号中，支持中文引号和英文引号）
            branch_sequence_match = re.search(r'["""''""""]?([子丑寅卯辰巳午未申酉戌亥]+)["""''""""]?', cond2)
            if branch_sequence_match:
                branch_sequence = branch_sequence_match.group(1)
                branches = list(branch_sequence)
                # 地支顺序条件（需要在规则引擎中实现）
                return ParseResult(True, conditions={
                    "branches_sequence": {"names": branches}
                })
            
            # 如果是"甲戊庚"这样的误写（实际是天干），尝试提取为天干序列
            # 虽然条件类型是"地支"，但内容是天干，我们将其解析为天干序列条件
            # 这样可以在规则引擎中正确匹配（规则引擎会根据实际内容匹配）
            stem_sequence_match = re.search(r'["""''""""]?([甲乙丙丁戊己庚辛壬癸]+)["""''""""]?', cond2)
            if stem_sequence_match:
                stem_sequence = stem_sequence_match.group(1)
                stems = list(stem_sequence)
                # 返回天干序列条件（虽然条件类型是地支，但实际内容是天干）
                # 规则引擎可以根据stems_sequence条件正确匹配
                return ParseResult(True, conditions={
                    "stems_sequence": {"names": stems}
                })
        
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
        
        # ========== 新增：旺相条件解析（增强） ==========
        # "旺相" 等同于 "身旺" 或 "极旺"
        if "旺相" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["身旺", "极旺"]})
        
        # "且旺" 等同于 "身旺" 或 "极旺"
        if "且旺" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["身旺", "极旺"]})
        
        # "并且旺相"
        if "并且旺相" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["身旺", "极旺"]})
        
        # "日主身旺"
        if "日主身旺" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["身旺"]})
        
        # ========== 新增：日主极弱 ==========
        if "极弱" in cond2 or "日主极弱" in cond2:
            return ParseResult(True, conditions={"wangshuai": ["极弱"]})
        
        return ParseResult(False, reason=f"未识别的旺衰条件: {cond2}")
    
    @classmethod
    def _parse_wuxing(cls, cond2: str) -> ParseResult:
        """解析五行条件"""
        conds = []
        
        # "五行金的数量为0-1" 或 "五行金的数量为0-1，没有火为0"
        # 解析五行数量条件
        element_pattern = r"五行([木火土金水])的数量为(\d+)(?:-(\d+))?"
        element_match = re.search(element_pattern, cond2)
        if element_match:
            element = element_match.group(1)
            min_count = int(element_match.group(2))
            max_count = int(element_match.group(3)) if element_match.group(3) else None
            
            if max_count is not None:
                # 范围条件
                conds.append({"element_total": {"names": [element], "min": min_count, "max": max_count}})
            else:
                # 单个数量条件
                conds.append({"element_total": {"names": [element], "eq": min_count}})
        
        # "没有X为0" - 五行数量为0
        no_element_pattern = r"没有([木火土金水])为0"
        no_element_match = re.search(no_element_pattern, cond2)
        if no_element_match:
            element = no_element_match.group(1)
            conds.append({"element_total": {"names": [element], "eq": 0}})
        
        # "五行X的数量为Y个及以上"
        element_min_pattern = r"五行([木火土金水])的数量为(\d+)个及以上"
        element_min_match = re.search(element_min_pattern, cond2)
        if element_min_match:
            element = element_min_match.group(1)
            min_count = int(element_min_match.group(2))
            conds.append({"element_total": {"names": [element], "min": min_count}})
        
        # "五行X的数量少于Y个"
        element_max_pattern = r"五行([木火土金水])的数量少于(\d+)个"
        element_max_match = re.search(element_max_pattern, cond2)
        if element_max_match:
            element = element_max_match.group(1)
            max_count = int(element_max_match.group(2))
            conds.append({"element_total": {"names": [element], "max": max_count - 1}})
        
        # ========== 新增：八字五行金木水火土都有 ==========
        if "五行" in cond2 and ("都有" in cond2 or "全部都有" in cond2):
            # 检查是否包含所有五行
            all_elements = ["木", "火", "土", "金", "水"]
            present_elements = [e for e in all_elements if e in cond2]
            if len(present_elements) >= 4:  # 至少有4个五行
                conds = [{"element_total": {"names": [e], "min": 1}} for e in all_elements]
                # 检查"无刑冲破害"条件（需要在规则引擎中实现）
                if "无刑冲破害" in cond2 or "无刑冲" in cond2:
                    conds.append({"no_xing_chong": True})
                return ParseResult(True, conditions={"all": conds})
        
        if conds:
            return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        return ParseResult(False, reason=f"未识别的五行条件: {cond2}")
    
    @classmethod
    def _parse_nayin(cls, cond2: str) -> ParseResult:
        """解析纳音条件"""
        conds = []
        
        # "年命纳音刑克日柱或时柱纳音"
        if "年命纳音" in cond2 and ("刑克" in cond2 or "克" in cond2):
            # 解析目标柱
            target_pillars = []
            if "日柱" in cond2:
                target_pillars.append("day")
            if "时柱" in cond2:
                target_pillars.append("hour")
            if "月柱" in cond2:
                target_pillars.append("month")
            
            if target_pillars:
                # 使用nayin_relation条件（需要在规则引擎中实现）
                if len(target_pillars) == 1:
                    return ParseResult(True, conditions={
                        "nayin_relation": {"pillar_a": "year", "pillar_b": target_pillars[0], "relation": "ke"}
                    })
                else:
                    # 多个目标柱，使用any组合
                    any_conds = []
                    for target_pillar in target_pillars:
                        any_conds.append({
                            "nayin_relation": {"pillar_a": "year", "pillar_b": target_pillar, "relation": "ke"}
                        })
                    return ParseResult(True, conditions={"any": any_conds})
        
        # "年柱纳音是X，日柱纳音是Y"
        nayin_pillar_match = re.search(r"(年柱|月柱|日柱|时柱)纳音(?:是|为)(.+?)(?:，|$)", cond2)
        if nayin_pillar_match:
            pillar_name = nayin_pillar_match.group(1)
            nayin_name = nayin_pillar_match.group(2).strip()
            pillar_key = cls._pillar_to_key(pillar_name)
            return ParseResult(True, conditions={
                "nayin_equals": {"pillar": pillar_key, "nayin": nayin_name}
            })
        
        return ParseResult(False, reason=f"未识别的纳音条件: {cond2}")
    
    @classmethod
    def _parse_stem(cls, cond2: str) -> ParseResult:
        """解析天干条件"""
        conds = []
        
        # "四柱中戊和辛总数3个及以上"
        stem_count_pattern = r"四柱中([甲乙丙丁戊己庚辛壬癸])(?:和([甲乙丙丁戊己庚辛壬癸]))?总数(\d+)个(?:及以上|以上)?"
        stem_count_match = re.search(stem_count_pattern, cond2)
        if stem_count_match:
            stem1 = stem_count_match.group(1)
            stem2 = stem_count_match.group(2)
            count = int(stem_count_match.group(3))
            
            stems = [stem1]
            if stem2:
                stems.append(stem2)
            
            conds.append({"stems_count": {"names": stems, "min": count}})
        
        # "天干中出现X，Y，Z"
        if "天干中出现" in cond2:
            stems = [s for s in STEMS if s in cond2]
            if stems:
                conds.append({"stems_count": {"names": stems, "min": len(stems)}})
        
        # "天干中有X，Y，Z"
        if "天干中有" in cond2:
            stems = [s for s in STEMS if s in cond2]
            if stems:
                conds.append({"stems_count": {"names": stems, "min": len(stems)}})
        
        # ========== 新增：天干顺次排列（"天干'乙丙丁'顺次排列"） ==========
        if "顺次排列" in cond2:
            # 提取天干序列（从引号中，支持中文引号和英文引号）
            stem_sequence_match = re.search(r'["""''""""]?([甲乙丙丁戊己庚辛壬癸]+)["""''""""]?', cond2)
            if stem_sequence_match:
                stem_sequence = stem_sequence_match.group(1)
                stems = list(stem_sequence)
                # 天干顺序条件（需要在规则引擎中实现）
                return ParseResult(True, conditions={
                    "stems_sequence": {"names": stems}
                })
        
        # ========== 新增：天干有X ==========
        if "天干有" in cond2:
            stem_match = re.search(r'天干有([甲乙丙丁戊己庚辛壬癸])', cond2)
            if stem_match:
                stem = stem_match.group(1)
                return ParseResult(True, conditions={
                    "stems_count": {"names": [stem], "min": 1}
                })
        
        if conds:
            return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        return ParseResult(False, reason=f"未识别的天干条件: {cond2}")
    
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
        
        # ========== 新增：四柱中有特定地支排列（"四柱中有子午子，或四柱中有午子午"） ==========
        if "四柱中有" in cond2 and ("子午子" in cond2 or "午子午" in cond2):
            # 提取地支序列
            branch_pattern = re.findall(r'([子丑寅卯辰巳午未申酉戌亥]{3})', cond2)
            if branch_pattern:
                conds = []
                for pattern in branch_pattern:
                    # 转换为条件：四柱中必须包含这些地支
                    branches = list(pattern)
                    conds.append({
                        "all": [
                            {"branches_count": {"names": [branches[0]], "min": 1}},
                            {"branches_count": {"names": [branches[1]], "min": 1}},
                            {"branches_count": {"names": [branches[2]], "min": 1}}
                        ]
                    })
                if len(conds) > 1:
                    return ParseResult(True, conditions={"any": conds})
                else:
                    return ParseResult(True, conditions=conds[0])
        
        # ========== 新增：日主身弱，四柱主星和副星中... ==========
        if "日主身弱" in cond2 and "四柱主星和副星" in cond2:
            conds = [{"wangshuai": ["身弱"]}]
            
            # 提取十神名称和数量要求
            ten_gods_found = [tg for tg in TEN_GODS if tg in cond2]
            if ten_gods_found:
                # 检查数量要求（"达到3个以上"、"包含3个"）
                count_match = re.search(r'达到(\d+)个以上|包含(\d+)个|达到(\d+)个', cond2)
                min_count = 3  # 默认3个
                if count_match:
                    min_count = int(count_match.group(1) or count_match.group(2) or count_match.group(3))
                
                conds.append({
                    "ten_gods_total": {
                        "names": ten_gods_found,
                        "min": min_count
                    }
                })
            
            # 检查"无"条件（"无正印、偏印"、"无比肩、劫财"）
            if "无" in cond2:
                no_ten_gods = [tg for tg in TEN_GODS if tg in cond2.split("无")[1] if tg in TEN_GODS]
                if no_ten_gods:
                    conds.append({
                        "not": {
                            "ten_gods_total": {
                                "names": no_ten_gods,
                                "min": 1
                            }
                        }
                    })
            
            if len(conds) > 1:
                return ParseResult(True, conditions={"all": conds})
            else:
                return ParseResult(True, conditions=conds[0])
        
        # ========== 新增：日主八字五行属性到达4个以上 ==========
        if "五行属性到达" in cond2 or "五行属性达到" in cond2:
            count_match = re.search(r'到达(\d+)个以上|达到(\d+)个以上|到达(\d+)个|达到(\d+)个', cond2)
            if count_match:
                min_count = int(count_match.group(1) or count_match.group(2) or count_match.group(3) or count_match.group(4))
                # 使用五行总数条件（需要在规则引擎中支持）
                return ParseResult(True, conditions={
                    "wuxing_count": {"min": min_count}
                })
        
        return ParseResult(False, reason=f"未识别的四柱条件: {cond2}")
    
    @classmethod
    def _parse_rigan(cls, cond2: str) -> ParseResult:
        """解析日干条件"""
        conds = []
        
        # ========== 日干五行属性是X，且地支必须是... ==========
        if "五行属性是" in cond2:
            # 提取五行
            element_match = re.search(r'五行属性是([木火土金水])', cond2)
            if element_match:
                element = element_match.group(1)
                # 日干五行对应日柱天干
                # 需要在规则引擎中实现：根据日柱天干判断五行
                conds.append({"day_stem_element": element})
        
        # ========== 地支条件（"且地支必须是..."、"且地支必须只有..."） ==========
        if "地支" in cond2:
            # 提取地支列表
            branch_pattern = r'[子丑寅卯辰巳午未申酉戌亥]'
            branches = re.findall(branch_pattern, cond2.split("地支")[-1])
            
            if branches:
                # 检查是"必须是"还是"必须只有"
                if "必须只有" in cond2 or "只有" in cond2:
                    # 只有这些地支，不能有其他
                    conds.append({
                        "branches_only": {"names": branches}
                    })
                else:
                    # 必须有这些地支
                    conds.append({
                        "branches_count": {"names": branches, "min": len(branches)}
                    })
        
        # ========== 日干与月干/时干五合 ==========
        if "五合" in cond2:
            if "日干与月干五合" in cond2:
                conds.append({
                    "pillar_relation": {
                        "pillar_a": "day",
                        "pillar_b": "month",
                        "relation": "he",
                        "part": "stem"
                    }
                })
            if "日干与时干五合" in cond2:
                conds.append({
                    "pillar_relation": {
                        "pillar_a": "day",
                        "pillar_b": "hour",
                        "relation": "he",
                        "part": "stem"
                    }
                })
            if "或" in cond2:
                # 两个都有，用any
                return ParseResult(True, conditions={
                    "any": [
                        {"pillar_relation": {"pillar_a": "day", "pillar_b": "month", "relation": "he", "part": "stem"}},
                        {"pillar_relation": {"pillar_a": "day", "pillar_b": "hour", "relation": "he", "part": "stem"}}
                    ]
                })
        
        if conds:
            if len(conds) > 1:
                return ParseResult(True, conditions={"all": conds})
            else:
                return ParseResult(True, conditions=conds[0])
        
        return ParseResult(False, reason=f"未识别的日干条件: {cond2}")
    
    @classmethod
    def _parse_yueling(cls, cond2: str) -> ParseResult:
        """解析月令条件"""
        conds = []
        
        # ========== 月令为正印且在天干里出现 ==========
        if "为正印" in cond2 or "为正官" in cond2 or "为正财" in cond2:
            # 提取十神名称
            ten_god = None
            for tg in TEN_GODS:
                if f"为{tg}" in cond2:
                    ten_god = tg
                    break
            
            if ten_god:
                # 月令（月支）有该十神
                conds.append({
                    "ten_gods_sub": {
                        "names": [ten_god],
                        "pillars": ["month"],
                        "min": 1
                    }
                })
                
                # 且在天干里出现（主星）
                conds.append({
                    "ten_gods_main": {
                        "names": [ten_god],
                        "min": 1
                    }
                })
        
        # ========== 没有正财偏财来破坏 ==========
        if "没有" in cond2 and ("正财" in cond2 or "偏财" in cond2):
            no_gods = []
            if "正财" in cond2:
                no_gods.append("正财")
            if "偏财" in cond2:
                no_gods.append("偏财")
            
            if no_gods:
                conds.append({
                    "not": {
                        "ten_gods_total": {
                            "names": no_gods,
                            "min": 1
                        }
                    }
                })
        
        if conds:
            return ParseResult(True, conditions={"all": conds} if len(conds) > 1 else conds[0])
        
        # 默认：月令通常指月支，可以用月柱地支条件来处理
        # 提取地支
        branch_pattern = r'[子丑寅卯辰巳午未申酉戌亥]'
        branches = re.findall(branch_pattern, cond2)
        
        if branches:
            return ParseResult(True, conditions={
                "pillar_in": {"pillar": "month", "part": "branch", "values": branches}
            })
        
        return ParseResult(False, reason=f"未识别的月令条件: {cond2}")
    
    @classmethod
    def _parse_shishen_mingge(cls, cond2: str) -> ParseResult:
        """解析十神命格条件"""
        # 十神作为命格
        if cond2 in TEN_GODS:
            return ParseResult(True, conditions={"shishen_ming_ge": cond2})
        
        # ========== 新增：金神格，且... ==========
        if "金神格" in cond2:
            conds = []
            # 添加金神格条件（需要在规则引擎中支持）
            conds.append({"special_pattern": "金神格"})
            
            # 解析附加条件
            if "，且" in cond2 or "且" in cond2:
                rest = cond2.split("，且")[-1] if "，且" in cond2 else cond2.split("且")[-1]
                rest = rest.strip()
                
                # 神煞条件（"神煞有羊刃"）
                if "神煞有" in rest:
                    shensha = rest.replace("神煞有", "").strip()
                    conds.append({"deities_in_any_pillar": shensha})
                
                # 五行条件（"八字对应五行属火数量超过3个"）
                if "五行属" in rest and "数量超过" in rest:
                    element_match = re.search(r'五行属([木火土金水])数量超过(\d+)个', rest)
                    if element_match:
                        element = element_match.group(1)
                        min_count = int(element_match.group(2)) + 1  # 超过3个 = >= 4个
                        conds.append({"element_total": {"element": element, "min": min_count}})
                
                # 天干条件（"天干有甲"）
                if "天干有" in rest:
                    stem_match = re.search(r'天干有([甲乙丙丁戊己庚辛壬癸])', rest)
                    if stem_match:
                        stem = stem_match.group(1)
                        conds.append({"stems_count": {"names": [stem], "min": 1}})
                
                # 十神条件（"四柱主星和副星有XX"）
                if "四柱主星和副星有" in rest:
                    ten_gods_found = [tg for tg in TEN_GODS if tg in rest]
                    if ten_gods_found:
                        # 检查"或"连接（"正印或偏印"）
                        if "或" in rest:
                            conds.append({
                                "any": [
                                    {"ten_gods_total": {"names": [tg], "min": 1}}
                                    for tg in ten_gods_found
                                ]
                            })
                        else:
                            conds.append({
                                "ten_gods_total": {
                                    "names": ten_gods_found,
                                    "min": 1
                                }
                            })
            
            if len(conds) > 1:
                return ParseResult(True, conditions={"all": conds})
            else:
                return ParseResult(True, conditions=conds[0])
        
        return ParseResult(False, reason=f"未识别的十神命格条件: {cond2}")
    
    @classmethod
    def _parse_composite(cls, cond1: str, cond2: str, qty: str) -> ParseResult:
        """解析复合条件"""
        conds = []
        
        # "女命四柱都有十神X" - 神煞十神条件
        if "四柱都有十神" in cond2:
            gods = [g for g in TEN_GODS if g in cond2]
            if gods:
                # 检查每个柱都有该十神
                return ParseResult(True, conditions={
                    "ten_gods_in_all_pillars": {"names": gods}
                })
        
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
        
        # ========== 新增：神煞十神复合条件 ==========
        if cond1 == "神煞十神":
            # "女命四柱都有十神七杀"
            if "女命" in cond2:
                conds.append({"gender": "female"})
            
            # 提取十神
            for god in TEN_GODS:
                if god in cond2:
                    # 检查是否有"四柱都有"或"四柱都有十神"
                    if "四柱都有" in cond2 or "四柱都有十神" in cond2:
                        conds.append({"ten_gods_main": {"names": [god], "min": 4}})
                    elif "四柱" in cond2:
                        # 默认至少1个
                        conds.append({"ten_gods_main": {"names": [god], "min": 1}})
                    else:
                        conds.append({"ten_gods_total": {"names": [god], "min": 1}})
                    break
            
            # 提取神煞
            # 这里需要从cond2中提取神煞名称，暂时使用通用匹配
            if conds:
                return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
        # ========== 新增：处理"神煞十神"复合条件类型 ==========
        if "神煞" in cond1 and "十神" in cond1:
            # 解析十神部分
            for god in TEN_GODS:
                if god in cond2:
                    if "四柱都有" in cond2:
                        conds.append({"ten_gods_main": {"names": [god], "min": 4}})
                    else:
                        conds.append({"ten_gods_total": {"names": [god], "min": 1}})
                    break
            
            # 解析神煞部分（如果有）
            # 这里可以添加神煞解析逻辑
            
            if conds:
                return ParseResult(True, conditions=conds if len(conds) > 1 else conds[0])
        
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


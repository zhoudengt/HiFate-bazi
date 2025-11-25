#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年大运关系分析器

功能：
- 分析流年与大运的关系（生/克/冲/合/刑/害/破）
- 分析流年与八字四柱的关系
- 分析大运与八字四柱的关系

设计原则：
- 复用现有模块（src/data/relations.py, src/data/constants.py）
- 独立模块，可被其他服务调用
- 微服务思维，单一职责
"""

import logging
from typing import Dict, List, Any, Optional
from src.data.relations import (
    STEM_HE,           # 天干合
    BRANCH_LIUHE,      # 地支六合
    BRANCH_CHONG,      # 地支六冲
    BRANCH_XING,       # 地支刑
    BRANCH_HAI,        # 地支害
    BRANCH_PO,         # 地支破
    BRANCH_SANHE_GROUPS,  # 三合局
)
from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS

logger = logging.getLogger(__name__)


class FortuneRelationAnalyzer:
    """流年大运关系分析器"""
    
    @staticmethod
    def analyze(
        bazi_pillars: Dict[str, Dict[str, str]],
        liunian: Dict[str, str],
        dayun: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        分析流年、大运与八字的关系
        
        Args:
            bazi_pillars: 八字四柱，如 {
                "year": {"stem": "丁", "branch": "卯"},
                "month": {"stem": "己", "branch": "酉"},
                "day": {"stem": "戊", "branch": "辰"},
                "hour": {"stem": "乙", "branch": "卯"}
            }
            liunian: 流年信息，如 {"stem": "丁", "branch": "未"}
            dayun: 大运信息（可选），如 {"stem": "丙", "branch": "午"}
        
        Returns:
            {
                "liunian_dayun_relation": {...},  # 流年vs大运
                "liunian_bazi_relation": {...},   # 流年vs八字
                "dayun_bazi_relation": {...},     # 大运vs八字
                "summary": "流年大运火土两旺，与日柱有破"
            }
        """
        try:
            result = {}
            
            # 1. 流年 vs 大运
            if dayun and dayun.get('stem') and dayun.get('branch'):
                liunian_dayun = FortuneRelationAnalyzer._analyze_liunian_dayun(
                    liunian, dayun
                )
                result['liunian_dayun_relation'] = liunian_dayun
            else:
                result['liunian_dayun_relation'] = {}
            
            # 2. 流年 vs 八字
            liunian_bazi = FortuneRelationAnalyzer._analyze_fortune_bazi(
                liunian, bazi_pillars, "流年"
            )
            result['liunian_bazi_relation'] = liunian_bazi
            
            # 3. 大运 vs 八字
            if dayun and dayun.get('stem') and dayun.get('branch'):
                dayun_bazi = FortuneRelationAnalyzer._analyze_fortune_bazi(
                    dayun, bazi_pillars, "大运"
                )
                result['dayun_bazi_relation'] = dayun_bazi
            else:
                result['dayun_bazi_relation'] = {}
            
            # 4. 分析八字内部刑冲合害关系（新增）
            internal_relations = FortuneRelationAnalyzer._analyze_internal_relations(
                bazi_pillars
            )
            result['internal_relations'] = internal_relations
            
            # 5. 生成总结
            summary = FortuneRelationAnalyzer._generate_summary(result)
            result['summary'] = summary
            
            return result
            
        except Exception as e:
            logger.error(f"流年大运关系分析失败: {e}")
            return {
                "liunian_dayun_relation": {},
                "liunian_bazi_relation": {},
                "dayun_bazi_relation": {},
                "summary": "分析失败"
            }
    
    @staticmethod
    def _analyze_liunian_dayun(liunian: Dict, dayun: Dict) -> Dict[str, Any]:
        """
        分析流年与大运的关系
        
        Args:
            liunian: {"stem": "丁", "branch": "未"}
            dayun: {"stem": "丙", "branch": "午"}
        
        Returns:
            {
                "stem_relation": "丁丙比劫并见",
                "branch_relation": "午未六合",
                "element_relation": "火土相生"
            }
        """
        ln_stem = liunian.get('stem', '')
        ln_branch = liunian.get('branch', '')
        dy_stem = dayun.get('stem', '')
        dy_branch = dayun.get('branch', '')
        
        result = {}
        
        # 天干关系
        if ln_stem and dy_stem:
            stem_rel = FortuneRelationAnalyzer._get_stem_relation(ln_stem, dy_stem)
            result['stem_relation'] = stem_rel
        
        # 地支关系
        if ln_branch and dy_branch:
            branch_rel = FortuneRelationAnalyzer._get_branch_relation(ln_branch, dy_branch)
            result['branch_relation'] = branch_rel
        
        # 五行关系
        if ln_stem and ln_branch and dy_stem and dy_branch:
            ln_element = STEM_ELEMENTS.get(ln_stem)
            dy_element = STEM_ELEMENTS.get(dy_stem)
            if ln_element and dy_element:
                element_rel = FortuneRelationAnalyzer._get_element_relation(ln_element, dy_element)
                result['element_relation'] = element_rel
        
        return result
    
    @staticmethod
    def _analyze_fortune_bazi(
        fortune: Dict,
        bazi_pillars: Dict,
        fortune_type: str = "流年"
    ) -> Dict[str, Any]:
        """
        分析流年/大运与八字四柱的关系
        
        Args:
            fortune: {"stem": "丁", "branch": "未"}
            bazi_pillars: 八字四柱
            fortune_type: "流年" 或 "大运"
        
        Returns:
            {
                "vs_day_pillar": "辰未相破",
                "vs_year_pillar": "无特殊关系",
                "vs_month_pillar": "无特殊关系",
                "vs_hour_pillar": "无特殊关系",
                "important_relations": ["与日柱辰未相破"]
            }
        """
        f_stem = fortune.get('stem', '')
        f_branch = fortune.get('branch', '')
        
        result = {}
        important_relations = []
        
        # 逐个分析与四柱的关系
        for pillar_name, pillar_label in [
            ('day', '日柱'),
            ('year', '年柱'),
            ('month', '月柱'),
            ('hour', '时柱')
        ]:
            pillar = bazi_pillars.get(pillar_name, {})
            p_stem = pillar.get('stem', '')
            p_branch = pillar.get('branch', '')
            
            relations = []
            
            # 天干关系
            if f_stem and p_stem:
                stem_rel = FortuneRelationAnalyzer._get_stem_relation(f_stem, p_stem)
                if "无特殊" not in stem_rel:
                    relations.append(f"天干{stem_rel}")
            
            # 地支关系
            if f_branch and p_branch:
                branch_rel = FortuneRelationAnalyzer._get_branch_relation(f_branch, p_branch)
                if "无特殊" not in branch_rel:
                    relations.append(f"地支{branch_rel}")
            
            # 记录结果
            if relations:
                result[f'vs_{pillar_name}_pillar'] = "、".join(relations)
                # 日柱关系最重要
                if pillar_name == 'day':
                    important_relations.append(f"与{pillar_label}{relations[0]}")
            else:
                result[f'vs_{pillar_name}_pillar'] = "无特殊关系"
        
        result['important_relations'] = important_relations
        
        return result
    
    @staticmethod
    def _get_stem_relation(stem1: str, stem2: str) -> str:
        """
        获取天干关系
        
        Returns:
            如 "甲己相合"、"甲乙比劫"、"甲庚相克"、"无特殊关系"
        """
        if not stem1 or not stem2:
            return "无特殊关系"
        
        # 天干合
        if STEM_HE.get(stem1) == stem2:
            return f"{stem1}{stem2}相合"
        
        # 同五行（比劫）
        elem1 = STEM_ELEMENTS.get(stem1)
        elem2 = STEM_ELEMENTS.get(stem2)
        
        if elem1 == elem2:
            return f"{stem1}{stem2}比劫并见"
        
        # 五行生克
        if elem1 and elem2:
            from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
            relations = WangShuaiAnalyzer.ELEMENT_RELATIONS.get(elem1, {})
            
            if relations.get('produces') == elem2:
                return f"{stem1}生{stem2}"
            elif relations.get('controls') == elem2:
                return f"{stem1}克{stem2}"
            elif relations.get('produced_by') == elem2:
                return f"{stem2}生{stem1}"
            elif relations.get('controlled_by') == elem2:
                return f"{stem2}克{stem1}"
        
        return "无特殊关系"
    
    @staticmethod
    def _get_branch_relation(branch1: str, branch2: str) -> str:
        """
        获取地支关系
        
        Returns:
            如 "子午相冲"、"子丑六合"、"寅巳相刑"、"子酉相破"、"无特殊关系"
        """
        if not branch1 or not branch2:
            return "无特殊关系"
        
        # 六冲
        if BRANCH_CHONG.get(branch1) == branch2:
            return f"{branch1}{branch2}相冲⚠️"
        
        # 六合
        if BRANCH_LIUHE.get(branch1) == branch2:
            return f"{branch1}{branch2}六合✅"
        
        # 刑
        if branch2 in BRANCH_XING.get(branch1, []):
            return f"{branch1}{branch2}相刑⚠️"
        
        # 害
        if branch2 in BRANCH_HAI.get(branch1, []):
            return f"{branch1}{branch2}相害⚠️"
        
        # 破
        if BRANCH_PO.get(branch1) == branch2:
            return f"{branch1}{branch2}相破⚠️"
        
        # 三合局（简化判断）
        for sanhe in BRANCH_SANHE_GROUPS:
            if branch1 in sanhe and branch2 in sanhe:
                return f"{branch1}{branch2}三合✅"
        
        # 五行生克
        elem1 = BRANCH_ELEMENTS.get(branch1)
        elem2 = BRANCH_ELEMENTS.get(branch2)
        
        if elem1 and elem2:
            from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
            relations = WangShuaiAnalyzer.ELEMENT_RELATIONS.get(elem1, {})
            
            if relations.get('produces') == elem2:
                return f"{branch1}生{branch2}"
            elif relations.get('controls') == elem2:
                return f"{branch1}克{branch2}"
        
        return "无特殊关系"
    
    @staticmethod
    def _get_element_relation(elem1: str, elem2: str) -> str:
        """
        获取五行关系
        
        Returns:
            如 "火生土"、"木克土"、"同属火"、"无特殊关系"
        """
        if not elem1 or not elem2:
            return "无特殊关系"
        
        if elem1 == elem2:
            return f"同属{elem1}"
        
        from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
        relations = WangShuaiAnalyzer.ELEMENT_RELATIONS.get(elem1, {})
        
        if relations.get('produces') == elem2:
            return f"{elem1}生{elem2}"
        elif relations.get('controls') == elem2:
            return f"{elem1}克{elem2}"
        elif relations.get('produced_by') == elem2:
            return f"{elem2}生{elem1}"
        elif relations.get('controlled_by') == elem2:
            return f"{elem2}克{elem1}"
        
        return "无特殊关系"
    
    @staticmethod
    def _generate_summary(result: Dict) -> str:
        """
        生成关系分析总结
        
        Args:
            result: 完整的关系分析结果
        
        Returns:
            总结文本
        """
        summary_parts = []
        
        # 流年vs大运
        liunian_dayun = result.get('liunian_dayun_relation', {})
        if liunian_dayun:
            if liunian_dayun.get('branch_relation'):
                summary_parts.append(liunian_dayun['branch_relation'])
        
        # 流年vs八字（重要关系）
        liunian_bazi = result.get('liunian_bazi_relation', {})
        if liunian_bazi.get('important_relations'):
            summary_parts.extend(liunian_bazi['important_relations'])
        
        if not summary_parts:
            return "无明显特殊关系"
        
        return "；".join(summary_parts)
    
    @staticmethod
    def _analyze_internal_relations(bazi_pillars: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        分析八字内部刑冲合害关系（新增）
        
        功能：
        - 检查四柱之间的刑冲合害破关系
        - 重点关注日柱与其他柱的关系（日柱代表自身和配偶宫）
        - 统计整体刑冲合害数量
        
        Args:
            bazi_pillars: 八字四柱
        
        Returns:
            {
                'has_chong': bool,           # 是否有冲
                'has_xing': bool,            # 是否有刑
                'has_he': bool,              # 是否有合
                'has_hai': bool,             # 是否有害
                'has_po': bool,              # 是否有破
                'chong_details': list,       # 冲的详情
                'xing_details': list,        # 刑的详情
                'he_details': list,          # 合的详情
                'hai_details': list,         # 害的详情
                'po_details': list,          # 破的详情
                'day_branch_chong': bool,    # 日支是否被冲
                'day_branch_xing': bool,     # 日支是否被刑
                'summary': str               # 总结
            }
        """
        # 提取所有地支
        branches = {}
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_name, {})
            branch = pillar.get('branch', '')
            if branch:
                branches[pillar_name] = branch
        
        # 初始化结果
        result = {
            'has_chong': False,
            'has_xing': False,
            'has_he': False,
            'has_hai': False,
            'has_po': False,
            'chong_details': [],
            'xing_details': [],
            'he_details': [],
            'hai_details': [],
            'po_details': [],
            'day_branch_chong': False,
            'day_branch_xing': False,
            'summary': ''
        }
        
        day_branch = branches.get('day', '')
        
        # 检查冲
        for p1_name, b1 in branches.items():
            for p2_name, b2 in branches.items():
                if p1_name >= p2_name:  # 避免重复检查
                    continue
                
                # 检查冲
                if BRANCH_CHONG.get(b1) == b2:
                    result['has_chong'] = True
                    result['chong_details'].append(f"{p1_name}柱{b1}与{p2_name}柱{b2}相冲")
                    if b1 == day_branch or b2 == day_branch:
                        result['day_branch_chong'] = True
                
                # 检查刑
                if b2 in BRANCH_XING.get(b1, []):
                    result['has_xing'] = True
                    result['xing_details'].append(f"{p1_name}柱{b1}刑{p2_name}柱{b2}")
                    if b1 == day_branch or b2 == day_branch:
                        result['day_branch_xing'] = True
                
                # 检查合
                if BRANCH_LIUHE.get(b1) == b2:
                    result['has_he'] = True
                    result['he_details'].append(f"{p1_name}柱{b1}与{p2_name}柱{b2}六合")
                
                # 检查害
                if b2 in BRANCH_HAI.get(b1, []):
                    result['has_hai'] = True
                    result['hai_details'].append(f"{p1_name}柱{b1}害{p2_name}柱{b2}")
                
                # 检查破
                if BRANCH_PO.get(b1) == b2:
                    result['has_po'] = True
                    result['po_details'].append(f"{p1_name}柱{b1}破{p2_name}柱{b2}")
        
        # 检查三合局
        branch_list = list(branches.values())
        for sanhe_group in BRANCH_SANHE_GROUPS:
            if all(b in branch_list for b in sanhe_group):
                result['has_he'] = True
                result['he_details'].append(f"三合{sanhe_group[0]}{sanhe_group[1]}{sanhe_group[2]}局")
        
        # 生成总结
        summary_parts = []
        if result['chong_details']:
            summary_parts.extend(result['chong_details'])
        if result['xing_details']:
            summary_parts.extend(result['xing_details'])
        if result['he_details']:
            summary_parts.extend(result['he_details'])
        if result['hai_details']:
            summary_parts.extend(result['hai_details'])
        if result['po_details']:
            summary_parts.extend(result['po_details'])
        
        result['summary'] = "；".join(summary_parts) if summary_parts else "八字内部无明显刑冲合害"
        
        return result


# 使用示例（仅供参考）
if __name__ == "__main__":
    # 测试数据：1987-09-16 05:00 男（日主戊土）
    bazi_pillars = {
        "year": {"stem": "丁", "branch": "卯"},
        "month": {"stem": "己", "branch": "酉"},
        "day": {"stem": "戊", "branch": "辰"},
        "hour": {"stem": "乙", "branch": "卯"}
    }
    liunian = {"stem": "丁", "branch": "未"}
    dayun = {"stem": "丙", "branch": "午"}
    
    result = FortuneRelationAnalyzer.analyze(bazi_pillars, liunian, dayun)
    
    print("=" * 80)
    print("流年大运关系分析测试")
    print("=" * 80)
    print(f"\n流年 vs 大运:")
    for key, value in result['liunian_dayun_relation'].items():
        print(f"  {key}: {value}")
    
    print(f"\n流年 vs 八字:")
    for key, value in result['liunian_bazi_relation'].items():
        if key != 'important_relations':
            print(f"  {key}: {value}")
    
    print(f"\n总结: {result['summary']}")
    print("=" * 80)


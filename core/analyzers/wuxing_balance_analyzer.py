#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行动态平衡分析器

功能：
- 计算八字原局五行统计
- 计算流年五行贡献
- 计算大运五行贡献
- 综合统计：八字 + 流年 + 大运
- 判断：哪个五行过旺/过弱

设计原则：
- 复用现有模块（src/data/constants.py）
- 独立模块，可被其他服务调用
- 微服务思维，单一职责
"""

import logging
from typing import Dict, List, Any, Optional
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS

logger = logging.getLogger(__name__)


class WuxingBalanceAnalyzer:
    """五行动态平衡分析器"""
    
    # 地支五行权重（考虑藏干，本气为主）
    # 权重说明：本气=2，中气=0.5，余气=0.3
    BRANCH_ELEMENT_WEIGHTS = {
        # 四正（本气纯粹）
        '子': {'水': 2.0},
        '午': {'火': 2.0},
        '卯': {'木': 2.0},
        '酉': {'金': 2.0},
        
        # 四生（本气+中气+余气）
        '寅': {'木': 1.5, '火': 0.5, '土': 0.3},  # 寅藏甲丙戊
        '申': {'金': 1.5, '水': 0.5, '土': 0.3},  # 申藏庚壬戊
        '巳': {'火': 1.5, '金': 0.5, '土': 0.3},  # 巳藏丙庚戊
        '亥': {'水': 1.5, '木': 0.5},             # 亥藏壬甲
        
        # 四墓（杂气）
        '辰': {'土': 1.5, '木': 0.5, '水': 0.3},  # 辰藏戊乙癸
        '戌': {'土': 1.5, '金': 0.5, '火': 0.3},  # 戌藏戊辛丁
        '丑': {'土': 1.5, '水': 0.5, '金': 0.3},  # 丑藏己癸辛
        '未': {'土': 1.5, '火': 0.5, '木': 0.3},  # 未藏己丁乙
    }
    
    # 五行旺衰阈值
    BALANCE_THRESHOLDS = {
        'very_strong': 5.0,   # 极旺（>=5）
        'strong': 3.5,        # 偏旺（3.5-5）
        'balanced': 2.0,      # 中和（2-3.5）
        'weak': 1.0,          # 偏弱（1-2）
        # 极弱（<1）
    }
    
    @staticmethod
    def analyze(
        bazi_elements: Dict[str, int],
        liunian: Dict[str, str],
        dayun: Optional[Dict[str, str]] = None,
        tiaohou: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析五行动态平衡（含调候分析）
        
        Args:
            bazi_elements: 八字原局五行统计，如 {"金": 1, "木": 3, "水": 0, "火": 1, "土": 3}
            liunian: 流年信息，如 {"stem": "丁", "branch": "未", "year": 2027}
            dayun: 大运信息（可选），如 {"stem": "丙", "branch": "午"}
            tiaohou: 调候信息（可选），如 {"tiaohou_element": "水", "season": "夏季"}
        
        Returns:
            {
                "bazi_elements": {...},          # 八字五行
                "liunian_elements": {...},       # 流年五行贡献
                "dayun_elements": {...},         # 大运五行贡献（如有）
                "combined_elements": {...},      # 综合五行
                "analysis": {
                    "strong_elements": ["火", "土"],
                    "weak_elements": ["水"],
                    "balanced_elements": ["金", "木"],
                    "summary": "火土过旺，水严重不足",
                    "tiaohou_analysis": {...}    # 调候分析（新增）
                }
            }
        """
        try:
            # 1. 计算流年五行（使用权重）
            liunian_elements = WuxingBalanceAnalyzer._calculate_ganzhi_elements(
                liunian.get('stem', ''),
                liunian.get('branch', '')
            )
            logger.info(f"流年{liunian.get('stem')}{liunian.get('branch')}五行: {liunian_elements}")
            
            # 2. 计算大运五行（如有）
            dayun_elements = {}
            if dayun and dayun.get('stem') and dayun.get('branch'):
                dayun_elements = WuxingBalanceAnalyzer._calculate_ganzhi_elements(
                    dayun.get('stem', ''),
                    dayun.get('branch', '')
                )
                logger.info(f"大运{dayun.get('stem')}{dayun.get('branch')}五行: {dayun_elements}")
            
            # 3. 综合统计（八字 + 流年 + 大运）
            combined_elements = WuxingBalanceAnalyzer._combine_elements(
                bazi_elements,
                liunian_elements,
                dayun_elements
            )
            
            # 4. 判断旺弱
            analysis = WuxingBalanceAnalyzer._analyze_balance(combined_elements)
            
            # 5. 调候分析（新增）
            if tiaohou and tiaohou.get('tiaohou_element'):
                tiaohou_analysis = WuxingBalanceAnalyzer._analyze_tiaohou(
                    tiaohou,
                    bazi_elements,
                    liunian_elements,
                    dayun_elements,
                    combined_elements
                )
                analysis['tiaohou_analysis'] = tiaohou_analysis
                logger.info(f"调候分析: {tiaohou_analysis.get('status')}")
            
            return {
                "bazi_elements": bazi_elements,
                "liunian_elements": liunian_elements,
                "dayun_elements": dayun_elements,
                "combined_elements": combined_elements,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"五行平衡分析失败: {e}")
            return {
                "bazi_elements": bazi_elements,
                "liunian_elements": {},
                "dayun_elements": {},
                "combined_elements": bazi_elements,
                "analysis": {
                    "strong_elements": [],
                    "weak_elements": [],
                    "balanced_elements": [],
                    "summary": "分析失败"
                }
            }
    
    @staticmethod
    def _calculate_ganzhi_elements(stem: str, branch: str) -> Dict[str, float]:
        """
        计算天干地支的五行贡献（带权重）
        
        Args:
            stem: 天干，如 "丁"
            branch: 地支，如 "未"
        
        Returns:
            {"火": 1.5, "土": 1.8} - 五行及其权重
        """
        elements = {}
        
        # 天干五行（权重=1）
        if stem and stem in STEM_ELEMENTS:
            stem_element = STEM_ELEMENTS[stem]
            elements[stem_element] = elements.get(stem_element, 0) + 1.0
        
        # 地支五行（使用权重表）
        if branch and branch in WuxingBalanceAnalyzer.BRANCH_ELEMENT_WEIGHTS:
            branch_weights = WuxingBalanceAnalyzer.BRANCH_ELEMENT_WEIGHTS[branch]
            for element, weight in branch_weights.items():
                elements[element] = elements.get(element, 0) + weight
        
        return elements
    
    @staticmethod
    def _combine_elements(
        bazi_elements: Dict[str, int],
        liunian_elements: Dict[str, float],
        dayun_elements: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        综合计算五行（八字 + 流年 + 大运）
        
        Args:
            bazi_elements: 八字五行（整数）
            liunian_elements: 流年五行（浮点数，带权重）
            dayun_elements: 大运五行（可选）
        
        Returns:
            综合五行统计，如 {"金": 1.0, "木": 3.0, "水": 0.0, "火": 4.5, "土": 4.8}
        """
        combined = {}
        
        # 初始化五行（确保所有五行都有值）
        for element in ['木', '火', '土', '金', '水']:
            combined[element] = 0.0
        
        # 加上八字五行
        for element, count in bazi_elements.items():
            combined[element] += count
        
        # 加上流年五行
        for element, weight in liunian_elements.items():
            combined[element] += weight
        
        # 加上大运五行（如有）
        if dayun_elements:
            for element, weight in dayun_elements.items():
                combined[element] += weight
        
        return combined
    
    @staticmethod
    def _analyze_balance(combined_elements: Dict[str, float]) -> Dict[str, Any]:
        """
        分析五行平衡状态
        
        Args:
            combined_elements: 综合五行统计
        
        Returns:
            {
                "strong_elements": ["火", "土"],
                "weak_elements": ["水"],
                "balanced_elements": ["金", "木"],
                "summary": "火土过旺，水严重不足"
            }
        """
        strong_elements = []
        weak_elements = []
        balanced_elements = []
        
        thresholds = WuxingBalanceAnalyzer.BALANCE_THRESHOLDS
        
        for element, value in combined_elements.items():
            if value >= thresholds['very_strong']:
                strong_elements.append(f"{element}(极旺)")
            elif value >= thresholds['strong']:
                strong_elements.append(f"{element}(偏旺)")
            elif value >= thresholds['balanced']:
                balanced_elements.append(f"{element}(中和)")
            elif value >= thresholds['weak']:
                weak_elements.append(f"{element}(偏弱)")
            else:
                weak_elements.append(f"{element}(极弱)")
        
        # 生成总结
        summary_parts = []
        if strong_elements:
            summary_parts.append(f"{','.join(strong_elements)}过旺")
        if weak_elements:
            summary_parts.append(f"{','.join(weak_elements)}不足")
        if not summary_parts:
            summary_parts.append("五行相对平衡")
        
        summary = "；".join(summary_parts)
        
        return {
            "strong_elements": strong_elements,
            "weak_elements": weak_elements,
            "balanced_elements": balanced_elements,
            "summary": summary
        }
    
    @staticmethod
    def format_elements_for_display(elements: Dict[str, float]) -> str:
        """
        格式化五行数据为展示文本
        
        Args:
            elements: 五行统计，如 {"金": 1.0, "木": 3.0, ...}
        
        Returns:
            "木3.0 火4.5 土4.8 金1.0 水0.0"
        """
        order = ['木', '火', '土', '金', '水']
        parts = []
        for element in order:
            value = elements.get(element, 0)
            # 如果是整数，不显示小数点
            if value == int(value):
                parts.append(f"{element}{int(value)}")
            else:
                parts.append(f"{element}{value:.1f}")
        return " ".join(parts)
    
    @staticmethod
    def _analyze_tiaohou(
        tiaohou: Dict[str, Any],
        bazi_elements: Dict[str, int],
        liunian_elements: Dict[str, float],
        dayun_elements: Dict[str, float],
        combined_elements: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        分析调候平衡情况
        
        Args:
            tiaohou: 调候信息
            bazi_elements: 八字五行
            liunian_elements: 流年五行
            dayun_elements: 大运五行
            combined_elements: 综合五行
        
        Returns:
            {
                'tiaohou_element': str,      # 调候五行
                'season': str,               # 季节
                'bazi_count': int,           # 八字中调候五行数量
                'liunian_brings': float,     # 流年带来的调候五行
                'dayun_brings': float,       # 大运带来的调候五行
                'total_count': float,        # 总计调候五行
                'status': str,               # 调候状态：'严重不足'/'不足'/'适中'/'充足'
                'analysis': str,             # 分析说明
                'suggestions': list          # 建议
            }
        """
        tiaohou_element = tiaohou.get('tiaohou_element')
        season = tiaohou.get('season', '')
        
        # 统计各层面的调候五行数量
        bazi_count = bazi_elements.get(tiaohou_element, 0)
        liunian_brings = liunian_elements.get(tiaohou_element, 0)
        dayun_brings = dayun_elements.get(tiaohou_element, 0) if dayun_elements else 0
        total_count = combined_elements.get(tiaohou_element, 0)
        
        # 判断调候状态
        if total_count == 0:
            status = '严重不足'
            analysis = f"{season}生人，命局缺{tiaohou_element}，调候严重失衡，易受气候影响"
            suggestions = [
                f"急需补充{tiaohou_element}元素",
                f"生活中多接触{tiaohou_element}相关事物",
                "注意季节变化对健康的影响"
            ]
        elif total_count < 1.5:
            status = '不足'
            analysis = f"{season}生人，命局{tiaohou_element}不足，调候欠佳"
            suggestions = [
                f"适当补充{tiaohou_element}元素",
                "注意气候调节"
            ]
        elif total_count < 3.0:
            status = '适中'
            analysis = f"{season}生人，命局{tiaohou_element}适中，调候基本平衡"
            suggestions = [
                "调候良好，保持现状"
            ]
        else:
            status = '充足'
            analysis = f"{season}生人，命局{tiaohou_element}充足，调候得当"
            suggestions = [
                "调候平衡，气候适应力强"
            ]
        
        # 流年大运对调候的影响
        if liunian_brings > 0:
            analysis += f"，流年补充{tiaohou_element}{liunian_brings:.1f}"
            suggestions.append(f"今年流年带来{tiaohou_element}，有利调候")
        
        if dayun_brings > 0:
            analysis += f"，大运补充{tiaohou_element}{dayun_brings:.1f}"
            suggestions.append(f"当前大运带来{tiaohou_element}，长期有利")
        
        return {
            'tiaohou_element': tiaohou_element,
            'season': season,
            'bazi_count': bazi_count,
            'liunian_brings': liunian_brings,
            'dayun_brings': dayun_brings,
            'total_count': total_count,
            'status': status,
            'analysis': analysis,
            'suggestions': suggestions
        }


# 使用示例（仅供参考）
if __name__ == "__main__":
    # 测试数据：1987-09-16 05:00 男（日主戊土）
    bazi_elements = {"金": 1, "木": 3, "水": 0, "火": 1, "土": 3}
    liunian = {"stem": "丁", "branch": "未", "year": 2027}
    dayun = {"stem": "丙", "branch": "午"}
    
    result = WuxingBalanceAnalyzer.analyze(bazi_elements, liunian, dayun)
    
    print("=" * 80)
    print("五行动态平衡分析测试")
    print("=" * 80)
    print(f"\n八字五行: {WuxingBalanceAnalyzer.format_elements_for_display(result['bazi_elements'])}")
    print(f"流年五行贡献: {WuxingBalanceAnalyzer.format_elements_for_display(result['liunian_elements'])}")
    print(f"大运五行贡献: {WuxingBalanceAnalyzer.format_elements_for_display(result['dayun_elements'])}")
    print(f"\n综合五行: {WuxingBalanceAnalyzer.format_elements_for_display(result['combined_elements'])}")
    print(f"\n分析结果: {result['analysis']['summary']}")
    print("=" * 80)


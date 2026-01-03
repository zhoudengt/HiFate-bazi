#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字前端展示服务 - 提供前端友好的数据格式
"""

import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.bazi_detail_service import BaziDetailService

# 导入常量
from src.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from src.data.stems_branches import STEM_YINYANG, BRANCH_YINYANG


class BaziDisplayService:
    """八字前端展示服务"""
    
    @staticmethod
    def get_pan_display(solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """
        获取排盘数据（前端优化格式）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            
        Returns:
            dict: 前端友好的排盘数据
        """
        # 调用现有服务（不修改）
        bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
        if not bazi_result:
            return {"success": False, "error": "八字计算失败"}
        
        bazi_data = bazi_result.get('bazi', {})
        
        # 先格式化四柱数据
        formatted_pillars = BaziDisplayService._format_pillars_for_display(bazi_data)
        
        # ✅ 获取日柱解析（性格与命运解析）
        rizhu_analysis = None
        try:
            from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            analyzer = RizhuGenderAnalyzer(bazi_pillars, gender)
            analysis_result = analyzer.analyze_rizhu_gender()
            if analysis_result.get('has_data'):
                rizhu_analysis = {
                    "rizhu": analysis_result.get('rizhu', ''),
                    "gender": analysis_result.get('gender', ''),
                    "descriptions": analysis_result.get('descriptions', []),
                    "summary": analysis_result.get('summary', '')
                }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"获取日柱解析失败: {e}")
        
        # ✅ 获取婚姻规则
        marriage_rules = []
        try:
            from server.services.rule_service import RuleService
            # 构建规则匹配数据
            rule_data = {
                'basic_info': bazi_data.get('basic_info', {}),
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                'details': bazi_data.get('details', {}),
                'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
                'elements': bazi_data.get('elements', {}),
                'element_counts': bazi_data.get('element_counts', {}),
                'relationships': bazi_data.get('relationships', {})
            }
            # 匹配所有规则
            all_rules = RuleService.match_rules(rule_data, rule_types=None, use_cache=True)
            # 筛选婚姻相关规则（rule_type 包含 'marriage' 或 '婚'）
            marriage_rules_all = [
                rule for rule in all_rules 
                if 'marriage' in str(rule.get('rule_type', '')).lower() or '婚' in str(rule.get('rule_type', ''))
            ]
            
            # ✅ 规则优化：按优先级排序（不限制数量，显示所有匹配的规则）
            marriage_rules = sorted(
                marriage_rules_all, 
                key=lambda x: x.get('priority', 0), 
                reverse=True
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"获取婚姻规则失败: {e}")
        
        # 格式化为前端友好格式
        return {
            "success": True,
            "pan": {
                "basic": bazi_data.get('basic_info', {}),
                "pillars": formatted_pillars,
                "wuxing": BaziDisplayService._format_wuxing_for_display(bazi_data, formatted_pillars),
                "rizhu_analysis": rizhu_analysis,  # ✅ 添加日柱解析
                "marriage_rules": marriage_rules  # ✅ 添加婚姻规则
            }
        }
    
    @staticmethod
    def get_dayun_display(solar_date: str, solar_time: str, gender: str, 
                          current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取大运数据（前端优化格式）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            current_time: 当前时间（可选）
            
        Returns:
            dict: 前端友好的大运数据
        """
        # 调用现有服务（不修改）
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender, current_time
        )
        if not detail_result:
            return {"success": False, "error": "详细计算失败"}
        
        details = detail_result.get('details', {})
        dayun_sequence = details.get('dayun_sequence', [])
        dayun_info = details.get('dayun', {})
        qiyun_info = details.get('qiyun', {})
        jiaoyun_info = details.get('jiaoyun', {})
        
        # 确定当前大运
        current_dayun = None
        if current_time:
            current_year = current_time.year
            birth_year = int(solar_date.split('-')[0])
            current_age = current_year - birth_year + 1  # 虚岁计算
            
            for dayun in dayun_sequence:
                age_range = dayun.get('age_range', {})
                if age_range:
                    age_start = age_range.get('start', 0)
                    age_end = age_range.get('end', 0)
                    if age_start <= current_age <= age_end:
                        current_dayun = dayun
                        break
        
        # 格式化大运列表，标记当前大运
        formatted_dayun_list = []
        for dayun in dayun_sequence:
            formatted = BaziDisplayService._format_dayun_item(dayun)
            if current_dayun and dayun.get('step') == current_dayun.get('step'):
                formatted['is_current'] = True
            formatted_dayun_list.append(formatted)
        
        return {
            "success": True,
            "dayun": {
                "current": BaziDisplayService._format_dayun_item(current_dayun or dayun_info),
                "list": formatted_dayun_list,
                "qiyun": {
                    "date": qiyun_info.get('date', ''),
                    "age_display": qiyun_info.get('age_display', ''),
                    "description": qiyun_info.get('description', '')
                },
                "jiaoyun": {
                    "date": jiaoyun_info.get('date', ''),
                    "age_display": jiaoyun_info.get('age_display', ''),
                    "description": jiaoyun_info.get('description', '')
                }
            }
        }
    
    @staticmethod
    def get_liunian_display(solar_date: str, solar_time: str, gender: str,
                            year_range: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        获取流年数据（前端优化格式）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            year_range: 年份范围 {"start": 2020, "end": 2030}，可选
            
        Returns:
            dict: 前端友好的流年数据
        """
        # 调用现有服务（不修改）
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender
        )
        if not detail_result:
            return {"success": False, "error": "详细计算失败"}
        
        details = detail_result.get('details', {})
        liunian_sequence = details.get('liunian_sequence', [])
        liunian_info = details.get('liunian', {})
        
        # 如果指定了年份范围，过滤流年
        if year_range:
            start_year = year_range.get('start')
            end_year = year_range.get('end')
            liunian_sequence = [
                l for l in liunian_sequence 
                if start_year <= l.get('year', 0) <= end_year
            ]
        
        # 确定当前流年
        from datetime import datetime
        current_year = datetime.now().year
        current_liunian = None
        for liunian in liunian_sequence:
            if liunian.get('year') == current_year:
                current_liunian = liunian
                break
        
        # 格式化流年列表，标记当前流年
        formatted_liunian_list = []
        for liunian in liunian_sequence:
            formatted = BaziDisplayService._format_liunian_item(liunian)
            if current_liunian and liunian.get('year') == current_liunian.get('year'):
                formatted['is_current'] = True
            formatted_liunian_list.append(formatted)
        
        return {
            "success": True,
            "liunian": {
                "current": BaziDisplayService._format_liunian_item(current_liunian or liunian_info),
                "list": formatted_liunian_list
            }
        }
    
    @staticmethod
    def get_liuyue_display(solar_date: str, solar_time: str, gender: str,
                           target_year: Optional[int] = None) -> Dict[str, Any]:
        """
        获取流月数据（前端优化格式）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            target_year: 目标年份（可选），用于计算该年份的流月，默认为当前年份
            
        Returns:
            dict: 前端友好的流月数据
        """
        # 调用现有服务（不修改）
        detail_result = BaziDetailService.calculate_detail_full(
            solar_date, solar_time, gender
        )
        if not detail_result:
            return {"success": False, "error": "详细计算失败"}
        
        details = detail_result.get('details', {})
        
        # 从流年序列中获取流月
        liunian_sequence = details.get('liunian_sequence', [])
        
        # 如果指定了目标年份，找到对应年份的流年
        if target_year:
            target_liunian = None
            for liunian in liunian_sequence:
                if liunian.get('year') == target_year:
                    target_liunian = liunian
                    break
            
            if target_liunian:
                # 使用该流年的流月序列
                liuyue_sequence = target_liunian.get('liuyue_sequence', [])
            else:
                # 如果没有找到，使用当前流年的流月序列
                from datetime import datetime
                current_year = datetime.now().year
                current_liunian = None
                for liunian in liunian_sequence:
                    if liunian.get('year') == current_year:
                        current_liunian = liunian
                        break
                if current_liunian:
                    liuyue_sequence = current_liunian.get('liuyue_sequence', [])
                else:
                    # 如果还是没有，使用 details 中的流月序列
                    liuyue_sequence = details.get('liuyue_sequence', [])
        else:
            # 使用当前流年的流月序列
            from datetime import datetime
            current_year = datetime.now().year
            current_liunian = None
            for liunian in liunian_sequence:
                if liunian.get('year') == current_year:
                    current_liunian = liunian
                    break
            if current_liunian:
                liuyue_sequence = current_liunian.get('liuyue_sequence', [])
            else:
                # 如果还是没有，使用 details 中的流月序列
                liuyue_sequence = details.get('liuyue_sequence', [])
        
        # 确定当前流月
        from datetime import datetime
        current_month = datetime.now().month
        current_liuyue = None
        for liuyue in liuyue_sequence:
            if liuyue.get('month') == current_month:
                current_liuyue = liuyue
                break
        
        # 格式化流月列表，标记当前流月
        formatted_liuyue_list = []
        for liuyue in liuyue_sequence:
            formatted = BaziDisplayService._format_liuyue_item(liuyue)
            if current_liuyue and liuyue.get('month') == current_liuyue.get('month'):
                formatted['is_current'] = True
            formatted_liuyue_list.append(formatted)
        
        return {
            "success": True,
            "liuyue": {
                "current": BaziDisplayService._format_liuyue_item(current_liuyue or (liuyue_sequence[0] if liuyue_sequence else {})),
                "list": formatted_liuyue_list,
                "target_year": target_year
            }
        }
    
    @staticmethod
    def _format_pillars_for_display(bazi_data: Dict[str, Any]) -> list:
        """将四柱数据格式化为数组格式（前端友好）"""
        pillars = []
        pillar_types = [
            {"type": "year", "label": "年柱"},
            {"type": "month", "label": "月柱"},
            {"type": "day", "label": "日柱"},
            {"type": "hour", "label": "时柱"}
        ]
        
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        details = bazi_data.get('details', {})
        
        for pillar_info in pillar_types:
            pillar_type = pillar_info['type']
            pillar = bazi_pillars.get(pillar_type, {})
            pillar_detail = details.get(pillar_type, {})
            
            stem_char = pillar.get('stem', '')
            branch_char = pillar.get('branch', '')
            
            pillars.append({
                "type": pillar_type,
                "label": pillar_info['label'],
                "stem": {
                    "char": stem_char,
                    "wuxing": STEM_ELEMENTS.get(stem_char, ''),
                    "yinyang": STEM_YINYANG.get(stem_char, ''),
                    "ten_god": pillar_detail.get('main_star', '')
                },
                "branch": {
                    "char": branch_char,
                    "wuxing": BRANCH_ELEMENTS.get(branch_char, ''),
                    "yinyang": BRANCH_YINYANG.get(branch_char, ''),
                    "hidden_stems": [
                        {
                            "char": h if isinstance(h, str) else (h.get('char', '') if isinstance(h, dict) else ''),  # ✅ 修复：保留完整藏干字符串（如"己土"）
                            "wuxing": STEM_ELEMENTS.get(h[0] if isinstance(h, str) and len(h) > 0 else (h.get('char', '')[0] if isinstance(h, dict) and h.get('char') else ''), ''),
                            "yinyang": STEM_YINYANG.get(h[0] if isinstance(h, str) and len(h) > 0 else (h.get('char', '')[0] if isinstance(h, dict) and h.get('char') else ''), ''),
                            "ten_god": (pillar_detail.get('hidden_stars', [])[idx] 
                                       if isinstance(pillar_detail.get('hidden_stars'), list) 
                                       and idx < len(pillar_detail.get('hidden_stars', []))
                                       else '')
                        }
                        for idx, h in enumerate(pillar_detail.get('hidden_stems', []))
                    ]
                },
                "main_star": pillar_detail.get('main_star', ''),  # ✅ 添加主星
                "hidden_stars": pillar_detail.get('hidden_stars', []),  # ✅ 添加副星（用于副星行）
                "star_fortune": pillar_detail.get('star_fortune', ''),  # ✅ 添加星运
                "self_sitting": pillar_detail.get('self_sitting', ''),  # ✅ 添加自坐
                "kongwang": pillar_detail.get('kongwang', ''),  # ✅ 添加空亡
                "nayin": pillar_detail.get('nayin', ''),
                "deities": pillar_detail.get('deities', [])
            })
        
        return pillars
    
    @staticmethod
    def _format_wuxing_for_display(bazi_data: Dict[str, Any], formatted_pillars: list = None) -> Dict[str, Any]:
        """格式化五行数据（前端友好）"""
        # 优先从格式化后的四柱数据中计算
        if formatted_pillars:
            element_counts = BaziDisplayService._calculate_wuxing_from_formatted_pillars(formatted_pillars)
        else:
            # 尝试从多个可能的字段获取 element_counts
            element_counts = bazi_data.get('element_counts', {})
            
            # 如果 element_counts 为空，尝试从其他地方获取
            if not element_counts or sum(element_counts.values()) == 0:
                # 尝试从 bazi_data 的根级别获取
                if 'element_counts' in bazi_data:
                    element_counts = bazi_data['element_counts']
                # 如果还是没有，尝试从 elements 字段计算
                elif 'elements' in bazi_data:
                    elements = bazi_data['elements']
                    if isinstance(elements, dict):
                        # 将 elements 转换为 element_counts 格式
                        element_counts = {
                            'wood': elements.get('wood', 0),
                            'fire': elements.get('fire', 0),
                            'earth': elements.get('earth', 0),
                            'metal': elements.get('metal', 0),
                            'water': elements.get('water', 0)
                        }
            
            # 如果仍然为空，从四柱数据中计算
            if not element_counts or sum(element_counts.values()) == 0:
                element_counts = BaziDisplayService._calculate_wuxing_from_pillars(bazi_data)
        
        total = sum(element_counts.values()) if element_counts else 1
        
        wuxing_names = {
            'wood': '木',
            'fire': '火',
            'earth': '土',
            'metal': '金',
            'water': '水'
        }
        
        result = {}
        for key, name in wuxing_names.items():
            count = element_counts.get(key, 0)
            # 确保 count 是整数
            try:
                count = int(count) if count is not None else 0
            except (ValueError, TypeError):
                count = 0
            result[key] = {
                "name": name,
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0
            }
        
        return result
    
    @staticmethod
    def _calculate_wuxing_from_pillars(bazi_data: Dict[str, Any]) -> Dict[str, Any]:
        """从四柱数据中计算五行统计"""
        element_counts = {
            'wood': 0,
            'fire': 0,
            'earth': 0,
            'metal': 0,
            'water': 0
        }
        
        # 五行映射
        wuxing_map = {
            '木': 'wood',
            '火': 'fire',
            '土': 'earth',
            '金': 'metal',
            '水': 'water'
        }
        
        # 从四柱中统计
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            if isinstance(pillar, dict):
                # 统计天干
                stem_wuxing = pillar.get('stem', {}).get('wuxing', '') if isinstance(pillar.get('stem'), dict) else ''
                if stem_wuxing and stem_wuxing in wuxing_map:
                    element_counts[wuxing_map[stem_wuxing]] += 1
                
                # 统计地支
                branch_wuxing = pillar.get('branch', {}).get('wuxing', '') if isinstance(pillar.get('branch'), dict) else ''
                if branch_wuxing and branch_wuxing in wuxing_map:
                    element_counts[wuxing_map[branch_wuxing]] += 1
                
                # 统计藏干
                hidden_stems = pillar.get('branch', {}).get('hidden_stems', []) if isinstance(pillar.get('branch'), dict) else []
                if isinstance(hidden_stems, list):
                    for hidden_stem in hidden_stems:
                        if isinstance(hidden_stem, dict):
                            hidden_wuxing = hidden_stem.get('wuxing', '')
                            if hidden_wuxing and hidden_wuxing in wuxing_map:
                                element_counts[wuxing_map[hidden_wuxing]] += 1
        
        return element_counts
    
    @staticmethod
    def _calculate_wuxing_from_formatted_pillars(formatted_pillars: list) -> Dict[str, Any]:
        """从格式化后的四柱数据中计算五行统计"""
        element_counts = {
            'wood': 0,
            'fire': 0,
            'earth': 0,
            'metal': 0,
            'water': 0
        }
        
        # 五行映射
        wuxing_map = {
            '木': 'wood',
            '火': 'fire',
            '土': 'earth',
            '金': 'metal',
            '水': 'water'
        }
        
        # 从格式化后的四柱中统计
        for pillar in formatted_pillars:
            # 统计天干
            stem_wuxing = pillar.get('stem', {}).get('wuxing', '')
            if stem_wuxing and stem_wuxing in wuxing_map:
                element_counts[wuxing_map[stem_wuxing]] += 1
            
            # 统计地支
            branch_wuxing = pillar.get('branch', {}).get('wuxing', '')
            if branch_wuxing and branch_wuxing in wuxing_map:
                element_counts[wuxing_map[branch_wuxing]] += 1
            
            # 统计藏干
            hidden_stems = pillar.get('branch', {}).get('hidden_stems', [])
            if isinstance(hidden_stems, list):
                for hidden_stem in hidden_stems:
                    if isinstance(hidden_stem, dict):
                        hidden_wuxing = hidden_stem.get('wuxing', '')
                        if hidden_wuxing and hidden_wuxing in wuxing_map:
                            element_counts[wuxing_map[hidden_wuxing]] += 1
        
        return element_counts
    
    @staticmethod
    def _format_dayun_item(dayun: Dict[str, Any]) -> Dict[str, Any]:
        """格式化单个大运项"""
        if not dayun:
            return {}
        
        stem = dayun.get('stem', '')
        branch = dayun.get('branch', '')
        ganzhi = stem + branch if stem and branch else ''
        
        age_range = dayun.get('age_range', {})
        if not age_range:
            # 从 age_display 解析
            age_display = dayun.get('age_display', '')
            if age_display:
                import re
                match = re.match(r'(\d+)-(\d+)岁', age_display)
                if match:
                    age_range = {"start": int(match.group(1)), "end": int(match.group(2))}
                else:
                    # 支持"10岁"格式（大运，只显示起始年龄）
                    match = re.match(r'(\d+)岁', age_display)
                    if match:
                        age_val = int(match.group(1))
                        # 大运：起始年龄到起始年龄+9岁
                        age_range = {"start": age_val, "end": age_val + 9}
        
        # ✅ 添加详细信息（用于细盘表格）
        # ✅ 添加五行属性（由后端计算，前端只负责展示）
        return {
            "index": dayun.get('step', 0),
            "ganzhi": ganzhi,
            "stem": {
                "char": stem,
                "wuxing": STEM_ELEMENTS.get(stem, '')  # ✅ 后端提供五行属性
            },
            "branch": {
                "char": branch,
                "wuxing": BRANCH_ELEMENTS.get(branch, '')  # ✅ 后端提供五行属性
            },
            "age_range": age_range or {"start": 0, "end": 0},
            "age_display": dayun.get('age_display', ''),
            "year_range": {
                "start": dayun.get('year_start', 0),
                "end": dayun.get('year_end', 0)
            },
            "nayin": dayun.get('nayin', ''),
            "main_star": dayun.get('main_star', ''),
            "hidden_stems": dayun.get('hidden_stems', []),
            "hidden_stars": dayun.get('hidden_stars', []),
            "star_fortune": dayun.get('star_fortune', ''),
            "self_sitting": dayun.get('self_sitting', ''),
            "kongwang": dayun.get('kongwang', ''),
            "deities": dayun.get('deities', []),
            "is_current": False  # 由调用方设置
        }
    
    @staticmethod
    def _format_liunian_item(liunian: Dict[str, Any]) -> Dict[str, Any]:
        """格式化单个流年项"""
        if not liunian:
            return {}
        
        stem = liunian.get('stem', '')
        branch = liunian.get('branch', '')
        ganzhi = stem + branch if stem and branch else ''
        
        # ✅ 添加详细信息（用于细盘表格）
        # ✅ 添加五行属性（由后端计算，前端只负责展示）
        return {
            "year": liunian.get('year', 0),
            "age": liunian.get('age', 0),  # 新增字段
            "age_display": liunian.get('age_display', ''),  # 新增字段
            "ganzhi": ganzhi,
            "stem": {
                "char": stem,
                "wuxing": STEM_ELEMENTS.get(stem, '')  # ✅ 后端提供五行属性
            },
            "branch": {
                "char": branch,
                "wuxing": BRANCH_ELEMENTS.get(branch, '')  # ✅ 后端提供五行属性
            },
            "nayin": liunian.get('nayin', ''),
            "main_star": liunian.get('main_star', ''),
            "hidden_stems": liunian.get('hidden_stems', []),
            "hidden_stars": liunian.get('hidden_stars', []),
            "star_fortune": liunian.get('star_fortune', ''),
            "self_sitting": liunian.get('self_sitting', ''),
            "kongwang": liunian.get('kongwang', ''),
            "deities": liunian.get('deities', []),
            "relations": liunian.get('relations', []),  # 新增：关系列表
            "is_current": False  # 由调用方设置
        }
    
    @staticmethod
    def _format_liuyue_item(liuyue: Dict[str, Any]) -> Dict[str, Any]:
        """格式化单个流月项"""
        if not liuyue:
            return {}
        
        stem = liuyue.get('stem', '')
        branch = liuyue.get('branch', '')
        ganzhi = stem + branch if stem and branch else ''
        
        # ✅ 添加五行属性（由后端计算，前端只负责展示）
        return {
            "month": liuyue.get('month', 0),
            "solar_term": liuyue.get('solar_term', ''),
            "term_date": liuyue.get('term_date', ''),
            "ganzhi": ganzhi,
            "stem": {
                "char": stem,
                "wuxing": STEM_ELEMENTS.get(stem, '')  # ✅ 后端提供五行属性
            },
            "branch": {
                "char": branch,
                "wuxing": BRANCH_ELEMENTS.get(branch, '')  # ✅ 后端提供五行属性
            },
            "nayin": liuyue.get('nayin', ''),
            "is_current": False  # 由调用方设置
        }
    
    # Redis缓存TTL（30天，大运流年流月数据不随时间变化）
    CACHE_TTL = 2592000  # 30天
    
    @staticmethod
    def _generate_fortune_cache_key(solar_date: str, solar_time: str, gender: str,
                                     current_time: Optional[datetime] = None,
                                     dayun_index: Optional[int] = None,
                                     dayun_year_start: Optional[int] = None,
                                     dayun_year_end: Optional[int] = None,
                                     target_year: Optional[int] = None) -> str:
        """
        生成大运流年流月缓存键
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            current_time: 当前时间（可选）
            dayun_index: 大运索引（可选）
            dayun_year_start: 大运起始年份（可选）
            dayun_year_end: 大运结束年份（可选）
            target_year: 目标年份（可选）
            
        Returns:
            str: 缓存键
        """
        # 生成键（格式：fortune_display:{solar_date}:{solar_time}:{gender}:{current_time}:{dayun_index}:{dayun_year_start}:{dayun_year_end}:{target_year}）
        key_parts = [
            'fortune_display',
            solar_date,
            solar_time,
            gender,
            current_time.strftime('%Y-%m-%d %H:%M') if current_time else '',
            str(dayun_index) if dayun_index is not None else '',
            str(dayun_year_start) if dayun_year_start is not None else '',
            str(dayun_year_end) if dayun_year_end is not None else '',
            str(target_year) if target_year is not None else ''
        ]
        return ':'.join(key_parts)
    
    @staticmethod
    def get_fortune_display(solar_date: str, solar_time: str, gender: str,
                            current_time: Optional[datetime] = None,
                            dayun_index: Optional[int] = None,
                            dayun_year_start: Optional[int] = None,
                            dayun_year_end: Optional[int] = None,
                            target_year: Optional[int] = None,
                            quick_mode: bool = True,
                            async_warmup: bool = True) -> Dict[str, Any]:
        """
        获取大运流年流月数据（统一接口，性能优化，带Redis缓存）
        
        性能优化：
        1. 只计算指定大运范围内的流年（约10年），而不是所有流年
        2. 使用多级缓存（L1内存 + L2 Redis，30天TTL）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            current_time: 当前时间（可选）
            dayun_index: 大运索引（可选，已废弃，优先使用dayun_year_start和dayun_year_end）
            dayun_year_start: 大运起始年份（可选），指定要显示的大运的起始年份
            dayun_year_end: 大运结束年份（可选），指定要显示的大运的结束年份
            target_year: 目标年份（可选），用于计算该年份的流月，默认为当前流年
            
        Returns:
            dict: 包含大运、流年、流月的前端友好数据
        """
        # 1. 生成缓存键
        cache_key = BaziDisplayService._generate_fortune_cache_key(
            solar_date, solar_time, gender, current_time, dayun_index,
            dayun_year_start, dayun_year_end, target_year
        )
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            # 设置 L2 Redis TTL 为 30 天
            cache.l2.ttl = BaziDisplayService.CACHE_TTL
            cached_result = cache.get(cache_key)
            if cached_result:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"✅ [缓存命中] BaziDisplayService.get_fortune_display: {cache_key[:80]}...")
                return cached_result
        except Exception as e:
            # Redis不可用，降级到直接计算
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️  Redis缓存不可用，降级到直接计算: {e}")
        
        # 3. 缓存未命中，执行计算
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"⏱️ [缓存未命中] BaziDisplayService.get_fortune_display: {cache_key[:80]}...")
        # ✅ 优化：根据年份范围查找大运索引（如果提供了年份范围）
        # 优化：如果已经提供了 dayun_year_start 和 dayun_year_end，先调用一次获取大运列表（利用缓存）
        # 然后从结果中提取大运索引，避免第二次调用时重复计算
        resolved_dayun_index = dayun_index
        detail_result_for_index = None
        
        if dayun_year_start is not None and dayun_year_end is not None and dayun_index is None:
            # ✅ 优化：先调用一次获取大运列表（利用缓存，如果之前调用过会命中缓存）
            # 注意：这里调用会利用缓存，性能影响已经减小
            # 注意：获取大运列表时使用完整模式（quick_mode=False），因为需要所有大运来确定索引
            detail_result_for_index = BaziDetailService.calculate_detail_full(
                solar_date, solar_time, gender, current_time, None, None,
                quick_mode=False, async_warmup=False,  # 获取列表时不使用快速模式
                include_wangshuai=False, include_shengong_minggong=False,  # 只获取大运列表，不需要其他数据
                include_rules=False, include_wuxing_proportion=False, include_rizhu_liujiazi=False
            )
            temp_details = detail_result_for_index.get('details', {}) if detail_result_for_index else {}
            temp_dayun_sequence = temp_details.get('dayun_sequence', [])
            
            # ✅ 修复：根据年份范围查找对应的大运（使用step作为唯一标识）
            # 支持精确匹配和包含匹配（如果年份范围不完全匹配，查找包含起始年份的大运）
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"查找大运: 年份范围 {dayun_year_start}-{dayun_year_end}")
            
            for dayun in temp_dayun_sequence:
                dayun_year_start_actual = dayun.get('year_start')
                dayun_year_end_actual = dayun.get('year_end')
                step = dayun.get('step')
                
                # 精确匹配
                if dayun_year_start_actual == dayun_year_start and dayun_year_end_actual == dayun_year_end:
                    resolved_dayun_index = step
                    logger.info(f"找到精确匹配的大运: step={step}, 年份范围 {dayun_year_start_actual}-{dayun_year_end_actual}")
                    break
                # 包含匹配：查找包含起始年份的大运
                elif dayun_year_start_actual <= dayun_year_start <= dayun_year_end_actual:
                    resolved_dayun_index = step
                    logger.info(f"找到包含匹配的大运: step={step}, 年份范围 {dayun_year_start_actual}-{dayun_year_end_actual}")
                    break
            
            if resolved_dayun_index is None:
                logger.warning(f"未找到匹配的大运，年份范围 {dayun_year_start}-{dayun_year_end}")
                # 列出所有大运供调试
                for dayun in temp_dayun_sequence:
                    logger.warning(f"  大运 step={dayun.get('step')}: {dayun.get('year_start')}-{dayun.get('year_end')}")
        
        # ✅ 优化：如果已经获取了完整结果（用于查找大运索引），且不需要指定大运索引，直接使用该结果
        # 这样可以避免第二次调用（如果 resolved_dayun_index 为 None，说明需要所有大运的数据）
        if detail_result_for_index and resolved_dayun_index is None and target_year is None:
            # 已经获取了完整结果，直接使用
            detail_result = detail_result_for_index
        else:
            # 只调用一次详细计算（如果指定了大运索引，只计算该大运范围内的流年）
            # 注意：如果第一次调用命中了缓存，第二次调用也会命中缓存（相同的参数）
            detail_result = BaziDetailService.calculate_detail_full(
                solar_date, solar_time, gender, current_time, resolved_dayun_index, target_year,
                quick_mode=quick_mode, async_warmup=async_warmup,
                include_wangshuai=True, include_shengong_minggong=True,
                include_rules=True, include_wuxing_proportion=True, include_rizhu_liujiazi=True
            )
        if not detail_result:
            return {"success": False, "error": "详细计算失败"}
        
        details = detail_result.get('details', {})
        
        # 处理大运数据
        dayun_sequence = details.get('dayun_sequence', [])
        dayun_info = details.get('dayun', {})
        qiyun_info = details.get('qiyun', {})
        jiaoyun_info = details.get('jiaoyun', {})
        
        # 确定当前大运
        current_dayun = None
        if current_time:
            current_year = current_time.year
            birth_year = int(solar_date.split('-')[0])
            current_age = current_year - birth_year + 1  # 虚岁计算
            
            for dayun in dayun_sequence:
                age_range = dayun.get('age_range', {})
                if age_range:
                    age_start = age_range.get('start', 0)
                    age_end = age_range.get('end', 0)
                    if age_start <= current_age <= age_end:
                        current_dayun = dayun
                        break
        
        # 确定要显示的大运（如果指定了dayun_index，使用指定的；否则使用当前大运）
        target_dayun = None
        if dayun_index is not None:
            # ✅ 修复：根据step查找大运（step是唯一标识，不受列表顺序影响）
            for dayun in dayun_sequence:
                if dayun.get('step') == dayun_index:
                    target_dayun = dayun
                    break
        else:
            target_dayun = current_dayun
        
        # 如果没有找到目标大运，使用当前大运
        if not target_dayun:
            target_dayun = current_dayun or (dayun_sequence[0] if dayun_sequence else None)
        
        # 格式化大运列表
        formatted_dayun_list = []
        for dayun in dayun_sequence:
            formatted = BaziDisplayService._format_dayun_item(dayun)
            if current_dayun and dayun.get('step') == current_dayun.get('step'):
                formatted['is_current'] = True
            formatted_dayun_list.append(formatted)
        
        # 处理流年数据 - 底层服务已经根据dayun_index生成了对应大运范围内的流年
        from datetime import datetime
        current_year = datetime.now().year if not current_time else current_time.year
        
        # ✅ 直接使用底层服务返回的流年序列（底层已经根据dayun_index生成了对应大运范围内的流年）
        liunian_sequence = details.get('liunian_sequence', [])
        
        # 确定当前流年
        current_liunian = None
        for liunian in liunian_sequence:
            if liunian.get('year') == current_year:
                current_liunian = liunian
                break
        
        # 格式化流年列表（底层已经只包含目标大运范围内的流年，约10年）
        formatted_liunian_list = []
        for liunian in liunian_sequence:
            formatted = BaziDisplayService._format_liunian_item(liunian)
            if current_liunian and liunian.get('year') == current_liunian.get('year'):
                formatted['is_current'] = True
            formatted_liunian_list.append(formatted)
        
        # 处理流月数据 - 只返回目标年份的流月（12个月）
        target_year_for_liuyue = target_year or (current_liunian.get('year') if current_liunian else current_year)
        
        # 从流年序列中获取流月（底层已经只计算了当前大运范围内的流年）
        target_liunian = None
        for liunian in liunian_sequence:
            if liunian.get('year') == target_year_for_liuyue:
                target_liunian = liunian
                break
        
        if target_liunian:
            liuyue_sequence = target_liunian.get('liuyue_sequence', [])
        else:
            liuyue_sequence = details.get('liuyue_sequence', [])
        
        # 确定当前流月
        current_month = datetime.now().month if not current_time else current_time.month
        current_liuyue = None
        for liuyue in liuyue_sequence:
            if liuyue.get('month') == current_month:
                current_liuyue = liuyue
                break
        
        # 格式化流月列表
        formatted_liuyue_list = []
        for liuyue in liuyue_sequence:
            formatted = BaziDisplayService._format_liuyue_item(liuyue)
            if current_liuyue and liuyue.get('month') == current_liuyue.get('month'):
                formatted['is_current'] = True
            formatted_liuyue_list.append(formatted)
        
        # ✅ 添加四柱详细信息（用于细盘表格）
        bazi_pillars = detail_result.get('bazi_pillars', {})
        formatted_pillars = {}
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_details = details.get(pillar_type, {})
            formatted_pillars[pillar_type] = {
                "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
                "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
                "main_star": pillar_details.get('main_star', ''),
                "hidden_stars": pillar_details.get('hidden_stars', []),
                "sub_stars": pillar_details.get('sub_stars', pillar_details.get('hidden_stars', [])),
                "hidden_stems": pillar_details.get('hidden_stems', []),
                "star_fortune": pillar_details.get('star_fortune', ''),
                "self_sitting": pillar_details.get('self_sitting', ''),
                "kongwang": pillar_details.get('kongwang', ''),
                "nayin": pillar_details.get('nayin', ''),
                "deities": pillar_details.get('deities', [])
            }
        
        result = {
            "success": True,
            "pillars": formatted_pillars,  # ✅ 添加四柱信息
            "dayun": {
                "current": BaziDisplayService._format_dayun_item(current_dayun or dayun_info),
                "list": formatted_dayun_list,
                "qiyun": {
                    "date": qiyun_info.get('date', ''),
                    "age_display": qiyun_info.get('age_display', ''),
                    "description": qiyun_info.get('description', '')
                },
                "jiaoyun": {
                    "date": jiaoyun_info.get('date', ''),
                    "age_display": jiaoyun_info.get('age_display', ''),
                    "description": jiaoyun_info.get('description', '')
                }
            },
            "liunian": {
                "current": BaziDisplayService._format_liunian_item(current_liunian) if current_liunian else None,
                "list": formatted_liunian_list
            },
            "liuyue": {
                "current": BaziDisplayService._format_liuyue_item(current_liuyue or (liuyue_sequence[0] if liuyue_sequence else {})),
                "list": formatted_liuyue_list,
                "target_year": target_year_for_liuyue
            },
            "details": {
                "dayun_sequence": dayun_sequence  # ✅ 添加大运序列，供前端使用
            }
        }
        
        # 4. 写入缓存（仅成功时）
        if result.get('success'):
            try:
                cache = get_multi_cache()
                cache.l2.ttl = BaziDisplayService.CACHE_TTL
                cache.set(cache_key, result)
                logger.info(f"✅ [缓存写入] BaziDisplayService.get_fortune_display: {cache_key[:80]}...")
            except Exception as e:
                # 缓存写入失败不影响业务
                logger.warning(f"⚠️  缓存写入失败（不影响业务）: {e}")
        
        return result


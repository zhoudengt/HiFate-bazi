#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行占比计算服务
基于生辰八字统计五行占比，并提供大模型分析所需数据
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List

from server.services.bazi_service import BaziService
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.analyzers.wangshuai_analyzer import WangShuaiAnalyzer

logger = logging.getLogger(__name__)


class WuxingProportionService:
    """五行占比计算服务"""
    
    @staticmethod
    def calculate_proportion(
        solar_date: str,
        solar_time: str,
        gender: str
    ) -> Dict[str, Any]:
        """
        计算五行占比
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
        
        Returns:
            dict: 包含五行占比、八字信息、十神、旺衰等
        """
        try:
            # 1. 获取基础八字数据
            bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
            if not bazi_result:
                return {
                    "success": False,
                    "error": "八字计算失败"
                }
            
            # 2. 提取四柱信息
            # calculate_bazi_full 返回的数据结构可能有两种：
            # 1. {"bazi": {...}, "rizhu": "...", "matched_rules": []} - 标准结构
            # 2. 直接包含 bazi_pillars（如果没有 bazi 字段）
            # 参考 monthly_fortune_service.py 的处理方式
            bazi_data = bazi_result.get('bazi', bazi_result)  # 如果没有 'bazi' 键，使用整个结果
            
            if not bazi_data or not isinstance(bazi_data, dict):
                return {
                    "success": False,
                    "error": f"无法提取八字数据。返回数据键: {list(bazi_result.keys()) if isinstance(bazi_result, dict) else type(bazi_result)}"
                }
            
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            details = bazi_data.get('details', {})
            
            # 验证 bazi_pillars 是否有效
            if not bazi_pillars or not isinstance(bazi_pillars, dict):
                return {
                    "success": False,
                    "error": f"无法提取四柱信息。bazi数据键: {list(bazi_data.keys()) if isinstance(bazi_data, dict) else type(bazi_data)}"
                }
            
            # 验证是否有有效的柱数据
            has_valid_pillar = False
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                if isinstance(pillar, dict) and (pillar.get('stem') or pillar.get('branch')):
                    has_valid_pillar = True
                    break
            
            if not has_valid_pillar:
                return {
                    "success": False,
                    "error": f"四柱数据无效。bazi_pillars内容: {bazi_pillars}"
                }
            
            # 3. 统计五行占比（天干+地支，8个位置）
            element_counts = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
            element_details = {'金': [], '木': [], '水': [], '火': [], '土': []}
            
            # 统计天干五行（4个位置）
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                stem = pillar.get('stem', '')
                if stem and stem in STEM_ELEMENTS:
                    element = STEM_ELEMENTS[stem]
                    element_counts[element] += 1
                    element_details[element].append(stem)
            
            # 统计地支五行（4个位置）
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                branch = pillar.get('branch', '')
                if branch and branch in BRANCH_ELEMENTS:
                    element = BRANCH_ELEMENTS[branch]
                    element_counts[element] += 1
                    element_details[element].append(branch)
            
            # 4. 计算占比（保留两位小数）
            total = 8
            proportions = {}
            for element in ['金', '木', '水', '火', '土']:
                count = element_counts[element]
                percentage = round(count / total * 100, 2) if total > 0 else 0.0
                proportions[element] = {
                    'count': count,
                    'percentage': percentage,
                    'details': element_details[element]
                }
            
            # 5. 提取十神信息（主星和副星）
            ten_gods_info = WuxingProportionService._extract_ten_gods(details)
            
            # 6. 获取旺衰分析
            wangshuai_result = None
            try:
                analyzer = WangShuaiAnalyzer()
                wangshuai_result = analyzer.analyze(solar_date, solar_time, gender)
            except Exception as e:
                logger.warning(f"⚠️  旺衰分析失败（不影响业务）: {e}")
            
            # 7. 分析相生相克关系
            element_relations = WuxingProportionService._analyze_element_relations(proportions)
            
            return {
                "success": True,
                "bazi_pillars": bazi_pillars,
                "proportions": proportions,
                "ten_gods": ten_gods_info,
                "wangshuai": wangshuai_result,
                "element_relations": element_relations,
                "bazi_data": bazi_result
            }
        except Exception as e:
            import traceback
            logger.error(f"❌ 五行占比计算失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"计算失败: {str(e)}"
            }
    
    @staticmethod
    def _extract_ten_gods(details: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        提取四柱十神信息（主星和副星）
        
        Args:
            details: 八字详情数据
        
        Returns:
            dict: 包含四柱的主星和副星信息
        """
        ten_gods_info = {}
        
        for pillar_name in ['year', 'month', 'day', 'hour']:
            pillar_detail = details.get(pillar_name, {})
            if not isinstance(pillar_detail, dict):
                pillar_detail = {}
            
            main_star = pillar_detail.get('main_star', '')
            hidden_stars = pillar_detail.get('hidden_stars', [])
            if not isinstance(hidden_stars, list):
                hidden_stars = []
            
            ten_gods_info[pillar_name] = {
                'main_star': main_star,
                'hidden_stars': hidden_stars
            }
        
        return ten_gods_info
    
    @staticmethod
    def _analyze_element_relations(proportions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析五行相生相克关系
        
        Args:
            proportions: 五行占比数据
        
        Returns:
            dict: 相生相克关系分析
        """
        # 五行生克关系
        element_relations_map = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }
        
        relations = {
            'produces': [],  # 生
            'controls': [],  # 克
            'produced_by': [],  # 被生
            'controlled_by': []  # 被克
        }
        
        # 分析每个五行与其他五行的关系
        for element, data in proportions.items():
            if data['count'] == 0:
                continue
            
            element_relation = element_relations_map.get(element, {})
            
            # 检查生（我生）
            produces = element_relation.get('produces', '')
            if produces and proportions.get(produces, {}).get('count', 0) > 0:
                relations['produces'].append({
                    'from': element,
                    'to': produces,
                    'from_count': data['count'],
                    'to_count': proportions[produces]['count']
                })
            
            # 检查克（我克）
            controls = element_relation.get('controls', '')
            if controls and proportions.get(controls, {}).get('count', 0) > 0:
                relations['controls'].append({
                    'from': element,
                    'to': controls,
                    'from_count': data['count'],
                    'to_count': proportions[controls]['count']
                })
            
            # 检查被生（生我）
            produced_by = element_relation.get('produced_by', '')
            if produced_by and proportions.get(produced_by, {}).get('count', 0) > 0:
                relations['produced_by'].append({
                    'from': produced_by,
                    'to': element,
                    'from_count': proportions[produced_by]['count'],
                    'to_count': data['count']
                })
            
            # 检查被克（克我）
            controlled_by = element_relation.get('controlled_by', '')
            if controlled_by and proportions.get(controlled_by, {}).get('count', 0) > 0:
                relations['controlled_by'].append({
                    'from': controlled_by,
                    'to': element,
                    'from_count': proportions[controlled_by]['count'],
                    'to_count': data['count']
                })
        
        return relations
    
    @staticmethod
    def build_llm_prompt(proportion_data: Dict[str, Any]) -> str:
        """
        构建大模型提示词
        
        Args:
            proportion_data: 五行占比数据（calculate_proportion 返回的数据）
        
        Returns:
            str: 大模型提示词
        """
        if not proportion_data.get('success'):
            return ""
        
        prompt_lines = []
        prompt_lines.append("请基于以下八字信息进行五行占比分析：")
        prompt_lines.append("")
        
        # 1. 五行占比数据
        prompt_lines.append("【五行占比】")
        proportions = proportion_data.get('proportions', {})
        for element in ['金', '木', '水', '火', '土']:
            data = proportions.get(element, {})
            count = data.get('count', 0)
            percentage = data.get('percentage', 0.0)
            details = data.get('details', [])
            details_str = '、'.join(details) if details else '无'
            prompt_lines.append(f"{element}：{percentage}% ({details_str})")
        prompt_lines.append("")
        
        # 2. 四柱十神信息
        prompt_lines.append("【四柱十神】")
        ten_gods = proportion_data.get('ten_gods', {})
        pillar_names = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
        for pillar_key, pillar_name in pillar_names.items():
            pillar_ten_gods = ten_gods.get(pillar_key, {})
            main_star = pillar_ten_gods.get('main_star', '')
            hidden_stars = pillar_ten_gods.get('hidden_stars', [])
            hidden_stars_str = '、'.join(hidden_stars) if hidden_stars else '无'
            prompt_lines.append(f"{pillar_name}：主星{main_star}，副星{hidden_stars_str}")
        prompt_lines.append("")
        
        # 3. 旺衰分析
        prompt_lines.append("【旺衰分析】")
        wangshuai = proportion_data.get('wangshuai', {})
        if wangshuai:
            wangshuai_type = wangshuai.get('wangshuai', '')
            total_score = wangshuai.get('total_score', 0)
            prompt_lines.append(f"身旺/身弱：{wangshuai_type}")
            prompt_lines.append(f"得分：{total_score}")
            
            # 喜忌神
            xi_ji = wangshuai.get('xi_ji', {})
            if xi_ji:
                xi_shen = xi_ji.get('xi_shen', [])
                ji_shen = xi_ji.get('ji_shen', [])
                xi_shen_str = '、'.join(xi_shen) if xi_shen else '无'
                ji_shen_str = '、'.join(ji_shen) if ji_shen else '无'
                prompt_lines.append(f"喜神：{xi_shen_str}")
                prompt_lines.append(f"忌神：{ji_shen_str}")
        else:
            prompt_lines.append("旺衰分析：未获取")
        prompt_lines.append("")
        
        # 4. 相生相克关系
        prompt_lines.append("【相生相克关系】")
        element_relations = proportion_data.get('element_relations', {})
        if element_relations:
            produces = element_relations.get('produces', [])
            controls = element_relations.get('controls', [])
            produced_by = element_relations.get('produced_by', [])
            controlled_by = element_relations.get('controlled_by', [])
            
            if produces:
                produces_str = '、'.join([f"{r['from']}生{r['to']}" for r in produces])
                prompt_lines.append(f"生：{produces_str}")
            if controls:
                controls_str = '、'.join([f"{r['from']}克{r['to']}" for r in controls])
                prompt_lines.append(f"克：{controls_str}")
            if produced_by:
                produced_by_str = '、'.join([f"{r['from']}生{r['to']}" for r in produced_by])
                prompt_lines.append(f"被生：{produced_by_str}")
            if controlled_by:
                controlled_by_str = '、'.join([f"{r['from']}克{r['to']}" for r in controlled_by])
                prompt_lines.append(f"被克：{controlled_by_str}")
        else:
            prompt_lines.append("相生相克关系：未分析")
        prompt_lines.append("")
        
        # 5. 分析要求
        prompt_lines.append("请基于以上信息，进行详细的五行占比分析，包括：")
        prompt_lines.append("1. 五行平衡性分析")
        prompt_lines.append("2. 五行对命局的影响")
        prompt_lines.append("3. 相生相克关系的解读")
        prompt_lines.append("4. 建议和指导")
        
        return '\n'.join(prompt_lines)


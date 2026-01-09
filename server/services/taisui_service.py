#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太岁服务 - 提供太岁信息、犯太岁判断、化解建议、躲星时间等功能
"""

import sys
import os
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.tool.LunarConverter import LunarConverter
from src.data.stems_branches import BRANCH_ZODIAC
from src.data.relations import BRANCH_CHONG, BRANCH_XING, BRANCH_HAI, BRANCH_PO
import logging

logger = logging.getLogger(__name__)


# 太岁名称映射（根据年份地支）
TAISUI_NAMES = {
    '子': '甲子太岁金辨星君',
    '丑': '乙丑太岁陈材星君',
    '寅': '丙寅太岁耿章星君',
    '卯': '丁卯太岁沈兴星君',
    '辰': '戊辰太岁赵达星君',
    '巳': '己巳太岁郭灿星君',
    '午': '丙午太岁文哲星君',
    '未': '丁未太岁缪丙星君',
    '申': '戊申太岁徐浩星君',
    '酉': '己酉太岁程宝星君',
    '戌': '庚戌太岁倪秘星君',
    '亥': '辛亥太岁叶坚星君',
}

# 太岁描述映射
TAISUI_DESCRIPTIONS = {
    '子': '司水势，主变动',
    '丑': '司土势，主稳定',
    '寅': '司木势，主生发',
    '卯': '司木势，主成长',
    '辰': '司土势，主蓄积',
    '巳': '司火势，主变化',
    '午': '司火势，主变动',
    '未': '司土势，主成熟',
    '申': '司金势，主收敛',
    '酉': '司金势，主肃杀',
    '戌': '司土势，主收藏',
    '亥': '司水势，主归藏',
}

# 天干五行映射
STEM_ELEMENTS = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水'
}


class TaisuiService:
    """太岁服务"""
    
    @staticmethod
    def get_taisui_info(year: int) -> Dict[str, Any]:
        """
        获取指定年份的太岁信息
        
        Args:
            year: 年份（如：2026）
            
        Returns:
            dict: 太岁信息
            {
                'year': 2026,
                'stem': '丙',
                'branch': '午',
                'ganzhi': '丙午',
                'taisui_name': '丙午太岁文哲星君',
                'taisui_description': '司火势，主变动',
                'element': '火'
            }
        """
        try:
            # 获取年份干支
            year_ganzhi = LunarConverter.get_year_ganzhi(year)
            if not year_ganzhi:
                logger.error(f"无法获取年份 {year} 的干支")
                return {}
            
            stem = year_ganzhi.get('stem', '')
            branch = year_ganzhi.get('branch', '')
            
            if not stem or not branch:
                logger.error(f"年份 {year} 的干支不完整: {year_ganzhi}")
                return {}
            
            # 获取太岁名称和描述
            taisui_name = TaisuiService._get_taisui_name(stem, branch)
            taisui_description = TAISUI_DESCRIPTIONS.get(branch, '')
            element = STEM_ELEMENTS.get(stem, '')
            
            return {
                'year': year,
                'stem': stem,
                'branch': branch,
                'ganzhi': f"{stem}{branch}",
                'taisui_name': taisui_name,
                'taisui_description': taisui_description,
                'element': element
            }
        except Exception as e:
            logger.error(f"获取太岁信息失败: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def _get_taisui_name(stem: str, branch: str) -> str:
        """
        获取太岁名称
        
        Args:
            stem: 天干
            branch: 地支
            
        Returns:
            str: 太岁名称
        """
        # 优先使用年份干支对应的太岁名称
        ganzhi = f"{stem}{branch}"
        
        # 特殊年份的太岁名称（根据实际年份调整）
        special_names = {
            '丙午': '丙午太岁文哲星君',
            '丁未': '丁未太岁缪丙星君',
            '戊申': '戊申太岁徐浩星君',
            '己酉': '己酉太岁程宝星君',
            '庚戌': '庚戌太岁倪秘星君',
            '辛亥': '辛亥太岁叶坚星君',
            '壬子': '壬子太岁丘德星君',
            '癸丑': '癸丑太岁朱得星君',
            '甲寅': '甲寅太岁张朝星君',
            '乙卯': '乙卯太岁万清星君',
            '丙辰': '丙辰太岁辛亚星君',
            '丁巳': '丁巳太岁杨彦星君',
        }
        
        if ganzhi in special_names:
            return special_names[ganzhi]
        
        # 默认使用地支对应的太岁名称
        return TAISUI_NAMES.get(branch, f'{ganzhi}太岁')
    
    @staticmethod
    def check_fanshaisui(user_zodiac: str, taisui_branch: str) -> Dict[str, Any]:
        """
        判断是否犯太岁
        
        Args:
            user_zodiac: 用户生肖（如：'鼠'、'牛'等）
            taisui_branch: 太岁地支（如：'午'）
            
        Returns:
            dict: 犯太岁信息
            {
                'is_fanshaisui': True/False,
                'fanshaisui_types': ['冲', '刑', '害', '破'],  # 犯太岁类型列表
                'fanshaisui_details': {
                    '冲': {'zodiac': '鼠', 'branch': '子'},
                    '刑': {...},
                    '害': {...},
                    '破': {...}
                }
            }
        """
        try:
            # 将生肖转换为地支
            zodiac_to_branch = {v: k for k, v in BRANCH_ZODIAC.items()}
            user_branch = zodiac_to_branch.get(user_zodiac)
            
            if not user_branch:
                logger.warning(f"无法识别生肖: {user_zodiac}")
                return {
                    'is_fanshaisui': False,
                    'fanshaisui_types': [],
                    'fanshaisui_details': {}
                }
            
            fanshaisui_types = []
            fanshaisui_details = {}
            
            # 判断值太岁（本命年）
            if user_branch == taisui_branch:
                fanshaisui_types.append('值')
                fanshaisui_details['值'] = {
                    'zodiac': user_zodiac,
                    'branch': user_branch
                }
            
            # 判断冲太岁（六冲）
            chong_branch = BRANCH_CHONG.get(taisui_branch)
            if chong_branch == user_branch:
                fanshaisui_types.append('冲')
                chong_zodiac = BRANCH_ZODIAC.get(chong_branch, '')
                fanshaisui_details['冲'] = {
                    'zodiac': chong_zodiac,
                    'branch': chong_branch
                }
            
            # 判断刑太岁（相刑）
            xing_branches = BRANCH_XING.get(taisui_branch, [])
            if user_branch in xing_branches:
                fanshaisui_types.append('刑')
                xing_zodiac = BRANCH_ZODIAC.get(user_branch, '')
                fanshaisui_details['刑'] = {
                    'zodiac': xing_zodiac,
                    'branch': user_branch
                }
            
            # 判断害太岁（相害）
            hai_branches = BRANCH_HAI.get(taisui_branch, [])
            if user_branch in hai_branches:
                fanshaisui_types.append('害')
                hai_zodiac = BRANCH_ZODIAC.get(user_branch, '')
                fanshaisui_details['害'] = {
                    'zodiac': hai_zodiac,
                    'branch': user_branch
                }
            
            # 判断破太岁（相破）
            po_branch = BRANCH_PO.get(taisui_branch)
            if po_branch == user_branch:
                fanshaisui_types.append('破')
                po_zodiac = BRANCH_ZODIAC.get(po_branch, '')
                fanshaisui_details['破'] = {
                    'zodiac': po_zodiac,
                    'branch': po_branch
                }
            
            return {
                'is_fanshaisui': len(fanshaisui_types) > 0,
                'fanshaisui_types': fanshaisui_types,
                'fanshaisui_details': fanshaisui_details
            }
        except Exception as e:
            logger.error(f"判断犯太岁失败: {e}", exc_info=True)
            return {
                'is_fanshaisui': False,
                'fanshaisui_types': [],
                'fanshaisui_details': {}
            }
    
    @staticmethod
    def get_resolution_suggestions(
        fanshaisui_types: List[str],
        user_zodiac: str,
        taisui_info: Dict[str, Any],
        bazi_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        获取化解建议（结合命盘八字及属相）
        
        Args:
            fanshaisui_types: 犯太岁类型列表（如：['冲', '刑', '害', '破']）
            user_zodiac: 用户生肖
            taisui_info: 太岁信息
            bazi_data: 八字数据（可选，用于结合命盘分析）
            
        Returns:
            list: 化解建议列表
        """
        suggestions = []
        
        # 通用化解建议
        if '值' in fanshaisui_types:
            suggestions.append("本命年值太岁，需格外谨慎，避免重大决策。")
        if '冲' in fanshaisui_types:
            suggestions.append("冲太岁，易有变动，建议正月十五前拜太岁或佩戴太岁符。")
        if '刑' in fanshaisui_types:
            suggestions.append("刑太岁，易有口舌是非，建议行善积德，避免口舌争执。")
        if '害' in fanshaisui_types:
            suggestions.append("害太岁，易有小人作祟，建议谨慎交友，避免冲突。")
        if '破' in fanshaisui_types:
            suggestions.append("破太岁，易有破财，建议理性投资，避免冲动消费。")
        
        # 结合命盘分析（如果有八字数据）
        if bazi_data:
            # 可以根据命盘的五行喜忌给出更具体的建议
            # 例如：如果命局火旺，太岁也是火，建议补水
            taisui_element = taisui_info.get('element', '')
            if taisui_element:
                suggestions.append(f"太岁为{taisui_element}，建议根据命局五行平衡进行调整。")
        
        # 通用建议
        if not suggestions:
            suggestions.append("行善积德，避免口舌争执。")
            suggestions.append("可佩戴太岁符或进行拜太岁仪式。")
        
        return suggestions
    
    @staticmethod
    def get_duoxing_times(year: int) -> Dict[str, str]:
        """
        获取躲星时间
        
        Args:
            year: 年份（如：2026）
            
        Returns:
            dict: 躲星时间
            {
                '太岁星': '农历正月初四亥时（21:00-23:00）',
                '大耗星': '农历正月初十巳时（9:00-11:00）',
                '病符星': '农历正月十三辰时（7:00-9:00）',
                '罗睺星': '农历正月初八戌时（19:00-21:00）',
                '计都星': '农历正月十八未时（13:00-15:00）'
            }
        """
        # 注意：这里的时间是固定的，实际应该根据年份和农历计算
        # 暂时使用示例数据，后续可以根据实际需求调整
        return {
            '太岁星': f'农历正月初四亥时（21:00-23:00）',
            '大耗星': f'农历正月初十巳时（9:00-11:00）',
            '病符星': f'农历正月十三辰时（7:00-9:00）',
            '罗睺星': f'农历正月初八戌时（19:00-21:00）',
            '计都星': f'农历正月十八未时（13:00-15:00）'
        }

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

from core.data.stems_branches import BRANCH_ZODIAC
from core.data.relations import BRANCH_CHONG, BRANCH_XING, BRANCH_HAI, BRANCH_PO
import logging

logger = logging.getLogger(__name__)


# 六十甲子太岁名称完整对照表（按干支组合，非地支）
# 每六十年一轮回，每年对应一位太岁大将军
TAISUI_NAMES = {
    '甲子': '甲子太岁金辨大将军',
    '乙丑': '乙丑太岁陈材大将军',
    '丙寅': '丙寅太岁耿章大将军',
    '丁卯': '丁卯太岁沈兴大将军',
    '戊辰': '戊辰太岁赵达大将军',
    '己巳': '己巳太岁郭灿大将军',
    '庚午': '庚午太岁王济大将军',
    '辛未': '辛未太岁李素大将军',
    '壬申': '壬申太岁刘旺大将军',
    '癸酉': '癸酉太岁康志大将军',
    '甲戌': '甲戌太岁施广大将军',
    '乙亥': '乙亥太岁任保大将军',
    '丙子': '丙子太岁郭嘉大将军',
    '丁丑': '丁丑太岁汪文大将军',
    '戊寅': '戊寅太岁鲁先大将军',
    '己卯': '己卯太岁龙仲大将军',
    '庚辰': '庚辰太岁董德大将军',
    '辛巳': '辛巳太岁郑但大将军',
    '壬午': '壬午太岁陆明大将军',
    '癸未': '癸未太岁魏仁大将军',
    '甲申': '甲申太岁方杰大将军',
    '乙酉': '乙酉太岁蒋崇大将军',
    '丙戌': '丙戌太岁白敏大将军',
    '丁亥': '丁亥太岁封济大将军',
    '戊子': '戊子太岁邹铛大将军',
    '己丑': '己丑太岁傅佑大将军',
    '庚寅': '庚寅太岁邬桓大将军',
    '辛卯': '辛卯太岁范宁大将军',
    '壬辰': '壬辰太岁彭泰大将军',
    '癸巳': '癸巳太岁徐单大将军',
    '甲午': '甲午太岁章词大将军',
    '乙未': '乙未太岁杨仙大将军',
    '丙申': '丙申太岁管仲大将军',
    '丁酉': '丁酉太岁唐杰大将军',
    '戊戌': '戊戌太岁姜武大将军',
    '己亥': '己亥太岁谢太大将军',
    '庚子': '庚子太岁卢秘大将军',
    '辛丑': '辛丑太岁杨信大将军',
    '壬寅': '壬寅太岁贺谔大将军',
    '癸卯': '癸卯太岁皮时大将军',
    '甲辰': '甲辰太岁李诚大将军',
    '乙巳': '乙巳太岁吴遂大将军',
    '丙午': '丙午太岁文哲大将军',
    '丁未': '丁未太岁缪丙大将军',
    '戊申': '戊申太岁徐浩大将军',
    '己酉': '己酉太岁程宝大将军',
    '庚戌': '庚戌太岁倪秘大将军',
    '辛亥': '辛亥太岁叶坚大将军',
    '壬子': '壬子太岁丘德大将军',
    '癸丑': '癸丑太岁朱得大将军',
    '甲寅': '甲寅太岁张朝大将军',
    '乙卯': '乙卯太岁万清大将军',
    '丙辰': '丙辰太岁辛亚大将军',
    '丁巳': '丁巳太岁杨彦大将军',
    '戊午': '戊午太岁黎卿大将军',
    '己未': '己未太岁傅党大将军',
    '庚申': '庚申太岁毛梓大将军',
    '辛酉': '辛酉太岁石政大将军',
    '壬戌': '壬戌太岁洪充大将军',
    '癸亥': '癸亥太岁虞程大将军',
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
    
    # 天干地支序列（用于年干支计算）
    _STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    _BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    @staticmethod
    def _calc_year_ganzhi(year: int) -> tuple:
        """
        根据公历年份计算年干支（标准六十甲子公式）
        
        注意：LunarConverter.get_year_ganzhi() 使用 1月1日计算，
        但1月1日在立春之前，导致返回的是上一年干支。
        此处使用标准公式直接计算，确保年份与干支一一对应。
        
        公式：天干 = (year - 4) % 10，地支 = (year - 4) % 12
        例如：2025 → 乙巳，2026 → 丙午
        
        Args:
            year: 公历年份
            
        Returns:
            tuple: (天干, 地支)
        """
        stem_idx = (year - 4) % 10
        branch_idx = (year - 4) % 12
        return TaisuiService._STEMS[stem_idx], TaisuiService._BRANCHES[branch_idx]
    
    @staticmethod
    def get_taisui_info(year: int) -> Dict[str, Any]:
        """
        获取指定年份的太岁信息
        
        Args:
            year: 年份（如：2025）
            
        Returns:
            dict: 太岁信息
            {
                'year': 2025,
                'stem': '乙',
                'branch': '巳',
                'ganzhi': '乙巳',
                'taisui_name': '乙巳太岁吴遂大将军',
                'taisui_description': '司火势，主变化',
                'element': '木'
            }
        """
        try:
            # 使用标准公式计算年干支（避免 LunarConverter 的立春偏移问题）
            stem, branch = TaisuiService._calc_year_ganzhi(year)
            
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
        获取太岁名称（从六十甲子完整对照表查询）
        
        Args:
            stem: 天干
            branch: 地支
            
        Returns:
            str: 太岁名称，如 '乙巳太岁吴遂大将军'
        """
        ganzhi = f"{stem}{branch}"
        return TAISUI_NAMES.get(ganzhi, f'{ganzhi}太岁')
    
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

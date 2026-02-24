#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
年运报告服务 - 业务逻辑层（二级接口）
负责数据提取、数据构建、数据验证、数据格式化
"""

import sys
import os
from typing import Dict, Any, Optional, List
import json
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.taisui_service import TaisuiService
from server.services.fengshui_service import FengshuiService
from server.services.monthly_fortune_service import MonthlyFortuneService
from server.utils.dayun_liunian_helper import calculate_user_age
from core.data.stems_branches import BRANCH_ZODIAC
from core.calculators.LunarConverter import LunarConverter

try:
    from server.services.user_profile_service import UserProfileService
except ImportError:
    UserProfileService = None

logger = logging.getLogger(__name__)


class AnnualReportService:
    """年运报告服务（业务逻辑层）"""
    
    @staticmethod
    def build_annual_report_input_data(
        bazi_data: Dict[str, Any],
        wangshuai_result: Dict[str, Any],
        detail_result: Dict[str, Any],
        dayun_sequence: List[Dict[str, Any]],
        special_liunians: List[Dict[str, Any]] = None,  # ⚠️ 新增：特殊流年（岁运并临、天克地冲、天合地合）
        gender: str = None,
        solar_date: str = None,
        solar_time: str = None,
        target_year: int = None,
        focus_tags: List[str] = None,
        relationship_status: str = None,
        career_status: str = None,
    ) -> Dict[str, Any]:
        """
        构建年运报告的输入数据
        
        Args:
            bazi_data: 八字基础数据
            wangshuai_result: 旺衰分析结果
            detail_result: 详细计算结果
            dayun_sequence: 大运序列
            special_liunians: 特殊流年列表（岁运并临、天克地冲、天合地合）
            gender: 性别（male/female）
            solar_date: 出生日期
            solar_time: 出生时间
            target_year: 目标年份（如：2026）
            
        Returns:
            dict: 年运报告的input_data
        """
        try:
            # 1. 提取命盘分析数据
            mingpan_analysis = AnnualReportService._extract_mingpan_analysis(
                bazi_data, wangshuai_result
            )
            
            # 2. 提取流月解读数据（1-12月）
            monthly_analysis = AnnualReportService._extract_monthly_analysis(
                bazi_data, detail_result, target_year
            )
            
            # 3. 提取流年太岁信息
            taisui_info = AnnualReportService._extract_taisui_info(
                bazi_data, target_year
            )
            
            # 4. 提取九宫飞星避煞信息
            fengshui_info = AnnualReportService._extract_fengshui_info(
                target_year
            )
            
            # 5. 构建流年大运数据（包含 relations 字段）
            dayun_liunian_data = AnnualReportService._build_dayun_liunian_data(
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians or [],
                target_year=target_year
            )
            
            # 6. 构建用户画像（新增，失败时降级为空字典，不影响其他模块）
            user_profile = {}
            try:
                if UserProfileService is not None and solar_date:
                    wangshuai_data = {}
                    if isinstance(wangshuai_result, dict):
                        if wangshuai_result.get('success') and 'data' in wangshuai_result:
                            wangshuai_data = wangshuai_result.get('data', {})
                        elif 'xi_shen' in wangshuai_result or 'wangshuai' in wangshuai_result:
                            wangshuai_data = wangshuai_result
                    user_profile = UserProfileService.build_user_profile(
                        solar_date=solar_date,
                        gender=gender or "male",
                        bazi_data=bazi_data,
                        wangshuai_data=wangshuai_data,
                        target_year=target_year,
                        focus_tags=focus_tags,
                        relationship_status=relationship_status,
                        career_status=career_status,
                    )
            except Exception as e:
                logger.warning(f"构建用户画像失败，降级为空: {e}", exc_info=True)
                user_profile = {}

            # 7. 构建完整的input_data
            input_data = {
                'mingpan_analysis': mingpan_analysis,
                'monthly_analysis': monthly_analysis,
                'taisui_info': taisui_info,
                'fengshui_info': fengshui_info,
                'dayun_liunian': dayun_liunian_data,  # ⚠️ 新增：流年大运数据（含 relations）
                'user_profile': user_profile,          # 用户画像（分层/状态标记）
            }
            
            return input_data
        except Exception as e:
            logger.error(f"构建年运报告input_data失败: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _build_dayun_liunian_data(
        dayun_sequence: List[Dict[str, Any]],
        special_liunians: List[Dict[str, Any]],
        target_year: int = None
    ) -> Dict[str, Any]:
        """
        构建流年大运数据（包含 relations 字段）
        
        Args:
            dayun_sequence: 大运序列
            special_liunians: 特殊流年列表（岁运并临、天克地冲、天合地合）
            target_year: 目标年份
            
        Returns:
            dict: 流年大运数据（包含 relations）
        """
        try:
            # 1. 按大运步数对特殊流年进行分组
            special_by_dayun = {}
            for liunian in special_liunians:
                dayun_step = liunian.get('dayun_step')
                if dayun_step is not None:
                    if dayun_step not in special_by_dayun:
                        special_by_dayun[dayun_step] = []
                    special_by_dayun[dayun_step].append(liunian)
            
            # 2. 构建大运列表（每个大运包含其特殊流年）
            dayuns_with_liunians = []
            for dayun in dayun_sequence:
                step = dayun.get('step')
                stem = dayun.get('gan', dayun.get('stem', ''))
                branch = dayun.get('zhi', dayun.get('branch', ''))
                ganzhi = dayun.get('ganzhi', f'{stem}{branch}')
                
                # 获取该大运下的特殊流年
                liunians_for_dayun = special_by_dayun.get(step, [])
                
                # 格式化流年数据（保留 relations 字段）
                formatted_liunians = []
                for liunian in liunians_for_dayun:
                    formatted_liunians.append({
                        'year': liunian.get('year'),
                        'ganzhi': liunian.get('ganzhi', ''),
                        'dayun_step': liunian.get('dayun_step'),
                        'dayun_ganzhi': liunian.get('dayun_ganzhi', ''),
                        'relations': liunian.get('relations', []),  # ⚠️ 保留 relations 字段
                        'type_display': liunian.get('type_display', ''),
                        'age': liunian.get('age'),
                        'priority': liunian.get('priority', 999999)
                    })
                
                # 按优先级排序（不限制数量）
                formatted_liunians.sort(key=lambda x: x.get('priority', 999999))
                
                dayun_data = {
                    'step': step,
                    'ganzhi': ganzhi,
                    'stem': stem,
                    'branch': branch,
                    'age_display': dayun.get('age_display', dayun.get('age_range', '')),
                    'start_age': dayun.get('start_age'),
                    'end_age': dayun.get('end_age'),
                    'liunians': formatted_liunians  # ⚠️ 包含 relations 的流年列表
                }
                dayuns_with_liunians.append(dayun_data)
            
            # 3. 提取目标年份的流年（如果指定）
            target_liunian = None
            if target_year:
                for liunian in special_liunians:
                    if liunian.get('year') == target_year:
                        target_liunian = {
                            'year': liunian.get('year'),
                            'ganzhi': liunian.get('ganzhi', ''),
                            'relations': liunian.get('relations', []),
                            'type_display': liunian.get('type_display', '')
                        }
                        break
            
            return {
                'dayuns': dayuns_with_liunians,
                'dayun_count': len(dayun_sequence),
                'special_liunian_count': len(special_liunians),
                'target_year_liunian': target_liunian
            }
        except Exception as e:
            logger.error(f"构建流年大运数据失败: {e}", exc_info=True)
            return {
                'dayuns': [],
                'dayun_count': 0,
                'special_liunian_count': 0,
                'target_year_liunian': None
            }
    
    @staticmethod
    def _extract_mingpan_analysis(
        bazi_data: Dict[str, Any],
        wangshuai_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提取命盘分析数据
        
        Args:
            bazi_data: 八字基础数据
            wangshuai_result: 旺衰分析结果
            
        Returns:
            dict: 命盘分析数据
        """
        try:
            # 提取八字四柱
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            
            # 提取五行数量
            element_counts = bazi_data.get('element_counts', {})
            
            # 提取旺衰数据
            wangshuai_data = {}
            if isinstance(wangshuai_result, dict):
                if wangshuai_result.get('success') and 'data' in wangshuai_result:
                    wangshuai_data = wangshuai_result.get('data', {})
                elif 'wangshuai' in wangshuai_result or 'xi_shen' in wangshuai_result:
                    wangshuai_data = wangshuai_result
            
            wangshuai = wangshuai_data.get('wangshuai', '')
            
            # 提取喜忌用神
            xi_ji = {
                'xi_shen': wangshuai_data.get('xi_shen', ''),
                'ji_shen': wangshuai_data.get('ji_shen', ''),
                'xi_ji_elements': wangshuai_data.get('xi_ji_elements', {})
            }
            
            # 如果 xi_ji_elements 为空，尝试从 final_xi_ji 中获取
            if not xi_ji.get('xi_ji_elements'):
                final_xi_ji = wangshuai_data.get('final_xi_ji', {})
                if final_xi_ji:
                    xi_ji['xi_ji_elements'] = {
                        'xi_shen': final_xi_ji.get('xi_shen_elements', []),
                        'ji_shen': final_xi_ji.get('ji_shen_elements', [])
                    }
            
            return {
                'bazi_pillars': bazi_pillars,
                'element_counts': element_counts,
                'wangshuai': wangshuai,
                'xi_ji': xi_ji
            }
        except Exception as e:
            logger.error(f"提取命盘分析数据失败: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def _extract_monthly_analysis(
        bazi_data: Dict[str, Any],
        detail_result: Dict[str, Any],
        target_year: int
    ) -> Dict[str, Any]:
        """
        提取流月解读数据（1-12月）
        
        Args:
            bazi_data: 八字基础数据
            detail_result: 详细计算结果
            target_year: 目标年份（如：2026）
            
        Returns:
            dict: 流月解读数据
            {
                'year': 2026,
                'months': [
                    {
                        'month': 1,
                        'jieqi': '小寒、大寒',
                        'wuyun_liuqi': '木运，初之气',
                        'qi_liudong': '气的流动',
                        'yingxiang': '对命主产生的影响',
                        'fengxian': '规避风险',
                        'yangsheng_jianyi': '养生建议'
                    },
                    ...
                ]
            }
        """
        try:
            months = []
            
            # 为1-12月逐月生成分析
            for month in range(1, 13):
                # 获取五运六气信息
                wuyun_liuqi = MonthlyFortuneService.get_wuyun_liuqi(target_year, month)
                
                # 获取节气信息
                jieqi_info = MonthlyFortuneService.get_jieqi_info(target_year, month)
                jieqi_list = jieqi_info.get('jieqi_list', [])
                jieqi_str = '、'.join(jieqi_list) if jieqi_list else ''
                
                # 分析流月影响
                monthly_impact = MonthlyFortuneService.analyze_monthly_impact(
                    target_year, month, bazi_data
                )
                
                months.append({
                    'month': month,
                    'jieqi': jieqi_str,
                    'wuyun_liuqi': wuyun_liuqi.get('description', ''),
                    'qi_liudong': f"{wuyun_liuqi.get('wuyun', '')}当令，{wuyun_liuqi.get('liuqi', '')}主事",
                    'yingxiang': monthly_impact.get('yingxiang', ''),
                    'fengxian': monthly_impact.get('fengxian', ''),
                    'yangsheng_jianyi': monthly_impact.get('yangsheng_jianyi', '')
                })
            
            return {
                'year': target_year,
                'months': months
            }
        except Exception as e:
            logger.error(f"提取流月解读数据失败: {e}", exc_info=True)
            return {
                'year': target_year,
                'months': []
            }
    
    @staticmethod
    def _extract_taisui_info(
        bazi_data: Dict[str, Any],
        target_year: int
    ) -> Dict[str, Any]:
        """
        提取流年太岁信息
        
        Args:
            bazi_data: 八字基础数据
            target_year: 目标年份（如：2026）
            
        Returns:
            dict: 流年太岁信息
        """
        try:
            # 获取太岁信息
            taisui_info = TaisuiService.get_taisui_info(target_year)
            if not taisui_info:
                return {}
            
            taisui_branch = taisui_info.get('branch', '')
            
            # 获取用户生肖（从年支提取）
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            year_branch = bazi_pillars.get('year', {}).get('branch', '')
            user_zodiac = BRANCH_ZODIAC.get(year_branch, '')
            
            # 判断犯太岁
            fanshaisui_result = TaisuiService.check_fanshaisui(user_zodiac, taisui_branch)
            
            # 获取化解建议
            fanshaisui_types = fanshaisui_result.get('fanshaisui_types', [])
            resolution_suggestions = TaisuiService.get_resolution_suggestions(
                fanshaisui_types, user_zodiac, taisui_info, bazi_data
            )
            
            # 获取躲星时间
            duoxing_times = TaisuiService.get_duoxing_times(target_year)
            
            # 格式化犯太岁信息
            fanshaisui_details = fanshaisui_result.get('fanshaisui_details', {})
            fanshaisui_dict = {}
            for fstype, detail in fanshaisui_details.items():
                zodiac = detail.get('zodiac', '')
                fanshaisui_dict[zodiac] = fstype
            
            return {
                'year': target_year,
                'taisui_name': taisui_info.get('taisui_name', ''),
                'taisui_description': taisui_info.get('taisui_description', ''),
                'fanshaisui': fanshaisui_dict,
                'resolution': resolution_suggestions,
                'duoxing_times': duoxing_times
            }
        except Exception as e:
            logger.error(f"提取流年太岁信息失败: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def _extract_fengshui_info(target_year: int) -> Dict[str, Any]:
        """
        提取九宫飞星避煞信息
        
        Args:
            target_year: 目标年份（如：2026）
            
        Returns:
            dict: 九宫飞星避煞信息
        """
        try:
            # 获取九宫飞星分布
            jiugong_feixing = FengshuiService.get_jiugong_feixing(target_year)
            
            # 获取五黄二黑方位
            wuhuang_erhei = FengshuiService.get_wuhuang_erhei(target_year)
            
            # 获取避煞时间
            bixing_times = FengshuiService.get_bixing_times(target_year)
            
            # 获取立春建议
            lichun_suggestions = FengshuiService.get_lichun_suggestions(target_year)
            
            return {
                'year': target_year,
                'jiugong_feixing': jiugong_feixing.get('positions', {}),
                'wuhuang': wuhuang_erhei.get('wuhuang', {}),
                'erhei': wuhuang_erhei.get('erhei', {}),
                'bixing_times': bixing_times,
                'lichun_suggestions': lichun_suggestions
            }
        except Exception as e:
            logger.error(f"提取九宫飞星避煞信息失败: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def format_input_data_for_coze(input_data: Dict[str, Any]) -> str:
        """
        格式化数据为JSON字符串（用于Coze Bot的{{input}}占位符）
        
        Args:
            input_data: 输入数据字典
            
        Returns:
            str: JSON格式的字符串
        """
        try:
            # 使用引用避免重复，节省Token
            # 这里可以优化，将重复的数据提取为引用
            formatted_json = json.dumps(input_data, ensure_ascii=False, indent=2)
            return formatted_json
        except Exception as e:
            logger.error(f"格式化数据失败: {e}", exc_info=True)
            return json.dumps({}, ensure_ascii=False)
    
    @staticmethod
    def validate_annual_report_input_data(input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证年运报告input_data的完整性
        
        Args:
            input_data: 输入数据字典
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            # 验证命盘分析
            mingpan_analysis = input_data.get('mingpan_analysis', {})
            if not mingpan_analysis:
                return False, "命盘分析数据缺失"
            if not mingpan_analysis.get('bazi_pillars'):
                return False, "命盘分析：八字四柱数据缺失"
            if not mingpan_analysis.get('element_counts'):
                return False, "命盘分析：五行数量数据缺失"
            if not mingpan_analysis.get('wangshuai'):
                return False, "命盘分析：旺衰数据缺失"
            if not mingpan_analysis.get('xi_ji'):
                return False, "命盘分析：喜忌用神数据缺失"
            
            # 验证流月解读
            monthly_analysis = input_data.get('monthly_analysis', {})
            if not monthly_analysis:
                return False, "流月解读数据缺失"
            months = monthly_analysis.get('months', [])
            if len(months) != 12:
                return False, f"流月解读：月份数据不完整（期望12个月，实际{len(months)}个月）"
            
            # 验证流年太岁
            taisui_info = input_data.get('taisui_info', {})
            if not taisui_info:
                return False, "流年太岁数据缺失"
            if not taisui_info.get('taisui_name'):
                return False, "流年太岁：太岁名称缺失"
            if not taisui_info.get('duoxing_times'):
                return False, "流年太岁：躲星时间缺失"
            
            # 验证九宫飞星避煞
            fengshui_info = input_data.get('fengshui_info', {})
            if not fengshui_info:
                return False, "九宫飞星避煞数据缺失"
            if not fengshui_info.get('wuhuang'):
                return False, "九宫飞星避煞：五黄星信息缺失"
            if not fengshui_info.get('erhei'):
                return False, "九宫飞星避煞：二黑星信息缺失"
            
            return True, None
        except Exception as e:
            logger.error(f"验证数据完整性失败: {e}", exc_info=True)
            return False, f"验证过程异常: {str(e)}"

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风水服务 - 提供九宫飞星、五黄二黑方位、避煞时间、立春建议等功能
"""

import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import logging

logger = logging.getLogger(__name__)


# 九宫飞星方位映射（根据年份计算）
# 九宫飞星每年会轮换位置
JIUGONG_FEIXING_POSITIONS = {
    # 2026年九宫飞星分布（示例，需要根据实际年份计算）
    2026: {
        '一白': '中宫',
        '二黑': '南·离宫',
        '三碧': '北·坎宫',
        '四绿': '西南·坤宫',
        '五黄': '东·震宫',
        '六白': '东南·巽宫',
        '七赤': '中宫',
        '八白': '西北·乾宫',
        '九紫': '西·兑宫',
    }
}

# 五黄二黑方位映射（根据年份计算）
WUHUANG_ERHEI_POSITIONS = {
    # 2026年五黄二黑方位（示例，需要根据实际年份计算）
    2026: {
        'wuhuang': {
            'direction': '东·震宫',
            'impact': '主灾祸、急性病',
            'resolution': '铜葫芦、五帝钱'
        },
        'erhei': {
            'direction': '南·离宫',
            'impact': '主病符、慢性病',
            'resolution': '白玉摆件、黑曜石'
        }
    }
}

# 避煞时间建议（按方位）
BIXING_TIMES = {
    '五黄在东': '每月初一、十五避免在东边活动，早上7-9点（辰时·土）少待东边',
    '二黑在南': '每月十五、三十避免在南边久坐，下午1-3点（未时·土）少待南边',
    '五黄在南': '每月初一、十五避免在南边活动，早上7-9点（辰时·土）少待南边',
    '二黑在北': '每月十五、三十避免在北边久坐，下午1-3点（未时·土）少待北边',
    # 可以根据实际方位添加更多
}

# 立春日期（示例，需要根据实际年份计算）
LICHUN_DATES = {
    2026: '2026-02-03',
    2027: '2027-02-04',
    # 可以根据实际年份添加更多
}


class FengshuiService:
    """风水服务"""
    
    @staticmethod
    def get_jiugong_feixing(year: int) -> Dict[str, Any]:
        """
        获取九宫飞星分布
        
        Args:
            year: 年份（如：2026）
            
        Returns:
            dict: 九宫飞星分布
            {
                'year': 2026,
                'positions': {
                    '一白': '中宫',
                    '二黑': '南·离宫',
                    ...
                }
            }
        """
        try:
            # 如果年份在配置中，直接返回
            if year in JIUGONG_FEIXING_POSITIONS:
                return {
                    'year': year,
                    'positions': JIUGONG_FEIXING_POSITIONS[year]
                }
            
            # 如果年份不在配置中，使用默认值或计算
            # 注意：这里需要根据实际年份计算九宫飞星位置
            # 暂时返回默认值
            logger.warning(f"年份 {year} 的九宫飞星配置不存在，使用默认值")
            return {
                'year': year,
                'positions': JIUGONG_FEIXING_POSITIONS.get(2026, {})
            }
        except Exception as e:
            logger.error(f"获取九宫飞星分布失败: {e}", exc_info=True)
            return {
                'year': year,
                'positions': {}
            }
    
    @staticmethod
    def get_wuhuang_erhei(year: int) -> Dict[str, Any]:
        """
        获取五黄二黑方位
        
        Args:
            year: 年份（如：2026）
            
        Returns:
            dict: 五黄二黑信息
            {
                'year': 2026,
                'wuhuang': {
                    'direction': '东·震宫',
                    'impact': '主灾祸、急性病',
                    'resolution': '铜葫芦、五帝钱'
                },
                'erhei': {
                    'direction': '南·离宫',
                    'impact': '主病符、慢性病',
                    'resolution': '白玉摆件、黑曜石'
                }
            }
        """
        try:
            # 如果年份在配置中，直接返回
            if year in WUHUANG_ERHEI_POSITIONS:
                result = WUHUANG_ERHEI_POSITIONS[year].copy()
                result['year'] = year
                return result
            
            # 如果年份不在配置中，使用默认值
            logger.warning(f"年份 {year} 的五黄二黑配置不存在，使用默认值")
            default = WUHUANG_ERHEI_POSITIONS.get(2026, {})
            result = default.copy()
            result['year'] = year
            return result
        except Exception as e:
            logger.error(f"获取五黄二黑方位失败: {e}", exc_info=True)
            return {
                'year': year,
                'wuhuang': {},
                'erhei': {}
            }
    
    @staticmethod
    def get_bixing_times(year: int, direction: Optional[str] = None) -> Dict[str, str]:
        """
        获取避煞时间（按方位给出具体时间建议）
        
        Args:
            year: 年份（如：2026）
            direction: 方位（可选，如：'东'、'南'等）
            
        Returns:
            dict: 避煞时间建议
            {
                '五黄在东': '每月初一、十五避免在东边活动，早上7-9点（辰时·土）少待东边',
                '二黑在南': '每月十五、三十避免在南边久坐，下午1-3点（未时·土）少待南边',
                ...
            }
        """
        try:
            # 获取五黄二黑方位
            wuhuang_erhei = FengshuiService.get_wuhuang_erhei(year)
            wuhuang_direction = wuhuang_erhei.get('wuhuang', {}).get('direction', '')
            erhei_direction = wuhuang_erhei.get('erhei', {}).get('direction', '')
            
            bixing_times = {}
            
            # 根据五黄方位生成避煞时间
            if wuhuang_direction:
                # 提取方位（如：'东·震宫' -> '东'）
                wuhuang_dir = wuhuang_direction.split('·')[0] if '·' in wuhuang_direction else wuhuang_direction
                key = f'五黄在{wuhuang_dir}'
                if key in BIXING_TIMES:
                    bixing_times[key] = BIXING_TIMES[key]
                else:
                    # 默认建议
                    bixing_times[key] = f'每月初一、十五避免在{wuhuang_dir}边活动，早上7-9点（辰时·土）少待{wuhuang_dir}边'
            
            # 根据二黑方位生成避煞时间
            if erhei_direction:
                # 提取方位（如：'南·离宫' -> '南'）
                erhei_dir = erhei_direction.split('·')[0] if '·' in erhei_direction else erhei_direction
                key = f'二黑在{erhei_dir}'
                if key in BIXING_TIMES:
                    bixing_times[key] = BIXING_TIMES[key]
                else:
                    # 默认建议
                    bixing_times[key] = f'每月十五、三十避免在{erhei_dir}边久坐，下午1-3点（未时·土）少待{erhei_dir}边'
            
            # 如果指定了方位，只返回该方位的建议
            if direction:
                filtered = {}
                for key, value in bixing_times.items():
                    if direction in key:
                        filtered[key] = value
                return filtered
            
            return bixing_times
        except Exception as e:
            logger.error(f"获取避煞时间失败: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def get_lichun_suggestions(year: int) -> str:
        """
        获取立春当日建议
        
        Args:
            year: 年份（如：2026）
            
        Returns:
            str: 立春建议（如：'立春（2月3日）当日清扫方位，保持通风明亮'）
        """
        try:
            # 获取立春日期
            lichun_date = LICHUN_DATES.get(year, '')
            if not lichun_date:
                # 如果年份不在配置中，使用默认值
                logger.warning(f"年份 {year} 的立春日期不存在，使用默认值")
                lichun_date = LICHUN_DATES.get(2026, '2026-02-03')
            
            # 解析日期
            from datetime import datetime
            date_obj = datetime.strptime(lichun_date, '%Y-%m-%d')
            month_day = f"{date_obj.month}月{date_obj.day}日"
            
            return f"立春（{month_day}）当日清扫方位，保持通风明亮"
        except Exception as e:
            logger.error(f"获取立春建议失败: {e}", exc_info=True)
            return f"立春当日清扫方位，保持通风明亮"

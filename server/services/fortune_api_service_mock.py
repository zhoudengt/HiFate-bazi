#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运势API服务 - 模拟版本（用于测试，不依赖真实API）
当没有配置真实API密钥时，可以使用此服务进行测试

.. deprecated::
    本模块为 Mock 实现，混在生产代码中。建议后续迁移至 tests/mocks/
    当前被 fortune_api_service 作为降级使用，迁移时需同步更新导入路径。
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import random

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class FortuneAPIServiceMock:
    """运势API服务 - 模拟版本（用于测试）"""
    
    # 模拟运势数据模板
    FORTUNE_TEMPLATES = {
        'overall': [
            "整体运势较好，适合开展新计划。",
            "整体运势平稳，保持现状即可。",
            "整体运势一般，需要谨慎行事。",
            "整体运势良好，把握机会。",
            "整体运势不错，适合社交活动。"
        ],
        'career': [
            "事业运势良好，工作进展顺利。",
            "事业运势平稳，按部就班即可。",
            "事业运势一般，需要更加努力。",
            "事业运势不错，适合拓展业务。",
            "事业运势良好，容易获得认可。"
        ],
        'love': [
            "感情运势良好，与伴侣关系融洽。",
            "感情运势平稳，保持沟通即可。",
            "感情运势一般，需要多些耐心。",
            "感情运势不错，适合表达心意。",
            "感情运势良好，单身者有机会遇到心仪对象。"
        ],
        'wealth': [
            "财运一般，需要理性消费。",
            "财运平稳，收支平衡。",
            "财运不错，可能有意外收入。",
            "财运良好，适合投资理财。",
            "财运一般，避免冲动消费。"
        ],
        'health': [
            "健康运势良好，身体状况不错。",
            "健康运势平稳，注意休息。",
            "健康运势一般，需要多运动。",
            "健康运势不错，保持良好作息。",
            "健康运势良好，精力充沛。"
        ],
        'lucky_color': ['红色', '蓝色', '绿色', '黄色', '紫色', '橙色', '粉色'],
        'lucky_number': ['1', '3', '5', '7', '8', '9', '11'],
        'lucky_direction': ['东方', '西方', '南方', '北方', '东南', '西南', '东北', '西北']
    }
    
    def __init__(self):
        """初始化模拟服务"""
        logger.info("使用运势API模拟服务（测试模式）")
    
    def get_daily_fortune(
        self,
        constellation: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取今日运势（模拟）
        
        Args:
            constellation: 星座名称（中文）
            date: 日期字符串 YYYY-MM-DD
            
        Returns:
            运势数据字典
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if not constellation:
            constellation = self._get_constellation_from_date(date)
        
        # 根据日期生成稳定的随机数（相同日期得到相同结果）
        random.seed(date)
        
        return {
            'success': True,
            'provider': 'mock',
            'constellation': constellation,
            'date': date,
            'fortune': {
                'overall': random.choice(self.FORTUNE_TEMPLATES['overall']),
                'career': random.choice(self.FORTUNE_TEMPLATES['career']),
                'love': random.choice(self.FORTUNE_TEMPLATES['love']),
                'wealth': random.choice(self.FORTUNE_TEMPLATES['wealth']),
                'health': random.choice(self.FORTUNE_TEMPLATES['health']),
                'lucky_color': random.choice(self.FORTUNE_TEMPLATES['lucky_color']),
                'lucky_number': random.choice(self.FORTUNE_TEMPLATES['lucky_number']),
                'lucky_direction': random.choice(self.FORTUNE_TEMPLATES['lucky_direction'])
            }
        }
    
    def get_monthly_fortune(
        self,
        constellation: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取本月运势（模拟）
        
        Args:
            constellation: 星座名称（中文）
            year: 年份
            month: 月份
            
        Returns:
            运势数据字典
        """
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        date_str = f"{year}-{month:02d}-01"
        
        if not constellation:
            constellation = self._get_constellation_from_date(date_str)
        
        # 根据年月生成稳定的随机数
        random.seed(f"{year}-{month}")
        
        return {
            'success': True,
            'provider': 'mock',
            'constellation': constellation,
            'year': year,
            'month': month,
            'fortune': {
                'overall': random.choice(self.FORTUNE_TEMPLATES['overall']),
                'career': random.choice(self.FORTUNE_TEMPLATES['career']),
                'love': random.choice(self.FORTUNE_TEMPLATES['love']),
                'wealth': random.choice(self.FORTUNE_TEMPLATES['wealth']),
                'health': random.choice(self.FORTUNE_TEMPLATES['health'])
            }
        }
    
    def _get_constellation_from_date(self, date_str: str) -> str:
        """根据日期计算星座"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            day = date_obj.day
            
            if (month == 3 and day >= 21) or (month == 4 and day <= 19):
                return '白羊座'
            elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
                return '金牛座'
            elif (month == 5 and day >= 21) or (month == 6 and day <= 21):
                return '双子座'
            elif (month == 6 and day >= 22) or (month == 7 and day <= 22):
                return '巨蟹座'
            elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
                return '狮子座'
            elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
                return '处女座'
            elif (month == 9 and day >= 23) or (month == 10 and day <= 23):
                return '天秤座'
            elif (month == 10 and day >= 24) or (month == 11 and day <= 22):
                return '天蝎座'
            elif (month == 11 and day >= 23) or (month == 12 and day <= 21):
                return '射手座'
            elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
                return '摩羯座'
            elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
                return '水瓶座'
            else:
                return '双鱼座'
        except Exception as e:
            logger.error(f"计算星座失败: {e}")
            return '白羊座'


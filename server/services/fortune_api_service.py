#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运势API服务 - 调用第三方运势API
支持今日运势和本月运势
"""

import os
import sys
import logging
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class FortuneAPIService:
    """运势API服务 - 调用第三方运势API"""
    
    # 支持的API提供商
    API_PROVIDERS = {
        'jisuapi': {
            'name': '极速数据',
            'base_url': 'https://api.jisuapi.com',
            'daily_endpoint': '/astro/day',
            'monthly_endpoint': '/astro/month',
            'api_key_env': 'JISUAPI_KEY'
        },
        'tianapi': {
            'name': '天聚数行',
            'base_url': 'https://api.tianapi.com',
            'daily_endpoint': '/astro/index',
            'monthly_endpoint': '/astro/month',
            'api_key_env': 'TIANAPI_KEY'
        },
        '6api': {
            'name': '六派数据',
            'base_url': 'https://api.6api.net',
            'daily_endpoint': '/astro/day',
            'monthly_endpoint': '/astro/month',
            'api_key_env': 'API6API_KEY'
        }
    }
    
    # 星座映射（从生肖或八字推算星座，这里简化处理）
    CONSTELLATION_MAP = {
        'Aries': '白羊座',
        'Taurus': '金牛座',
        'Gemini': '双子座',
        'Cancer': '巨蟹座',
        'Leo': '狮子座',
        'Virgo': '处女座',
        'Libra': '天秤座',
        'Scorpio': '天蝎座',
        'Sagittarius': '射手座',
        'Capricorn': '摩羯座',
        'Aquarius': '水瓶座',
        'Pisces': '双鱼座'
    }
    
    def __init__(self, provider: str = None, use_mock: bool = False):
        """
        初始化运势API服务
        
        Args:
            provider: API提供商名称（jisuapi/tianapi/6api），默认自动选择
            use_mock: 是否使用模拟服务（用于测试，不依赖真实API）
        """
        self.use_mock = use_mock
        
        if use_mock:
            # 使用模拟服务
            from .fortune_api_service_mock import FortuneAPIServiceMock
            self.mock_service = FortuneAPIServiceMock()
            logger.info("使用运势API模拟服务（测试模式）")
            return
        
        self.provider = provider or self._auto_select_provider()
        self.config = self.API_PROVIDERS.get(self.provider)
        
        if not self.config:
            raise ValueError(f"不支持的API提供商: {self.provider}")
        
        self.api_key = os.getenv(self.config['api_key_env'])
        if not self.api_key:
            logger.warning(f"未配置 {self.config['name']} API密钥 ({self.config['api_key_env']})")
            # 如果没有配置API密钥，自动切换到模拟模式
            logger.info("自动切换到模拟模式（测试）")
            from .fortune_api_service_mock import FortuneAPIServiceMock
            self.mock_service = FortuneAPIServiceMock()
            self.use_mock = True
    
    def _auto_select_provider(self) -> str:
        """自动选择可用的API提供商"""
        for provider_name, config in self.API_PROVIDERS.items():
            api_key = os.getenv(config['api_key_env'])
            if api_key:
                logger.info(f"选择API提供商: {config['name']} ({provider_name})")
                return provider_name
        
        # 如果没有配置任何API密钥，默认使用第一个
        logger.warning("未配置任何API密钥，使用默认提供商（需要配置API密钥才能正常工作）")
        return 'jisuapi'
    
    def _get_constellation_from_date(self, date_str: str) -> str:
        """
        根据日期计算星座（简化版本）
        
        Args:
            date_str: 日期字符串 YYYY-MM-DD
            
        Returns:
            星座名称（中文）
        """
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            day = date_obj.day
            
            # 简化的星座判断（实际应该根据用户出生日期计算）
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
            return '白羊座'  # 默认值
    
    def get_daily_fortune(
        self,
        constellation: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取今日运势
        
        Args:
            constellation: 星座名称（中文），如果不提供则根据日期计算
            date: 日期字符串 YYYY-MM-DD，默认为今天
            
        Returns:
            运势数据字典
        """
        # 如果使用模拟服务
        if self.use_mock:
            return self.mock_service.get_daily_fortune(constellation, date)
        
        if not self.api_key:
            # 如果没有API密钥，自动切换到模拟模式
            logger.info("未配置API密钥，自动切换到模拟模式")
            from .fortune_api_service_mock import FortuneAPIServiceMock
            mock_service = FortuneAPIServiceMock()
            return mock_service.get_daily_fortune(constellation, date)
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if not constellation:
            constellation = self._get_constellation_from_date(date)
        
        try:
            # 根据不同的API提供商调用不同的接口
            if self.provider == 'jisuapi':
                return self._call_jisuapi_daily(constellation, date)
            elif self.provider == 'tianapi':
                return self._call_tianapi_daily(constellation, date)
            elif self.provider == '6api':
                return self._call_6api_daily(constellation, date)
            else:
                return {
                    'success': False,
                    'error': f'不支持的API提供商: {self.provider}'
                }
        except Exception as e:
            logger.error(f"获取今日运势失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'获取今日运势失败: {str(e)}'
            }
    
    def get_monthly_fortune(
        self,
        constellation: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取本月运势
        
        Args:
            constellation: 星座名称（中文），如果不提供则根据日期计算
            year: 年份，默认为今年
            month: 月份，默认为本月
            
        Returns:
            运势数据字典
        """
        # 如果使用模拟服务
        if self.use_mock:
            return self.mock_service.get_monthly_fortune(constellation, year, month)
        
        if not self.api_key:
            # 如果没有API密钥，自动切换到模拟模式
            logger.info("未配置API密钥，自动切换到模拟模式")
            from .fortune_api_service_mock import FortuneAPIServiceMock
            mock_service = FortuneAPIServiceMock()
            return mock_service.get_monthly_fortune(constellation, year, month)
        
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        date_str = f"{year}-{month:02d}-01"
        
        if not constellation:
            constellation = self._get_constellation_from_date(date_str)
        
        try:
            # 根据不同的API提供商调用不同的接口
            if self.provider == 'jisuapi':
                return self._call_jisuapi_monthly(constellation, year, month)
            elif self.provider == 'tianapi':
                return self._call_tianapi_monthly(constellation, year, month)
            elif self.provider == '6api':
                return self._call_6api_monthly(constellation, year, month)
            else:
                return {
                    'success': False,
                    'error': f'不支持的API提供商: {self.provider}'
                }
        except Exception as e:
            logger.error(f"获取本月运势失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'获取本月运势失败: {str(e)}'
            }
    
    def _call_jisuapi_daily(self, constellation: str, date: str) -> Dict[str, Any]:
        """调用极速数据今日运势API"""
        url = f"{self.config['base_url']}{self.config['daily_endpoint']}"
        params = {
            'appkey': self.api_key,
            'astro': constellation,
            'date': date
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == '0' and data.get('result'):
            result = data['result']
            return {
                'success': True,
                'provider': 'jisuapi',
                'constellation': constellation,
                'date': date,
                'fortune': {
                    'overall': result.get('summary', ''),
                    'career': result.get('career', ''),
                    'love': result.get('love', ''),
                    'wealth': result.get('wealth', ''),
                    'health': result.get('health', ''),
                    'lucky_color': result.get('color', ''),
                    'lucky_number': result.get('number', ''),
                    'lucky_direction': result.get('QFriend', '')
                }
            }
        else:
            return {
                'success': False,
                'error': data.get('msg', 'API调用失败')
            }
    
    def _call_jisuapi_monthly(self, constellation: str, year: int, month: int) -> Dict[str, Any]:
        """调用极速数据本月运势API"""
        url = f"{self.config['base_url']}{self.config['monthly_endpoint']}"
        params = {
            'appkey': self.api_key,
            'astro': constellation,
            'year': year,
            'month': month
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == '0' and data.get('result'):
            result = data['result']
            return {
                'success': True,
                'provider': 'jisuapi',
                'constellation': constellation,
                'year': year,
                'month': month,
                'fortune': {
                    'overall': result.get('summary', ''),
                    'career': result.get('career', ''),
                    'love': result.get('love', ''),
                    'wealth': result.get('wealth', ''),
                    'health': result.get('health', '')
                }
            }
        else:
            return {
                'success': False,
                'error': data.get('msg', 'API调用失败')
            }
    
    def _call_tianapi_daily(self, constellation: str, date: str) -> Dict[str, Any]:
        """调用天聚数行今日运势API"""
        url = f"{self.config['base_url']}{self.config['daily_endpoint']}"
        params = {
            'key': self.api_key,
            'astro': constellation
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') == 200 and data.get('newslist'):
            result = data['newslist'][0] if data['newslist'] else {}
            return {
                'success': True,
                'provider': 'tianapi',
                'constellation': constellation,
                'date': date,
                'fortune': {
                    'overall': result.get('content', ''),
                    'career': result.get('work', ''),
                    'love': result.get('love', ''),
                    'wealth': result.get('money', ''),
                    'health': result.get('health', ''),
                    'lucky_color': result.get('color', ''),
                    'lucky_number': result.get('number', '')
                }
            }
        else:
            return {
                'success': False,
                'error': data.get('msg', 'API调用失败')
            }
    
    def _call_tianapi_monthly(self, constellation: str, year: int, month: int) -> Dict[str, Any]:
        """调用天聚数行本月运势API"""
        url = f"{self.config['base_url']}{self.config['monthly_endpoint']}"
        params = {
            'key': self.api_key,
            'astro': constellation,
            'year': year,
            'month': month
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') == 200 and data.get('newslist'):
            result = data['newslist'][0] if data['newslist'] else {}
            return {
                'success': True,
                'provider': 'tianapi',
                'constellation': constellation,
                'year': year,
                'month': month,
                'fortune': {
                    'overall': result.get('content', ''),
                    'career': result.get('work', ''),
                    'love': result.get('love', ''),
                    'wealth': result.get('money', ''),
                    'health': result.get('health', '')
                }
            }
        else:
            return {
                'success': False,
                'error': data.get('msg', 'API调用失败')
            }
    
    def _call_6api_daily(self, constellation: str, date: str) -> Dict[str, Any]:
        """调用六派数据今日运势API"""
        url = f"{self.config['base_url']}{self.config['daily_endpoint']}"
        params = {
            'appkey': self.api_key,
            'astro': constellation,
            'date': date
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') == 200 and data.get('data'):
            result = data['data']
            return {
                'success': True,
                'provider': '6api',
                'constellation': constellation,
                'date': date,
                'fortune': {
                    'overall': result.get('summary', ''),
                    'career': result.get('career', ''),
                    'love': result.get('love', ''),
                    'wealth': result.get('wealth', ''),
                    'health': result.get('health', ''),
                    'lucky_color': result.get('color', ''),
                    'lucky_number': result.get('number', '')
                }
            }
        else:
            return {
                'success': False,
                'error': data.get('msg', 'API调用失败')
            }
    
    def _call_6api_monthly(self, constellation: str, year: int, month: int) -> Dict[str, Any]:
        """调用六派数据本月运势API"""
        url = f"{self.config['base_url']}{self.config['monthly_endpoint']}"
        params = {
            'appkey': self.api_key,
            'astro': constellation,
            'year': year,
            'month': month
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') == 200 and data.get('data'):
            result = data['data']
            return {
                'success': True,
                'provider': '6api',
                'constellation': constellation,
                'year': year,
                'month': month,
                'fortune': {
                    'overall': result.get('summary', ''),
                    'career': result.get('career', ''),
                    'love': result.get('love', ''),
                    'wealth': result.get('wealth', ''),
                    'health': result.get('health', '')
                }
            }
        else:
            return {
                'success': False,
                'error': data.get('msg', 'API调用失败')
            }


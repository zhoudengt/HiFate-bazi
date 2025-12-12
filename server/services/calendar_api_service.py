#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万年历API服务 - 调用第三方万年历API
支持查询指定日期的万年历信息
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


class CalendarAPIService:
    """万年历API服务 - 调用第三方万年历API"""
    
    # 支持的API提供商
    API_PROVIDERS = {
        'jisuapi': {
            'name': '极速数据',
            'base_url': 'https://api.jisuapi.com',
            'calendar_endpoint': '/calendar/day',
            'api_key_env': 'JISUAPI_KEY'
        },
        'tianapi': {
            'name': '天聚数行',
            'base_url': 'https://api.tianapi.com',
            'calendar_endpoint': '/lunar/index',
            'api_key_env': 'TIANAPI_KEY'
        },
        '6api': {
            'name': '六派数据',
            'base_url': 'https://api.6api.net',
            'calendar_endpoint': '/calendar/day',
            'api_key_env': 'API6API_KEY'
        }
    }
    
    # 星期几映射
    WEEKDAY_MAP = {
        'Monday': '星期一',
        'Tuesday': '星期二',
        'Wednesday': '星期三',
        'Thursday': '星期四',
        'Friday': '星期五',
        'Saturday': '星期六',
        'Sunday': '星期日'
    }
    
    def __init__(self, provider: str = None, use_mock: bool = False):
        """
        初始化万年历API服务
        
        Args:
            provider: API提供商名称（jisuapi/tianapi/6api），默认自动选择
            use_mock: 是否使用模拟服务（用于测试，不依赖真实API）
        """
        self.use_mock = use_mock
        
        if use_mock:
            logger.info("使用万年历API模拟服务（测试模式）")
            return
        
        self.provider = provider or self._auto_select_provider()
        self.config = self.API_PROVIDERS.get(self.provider)
        
        if not self.config:
            raise ValueError(f"不支持的API提供商: {self.provider}")
        
        self.api_key = os.getenv(self.config['api_key_env'])
        if not self.api_key:
            logger.warning(f"未配置 {self.config['name']} API密钥 ({self.config['api_key_env']})")
            logger.info("将使用本地计算模式")
    
    def _auto_select_provider(self) -> str:
        """自动选择可用的API提供商"""
        for provider_name, config in self.API_PROVIDERS.items():
            api_key = os.getenv(config['api_key_env'])
            if api_key:
                logger.info(f"选择API提供商: {config['name']} ({provider_name})")
                return provider_name
        
        # 如果没有配置任何API密钥，默认使用第一个
        logger.warning("未配置任何API密钥，将使用本地计算模式")
        return 'jisuapi'
    
    def get_calendar(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取万年历信息
        
        Args:
            date: 日期字符串 YYYY-MM-DD，默认为今天
            
        Returns:
            万年历数据字典
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 解析日期
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return {
                'success': False,
                'error': f'日期格式错误: {date}，应为 YYYY-MM-DD'
            }
        
        # 计算星期几
        weekday_en = date_obj.strftime('%A')
        weekday_cn = self.WEEKDAY_MAP.get(weekday_en, weekday_en)
        
        # 如果有API密钥，尝试调用第三方API
        if self.api_key and not self.use_mock:
            try:
                if self.provider == 'jisuapi':
                    return self._call_jisuapi(date)
                elif self.provider == 'tianapi':
                    return self._call_tianapi(date)
                elif self.provider == '6api':
                    return self._call_6api(date)
            except Exception as e:
                logger.warning(f"调用第三方API失败，使用本地计算: {e}")
        
        # 使用本地计算（农历和干支）
        return self._calculate_local(date, date_obj, weekday_cn, weekday_en)
    
    def _calculate_local(self, date: str, date_obj: datetime, weekday_cn: str, weekday_en: str) -> Dict[str, Any]:
        """使用本地计算万年历信息（使用 lunar_python 库）"""
        try:
            from lunar_python import Solar
            
            # 创建阳历对象
            solar = Solar.fromYmd(date_obj.year, date_obj.month, date_obj.day)
            lunar = solar.getLunar()
            
            # 获取农历日期
            lunar_year_cn = lunar.getYearInChinese()
            lunar_month_cn = lunar.getMonthInChinese()
            lunar_day_cn = lunar.getDayInChinese()
            lunar_date_str = f"农历{lunar_month_cn}月{lunar_day_cn}"
            
            # 获取生肖和星座
            shengxiao = lunar.getYearShengXiao()
            xingzuo = solar.getXingZuo()
            
            # 获取八字干支
            bazi = lunar.getBaZi()
            year_ganzhi = bazi[0] if len(bazi) > 0 else ''
            month_ganzhi = bazi[1] if len(bazi) > 1 else ''
            day_ganzhi = bazi[2] if len(bazi) > 2 else ''
            hour_ganzhi = bazi[3] if len(bazi) > 3 else ''
            
            # 获取八字五行
            bazi_wuxing = lunar.getBaZiWuXing() or []
            
            # 获取八字纳音
            bazi_nayin = lunar.getBaZiNaYin() or []
            
            # 获取宜忌
            yi_list = lunar.getDayYi() or []
            ji_list = lunar.getDayJi() or []
            
            # 获取神煞方位
            xi_shen = lunar.getDayPositionXiDesc() or ''  # 喜神方位
            cai_shen = lunar.getDayPositionCaiDesc() or ''  # 财神方位
            fu_shen = lunar.getDayPositionFuDesc() or ''  # 福神方位
            yang_gui = lunar.getDayPositionYangGuiDesc() or ''  # 阳贵方位
            yin_gui = lunar.getDayPositionYinGuiDesc() or ''  # 阴贵方位
            
            # 获取冲煞信息
            chong_desc = lunar.getDayChongDesc() or ''  # 冲（如：(丙子)鼠）
            sha_desc = lunar.getDaySha() or ''  # 煞方位（如：北）
            
            # 获取合（六合）
            day_branch = day_ganzhi[1] if len(day_ganzhi) > 1 else ''
            from src.data.relations import BRANCH_LIUHE
            from src.data.stems_branches import BRANCH_ZODIAC
            he_branch = BRANCH_LIUHE.get(day_branch, '')
            he_zodiac = BRANCH_ZODIAC.get(he_branch, '')
            
            # 获取星宿信息
            xiu = lunar.getXiu() or ''  # 星宿
            xiu_luck = lunar.getXiuLuck() or ''  # 星宿吉凶
            xiu_song = lunar.getXiuSong() or ''  # 星宿歌诀
            zheng = lunar.getZheng() or ''  # 政（五行）
            animal = lunar.getAnimal() or ''  # 星宿动物
            
            # 获取彭祖百忌
            pengzu_gan = lunar.getPengZuGan() or ''  # 天干
            pengzu_zhi = lunar.getPengZuZhi() or ''  # 地支
            
            # 获取吉神凶煞
            ji_shen = lunar.getDayJiShen() or []  # 吉神
            xiong_sha = lunar.getDayXiongSha() or []  # 凶煞
            
            # 获取九星
            year_nine_star = str(lunar.getYearNineStar()) if lunar.getYearNineStar() else ''
            month_nine_star = str(lunar.getMonthNineStar()) if lunar.getMonthNineStar() else ''
            day_nine_star = str(lunar.getDayNineStar()) if lunar.getDayNineStar() else ''
            
            # 获取六曜、建除十二神、月相
            liu_yao = lunar.getLiuYao() or ''  # 六曜
            zhi_xing = lunar.getZhiXing() or ''  # 建除十二神
            yue_xiang = lunar.getYueXiang() or ''  # 月相
            
            # 获取物候
            wu_hou = lunar.getWuHou() or ''  # 物候
            hou = lunar.getHou() or ''  # 候（节气+第几候）
            
            # 获取节气
            jie_qi = lunar.getJieQi() or ''  # 当天节气（如果有）
            
            # 获取节日
            solar_festivals = solar.getFestivals() or []
            solar_other_festivals = solar.getOtherFestivals() or []
            lunar_festivals = lunar.getFestivals() or []
            lunar_other_festivals = lunar.getOtherFestivals() or []
            all_festivals = solar_festivals + solar_other_festivals + lunar_festivals + lunar_other_festivals
            
            # 计算吉凶等级（基于宜忌数量和吉神凶煞）
            yi_count = len(yi_list)
            ji_count = len(ji_list)
            ji_shen_count = len(ji_shen)
            xiong_sha_count = len(xiong_sha)
            
            # 综合评分
            score = (yi_count - ji_count) * 2 + (ji_shen_count - xiong_sha_count)
            if score >= 15:
                luck_level = '大吉'
            elif score >= 8:
                luck_level = '吉'
            elif score <= -10:
                luck_level = '大凶'
            elif score <= -5:
                luck_level = '凶'
            else:
                luck_level = '中平'
            
            return {
                'success': True,
                'provider': 'local',
                'date': date,
                'solar_date': f"{date_obj.year}年{date_obj.month}月{date_obj.day}日",
                'weekday': weekday_cn,
                'weekday_en': weekday_en,
                'lunar_date': lunar_date_str,
                'lunar_year': lunar_year_cn,
                'shengxiao': shengxiao,  # 生肖
                'xingzuo': xingzuo,  # 星座
                'ganzhi': {
                    'year': year_ganzhi,
                    'month': month_ganzhi,
                    'day': day_ganzhi,
                    'hour': hour_ganzhi  # 子时干支（默认）
                },
                'wuxing': bazi_wuxing,  # 八字五行
                'nayin': bazi_nayin,  # 八字纳音
                'yi': yi_list,
                'ji': ji_list,
                'luck_level': luck_level,
                'deities': {
                    'xishen': xi_shen,
                    'caishen': cai_shen,
                    'fushen': fu_shen,
                    'yanggui': yang_gui,  # 阳贵
                    'yingui': yin_gui  # 阴贵
                },
                'chong_he_sha': {
                    'chong': chong_desc,
                    'he': he_zodiac,
                    'sha': sha_desc
                },
                # 新增字段
                'xingxiu': {  # 星宿
                    'name': xiu,
                    'luck': xiu_luck,
                    'song': xiu_song,
                    'zheng': zheng,
                    'animal': animal
                },
                'pengzu': {  # 彭祖百忌
                    'gan': pengzu_gan,
                    'zhi': pengzu_zhi
                },
                'shensha': {  # 吉神凶煞
                    'jishen': ji_shen,
                    'xiongsha': xiong_sha
                },
                'jiuxing': {  # 九星
                    'year': year_nine_star,
                    'month': month_nine_star,
                    'day': day_nine_star
                },
                'other': {  # 其他
                    'liuyao': liu_yao,  # 六曜
                    'zhixing': zhi_xing,  # 建除十二神
                    'yuexiang': yue_xiang,  # 月相
                    'wuhou': wu_hou,  # 物候
                    'hou': hou,  # 候
                    'jieqi': jie_qi  # 节气
                },
                'festivals': all_festivals  # 节日
            }
        except Exception as e:
            logger.error(f"本地计算万年历失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'计算万年历失败: {str(e)}'
            }
    
    def _call_jisuapi(self, date: str) -> Dict[str, Any]:
        """调用极速数据万年历API"""
        url = f"{self.config['base_url']}{self.config['calendar_endpoint']}"
        params = {
            'appkey': self.api_key,
            'date': date
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '0' and data.get('result'):
                result = data['result']
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                weekday_en = date_obj.strftime('%A')
                weekday_cn = self.WEEKDAY_MAP.get(weekday_en, weekday_en)
                
                return {
                    'success': True,
                    'provider': 'jisuapi',
                    'date': date,
                    'solar_date': result.get('solar', f"{date_obj.year}年{date_obj.month}月{date_obj.day}日"),
                    'weekday': weekday_cn,
                    'weekday_en': weekday_en,
                    'lunar_date': result.get('lunar', ''),
                    'ganzhi': {
                        'year': result.get('year', ''),
                        'month': result.get('month', ''),
                        'day': result.get('day', '')
                    },
                    'yi': result.get('yi', []),
                    'ji': result.get('ji', []),
                    'luck_level': result.get('luck', ''),
                    'deities': {
                        'fucai': result.get('fucai', ''),
                        'caishen': result.get('caishen', ''),
                        'xishen': result.get('xishen', '')
                    },
                    'chong_he_sha': {
                        'chong': result.get('chong', ''),
                        'he': result.get('he', ''),
                        'sha': result.get('sha', '')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': data.get('msg', 'API调用失败')
                }
        except Exception as e:
            logger.error(f"调用极速数据API失败: {e}")
            raise
    
    def _call_tianapi(self, date: str) -> Dict[str, Any]:
        """调用天聚数行万年历API"""
        url = f"{self.config['base_url']}{self.config['calendar_endpoint']}"
        params = {
            'key': self.api_key,
            'date': date
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 200 and data.get('newslist'):
                result = data['newslist'][0] if data['newslist'] else {}
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                weekday_en = date_obj.strftime('%A')
                weekday_cn = self.WEEKDAY_MAP.get(weekday_en, weekday_en)
                
                return {
                    'success': True,
                    'provider': 'tianapi',
                    'date': date,
                    'solar_date': f"{date_obj.year}年{date_obj.month}月{date_obj.day}日",
                    'weekday': weekday_cn,
                    'weekday_en': weekday_en,
                    'lunar_date': result.get('lunar', ''),
                    'ganzhi': {
                        'year': result.get('year', ''),
                        'month': result.get('month', ''),
                        'day': result.get('day', '')
                    },
                    'yi': result.get('yi', []),
                    'ji': result.get('ji', []),
                    'luck_level': result.get('luck', ''),
                    'deities': {
                        'fucai': result.get('fucai', ''),
                        'caishen': result.get('caishen', ''),
                        'xishen': result.get('xishen', '')
                    },
                    'chong_he_sha': {
                        'chong': result.get('chong', ''),
                        'he': result.get('he', ''),
                        'sha': result.get('sha', '')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': data.get('msg', 'API调用失败')
                }
        except Exception as e:
            logger.error(f"调用天聚数行API失败: {e}")
            raise
    
    def _call_6api(self, date: str) -> Dict[str, Any]:
        """调用六派数据万年历API"""
        url = f"{self.config['base_url']}{self.config['calendar_endpoint']}"
        params = {
            'appkey': self.api_key,
            'date': date
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 200 and data.get('data'):
                result = data['data']
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                weekday_en = date_obj.strftime('%A')
                weekday_cn = self.WEEKDAY_MAP.get(weekday_en, weekday_en)
                
                return {
                    'success': True,
                    'provider': '6api',
                    'date': date,
                    'solar_date': f"{date_obj.year}年{date_obj.month}月{date_obj.day}日",
                    'weekday': weekday_cn,
                    'weekday_en': weekday_en,
                    'lunar_date': result.get('lunar', ''),
                    'ganzhi': {
                        'year': result.get('year', ''),
                        'month': result.get('month', ''),
                        'day': result.get('day', '')
                    },
                    'yi': result.get('yi', []),
                    'ji': result.get('ji', []),
                    'luck_level': result.get('luck', ''),
                    'deities': {
                        'fucai': result.get('fucai', ''),
                        'caishen': result.get('caishen', ''),
                        'xishen': result.get('xishen', '')
                    },
                    'chong_he_sha': {
                        'chong': result.get('chong', ''),
                        'he': result.get('he', ''),
                        'sha': result.get('sha', '')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': data.get('msg', 'API调用失败')
                }
        except Exception as e:
            logger.error(f"调用六派数据API失败: {e}")
            raise

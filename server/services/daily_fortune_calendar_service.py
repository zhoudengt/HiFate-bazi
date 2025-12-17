#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日运势日历服务
基于万年历接口，提供完整的每日运势信息
"""

import sys
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.calendar_api_service import CalendarAPIService
from server.config.mysql_config import get_mysql_connection, return_mysql_connection


class DailyFortuneCalendarService:
    """每日运势日历服务"""
    
    @staticmethod
    def get_daily_fortune_calendar(
        date_str: Optional[str] = None,
        user_solar_date: Optional[str] = None,
        user_solar_time: Optional[str] = None,
        user_gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取每日运势日历信息
        
        Args:
            date_str: 查询日期（可选，默认为今天），格式：YYYY-MM-DD
            user_solar_date: 用户生辰阳历日期（可选，用于十神提示），格式：YYYY-MM-DD
            user_solar_time: 用户生辰时间（可选），格式：HH:MM
            user_gender: 用户性别（可选），male/female
            
        Returns:
            dict: 包含完整的每日运势信息
        """
        try:
            # 1. 获取万年历基础信息
            calendar_service = CalendarAPIService()
            calendar_result = calendar_service.get_calendar(date=date_str)
            
            if not calendar_result.get('success'):
                return {
                    'success': False,
                    'error': calendar_result.get('error', '获取万年历信息失败')
                }
            
            # 2. 计算流年、流月、流日
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            liunian, liuyue, liuri = DailyFortuneCalendarService.calculate_liunian_liuyue_liuri(target_date)
            
            # 3. 获取六十甲子运势
            # 数据库存储格式是"甲子日"，所以直接使用liuri（已经是"乙卯日"格式）
            jiazi_fortune = DailyFortuneCalendarService.get_jiazi_fortune(liuri)
            
            # 4. 获取十神提示（需要用户生辰）
            shishen_hint = None
            if user_solar_date and user_solar_time and user_gender:
                # 获取当日日干
                day_stem = DailyFortuneCalendarService._get_day_stem(target_date)
                
                # 优先从 /bazi/pan/display 接口获取用户生辰日干
                birth_stem = None
                try:
                    from server.services.bazi_display_service import BaziDisplayService
                    pan_result = BaziDisplayService.get_pan_display(
                        user_solar_date, user_solar_time, user_gender
                    )
                    if pan_result.get('success'):
                        # 从返回结果中提取日干：pan.pillars[2].stem.char（日柱是索引2）
                        pan_data = pan_result.get('pan', {})
                        pillars = pan_data.get('pillars', [])
                        if isinstance(pillars, list) and len(pillars) > 2:
                            # 日柱是索引2
                            day_pillar = pillars[2]
                            if isinstance(day_pillar, dict):
                                stem_data = day_pillar.get('stem', {})
                                if isinstance(stem_data, dict):
                                    birth_stem = stem_data.get('char', '')
                except Exception as e:
                    import traceback
                    print(f"从 /bazi/pan/display 接口获取日干失败，回退到原有方式: {e}\n{traceback.format_exc()}")
                
                # 如果接口调用失败，回退到原有方式
                if not birth_stem:
                    birth_stem = DailyFortuneCalendarService._get_birth_stem(user_solar_date, user_solar_time, user_gender)
                
                if day_stem and birth_stem:
                    shishen_hint = DailyFortuneCalendarService.get_shishen_hint(day_stem, birth_stem)
            
            # 5. 获取生肖刑冲破害
            day_branch = DailyFortuneCalendarService._get_day_branch(target_date)
            zodiac_relations = DailyFortuneCalendarService.get_zodiac_relations(day_branch) if day_branch else None
            
            # 6. 获取建除十二神能量小结
            jianchu = calendar_result.get('other', {}).get('zhixing', '')  # 建除十二神
            jianchu_summary = DailyFortuneCalendarService.get_jianchu_summary(jianchu) if jianchu else None
            
            # 7. 组装返回结果
            return {
                'success': True,
                # 基础万年历信息
                'solar_date': calendar_result.get('solar_date', ''),
                'lunar_date': calendar_result.get('lunar_date', ''),
                'weekday': calendar_result.get('weekday', ''),
                'weekday_en': calendar_result.get('weekday_en', ''),
                # 流年流月流日
                'liunian': liunian,
                'liuyue': liuyue,
                'liuri': liuri,
                # 万年历信息
                'yi': calendar_result.get('yi', []),
                'ji': calendar_result.get('ji', []),
                'luck_level': calendar_result.get('luck_level', ''),
                'deities': calendar_result.get('deities', {}),
                'chong_he_sha': calendar_result.get('chong_he_sha', {}),
                'jianchu': jianchu,
                # 运势内容
                'jiazi_fortune': jiazi_fortune,
                'shishen_hint': shishen_hint,
                'zodiac_relations': zodiac_relations,
                'jianchu_summary': jianchu_summary
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': f'获取每日运势异常: {str(e)}\n{traceback.format_exc()}'
            }
    
    @staticmethod
    def calculate_liunian_liuyue_liuri(target_date: date) -> Tuple[str, str, str]:
        """
        计算流年、流月、流日
        
        Args:
            target_date: 目标日期
            
        Returns:
            tuple: (流年, 流月, 流日) 格式：("甲辰年", "戊子月", "乙卯日")
        """
        try:
            from lunar_python import Solar
            
            # 创建阳历对象
            solar = Solar.fromYmd(target_date.year, target_date.month, target_date.day)
            lunar = solar.getLunar()
            
            # 获取八字干支
            bazi = lunar.getBaZi()
            year_ganzhi = bazi[0] if len(bazi) > 0 else ''  # 年柱干支
            month_ganzhi = bazi[1] if len(bazi) > 1 else ''  # 月柱干支
            day_ganzhi = bazi[2] if len(bazi) > 2 else ''    # 日柱干支
            
            # 格式化输出
            liunian = f"{year_ganzhi}年" if year_ganzhi else ""
            liuyue = f"{month_ganzhi}月" if month_ganzhi else ""
            liuri = f"{day_ganzhi}日" if day_ganzhi else ""
            
            return liunian, liuyue, liuri
            
        except Exception as e:
            import traceback
            print(f"计算流年流月流日失败: {e}\n{traceback.format_exc()}")
            return "", "", ""
    
    @staticmethod
    def _get_day_stem(target_date: date) -> Optional[str]:
        """获取指定日期的日干"""
        try:
            from lunar_python import Solar
            solar = Solar.fromYmd(target_date.year, target_date.month, target_date.day)
            lunar = solar.getLunar()
            bazi = lunar.getBaZi()
            if len(bazi) > 2:
                day_ganzhi = bazi[2]
                return day_ganzhi[0] if len(day_ganzhi) > 0 else None
            return None
        except:
            return None
    
    @staticmethod
    def _get_day_branch(target_date: date) -> Optional[str]:
        """获取指定日期的日支"""
        try:
            from lunar_python import Solar
            solar = Solar.fromYmd(target_date.year, target_date.month, target_date.day)
            lunar = solar.getLunar()
            bazi = lunar.getBaZi()
            if len(bazi) > 2:
                day_ganzhi = bazi[2]
                return day_ganzhi[1] if len(day_ganzhi) > 1 else None
            return None
        except:
            return None
    
    @staticmethod
    def _get_birth_stem(solar_date: str, solar_time: str, gender: str) -> Optional[str]:
        """获取用户生辰日干"""
        try:
            # 使用BaziService计算用户八字
            from server.services.bazi_service import BaziService
            bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
            if not bazi_result:
                return None
            
            # 提取日干
            bazi_data = bazi_result.get('bazi', bazi_result)
            day_pillar = bazi_data.get('bazi_pillars', {}).get('day', {})
            return day_pillar.get('stem')
        except:
            return None
    
    @staticmethod
    def get_jiazi_fortune(jiazi_day: str) -> Optional[str]:
        """
        获取六十甲子运势
        
        Args:
            jiazi_day: 甲子日（如："乙丑日"或"乙丑"，数据库存储格式为"乙丑日"）
            
        Returns:
            str: 整体运势内容，如果未找到返回None
        """
        # 如果传入的格式不带"日"，自动添加
        if not jiazi_day.endswith('日'):
            jiazi_day = jiazi_day + '日'
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # 🔴 修复：enabled 字段可能是 NULL 或 0，使用 COALESCE 处理
                cursor.execute(
                    "SELECT content FROM daily_fortune_jiazi WHERE jiazi_day = %s AND COALESCE(enabled, 1) = 1",
                    (jiazi_day,)
                )
                result = cursor.fetchone()
                if result:
                    return result.get('content')
                return None
        except Exception as e:
            print(f"查询六十甲子运势失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            return_mysql_connection(conn)
    
    @staticmethod
    def get_shishen_hint(day_stem: str, birth_stem: str) -> Optional[str]:
        """
        获取十神提示
        
        Args:
            day_stem: 当日日干（如："甲"）
            birth_stem: 命主日干（如："己"）
            
        Returns:
            str: 十神提示内容（包含十神提示和十神象义提示词），如果未找到返回None
        """
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # 1. 查询十神
                # 🔴 修复：enabled 字段可能是 NULL 或 0，使用 COALESCE 处理
                cursor.execute(
                    "SELECT shishen FROM daily_fortune_shishen_query WHERE day_stem = %s AND birth_stem = %s AND COALESCE(enabled, 1) = 1",
                    (day_stem, birth_stem)
                )
                query_result = cursor.fetchone()
                if not query_result:
                    return None
                
                shishen = query_result.get('shishen')
                
                # 2. 查询十神象义
                # 🔴 修复：enabled 字段可能是 NULL 或 0，使用 COALESCE 处理
                cursor.execute(
                    "SELECT hint, hint_keywords FROM daily_fortune_shishen_meaning WHERE shishen = %s AND COALESCE(enabled, 1) = 1",
                    (shishen,)
                )
                meaning_result = cursor.fetchone()
                if not meaning_result:
                    return None
                
                hint = meaning_result.get('hint', '')
                hint_keywords = meaning_result.get('hint_keywords', '')
                
                # 3. 组合输出
                if hint_keywords:
                    return f"{hint}今日提示词：{hint_keywords}"
                else:
                    return hint
                    
        except Exception as e:
            print(f"查询十神提示失败: {e}")
            return None
        finally:
            return_mysql_connection(conn)
    
    @staticmethod
    def get_zodiac_relations(day_branch: str) -> Optional[str]:
        """
        获取生肖刑冲破害
        
        Args:
            day_branch: 日支（如："辰"）
            
        Returns:
            str: 生肖简运内容（按合、冲、刑、破、害顺序），如果未找到返回None
        """
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # 查询所有关系
                # 🔴 修复：enabled 字段可能是 NULL 或 0，使用 COALESCE 处理
                cursor.execute(
                    "SELECT relation_type, target_branch, target_zodiac, content FROM daily_fortune_zodiac WHERE day_branch = %s AND COALESCE(enabled, 1) = 1 ORDER BY FIELD(relation_type, '合', '冲', '刑', '破', '害')",
                    (day_branch,)
                )
                results = cursor.fetchall()
                
                if not results:
                    return None
                
                # 按顺序组合输出
                lines = []
                for row in results:
                    relation_type = row.get('relation_type', '')
                    target_zodiac = row.get('target_zodiac', '')
                    target_branch = row.get('target_branch', '')
                    content = row.get('content', '')
                    
                    # 格式化：合 狗 (戌)：合作运佳，易遇诚信伙伴。
                    line = f"{relation_type} {target_zodiac} ({target_branch})：{content}"
                    lines.append(line)
                
                return "\n".join(lines)
                
        except Exception as e:
            print(f"查询生肖刑冲破害失败: {e}")
            return None
        finally:
            return_mysql_connection(conn)
    
    @staticmethod
    def get_jianchu_summary(jianchu: str) -> Optional[str]:
        """
        获取建除十二神能量小结
        
        Args:
            jianchu: 建除十二神（如："定"）
            
        Returns:
            str: 能量小结内容，如果未找到返回None
        """
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # 🔴 修复：enabled 字段可能是 NULL 或 0，使用 COALESCE 处理
                cursor.execute(
                    "SELECT content FROM daily_fortune_jianchu WHERE jianchu = %s AND COALESCE(enabled, 1) = 1",
                    (jianchu,)
                )
                result = cursor.fetchone()
                if result:
                    return result.get('content')
                return None
        except Exception as e:
            print(f"查询建除十二神能量小结失败: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            return_mysql_connection(conn)


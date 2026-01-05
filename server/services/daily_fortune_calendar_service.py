#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日运势日历服务
基于万年历接口，提供完整的每日运势信息
"""

import sys
import os
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.calendar_api_service import CalendarAPIService
from server.config.mysql_config import get_mysql_connection, return_mysql_connection


class DailyFortuneCalendarService:
    """每日运势日历服务"""
    
    # Redis缓存TTL（24小时，因为每日运势每天变化）
    CACHE_TTL = 86400
    
    @staticmethod
    def _generate_cache_key(
        date_str: Optional[str],
        user_solar_date: Optional[str],
        user_solar_time: Optional[str],
        user_gender: Optional[str]
    ) -> str:
        """
        生成缓存键
        
        Args:
            date_str: 查询日期
            user_solar_date: 用户生辰阳历日期
            user_solar_time: 用户生辰时间
            user_gender: 用户性别
            
        Returns:
            str: 缓存键（格式：daily_fortune:calendar:{date}:{user_solar_date}:{user_solar_time}:{user_gender}）
        """
        # 标准化参数
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            date_key = target_date.strftime('%Y-%m-%d')
        else:
            date_key = date.today().strftime('%Y-%m-%d')
        
        user_solar_date = user_solar_date or ''
        user_solar_time = user_solar_time or ''
        user_gender = user_gender or ''
        
        # 生成键（使用完整字符串，不使用MD5，便于调试和清理）
        key_parts = [
            'daily_fortune',
            'calendar',
            date_key,
            user_solar_date,
            user_solar_time,
            user_gender
        ]
        return ':'.join(key_parts)
    
    @staticmethod
    def _query_from_database(
        date_str: Optional[str] = None,
        user_solar_date: Optional[str] = None,
        user_solar_time: Optional[str] = None,
        user_gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从数据库查询每日运势日历信息（原有逻辑，用于缓存未命中时调用）
        
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
            
            # 即使万年历API失败，也尝试返回基本数据
            if not calendar_result.get('success'):
                # 使用默认值，确保基本功能可用
                calendar_result = {
                    'success': True,
                    'solar_date': f"{target_date.year}年{target_date.month}月{target_date.day}日" if date_str else "",
                    'lunar_date': '',
                    'weekday': '',
                    'weekday_en': '',
                    'yi': [],
                    'ji': [],
                    'luck_level': '',
                    'deities': {},
                    'chong_he_sha': {},
                    'other': {}
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
            
            # 6. 获取建除十二神能量小结（包含能量值）
            jianchu = calendar_result.get('other', {}).get('zhixing', '')  # 建除十二神
            jianchu_info = None
            if jianchu:
                jianchu_info = DailyFortuneCalendarService.get_jianchu_info(jianchu)
                # 如果查询失败，至少返回名称
                if not jianchu_info:
                    jianchu_info = {'name': jianchu, 'energy': None, 'summary': None}
            else:
                # 即使万年历API失败，也尝试从日期计算建除（需要lunar_python）
                # 如果lunar_python不可用，至少返回一个默认值
                try:
                    from lunar_python import Solar
                    solar = Solar.fromYmd(target_date.year, target_date.month, target_date.day)
                    lunar = solar.getLunar()
                    jianchu = lunar.getDayJianChu()  # 获取建除
                    if jianchu:
                        jianchu_info = DailyFortuneCalendarService.get_jianchu_info(jianchu)
                        if not jianchu_info:
                            jianchu_info = {'name': jianchu, 'energy': None, 'summary': None}
                except ImportError:
                    # lunar_python不可用，跳过
                    pass
                except Exception as e:
                    print(f"计算建除失败: {e}")
                    pass
            
            # 7. 获取胎神信息
            taishen = calendar_result.get('deities', {}).get('taishen', '')
            taishen_explanation = calendar_result.get('deities', {}).get('taishen_explanation', '')
            
            # 8. 获取命主信息（即使万年历API失败，也尝试计算日主）
            master_info = DailyFortuneCalendarService.get_master_info(
                target_date, user_solar_date, user_solar_time, user_gender
            )
            # 如果master_info为None，至少返回日主（不包含今日十神）
            if not master_info:
                try:
                    day_stem = DailyFortuneCalendarService._get_day_stem(target_date)
                    if day_stem:
                        rizhu = DailyFortuneCalendarService._get_stem_element(day_stem)
                        if rizhu:
                            master_info = {'rizhu': rizhu, 'today_shishen': None}
                except Exception as e:
                    print(f"计算日主失败: {e}")
                    pass
            
            # 9. 获取五行穿搭（原幸运颜色）
            wuxing_wear = DailyFortuneCalendarService.get_lucky_colors(
                target_date, user_solar_date, user_solar_time, user_gender, calendar_result
            )
            
            # 10. 获取贵人方位（原贵人指路）
            guiren_fangwei = DailyFortuneCalendarService.get_guiren_directions(
                target_date, calendar_result
            )
            
            # 11. 获取瘟神方位
            wenshen_directions = DailyFortuneCalendarService.get_wenshen_directions(
                target_date, calendar_result
            )
            
            # 12. 组装返回结果
            return {
                'success': True,
                # 基础万年历信息
                'solar_date': calendar_result.get('solar_date', ''),
                'lunar_date': calendar_result.get('lunar_date', ''),
                'weekday': calendar_result.get('weekday', ''),
                'weekday_en': calendar_result.get('weekday_en', ''),
                # 当天干支信息
                'year_pillar': liunian,
                'month_pillar': liuyue,
                'day_pillar': liuri,
                # 万年历信息
                'yi': calendar_result.get('yi', []),
                'ji': calendar_result.get('ji', []),
                'luck_level': calendar_result.get('luck_level', ''),
                'deities': calendar_result.get('deities', {}),
                'chong_he_sha': calendar_result.get('chong_he_sha', {}),
                # 建除信息（包含能量值）
                'jianchu': jianchu_info,
                # 胎神信息
                'taishen': taishen,
                'taishen_explanation': taishen_explanation,
                # 运势内容
                'jiazi_fortune': jiazi_fortune,
                'shishen_hint': shishen_hint,
                'zodiac_relations': zodiac_relations,
                # 新增功能
                'master_info': master_info,
                'wuxing_wear': wuxing_wear,
                'guiren_fangwei': guiren_fangwei,
                'wenshen_directions': wenshen_directions
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': f'获取每日运势异常: {str(e)}\n{traceback.format_exc()}'
            }
    
    @staticmethod
    def get_daily_fortune_calendar(
        date_str: Optional[str] = None,
        user_solar_date: Optional[str] = None,
        user_solar_time: Optional[str] = None,
        user_gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取每日运势日历信息（带Redis缓存）
        
        Args:
            date_str: 查询日期（可选，默认为今天），格式：YYYY-MM-DD
            user_solar_date: 用户生辰阳历日期（可选，用于十神提示），格式：YYYY-MM-DD
            user_solar_time: 用户生辰时间（可选），格式：HH:MM
            user_gender: 用户性别（可选），male/female
            
        Returns:
            dict: 包含完整的每日运势信息
        """
        # 1. 生成缓存键
        cache_key = DailyFortuneCalendarService._generate_cache_key(
            date_str, user_solar_date, user_solar_time, user_gender
        )
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                # 缓存命中，直接返回（0个数据库连接）
                return cached_result
        except Exception as e:
            # Redis不可用，降级到数据库查询
            print(f"⚠️  Redis缓存不可用，降级到数据库查询: {e}")
        
        # 3. 缓存未命中，查询数据库
        result = DailyFortuneCalendarService._query_from_database(
            date_str, user_solar_date, user_solar_time, user_gender
        )
        
        # 4. 写入缓存（仅成功时）
        if result.get('success'):
            try:
                from server.utils.cache_multi_level import get_multi_cache
                cache = get_multi_cache()
                # 使用自定义TTL（24小时）
                cache.l2.ttl = DailyFortuneCalendarService.CACHE_TTL
                cache.set(cache_key, result)
                # 恢复默认TTL
                cache.l2.ttl = 3600
            except Exception as e:
                # 缓存写入失败不影响业务
                print(f"⚠️  缓存写入失败（不影响业务）: {e}")
        
        return result
    
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
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT content FROM daily_fortune_jiazi WHERE jiazi_day = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                    (jiazi_day,)
                )
                result = cursor.fetchone()
                if result:
                    content = result.get('content')
                    if content and isinstance(content, str):
                        if '\\n' in content:
                            content = content.replace('\\n', '\n')
                    return content
                return None
        except Exception as e:
            print(f"查询六十甲子运势失败: {e}")
            return None
        finally:
            if conn:
                try:
                    return_mysql_connection(conn)
                except:
                    pass
    
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
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None
            with conn.cursor() as cursor:
                # 1. 查询十神
                cursor.execute(
                    "SELECT shishen FROM daily_fortune_shishen_query WHERE day_stem = %s AND birth_stem = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                    (day_stem, birth_stem)
                )
                query_result = cursor.fetchone()
                if not query_result:
                    return None
                
                shishen = query_result.get('shishen')
                
                # 十神名称映射（偏官 = 七杀）
                shishen_mapping = {
                    '偏官': '七杀',
                    '偏印': '偏印',
                }
                mapped_shishen = shishen_mapping.get(shishen, shishen)
                
                # 2. 查询十神象义
                cursor.execute(
                    "SELECT hint, hint_keywords FROM daily_fortune_shishen_meaning WHERE shishen = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                    (mapped_shishen,)
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
            if conn:
                try:
                    return_mysql_connection(conn)
                except:
                    pass
    
    @staticmethod
    def get_zodiac_relations(day_branch: str) -> Optional[str]:
        """
        获取生肖刑冲破害
        
        Args:
            day_branch: 日支（如："辰"）
            
        Returns:
            str: 生肖简运内容（按合、冲、刑、破、害顺序），如果未找到返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None
            with conn.cursor() as cursor:
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
                    
                    line = f"{relation_type} {target_zodiac} ({target_branch})：{content}"
                    lines.append(line)
                
                return "\n".join(lines)
                
        except Exception as e:
            print(f"查询生肖刑冲破害失败: {e}")
            return None
        finally:
            if conn:
                try:
                    return_mysql_connection(conn)
                except:
                    pass
    
    @staticmethod
    def get_jianchu_summary(jianchu: str) -> Optional[str]:
        """
        获取建除十二神能量小结（保留用于向后兼容）
        
        Args:
            jianchu: 建除十二神（如："定"）
            
        Returns:
            str: 能量小结内容，如果未找到返回None
        """
        jianchu_info = DailyFortuneCalendarService.get_jianchu_info(jianchu)
        return jianchu_info.get('summary') if jianchu_info else None
    
    @staticmethod
    def get_jianchu_info(jianchu: str) -> Optional[Dict[str, Any]]:
        """
        获取建除十二神信息（包含能量值）
        
        Args:
            jianchu: 建除十二神（如："定"）
            
        Returns:
            dict: 包含 name, energy, summary 的字典，如果未找到返回None
        """
        if not jianchu:
            return None
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None
            with conn.cursor() as cursor:
                # 检查score列是否存在，如果不存在就不查询score
                cursor.execute("SHOW COLUMNS FROM daily_fortune_jianchu LIKE 'score'")
                has_score = cursor.fetchone() is not None
                
                if has_score:
                    cursor.execute(
                        "SELECT jianchu, content, score FROM daily_fortune_jianchu WHERE BINARY jianchu = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                        (jianchu,)
                    )
                else:
                    cursor.execute(
                        "SELECT jianchu, content FROM daily_fortune_jianchu WHERE BINARY jianchu = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                        (jianchu,)
                    )
                result = cursor.fetchone()
                if result:
                    score_value = result.get('score') if has_score else None
                    # 如果score为None，返回None（让前端显示"暂无"）
                    # 注意：score=0是有效值，不应该转换为None
                    # 只有score为None时才返回None
                    return {
                        'name': result.get('jianchu', jianchu),
                        'energy': score_value,  # 保留原始值（包括0），字段名改为energy
                        'summary': result.get('content', '')
                    }
                # 如果数据库中没有数据，至少返回名称
                return {
                    'name': jianchu,
                    'energy': None,
                    'summary': None
                }
        except Exception as e:
            print(f"查询建除十二神信息失败: {e}")
            return None
        finally:
            if conn:
                try:
                    return_mysql_connection(conn)
                except:
                    pass
    
    @staticmethod
    def get_master_info(
        target_date: date,
        user_solar_date: Optional[str] = None,
        user_solar_time: Optional[str] = None,
        user_gender: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        获取命主信息
        
        Args:
            target_date: 目标日期
            user_solar_date: 用户生辰阳历日期（可选）
            user_solar_time: 用户生辰时间（可选）
            user_gender: 用户性别（可选）
            
        Returns:
            dict: 包含 rizhu (日主), today_shishen (今日十神) 的字典
        """
        try:
            # 获取当日日干
            day_stem = DailyFortuneCalendarService._get_day_stem(target_date)
            if not day_stem:
                return None
            
            # 获取日主（日干 + 五行）
            rizhu = DailyFortuneCalendarService._get_stem_element(day_stem)
            if not rizhu:
                return None
            
            # 获取今日十神（需要用户生辰）
            today_shishen = None
            if user_solar_date and user_solar_time and user_gender:
                try:
                    birth_stem = DailyFortuneCalendarService._get_birth_stem(user_solar_date, user_solar_time, user_gender)
                    if day_stem and birth_stem:
                        # 查询十神
                        shishen = DailyFortuneCalendarService._get_shishen_from_stems(day_stem, birth_stem)
                        if shishen:
                            today_shishen = shishen
                except:
                    pass  # 十神查询失败不影响日主显示
            else:
                # 如果没有提供用户生辰信息，返回提示信息
                # 前端会根据是否有用户登录信息显示不同的提示
                today_shishen = "需要提供生辰信息"
            
            return {
                'rizhu': rizhu,
                'today_shishen': today_shishen
            }
        except Exception as e:
            print(f"获取命主信息失败: {e}")
            return None
    
    @staticmethod
    def _get_stem_element(stem: str) -> str:
        """
        获取天干对应的五行
        
        Args:
            stem: 天干（如："甲"）
            
        Returns:
            str: 天干 + 五行（如："甲木"）
        """
        element_map = {
            '甲': '木', '乙': '木',
            '丙': '火', '丁': '火',
            '戊': '土', '己': '土',
            '庚': '金', '辛': '金',
            '壬': '水', '癸': '水'
        }
        element = element_map.get(stem, '')
        return f"{stem}{element}" if element else stem
    
    @staticmethod
    def _get_shishen_from_stems(day_stem: str, birth_stem: str) -> Optional[str]:
        """
        根据日干和命主日干查询十神
        
        Args:
            day_stem: 当日日干
            birth_stem: 命主日干
            
        Returns:
            str: 十神名称，如果未找到返回None
        """
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT shishen FROM daily_fortune_shishen_query WHERE day_stem = %s AND birth_stem = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                    (day_stem, birth_stem)
                )
                result = cursor.fetchone()
                if result:
                    return result.get('shishen')
                return None
        except Exception as e:
            print(f"查询十神失败: {e}")
            return None
        finally:
            if conn:
                try:
                    return_mysql_connection(conn)
                except:
                    pass
    
    @staticmethod
    def _filter_colors_to_limit(colors: list, max_count: int = 4) -> list:
        """
        如果颜色数量超过限制，删除相近的颜色
        
        Args:
            colors: 颜色列表
            max_count: 最大颜色数量（默认4）
            
        Returns:
            筛选后的颜色列表
        """
        if len(colors) <= max_count:
            return colors
        
        import difflib
        
        # 找出两个最相近的颜色
        max_similarity = 0.0
        similar_pair = None
        
        for i in range(len(colors)):
            for j in range(i + 1, len(colors)):
                color1 = colors[i]
                color2 = colors[j]
                # 计算字符串相似度
                similarity = difflib.SequenceMatcher(None, color1, color2).ratio()
                if similarity > max_similarity:
                    max_similarity = similarity
                    similar_pair = (i, j)
        
        # 如果找到相近的颜色对（相似度 >= 0.6），删除其中一个
        if similar_pair and max_similarity >= 0.6:
            # 保留列表中靠前的颜色，删除靠后的
            remove_index = similar_pair[1]
            filtered_colors = [c for idx, c in enumerate(colors) if idx != remove_index]
            # 递归调用，确保最终数量 <= max_count
            return DailyFortuneCalendarService._filter_colors_to_limit(filtered_colors, max_count)
        else:
            # 如果没有找到相近的颜色，删除最后一个（保持顺序）
            return colors[:max_count]
    
    @staticmethod
    def get_lucky_colors(
        target_date: date,
        user_solar_date: Optional[str],
        user_solar_time: Optional[str],
        user_gender: Optional[str],
        calendar_result: Dict[str, Any]
    ) -> str:
        """
        获取幸运颜色
        
        Args:
            target_date: 目标日期
            user_solar_date: 用户生辰阳历日期（可选）
            user_solar_time: 用户生辰时间（可选）
            user_gender: 用户性别（可选）
            calendar_result: 万年历结果
            
        Returns:
            str: 幸运颜色（逗号分隔），如果未找到返回空字符串
        """
        colors = []
        
        # 1. 从万年历获取喜神、福神方位
        deities = calendar_result.get('deities', {})
        xishen_direction = deities.get('xishen', '')
        fushen_direction = deities.get('fushen', '')
        
        # 2. 查询万年历方位对应的颜色
        conn = None
        try:
            conn = get_mysql_connection()
            if not conn:
                return None  # 返回None而不是空字符串
            with conn.cursor() as cursor:
                # 查询喜神方位颜色（使用BINARY比较确保编码正确）
                if xishen_direction:
                    cursor.execute(
                        "SELECT colors FROM daily_fortune_lucky_color_wannianli WHERE BINARY direction = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                        (xishen_direction,)
                    )
                    result = cursor.fetchone()
                    if result:
                        colors_str = result.get('colors', '')
                        if colors_str:
                            # 处理颜色字符串（可能是"、"或","分隔）
                            colors_list = [c.strip() for c in colors_str.replace('、', ',').split(',') if c.strip()]
                            colors.extend(colors_list)
                
                # 查询福神方位颜色（使用BINARY比较确保编码正确）
                if fushen_direction:
                    cursor.execute(
                        "SELECT colors FROM daily_fortune_lucky_color_wannianli WHERE BINARY direction = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                        (fushen_direction,)
                    )
                    result = cursor.fetchone()
                    if result:
                        colors_str = result.get('colors', '')
                        if colors_str:
                            colors_list = [c.strip() for c in colors_str.replace('、', ',').split(',') if c.strip()]
                            colors.extend(colors_list)
                
                # 3. 查询今日十神颜色（需要用户生辰且为喜用）
                if user_solar_date and user_solar_time and user_gender:
                    day_stem = DailyFortuneCalendarService._get_day_stem(target_date)
                    birth_stem = DailyFortuneCalendarService._get_birth_stem(user_solar_date, user_solar_time, user_gender)
                    
                    if day_stem and birth_stem:
                        # 获取今日十神
                        today_shishen = DailyFortuneCalendarService._get_shishen_from_stems(day_stem, birth_stem)
                        
                        if today_shishen:
                            # 判断是否为喜用
                            is_xishen = DailyFortuneCalendarService._is_shishen_xishen(
                                user_solar_date, user_solar_time, user_gender, today_shishen
                            )
                            
                            if is_xishen:
                                # 查询十神颜色（使用BINARY比较确保编码正确）
                                cursor.execute(
                                    "SELECT color FROM daily_fortune_lucky_color_shishen WHERE BINARY shishen = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                                    (today_shishen,)
                                )
                                result = cursor.fetchone()
                                if result:
                                    color = result.get('color', '').strip()
                                    if color:
                                        colors.append(color)
        except Exception as e:
            print(f"获取幸运颜色失败: {e}")
        finally:
            if conn:
                try:
                    return_mysql_connection(conn)
                except:
                    pass
        
        # 去重并返回
        unique_colors = list(dict.fromkeys(colors))  # 保持顺序的去重
        
        # 如果颜色数量 > 4，删除相近的颜色
        filtered_colors = DailyFortuneCalendarService._filter_colors_to_limit(unique_colors, max_count=4)
        
        result = '、'.join(filtered_colors) if filtered_colors else ''
        # 如果没有任何颜色，返回None而不是空字符串，让前端显示"暂无"
        if not result:
            return None
        return result if result else None
    
    @staticmethod
    def _is_shishen_xishen(
        user_solar_date: str,
        user_solar_time: str,
        user_gender: str,
        shishen: str
    ) -> bool:
        """
        判断十神是否为喜用神
        
        Args:
            user_solar_date: 用户生辰阳历日期
            user_solar_time: 用户生辰时间
            user_gender: 用户性别
            shishen: 十神名称
            
        Returns:
            bool: 是否为喜用神
        """
        try:
            from server.services.wangshuai_service import WangShuaiService
            
            # 调用旺衰服务获取喜忌神
            wangshuai_result = WangShuaiService.calculate_wangshuai(
                user_solar_date, user_solar_time, user_gender
            )
            
            if not wangshuai_result.get('success'):
                return False
            
            data = wangshuai_result.get('data', {})
            xi_ji = data.get('xi_ji', {})
            xi_shen_list = xi_ji.get('xi_shen', [])
            
            # 判断十神是否在喜神列表中
            return shishen in xi_shen_list
        except Exception as e:
            print(f"判断十神是否为喜用失败: {e}")
            return False
    
    @staticmethod
    def get_guiren_directions(
        target_date: date,
        calendar_result: Dict[str, Any]
    ) -> str:
        """
        获取贵人指路
        
        Args:
            target_date: 目标日期
            calendar_result: 万年历结果
            
        Returns:
            str: 贵人指路（逗号分隔），如果未找到返回空字符串
        """
        directions = []
        
        # 1. 从万年历获取喜神、福神方位
        deities = calendar_result.get('deities', {})
        xishen_direction = deities.get('xishen', '')
        fushen_direction = deities.get('fushen', '')
        
        if xishen_direction:
            directions.append(xishen_direction)
        if fushen_direction:
            directions.append(fushen_direction)
        
        # 2. 获取当日日干
        day_stem = DailyFortuneCalendarService._get_day_stem(target_date)
        
        # 3. 查询日干对应方位
        if day_stem:
            conn = None
            try:
                conn = get_mysql_connection()
                if conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT directions FROM daily_fortune_guiren_direction WHERE day_stem = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                            (day_stem,)
                        )
                        result = cursor.fetchone()
                        if result:
                            directions_str = result.get('directions', '')
                            if directions_str:
                                # 处理方位字符串（可能是"、"或","分隔）
                                directions_list = [d.strip() for d in directions_str.replace('、', ',').split(',') if d.strip()]
                                directions.extend(directions_list)
            except Exception as e:
                print(f"获取贵人指路失败: {e}")
            finally:
                if conn:
                    try:
                        return_mysql_connection(conn)
                    except:
                        pass
        
        # 去重并返回
        unique_directions = list(dict.fromkeys(directions))  # 保持顺序的去重
        return '、'.join(unique_directions) if unique_directions else ''
    
    @staticmethod
    def get_wenshen_directions(
        target_date: date,
        calendar_result: Dict[str, Any]
    ) -> str:
        """
        获取瘟神方位
        
        Args:
            target_date: 目标日期
            calendar_result: 万年历结果
            
        Returns:
            str: 瘟神方位（逗号分隔），如果未找到返回空字符串
        """
        directions = []
        
        # 1. 从万年历获取煞方位
        chong_he_sha = calendar_result.get('chong_he_sha', {})
        sha_direction = chong_he_sha.get('sha', '')
        
        if sha_direction:
            directions.append(sha_direction)
        
        # 2. 获取当日日支
        day_branch = DailyFortuneCalendarService._get_day_branch(target_date)
        
        # 3. 查询日支对应方位
        if day_branch:
            conn = None
            try:
                conn = get_mysql_connection()
                if conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT direction FROM daily_fortune_wenshen_direction WHERE day_branch = %s AND COALESCE(enabled, 1) = 1 LIMIT 1",
                            (day_branch,)
                        )
                        result = cursor.fetchone()
                        if result:
                            direction = result.get('direction', '').strip()
                            if direction:
                                directions.append(direction)
            except Exception as e:
                print(f"获取瘟神方位失败: {e}")
            finally:
                if conn:
                    try:
                        return_mysql_connection(conn)
                    except:
                        pass
        
        # 去重并返回
        unique_directions = list(dict.fromkeys(directions))  # 保持顺序的去重
        return '、'.join(unique_directions) if unique_directions else ''
    
    @staticmethod
    def invalidate_cache_for_date(target_date: Optional[str] = None):
        """
        使指定日期的缓存失效（支持双机同步）
        
        Args:
            target_date: 目标日期（可选，默认为今天），格式：YYYY-MM-DD
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            from server.config.redis_config import get_redis_client
            
            # 1. 清理本地L1缓存
            cache = get_multi_cache()
            cache.l1.clear()  # 清空所有L1缓存（简单实现）
            
            # 2. 清理Redis缓存（支持pattern匹配）
            redis_client = get_redis_client()
            if redis_client:
                if target_date:
                    # 清理指定日期的缓存
                    pattern = f"daily_fortune:calendar:{target_date}:*"
                else:
                    # 清理所有每日运势缓存
                    pattern = "daily_fortune:calendar:*"
                
                # 使用SCAN迭代删除（避免阻塞）
                cursor = 0
                deleted_count = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted_count += redis_client.delete(*keys)
                    if cursor == 0:
                        break
                
                # 3. 发布缓存失效事件（双机同步）
                try:
                    redis_client.publish('cache:invalidate:daily_fortune', target_date or 'all')
                except Exception as e:
                    print(f"⚠️  发布缓存失效事件失败: {e}")
                
                print(f"✅ 已清理每日运势缓存: {deleted_count} 条（日期: {target_date or 'all'}）")
        except Exception as e:
            print(f"⚠️  缓存失效操作失败（不影响业务）: {e}")


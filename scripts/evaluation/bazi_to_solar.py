# -*- coding: utf-8 -*-
"""
八字反推公历日期

根据八字四柱反推公历日期和时间
年柱取最接近现在的年份，时柱取时辰中间时刻
"""

from typing import Optional, Tuple, Dict
from datetime import datetime
from lunar_python import Solar, Lunar

from .bazi_to_time import BaziToTimeConverter


class BaziToSolarConverter:
    """八字反推公历日期转换器"""
    
    # 天干列表
    HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    
    # 地支列表
    EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    @classmethod
    def convert_bazi_to_solar(cls, pillars: Dict[str, str], target_year: Optional[int] = None) -> Optional[Tuple[str, str]]:
        """
        根据八字四柱反推公历日期和时间
        
        Args:
            pillars: 四柱字典，如 {'year': '乙丑', 'month': '乙酉', 'day': '丙辰', 'hour': '辛卯'}
            target_year: 目标年份（可选，默认使用当前年份）
            
        Returns:
            (solar_date, solar_time) 元组，格式为 ("YYYY-MM-DD", "HH:MM")
            反推失败返回 None
        """
        if not pillars:
            return None
        
        # 1. 根据时柱确定时间（使用已有的逻辑）
        hour_pillar = pillars.get('hour', '')
        if not hour_pillar or len(hour_pillar) != 2:
            return None
        
        # 直接使用时柱地支获取时辰对应的小时
        hour_branch = hour_pillar[1]  # 时柱地支
        hour = BaziToTimeConverter.BRANCH_TO_HOUR.get(hour_branch)
        if hour is None:
            return None
        
        minute = 0
        time_str = f"{hour:02d}:00"
        
        # 2. 根据年柱确定年份（取最接近目标年份的年份）
        year_pillar = pillars.get('year', '')
        if not year_pillar or len(year_pillar) != 2:
            return None
        
        year_stem = year_pillar[0]
        year_branch = year_pillar[1]
        
        # 获取年柱对应的年份（60年一个周期）
        if target_year is None:
            target_year = datetime.now().year
        
        stem_idx = cls.HEAVENLY_STEMS.index(year_stem) if year_stem in cls.HEAVENLY_STEMS else -1
        branch_idx = cls.EARTHLY_BRANCHES.index(year_branch) if year_branch in cls.EARTHLY_BRANCHES else -1
        
        if stem_idx < 0 or branch_idx < 0:
            return None
        
        # 计算年份（60年一个周期）
        year = cls._find_closest_year(stem_idx, branch_idx, target_year)
        
        # 3. 根据月柱和日柱确定月份和日期
        month_pillar = pillars.get('month', '')
        day_pillar = pillars.get('day', '')
        
        if not month_pillar or not day_pillar:
            return None
        
        # 遍历可能的月份和日期（简化实现：遍历一年）
        solar_date = cls._find_matching_date(year, month_pillar, day_pillar, hour, minute)
        
        if solar_date:
            return (solar_date, time_str)
        
        # 如果当前年份找不到，尝试前后各一个周期（60年）
        for cycle_adjust in [-60, 60]:
            try_year = year + cycle_adjust
            if 1900 <= try_year <= 2100:  # 合理的年份范围
                solar_date = cls._find_matching_date(try_year, month_pillar, day_pillar, hour, minute)
                if solar_date:
                    return (solar_date, time_str)
        
        return None
    
    @classmethod
    def _get_year_ganzhi(cls, year: int) -> str:
        """
        获取指定年份的干支
        
        Args:
            year: 年份
            
        Returns:
            干支字符串，如 "甲子"
        """
        # 天干地支60年一个周期
        # 1984年是甲子年
        base_year = 1984
        base_stem_idx = 0  # 甲
        base_branch_idx = 0  # 子
        
        offset = (year - base_year) % 60
        stem_idx = (base_stem_idx + offset) % 10
        branch_idx = (base_branch_idx + offset) % 12
        
        return f"{cls.HEAVENLY_STEMS[stem_idx]}{cls.EARTHLY_BRANCHES[branch_idx]}"
    
    @classmethod
    def _find_closest_year(cls, stem_idx: int, branch_idx: int, target_year: int) -> int:
        """
        找到最接近目标年份的年份（满足指定干支）
        
        Args:
            stem_idx: 天干索引
            branch_idx: 地支索引
            target_year: 目标年份
            
        Returns:
            最接近的年份
        """
        # 1984年是甲子年（stem_idx=0, branch_idx=0）
        base_year = 1984
        
        # 计算目标年份的干支
        target_offset = (target_year - base_year) % 60
        target_stem_idx = target_offset % 10
        target_branch_idx = target_offset % 12
        
        # 计算所需干支相对于甲子的偏移量
        # 需要找到满足 stem_idx 和 branch_idx 的年份
        # 在60年周期内，每个干支组合唯一对应一个年份
        
        # 方法：遍历60年周期，找到匹配的年份
        best_year = None
        min_diff = float('inf')
        
        for cycle_offset in range(-2, 3):  # 检查前后2个周期（120年范围）
            for i in range(60):
                candidate_offset = i + cycle_offset * 60
                candidate_year = base_year + candidate_offset
                
                # 计算该年份的干支索引
                year_offset = (candidate_year - base_year) % 60
                year_stem_idx = year_offset % 10
                year_branch_idx = year_offset % 12
                
                # 检查是否匹配
                if year_stem_idx == stem_idx and year_branch_idx == branch_idx:
                    diff = abs(candidate_year - target_year)
                    if diff < min_diff:
                        min_diff = diff
                        best_year = candidate_year
        
        if best_year is None:
            # 如果找不到，使用简单计算
            # 计算相对于甲子的偏移量
            offset = None
            for i in range(60):
                if (i % 10 == stem_idx) and (i % 12 == branch_idx):
                    offset = i
                    break
            
            if offset is not None:
                # 找到最接近目标年份的周期
                base_offset = (target_year - base_year) % 60
                cycle_adjustment = ((offset - base_offset + 30) // 60) * 60
                best_year = target_year + (offset - base_offset) - cycle_adjustment
            else:
                # 降级方案：使用目标年份
                best_year = target_year
        
        return best_year
    
    @classmethod
    def _find_matching_date(cls, year: int, month_pillar: str, day_pillar: str, hour: int, minute: int) -> Optional[str]:
        """
        找到匹配月柱和日柱的日期
        
        Args:
            year: 年份
            month_pillar: 月柱，如 "乙酉"
            day_pillar: 日柱，如 "丙辰"
            hour: 小时
            minute: 分钟
            
        Returns:
            日期字符串，格式为 "YYYY-MM-DD"，找不到返回 None
        """
        # 优化：先按日柱查找（日柱60天一个周期，更容易匹配）
        # 然后验证月柱是否匹配
        
        from datetime import timedelta
        
        # 日柱60天一个周期，所以最多需要遍历60天就能找到匹配的日柱
        # 但月柱需要匹配，所以可能需要遍历更多天数
        
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        
        # 先尝试快速匹配：找到第一个匹配日柱的日期，然后检查月柱
        current_date = start_date
        checked_days = 0
        max_check_days = 400  # 最多检查400天（约13个月，考虑跨年）
        
        while current_date <= end_date and checked_days < max_check_days:
            try:
                solar = Solar.fromYmdHms(year, current_date.month, current_date.day, hour, minute, 0)
                lunar = solar.getLunar()
                bazi = lunar.getBaZi()
                
                # 检查日柱
                actual_day_pillar = f"{bazi[2][0]}{bazi[2][1]}"
                
                if actual_day_pillar == day_pillar:
                    # 日柱匹配，检查月柱
                    actual_month_pillar = f"{bazi[1][0]}{bazi[1][1]}"
                    if actual_month_pillar == month_pillar:
                        return current_date.strftime("%Y-%m-%d")
                
                current_date += timedelta(days=1)
                checked_days += 1
                
            except Exception:
                current_date += timedelta(days=1)
                checked_days += 1
                continue
        
        return None

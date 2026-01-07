# -*- coding: utf-8 -*-
"""
八字到时辰转换器

根据八字时柱的地支推算对应的时辰（小时）。

时辰与小时对应关系：
子时: 23:00-01:00 (取00:30)
丑时: 01:00-03:00 (取02:00)
寅时: 03:00-05:00 (取04:00)
卯时: 05:00-07:00 (取06:00)
辰时: 07:00-09:00 (取08:00)
巳时: 09:00-11:00 (取10:00)
午时: 11:00-13:00 (取12:00)
未时: 13:00-15:00 (取14:00)
申时: 15:00-17:00 (取16:00)
酉时: 17:00-19:00 (取18:00)
戌时: 19:00-21:00 (取20:00)
亥时: 21:00-23:00 (取22:00)
"""

import re
from typing import Tuple, Optional


class BaziToTimeConverter:
    """八字到时辰转换器"""
    
    # 地支与时辰中心小时的映射（取时辰中间时刻）
    BRANCH_TO_HOUR = {
        '子': 0,   # 23:00-01:00，取00:00（子时正中）
        '丑': 2,   # 01:00-03:00
        '寅': 4,   # 03:00-05:00
        '卯': 6,   # 05:00-07:00
        '辰': 8,   # 07:00-09:00
        '巳': 10,  # 09:00-11:00
        '午': 12,  # 11:00-13:00
        '未': 14,  # 13:00-15:00
        '申': 16,  # 15:00-17:00
        '酉': 18,  # 17:00-19:00
        '戌': 20,  # 19:00-21:00
        '亥': 22,  # 21:00-23:00
    }
    
    # 地支列表
    EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    # 天干列表
    HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    
    @classmethod
    def parse_bazi_string(cls, bazi_str: str) -> Optional[dict]:
        """
        解析八字字符串
        
        支持格式：
        - "乙丑・丙戌・癸巳・戊午" (带分隔符)
        - "乙丑丙戌癸巳戊午" (无分隔符)
        - "乙丑 丙戌 癸巳 戊午" (空格分隔)
        
        Args:
            bazi_str: 八字字符串
            
        Returns:
            包含四柱信息的字典，如 {'year': ('乙', '丑'), 'month': ('丙', '戌'), ...}
            解析失败返回 None
        """
        if not bazi_str or str(bazi_str).strip() == "" or str(bazi_str) == "nan":
            return None
        
        bazi_str = str(bazi_str).strip()
        
        # 移除所有分隔符，提取干支
        # 匹配模式：连续的天干地支对
        clean_str = re.sub(r'[・·、，,\s]+', '', bazi_str)
        
        # 应该是8个字符（4柱 x 2字符）
        if len(clean_str) != 8:
            return None
        
        # 验证并提取四柱
        pillars = {}
        pillar_names = ['year', 'month', 'day', 'hour']
        
        for i, name in enumerate(pillar_names):
            stem = clean_str[i * 2]
            branch = clean_str[i * 2 + 1]
            
            if stem not in cls.HEAVENLY_STEMS:
                return None
            if branch not in cls.EARTHLY_BRANCHES:
                return None
            
            pillars[name] = (stem, branch)
        
        return pillars
    
    @classmethod
    def get_hour_from_bazi(cls, bazi_str: str) -> Optional[int]:
        """
        根据八字字符串获取时辰对应的小时
        
        Args:
            bazi_str: 八字字符串
            
        Returns:
            小时数（0-23），解析失败返回 None
        """
        pillars = cls.parse_bazi_string(bazi_str)
        if not pillars:
            return None
        
        hour_branch = pillars['hour'][1]  # 时柱地支
        return cls.BRANCH_TO_HOUR.get(hour_branch)
    
    @classmethod
    def get_time_from_bazi(cls, bazi_str: str) -> Optional[str]:
        """
        根据八字字符串获取时间字符串
        
        Args:
            bazi_str: 八字字符串
            
        Returns:
            时间字符串 "HH:00"，解析失败返回 None
        """
        hour = cls.get_hour_from_bazi(bazi_str)
        if hour is None:
            return None
        
        return f"{hour:02d}:00"
    
    @classmethod
    def get_day_pillar(cls, bazi_str: str) -> Optional[str]:
        """
        获取日柱（日元）
        
        Args:
            bazi_str: 八字字符串
            
        Returns:
            日柱字符串（如"癸巳"），解析失败返回 None
        """
        pillars = cls.parse_bazi_string(bazi_str)
        if not pillars:
            return None
        
        day_stem, day_branch = pillars['day']
        return f"{day_stem}{day_branch}"
    
    @classmethod
    def get_four_pillars(cls, bazi_str: str) -> Optional[dict]:
        """
        获取完整的四柱信息
        
        Args:
            bazi_str: 八字字符串
            
        Returns:
            四柱字典，如 {'year': '乙丑', 'month': '丙戌', 'day': '癸巳', 'hour': '戊午'}
        """
        pillars = cls.parse_bazi_string(bazi_str)
        if not pillars:
            return None
        
        return {
            'year': f"{pillars['year'][0]}{pillars['year'][1]}",
            'month': f"{pillars['month'][0]}{pillars['month'][1]}",
            'day': f"{pillars['day'][0]}{pillars['day'][1]}",
            'hour': f"{pillars['hour'][0]}{pillars['hour'][1]}"
        }


# 便捷函数
def bazi_to_hour(bazi_str: str) -> Optional[int]:
    """根据八字获取小时"""
    return BaziToTimeConverter.get_hour_from_bazi(bazi_str)


def bazi_to_time(bazi_str: str) -> Optional[str]:
    """根据八字获取时间字符串"""
    return BaziToTimeConverter.get_time_from_bazi(bazi_str)


def get_day_pillar(bazi_str: str) -> Optional[str]:
    """获取日柱"""
    return BaziToTimeConverter.get_day_pillar(bazi_str)


if __name__ == "__main__":
    # 测试
    test_cases = [
        "乙丑・丙戌・癸巳・戊午",
        "癸酉・甲寅・庚辰・丁丑",
        "甲子 乙丑 丙寅 丁卯",
        "甲子乙丑丙寅丁卯",
    ]
    
    for bazi in test_cases:
        print(f"\n八字: {bazi}")
        print(f"  四柱: {BaziToTimeConverter.get_four_pillars(bazi)}")
        print(f"  日柱: {BaziToTimeConverter.get_day_pillar(bazi)}")
        print(f"  时辰小时: {BaziToTimeConverter.get_hour_from_bazi(bazi)}")
        print(f"  时间字符串: {BaziToTimeConverter.get_time_from_bazi(bazi)}")


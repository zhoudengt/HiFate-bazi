# -*- coding: utf-8 -*-
"""
八字解析器

解析换行分隔的4柱格式八字（年柱/月柱/日柱/时柱）
"""

from typing import Optional, Dict, List


class BaziParser:
    """八字解析器"""
    
    # 天干列表
    HEAVENLY_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
    
    # 地支列表
    EARTHLY_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
    
    @classmethod
    def parse_bazi_lines(cls, bazi_text: str) -> Optional[Dict[str, str]]:
        """
        解析换行分隔的4柱格式八字
        
        支持格式：
        - 换行分隔（年柱/月柱/日柱/时柱）
        - 如：
          乙丑
          乙酉
          丙辰
          辛卯
        
        Args:
            bazi_text: 八字文本
            
        Returns:
            包含四柱信息的字典，如 {'year': '乙丑', 'month': '乙酉', 'day': '丙辰', 'hour': '辛卯'}
            解析失败返回 None
        """
        if not bazi_text or str(bazi_text).strip() == "" or str(bazi_text) == "nan":
            return None
        
        bazi_text = str(bazi_text).strip()
        
        # 按换行符分割
        lines = [line.strip() for line in bazi_text.split('\n') if line.strip()]
        
        # 必须恰好4行
        if len(lines) != 4:
            return None
        
        pillars = {}
        pillar_names = ['year', 'month', 'day', 'hour']
        
        for i, pillar_name in enumerate(pillar_names):
            pillar_text = lines[i]
            
            # 验证格式（应该是2个字符，天干+地支）
            if len(pillar_text) != 2:
                return None
            
            stem = pillar_text[0]
            branch = pillar_text[1]
            
            # 验证天干地支
            if stem not in cls.HEAVENLY_STEMS:
                return None
            if branch not in cls.EARTHLY_BRANCHES:
                return None
            
            pillars[pillar_name] = pillar_text
        
        return pillars
    
    @classmethod
    def format_bazi_string(cls, pillars: Dict[str, str]) -> str:
        """
        格式化八字为字符串格式（用于调用API）
        
        Args:
            pillars: 四柱字典
            
        Returns:
            八字字符串，如 "乙丑乙酉丙辰辛卯"
        """
        return f"{pillars['year']}{pillars['month']}{pillars['day']}{pillars['hour']}"

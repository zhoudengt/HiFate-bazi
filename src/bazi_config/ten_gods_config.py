# -*- coding: utf-8 -*-

from ..data.constants import HEAVENLY_STEMS, HIDDEN_STEMS

class TenGodsCalculator:
    """十神计算器 - 修正版本"""

    def __init__(self):
        # 十神关系映射：基于日干与其他天干的关系
        self.ten_gods_relation = {
            0: '比肩',  # 同我
            1: '劫财',  # 同我但阴阳不同
            2: '食神',  # 我生
            3: '伤官',  # 我生但阴阳不同
            4: '偏财',  # 我克
            5: '正财',  # 我克但阴阳不同
            6: '七杀',  # 克我
            7: '正官',  # 克我但阴阳不同
            8: '偏印',  # 生我
            9: '正印'   # 生我但阴阳不同
        }

    def get_stem_ten_god(self, day_stem, target_stem):
        """计算天干十神"""
        if day_stem == target_stem:
            return '比肩'

        day_index = HEAVENLY_STEMS.index(day_stem)
        target_index = HEAVENLY_STEMS.index(target_stem)

        # 计算关系索引
        relation_index = (target_index - day_index) % 10

        return self.ten_gods_relation.get(relation_index, '未知')

    def get_main_star(self, day_stem, pillar_stem, pillar_type):
        """计算主星 - 修正版本"""
        if pillar_type == 'day':
            return '元男'  # 日柱主星固定为元男

        return self.get_stem_ten_god(day_stem, pillar_stem)

    def get_branch_ten_gods(self, day_stem, branch):
        """计算地支藏干的十神 - 修正版本"""
        hidden_stems = HIDDEN_STEMS.get(branch, [])
        ten_gods = []

        for stem_info in hidden_stems:
            if isinstance(stem_info, str) and stem_info:
                stem_char = stem_info[0]  # 获取天干字符
                ten_god = self.get_stem_ten_god(day_stem, stem_char)
                ten_gods.append(ten_god)

        return ten_gods









































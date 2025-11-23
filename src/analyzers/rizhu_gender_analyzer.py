#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日柱性别查询分析器
处理日柱和性别组合的命理查询逻辑
"""

import sys
import os

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.bazi_config.rizhu_gender_config import get_rizhu_gender_description

class RizhuGenderAnalyzer:
    """日柱性别查询分析器"""

    def __init__(self, bazi_pillars, gender):
        """
        初始化分析器

        Args:
            bazi_pillars (dict): 八字四柱数据
            gender (str): 性别，'male'或'female'
        """
        self.bazi_pillars = bazi_pillars
        self.gender = gender
        self.day_stem = bazi_pillars['day']['stem']
        self.day_branch = bazi_pillars['day']['branch']
        self.rizhu = f"{self.day_stem}{self.day_branch}"

    def analyze_rizhu_gender(self):
        """
        分析日柱性别组合的命理

        Returns:
            dict: 包含命理描述的结果字典
        """
        result = {
            'rizhu': self.rizhu,
            'gender': self.gender,
            'descriptions': [],
            'has_data': False
        }

        # 获取日柱性别对应的命理描述
        descriptions = get_rizhu_gender_description(self.rizhu, self.gender)

        if descriptions:
            result['descriptions'] = descriptions
            result['has_data'] = True
            result['summary'] = f"日柱{self.rizhu}{'男' if self.gender == 'male' else '女'}命分析"
        else:
            result['summary'] = f"日柱{self.rizhu}{'男' if self.gender == 'male' else '女'}命暂无详细分析数据"

        return result

    def get_formatted_output(self):
        """
        获取格式化的输出结果

        Returns:
            str: 格式化的命理描述文本
        """
        analysis_result = self.analyze_rizhu_gender()

        if not analysis_result['has_data']:
            return analysis_result['summary']

        # 构建格式化的输出
        output_lines = []
        #output_lines.append(f"【日柱{analysis_result['rizhu']}{'男' if self.gender == 'male' else '女'}命分析】")
        output_lines.append(f"【性格与命运解析】")

        output_lines.append("=" * 60)

        for i, description in enumerate(analysis_result['descriptions'], 1):
            output_lines.append(f"{i}. {description}")

        return "\n".join(output_lines)
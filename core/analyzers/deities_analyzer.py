#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
神煞分析器
处理神煞规则的分析逻辑
"""

from core.config.deities_rules_config import DEITIES_RULES_CONFIG, DEITIES_COMBINATIONS_CONFIG


class DeitiesAnalyzer:
    """神煞分析器 - 简化版本"""

    def __init__(self, bazi_pillars, details, gender):
        self.bazi_pillars = bazi_pillars
        self.details = details
        self.gender = gender

    def analyze_all_deities_rules(self):
        """分析所有神煞规则"""
        rules_result = {}

        # 分析每个神煞的影响
        for pillar in ['year', 'month', 'day', 'hour']:
            deities_list = self.details[pillar].get('deities', [])
            for deity in deities_list:
                deity_rules = self._analyze_deity_rules(deity, pillar)
                if deity_rules:
                    rules_result[f"{pillar}柱{deity}"] = deity_rules

        return rules_result

    def analyze_deities_combinations(self):
        """分析神煞组合规则"""
        combinations_result = {}

        # 获取所有神煞
        all_deities = self._get_all_deities()

        # 分析组合规则
        for combo_name, combo_config in DEITIES_COMBINATIONS_CONFIG.items():
            condition = combo_config['condition']

            # 检查条件是否满足
            if combo_config.get('gender_specific', False):
                if condition(all_deities, self.gender):
                    combinations_result[combo_name] = combo_config['rule']
            else:
                if condition(all_deities):
                    combinations_result[combo_name] = combo_config['rule']

        return combinations_result

    def get_all_deities_list(self):
        """获取所有神煞列表"""
        all_deities = []
        for pillar in ['year', 'month', 'day', 'hour']:
            deities = self.details[pillar].get('deities', [])
            if deities:
                all_deities.extend(deities)
        return list(set(all_deities))

    def _analyze_deity_rules(self, deity_name, pillar):
        """分析单个神煞的规则"""
        rules = []

        deity_config = DEITIES_RULES_CONFIG.get(deity_name)

        if not deity_config:
            return ""

        # 处理性别特定的规则
        if deity_config.get('gender_specific', False):
            if isinstance(deity_config['rules'], dict):
                gender_rules = deity_config['rules'].get(self.gender, [])
                rules.extend(gender_rules)
            else:
                rules.extend(deity_config['rules'])
                gender_rule = deity_config.get('gender_rules', {}).get(self.gender)
                if gender_rule:
                    rules.append(gender_rule)
        else:
            rules.extend(deity_config['rules'])

        # 处理柱位特定的规则
        pillar_specific = deity_config.get('pillar_specific', {})
        pillar_rule = pillar_specific.get(pillar)
        if pillar_rule:
            rules.append(pillar_rule)

        return "；".join(rules) if rules else ""

    def _get_all_deities(self):
        """获取所有神煞"""
        return self.get_all_deities_list()
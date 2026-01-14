# -*- coding: utf-8 -*-
"""
规则类目映射器

将中文类目名称映射到 rule_type
"""

from typing import List


class RuleCategoryMapper:
    """规则类目映射器"""
    
    # 类目名称到 rule_type 的映射
    CATEGORY_MAPPING = {
        "财富": "wealth",
        "事业": "career",
        "婚姻": "marriage",
        "健康": "health",
        "性格": "character",
        "子女": "children",
        "身体": "health",
        "桃花": "peach_blossom",
        "总评": "general",
        "流年": "fortune",
        "年运": "annual",
        "运势": "fortune",
    }
    
    @classmethod
    def map_categories_to_rule_types(cls, categories_text: str) -> List[str]:
        """
        将类目文本（空格分隔）映射到 rule_type 列表
        
        Args:
            categories_text: 类目文本，如 "财富 事业"
            
        Returns:
            rule_type 列表，如 ["wealth", "career"]
        """
        if not categories_text or str(categories_text).strip() == "":
            return []
        
        categories = str(categories_text).strip().split()
        rule_types = []
        
        for category in categories:
            category = category.strip()
            if category in cls.CATEGORY_MAPPING:
                rule_type = cls.CATEGORY_MAPPING[category]
                if rule_type not in rule_types:
                    rule_types.append(rule_type)
        
        return rule_types
